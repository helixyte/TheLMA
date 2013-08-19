"""
ISO job preparation plate mapper
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.iso import IsoJobPreparationPlate
from thelma.models.job import IsoJob
from thelma.models.rack import Rack
from thelma.models.racklayout import RackLayout

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
                        back_populates='iso_job_preparation_plate'),
                    ),
               )
    return m
