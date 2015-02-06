"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

ISO job mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import mapper
from thelma.entities.iso import Iso
from thelma.entities.iso import IsoJobPreparationPlate
from thelma.entities.iso import IsoJobStockRack
from thelma.entities.job import IsoJob
from thelma.entities.job import JOB_TYPES
from thelma.entities.liquidtransfer import WorklistSeries


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(job_mapper, iso_job_tbl, iso_job_member_tbl,
                  worklist_series_iso_request_tbl):
    "Mapper factory."
    m = mapper(IsoJob, iso_job_tbl,
               inherits=job_mapper,
               polymorphic_identity=JOB_TYPES.ISO,
               properties=dict(
                    iso_job_stock_racks=relationship(IsoJobStockRack,
                                    back_populates='iso_job',
                                    cascade='all, delete-orphan'),
                    iso_job_preparation_plates=relationship(
                                    IsoJobPreparationPlate,
                                    back_populates='iso_job',
                                    cascade='all, delete-orphan'),
                    isos=relationship(Iso, secondary=iso_job_member_tbl,
                                    back_populates='iso_job',
                                    cascade='all, delete-orphan',
                                    single_parent=True),
                    worklist_series=relationship(WorklistSeries,
                                    cascade='all, delete-orphan',
                                    uselist=False, single_parent=True,
                                    secondary=worklist_series_iso_request_tbl)
                    )
               )
    return m
