"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Executed worklist member table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy.schema import PrimaryKeyConstraint


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, executed_worklist_tbl, executed_liquid_transfer_tbl):
    "Table factory."
    tbl = Table('executed_worklist_member', metadata,
                Column('executed_worklist_id', Integer,
                       ForeignKey(executed_worklist_tbl.c.executed_worklist_id),
                       nullable=False),
                Column('executed_liquid_transfer_id', Integer,
                       ForeignKey(executed_liquid_transfer_tbl.c.\
                                  executed_liquid_transfer_id),
                       nullable=False),
                )
    PrimaryKeyConstraint(tbl.c.executed_worklist_id,
                         tbl.c.executed_liquid_transfer_id)
    return tbl
