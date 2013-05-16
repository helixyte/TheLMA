"""
Barcoded location type mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.sql import select
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.location import BarcodedLocationType

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(barcoded_location_tbl):
    "Mapper factory."
    bl = barcoded_location_tbl.alias('bl')

    location_select = select([bl.c.type.label('name')]
                             ).distinct().alias('loctypes')

    m = mapper(BarcodedLocationType, location_select,
               primary_key=[location_select.c.name],
               )
    if isinstance(BarcodedLocationType.slug, property):
        BarcodedLocationType.slug = \
            hybrid_property(BarcodedLocationType.slug.fget,
                            expr=lambda cls: as_slug_expression(cls.name))
    return m
