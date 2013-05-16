'''
Created on May 26, 2011

@author: berger
'''

from thelma.models.user import User
from thelma.testing import ThelmaModelTestCase


class UserModelTest(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.username = 'Some Guy'
        self.directory_user_id = 'guy'
        self.preferences = self._create_user_preferences()

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.username
        del self.directory_user_id
        del self.preferences

    def test_user_init(self):
        user = User(self.username, self.directory_user_id, [self.preferences])
        self.assert_not_equal(user, None)
        self.assert_equal(user.username, self.username)
        self.assert_true(user.id is None)
        self.assert_not_equal(user.slug, None)

    def test_user_slug(self):
        expected_slug = 'guy'
        user = User(self.username, self.directory_user_id, [self.preferences])
        self.assert_not_equal(user.slug, self.username)
        self.assert_equal(user.slug, expected_slug)

    def test_user_equality(self):
        id1 = 1
        id2 = 2
        user1 = User(self.username, self.directory_user_id, [self.preferences])
        user1.id = id1
        user2 = User(self.username, self.directory_user_id, [self.preferences])
        user2.id = id2
        user3 = User('someone else', 'else', [self.preferences])
        user3.id = id1
        self.assert_not_equal(user1, user2)
        self.assert_equal(user1, user3)
