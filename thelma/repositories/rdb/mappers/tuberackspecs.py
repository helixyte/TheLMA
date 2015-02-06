"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Tube rack specs mapper.
"""
from sqlalchemy.orm import mapper, relationship

from thelma.entities.container import TubeSpecs
from thelma.entities.rack import RACK_SPECS_TYPES
from thelma.entities.rack import TubeRackSpecs


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(rackspecs_mapper, rack_specs_container_specs_tbl):
    "Mapper factory."
    rscs = rack_specs_container_specs_tbl
    m = mapper(TubeRackSpecs, inherits=rackspecs_mapper,
        properties=dict(
            tube_specs=relationship(TubeSpecs, secondary=rscs,
                                    back_populates='tube_rack_specs')
            ),
        polymorphic_identity=RACK_SPECS_TYPES.TUBE_RACK_SPECS,
        )
    return m
