"""
tube transfer table

AAB
"""

from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table


__docformat__ = 'reStructuredText en'

__all__ = ['create_table']


def create_table(metadata, container_tbl, rack_tbl, rack_position_tbl):
    """
    Tube transfer table factory method
    """

    tbl = Table('tube_transfer', metadata,
                Column('tube_transfer_id', Integer, primary_key=True),
                Column('tube_id', Integer,
                       ForeignKey(container_tbl.c.container_id),
                       nullable=False),
                Column('source_rack_id', Integer,
                       ForeignKey(rack_tbl.c.rack_id), nullable=False),
                Column('source_position_id', Integer,
                       ForeignKey(rack_position_tbl.c.rack_position_id),
                       nullable=False),
                Column('target_rack_id', Integer,
                       ForeignKey(rack_tbl.c.rack_id), nullable=False),
                Column('target_position_id', Integer,
                       ForeignKey(rack_position_tbl.c.rack_position_id),
                       nullable=False)
                )

    return tbl
