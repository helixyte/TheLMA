"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Plate mapper.
"""
from sqlalchemy.orm import mapper

from thelma.entities.rack import Plate
from thelma.entities.rack import RACK_TYPES


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(rack_mapper):
    "Mapper factory."
    m = mapper(Plate, inherits=rack_mapper,
               polymorphic_identity=RACK_TYPES.PLATE)
    return m
