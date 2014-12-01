"""
User resource.
"""
from pyramid.exceptions import Forbidden

from everest.querying.specifications import AscendingOrderSpecification
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.entities.utils import get_current_user
from thelma.interfaces import IUserPreferences
from thelma.resources.base import RELATION_BASE_URL


__docformat__ = 'reStructuredText en'
__all__ = ['UserCollection',
           'UserMember',
           'UserPreferencesCollection',
           'UserPreferencesMember',
           ]


class UserMember(Member):
    relation = "%s/user" % RELATION_BASE_URL
    title = attribute_alias('username')
    label = attribute_alias('username')
    username = terminal_attribute(str, 'username')
    user_preferenceses = collection_attribute(IUserPreferences,
                                              'user_preferenceses')
    directory_user_id = terminal_attribute(str, 'directory_user_id')


class UserCollection(Collection):
    title = 'Users'
    root_name = 'users'
    description = 'Manage Users'
    default_order = AscendingOrderSpecification('username')

    def __getitem__(self, key):
        if key == 'current-user':
            user = get_current_user()
            if user == None:
                raise Forbidden()
            key = user.slug

        return Collection.__getitem__(self, key)


class UserPreferencesMember(Member):
    relation = "%s/user-preferences" % RELATION_BASE_URL
    title = attribute_alias('app_name')
    label = attribute_alias('app_name')
    app_name = terminal_attribute(str, 'app_name')
    preferences = terminal_attribute(str, 'preferences')


class UserPreferencesCollection(Collection):
    title = 'User Preferencess'
    root_name = 'user-preferenceses'
    description = 'Manage UserPreferencess'
