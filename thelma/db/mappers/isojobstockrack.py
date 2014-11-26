"""
ISO job stock rack mapper
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.entities.iso import IsoJobStockRack
from thelma.entities.iso import STOCK_RACK_TYPES
from thelma.entities.job import IsoJob

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(stock_rack_mapper, iso_job_stock_rack_tbl):
    "Mapper factory."
    m = mapper(IsoJobStockRack, iso_job_stock_rack_tbl,
               inherits=stock_rack_mapper,
               properties=dict(
                    iso_job=relationship(IsoJob, uselist=False,
                        back_populates='iso_job_stock_racks'),
                    ),
               polymorphic_identity=STOCK_RACK_TYPES.ISO_JOB,
               )
    return m
