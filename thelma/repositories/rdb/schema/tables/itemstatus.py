"""
Item status table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Table


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata):
    "Factory function."
    tbl = Table('item_status', metadata,
            Column('item_status_id', String(9),
                   CheckConstraint('length(item_status_id)>0'),
                   primary_key=True),
            Column('name', String(18), CheckConstraint('length(name)>0'),
                   unique=True, nullable=False),
            Column('description', String, default='')
            )
    return tbl
