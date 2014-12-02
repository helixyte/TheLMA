"""
User preferences mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import mapper
from thelma.entities.user import User
from thelma.entities.user import UserPreferences


__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(user_preferences_tbl):
    "Mapper factory."
    m = mapper(UserPreferences, user_preferences_tbl,
               id_attribute='user_preferences_id',
               properties=dict(
                    user=relationship(User, uselist=False,
                                        back_populates='user_preferenceses',
                                        cascade='save-update'),
                    )
               )
    return m
