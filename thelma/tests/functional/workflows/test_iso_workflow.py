"""
Functional tests for the IsoRequest resource.

Created on Nov 26, 2013.
"""
from everest.entities.utils import get_root_aggregate
from everest.mime import XlsMime
from everest.mime import XmlMime
from everest.representers.utils import as_representer
from everest.resources.interfaces import IService
from everest.resources.staging import create_staging_collection
from everest.resources.utils import resource_to_url
from everest.resources.utils import url_to_resource
from everest.testing import RdbContextManager
from pkg_resources import resource_filename # pylint: disable=E0611
from pyramid.httpexceptions import HTTPCreated
from pyramid.httpexceptions import HTTPOk
from pyramid.httpexceptions import HTTPTemporaryRedirect
from pyramid.testing import DummyRequest
from thelma.interfaces import IExperimentMetadata
from thelma.interfaces import ISubproject
from thelma.models.experiment import ExperimentMetadata
from thelma.testing import ThelmaFunctionalTestCase
from thelma.tests.tools.iso.lab.utils import LAB_ISO_TEST_CASES
import os

__docformat__ = 'reStructuredText en'
__all__ = ['IsoWorkflowTestCase',
           ]


class IsoWorkflowTestCase(ThelmaFunctionalTestCase):
    def set_up(self):
        ThelmaFunctionalTestCase.set_up(self)
        # Set up a dummy request and start the service so we can use it before
        # the root factory is called (and starts it).
        base_url = app_url = self._get_app_url()
        request = DummyRequest(application_url=app_url,
                               host_url=base_url,
                               path_url=app_url,
                               url=app_url,
                               registry=self.config.registry,
                               environ=dict(REMOTE_USER='it'))
        self.config.manager.get()['request'] = request
        srvc = self.config.get_registered_utility(IService)
        request.root = srvc
        srvc.start()

    def test_workflow(self):
        with RdbContextManager():
            emd_url = self._upload_metadata(LAB_ISO_TEST_CASES.CASE_NO_JOB_DIRECT)
            emd = url_to_resource(emd_url)
            self._accept_iso_request(emd.iso_request)

    def _upload_metadata(self, case_name):
        # First, create a new metadata entity and POST it.
        emd_coll = create_staging_collection(IExperimentMetadata)
        esc = LAB_ISO_TEST_CASES.get_experiment_scenario(case_name)
        emd = ExperimentMetadata('unit_test_metadata',
                                 next(iter(get_root_aggregate(ISubproject))),
                                 1,
                                 esc,
#                                 ticket_number=0
                                 )
        mb_emd = emd_coll.create_member(emd)
        rpr = as_representer(mb_emd, XmlMime)
        emd_rpr = rpr.to_string(mb_emd)
        res = self.app.post("/%s" % emd_coll.__name__,
                            params=emd_rpr,
                            content_type=XmlMime.mime_type_string,
                            status=HTTPCreated.code)
        mb_url = res.headers['Location']
        # Now, PUT the excel meta data file.
        xls_fn = LAB_ISO_TEST_CASES.get_xls_file_name(case_name)
        pkg_fn = resource_filename(LAB_ISO_TEST_CASES.__module__,
                                   os.path.join('cases', xls_fn))
        with open(pkg_fn, 'rb') as xls_file:
            res = self.app.put(mb_url,
                               params=xls_file.read(),
                               content_type=XlsMime.mime_type_string)
        # If the file had warnings, we have to repeat the PUT.
        if res.status.endswith(HTTPTemporaryRedirect.title):
            # 307 Redirect: Repeat with warnings disabled.
            with open(pkg_fn, 'rb') as xls_file:
                res = self.app.put(res.headers['Location'],
                                   params=xls_file.read(),
                                   content_type=XlsMime.mime_type_string,
                                   status=HTTPOk.code)
        self.assert_true(res.status.endswith(HTTPOk.title))
        return mb_url

    def _accept_iso_request(self, iso_request):
        new_owner = 'thelma, stockmanagement'
        isor = iso_request.get_entity()
        old_owner = isor.owner
        isor.owner = new_owner
        rpr = as_representer(iso_request, XmlMime)
        rpr_str = rpr.to_string(iso_request)
        isor.owner = old_owner
        self.assert_equal(isor.owner, old_owner)
        self.app.put(resource_to_url(iso_request),
                     params=rpr_str,
                     content_type=XmlMime.mime_type_string,
                     status=HTTPOk.code)
        self.assert_equal(isor.owner, new_owner)

