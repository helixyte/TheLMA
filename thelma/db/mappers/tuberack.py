"""
Tube rack mapper.
"""
from sqlalchemy.orm import mapper
from thelma.models.rack import RACK_TYPES
from thelma.models.rack import TubeRack

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(rack_mapper):
    "Mapper factory."
    m = mapper(TubeRack, inherits=rack_mapper,
               polymorphic_identity=RACK_TYPES.TUBE_RACK)
    return m
