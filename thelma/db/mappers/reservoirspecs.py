"""
Reservoir specs mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.liquidtransfer import ReservoirSpecs
from thelma.models.rack import RackShape

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(reservoir_specs_tbl):
    "Mapper factory."
    m = mapper(ReservoirSpecs, reservoir_specs_tbl,
               properties=dict(
                    id=synonym('reservoir_specs_id'),
                    rack_shape=relationship(RackShape, uselist=False,
                                            lazy='joined')
                    )
               )
    if isinstance(ReservoirSpecs.slug, property):
        ReservoirSpecs.slug = hybrid_property(ReservoirSpecs.slug.fget,
                             expr=lambda cls: as_slug_expression(cls.name))

    return m
