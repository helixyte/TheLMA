"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Plate mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship

from thelma.entities.container import Well
from thelma.entities.rack import Plate
from thelma.entities.rack import RACK_TYPES


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(rack_mapper, plate_tbl):
    "Mapper factory."
    m = mapper(Plate, plate_tbl,
               inherits=rack_mapper,
               properties=dict(containers=
                                relationship(Well,
                                             back_populates='rack')
                               ),
               polymorphic_identity=RACK_TYPES.PLATE)
    return m
