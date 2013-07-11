"""
ISO plate table
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy import String
from thelma.models.iso import ISO_PLATE_TYPES

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, iso_tbl, rack_tbl):
    "Table factory."
    tbl = Table('iso_plate', metadata,
                Column('iso_plate_id', Integer, primary_key=True),
                Column('rack_id', Integer,
                       ForeignKey(rack_tbl.c.rack_id,
                                  ondelete='CASCADE', onupdate='CASCADE'),
                       nullable=False),
                Column('iso_id', Integer,
                       ForeignKey(iso_tbl.c.iso_id,
                                  ondelete='CASCADE', onupdate='CASCADE'),
                       nullable=False),
                Column('iso_plate_type', String(14),
                       CheckConstraint('iso_plate_type IN ' \
                           '(\'%s\', \'%s\', \'%s\', \'%s\')' %
                           (ISO_PLATE_TYPES.ISO_PLATE, ISO_PLATE_TYPES.ALIQUOT,
                            ISO_PLATE_TYPES.PREPARATION,
                            ISO_PLATE_TYPES.SECTOR_PREPARATION)),
                       nullable=False)
                )

    return tbl
