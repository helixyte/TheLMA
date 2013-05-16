"""
ISO control stock rack table
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, iso_job_tbl, rack_layout_tbl, rack_tbl,
                 planned_worklist_tbl):
    "Table factory."
    tbl = Table('iso_control_stock_rack', metadata,
                Column('iso_control_stock_rack_id', Integer, primary_key=True),
                Column('rack_id', Integer, ForeignKey(rack_tbl.c.rack_id),
                       nullable=False),
                Column('rack_layout_id', Integer,
                       ForeignKey(rack_layout_tbl.c.rack_layout_id),
                       nullable=False),
                Column('job_id', Integer,
                       ForeignKey(iso_job_tbl.c.job_id),
                       nullable=False),
                Column('planned_worklist_id', Integer,
                       ForeignKey(planned_worklist_tbl.c.planned_worklist_id),
                       nullable=False)
                )
    return tbl
