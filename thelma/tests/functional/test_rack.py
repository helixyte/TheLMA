"""
Functional tests for the rack resource.

FOG 01.11
"""

from everest.mime import CSV_MIME
from thelma.testing import ThelmaFunctionalTestCase

__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2012-07-11 16:04:16 +0200 (Wed, 11 Jul 2012) $'
__revision__ = '$Rev: 12659 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/tests/functional/te#$'

__all__ = ['RackCollectionTestCase',
           ]

class RackCollectionTestCase(ThelmaFunctionalTestCase):

    path = '/racks'
    barcode = '02494292'

    def test_get_collection_without_querying(self):
        res = self.app.get(self.path, status=200)
        self.assert_true(not res is None)
        xml = self._parse_body(res.body)
        contents = self.find_entry_contents(xml)
        racks = [(self.find_elements(content, name='plate')
                  or self.find_elements(content, name='tube_rack'))[0]
                 for content in contents]
        self.assert_equal(len(racks), 100)

    def test_filter_by_barcode(self):
        res = self.app.get(
                    self.path,
                    params=dict(q='barcode:equal-to:"%s"' % self.barcode),
                    status=200)
        self.assert_true(not res is None)

    # TODO: reactivate (inconsistent result on hudson)
#    def test_retrieve_wells(self):
#        res = self.app.get("%s/%s/wells" % (self.path, self.barcode),
#                           status=200)
#        self.assert_true(not res is None)

    def test_retrieve_racks_as_csv_by_header(self):
        res = self.app.get(self.path, status=200,
                           params=
                             dict(q='barcode:equal-to:"%s"' % self.barcode),
                           headers=dict(accept=CSV_MIME))
        self.assert_true(not res is None)
        self.assert_true(res.headers['content-type'].startswith(CSV_MIME))

    def test_retrieve_racks_as_csv_by_uri(self):
        res = self.app.get(self.path + '.csv', status=200,
                           params=
                             dict(q='barcode:equal-to:"%s"' % self.barcode))
        self.assert_true(not res is None)
        self.assert_true(res.headers['content-type'].startswith(CSV_MIME))
