"""
tube transfer worklist table

AAB
"""

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table


__docformat__ = 'reStructuredText en'

__all__ = ['create_table']


def create_table(metadata, user_tbl):
    """
    Tube transfer worklist table factory method
    """

    tbl = Table('tube_transfer_worklist', metadata,
                Column('tube_transfer_worklist_id', Integer, primary_key=True),
                Column('db_user_id', Integer, ForeignKey(user_tbl.c.db_user_id),
                       nullable=False),
                Column('timestamp', DateTime(timezone=True), nullable=False),
                )

    return tbl
