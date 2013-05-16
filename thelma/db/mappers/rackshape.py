"""
Rack shape mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.rack import RackShape
from thelma.models.rack import RackSpecs

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(rack_shape_tbl):
    "Mapper factory."
    m = mapper(RackShape, rack_shape_tbl,
        properties=dict(
            name=synonym('rack_shape_name'),
            id=synonym('rack_shape_name'),
            specs=relationship(RackSpecs, back_populates='shape'),
            ),
        )
    if isinstance(RackShape.slug, property):
        RackShape.slug = \
            hybrid_property(RackShape.slug.fget,
                            expr=lambda cls:
                                as_slug_expression(cls.rack_shape_name))
    return m
