"""
Planned worklist table.
"""
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_table(metadata):
    "Table factory."
    tbl = Table('planned_worklist', metadata,
                Column('planned_worklist_id', Integer, primary_key=True),
                Column('label', String, nullable=False),
                )
    return tbl
