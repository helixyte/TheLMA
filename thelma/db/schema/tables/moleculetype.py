"""
Molecule type table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Float
from sqlalchemy import String
from sqlalchemy import Table

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata):
    "Table factory."
    table = Table('molecule_type', metadata,
        Column('molecule_type_id', String(10),
               CheckConstraint('length(molecule_type_id)>0'),
               primary_key=True),
        Column('name', String(20),
               CheckConstraint('length(name)>0'),
               unique=True),
        Column('default_stock_concentration', Float,
               CheckConstraint('default_stock_concentration>0'),
               nullable=False),
        Column('description', String, default=''),
        Column('thaw_time', Integer, CheckConstraint('thaw_time>=0'),
               nullable=False, default=0),
        )
    return table
