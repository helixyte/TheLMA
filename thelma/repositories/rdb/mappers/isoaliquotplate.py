"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

ISO aliquot plate mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import mapper
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
