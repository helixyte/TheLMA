"""
User preferences mapper.
"""
from sqlalchemy import String
from sqlalchemy import cast
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.models.user import User
from thelma.models.user import UserPreferences

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(user_preferences_tbl):
    "Mapper factory."
    m = mapper(UserPreferences, user_preferences_tbl,
               properties=dict(
                    id=synonym('user_preferences_id'),
                    user=relationship(User, uselist=False,
                                        back_populates='user_preferenceses',
                                        cascade='save-update'),
                    )
               )
    if isinstance(UserPreferences.slug, property):
        UserPreferences.slug = \
            hybrid_property(UserPreferences.slug.fget,
                            expr=lambda cls: cast(cls.user_preferences_id,
                                                  String))
    return m
