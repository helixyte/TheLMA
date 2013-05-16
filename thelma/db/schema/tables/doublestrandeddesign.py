"""
double_stranded_design table

NP
"""

from sqlalchemy import Table, Column, String, Integer, ForeignKey
from sqlalchemy.schema import CheckConstraint, DDL

__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2010-05-07 17:50:46 +0200 (Fri, 07 May 2010) $'
__revision__ = '$Rev: 11476 $'
__source__ = '$URL: http://svn/cenix/TheLMA/trunk/thelma/db/schema/tables/doublestrandeddesign.py $'

__all__ = ['create_table']


def _setup_postgres_ddl(table):
    """
    ...explain...
    """
    DDL("""
        CREATE UNIQUE INDEX %(table)s_key ON %(table)s
          USING btree (modification, md5(sequence_1), md5(sequence_2));
        """,
        on='postgres',
        ).execute_at('after-create', table)

    # Index on md5(double_stranded_desing.sequence_1) to speed lookups
    DDL("""
        CREATE INDEX %(table)s_sequence_1_md5 ON %(table)s
          USING btree (md5(sequence_1));
        """,
        on='postgres',
        ).execute_at('after-create', table)
    # Index on md5(double_stranded_desing.sequence_2) to speed lookups
    DDL("""
        CREATE INDEX %(table)s_sequence_2_md5 ON %(table)s
          USING btree (md5(sequence_2));
        """,
        on='postgres',
        ).execute_at('after-create', table)


def _setup_sqlite_ddl(table):
    """
    ...explain...
    """
    DDL("""
        CREATE UNIQUE INDEX %(table)s_key ON %(table)s
          (modification, sequence_1, sequence_2);
        """,
        on='sqlite',
        ).execute_at('after-create', table)
    DDL("""
        CREATE INDEX %(table)s_sequence_1 ON %(table)s (sequence_1);
        """,
        on='sqlite',
        ).execute_at('after-create', table)
    DDL("""
        CREATE INDEX %(table)s_sequence_2 ON %(table)s (sequence_2);
        """,
        on='sqlite',
        ).execute_at('after-create', table)


def create_table(metadata, molecule_design_tbl,
                 double_stranded_modification_tbl):
    """
    double_stranded_design table factory
    """
    tbl = Table('double_stranded_design', metadata,
        Column('molecule_design_id', Integer,
               ForeignKey(molecule_design_tbl.c.molecule_design_id,
                          onupdate='CASCADE', ondelete='CASCADE'),
               primary_key=True),
        Column('sequence_1', String, nullable=False), # FIXME: validate sequence as a nucleic_acid domain
        Column('sequence_2', String, nullable=False), # FIXME: validate sequence as a nucleic_acid domain
        Column('modification', String,
               ForeignKey(double_stranded_modification_tbl.c.name,
                          # FIXME: Change action to ON UPDATE CASCADE ON DELETE RESTRICT in the DB
                          # onupdate='CASCADE', ondelete='RESTRICT'
                          ),
               nullable=False),
        # We require sequence_1 to be lexicograpically less than or equal to
        # sequence_2 to avoid having otherwise identical designs with the
        # sequences exchanged.
        CheckConstraint('sequence_1 <= sequence_2', 'sequence_order'),
        )
    _setup_postgres_ddl(tbl)
    _setup_sqlite_ddl(tbl)
    return tbl
