"""
Rack position table.
"""
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.schema import CheckConstraint
from sqlalchemy.schema import UniqueConstraint


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata):
    "Table factory."
    tbl = Table('rack_position', metadata,
                Column('rack_position_id', Integer, primary_key=True),
                Column('row_index', Integer,
                       CheckConstraint('row_index >= 0'), nullable=False),
                Column('column_index', Integer,
                       CheckConstraint('column_index >= 0'), nullable=False),
                Column('label', String(4), nullable=False, unique=True),
                )
    UniqueConstraint(tbl.c.row_index, tbl.c.column_index)
    return tbl
