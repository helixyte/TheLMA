"""
Rack layout mapper.
"""
from sqlalchemy import String
from sqlalchemy import cast
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.models.rack import RackShape
from thelma.models.racklayout import RackLayout
from thelma.models.tagging import TaggedRackPositionSet

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(rack_layout_tbl):
    "Mapper factory."
    rl = rack_layout_tbl
    m = mapper(RackLayout, rl,
               properties=
                dict(id=synonym("rack_layout_id"),
                     shape=relationship(RackShape,
                                        uselist=False),
                     tagged_rack_position_sets=
                       relationship(TaggedRackPositionSet,
                                    back_populates='layout',
                                    cascade='all,delete,delete-orphan'),
                     ),
               )
    if isinstance(RackLayout.slug, property):
        RackLayout.slug = \
            hybrid_property(RackLayout.slug.fget,
                            expr=lambda cls: cast(cls.rack_layout_id, String))
    return m
