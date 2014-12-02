"""
Worklist series member table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import Table


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, worklist_series_tbl, planned_worklist_tbl):
    "Table factory."
    tbl = Table('worklist_series_member', metadata,
                Column('worklist_series_id', Integer,
                       ForeignKey(worklist_series_tbl.c.worklist_series_id,
                                  onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False),
                Column('planned_worklist_id', Integer,
                       ForeignKey(planned_worklist_tbl.c.planned_worklist_id),
                       nullable=False, unique=True),
                Column('index', Integer, CheckConstraint('index>=0'),
                       nullable=False)
                )
    PrimaryKeyConstraint(tbl.c.worklist_series_id, tbl.c.planned_worklist_id)
    return tbl
