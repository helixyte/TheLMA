"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Rack position set mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import mapper
from thelma.entities.rack import RackPosition
from thelma.entities.rack import RackPositionSet


__docformat__ = "epytext"
__all__ = ['create_mapper']


def create_mapper(rack_position_set_tbl,
                  rack_position_set_member_tbl):
    "Mapper factory."
    m = mapper(RackPositionSet, rack_position_set_tbl,
               id_attribute='rack_position_set_id',
               slug_expression=lambda cls: cls._hash_value, # pylint: disable=W0212
               properties=
                dict(
                     _positions=
                       relationship(RackPosition, collection_class=set,
                                    secondary=rack_position_set_member_tbl),
                     _hash_value=rack_position_set_tbl.c.hash_value,
                     )
               )
    return m
