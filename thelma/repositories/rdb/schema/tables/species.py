"""
Species table.
"""
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import SmallInteger
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import UniqueConstraint


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata):
    "Table factory."
    tbl = Table('species', metadata,
        Column('species_id', Integer, primary_key=True),
        Column('genus_name', String(25), nullable=False),
        Column('species_name', String(25), nullable=False),
        Column('common_name', String(25), nullable=False, unique=True),
        Column('acronym', String(2), nullable=False, unique=True),
        Column('ncbi_tax_id', SmallInteger, nullable=False),
        )
    UniqueConstraint(tbl.c.genus_name, tbl.c.species_name)
    return tbl
