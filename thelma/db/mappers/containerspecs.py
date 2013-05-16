"""
Container specs mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from sqlalchemy.sql import case
from sqlalchemy.sql import literal
from sqlalchemy.sql import select
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.container import CONTAINER_SPECS_TYPES
from thelma.models.container import ContainerSpecs
from thelma.models.organization import Organization

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(container_specs_tbl):
    "Mapper factory."
    cs = container_specs_tbl.alias('cs')
    polymorphic_select = select([
        cs,
        (case([(cs.c.has_barcode, literal(CONTAINER_SPECS_TYPES.TUBE))],
              else_=literal(CONTAINER_SPECS_TYPES.WELL))).label(
                                                        'containerspecs_type')
        ],
        ).alias('containerspecs')
    m = mapper(ContainerSpecs, polymorphic_select,
        properties=dict(
            id=synonym('container_specs_id'),
            manufacturer=relationship(Organization),
            ),
        polymorphic_on=polymorphic_select.c.containerspecs_type,
        polymorphic_identity=CONTAINER_SPECS_TYPES.CONTAINER,
        )
    if isinstance(ContainerSpecs.slug, property):
        ContainerSpecs.slug = \
            hybrid_property(ContainerSpecs.slug.fget,
                            expr=lambda cls: as_slug_expression(cls.name))
    return m
