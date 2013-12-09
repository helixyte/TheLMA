"""
Functional tests for the IsoRequest resource.

Created on Nov 26, 2013.
"""
from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.entities.utils import get_root_aggregate
from everest.mime import XlsMime
from everest.mime import XmlMime
from everest.mime import ZipMime
from everest.repositories.rdb.testing import RdbContextManager
from everest.representers.config import IGNORE_OPTION
from everest.representers.config import WRITE_AS_LINK_OPTION
from everest.representers.utils import UpdatedRepresenterConfigurationContext
from everest.representers.utils import as_representer
from everest.resources.attributes import get_resource_class_attributes
from everest.resources.interfaces import IService
from everest.resources.staging import create_staging_collection
from everest.resources.utils import resource_to_url
from everest.resources.utils import url_to_resource
from pkg_resources import resource_filename # pylint: disable=E0611
from pyramid.compat import string_types
from pyramid.httpexceptions import HTTPCreated
from pyramid.httpexceptions import HTTPOk
from pyramid.httpexceptions import HTTPTemporaryRedirect
from pyramid.testing import DummyRequest
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.semiconstants import get_item_status_managed
from thelma.automation.semiconstants import get_rack_position_from_indices
from thelma.interfaces import IExperimentMetadata
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import IOrganization
from thelma.interfaces import IRack
from thelma.interfaces import IRackSpecs
from thelma.interfaces import IStockSample
from thelma.interfaces import ISubproject
from thelma.models.experiment import ExperimentMetadata
from thelma.models.iso import LabIso
from thelma.models.racklayout import RackLayout
from thelma.testing import ThelmaFunctionalTestCase
from thelma.tests.tools.iso.lab.utils import LAB_ISO_TEST_CASES
import os
from thelma.interfaces import ITubeRack
from everest.querying.specifications import eq

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
        self.__session = None

    def test_workflow(self):
        with RdbContextManager() as session:
            self.__session = session
            # Step 0: Create candidate samples.
            self._create_iso_candidates()
            session.commit()
            # Step 1: Upload metadata.
            emd_url = self._upload_metadata(
                                    LAB_ISO_TEST_CASES.CASE_NO_JOB_DIRECT)
            session.commit()
            # Step 2: Accept ISO request.
            emd = url_to_resource(emd_url)
            self._accept_iso_request(emd.iso_request)
            session.commit()
            # Step 3: Generate ISOs.
            self._generate_isos(emd.iso_request)
            session.commit()
            # Step 4: Generate XL20 worklist.
            iso = next(iter(emd.iso_request.isos))
            if emd.iso_request.process_job_first:
                self._create_xl20_worklist_for_iso_job(iso.iso_job)
            self._create_xl20_worklist_for_iso(iso)

    def _create_xl20_worklist_for_iso_job(self, iso_job):
        pass

    def _create_xl20_worklist_for_iso(self, iso):
        params = self.__get_empty_rack_barcode_params(4)
        params['type'] = 'XL20'
        params['include_dummy_output'] = 'true'
        res = self.app.get("%sworklists.zip" % resource_to_url(iso),
                           params=params,
                           headers=dict(accept=ZipMime.mime_type_string),
#                           status=HTTPOk.code
                           )
        self.assert_is_not_none(res)

    def _create_iso_candidates(self):
        ss_agg = get_root_aggregate(IStockSample)
        rack_agg = get_root_aggregate(IRack)
        tube_bc = 9000000000
        vol = 1e-4
        row_idx = 0
        col_idx = 0
        tube_rack = \
            self._create_tube_rack(label='test_iso_candidates',
                                   specs=self._get_entity(IRackSpecs,
                                                          'matrix0500'),
                                   status=get_item_status_managed())
        rack_agg.add(tube_rack)
        spl = self._get_entity(IOrganization, 'ambion')
        for mdp_id in [205201, 330001, 333803, 1056000, 180005]:
            tube = self._create_tube(barcode=str(tube_bc),
                                     status=get_item_status_managed())
            col_idx += 1
            tube_bc += 1
            tube_rack.add_tube(
                        tube,
                        get_rack_position_from_indices(row_idx, col_idx))
            mdp = self._get_entity(IMoleculeDesignPool, str(mdp_id))
            ss = self._create_stock_sample(
                            volume=vol,
                            container=tube,
                            molecule_design_pool=mdp,
                            supplier=spl,
                            molecule_type=mdp.molecule_type,
                            concentration=mdp.default_stock_concentration)
            ss_agg.add(ss)

    def _upload_metadata(self, case_name):
        # First, create a new metadata entity and POST it.
        emd_coll = create_staging_collection(IExperimentMetadata)
        esc = LAB_ISO_TEST_CASES.get_experiment_scenario(case_name)
        emd = ExperimentMetadata('unit_test_metadata',
                                 next(iter(get_root_aggregate(ISubproject))),
                                 1,
                                 esc
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
        patch_rpr = \
            self.__get_representation_from_file('accept_iso_request.xml')
#            self.__make_accept_iso_request_patch_representation(iso_request)
        self.app.patch(resource_to_url(iso_request),
                       params=patch_rpr,
                       content_type=XmlMime.mime_type_string,
                       status=HTTPOk.code)

    def _generate_isos(self, iso_request):
        patch_rpr = \
            self.__get_representation_from_file('generate_isos.xml')
#            self.__make_generate_isos_patch_representation(iso_request)
        self.app.patch(resource_to_url(iso_request),
                       params=patch_rpr,
                       content_type=XmlMime.mime_type_string,
                       status=HTTPOk.code
                       )
        self.assert_equal(len(iso_request.get_entity().isos), 1)

    def __get_representation_from_file(self, filename):
        fn = resource_filename(self.__class__.__module__,
                               os.path.join('data', filename))
        return open(fn, 'rb').read()

    def __make_accept_iso_request_patch_representation(self, iso_request):
        new_owner = 'thelma, stockmanagement'
        isor = iso_request.get_entity()
        old_owner = isor.owner
        isor.owner = new_owner
        rpr = as_representer(iso_request, XmlMime)
        with self.__get_patch_context(iso_request, ('owner',)):
            rpr_str = rpr.to_string(iso_request)
        isor.owner = old_owner
        self.assert_equal(isor.owner, old_owner)
        return rpr_str

    def __make_generate_isos_patch_representation(self, iso_request):
        isor = iso_request.get_entity()
        # FIXME: This status should be part of the ISO_STATUS const group.
        iso = LabIso('NEW ISO', 0,
                     rack_layout=RackLayout(shape=get_96_rack_shape()),
                     iso_request=isor,
                     status='NEW')
        isor.isos.append(iso)
        rpr = as_representer(iso_request, XmlMime)
        patch_ctxt = self.__get_patch_context(iso_request,
                                              ('isos', ('isos', 'status')))
        with patch_ctxt:
            rpr_str = rpr.to_string(iso_request)
        return rpr_str

    def __get_patch_context(self, rc, attributes):
        # Use this to create am XML representation of the given resource
        # which *only* contains the given attributes (useful for PATCHing).
        attr_map = get_resource_class_attributes(rc)
        cfg_opts = dict([((attr_name,), {IGNORE_OPTION:True})
                         for attr_name in attr_map])
        for attr_key in attributes:
            attr_cfg_opts = {IGNORE_OPTION:False}
            if isinstance(attr_key, string_types):
                key = (attr_key,)
                attr = attr_map[attr_key]
                if not attr.kind == RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
                    attr_cfg_opts[WRITE_AS_LINK_OPTION] = False
                    # Disable nested attributes.
                    # FIXME: This should be recursive.
                    for attr_attr_name in \
                            get_resource_class_attributes(attr.attr_type):
                        cfg_opts[(attr_key, attr_attr_name)] = \
                                                    {IGNORE_OPTION:True}
            else:
                key = attr_key
            cfg_opts[key] = attr_cfg_opts
        return UpdatedRepresenterConfigurationContext(type(rc),
                                                      XmlMime,
                                                      attribute_options=
                                                                    cfg_opts)

    def __get_empty_rack_barcode_params(self, count):
        rack_agg = get_root_aggregate(ITubeRack)
        rack_agg.filter = eq(total_containers=0,
                             specs=self._get_entity(IRackSpecs, 'matrix0500'))
        rack_agg.slice = slice(0, count)
        if count == 1:
            params = dict(rack=next(rack_agg.iterator()).barcode)
        else:
            params = dict([('rack%d' % (cnt + 1,), rack.barcode)
                           for (cnt, rack) in enumerate(rack_agg.iterator())])
        return params
