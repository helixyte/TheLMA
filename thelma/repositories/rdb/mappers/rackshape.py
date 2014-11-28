"""
Rack shape mapper.
"""
from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from everest.repositories.rdb.utils import synonym
from sqlalchemy.orm import relationship
from thelma.entities.rack import RackShape
from thelma.entities.rack import RackSpecs

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(rack_shape_tbl):
    "Mapper factory."
    m = mapper(RackShape, rack_shape_tbl,
        id_attribute='rack_shape_name',
        slug_expression=lambda cls: as_slug_expression(cls.rack_shape_name),
        properties=dict(
            specs=relationship(RackSpecs, back_populates='shape'),
            ),
        )
    RackShape.name = synonym('rack_shape_name')
    return m
