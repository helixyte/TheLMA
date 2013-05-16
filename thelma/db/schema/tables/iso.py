"""
ISO table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.schema import CheckConstraint
from thelma.models.iso import ISO_TYPES

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
                Column('optimizer_excluded_racks', String, nullable=True),
                Column('optimizer_required_racks', String, nullable=True),
                Column('rack_layout_id', Integer,
                       ForeignKey(rack_layout_tbl.c.rack_layout_id),
                       nullable=False),
                Column('iso_type', String,
                       CheckConstraint(
                         'iso_type IN (\'%s\', \'%s\')'
                         % (ISO_TYPES.STANDARD, ISO_TYPES.LIBRARY_CREATION)),
                         nullable=False, default=ISO_TYPES.STANDARD)
                )
    return tbl
