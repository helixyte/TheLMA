"""
Rack specs mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import column_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from sqlalchemy.sql import case
from sqlalchemy.sql import literal
from sqlalchemy.sql import select
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.organization import Organization
from thelma.models.rack import RACK_SPECS_TYPES
from thelma.models.rack import RackShape
from thelma.models.rack import RackSpecs

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(rack_specs_tbl):
    "Mapper factory."
    rs = rack_specs_tbl
    polymorphic_select = select([
        rs,
        (case([(rs.c.has_movable_subitems,
                literal(RACK_SPECS_TYPES.TUBE_RACK_SPECS))],
              else_=literal(RACK_SPECS_TYPES.PLATE_SPECS))).label(
                                                            'rackspecs_type')
        ],
        ).alias('rackspecs')
    m = mapper(RackSpecs, polymorphic_select,
        properties=dict(
            id=synonym('rack_specs_id'),
            has_tubes=synonym('has_movable_subitems'),
            manufacturer=relationship(Organization),
            shape=relationship(RackShape, uselist=False,
                               back_populates='specs'),
            rack_specs_type=
                    column_property(polymorphic_select.c.rackspecs_type),
            ),
        polymorphic_on=polymorphic_select.c.rackspecs_type,
        polymorphic_identity=RACK_SPECS_TYPES.RACK_SPECS,
        )
    if isinstance(RackSpecs.slug, property):
        RackSpecs.slug = hybrid_property(RackSpecs.slug.fget,
                                         expr=lambda cls:
                                                as_slug_expression(cls.name))
    return m
