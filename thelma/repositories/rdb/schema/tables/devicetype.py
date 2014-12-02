"""
Device type table.
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
        ALTER TABLE %(table)s ALTER COLUMN "name" SET DATA TYPE name
        """,
        on='postgres'
        ).execute_at('after-create', table)


def create_table(metadata):
    "Table factory."
    tbl = Table('device_type', metadata,
        Column('device_type_id', Integer, primary_key=True),
        Column('name', String, nullable=False, unique=True),
        Column('label', String, nullable=False, unique=True),
        )
    _setup_postgres_ddl(tbl)
    return tbl
