"""
Tagged mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import mapper
from thelma.entities.tagging import Tag
from thelma.entities.tagging import Tagged
from thelma.entities.tagging import Tagging


__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


TAGGED_TYPE = 'TAGGED'


def create_mapper(tagged_tbl, tagging_tbl):
    "Mapper factory."
    m = mapper(Tagged, tagged_tbl,
               id_attribute='tagged_id',
               properties=dict(tags=relationship(Tag,
                                         secondary=tagging_tbl,
                                         viewonly=True,
                                         collection_class=set,
#                                         lazy='joined'
                                         ),
                               taggings=relationship(Tagging,
                                         back_populates='tagged',
                                         cascade='all,delete,delete-orphan'),
                               ),
               polymorphic_on=tagged_tbl.c.type,
               polymorphic_identity=TAGGED_TYPE,
               )
    return m
