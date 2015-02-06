"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Worklist series table.
"""
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Table


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata):
    "Table factory."
    tbl = Table('worklist_series', metadata,
                Column('worklist_series_id', Integer, primary_key=True),
                )
    return tbl
