"""
Library creation ISO table
"""

from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, iso_tbl):
    '''Table factory'''
    tbl = Table('library_creation_iso', metadata,
                Column('iso_id', Integer,
                       ForeignKey(iso_tbl.c.iso_id),
                       nullable=False, primary_key=True),
                Column('ticket_number', Integer,
                       CheckConstraint('ticket_number > 0'),
                       nullable=False),
                Column('layout_number', Integer,
                       CheckConstraint('layout_number > 0'),
                       nullable=False),
                )

    return tbl
