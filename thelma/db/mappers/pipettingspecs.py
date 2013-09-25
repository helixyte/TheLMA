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

    tbl = pipetting_specs_tbl
    m = mapper(PipettingSpecs, pipetting_specs_tbl,
               id_attribute='pipetting_specs_id',
               slug_expression=lambda cls: as_slug_expression(cls.name),
               properties=dict(
                        _name=tbl.c.name,
                        _min_transfer_volume=tbl.c.min_transfer_volume,
                        _max_transfer_volume=tbl.c.max_transfer_volume,
                        _max_dilution_factor=tbl.c.max_dilution_factor,
                        _has_dynamic_dead_volume=tbl.c.has_dynamic_dead_volume,
                        _is_sector_bound=tbl.c.is_sector_bound)
               )

    return m
