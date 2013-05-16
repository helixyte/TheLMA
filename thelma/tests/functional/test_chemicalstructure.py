"""
Functional tests for the chemical structure resource.
"""
from thelma.testing import ThelmaFunctionalTestCase

__docformat__ = 'reStructuredText en'
__all__ = ['ChemicalStructureCollectionTestCase',
           ]

class ChemicalStructureCollectionTestCase(ThelmaFunctionalTestCase):

    path = '/chemical-structures'

    def test_get_collection_without_querying(self):
        res = self.app.get(self.path, status=200)
        self.assert_true(not res is None)

    def test_filter_by_id(self):
        expected_id = '107'
        res = self.app.get(self.path,
                           params=dict(q='id:equal-to:%s' % expected_id),
                           status=200)
        self.assert_true(not res is None)

    def test_filter_by_molecule_type(self):
        moltype_href = 'http://localhost/molecule-types/sirna/'
        res = self.app.get(self.path,
            params=dict(q='molecule-designs.molecule-type:equal-to:%s' \
                          % moltype_href),
            status=200)
        self.assert_true(not res is None)

    def test_filter_by_modification(self):
        moltype_href = 'http://localhost/molecule-types/cloned-dsdna'
        res = self.app.get(self.path,
            params=dict(q='molecule-designs.molecule-type:equal-to:%s' \
                          '~structure-type-id:equal-to:"MODIFICATION"' \
                          % moltype_href),
            status=200)
        self.assert_true(not res is None)

    def test_sort_by_id(self):
        res = self.app.get(self.path, params=dict(sort='id:asc'),
                           status=200)
        self.assert_true(not res is None)
        res = self.app.get(self.path, params=dict(sort='id:desc'),
                           status=200)
        self.assert_true(not res is None)
