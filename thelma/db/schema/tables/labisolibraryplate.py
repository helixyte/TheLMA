"""
ISO library plate table
"""

from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy.schema import PrimaryKeyConstraint

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']

def create_table(metadata, iso_tbl, library_plate_tbl):
    """Table factory"""
    tbl = Table('lab_iso_library_plate', metadata,
                Column('iso_id', Integer,
                       ForeignKey(iso_tbl.c.iso_id,
                                  onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False),
                Column('library_plate_id', Integer,
                       ForeignKey(library_plate_tbl.c.library_plate_id,
                                  onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False)
                )

    PrimaryKeyConstraint(tbl.c.iso_id, tbl.c.library_plate_id)
    return tbl
