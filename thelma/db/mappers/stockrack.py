"""
Stock rack mapper
"""

from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.iso import STOCK_RACK_TYPES
from thelma.models.iso import StockRack
from thelma.models.liquidtransfer import WorklistSeries
from thelma.models.rack import Rack
from thelma.models.racklayout import RackLayout

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']

def create_mapper(stock_rack_tbl):
    "Mapper factory."

    m = mapper(StockRack, stock_rack_tbl,
               id_attribute='stock_rack_id',
               polymorphic_on=stock_rack_tbl.c.stock_rack_type,
               polymorphic_identity=STOCK_RACK_TYPES.STOCK_RACK,
               properties=dict(
                    rack=relationship(Rack, uselist=False),
                    worklist_series=relationship(WorklistSeries,
                                      uselist=False, single_parent=True,
                                      cascade='all,delete,delete-orphan'),
                    rack_layout=relationship(RackLayout, uselist=False,
                                      cascade='all,delete,delete-orphan',
                                      single_parent=True),
                               )
               )
    return m
