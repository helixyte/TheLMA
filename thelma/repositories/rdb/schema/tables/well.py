"""
Container table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, container_tbl, plate_tbl, rack_position_tbl):
    "Table factory."
    tbl = Table('well', metadata,
                Column('container_id', Integer,
                       ForeignKey(container_tbl.c.container_id),
                       primary_key=True),
                Column('rack_id', Integer, ForeignKey(plate_tbl.c.rack_id),
                       nullable=False),
                Column('rack_position_id', Integer,
                       ForeignKey(rack_position_tbl.c.rack_position_id),
                       nullable=False),
                )
    return tbl
