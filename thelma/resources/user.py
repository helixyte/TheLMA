"""
User resource.

TR
"""

from everest.querying.specifications import AscendingOrderSpecification
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import terminal_attribute
from pyramid.exceptions import Forbidden
from thelma.interfaces import IUserPreferences
from thelma.resources.base import RELATION_BASE_URL
from thelma.models.utils import get_current_user


__docformat__ = 'reStructuredText en'

__author__ = 'Tobias Rothe'
__date__ = '$Date: 2013-02-12 09:16:49 +0100 (Tue, 12 Feb 2013) $'
__revision__ = '$Rev: 13137 $'
__source__ = '$URL:#$'

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
                                              'user_preferenceses',
                                              is_nested=True)
    directory_user_id = terminal_attribute(str, 'directory_user_id')

    def update_from_data(self, data_element):
        Member.update_from_data(self, data_element)


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