"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Script to populate a TheLMA test database.

This is the (somewhat rough) workflow:
 1) Drop the target database (defined by TARGET_DB_NAME, TARGET_DB_HOST,
    TARGET_DB_PORT; the user name and password are assumed to be the same
    as what is used for the source database defined in the app config file
    referenced by the alembic config file);
 2) Create fresh empty TARGET_DB_NAME on TARGET_DB_HOST and TARGET_DB_PORT;
 3) Migrate structure to head using alembic;
 4) Transfer selected objects from the source database to the target database;
 5) Export data from target database with pg_dump:
         pg_dump -f p -a > exported_data.sql

The script assumes you have alembic in your virtual environment and pg_dump
somewhere on your system.
"""
import os
from subprocess import PIPE
from subprocess import Popen
import sys

from alembic.config import Config
from pyramid.registry import Registry
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import subqueryload_all

from everest.repositories.constants import REPOSITORY_TYPES
from everest.repositories.interfaces import IRepositoryManager
from paste.deploy import appconfig # pylint: disable=E0611,F0401
from thelma.entities.container import ContainerSpecs
from thelma.entities.device import Device
from thelma.entities.device import DeviceType
from thelma.entities.experiment import ExperimentMetadataType
from thelma.entities.liquidtransfer import PipettingSpecs
from thelma.entities.liquidtransfer import ReservoirSpecs
from thelma.entities.moleculetype import MoleculeType
from thelma.entities.organization import Organization
from thelma.entities.project import Project
from thelma.entities.rack import PlateSpecs
from thelma.entities.rack import Rack
from thelma.entities.rack import RackPosition
from thelma.entities.rack import RackShape
from thelma.entities.rack import RackSpecs
from thelma.entities.rack import TubeRack
from thelma.entities.rack import TubeRackSpecs
from thelma.entities.species import Species
from thelma.entities.status import ItemStatus
from thelma.entities.user import User
from thelma.run import create_config


__docformat__ = 'reStructuredText en'
__all__ = []

try:
    alembic_ini_file_path = sys.argv[1]
except: # catch all pylint:disable=W0702
    print('Usage: python populate_test_db.py <alembic config file>')


TARGET_DB_HOST = 'raven'
TARGET_DB_PORT = '5432'
TARGET_DB_NAME = 'unidb_unit_test_empty'
PG_BINARIES_PATH = '/Library/PostgreSQL/9.2/bin/'
EXPORT_DATA_FILE = 'exported_data_%s.sql' % TARGET_DB_NAME


def parse_config():
    alembic_cfg = Config(alembic_ini_file_path)
    app_ini_file_name = alembic_cfg.get_main_option('pylons_config_file')
    app_ini_file_dir = os.path.dirname(alembic_cfg.config_file_name)
    app_config_uri = 'config:%s' % app_ini_file_name
    return appconfig(app_config_uri, 'thelma', relative_to=app_ini_file_dir)

print('STARTING TEST DATABASE CREATION:')

print('Parsing configuration.')
settings = parse_config()

db_user = settings.get('db_user')
db_pwd = settings.get('db_password')

DROP_DB_CMD = os.path.join(PG_BINARIES_PATH,
                           'dropdb -h %s -p %s -U %s %s'
                           % (TARGET_DB_HOST, TARGET_DB_PORT, db_user,
                              TARGET_DB_NAME))
CREATE_DB_CMD = os.path.join(PG_BINARIES_PATH,
                           'createdb -h %s -p %s -U %s %s'
                            % (TARGET_DB_HOST, TARGET_DB_PORT, db_user,
                               TARGET_DB_NAME))
ALEMBIC_CMD = os.path.join(os.path.dirname(sys.executable),
                           'alembic --config %s upgrade head'
                           % alembic_ini_file_path)
PG_DUMP_CMD = os.path.join(PG_BINARIES_PATH,
                           'pg_dump -h %s -p %s -U %s -a %s > %s'
                           % (TARGET_DB_HOST, TARGET_DB_PORT, db_user,
                              TARGET_DB_NAME, EXPORT_DATA_FILE))

FIX_SEQUENCES_SQL = """\
CREATE OR REPLACE FUNCTION
    "reset_sequence" (tablename text, columnname text, sequence_name text)
    RETURNS "pg_catalog"."void" AS
    $body$
      DECLARE
      BEGIN
      EXECUTE 'SELECT setval( ''' || sequence_name  || ''', ' ||
              '(SELECT MAX(' || columnname || ') FROM ' || tablename || ')' || ')';
      END;
    $body$
    LANGUAGE 'plpgsql';

select table_name || '_' || column_name || '_seq',
    reset_sequence(table_name, column_name, table_name || '_' || column_name || '_seq')
    from information_schema.columns
    where column_default like 'nextval%';
"""


def run_command(command_string):
    child = Popen(command_string,
                  shell=True,
                  universal_newlines=True, stdout=PIPE, stderr=PIPE)
    sys.stdout.write('Running command <%s>.\n' % command_string)
    output_string, error_string = child.communicate()
    if error_string != '':
        sys.stderr.write('Failed. Output:\n%s' % error_string)
        sys.exit(0)
    if error_string != '':
        sys.stdout.write('Sucess. Output:\n%s' % output_string)


print('Dropping target database.')
run_command(DROP_DB_CMD)

print('Creating new target database.')
run_command(CREATE_DB_CMD)

print 'Migrating target database to head.'
run_command(ALEMBIC_CMD)


def setup_thelma(thelma_settings):
    reg = Registry('thelma')
    config = create_config(thelma_settings, registry=reg)
    config.setup_registry(settings=thelma_settings)
    config.begin()
    config.load_zcml('configure.zcml')
    repo_mgr = config.get_registered_utility(IRepositoryManager)
    repo_mgr.initialize_all()
    target_db_string = "postgresql+psycopg2://%s:%s@%s:%s/%s" \
                       % (db_user, db_pwd, TARGET_DB_HOST,
                          TARGET_DB_PORT, TARGET_DB_NAME)
    tgt_engine = create_engine(target_db_string)
    repo = repo_mgr.get(REPOSITORY_TYPES.RDB)
    src_sess = repo.session_factory()
    tgt_session_maker = sessionmaker(bind=tgt_engine)
    tgt_sess = tgt_session_maker()
    return src_sess, tgt_sess

print('Setting up source and target database sessions.')
src_session, tgt_session = setup_thelma(settings)


class EntityTraverser(object):
    def __init__(self, transferer):
        self._transferer = transferer

    def traverse(self, entity):
        raise NotImplementedError('Abstract method.')


class RackPreTraverser(EntityTraverser):
    def traverse(self, rack_):
        for cnt in rack_.containers:
            getattr(cnt, 'barcode', None)
            spl = getattr(cnt, 'sample', None)
            if not spl is None:
                getattr(spl, 'molecule_design_pool', None)
        loc_rack = getattr(rack_, 'location_rack', None)
        if not loc_rack is None:
            getattr(loc_rack, 'location', None)


class ProjectPreTraverser(EntityTraverser):
    def traverse(self, project_):
        getattr(project_, 'subprojects', None)


class PlateSpecsPreTraverser(EntityTraverser):
    def traverse(self, plate_):
        getattr(plate_, 'well_specs')


class TubeRackSpecsPreTraverser(EntityTraverser):
    def traverse(self, tube_rack_):
        getattr(tube_rack_, 'tube_specs')


class EntityTransferer(object):
    __pre_trv_map = {Rack:RackPreTraverser,
                     TubeRack:RackPreTraverser,
#                     Project:ProjectPreTraverser,
                     PlateSpecs:PlateSpecsPreTraverser,
                     TubeRackSpecs:TubeRackSpecsPreTraverser,
#                     BarcodedLocation:BarcodedLocationPreTraverser
                     }
    __post_trv_map = {}

    def __init__(self, src_sess, tgt_sess):
        self.__src_session = src_sess
        self.__tgt_session = tgt_sess

    @classmethod
    def get_traverser(cls, entity_class):
        return cls.__pre_trv_map.get(entity_class)

    def transfer(self, entity):
        pre_trv_cls = self.get_traverser(type(entity))
        if not pre_trv_cls is None:
            pre_trv = pre_trv_cls(self)
            pre_trv.traverse(entity)
        tgt_ent = self.__tgt_session.merge(entity)
        self.__tgt_session.add(tgt_ent)
#        post_trv_cls = self.__post_trv_map.get(type(entity))
#        if not post_trv_cls is None:
#            post_trv = post_trv_cls(self)
#            post_trv.traverse(entity)

transfer = EntityTransferer(src_session, tgt_session).transfer

CONSTANTS_TABLES = ['transfer_type']

for constants_table in CONSTANTS_TABLES:
    for row in src_session.execute('select * from %s' % constants_table):
        tgt_session.execute('insert into %s (%s) values (%s)'
                            % (constants_table,
                               ','.join(row.keys()),
                               ','.join([str(val) if not isinstance(val, basestring)
                                         else "'%s'" % val
                                         for val in row.values()])))


SEMICONSTANT_ENTITY_CLASSES = [Organization,
                               User,
                               ItemStatus,
                               ContainerSpecs,
                               ExperimentMetadataType,
                               MoleculeType,
                               Species,
                               DeviceType,
                               Device,
                               PipettingSpecs,
                               RackPosition,
                               RackShape,
                               RackSpecs,
                               ReservoirSpecs,
                               ]

for ent_cls in SEMICONSTANT_ENTITY_CLASSES:
    print('Transferring %s records to target database.' % ent_cls.__name__)
    q = src_session.query(ent_cls)
    for ent in q.all():
        transfer(ent)
tgt_session.flush()


pq = src_session.query(Project) \
    .options(subqueryload_all('subprojects'))
project_ids = [72]
for project in pq.filter(Project.id.in_(project_ids)).all():
    print ('Transferring project %s to target database.' % project.label)
    transfer(project)

rq = src_session.query(TubeRack) \
    .options(subqueryload_all('containers.sample.sample_molecules.molecule.molecule_design.genes')) \
    .options(subqueryload_all('containers.sample.sample_molecules.molecule.molecule_design.supplier_molecule_designs')) \
    .options(subqueryload_all('containers.sample.sample_molecules.molecule.molecule_design.chemical_structures'))
rack_bcs = [
            '02504203', # 85 siRNA tubes 50 um
            '02501355', # 87 siRNA tubes 50 um
            '02503031', # 96 siRNA tubes 10 um
            '02500516', # 96 siRNA tubes 10 um
            '02481500', # 59 compound tubes
            '02498991', # 95 primer tubes
            '02502503', # 0 tubes
            '02503989', # 0 tubes
            '02500565', # 0 tubes
            '02500558', # 0 tubes
            '02490439', # 0 tubes
            '02488242', # 0 tubes
            '02503032', # 0 tubes
            '02490469', # 0 tubes
            '02503920', # 0 tubes
            '02488447', # 0 tubes
            '02501359', # 0 tubes
            '02501366', # 0 tubes
            ]
for rack in rq.filter(Rack.barcode.in_(rack_bcs)).all():
    print ('Transferring rack %s to target database.' % rack.barcode)
    transfer(rack)

tgt_session.commit()

print('Fixing sequence values.')
tgt_session.execute(FIX_SEQUENCES_SQL)

print('Exporting data to SQL file "%s".' % EXPORT_DATA_FILE)
run_command(PG_DUMP_CMD)

print('DONE WITH TEST DATABASE CREATION.')
