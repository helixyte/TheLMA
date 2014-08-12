"""
Cell line batch mapper.
"""
from everest.repositories.rdb.utils import as_slug_expression, mapper
from sqlalchemy.orm import relationship
from thelma.models.cellline import CellLine, CellLineBatch
from thelma.models.container import Container
from thelma.models.project import Project

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(cell_line_tbl):
    "Mapper factory."
    m = mapper(CellLineBatch, cell_line_tbl,
               id_attribute='cell_line_id',
               slug_expression=lambda cls: as_slug_expression(cls.label),
               properties=dict(
                               container=relationship(Container, back_populates='cell_line_batch'),
                               cell_line=relationship(CellLine, back_populates='batches'), 
                               project=relationship(Project, back_populates='cell_line'),
                               ),
               )
    return m
