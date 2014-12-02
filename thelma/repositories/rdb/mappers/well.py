"""
Well mapper.
"""
from sqlalchemy.orm import mapper

from thelma.entities.container import CONTAINER_TYPES
from thelma.entities.container import Well


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(container_mapper):
    "Mapper factory."
    m = mapper(Well, inherits=container_mapper,
               polymorphic_identity=CONTAINER_TYPES.WELL)
    # FIXME: need a slug here # pylint:disable=W0511
    return m
