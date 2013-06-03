"""
Reservoir specs mapper.
"""
from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.liquidtransfer import ReservoirSpecs
from thelma.models.rack import RackShape

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(reservoir_specs_tbl):
    "Mapper factory."
    m = mapper(ReservoirSpecs, reservoir_specs_tbl,
               id_attribute='reservoir_specs_id',
               slug_expression=lambda cls: as_slug_expression(cls.name),
               properties=dict(
                    rack_shape=relationship(RackShape, uselist=False,
                                            lazy='joined')
                    )
               )
    return m
