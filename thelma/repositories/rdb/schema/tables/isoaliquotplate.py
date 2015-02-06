"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

ISO aliquot plate table.
"""
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import Table


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, iso_plate_tbl):
    "Table factory."
    tbl = Table('iso_aliquot_plate', metadata,
                Column('iso_plate_id', Integer,
                       ForeignKey(iso_plate_tbl.c.iso_plate_id,
                                  onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False),
                Column('has_been_used', Boolean, nullable=False),
                )

    PrimaryKeyConstraint(tbl.c.iso_plate_id)
    return tbl
