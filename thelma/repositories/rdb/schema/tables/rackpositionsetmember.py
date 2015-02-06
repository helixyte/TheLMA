"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Rack position set member table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, rack_position_set_tbl, rack_position_tbl):
    "Table factory."
    tbl = Table('rack_position_set_member', metadata,
                Column('rack_position_set_id', Integer,
                       ForeignKey(rack_position_set_tbl.c.rack_position_set_id),
                       nullable=False,
                       ),
                Column('rack_position_id', Integer,
                       ForeignKey(rack_position_tbl.c.rack_position_id),
                       nullable=False),
                )
    return tbl
