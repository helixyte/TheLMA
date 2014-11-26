"""
ISO aliquot plate mapper
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.entities.iso import ISO_PLATE_TYPES
from thelma.entities.iso import Iso
from thelma.entities.iso import IsoAliquotPlate

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(iso_plate_mapper, iso_aliquot_plate_tbl):
    "Mapper factory."
    m = mapper(IsoAliquotPlate, iso_aliquot_plate_tbl,
               inherits=iso_plate_mapper,
               properties=dict(
                    iso=relationship(Iso, uselist=False,
                                     back_populates='iso_aliquot_plates'),
                    ),
               polymorphic_identity=ISO_PLATE_TYPES.ALIQUOT,
               )
    return m
