"""
Rack position set mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.models.rack import RackPosition
from thelma.models.rack import RackPositionSet

__docformat__ = "epytext"
__all__ = ['create_mapper']


def create_mapper(rack_position_set_tbl,
                  rack_position_set_member_tbl):
    "Mapper factory."
    m = mapper(RackPositionSet, rack_position_set_tbl,
               properties=
                dict(
                     id=synonym('rack_position_set_id'),
                     _positions=
                       relationship(RackPosition, collection_class=set,
                                    secondary=rack_position_set_member_tbl),
                     _hash_value=rack_position_set_tbl.c.hash_value,
                     )
               )
    if isinstance(RackPositionSet.slug, property):
        RackPositionSet.slug = \
            hybrid_property(RackPositionSet.slug.fget,
                    expr=lambda cls: cls._hash_value) # pylint: disable=W0212
    return m
