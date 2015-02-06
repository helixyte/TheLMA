"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Rack position set table.
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
    tbl = Table('rack_position_set', metadata,
                Column('rack_position_set_id', Integer, primary_key=True),
                Column('hash_value', String,
                       CheckConstraint('length(hash_value)>0'),
                       nullable=False, unique=True, index=True)
                )
    return tbl
