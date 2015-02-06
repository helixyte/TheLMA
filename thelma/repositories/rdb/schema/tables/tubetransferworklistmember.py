"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Tube transfer worklist member table."""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy.schema import PrimaryKeyConstraint


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, tube_transfer_tbl, tube_transfer_worklist_tbl):
    "Table factory."
    tbl = Table('tube_transfer_worklist_member', metadata,
                Column('tube_transfer_worklist_id', Integer,
                       ForeignKey(tube_transfer_worklist_tbl.c.\
                                  tube_transfer_worklist_id),
                       nullable=False),
                Column('tube_transfer_id', Integer,
                       ForeignKey(tube_transfer_tbl.c.tube_transfer_id),
                       nullable=False),
                )
    PrimaryKeyConstraint(tbl.c.tube_transfer_worklist_id,
                         tbl.c.tube_transfer_id)
    return tbl
