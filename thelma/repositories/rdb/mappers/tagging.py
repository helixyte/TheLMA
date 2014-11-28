"""
Tagging mapper.
"""
from sqlalchemy.orm import mapper, relationship
from thelma.entities.tagging import Tag, Tagging, Tagged
from thelma.entities.user import User

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(tagging_tbl):
    "Mapper factory."
    m = mapper(Tagging, tagging_tbl,
               properties=dict(tag=relationship(Tag, uselist=False),
                               tagged=relationship(Tagged, uselist=False),
                               user=relationship(User, uselist=False)),
               )
    return m
