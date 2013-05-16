"""
User model classes.

TR, AAB
"""

from everest.entities.base import Entity
from everest.entities.utils import slug_from_string

__docformat__ = "reStructuredText en"
__author__ = 'Tobias Rothe'

__all__ = ['User']


class User(Entity):
    """
    This class represents TheLMA users.

    **Equality Condition**: equal :attr:`id`
    """

    #: The database user name of the user.
    username = None
    #: The organization wide directory ID of the user.
    directory_user_id = None
    #: a list of preferences (:class:`thelma.models.user.UserPreferences`)
    #: belonging to this user.
    user_preferenceses = None

    def __init__(self, username, directory_user_id, user_preferenceses, **kw):
        Entity.__init__(self, **kw)
        self.username = username
        self.directory_user_id = directory_user_id
        if user_preferenceses is None:
            user_preferenceses = []
        self.user_preferenceses = user_preferenceses

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`username`.
        return slug_from_string(self.directory_user_id)

    def __eq__(self, other):
        """Equality operator

        Equality is based on ID only
        """
        return (isinstance(other, User) and self.id == other.id)

    def __str__(self):
        return self.username


class UserPreferences(Entity):
    """
    This class represents TheLMA users.

    **Equality Condition**: equal :attr:`id`
    """

    #: The user who this preferences belong to
    #: (:class:`thelma.models.user.User`).
    user = None
    #: The name of the associated application
    app_name = None
    #: A application specific serialization of preferences
    preferences = None

    def __init__(self, app_name, preferences, **kw):
        Entity.__init__(self, **kw)
        self.app_name = app_name
        self.preferences = preferences

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`username`.
        return slug_from_string(self.user.username + '_' + self.app_name)

    def __eq__(self, other):
        """Equality operator

        Equality is based on ID only
        """
        return (isinstance(other, User) and self.id == other.id)

    def __str__(self):
        return self.preferences
