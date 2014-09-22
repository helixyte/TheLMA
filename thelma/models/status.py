"""
Item status model classes.

NP, AAB
"""

from everest.entities.base import Entity
from everest.entities.utils import slug_from_string

__docformat__ = 'reStructuredText en'

__all__ = ['ItemStatus']


class ITEM_STATUSES(object):
    MANAGED = 'Managed'
    FUTURE = 'Future'
    UNMANAGED = 'Unmanaged'
    DESTROYED = 'Destroyed'


class ItemStatus(Entity):
    """
    The item status of a rack of container.
    At the moment, there are four different item status:
    *managed*, *unmanaged*, *future* and *destroyed*.
    """

    #: The name is similar to the :attr:`id`.
    name = None
    #: A description of the item status.
    description = None

    def __init__(self, name, description=None, **kw):
        Entity.__init__(self, **kw)
        self.name = name
        self.description = description

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`name`.
        return slug_from_string(self.name)

    def __str__(self):
        return self.id

    def __repr__(self):
        str_format = '<%s id: %s, name: %s, description: %s>'
        params = (self.__class__.__name__, self.id,
                  self.name, self.description)
        return str_format % params
