"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

User mapper.
"""
from sqlalchemy.orm import column_property
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from thelma.entities.user import User
from thelma.entities.user import UserPreferences
from thelma.repositories.rdb.mappers.utils import CaseInsensitiveComparator


__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(dbuser_tbl):
    "Mapper factory."
    m = mapper(User, dbuser_tbl,
               id_attribute='db_user_id',
               slug_expression=
                    lambda cls: as_slug_expression(cls.directory_user_id),
               properties=dict(
                    username=column_property(
                          dbuser_tbl.c.username,
                          comparator_factory=CaseInsensitiveComparator
                          ),
                    user_preferenceses=relationship(UserPreferences,
                                             back_populates='user',
                                             cascade='all, delete-orphan'
                                             ),
                    ),
               )
    return m
