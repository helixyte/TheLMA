"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Executed worklist table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, planned_worklist_tbl):
    "Table factory."
    tbl = Table('executed_worklist', metadata,
                Column('executed_worklist_id', Integer, primary_key=True),
                Column('planned_worklist_id', Integer,
                       ForeignKey(planned_worklist_tbl.c.planned_worklist_id,
                                  onupdate='RESTRICT', ondelete='RESTRICT'),
                       nullable=False)
                )
    return tbl
