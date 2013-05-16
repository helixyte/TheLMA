"""
Planned rack transfer table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, planned_transfer_tbl):
    "Table factory."
    tbl = Table('planned_rack_transfer', metadata,
                Column('planned_transfer_id', Integer,
                       ForeignKey(planned_transfer_tbl.c.planned_transfer_id),
                       nullable=False, primary_key=True),
                Column('source_sector_index', Integer,
                       CheckConstraint('source_sector_index>=0'),
                       nullable=False),
                Column('target_sector_index', Integer,
                       CheckConstraint('target_sector_index>=0'),
                       nullable=False),
                Column('sector_number', Integer,
                       CheckConstraint('sector_number > 0'),
                       nullable=False)
                )
    return tbl
