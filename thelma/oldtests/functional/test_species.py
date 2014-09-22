"""
Functional tests for the species resource.
"""

from thelma.testing import ThelmaFunctionalTestCase

__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2011-11-25 16:40:58 +0100 (Fri, 25 Nov 2011) $'
__revision__ = '$Rev: 12281 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/tests/functional/te#$'

__all__ = ['SpeciesCollectionTestCase',
           ]

class SpeciesCollectionTestCase(ThelmaFunctionalTestCase):

    path = '/species'

    def test_get_collection_without_querying(self):
        res = self.app.get(self.path, status=200)
        self.assert_true(not res is None)

    def test_filter_by_genus_name(self):
        expected_name = 'Homo'
        res = self.app.get(self.path,
                           params=dict(q='genus-name:equal-to:"%s"' % expected_name),
                           status=200)
        self.assert_true(not res is None)

    def test_filter_by_species_name(self):
        expected_name = 'sapiens'
        res = self.app.get(self.path,
                           params=dict(q='species-name:equal-to:"%s"' % expected_name),
                           status=200)
        self.assert_true(not res is None)

    def test_filter_by_common_name(self):
        expected_name = 'human'
        res = self.app.get(self.path,
                           params=dict(q='common-name:equal-to:"%s"' % expected_name),
                           status=200)
        self.assert_true(not res is None)

    def test_filter_by_acronym(self):
        expected_name = 'HS'
        res = self.app.get(self.path,
                           params=dict(q='acronym:equal-to:"%s"' % expected_name),
                           status=200)
        self.assert_true(not res is None)

    def test_sort_by_genus_name(self):
        res = self.app.get(self.path, params=dict(sort='genus-name:asc'),
                           status=200)
        self.assert_true(not res is None)
        res = self.app.get(self.path, params=dict(sort='genus-name:desc'),
                           status=200)
        self.assert_true(not res is None)

    def test_sort_by_species_name(self):
        res = self.app.get(self.path, params=dict(sort='species-name:asc'),
                           status=200)
        self.assert_true(not res is None)
        res = self.app.get(self.path, params=dict(sort='species-name:desc'),
                           status=200)
        self.assert_true(not res is None)

    def test_sort_by_common_name(self):
        res = self.app.get(self.path, params=dict(sort='common-name:asc'),
                           status=200)
        self.assert_true(not res is None)
        res = self.app.get(self.path, params=dict(sort='common-name:desc'),
                           status=200)
        self.assert_true(not res is None)

    def test_sort_by_acronym(self):
        res = self.app.get(self.path, params=dict(sort='acronym:asc'),
                           status=200)
        self.assert_true(not res is None)
        res = self.app.get(self.path, params=dict(sort='acronym:desc'),
                           status=200)
        self.assert_true(not res is None)
