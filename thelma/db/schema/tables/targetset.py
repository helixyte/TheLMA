"""
Target set table.
"""
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata):
    "Table factory."
    tbl = Table('target_set', metadata,
                Column('target_set_id', Integer, primary_key=True),
                Column('label', String, nullable=False)
                )
    return tbl
