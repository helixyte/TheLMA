"""
Organization mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import column_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import synonym
from thelma.db.mappers.utils import CaseInsensitiveComparator
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.organization import Organization

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(organization_tbl):
    "Mapper factory."
    m = mapper(Organization, organization_tbl,
                  properties=dict(
                      id=synonym('organization_id'),
                      name=column_property(
                          organization_tbl.c.name,
                          comparator_factory=CaseInsensitiveComparator
                          ),
                      ),
                  )
    if isinstance(Organization.slug, property):
        Organization.slug = \
            hybrid_property(Organization.slug.fget,
                            expr=lambda cls: as_slug_expression(cls.name))
    return m
