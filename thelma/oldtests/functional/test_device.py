"""
Functional tests for the device resource.
"""

from thelma.testing import ThelmaFunctionalTestCase

__docformat__ = 'reStructuredText en'
__all__ = ['DeviceCollectionTestCase',
           ]


class DeviceCollectionTestCase(ThelmaFunctionalTestCase):

    path = '/devices'

    def test_get_collection_without_querying(self):
        res = self.app.get(self.path, status=200)
        self.assert_true(not res is None)

    def test_sort_by_type(self):
        res = self.app.get(self.path, params=dict(sort='type.name:asc'),
                           status=200)
        self.assert_true(not res is None)
