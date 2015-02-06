"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

User preferences table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table


__docformat__ = "epytext"
__all__ = ['create_table']


def create_table(metadata, user_tbl):
    "Table factory."
    tbl = Table('user_preferences', metadata,
                Column('user_preferences_id', Integer, primary_key=True),
                Column('user_id', Integer,
                       ForeignKey(user_tbl.c.db_user_id,
                                  onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False),
                Column('app_name', String,
                       CheckConstraint('length(app_name)>0'),
                       nullable=False),
                Column('preferences', String,
                       CheckConstraint('length(preferences)>0'),
                       nullable=False
                       ),
                )
    return tbl
