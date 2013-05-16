"""
Tube rack specs mapper.
"""
from sqlalchemy.orm import mapper, relationship
from thelma.models.container import TubeSpecs
from thelma.models.rack import RACK_SPECS_TYPES
from thelma.models.rack import TubeRackSpecs

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
