"""
Tube specs mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship

from thelma.entities.container import CONTAINER_SPECS_TYPES
from thelma.entities.container import TubeSpecs
from thelma.entities.rack import TubeRackSpecs


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(containerspecs_mapper, rack_specs_container_specs_tbl):
    "Mapper factory."
    rscs = rack_specs_container_specs_tbl
    m = mapper(TubeSpecs, inherits=containerspecs_mapper,
        properties=dict(
            tube_rack_specs=relationship(TubeRackSpecs, secondary=rscs,
                                         back_populates='tube_specs')
            ),
        polymorphic_identity=CONTAINER_SPECS_TYPES.TUBE
        )
    return m
