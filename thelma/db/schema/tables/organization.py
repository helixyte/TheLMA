"""
Organization table.
"""
from sqlalchemy import Table
from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import CheckConstraint

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata):
    "Table factory."
    tbl = Table('organization', metadata,
        Column('organization_id', Integer, primary_key=True),
        Column('name', String, CheckConstraint('length(name)>0'), unique=True),
        )
    return tbl
