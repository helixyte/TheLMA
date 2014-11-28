"""
Utility functions for schema migrations with alembic.
"""
import os
import sys

from alembic import context
from alembic import op
from alembic.config import Config
from pkg_resources import resource_filename # pylint: disable=E0611
from sqlalchemy.engine import create_engine as sa_create_engine

from paste.deploy import appconfig


__docformat__ = 'reStructuredText en'
__all__ = ['create_engine',
           'get_db_url',
           'load_downgrade_sql_file',
           'load_upgrade_sql_file',
           'parse_config',
           ]


def parse_config():
    ok = True
    try:
        ini_file = sys.argv[1]
    except IndexError:
        ok = False
    else:
        ok = os.path.isfile(ini_file)
    if not ok:
        print('Usage: python base.py <alembic ini file>')
        sys.exit(0)
    alembic_cfg = Config(ini_file)
    return alembic_cfg


def get_db_url(config):
    config_file = config.get_main_option('pylons_config_file')
    config_uri = 'config:%s' % config_file
    settings = appconfig(config_uri, 'thelma',
                         relative_to=os.path.dirname(config.config_file_name))
    return settings.get('test_db_string')


def create_engine(config):
    db_url = get_db_url(config)
    return sa_create_engine(db_url)


def load_upgrade_sql_file(revision):
    _load_sql_file(revision, 'upgrade')


def load_downgrade_sql_file(revision):
    _load_sql_file(revision, 'downgrade')


def _load_sql_file(revision, action):
    script_rc = context.config.get_main_option("script_location") # pylint:disable=E1101
    script_dir = resource_filename(*script_rc.split(':'))
    rev_dir = os.path.join(script_dir, 'versions')
    sql_file = os.path.join(rev_dir, "%s_%s.sql" % (revision, action))
    if not os.path.isfile(sql_file):
        raise IOError('SQL migration file %s not found.' % sql_file)
    with open(sql_file) as sql_source:
        op.execute(sql_source.read()) # pylint:disable=E1101
