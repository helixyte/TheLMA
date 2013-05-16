"""
Functional tests for the moleculetype resource.
"""

from thelma.testing import ThelmaFunctionalTestCase

__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2011-11-25 16:40:58 +0100 (Fri, 25 Nov 2011) $'
__revision__ = '$Rev: 12281 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/tests/functional/te#$'

__all__ = ['MoleculeTypeCollectionTestCase',
           ]

class MoleculeTypeCollectionTestCase(ThelmaFunctionalTestCase):

    path = '/molecule-types'

    def test_get_collection_without_querying(self):
        res = self.app.get(self.path, status=200)
        self.assert_true(not res is None)

    def test_filter_by_id(self):
        expected_id = 'SIRNA'
        res = self.app.get(self.path,
                           params=dict(q='id:equal-to:"%s"' % expected_id),
                           status=200)
        self.assert_true(not res is None)

    def test_filter_by_name(self):
        expected_name = 'siRNA'
        res = self.app.get(self.path,
                           params=dict(q='name:equal-to:"%s"' % expected_name),
                           status=200)
        self.assert_true(not res is None)

    def test_sort_by_name(self):
        res = self.app.get(self.path, params=dict(sort='name:asc'),
                           status=200)
        self.assert_true(not res is None)
        res = self.app.get(self.path, params=dict(sort='name:desc'),
                           status=200)
        self.assert_true(not res is None)

    def test_sort_by_thaw_time(self):
        res = self.app.get(self.path, params=dict(sort='thaw-time:asc'),
                           status=200)
        self.assert_true(not res is None)
        res = self.app.get(self.path, params=dict(sort='thaw-time:desc'),
                           status=200)
        self.assert_true(not res is None)
