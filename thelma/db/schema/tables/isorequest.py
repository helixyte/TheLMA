"""
ISO request table.
"""
from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import Text
from sqlalchemy.schema import CheckConstraint
from thelma.models.iso import ISO_TYPES

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, rack_layout_tbl, user_tbl):
    "Table factory."
    tbl = Table('iso_request', metadata,
                Column('iso_request_id', Integer,
                       primary_key=True),
                Column('rack_layout_id', Integer,
                       ForeignKey(rack_layout_tbl.c.rack_layout_id)),
                Column('requester_id', Integer,
                       ForeignKey(user_tbl.c.db_user_id),
                       nullable=False),
                Column('delivery_date', Date, nullable=False),
                Column('plate_set_label', String),
                Column('number_plates', Integer, nullable=False),
                Column('number_aliquots', Integer, nullable=False,
                       default=1),
                Column('comment', Text),
                Column('owner', String),
                Column('iso_type', String,
                       CheckConstraint(
                         'iso_type IN (\'%s\', \'%s\')'
                         % (ISO_TYPES.STANDARD, ISO_TYPES.LIBRARY_CREATION)),
                       nullable=False, default=ISO_TYPES.STANDARD)
                )
    return tbl
