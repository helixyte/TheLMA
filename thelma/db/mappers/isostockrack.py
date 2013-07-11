"""
ISO sample stock rack mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.iso import Iso
from thelma.models.iso import IsoStockRack
from thelma.models.iso import STOCK_RACK_TYPES

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(stock_rack_mapper, iso_stock_rack_tbl):
    "Mapper factory."
    m = mapper(IsoStockRack, iso_stock_rack_tbl,
               inherits=stock_rack_mapper,
               properties=dict(
                    iso=relationship(Iso, uselist=False,
                        back_populates='iso_stock_racks'),
                    ),
               polymorphic_identity=STOCK_RACK_TYPES.ISO,
               )
    return m
