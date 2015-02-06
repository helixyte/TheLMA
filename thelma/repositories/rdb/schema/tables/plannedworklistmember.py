"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Planned worklist member table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy.schema import PrimaryKeyConstraint


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, planned_worklist_tbl, planned_liquid_transfer_tbl):
    "Table factory."
    tbl = Table('planned_worklist_member', metadata,
                Column('planned_worklist_id', Integer,
                       ForeignKey(planned_worklist_tbl.c.planned_worklist_id,
                                  onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False),
                Column('planned_liquid_transfer_id', Integer,
                       ForeignKey(planned_liquid_transfer_tbl.c.\
                                  planned_liquid_transfer_id,
                                  onupdate='CASCADE'),
                       nullable=False),
                )
    PrimaryKeyConstraint(tbl.c.planned_worklist_id,
                         tbl.c.planned_liquid_transfer_id)
    return tbl
