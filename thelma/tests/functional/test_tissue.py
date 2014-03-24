"""
Functional tests for the species resource.
"""

from thelma.testing import ThelmaFunctionalTestCase

__all__ = ['TissuesCollectionTestCase']

class TissuesCollectionTestCase(ThelmaFunctionalTestCase):

    path = '/tissue'

    def test_get_collection_without_querying(self):
        res = self.app.get(self.path, status=200)
        self.assert_true(not res is None)

    def test_filter_by_label(self):
        expected_name = 'Skin'
        res = self.app.get(self.path,
                           params=dict(q='label:equal-to:"%s"' % expected_name),
                           status=200)
        self.assert_true(not res is None)

    def test_sort_by_label(self):
        res = self.app.get(self.path, params=dict(sort='label:asc'),
                           status=200)
        self.assert_true(not res is None)
        res = self.app.get(self.path, params=dict(sort='label:desc'),
                           status=200)
        self.assert_true(not res is None)

