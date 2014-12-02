"""
Organization mapper.
"""
from sqlalchemy.orm import column_property

from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from thelma.entities.organization import Organization
from thelma.repositories.rdb.mappers.utils import CaseInsensitiveComparator


__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(organization_tbl):
    "Mapper factory."
    m = mapper(Organization, organization_tbl,
               id_attribute='organization_id',
               slug_expression=lambda cls: as_slug_expression(cls.name),
               properties=dict(
                      name=column_property(
                          organization_tbl.c.name,
                          comparator_factory=CaseInsensitiveComparator
                          ),
                      ),
                  )
    return m
