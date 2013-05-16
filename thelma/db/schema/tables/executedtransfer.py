"""
Executed transfer table.
"""
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, planned_transfer_tbl, user_tbl):
    "Table function."
    tbl = Table('executed_transfer', metadata,
                Column('executed_transfer_id', Integer, primary_key=True),
                Column('planned_transfer_id', Integer,
                       ForeignKey(planned_transfer_tbl.c.planned_transfer_id),
                       nullable=False),
                Column('db_user_id', Integer, ForeignKey(user_tbl.c.db_user_id),
                       nullable=False),
                Column('timestamp', DateTime(timezone=True), nullable=False),
                Column('type', String, nullable=False)
                )
    return tbl
