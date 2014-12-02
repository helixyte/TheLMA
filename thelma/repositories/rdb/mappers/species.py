"""
Species mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from thelma.entities.gene import Gene
from thelma.entities.species import Species


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(species_tbl):
    "Mapper factory."
    m = mapper(Species, species_tbl,
               id_attribute='species_id',
               slug_expression=lambda cls: as_slug_expression(cls.common_name),
               properties=dict(
                      genes=relationship(Gene,
                                         back_populates='species'),
                      ),
                  )
    return m
