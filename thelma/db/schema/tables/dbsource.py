"""
DB source table.
"""
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata):
    "Table factory."
    tbl = Table('db_source', metadata,
        Column('db_source_id', Integer, primary_key=True),
        Column('db_name', String(20), nullable=False, unique=True),
        Column('curating_organization', String(25), nullable=False),
        )
    return tbl
