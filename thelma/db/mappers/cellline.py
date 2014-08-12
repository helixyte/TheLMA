"""
Cell line mapper.
"""
from everest.repositories.rdb.utils import as_slug_expression, mapper
from sqlalchemy.orm import relationship
from thelma.models.cellcultureware import CellCultureWare
from thelma.models.cellline import CellLine, CellLineBatch
from thelma.models.organization import Organization
from thelma.models.species import Species
from thelma.models.tissue import Tissue

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(cell_line_tbl):
    "Mapper factory."
    m = mapper(CellLine, cell_line_tbl,
               id_attribute='cell_line_id',
               slug_expression=lambda cls: as_slug_expression(cls.label),
               properties=dict(
                               species=relationship(Species, back_populates='cell_line'),
                               tissue=relationship(Tissue, back_populates='cell_line'), 
                               supplier=relationship(Organization, back_populates='cell_line'),
                               cell_culture_ware=relationship(CellCultureWare, back_populates='cell_line'),
                               batches=relationship(CellLineBatch, back_populates='cell_line'),
                               ),
               )
    return m
