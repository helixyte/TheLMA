"""
Planned container transfer table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, planned_transfer_tbl, rack_position_tbl):
    "Table factory."
    tbl = Table('planned_container_transfer', metadata,
                Column('planned_transfer_id', Integer,
                       ForeignKey(planned_transfer_tbl.c.planned_transfer_id),
                       nullable=False, primary_key=True),
                Column('source_position_id', Integer,
                       ForeignKey(rack_position_tbl.c.rack_position_id),
                       nullable=False),
                Column('target_position_id', Integer,
                       ForeignKey(rack_position_tbl.c.rack_position_id),
                       nullable=False)
                )
    return tbl
