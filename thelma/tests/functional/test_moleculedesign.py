"""
Functional tests for the moleculedesign resource.
"""
from thelma.testing import ThelmaFunctionalTestCase
from everest.resources.utils import get_root_collection
from thelma.interfaces import IChemicalStructure
from everest.querying.specifications import eq

__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2012-11-12 12:45:24 +0100 (Mon, 12 Nov 2012) $'
__revision__ = '$Rev: 12945 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/tests/functional/te#$'

__all__ = ['MoleculeDesignCollectionTestCase',
           ]

class MoleculeDesignCollectionTestCase(ThelmaFunctionalTestCase):

    path = '/molecule-designs'

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
            params=dict(q='molecule-type:equal-to:"%s"' % moltype_href,
                        size=3),
            status=200)
        self.assert_true(not res is None)

    def test_filter_by_molecule_type_and_then_follow_next_page(self):
        # TODO: create a separate series of tests for paging issues # pylint: disable-msg=W0511
        moltype_href = 'http://localhost/molecule-types/sirna/'
        res = self.app.get(self.path,
            params=dict(q='molecule-type:equal-to:"%s"' % moltype_href,
                        size=3),
            status=200)
        self.assert_true(not res is None)

    def test_filter_by_modification(self):
        coll = get_root_collection(IChemicalStructure)
        coll.filter = eq(representation='Regulus A')
        cs = iter(coll).next()
        mod_href = 'http://localhost/chemical-structures/%d' % cs.id
        criteria = 'chemical-structures:contains:"%s"' % mod_href
        res = self.app.get(self.path,
            params=dict(q=criteria, size=100),
            status=200)
        self.assert_true(not res is None)

    def test_sort_by_id(self):
        res = self.app.get(self.path, params=dict(sort='id:asc'),
                           status=200)
        self.assert_true(not res is None)
        res = self.app.get(self.path, params=dict(sort='id:desc'),
                           status=200)
        self.assert_true(not res is None)

    def test_sort_by_molecule_type(self):
        res = self.app.get(self.path,
                           params=dict(sort='molecule-type.name:asc'),
                           status=200)
        self.assert_true(not res is None)
        res = self.app.get(self.path,
                           params=dict(sort='molecule-type.name:desc'),
                           status=200)
        self.assert_true(not res is None)
