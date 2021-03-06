"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

ISO job preparation plate mapper
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import mapper
from thelma.entities.iso import IsoJobPreparationPlate
from thelma.entities.job import IsoJob
from thelma.entities.rack import Rack
from thelma.entities.racklayout import RackLayout


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(iso_job_preparation_plate_tbl):
    "Mapper factory."
    m = mapper(IsoJobPreparationPlate, iso_job_preparation_plate_tbl,
               id_attribute='iso_job_preparation_plate_id',
               properties=dict(
                    rack=relationship(Rack, uselist=False),
                    rack_layout=relationship(RackLayout, uselist=False),
                    iso_job=relationship(IsoJob, uselist=False,
                        back_populates='iso_job_preparation_plates'),
                    ),
               )
    return m
