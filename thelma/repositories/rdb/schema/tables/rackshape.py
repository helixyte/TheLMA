"""
Rack shape table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import UniqueConstraint


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata):
    "Table factory."
    tbl = Table('rack_shape', metadata,
        Column('rack_shape_name', String, primary_key=True),
        Column('number_rows', Integer, CheckConstraint('number_rows>0'),
               nullable=False),
        Column('number_columns', Integer,
               CheckConstraint('number_columns>0'), nullable=False),
        Column('label', String, nullable=False, unique=True),
        UniqueConstraint('number_rows', 'number_columns'),
        )
    return tbl
