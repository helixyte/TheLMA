"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Planned sample transfer table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, planned_liquid_transfer_tbl, rack_position_tbl):
    "Table factory."
    tbl = Table('planned_sample_transfer', metadata,
                Column('planned_liquid_transfer_id', Integer,
                       ForeignKey(planned_liquid_transfer_tbl.c.\
                                  planned_liquid_transfer_id,
                                  onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False, primary_key=True),
                Column('source_position_id', Integer,
                       ForeignKey(rack_position_tbl.c.rack_position_id,
                                  onupdate='CASCADE'),
                       nullable=False),
                Column('target_position_id', Integer,
                       ForeignKey(rack_position_tbl.c.rack_position_id,
                                  onupdate='CASCADE'),
                       nullable=False)
                )
    return tbl
