"""
Functional tests for the gene resource.
"""

from thelma.testing import ThelmaFunctionalTestCase

__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2012-04-20 15:00:15 +0200 (Fri, 20 Apr 2012) $'
__revision__ = '$Rev: 12557 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/tests/functional/te#$'

__all__ = ['GeneCollectionTestCase',
           ]

class NewGeneCollectionTestCase(ThelmaFunctionalTestCase):
    path = '/genes'


class GeneCollectionTestCase(ThelmaFunctionalTestCase):

    path = '/genes'

    def test_get_collection_without_querying(self):
        self.app.get('/genes', status=200) # , params=dict(size=4))

    def test_get_member(self):
        res = self.app.get('/genes/10', status=200,
                           params=dict(size=4))
        self.assert_true(not res is None)

    def test_filter_by_accession(self):
        expected_accession = '553129'
        res = self.app.get(self.path,
            params=dict(q='accession:equal-to:"%s"' % expected_accession),
            status=200)
        self.assert_true(not res is None)
        xml = self._parse_body(res.body)
        self.assert_equal(self.count_entries(xml), 1)

    def test_filter_by_name(self):
        expected_name = 'CAT'
        res = self.app.get(self.path,
            params=dict(q='locus-name:equal-to:"%s"' % expected_name), #, size=3),
            status=200)
        self.assert_true(not res is None)
        xml = self._parse_body(res.body)
        self.assert_equal(self.count_entries(xml), 3)

    def test_filter_by_species(self):
        expected_species_href = 'http://localhost/species/mouse/'
        res = self.app.get(self.path,
            params=dict(q='species:equal-to:"%s"' % expected_species_href,
                        size=4),
            status=200)
        self.assert_true(not res is None)
        xml = self._parse_body(res.body)
        self.assert_equal(self.count_entries(xml), 4)

    def test_sort_by_accession(self):
        res = self.app.get(self.path, params=dict(sort='accession:asc'),
                           status=200)
        self.assert_true(not res is None)
        res = self.app.get(self.path, params=dict(sort='accession:desc'),
                           status=200)
        self.assert_true(not res is None)

    def test_sort_by_name(self):
        res = self.app.get(self.path, params=dict(sort='locus-name:asc'),
                           status=200)
        self.assert_true(not res is None)
        res = self.app.get(self.path, params=dict(sort='locus-name:desc'),
                           status=200)
        self.assert_true(not res is None)

    def test_sort_by_species(self):
        res = self.app.get(self.path,
                           params=dict(sort='species.common-name:asc'),
                           status=200)
        self.assert_true(not res is None)
        res = self.app.get(self.path,
                           params=dict(sort='species.common-name:desc'),
                           status=200)
        self.assert_true(not res is None)
