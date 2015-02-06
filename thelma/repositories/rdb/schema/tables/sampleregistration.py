"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Sample registration table.
"""
from datetime import datetime

from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy.schema import ForeignKey


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, sample_tbl):
    "Table factory."
    tbl = Table('sample_registration', metadata,
            Column('sample_id', Integer,
                   ForeignKey(sample_tbl.c.sample_id,
                              onupdate='RESTRICT', ondelete='RESTRICT'),
                    primary_key=True),
            Column('volume', Float, CheckConstraint('volume>=0.0'),
                   nullable=False),
            Column('time_stamp', DateTime(timezone=True),
                   nullable=False, default=datetime.now),
            )
    return tbl
