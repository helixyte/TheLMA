"""
ISO stock rack table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import Table


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, stock_rack_tbl, iso_tbl):
    "Table factory."
    tbl = Table('iso_stock_rack', metadata,
                Column('stock_rack_id', Integer,
                       ForeignKey(stock_rack_tbl.c.stock_rack_id,
                                  onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False),
                Column('iso_id', Integer,
                       ForeignKey(iso_tbl.c.iso_id,
                                  onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False),
                )

    PrimaryKeyConstraint(tbl.c.stock_rack_id)
    return tbl
