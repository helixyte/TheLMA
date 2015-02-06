"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

ISO sample stock rack mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import mapper
from thelma.entities.iso import Iso
from thelma.entities.iso import IsoStockRack
from thelma.entities.iso import STOCK_RACK_TYPES


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
