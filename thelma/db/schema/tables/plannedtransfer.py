"""
Planned transfer table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata):
    "Table factory."
    tbl = Table('planned_transfer', metadata,
                Column('planned_transfer_id', Integer, primary_key=True),
                Column('volume', Float, CheckConstraint('volume>0'),
                       nullable=False),
                Column('type', String, nullable=False)
                )
    return tbl
