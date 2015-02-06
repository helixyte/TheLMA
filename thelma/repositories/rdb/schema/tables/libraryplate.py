"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Library plate table.
"""
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy.schema import CheckConstraint


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, molecule_design_library_tbl, rack_tbl):
    "Table factory."
    tbl = Table('library_plate', metadata,
                Column('library_plate_id', Integer, primary_key=True),
                Column('molecule_design_library_id', Integer,
                       ForeignKey(molecule_design_library_tbl.c.\
                                  molecule_design_library_id,
                                  onupdate='CASCADE', ondelete='RESTRICT'),
                       nullable=False),
                Column('rack_id', Integer,
                       ForeignKey(rack_tbl.c.rack_id,
                                  onupdate='CASCADE', ondelete='RESTRICT'),
                       nullable=False),
                Column('layout_number', Integer, nullable=False),
                Column('has_been_used', Boolean, nullable=False),
                CheckConstraint('layout_number > 0'))
    return tbl
