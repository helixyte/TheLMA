"""
Tagged mapper.
"""
from sqlalchemy import String
from sqlalchemy import cast
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.models.tagging import Tag
from thelma.models.tagging import Tagged
from thelma.models.tagging import Tagging

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']

TAGGED_TYPE = 'TAGGED'


def create_mapper(tagged_tbl, tagging_tbl):
    "Mapper factory."
    m = mapper(Tagged, tagged_tbl,
               properties=dict(id=synonym('tagged_id'),
                               tags=relationship(Tag,
                                         secondary=tagging_tbl,
                                         viewonly=True,
                                         collection_class=set),
                               taggings=relationship(Tagging,
                                         back_populates='tagged',
                                         cascade='all,delete,delete-orphan'),
                               ),
               polymorphic_on=tagged_tbl.c.type,
               polymorphic_identity=TAGGED_TYPE,
               )
    if isinstance(Tagged.slug, property):
        Tagged.slug = \
            hybrid_property(Tagged.slug.fget,
                            expr=lambda cls: cast(cls.tagged_id, String))
    return m
