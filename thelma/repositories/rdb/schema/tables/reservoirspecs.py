"""
Reservoir specs table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, rack_shape_tbl):
    "Table factory."
    tbl = Table('reservoir_specs', metadata,
                Column('reservoir_specs_id', Integer, primary_key=True),
                Column('name', String, nullable=False),
                Column('description', String, nullable=False),
                Column('rack_shape_name', String,
                       ForeignKey(rack_shape_tbl.c.rack_shape_name),
                       nullable=False),
                Column('max_volume', Float,
                       CheckConstraint('max_volume>0'), nullable=False),
                Column('min_dead_volume', Float,
                       CheckConstraint('min_dead_volume>0'), nullable=False),
                Column('max_dead_volume', Float,
                       CheckConstraint('max_dead_volume>0'), nullable=False)
                )
    return tbl
