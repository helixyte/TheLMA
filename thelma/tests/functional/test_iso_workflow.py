"""
Functional tests for the IsoRequest resource.

Created on Nov 26, 2013.
"""
import os

from pkg_resources import resource_filename # pylint: disable=E0611
from pyramid.compat import NativeIO
from pyramid.compat import string_types
from pyramid.httpexceptions import HTTPCreated
from pyramid.httpexceptions import HTTPOk
from pyramid.httpexceptions import HTTPTemporaryRedirect
import pytest

from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.entities.utils import get_root_aggregate
from everest.mime import XlsMime
from everest.mime import XmlMime
from everest.mime import ZipMime
from everest.querying.specifications import eq
from everest.repositories.interfaces import IRepositoryManager
from everest.representers.config import IGNORE_OPTION
from everest.representers.config import WRITE_AS_LINK_OPTION
from everest.representers.utils import UpdatedRepresenterConfigurationContext
from everest.representers.utils import as_representer
from everest.resources.attributes import get_resource_class_attributes
from everest.resources.staging import create_staging_collection
from everest.resources.utils import resource_to_url
from everest.resources.utils import url_to_resource
from thelma.automation.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.semiconstants import get_item_status_managed
from thelma.automation.semiconstants import get_rack_position_from_indices
from thelma.automation.tools.iso.lab.planner import LabIsoPlanner
from thelma.automation.tools.worklists.tubehandler import XL20Executor
from thelma.automation.tools.writers import read_zip_archive
from thelma.interfaces import IExperimentMetadata
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import IRack
from thelma.interfaces import IStockSample
from thelma.interfaces import ISubproject
from thelma.interfaces import ITubeRack
from thelma.models.experiment import ExperimentMetadata
from thelma.models.iso import LabIso
from thelma.models.racklayout import RackLayout
from thelma.models.utils import get_current_user
from thelma.tests.functional.conftest import TestFunctionalBase
from thelma.automation.semiconstants import get_experiment_metadata_type


__docformat__ = 'reStructuredText en'
__all__ = ['TestIsoWorkflow',
           ]


class TestIsoWorkflow(TestFunctionalBase):
    setup_rdb_context = True
    __session = None

    @pytest.mark.parametrize(
        'xls_filename,scenario',
        [(resource_filename('thelma.tests.functional',
                            os.path.join('data',
                                         'association_direct.xls')),
          EXPERIMENT_SCENARIOS.SCREENING)])
    def test_workflow(self, app_creator, tube_rack_specs_matrix,
#                      tube_rack_fac, tube_fac, item_status_managed,
#                      organization_cenix, stock_sample_fac,
                      xls_filename, scenario, monkeypatch):
        repo_mgr = \
            app_creator.config.get_registered_utility(IRepositoryManager)
        repo = repo_mgr.get_default()
        self.__session = repo.session_factory()
        # Step 0: Create candidate samples.
#        self._create_iso_candidates(tube_rack_fac, tube_rack_specs_matrix,
#                                    tube_fac, item_status_managed,
#                                    organization_cenix, stock_sample_fac)
        # Step 1: Upload metadata.
        emd_url = self._upload_metadata(xls_filename, scenario, app_creator)
        # Step 2: Accept ISO request.
        emd = url_to_resource(emd_url)
        self._accept_iso_request(emd.iso_request, app_creator)
        # Step 3: Generate ISOs.
        # We need to temporarily reduce the threshold that controls
        # when to use the Cybio.
        monkeypatch.setattr(LabIsoPlanner, '_MIN_CYBIO_TRANSFER_NUMBER', 6)
        self._generate_isos(emd.iso_request, app_creator)
        # Step 4: Process ISO jobs (if needed).
        if emd.iso_request.process_job_first:
            for iso_job in emd.iso_request.iso_jobs:
                if iso_job.number_stock_racks == 0:
                    continue
                patch_body = \
                    self.__get_representation_from_file(
                                'transfer_to_iso_job.xml') % iso_job.id
#                    self.__make_transfer_to_patch_representation(
#                                                  emd.iso_request,
#                                                  'iso_jobs')
                self._process_iso_or_iso_job(iso_job, emd.iso_request,
                                             1, patch_body, app_creator,
                                             tube_rack_specs_matrix)
        # Step 5: Process ISOs.
        for iso_job in emd.iso_request.iso_jobs:
            for iso in iter(iso_job.isos):
                patch_body = \
                  self.__get_representation_from_file(
                                        'transfer_to_iso.xml') % iso.id
#                  self.__make_transfer_to_patch_representation(
#                                                    emd.iso_request,
#                                                    'isos')
                self._process_iso_or_iso_job(iso, emd.iso_request,
                                             4, patch_body, app_creator,
                                             tube_rack_specs_matrix)

    def _create_iso_candidates(self, tube_rack_fac, tube_rack_specs_matrix,
                               tube_fac, item_status_managed,
                               organization_cenix, stock_sample_fac):
        ss_agg = get_root_aggregate(IStockSample)
        rack_agg = get_root_aggregate(IRack)
        tube_bc = 9000000000
        vol = 1e-4
        row_idx = 0
        col_idx = 0
        tube_rack = tube_rack_fac(label='test_iso_candidates',
                                  specs=tube_rack_specs_matrix,
                                  status=get_item_status_managed())
        rack_agg.add(tube_rack)
        mdp_agg = get_root_aggregate(IMoleculeDesignPool)
        for mdp_id in [288282, 3349397, 3430173, 1139866, 199937]:
            tube = tube_fac(barcode=str(tube_bc),
                            status=item_status_managed)
            col_idx += 1
            tube_bc += 1
            tube_rack.add_tube(
                        tube,
                        get_rack_position_from_indices(row_idx, col_idx))
            mdp = mdp_agg.get_by_id(mdp_id)
            ss = stock_sample_fac(
                            volume=vol,
                            container=tube,
                            molecule_design_pool=mdp,
                            supplier=organization_cenix,
                            molecule_type=mdp.molecule_type,
                            concentration=mdp.default_stock_concentration)
            ss_agg.add(ss)

    def _upload_metadata(self, xls_filename, scenario, app):
        # First, create a new metadata entity and POST it.
        emd_coll = create_staging_collection(IExperimentMetadata)
        emd = ExperimentMetadata('unit_test_metadata',
                                 next(iter(get_root_aggregate(ISubproject))),
                                 1,
                                 get_experiment_metadata_type(scenario)
                                 )
        mb_emd = emd_coll.create_member(emd)
        rpr = as_representer(mb_emd, XmlMime)
        emd_rpr = rpr.to_string(mb_emd)
        res = app.post("/%s" % emd_coll.__name__,
                       params=emd_rpr,
                       content_type=XmlMime.mime_type_string,
                       status=HTTPCreated.code)
        self.__session.commit()
        mb_url = res.headers['Location']
        # Now, PUT the excel meta data file.
        self.__session.begin_nested()
        with open(xls_filename, 'rb') as xls_file:
            res = app.put(mb_url,
                          params=xls_file.read(),
                          content_type=XlsMime.mime_type_string)
        # If the file had warnings, we have to repeat the PUT.
        if res.status.endswith(HTTPTemporaryRedirect.title):
            self.__session.rollback()
            # 307 Redirect: Repeat with warnings disabled.
            with open(xls_filename, 'rb') as xls_file:
                res = app.put(res.headers['Location'],
                              params=xls_file.read(),
                              content_type=XlsMime.mime_type_string,
                              status=HTTPOk.code)
        self.__session.commit()
        assert res.status.endswith(HTTPOk.title)
        return mb_url

    def _accept_iso_request(self, iso_request, app):
        patch_rpr = \
            self.__get_representation_from_file('accept_iso_request.xml')
#            self.__make_accept_iso_request_patch_representation(iso_request)
        app.patch(resource_to_url(iso_request),
                  params=patch_rpr,
                  content_type=XmlMime.mime_type_string,
                  status=HTTPOk.code)

    def _generate_isos(self, iso_request, app):
        patch_rpr = \
            self.__get_representation_from_file('generate_isos.xml')
#            self.__make_generate_isos_patch_representation(iso_request)
        self.__session.begin_nested()
        res = app.patch(resource_to_url(iso_request),
                        params=patch_rpr,
                        content_type=XmlMime.mime_type_string)
        # If the request triggered warnings, we have to repeat the PUT.
        if res.status.endswith(HTTPTemporaryRedirect.title):
            self.__session.rollback()
            # 307 Redirect: Repeat with warnings disabled.
            app.patch(res.headers['Location'],
                      params=patch_rpr,
                      content_type=XmlMime.mime_type_string,
                      status=HTTPOk.code)
            assert len(iso_request.get_entity().isos) > 0
        self.__session.commit()

    def _process_iso_or_iso_job(self, iso_or_iso_job, iso_request,
                                num_barcodes, patch_body,
                                app, tube_rack_specs_matrix):
        # Create XL20 worklist.
        barcodes = \
            self.__get_empty_rack_barcode_params(num_barcodes,
                                                 tube_rack_specs_matrix)
        dummy_wl = self._create_xl20_worklist(iso_or_iso_job, barcodes, app)
        assert not dummy_wl is None
        # Intermediate step: Run XL20 worklist output to move tubes.
        self._run_xl20_executor(dummy_wl)
        # Get processing worklist.
        self.__session.begin_nested()
        zip_map = self._create_processing_worklist(iso_or_iso_job, dict(),
                                                   app)
        assert not zip_map is None
        self.__session.rollback()
        # Execute worklist.
        res = app.patch(resource_to_url(iso_request),
                        params=patch_body,
                        content_type=XmlMime.mime_type_string,
                        status=HTTPOk.code)
        assert not res is None
        self.__session.commit()

    def _create_xl20_worklist(self, rc, params, app):
        params['type'] = 'XL20'
        params['include_dummy_output'] = 'true'
        res = app.get("%sworklists.zip" % resource_to_url(rc),
                      params=params,
                      headers=dict(accept=ZipMime.mime_type_string),
                      status=HTTPOk.code
                      )
        assert not res is None
        # Extract the dummy output worklist from the returned ZIP file.
        zip_map = read_zip_archive(NativeIO(res.body))
        return zip_map['%s_dummy_xl20_output.tpo' % rc.label]

    def _run_xl20_executor(self, worklist):
        user = get_current_user()
        tool = XL20Executor(worklist, user)
        tool.run()
        assert not tool.has_errors()
        self.__session.commit()

    def _create_processing_worklist(self, rc, params, app):
        params['type'] = 'PIPETTING'
        res = app.get("%sworklists.zip" % resource_to_url(rc),
                      params=params,
                      headers=dict(accept=ZipMime.mime_type_string),
#                      status=HTTPOk.code
                      )
        assert not res is None
        zip_map = read_zip_archive(NativeIO(res.body))
        return zip_map

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
        assert isor.owner == old_owner
        return rpr_str

    def __make_generate_isos_patch_representation(self, iso_request):
        isor = iso_request.get_entity()
        # FIXME: The status should be part of the ISO_STATUS const group.
        iso = LabIso('NEW ISO',
                     0,
                     RackLayout(shape=get_96_rack_shape()),
                     iso_request=isor,
                     status='NEW')
        isor.isos.append(iso)
        rpr = as_representer(iso_request, XmlMime)
        patch_ctxt = self.__get_patch_context(iso_request,
                                              ('isos', ('isos', 'status')))
        with patch_ctxt:
            rpr_str = rpr.to_string(iso_request)
        return rpr_str

    def __make_transfer_to_patch_representation(self, iso_request,
                                                attribute):
        # This creates a representation with all isos or iso
        isor_ent = iso_request.get_entity()
        # FIXME: The status should be part of the ISO_STATUS const group.
        for ent in getattr(isor_ent, attribute):
            ent.status = 'PIPETTING'
        rpr = as_representer(iso_request, XmlMime)
        patch_ctxt = self.__get_patch_context(iso_request,
                                              (attribute,
                                               (attribute, 'status'),
                                               (attribute, 'id')
                                               )
                                              )
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
                rc_attr = attr_map[attr_key]
                if not rc_attr.kind == RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
                    attr_cfg_opts[WRITE_AS_LINK_OPTION] = False
                    # Disable nested attributes.
                    # FIXME: This should be recursive.
                    for attr_attr_name in \
                            get_resource_class_attributes(rc_attr.attr_type):
                        cfg_opts[(attr_key, attr_attr_name)] = \
                                                    {IGNORE_OPTION:True}
            else:
                key = attr_key
            cfg_opts[key] = attr_cfg_opts
        return UpdatedRepresenterConfigurationContext(type(rc),
                                                      XmlMime,
                                                      attribute_options=
                                                                    cfg_opts)

    def __get_empty_rack_barcode_params(self, count, tube_rack_specs_matrix):
        rack_agg = get_root_aggregate(ITubeRack)
        rack_agg.filter = eq(total_containers=0, specs=tube_rack_specs_matrix)
        rack_agg.slice = slice(0, count)
        if count == 1:
            params = dict(rack=str(next(rack_agg.iterator()).barcode))
        else:
            params = dict([('rack%d' % (cnt + 1,), str(rack.barcode))
                           for (cnt, rack) in enumerate(rack_agg.iterator())])
        return params
