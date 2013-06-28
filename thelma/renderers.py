"""
TheLMA response renderers.
"""
from StringIO import StringIO
from everest.interfaces import IUserMessageNotifier
from everest.messaging import UserMessageHandlingContextManager
from everest.mime import ZipMime
from everest.renderers import ResourceRenderer
from everest.resources.interfaces import IResource
from everest.views.base import ViewUserMessageChecker
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.threadlocal import get_current_registry
from thelma.automation.tools.experiment.batch import \
    ExperimentBatchWorklistWriter
from thelma.automation.tools.experiment.writer import \
    ExperimentWorklistWriterOptimisation
from thelma.automation.tools.experiment.writer import \
    ExperimentWorklistWriterScreening
from thelma.automation.tools.iso.aliquot import IsoAliquotWorklistWriter
from thelma.automation.tools.iso.isoprocessing \
    import IsoProcessingWorklistWriter
from thelma.automation.tools.iso.stocktransfer \
    import IsoControlStockRackWorklistWriter
from thelma.automation.tools.iso.stocktransfer \
    import IsoSampleStockRackWorklistWriter
from thelma.automation.tools.iso.tubehandler import \
    IsoXL20WorklistGenerator384Controls
from thelma.automation.tools.iso.tubehandler import \
    IsoXL20WorklistGenerator384Samples
from thelma.automation.tools.iso.tubehandler import \
    IsoXL20WorklistGenerator96
from thelma.models.experiment import EXPERIMENT_METADATA_TYPES
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

        checker = ViewUserMessageChecker()
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
            if entity.experiment_design.experiment_metadata.is_type(
                                                EXPERIMENT_METADATA_TYPES.OPTI):
                tool = ExperimentWorklistWriterOptimisation(experiment=entity)
            else:
                tool = ExperimentWorklistWriterScreening(experiment=entity)
        else:
            raise HTTPBadRequest("Unknown work list type!").exception
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

        checker = ViewUserMessageChecker()
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
        tool = IsoXL20WorklistGenerator384Controls(iso_job=entity,
                                     destination_rack_barcode=barcode,
                                     excluded_racks=optimizer_excluded_racks,
                                     requested_tubes=optimizer_required_racks,
                                     include_dummy_output=include_dummy_output)
        return self._run_tool(tool, always_abort=False)

    def __create_transfer_worklist(self, resource):
        entity = resource.get_entity()
        tool = IsoControlStockRackWorklistWriter(iso_job=entity)
        return self._run_tool(tool)


class IsoWorklistRenderer(ZippedWorklistRenderer):

    def __call__(self, value, system):
        CustomRenderer.__call__(self, value, system)
        resource = value.get('context', system.get('context'))
        request = system['request']
        params = request.params
        checker = ViewUserMessageChecker()
        with UserMessageHandlingContextManager(checker):
            if params['type'] == 'XL20':
                stream = self.__create_xl20_worklist_stream(resource, request)
            elif params['type'] == 'STOCK_TRANSFER':
                stream = self.__create_transfer_worklist_stream(resource)
            elif params['type'] == 'ISO_PROCESSING':
                stream = \
                    self.__create_iso_processing_worklist_stream(resource)
            elif params['type'] == 'ISO_PROCESSING_ALIQUOT':
                stream = \
                    self.__create_iso_processing_aliquote_worklist_stream(
                                                            resource, request)
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
        shape = params['shape']
        rack_map = { 0 : barcode1, 1 : barcode2, 2: barcode3, 3 : barcode4}
        enforce_cybio_compatibility = params['enforce_multiple_racks'] == 'true'
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

        if shape == '384':
            del entity.iso_sample_stock_racks[:]
            tool = IsoXL20WorklistGenerator384Samples(iso=entity,
                     destination_rack_barcode_map=rack_map,
                     excluded_racks=optimizer_excluded_racks,
                     requested_tubes=optimizer_required_racks,
                     include_dummy_output=include_dummy_output,
                     enforce_cybio_compatibility=enforce_cybio_compatibility)
        elif shape == '96':
            del entity.iso_sample_stock_racks[:]
            tool = IsoXL20WorklistGenerator96(iso=entity,
                     destination_rack_barcode=barcode1,
                     excluded_racks=optimizer_excluded_racks,
                     requested_tubes=optimizer_required_racks,
                     include_dummy_output=include_dummy_output)
        else:
            raise HTTPBadRequest("Shape parameter is missing or unknown.")
        return self._run_tool(tool, always_abort=False)

    def __create_transfer_worklist_stream(self, resource):
        entity = resource.get_entity()
        tool = IsoSampleStockRackWorklistWriter(iso=entity)
        return self._run_tool(tool)

    def __create_iso_processing_worklist_stream(self, resource):
        entity = resource.get_entity()
        tool = IsoProcessingWorklistWriter(iso=entity)
        return self._run_tool(tool)

    def __create_iso_processing_aliquote_worklist_stream(self, resource, request):
        entity = resource.get_entity()
        params = request.params
        barcode = params['rack']
        tool = IsoAliquotWorklistWriter(iso=entity, barcode=barcode)
        return self._run_tool(tool)
