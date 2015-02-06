"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Sample table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table

from thelma.entities.sample import SAMPLE_TYPES


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, container_tbl):
    "Table factory."
    tbl = Table('sample', metadata,
            Column('sample_id', Integer, primary_key=True),
            Column('sample_type', String(10), nullable=False,
                   default=SAMPLE_TYPES.BASIC),
            Column('container_id', Integer,
                   ForeignKey(container_tbl.c.container_id,
                              onupdate='CASCADE', ondelete='CASCADE'),
                   nullable=False, unique=True, index=True),
            # FIXME: if a sample has volume 0.0 then we have NO sample
            # When we re-design the database we have to discuss the business
            # rules related to the whole sample management system
            Column('volume', Float, CheckConstraint('volume>=0.0'))
            )
    return tbl
