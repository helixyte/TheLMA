"""
Organization entity classes.
"""
from everest.entities.base import Entity
from everest.entities.utils import slug_from_string


__docformat__ = "reStructuredText en"
__all__ = ['Organization']


class Organization(Entity):
    """
    Organizations can be customers, suppliers, etc.
    """
    #: The name of the organization.
    name = None

    def __init__(self, name, **kw):
        Entity.__init__(self, **kw)
        self.name = str(name)

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`name`.
        return slug_from_string(self.name)

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        str_format = '<%s id: %s, name: %s>'
        params = (self.__class__.__name__, self.id, self.name)
        return str_format % params
