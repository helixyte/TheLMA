"""
User table.
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
    tbl = Table('db_user', metadata,
        Column('db_user_id', Integer, primary_key=True),
        Column('username', String,
               CheckConstraint('length(username)>0'), unique=True),
        Column('directory_user_id', String,
               CheckConstraint('length(directory_user_id)>0'), unique=True),
        )
    return tbl
