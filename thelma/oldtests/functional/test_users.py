"""
Functional tests for the user resource.
"""

from thelma.testing import ThelmaFunctionalTestCase

__docformat__ = 'reStructuredText en'

__author__ = 'Tobias Rothe'
__date__ = '$Date: 2011-11-25 16:40:58 +0100 (Fri, 25 Nov 2011) $'
__revision__ = '$Rev: 12281 $'
__source__ = '$URL:: $'

__all__ = ['UserCollectionTestCase',
           ]

class UserCollectionTestCase(ThelmaFunctionalTestCase):

    path = '/users'

    def test_get_collection(self):
        res = self.app.get(self.path, status=200)
        self.assert_true(not res is None)

    def test_get_collection_member(self):
        res = self.app.get(self.path + '/longden/', status=200)
        self.assert_true(not res is None)
