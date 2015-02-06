"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Item status mapper.
"""
from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from thelma.entities.status import ItemStatus


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(item_status_tbl):
    "Mapper factory."
    m = mapper(ItemStatus, item_status_tbl,
               id_attribute='item_status_id',
               slug_expression=lambda cls: as_slug_expression(cls.name))
    return m
