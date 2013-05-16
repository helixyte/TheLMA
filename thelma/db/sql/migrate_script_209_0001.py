from collections import defaultdict
from everest.repositories.rdb import Session
from md5 import md5
from sqlalchemy.engine import create_engine
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import select
from thelma.db import create_metadata
from thelma.models.chemicalstructure import CHEMICAL_STRUCTURE_TYPE_IDS
from thelma.models.chemicalstructure import ChemicalStructure
from thelma.models.chemicalstructure import CompoundChemicalStructure
from thelma.models.chemicalstructure import ModificationChemicalStructure
from thelma.models.chemicalstructure import NucleicAcidChemicalStructure
from thelma.models.moleculedesign import AntiMirDesign
from thelma.models.moleculedesign import CompoundDesign
from thelma.models.moleculedesign import DoubleStrandedDesign
from thelma.models.moleculedesign import MiRnaInhibitorDesign
from thelma.models.moleculedesign import MiRnaMimicDesign
from thelma.models.moleculedesign import MoleculeDesign
from thelma.models.moleculedesign import SingleStrandedDesign
from thelma.models.moleculetype import MoleculeType
from thelma.models.organization import Organization
from thelma.models.suppliermoleculedesign import SingleSupplierMoleculeDesign
from thelma.models.suppliermoleculedesign import SupplierStructureAnnotation

# List of warnings recorded during the migration.
WARNINGS = []

# If this is set to True, the changes will be committed when the script
# completes successfully (i.e., without errors and without warnings).
COMMIT = False

db_server = 'raven'
db_port = '5432'
db_user = 'thelma'
db_password = 'roo8Adei'
db_name = 'unidb'
db_string = "postgresql+psycopg2://%(db_user)s:%(db_password)s" \
            "@%(db_server)s:%(db_port)s/%(db_name)s" % locals()
engine = create_engine(db_string)
metadata = create_metadata(engine)

sess = Session()


def process_or_create_structure(molecule_design, structure_type,
                                representation, new_structures):
    cs_query = sess.query(ChemicalStructure)
    md5_rpr = md5(representation).hexdigest()
    try:
        cs = cs_query.filter(
                func.md5(ChemicalStructure.representation) == md5_rpr,
                ChemicalStructure.structure_type == structure_type).one()
    except NoResultFound:
        cs = None
    if cs is None:
        if structure_type == CHEMICAL_STRUCTURE_TYPE_IDS.COMPOUND:
            structure_class = CompoundChemicalStructure
        elif structure_type == CHEMICAL_STRUCTURE_TYPE_IDS.NUCLEIC_ACID:
            structure_class = NucleicAcidChemicalStructure
        elif structure_type == CHEMICAL_STRUCTURE_TYPE_IDS.MODIFICATION:
            structure_class = ModificationChemicalStructure
        else:
            raise ValueError('Invalid structure type "%s".' % structure_type)
        cs = structure_class(representation,
                             molecule_designs=[molecule_design])
        new_structures.add(cs)
    else:
        cs.molecule_designs.append(molecule_design)
    return cs


def process_design(molecule_design, data, new_structures):
    if isinstance(molecule_design, DoubleStrandedDesign):
        if isinstance(molecule_design, MiRnaMimicDesign):
            # MIRNA_MIMI. No structure nor modification information.
            pass
        else:
            # SIRNA, LONG_DSRNA, AMPLICON, ESI_RNA, CLND_DSDNA
            mod, seq1, seq2 = data
            if not mod is None and not seq1 is None and not seq2 is None:
                cs_seq1 = process_or_create_structure(
                                    molecule_design,
                                    CHEMICAL_STRUCTURE_TYPE_IDS.NUCLEIC_ACID,
                                    seq1,
                                    new_structures)
                cs_seq2 = process_or_create_structure(
                                    molecule_design,
                                    CHEMICAL_STRUCTURE_TYPE_IDS.NUCLEIC_ACID,
                                    seq2,
                                    new_structures)
                if mod != 'unmodified':
                    process_or_create_structure(
                                    molecule_design,
                                    CHEMICAL_STRUCTURE_TYPE_IDS.MODIFICATION,
                                    mod, new_structures)
                for smd in molecule_design.supplier_molecule_designs:
                    if smd.sense_strand == 'sequence_1':
                        cs_ssa = cs_seq1
                    elif smd.sense_strand == 'sequence_2':
                        cs_ssa = cs_seq2
                    else:
                        cs_ssa = None
                    if not cs_ssa is None:
                        ssa = SupplierStructureAnnotation(smd, cs_ssa,
                                                          'SENSE_STRAND')
                        sess.add(ssa)
            else:
                # These are known CLND_DSDNA IDs for which we do not have
                # sequences.
                known_ids = [10404427, 10404428, 10404429,
                             10404430, 10404431, 10404432]
                if not molecule_design.molecule_design_id in known_ids:
                    WARNINGS.append('Information missing for design ID %d.' %
                                    molecule_design.molecule_design_id)
    elif isinstance(molecule_design, SingleStrandedDesign):
        if isinstance(molecule_design, MiRnaInhibitorDesign):
            # MIRNA_INHI. No sequence information.
            mod, = data
        else:
            # SSRNA, SSDNA, ANTI_MIR.
            mod, seq = data
            process_or_create_structure(
                                    molecule_design,
                                    CHEMICAL_STRUCTURE_TYPE_IDS.NUCLEIC_ACID,
                                    seq,
                                    new_structures)
        if mod != 'unmodified':
            process_or_create_structure(
                                    molecule_design,
                                    CHEMICAL_STRUCTURE_TYPE_IDS.MODIFICATION,
                                    mod,
                                    new_structures)
        if isinstance(molecule_design, AntiMirDesign):
            # ANTI_MIR.
            # Create forgotten supplier molecule design records.
            suppl_query = sess.query(Organization)
            supplier = suppl_query.filter_by(name='Regulus').one()
            smd = SingleSupplierMoleculeDesign(
                            # Use our ID as supplier product ID.
                            str(molecule_design.molecule_design_id),
                            supplier,
                            is_current=True)
            molecule_design.supplier_molecule_designs.append(smd)
    elif isinstance(molecule_design, CompoundDesign):
        # COMPOUND.
        smiles, = data
        process_or_create_structure(molecule_design,
                                    CHEMICAL_STRUCTURE_TYPE_IDS.COMPOUND,
                                    smiles,
                                    new_structures)
    else:
        raise ValueError('Unknown molecule design type: %s' %
                         molecule_design.__class__)

mt_ids = [
          'SSRNA',
          'SSDNA',
          'AMPLICON',
          'SIRNA',
          'COMPOUND',
          'LONG_DSRNA',
          'ANTI_MIR',
          'ESI_RNA',
          'CLND_DSDNA',
          'MIRNA_INHI',
          'MIRNA_MIMI'
          ]
for mt_id in mt_ids:
    print
    print '------------------------------'
    print 'Processing %s molecule type.' % mt_id
    print
    print 'Building cache.'
    print
    md_tab = metadata.tables['molecule_design']
    where_clause = md_tab.c.molecule_type_id == mt_id
    if mt_id == 'MIRNA_MIMI':
        cch = defaultdict(lambda: None)
    else:
        if mt_id in ['SIRNA', 'LONG_DSRNA', 'AMPLICON', 'ESI_RNA',
                     'CLND_DSDNA']:
            dsd_tab = metadata.tables['double_stranded_design']
            prx = select([md_tab.c.molecule_design_id, dsd_tab.c.modification,
                          dsd_tab.c.sequence_1, dsd_tab.c.sequence_2],
                         where_clause,
                         from_obj=md_tab.outerjoin(dsd_tab)).execute()
        elif mt_id == 'MIRNA_INHI':
            mi_inhi_tab = metadata.tables['mirna_inhibitor_design']
            prx = select([md_tab.c.molecule_design_id,
                          mi_inhi_tab.c.modification],
                         where_clause,
                         from_obj=md_tab.outerjoin(mi_inhi_tab)).execute()
        elif mt_id in ['SSRNA', 'SSDNA', 'ANTI_MIR']:
            ssd_tab = metadata.tables['single_stranded_design']
            prx = select([md_tab.c.molecule_design_id, ssd_tab.c.modification,
                          ssd_tab.c.sequence],
                         where_clause,
                         from_obj=md_tab.outerjoin(ssd_tab)).execute()
        elif mt_id == 'COMPOUND':
            cmp_tab = metadata.tables['compound']
            prx = select([md_tab.c.molecule_design_id, cmp_tab.c.smiles],
                         where_clause,
                         from_obj=md_tab.outerjoin(cmp_tab)).execute()
        cch = dict([(row[0], row[1:]) for row in prx.fetchall()])
    print 'Fetching molecule designs.'
    print
    mt = sess.query(MoleculeType).filter_by(molecule_type_id=mt_id).one()
    new_structs = set()
    mds = sess.query(MoleculeDesign).filter_by(molecule_type=mt).all()
    for idx, md in enumerate(mds):
        print '%s: %d (%3d %%)' % (md.molecule_type_id,
                                  md.molecule_design_id,
                                  int((idx + 1) * 100 / len(mds)))
        process_design(md, cch[md.molecule_design_id], new_structs)
    sess.add_all(new_structs)
    if COMMIT and len(WARNINGS) == 0:
        sess.commit()
    else:
        if WARNINGS:
            print 'Warnings occurred - rolling back transaction.'
            print 'Warning messages:'
            print '\n'.join(WARNINGS)
        sess.rollback()

