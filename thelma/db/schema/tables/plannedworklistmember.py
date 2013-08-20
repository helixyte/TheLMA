"""
Planned worklist member table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy.schema import PrimaryKeyConstraint

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, planned_worklist_tbl, planned_transfer_tbl):
    "Table factory."
    tbl = Table('planned_worklist_member', metadata,
                Column('planned_worklist_id', Integer,
                       ForeignKey(planned_worklist_tbl.c.planned_worklist_id),
                       nullable=False),
                Column('planned_transfer_id', Integer,
                       ForeignKey(planned_transfer_tbl.c.planned_transfer_id),
                       nullable=False),
                )
    PrimaryKeyConstraint(tbl.c.planned_worklist_id, tbl.c.planned_transfer_id)
    return tbl
