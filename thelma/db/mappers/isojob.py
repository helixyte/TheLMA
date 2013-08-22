"""
ISO job mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.iso import Iso
from thelma.models.iso import IsoJobStockRack
from thelma.models.job import IsoJob
from thelma.models.job import JOB_TYPES
from thelma.models.iso import IsoJobPreparationPlate

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(job_mapper, job_tbl, iso_job_member_tbl):
    "Mapper factory."

    m = mapper(IsoJob, job_tbl,
               inherits=job_mapper,
               polymorphic_identity=JOB_TYPES.ISO,
               properties=dict(
                    iso_job_stock_racks=relationship(IsoJobStockRack,
                                    back_populates='iso_job',
                                    cascade='all, delete-orphan'),
                    iso_job_preparation_plate=relationship(
                                    IsoJobPreparationPlate, uselist=False,
                                    back_populates='iso_job',
                                    cascade='all, delete-orphan'),
                    isos=relationship(Iso, secondary=iso_job_member_tbl,
                                    back_populates='iso_job',
                                    cascade='all, delete-orphan',
                                    single_parent=True))
               )
    return m
