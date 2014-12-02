"""
Tagged table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table


__docformat__ = "reStructuredText en"
__all__ = ['create_table']

def create_table(metadata):
    "Table factory."
    tbl = Table('tagged', metadata,
                Column('tagged_id', Integer, primary_key=True),
                Column('type', String, CheckConstraint('length(type)>0'),
                       nullable=False),
                )
    return tbl
