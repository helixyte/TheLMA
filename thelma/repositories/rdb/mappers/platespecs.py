"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Plate specs mapper.
"""
from sqlalchemy.orm import mapper, relationship

from thelma.entities.container import WellSpecs
from thelma.entities.rack import PlateSpecs
from thelma.entities.rack import RACK_SPECS_TYPES


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(rackspecs_mapper, rack_specs_container_specs_tbl):
    "Mapper factory."
    rscs = rack_specs_container_specs_tbl
    m = mapper(PlateSpecs, inherits=rackspecs_mapper,
        properties=dict(
            well_specs=relationship(WellSpecs, uselist=False, secondary=rscs,
                                    back_populates='plate_specs')
        ),
        polymorphic_identity=RACK_SPECS_TYPES.PLATE_SPECS
        )
    return m
