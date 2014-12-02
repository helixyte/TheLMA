"""
Stock rack mapper
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import mapper
from thelma.entities.iso import STOCK_RACK_TYPES
from thelma.entities.iso import StockRack
from thelma.entities.liquidtransfer import WorklistSeries
from thelma.entities.rack import Rack
from thelma.entities.racklayout import RackLayout


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
                                      uselist=False, cascade='all,delete'),
                    rack_layout=relationship(RackLayout, uselist=False,
                                      cascade='all,delete,delete-orphan',
                                      single_parent=True),
                               )
               )
    return m
