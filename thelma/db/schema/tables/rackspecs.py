"""
Rack specs table.
"""
from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import SmallInteger
from sqlalchemy import String
from sqlalchemy import Table

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, organization_tbl, rack_shape_tbl):
    "Table factory."
    tbl = Table('rack_specs', metadata,
        Column('rack_specs_id', Integer, primary_key=True),
        Column('name', String(32), CheckConstraint('length(name)>0'),
               nullable=False, unique=True),
        Column('label', String(128), CheckConstraint('length(label)>0'),
               nullable=False, unique=True),
        Column('number_rows', SmallInteger,
               CheckConstraint('number_rows>0'), nullable=False),
        Column('number_columns', SmallInteger,
               CheckConstraint('number_columns>0'), nullable=False),
        Column('has_movable_subitems', Boolean, nullable=False),
        Column('manufacturer_id', Integer,
               ForeignKey(organization_tbl.c.organization_id)),
        Column('rack_shape_name', String,
               ForeignKey(rack_shape_tbl.c.rack_shape_name)),
        )
    return tbl
