"""
Functional tests for the Job resource.
"""
from everest.mime import XmlMime
from pkg_resources import resource_filename # pylint: disable=E0611,F0401
from thelma.testing import ThelmaFunctionalTestCase

__docformat__ = 'reStructuredText en'

__author__ = 'Tobias Rothe'
__date__ = '$Date: 2012-05-14 12:56:10 +0200 (Mon, 14 May 2012) $'
__revision__ = '$Rev: 12568 $'
__source__ = '$URL:: $'

__all__ = ['JobCollectionTestCase',
           'JobMemberCreateAndUpdateTestCase',
           ]


class JobCollectionTestCase(ThelmaFunctionalTestCase):

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

# FIXME: broke due to introduction of different JOB_+TYPES (2.0).
# should be fixed by Tobias since he is most familiar with it ...?

#class JobMemberCreateAndUpdateTestCase(ThelmaFunctionalTestCase):
#
#    path = '/jobs'
#
#
#    def test_create_and_update_existing_job(self):
#        req1_body = read_file('thelma:tests/functional/test_job.xml')
#        res1 = self.app.post(self.path,
#                             params=req1_body,
#                             content_type=XmlMime.mime_string,
#                             status=201)
##        orm.Session.flush()
#        self.assert_true(not res1 is None)
#        res1_location = res1.headers['Location']
#        res2 = self.app.get(res1_location, status=200)
#        self.assert_true(not res2 is None)
##        req3_body = read_file('thelma:tests/functional/test_job.xml')
##        res3 = self.app.put(res1_location,
##                             params=req3_body,
##                             content_type=XmlMime.mime_string,
##                             status=200)
##        self.assert_true(not res3 is None)
