"""
single_stranded_design table

NP
"""

from sqlalchemy import Table, Column, String, Integer, ForeignKey
from sqlalchemy.schema import DDL

__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2010-11-05 18:16:33 +0100 (Fri, 05 Nov 2010) $'
__revision__ = '$Rev: 11715 $'
__source__ = '$URL: http://svn/cenix/TheLMA/trunk/thelma/db/schema/tables/singlestrandeddesign.py $'

__all__ = ['create_table']


def _setup_postgres_ddl(table):
    """
    ...explain..
    """
    DDL("""
        CREATE UNIQUE INDEX %(table)s_key ON %(table)s
          USING btree (modification, md5(sequence));
        """,
        on='postgres',
        ).execute_at('after-create', table)

    # Index on md5(single_stranded_desing.sequence) to speed lookups
    DDL("""
        CREATE INDEX %(table)s_sequence_md5 ON %(table)s
          USING btree (md5(sequence));
        """,
        on='postgres',
        ).execute_at('after-create', table)


def _setup_sqlite_ddl(table):
    """
    ...explain..
    """
    DDL("""
        CREATE UNIQUE INDEX %(table)s_key ON %(table)s
          (modification, sequence);
        """,
        on='sqlite',
        ).execute_at('after-create', table)

    # Index on md5(single_stranded_desing.sequence) to speed lookups
    DDL("""
        CREATE INDEX %(table)s_sequence ON %(table)s
          (sequence);
        """,
        on='sqlite',
        ).execute_at('after-create', table)


def create_table(metadata, molecule_design_tbl,
                 single_stranded_modification_tbl):
    """
    single_stranded_design table factory
    """
    tbl = Table('single_stranded_design', metadata,
        Column('molecule_design_id', Integer,
               ForeignKey(molecule_design_tbl.c.molecule_design_id,
                          onupdate='CASCADE', ondelete='CASCADE'),
               primary_key=True),
        Column('sequence', String, nullable=False), # FIXME: validate sequence as a nucleic_acid domain
        Column('modification', String,
               ForeignKey(single_stranded_modification_tbl.c.name,
                          # FIXME: Change action to ON UPDATE CASCADE ON DELETE RESTRICT in the DB
                          onupdate='CASCADE', ondelete='CASCADE'),
               nullable=False),
        )
    _setup_postgres_ddl(tbl)
    _setup_sqlite_ddl(tbl)
    return tbl
