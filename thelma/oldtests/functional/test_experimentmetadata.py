"""
Functional tests for the ExperimentMetadata resource.
"""

#from everest.mime import XlsMime
#from everest.mime import XmlMime
from pkg_resources import resource_filename # pylint: disable=E0611,F0401
from thelma.testing import ThelmaFunctionalTestCase

__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2013-05-08 17:42:10 +0200 (Wed, 08 May 2013) $'
__revision__ = '$Rev: 13330 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/tests/functional/te#$'

__all__ = ['ExperimentMetadataCollectionTestCase',
           'ExperimentMetadataMemberCreateAndUpdateTestCase',
           ]


class ExperimentMetadataCollectionTestCase(ThelmaFunctionalTestCase):

    path = '/experiment-metadatas'

    def test_get_collection_without_querying(self):
        res = self.app.get(self.path, status=200)
        self.assert_true(not res is None)


def read_file(pkg_res_name):
    tokens = pkg_res_name.split(':')
    fn = resource_filename(*tokens) # pylint: disable=W0142
    try:
        f_stream = open(fn, 'rb')
        txt = f_stream.read()
    finally:
        f_stream.close()
    return txt


class ExperimentMetadataMemberCreateAndUpdateTestCase(
                                                    ThelmaFunctionalTestCase):

    path = '/experiment-metadatas'

#    def test_create_and_update_existing_experimentmetadata(self):
#        req1_body = \
#            read_file('thelma:tests/functional/test_experimentmetadata.xml')
#        res1 = self.app.post(self.path,
#                             params=req1_body,
#                             content_type=XmlMime.mime_string,
#                             status=201)
#        self.assert_true(not res1 is None)
#        res1_location = res1.headers['Location']
#
#        res2 = self.app.get(res1_location, status=200)
#        self.assert_true(not res2 is None)
#        req3_body = \
#            read_file('thelma:tests/tools/iso/iso_generator/valid_experiment_metadata.xls')
#        res3 = self.app.put(res1_location,
#                             params=req3_body,
#                             content_type=XlsMime.mime_string,
#                             status=307)
#        self.assert_true(not res3 is None)
#        res3_location = res3.headers['Location']
#        req4_body = \
#            read_file('thelma:tests/tools/iso/iso_generator/valid_experiment_metadata.xls')
#        res4 = self.app.put(res3_location,
#                             params=req4_body,
#                             content_type=XlsMime.mime_string,
#                             status=200)
#        self.assert_true(not res4 is None)
