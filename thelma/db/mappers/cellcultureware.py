"""
Cell culture ware mapper.
"""
from everest.repositories.rdb.utils import as_slug_expression, mapper
from sqlalchemy.orm import relationship
from thelma.models.cellcultureware import CellCultureWare
from thelma.models.cell_line import CellLine
from thelma.models.organization import Organization

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(cell_culture_ware_tbl):
    "Mapper factory."
    m = mapper(CellCultureWare, cell_culture_ware_tbl,
               id_attribute='cell_culture_ware_id',
               slug_expression=lambda cls: as_slug_expression(cls.label),
               properties=dict(
                      cell_line=relationship(CellLine,
                                         back_populates='cell_culture_ware'),
                      supplier=relationship(Organization,
                                         back_populates='cell_culture_ware'),
                      ),
                  )
    return m
