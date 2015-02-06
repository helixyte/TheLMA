"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Well specs mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship

from thelma.entities.container import CONTAINER_SPECS_TYPES
from thelma.entities.container import WellSpecs
from thelma.entities.rack import PlateSpecs


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(containerspecs_mapper, rack_specs_container_specs_tbl):
    "Mapper factory."
    rscs = rack_specs_container_specs_tbl
    m = mapper(WellSpecs, inherits=containerspecs_mapper,
        properties=dict(
            plate_specs=relationship(PlateSpecs, uselist=False, secondary=rscs,
                                     back_populates='well_specs')
            ),
        polymorphic_identity=CONTAINER_SPECS_TYPES.WELL,
        )
    return m
