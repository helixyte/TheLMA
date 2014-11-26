"""
Container specs mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.sql import case
from sqlalchemy.sql import literal
from sqlalchemy.sql import select
from everest.repositories.rdb.utils import as_slug_expression
from thelma.entities.container import CONTAINER_SPECS_TYPES
from thelma.entities.container import ContainerSpecs
from thelma.entities.organization import Organization

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
        id_attribute='container_specs_id',
        slug_expression=lambda cls: as_slug_expression(cls.name),
        properties=dict(manufacturer=relationship(Organization),
                        ),
        polymorphic_on=polymorphic_select.c.containerspecs_type,
        polymorphic_identity=CONTAINER_SPECS_TYPES.CONTAINER,
        )
    return m
