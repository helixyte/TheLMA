"""
Tissue mapper.
"""
from everest.repositories.rdb.utils import as_slug_expression, mapper
from sqlalchemy.orm import relationship
from thelma.models.cellline import CellLine
from thelma.models.tissue import Tissue

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(tissue_tbl):
    "Mapper factory."
    m = mapper(Tissue, tissue_tbl,
               id_attribute='tissue_id',
               slug_expression=lambda cls: as_slug_expression(cls.label),
               properties=dict(
                      cell_line=relationship(CellLine,
                                         back_populates='tissue'),
                      ),
                  )
    return m
