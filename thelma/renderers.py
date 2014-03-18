"""
TheLMA response renderers.
"""
from pyramid.httpexceptions import HTTPBadRequest

from everest.mime import ZipMime
from everest.renderers import ResourceRenderer
from everest.resources.interfaces import IResource
from everest.views.base import WarnAndResubmitExecutor
from thelma.automation.tools import experiment
from thelma.automation.tools.experiment.batch import \
    ExperimentBatchWorklistWriter
from thelma.automation.tools.iso import lab
from thelma.mime import ExperimentZippedWorklistMime
from thelma.mime import IsoJobZippedWorklistMime
from thelma.mime import IsoZippedWorklistMime
from thelma.utils import run_tool
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401


__docformat__ = "reStructuredText en"
__all__ = ['ThelmaRendererFactory',
           'CustomRenderer',
           'ExperimentWorklistRenderer',
           'ZippedWorklistRenderer',
           'IsoJobWorklistRenderer',
           'IsoWorklistRenderer']


class ThelmaRendererFactory(object):
    def __init__(self, info):
        self.__name = info.name

    def __call__(self, value, system):
        if self.__name == ExperimentZippedWorklistMime.mime_type_string:
            rnd = ExperimentWorklistRenderer()
        elif self.__name == IsoZippedWorklistMime.mime_type_string:
            rnd = IsoWorklistRenderer()
        elif self.__name == IsoJobZippedWorklistMime.mime_type_string:
            rnd = IsoJobWorklistRenderer()
        else:
            raise ValueError('No renderer available for ' + self.__name)
        return rnd(value, system)


class CustomRenderer(ResourceRenderer):
    def __call__(self, value, system):
        context = value.get('context', system.get('context'))
        if not IResource in provided_by(context):
            raise ValueError('Context is not a resource.')
        if not self._validate(context):
            raise ValueError('Invalid representation.')
        self._prepare_response(system)

    def _validate(self, value):
        return IResource in  provided_by(value)

    def _prepare_response(self, system):
        request = system['request']
        request.response_content_type = self._format
#        context = system['context']
#        if context.cache_for is not None:
#            request.response_cache_for = context.cache_for


class ExperimentWorklistRenderer(CustomRenderer):
    def __init__(self):
        CustomRenderer.__init__(self, ZipMime)

    def __call__(self, value, system):
        CustomRenderer.__call__(self, value, system)
        resource = value.get('context', system.get('context'))
        request = system['request']
        params = request.params
        creat_exec = \
            WarnAndResubmitExecutor(self.__create_experiment_worklist)
        # We always want to roll back all changes.
        request.response.headers['x-tm'] = 'abort'
        result = creat_exec(resource, params)
        if creat_exec.do_continue:
            result = result.getvalue()
        return result

    def __create_experiment_worklist(self, resource, params):
        entity = resource.get_entity()
        if params['type'] == 'ALL_WITH_ROBOT':
            tool = ExperimentBatchWorklistWriter([entity.job])
        elif params['type'] == 'ROBOT':
            try:
                tool = experiment.get_writer(experiment=entity)
            except TypeError as te:
                raise HTTPBadRequest(str(te)).exception
        return run_tool(tool)


class ZippedWorklistRenderer(CustomRenderer):
    def __init__(self):
        CustomRenderer.__init__(self, ZipMime)

    def __call__(self, value, system):
        CustomRenderer.__call__(self, value, system)
        resource = value.get('context', system.get('context'))
        request = system['request']
        params = request.params
        options = self._extract_from_params(params)
        wl_type = params['type']
        if wl_type == 'XL20':
            options['rack_barcodes'] = \
                        self._extract_stock_rack_barcodes(params)
        create_exec = WarnAndResubmitExecutor(self.__create_worklist_stream)
        result = create_exec(resource, options, wl_type)
        if not create_exec.do_continue:
            request.response = result
            result = None
            request.response.headers['x-tm'] = 'abort'
        else:
            result = result.getvalue()
            if not wl_type == 'XL20':
                # The transfer worklist writers simulate the transfers; we
                # do not want to commit them just yet.
                request.response.headers['x-tm'] = 'abort'
        return result

    def _extract_from_params(self, params):
        optimizer_excluded_racks = params.get('optimizer_excluded_racks', '')
        optimizer_requested_tubes = params.get('optimizer_requested_tubes', '')
        if len(optimizer_excluded_racks) > 0:
            optimizer_excluded_racks = optimizer_excluded_racks.split(',')
        else:
            optimizer_excluded_racks = None
        if len(optimizer_requested_tubes) > 0:
            optimizer_requested_tubes = optimizer_requested_tubes.split(',')
        else:
            optimizer_requested_tubes = None
        include_dummy_output = params.get('include_dummy_output') == 'true'
        return dict(excluded_racks=optimizer_excluded_racks,
                    requested_tubes=optimizer_requested_tubes,
                    include_dummy_output=include_dummy_output)

    def __create_worklist_stream(self, resource, options, worklist_type):
        if worklist_type == 'XL20':
            stream = self.__create_xl20_worklist_stream(resource, options)
        elif worklist_type == 'PIPETTING':
            stream = self.__create_pipetting_worklist_stream(resource)
        else:
            raise HTTPBadRequest("Unknown work list type!")
        return stream

    def __create_xl20_worklist_stream(self, resource, options):
        entity = resource.get_entity()
#        self._prepare_for_xl20_worklist_creation(entity)
        try:
            tool = lab.get_stock_rack_assembler(entity=entity,
                                                **options)
        except TypeError as te:
            raise HTTPBadRequest(str(te))
        return run_tool(tool)

    def __create_pipetting_worklist_stream(self, resource):
        entity = resource.get_entity()
        try:
            tool = lab.get_worklist_writer(entity=entity)
        except TypeError as te:
            raise HTTPBadRequest(str(te))
        return run_tool(tool)

    def _extract_stock_rack_barcodes(self, params):
        if params.has_key('rack'):
            bcs = [params['rack']]
        else:
            barcode1 = params['rack1']
            barcode2 = params['rack2']
            barcode3 = params['rack3']
            barcode4 = params['rack4']
            bcs = [barcode1, barcode2, barcode3, barcode4]
        return bcs

    def _prepare_for_xl20_worklist_creation(self, entity):
        raise NotImplementedError('Abstract method.')

    def _delete_stock_rack(self, stock_rack):
        # This is awkward - should be done by appropriate cascade settings
        # in the backend.
        if not stock_rack.worklist_series is None:
            for wls in stock_rack.worklist_series:
                while len(wls.executed_worklists) > 0:
                    wls.executed_worklists.pop()


class IsoJobWorklistRenderer(ZippedWorklistRenderer):
    def _prepare_for_xl20_worklist_creation(self, entity):
        while len(entity.iso_job_stock_racks) > 0:
            stock_rack = entity.iso_job_stock_racks.pop()
            self._delete_stock_rack(stock_rack)


class IsoWorklistRenderer(ZippedWorklistRenderer):
    def _prepare_for_xl20_worklist_creation(self, entity):
        for sr in entity.iso_stock_racks[:]:
            self._delete_stock_rack(sr)
            entity.iso_stock_racks.remove(sr)
        for sr in entity.iso_sector_stock_racks[:]:
            self._delete_stock_rack(sr)
            entity.iso_sector_stock_racks.remove(sr)
