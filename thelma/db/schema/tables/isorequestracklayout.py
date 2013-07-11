"""
ISO request rack layout association table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy.schema import PrimaryKeyConstraint

__docformat__ = "reStructuredText en"
__all__ = ['create_table']

def create_table(metadata, iso_request_tbl, rack_layout_tbl):
    "Table factory"
    tbl = Table('iso_request_rack_layout', metadata,
                Column('iso_request_id', Integer,
                       ForeignKey(iso_request_tbl.c.iso_request_id,
                                  ondelete='CASCADE', onupdate='CASCADE'),
                       nullable=False),
                Column('rack_layout_id', Integer,
                       ForeignKey(rack_layout_tbl.c.rack_layout_id),
                       nullable=False),
                )
    PrimaryKeyConstraint(tbl.c.iso_request_id)
    return tbl
