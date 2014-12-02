"""
Rack layout mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import mapper
from thelma.entities.rack import RackShape
from thelma.entities.racklayout import RackLayout
from thelma.entities.tagging import TaggedRackPositionSet


__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(rack_layout_tbl):
    "Mapper factory."
    rl = rack_layout_tbl
    m = mapper(RackLayout, rl,
               id_attribute='rack_layout_id',
               properties=
                dict(shape=relationship(RackShape,
                                        uselist=False),
                     tagged_rack_position_sets=
                       relationship(TaggedRackPositionSet,
                                    lazy='joined',
                                    back_populates='layout',
                                    cascade='all,delete,delete-orphan'),
                     ),
               )
    return m
