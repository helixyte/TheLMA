"""
ISO job stock rack mapper
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.iso import IsoJobStockRack
from thelma.models.iso import STOCK_RACK_TYPES
from thelma.models.job import IsoJob

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(stock_rack_mapper, iso_job_stock_rack_tbl):
    "Mapper factory."
    m = mapper(IsoJobStockRack, iso_job_stock_rack_tbl,
               inherits=stock_rack_mapper,
               properties=dict(
                    iso_job=relationship(IsoJob, uselist=False,
                        back_populates='iso_job_stock_rack'),
                    ),
               polymorphic_identity=STOCK_RACK_TYPES.ISO_JOB,
               )
    return m
