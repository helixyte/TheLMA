"""
Reservoir specs mapper.
"""
from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.entities.liquidtransfer import ReservoirSpecs
from thelma.entities.rack import RackShape

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(reservoir_specs_tbl):
    "Mapper factory."

    tbl = reservoir_specs_tbl
    m = mapper(ReservoirSpecs, reservoir_specs_tbl,
               id_attribute='reservoir_specs_id',
               slug_expression=lambda cls: as_slug_expression(cls._name), # pylint: disable=W0212
               properties=dict(
                    _rack_shape=relationship(RackShape, uselist=False,
                                            lazy='joined'),
                    _name=tbl.c.name,
                    _description=tbl.c.description,
                    _max_volume=tbl.c.max_volume,
                    _min_dead_volume=tbl.c.min_dead_volume,
                    _max_dead_volume=tbl.c.max_dead_volume)
               )
    return m
