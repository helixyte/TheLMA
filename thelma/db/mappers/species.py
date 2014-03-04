"""
Species mapper.
"""
from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.gene import Gene
from thelma.models.cell_line import CellLine
from thelma.models.species import Species

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
                      cell_line=relationship(CellLine,
                                         back_populates='tissue'),
                      ),
                  )
    return m
