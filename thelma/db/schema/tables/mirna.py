"""
MiRNA table
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.schema import DDL

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def _setup_postgres_ddl(table):
    DDL("""
        ALTER TABLE %(table)s ALTER COLUMN sequence SET DATA TYPE rna
        """,
        on='postgres'
        ).execute_at('after-create', table)


def create_table(metadata):
    "Table factory."
    tbl = Table('mirna', metadata,
        Column('accession', String(24),
               CheckConstraint('length(accession)>0'),
               primary_key=True),
        Column('sequence', String, nullable=False),
        )
    _setup_postgres_ddl(tbl)
    return tbl
