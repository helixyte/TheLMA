"""
Cell line batch mapper.
"""
from everest.repositories.rdb.utils import as_slug_expression, mapper
from sqlalchemy.orm import relationship
from thelma.models.cellline import CellLine, CellLineBatch
from thelma.models.container import Container
from thelma.models.subproject import Subproject

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(cell_line_batch_tbl):
    "Mapper factory."
    m = mapper(CellLineBatch, cell_line_batch_tbl,
               id_attribute='cell_line_id',
               slug_expression=lambda cls: as_slug_expression(cls.label),
               properties=dict(
                               container=relationship(Container, back_populates='cell_line_batch', uselist=False),
                               cell_line=relationship(CellLine, back_populates='batches', uselist=False),
                               parent=relationship(CellLineBatch, remote_side=CellLineBatch.id),
                               subproject=relationship(Subproject, back_populates='cell_line_batches', uselist=False),
                               ),
               )
    return m
