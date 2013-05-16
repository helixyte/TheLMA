"""
User mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import column_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.db.mappers.utils import CaseInsensitiveComparator
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.user import User
from thelma.models.user import UserPreferences

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(dbuser_tbl):
    "Mapper factory."
    m = mapper(User, dbuser_tbl,
               properties=dict(
                    id=synonym('db_user_id'),
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
    if isinstance(User.slug, property):
        User.slug = \
            hybrid_property(User.slug.fget,
                            expr=lambda cls:
                                    as_slug_expression(cls.directory_user_id))
    return m
