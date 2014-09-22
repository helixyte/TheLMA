"""
Rack layout table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, rack_shape_tbl):
    "Table factory."
    tbl = Table('rack_layout', metadata,
                Column('rack_layout_id', Integer, primary_key=True),
                Column('rack_shape_name', String,
                       ForeignKey(rack_shape_tbl.c.rack_shape_name),
                       nullable=False),
                )
    return tbl
