"""
ISO table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table

from thelma.entities.iso import ISO_TYPES


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, iso_request_tbl, rack_layout_tbl):
    "Table factory."
    tbl = Table('iso', metadata,
                Column('iso_id', Integer, primary_key=True),
                Column('label', String, nullable=False),
                Column('status', String, nullable=False),
                Column('iso_request_id', Integer,
                       ForeignKey(iso_request_tbl.c.iso_request_id),
                       nullable=False),
                Column('rack_layout_id', Integer,
                       ForeignKey(rack_layout_tbl.c.rack_layout_id),
                       nullable=False),
                Column('iso_type', String,
                       CheckConstraint(
                         'iso_type IN (\'%s\', \'%s\', \'%s\')'
                         % (ISO_TYPES.BASE, ISO_TYPES.LAB,
                            ISO_TYPES.STOCK_SAMPLE_GENERATION)),
                         nullable=False),
                Column('number_stock_racks', Integer,
                       CheckConstraint('number_stock_racks >= 0'),
                       nullable=False),
                Column('optimizer_excluded_racks', String, nullable=True),
                Column('optimizer_requested_tubes', String, nullable=True)
                )
    return tbl
