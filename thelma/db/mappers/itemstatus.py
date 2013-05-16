"""
Item status mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import synonym
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.status import ItemStatus

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(item_status_tbl):
    "Mapper factory."
    m = mapper(ItemStatus, item_status_tbl,
               properties=dict(
                   id=synonym('item_status_id'),
                   ),
               )
    if isinstance(ItemStatus.slug, property):
        ItemStatus.slug = \
            hybrid_property(ItemStatus.slug.fget,
                            expr=lambda cls: as_slug_expression(cls.name))
    return m
