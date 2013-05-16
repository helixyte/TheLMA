"""
ISO sample stock rack table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, iso_tbl, rack_tbl, planned_worklist_tbl):
    "Table factory."
    tbl = Table('iso_sample_stock_rack', metadata,
                Column('iso_sample_stock_rack_id', Integer, primary_key=True),
                Column('rack_id', Integer, ForeignKey(rack_tbl.c.rack_id),
                       nullable=False),
                Column('iso_id', Integer,
                       ForeignKey(iso_tbl.c.iso_id,
                                  onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False),
                Column('sector_index', Integer,
                       CheckConstraint('sector_index>=0'),
                       nullable=False),
                Column('planned_worklist_id', Integer,
                       ForeignKey(planned_worklist_tbl.c.planned_worklist_id),
                       nullable=False)
                )
    return tbl
