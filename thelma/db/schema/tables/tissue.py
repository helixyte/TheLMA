"""
Species table.
"""
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import UniqueConstraint

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata):
    "Table factory."
    tbl = Table('species', metadata,
        Column('species_id', Integer, primary_key=True),
        Column('label', String(128), nullable=False, unique=True),
        )
    return tbl
