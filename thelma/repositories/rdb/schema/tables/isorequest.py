"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

ISO request table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table

from thelma.entities.iso import ISO_TYPES


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata):
    "Table factory."
    tbl = Table('iso_request', metadata,
                Column('iso_request_id', Integer,
                       primary_key=True),

                Column('label', String, nullable=False),
                Column('expected_number_isos', Integer,
                       CheckConstraint('expected_number_isos > 0'),
                       nullable=False),
                Column('number_aliquots', Integer,
                       CheckConstraint('number_aliquots >= 0'),
                       nullable=False),

                Column('owner', String, nullable=False),
                Column('iso_type', String,
                       CheckConstraint(
                         'iso_type IN (\'%s\', \'%s\', \'%s\')'
                         % (ISO_TYPES.BASE, ISO_TYPES.LAB,
                            ISO_TYPES.STOCK_SAMPLE_GENERATION)),
                       nullable=False)
                )
    return tbl
