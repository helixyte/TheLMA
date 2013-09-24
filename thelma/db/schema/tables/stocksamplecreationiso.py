"""
Stock sample creation ISO table
"""

from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, iso_tbl):
    '''Table factory'''
    tbl = Table('stock_sample_creation_iso', metadata,
                Column('iso_id', Integer,
                       ForeignKey(iso_tbl.c.iso_id,
                                  ondelete='CASCADE', onupdate='CASCADE'),
                       nullable=False),
                Column('ticket_number', Integer,
                       CheckConstraint('ticket_number > 0'),
                       nullable=False),
                Column('layout_number', Integer,
                       CheckConstraint('layout_number > 0'),
                       nullable=False),
                )

    PrimaryKeyConstraint(tbl.c.iso_id)

    return tbl
