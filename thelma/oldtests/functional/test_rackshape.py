"""
Functional tests for the rackshape resource.
"""

from thelma.testing import ThelmaFunctionalTestCase

__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2011-11-25 16:40:58 +0100 (Fri, 25 Nov 2011) $'
__revision__ = '$Rev: 12281 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/tests/functional/te#$'

__all__ = ['RackShapeCollectionTestCase',
           ]

class RackShapeCollectionTestCase(ThelmaFunctionalTestCase):

    path = '/rack-shapes'

    def test_get_collection(self):
        res = self.app.get(self.path, status=200)
        self.assert_true(not res is None)

    def test_get_collection_member(self):
        res = self.app.get(self.path + '/8x12/', status=200)
        self.assert_true(not res is None)
