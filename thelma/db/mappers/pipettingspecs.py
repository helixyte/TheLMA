"""
Pipetting specs mapper.
"""
from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from thelma.models.liquidtransfer import PipettingSpecs

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']

def create_mapper(pipetting_specs_tbl):
    "Mapper Factory"
    m = mapper(PipettingSpecs, pipetting_specs_tbl,
               id_attribute='pipetting_specs_id',
               slug_expression=lambda cls: as_slug_expression(cls.name)
               )

    return m
