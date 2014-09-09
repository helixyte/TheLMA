"""
Chemical structure table.
"""
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.schema import DDL


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def _setup_postgres_ddl(table):
    DDL("""
        ALTER TABLE %(table)s ADD CONSTRAINT chemical_structure_md5_rpr
            UNIQUE(structure_type, md5(representation::text)
        """,
        on='postgres'
        ).execute_at('after-create', table)


def create_table(metadata):
    "Table factory."
    tbl = Table('chemical_structure', metadata,
                Column('chemical_structure_id', Integer, primary_key=True),
                Column('structure_type', String, nullable=False,
                       key='structure_type_id'),
                Column('representation', String, nullable=False),
                )
    _setup_postgres_ddl(tbl)
    return tbl
