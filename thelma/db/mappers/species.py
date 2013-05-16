"""
Species mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.gene import Gene
from thelma.models.species import Species

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(species_tbl):
    "Mapper factory."
    m = mapper(Species, species_tbl,
                  properties=dict(
                      id=synonym('species_id'),
                      genes=relationship(Gene,
                                         back_populates='species'),
                      ),
                  )
    if isinstance(Species.slug, property):
        Species.slug = hybrid_property(Species.slug.fget,
                                       expr=lambda cls:
                                        as_slug_expression(cls.common_name))
    return m
