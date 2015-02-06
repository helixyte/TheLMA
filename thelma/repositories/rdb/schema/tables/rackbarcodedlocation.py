"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Rack barcoded location table.
"""
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, rack_tbl, barcoded_location_tbl):
    "Table factory."
    tbl = Table('rack_barcoded_location', metadata,
        Column('rack_id', Integer,
               ForeignKey(rack_tbl.c.rack_id,
                          onupdate='CASCADE', ondelete='CASCADE'),
               primary_key=True),
        Column('barcoded_location_id', Integer,
               ForeignKey(barcoded_location_tbl.c.barcoded_location_id,
                          onupdate='NO ACTION', ondelete='NO ACTION'),
               nullable=False, unique=True, index=True),
        Column('checkin_date', DateTime(timezone=True), nullable=False),
        )
    return tbl
