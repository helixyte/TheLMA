"""
Functional tests for the stockinfo resource.
"""

from nose.plugins.attrib import attr
from thelma.testing import ThelmaFunctionalTestCase

__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2012-12-06 20:47:04 +0100 (Thu, 06 Dec 2012) $'
__revision__ = '$Rev: 12985 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/tests/functional/te#$'

__all__ = ['StockInfoCollectionTestCase',
           ]

class StockInfoCollectionTestCase(ThelmaFunctionalTestCase):

    path = '/stock-info'
    molecule_design_pool_id_query = 'molecule-design-pool-id:contained:%s' \
                                    % ', '.join(map(str, range(10, 100)))

    def test_load_by_molecule_type(self):
        res = self.app.get(self.path,
                           params=dict(q='molecule-type:equal-to:'
                                       'http://thelma/molecule-types/sirna/')
                           )
        self.assert_true(not res is None)

    @attr('slow')
    def test_search_by_minimum_volume_and_concentration(self):
        self.app.get(
            self.path,
            params=dict(q='minimum-volume:greater-than-or-equal-to:0.000005~'
                          'concentration:equal-to:0.00005'),
            status=200)

    @attr('slow')
    def test_sort_by_molecule_design_set_id(self):
        res = self.app.get(self.path,
                           params=dict(sort='molecule-design-pool-id:asc',
                                       q=self.molecule_design_pool_id_query),
                           status=200)
        self.assert_true(not res is None)
        res = self.app.get(self.path,
                           params=dict(sort='molecule-design-pool-id:desc',
                                       q=self.molecule_design_pool_id_query),
                           status=200)
        self.assert_true(not res is None)

    @attr('slow')
    def test_sort_by_molecule_type(self):
        res = self.app.get(self.path,
                           params=dict(sort='molecule-type.name:asc',
                                       q=self.molecule_design_pool_id_query),
                           status=200)
        self.assert_true(not res is None)
        res = self.app.get(self.path,
                           params=dict(sort='molecule-type.name:desc',
                                       q=self.molecule_design_pool_id_query),
                           status=200)
        self.assert_true(not res is None)

    @attr('slow')
    def test_sort_by_total_tubes(self):
        res = self.app.get(self.path,
                           params=dict(sort='total-tubes:asc',
                                       q=self.molecule_design_pool_id_query),
                           status=200)
        self.assert_true(not res is None)
        res = self.app.get(self.path,
                           params=dict(sort='total-tubes:desc',
                                       q=self.molecule_design_pool_id_query),
                           status=200)
        self.assert_true(not res is None)

    @attr('slow')
    def test_sort_by_total_volume(self):
        res = self.app.get(self.path,
                           params=dict(sort='total-volume:asc',
                                       q=self.molecule_design_pool_id_query),
                           status=200)
        self.assert_true(not res is None)
        res = self.app.get(self.path,
                           params=dict(sort='total-volume:desc',
                                       q=self.molecule_design_pool_id_query),
                           status=200)
        self.assert_true(not res is None)

    @attr('slow')
    def test_sort_by_minimum_volume(self):
        res = self.app.get(self.path,
                           params=dict(sort='minimum-volume:asc',
                                       q=self.molecule_design_pool_id_query),
                           status=200)
        self.assert_true(not res is None)
        res = self.app.get(self.path,
                           params=dict(sort='minimum-volume:desc',
                                       q=self.molecule_design_pool_id_query),
                           status=200)
        self.assert_true(not res is None)

    @attr('slow')
    def test_sort_by_maximum_volume(self):
        res = self.app.get(self.path,
                           params=dict(sort='maximum-volume:asc',
                                       q=self.molecule_design_pool_id_query),
                           status=200)
        self.assert_true(not res is None)
        res = self.app.get(self.path,
                           params=dict(sort='maximum-volume:desc',
                                       q=self.molecule_design_pool_id_query),
                           status=200)
        self.assert_true(not res is None)

    @attr('slow')
    def test_sort_by_concentration(self):
        res = self.app.get(self.path,
                           params=dict(sort='concentration:asc',
                                       q=self.molecule_design_pool_id_query),
                           status=200)
        self.assert_true(not res is None)
        res = self.app.get(self.path,
                           params=dict(sort='concentration:desc',
                                       q=self.molecule_design_pool_id_query),
                           status=200)
        self.assert_true(not res is None)
