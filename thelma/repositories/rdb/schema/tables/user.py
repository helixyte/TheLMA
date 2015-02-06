"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

User table.
"""
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
               nullable=False, unique=True),
        Column('login', String, nullable=False, unique=True),
        Column('password', String, nullable=False),
        Column('email_addr', String, nullable=False, unique=True),
        Column('directory_user_id', String, nullable=False, unique=True),
        )
    return tbl
