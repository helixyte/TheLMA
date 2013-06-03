"""
Barcoded location type mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.sql import select
from everest.repositories.rdb.utils import as_slug_expression
from thelma.models.location import BarcodedLocationType

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(barcoded_location_tbl):
    "Mapper factory."
    bl = barcoded_location_tbl.alias('bl')

    location_select = select([bl.c.type.label('name')]
                             ).distinct().alias('loctypes')

    m = mapper(BarcodedLocationType, location_select,
               slug_expression=lambda cls: as_slug_expression(cls.name),
               primary_key=[location_select.c.name],
               )
    return m
