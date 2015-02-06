"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

ISO sector preparation plate table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import Table


__docformat__ = "reStructuredText en"
__all__ = ['create_table']

def create_table(metadata, iso_plate_tbl, rack_layout_tbl):
    "Table factory."
    tbl = Table('iso_sector_preparation_plate', metadata,
                Column('iso_plate_id', Integer,
                       ForeignKey(iso_plate_tbl.c.iso_plate_id,
                                  onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False),
                Column('rack_layout_id', Integer,
                       ForeignKey(rack_layout_tbl.c.rack_layout_id,
                                  onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False),
                Column('sector_index', Integer,
                       CheckConstraint('sector_index>=0'),
                       nullable=False)
                )
    PrimaryKeyConstraint(tbl.c.iso_plate_id)
    return tbl
