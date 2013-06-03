"""
ISO preparation plate mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.iso import Iso
from thelma.models.iso import IsoPreparationPlate
from thelma.models.rack import Rack

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(iso_preparation_plate_tbl):
    "Mapper factory."
    m = mapper(IsoPreparationPlate, iso_preparation_plate_tbl,
               id_attribute='iso_preparation_plate_id',
               properties=dict(
                    plate=relationship(Rack, uselist=False),
                    iso=relationship(Iso, uselist=False,
                        back_populates='iso_preparation_plate'),
                    )
               )
    return m
