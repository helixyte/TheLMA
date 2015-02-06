"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

TheLMA response renderers.
"""
import os

from pyramid.compat import bytes_
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.interfaces import IRenderer

from everest.mime import HtmlMime
from everest.mime import ZipMime
from everest.renderers import ResourceRenderer
from everest.resources.interfaces import IResource
from everest.views.base import WarnAndResubmitExecutor
from thelma.mime import ExperimentZippedWorklistMime
from thelma.mime import IsoJobZippedWorklistMime
from thelma.mime import IsoZippedWorklistMime
from thelma.tools.iso import lab
from thelma.utils import run_tool
from zope.interface import implementer # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401


__docformat__ = "reStructuredText en"
__all__ = ['ThelmaRendererFactory',
           'CustomRenderer',
           'ExperimentWorklistRenderer',
           'LouiceServiceRenderer',
           'ZippedWorklistRenderer',
           'IsoJobWorklistRenderer',
           'IsoWorklistRenderer']


class ThelmaRendererFactory(object):
    def __init__(self, info):
        self.__name = info.name

    def __call__(self, value, system):
        if self.__name == 'louice':
            rnd = LouiceServiceRenderer()
        elif self.__name == ExperimentZippedWorklistMime.mime_type_string:
            rnd = ExperimentWorklistRenderer()
        elif self.__name == IsoZippedWorklistMime.mime_type_string:
            rnd = IsoWorklistRenderer()
        elif self.__name == IsoJobZippedWorklistMime.mime_type_string:
            rnd = IsoJobWorklistRenderer()
        else:
            raise ValueError('No renderer available for ' + self.__name)
        return rnd(value, system)


@implementer(IRenderer)
class LouiceServiceRenderer(object):
    """
    Renderer for the LOUICe service (root) object.
    """
    def __call__(self, value, system):
        request = system['request']
        public_dir = request.registry.settings['public_dir']
        client_html = os.path.join(public_dir, 'LOUICe.html')
        request.response.content_type = HtmlMime.mime_type_string
        return bytes_(open(client_html, 'rb').read(), 'utf8')


class CustomRenderer(ResourceRenderer):
    """
    Base class for custom renderers.
    """
    def __call__(self, value, system):
        context = value.get('context', system.get('context'))
        if not IResource in provided_by(context):
            raise ValueError('Context is not a resource.')
        if not self._validate(context):
            raise ValueError('Invalid representation.')
        self._prepare_response(system)
        # Extract options from parameters.
        resource = value.get('context', system.get('context'))
        request = system['request']
        params = request.params
        options = self._extract_from_params(params)
        # Wrap execution of the _run method.
        create_exec = WarnAndResubmitExecutor(self._run)
        result = create_exec(resource, options)
        if create_exec.do_continue:
            result = self._handle_success(request, result)
        else:
            request.response = result
            request.response.headers['x-tm'] = 'abort'
            result = None
        return result

    def _validate(self, value):
        return IResource in  provided_by(value)

    def _prepare_response(self, system):
        request = system['request']
        request.response_content_type = self._format
#        context = system['context']
#        if context.cache_for is not None:
#            request.response_cache_for = context.cache_for

    def _run(self, resource, options):
        raise NotImplementedError('Abstract method.')

    def _extract_from_params(self, params):
        raise NotImplementedError('Abstract method.')

    def _handle_success(self, request, result):
        raise NotImplementedError('Abstract method.')


class ExperimentWorklistRenderer(CustomRenderer):
    """
    Custom renderer for experiment (transfection) worklists.
    """
    def __init__(self):
        CustomRenderer.__init__(self, ZipMime)

    def __call__(self, value, system):
        result = CustomRenderer.__call__(self, value, system)
        # We always want to roll back all changes.
        request = system['request']
        request.response.headers['x-tm'] = 'abort'
        return result

    def _run(self, resource, options):
        if options['type'] == 'ALL_WITH_ROBOT':
            tool = resource.experiment_job.get_writer()
        elif options['type'] == 'ROBOT':
            try:
                tool = resource.get_writer()
            except TypeError as te:
                raise HTTPBadRequest(str(te)).exception
        return run_tool(tool)

    def _extract_from_params(self, params):
        return params

    def _handle_success(self, request, result):
        return result.getvalue()


class ZippedWorklistRenderer(CustomRenderer):
    """
    Custom renderer for zipped worklists.
    """
    def __init__(self):
        CustomRenderer.__init__(self, ZipMime)

    def _extract_from_params(self, params):
        wl_type = params['type']
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
        options = dict(worklist_type=wl_type,
                       excluded_racks=optimizer_excluded_racks,
                       requested_tubes=optimizer_requested_tubes,
                       include_dummy_output=include_dummy_output)
        if wl_type == 'XL20':
            options['rack_barcodes'] = \
                        self._extract_stock_rack_barcodes(params)
        return options

    def _run(self, resource, options):
        wl_type = options.pop('worklist_type')
        if wl_type == 'XL20':
            stream = self.__create_xl20_worklist_stream(resource, options)
        elif wl_type == 'PIPETTING':
            stream = self.__create_pipetting_worklist_stream(resource)
        else:
            raise HTTPBadRequest("Unknown work list type (%s)!" % wl_type)
        return stream

    def _handle_success(self, request, result):
        # The transfer worklist writers simulate the transfers; we
        # do not want to commit them just yet.
        if not request.params['type'] == 'XL20':
            request.response.headers['x-tm'] = 'abort'
        return result.getvalue()

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
            # We must have at least one barcode.
            bcs = [params['rack1']]
            for key in ('rack2', 'rack3', 'rack4'):
                bc = params.get(key)
                if not bc is None:
                    bcs.append(bc)
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
    """
    Custom renderer for zipped ISO job worklists.
    """
    def _prepare_for_xl20_worklist_creation(self, entity):
        while len(entity.iso_job_stock_racks) > 0:
            stock_rack = entity.iso_job_stock_racks.pop()
            self._delete_stock_rack(stock_rack)


class IsoWorklistRenderer(ZippedWorklistRenderer):
    """
    Custom renderer for zipped ISO worklists.
    """
    def _prepare_for_xl20_worklist_creation(self, entity):
        for sr in entity.iso_stock_racks[:]:
            self._delete_stock_rack(sr)
            entity.iso_stock_racks.remove(sr)
        for sr in entity.iso_sector_stock_racks[:]:
            self._delete_stock_rack(sr)
            entity.iso_sector_stock_racks.remove(sr)
