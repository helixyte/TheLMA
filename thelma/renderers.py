"""
TheLMA response renderers.
"""
from StringIO import StringIO
from everest.interfaces import IUserMessageNotifier
from everest.messaging import UserMessageHandlingContextManager
from everest.mime import ZipMime
from everest.renderers import ResourceRenderer
from everest.resources.interfaces import IResource
from everest.views.base import WarnAndResubmitUserMessageChecker
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.threadlocal import get_current_registry
from thelma.automation.tools import experiment
from thelma.automation.tools.experiment.batch import \
    ExperimentBatchWorklistWriter
from thelma.automation.tools.iso import lab
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
import logging
import transaction

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
        if self.__name == 'thelma+zip;type=ExperimentMember':
            rnd = ExperimentWorklistRenderer()
        elif self.__name == 'thelma+zip;type=IsoMember':
            rnd = IsoWorklistRenderer()
        elif self.__name == 'thelma+zip;type=IsoJobMember':
            rnd = IsoJobWorklistRenderer()
        else:
            raise ValueError('Unknown renderer for' + self.__name)
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

        checker = WarnAndResubmitUserMessageChecker()
        with UserMessageHandlingContextManager(checker):
            request = system['request']
            params = request.params
            stream = self.__create_experiment_worklist(resource, params)
        if not checker.vote is True:
            request.response = checker.create_307_response()
            result = None
        else:
            out_stream = StringIO()
            out_stream.write(stream.getvalue())
            result = out_stream.getvalue()
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
        zip_stream = tool.get_result()
        transaction.abort()
        warnings = tool.get_messages(logging.WARNING)
        if len(warnings) > 0:
            reg = get_current_registry()
            msg_notifier = reg.getUtility(IUserMessageNotifier)
            msg_notifier.notify(" -- ".join(warnings))
        if zip_stream == None:
            raise HTTPBadRequest(" --".join(tool.log.get_messages()))

        return zip_stream


class ZippedWorklistRenderer(CustomRenderer):
    def __init__(self):
        CustomRenderer.__init__(self, ZipMime)

    def _run_tool(self, tool, always_abort=True):
        zip_stream = tool.get_result()
        # FIXME: This is gross.
        # All the worklist generators simulate transfers to perform
        # consistency checks; we do not want any of these transfers to be
        # persisted.
        if always_abort or zip_stream is None:
            transaction.abort()
        warnings = tool.get_messages(logging.WARNING)
        if len(warnings) > 0:
            reg = get_current_registry()
            msg_notifier = reg.getUtility(IUserMessageNotifier)
            msg_notifier.notify(" -- ".join(warnings))
        if zip_stream is None:
            raise HTTPBadRequest(" --".join(tool.log.get_messages()))
        return zip_stream


class IsoJobWorklistRenderer(ZippedWorklistRenderer):

    def __call__(self, value, system):
        CustomRenderer.__call__(self, value, system)
        resource = value.get('context', system.get('context'))

        checker = WarnAndResubmitUserMessageChecker()
        with UserMessageHandlingContextManager(checker):
            request = system['request']
            params = request.params
            if params['type'] == 'XL20':
                stream = self.__create_xl20_worklist(resource, params)
            elif params['type'] == 'CONTROL_STOCK_TRANSFER':
                stream = self.__create_transfer_worklist(resource)
#            elif params['type'] == 'FILL_CONTROL_STOCK_RACKS':
#                stream = self.__fill_racks_for_testing(resource, request)
            else:
                raise HTTPBadRequest("Unknown work list type!").exception
        if not checker.vote is True:
            if params['type'] == 'XL20':
                transaction.abort()
            request.response = checker.create_307_response()
            result = None
        else:
            out_stream = StringIO()
            out_stream.write(stream.getvalue())
            result = out_stream.getvalue()
        return result

    def __create_xl20_worklist(self, resource, params):
        entity = resource.get_entity()
        barcode = params['rack']
        optimizer_excluded_racks = params['optimizer_excluded_racks']
        optimizer_required_racks = params['optimizer_required_racks']
        if len(optimizer_excluded_racks) > 0:
            optimizer_excluded_racks = optimizer_excluded_racks.split(',')
        else:
            optimizer_excluded_racks = None
        if len(optimizer_required_racks) > 0:
            optimizer_required_racks = optimizer_required_racks.split(',')
        else:
            optimizer_required_racks = None
        include_dummy_output = \
            params.get('include_dummy_output') == 'true'
        try:
            tool = lab.get_stock_rack_assembler(entity=entity,
                                    rack_barcodes=[barcode],
                                    excluded_racks=optimizer_excluded_racks,
                                    requested_tubes=optimizer_required_racks,
                                    include_dummy_output=include_dummy_output)
        except TypeError as te:
            raise HTTPBadRequest(str(te)).exception
        return self._run_tool(tool, always_abort=False)

    def __create_transfer_worklist(self, resource):
        entity = resource.get_entity()
        try:
            tool = lab.get_worklist_writer(entity=entity)
        except TypeError as te:
            raise HTTPBadRequest(str(te)).exception
        return self._run_tool(tool)


class IsoWorklistRenderer(ZippedWorklistRenderer):

    def __call__(self, value, system):
        CustomRenderer.__call__(self, value, system)
        resource = value.get('context', system.get('context'))
        request = system['request']
        params = request.params
        checker = WarnAndResubmitUserMessageChecker()
        with UserMessageHandlingContextManager(checker):
            if params['type'] == 'XL20':
                stream = self.__create_xl20_worklist_stream(resource, request)
            elif params['type'] == 'ISO_PROCESSING':
                stream = \
                    self.__create_iso_processing_worklist_stream(resource)
            else:
                raise HTTPBadRequest("Unknown work list type!").exception
        if not checker.vote is True:
            if params['type'] == 'XL20':
                transaction.abort()
            request.response = checker.create_307_response()
            result = None
        else:
            if not params['type'] == 'XL20':
                transaction.abort()
            out_stream = StringIO()
            out_stream.write(stream.getvalue())
            result = out_stream.getvalue()
        return result

    def __create_xl20_worklist_stream(self, resource, request):
        entity = resource.get_entity()
        params = request.params
        barcode1 = params['rack1']
        barcode2 = params['rack2']
        barcode3 = params['rack3']
        barcode4 = params['rack4']
        barcodes = [barcode1, barcode2, barcode3, barcode4]
        optimizer_excluded_racks = params['optimizer_excluded_racks']
        optimizer_required_racks = params['optimizer_required_racks']
        include_dummy_output = params.get('include_dummy_output') == 'true'
        if len(optimizer_excluded_racks) > 0:
            optimizer_excluded_racks = optimizer_excluded_racks.split(',')
        else:
            optimizer_excluded_racks = None
        if len(optimizer_required_racks) > 0:
            optimizer_required_racks = optimizer_required_racks.split(',')
        else:
            optimizer_required_racks = None

        del entity.iso_sample_stock_racks[:]
        del entity.iso_sector_stock_racks[:]
        try:
            tool = lab.get_stock_rack_assembler(entity=entity,
                        rack_barcodes=barcodes,
                        excluded_racks=optimizer_excluded_racks,
                        requested_tubes=optimizer_required_racks,
                        include_dummy_output=include_dummy_output)
        except TypeError as te:
            raise HTTPBadRequest(str(te)).exception
        return self._run_tool(tool, always_abort=False)

    def __create_iso_processing_worklist_stream(self, resource):
        entity = resource.get_entity()
        try:
            tool = lab.get_worklist_writer(entity=entity)
        except TypeError as te:
            raise HTTPBadRequest(str(te)).exception
        return self._run_tool(tool)
