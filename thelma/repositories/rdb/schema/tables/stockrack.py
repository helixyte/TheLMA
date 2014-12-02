"""
Stock rack table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table

from thelma.entities.iso import STOCK_RACK_TYPES


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, rack_tbl, rack_layout_tbl, worklist_series_tbl):
    "Table factory."
    tbl = Table('stock_rack', metadata,
                Column('stock_rack_id', Integer, primary_key=True),
                Column('label', String(20), nullable=False),
                Column('rack_id', Integer, ForeignKey(rack_tbl.c.rack_id),
                       nullable=False),
                Column('rack_layout_id', Integer,
                       ForeignKey(rack_layout_tbl.c.rack_layout_id,
                                  onupdate='CASCADE', ondelete='CASCADE')),
                Column('worklist_series_id', Integer,
                       ForeignKey(worklist_series_tbl.c.worklist_series_id,
                                  onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False),
                Column('stock_rack_type', String(10),
                       CheckConstraint('stock_rack_type IN ' \
                         '(\'%s\', \'%s\', \'%s\', \'%s\')' %
                          (STOCK_RACK_TYPES.STOCK_RACK, STOCK_RACK_TYPES.ISO,
                           STOCK_RACK_TYPES.ISO_JOB, STOCK_RACK_TYPES.SECTOR)),
                       nullable=False)
                )
    return tbl
