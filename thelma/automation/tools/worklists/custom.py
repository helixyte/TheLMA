"""
Tools dealing with custom transfers.

AAB
"""
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.handlers.sampletransfer import GenericSampleTransferPlanParserHandler
from thelma.automation.tools.worklists.base import TRANSFER_ROLES
from thelma.automation.tools.utils.base import add_list_map_element
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.automation.tools.worklists.series import ContainerDilutionJob
from thelma.automation.tools.semiconstants import get_pipetting_specs_biomek
from thelma.automation.tools.worklists.series import ContainerTransferJob
from thelma.automation.tools.worklists.series import SeriesWorklistWriter
from thelma.automation.tools.writers import create_zip_archive
from StringIO import StringIO
from thelma.models.user import User
from thelma.automation.tools.worklists.series import SeriesExecutor
from thelma.automation.tools.writers import merge_csv_streams

__docformat__ = 'reStructuredText en'

__all__ = ['_CustomLiquidTransferTool',
           'CustomLiquidTransferWorklistWriter',
           'CustomLiquidTransferExecutor']

#: TODO: review after ISO revision

#: TODO: think about how to add rack sample transfers

class _CustomLiquidTransferTool(BaseAutomationTool):
    """
    An base tool for tools dealing with custom liquid transfer worklist
    series.

    **Return Value:** depending on the subclass
    """

    def __init__(self, stream, **kw):
        """
        Constructor:

        :param stream: The custom transfer XLS file as stream.
        """
        BaseAutomationTool.__init__(self, depending=False, **kw)

        #: The custom transfer XLS file as stream.
        self.stream = stream

        #: The :class:`WorklistSeries` generate by the parser.
        self._worklist_series = None
        #: The :class:RackOrReservoirItem` for each rack or reservoir in the
        #: worklist series.
        self.__rors = None
        #: The source and targets :class:RackOrReservoirItem` for each worklist.
        self.__transfer_roles = None

        #: The transfer jobs mapped onto job indices.
        self._transfer_jobs = None

    def reset(self):
        BaseAutomationTool.reset(self)
        self._worklist_series = None
        self.__rors = None
        self.__transfer_roles = dict()
        self._transfer_jobs = dict()

    def run(self):
        self.reset()
        self.add_info('Start custom liquid transfer processing ...')

        self._check_input()
        if not self.has_errors(): self.__parse_file()
        if not self.has_errors(): self.__sort_transfer_roles()
        if not self.has_errors(): self.__create_transfer_jobs()
        if not self.has_errors(): self._execute_task()

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        if self.stream is None:
            msg = 'The stream must not be None!'
            self.add_error(msg)

    def __parse_file(self):
        """
        The parser returns a worklist series and the :attr:`__ror_map`.
        """
        self.add_debug('Parse file ...')

        handler = GenericSampleTransferPlanParserHandler(stream=self.stream,
                                                         log=self.log)
        self._worklist_series = handler.get_result()
        if self._worklist_series is None:
            msg = 'Error when trying to parse file!'
            self.add_error(msg)
        else:
            self.__rors = handler.get_racks_and_reservoir_items()

    def __sort_transfer_roles(self):
        """
        Obtains the source and target for each worklist.
        """
        self.add_debug('Sort source and targets for worklists ...')

        for ror in self.__rors:
            source_worklists = ror.get_worklists_for_source()
            for worklist in source_worklists:
                self.__store_worklist_roles(worklist, TRANSFER_ROLES.SOURCE,
                                            ror)
            target_worklists = ror.get_worklists_for_target()
            for worklist in target_worklists:
                self.__store_worklist_roles(worklist, TRANSFER_ROLES.TARGET,
                                            ror)

    def __store_worklist_roles(self, worklist, role, ror):
        """
        Sets the passed RackOrReservoirItem as source or target for the
        given worklist.
        """
        if self.__transfer_roles.has_key(worklist.label):
            role_map = self.__transfer_roles[worklist.label]
        else:
            role_map = dict()
            self.__transfer_roles[worklist.label] = role_map

        add_list_map_element(role_map, role, ror)

    def __create_transfer_jobs(self):
        """
        TODO:
        The type of the worklist is derived from its first planned liquid
        transfer.
        """
        self.add_debug('Create transfer jobs ...')

        # TODO: replace sorting by model function
        index_map = dict()
        for worklist in self._worklist_series:
            index_map[worklist.index] = worklist
        sorted_worklists = []
        for worklist_index in sorted(index_map.keys()):
            sorted_worklists.append(index_map[worklist_index])

        for worklist in sorted_worklists:
            role_map = self.__transfer_roles[worklist.label]
            sources = sorted(role_map[TRANSFER_ROLES.SOURCE])
            targets = sorted(role_map[TRANSFER_ROLES.TARGET])
            for src_ror in sources:
                for trg_ror in targets:
                    self.__create_transfer_job(worklist, src_ror, trg_ror)

    def __create_transfer_job(self, worklist, src_ror, trg_ror):
        """
        Helper function creating a new transfer job. The job indices are
        sequential.
        """
        job_index = len(self._transfer_jobs)
        transfer_type = worklist.planned_transfers[0].type

        robot_specs = get_pipetting_specs_biomek() #TODO: get from worklist

        if transfer_type == TRANSFER_TYPES.CONTAINER_DILUTION:
            job = ContainerDilutionJob(index=job_index,
                            planned_worklist=worklist,
                            target_rack=trg_ror.plate,
                            reservoir_specs=src_ror.reservoir_specs,
                            pipetting_specs=robot_specs,
                            source_rack_barcode=src_ror.barcode)
        elif transfer_type == TRANSFER_TYPES.CONTAINER_TRANSFER:
            job = ContainerTransferJob(index=job_index,
                            planned_worklist=worklist,
                            target_rack=trg_ror.plate,
                            source_rack=src_ror.plate,
                            pipetting_specs=robot_specs)

        self._transfer_jobs[job_index] = job

    def _execute_task(self):
        """
        Executes the specific task of the tool and sets the
        :attr:`return_value`.
        """
        raise NotImplementedError('Abstract method.')


class CustomLiquidTransferWorklistWriter(_CustomLiquidTransferTool):
    """
    Prints worklists for custom liquid transfer worklist series.

    **Return value:** worklist stream (zip archive)
    """
    NAME = 'Custom Liquid Transfer Worklist Writer'

    def __init__(self, stream, **kw):
        """
        Constructor:

        :param stream: The custom transfer XLS file as stream.
        """
        _CustomLiquidTransferTool.__init__(self, stream=stream, **kw)

        #: The stream map generated by the series writer.
        self.__stream_map = dict()

    def reset(self):
        _CustomLiquidTransferTool.reset(self)
        self.__stream_map = None

    def _execute_task(self):
        """
        Uses a :class:`SeriesWorklistWriter` to generate the worklists
        and wraps them into a zip stream. The file names are derived from
        the worklist and rack labels.
        """
        self.add_debug('Print worklists ...')

        writer = SeriesWorklistWriter(transfer_jobs=self._transfer_jobs.values(),
                                      log=self.log)
        stream_map = writer.get_result()
        if stream_map is None:
            msg = 'Error when trying to print worklist files!'
            self.add_error(msg)
        else:
            zip_stream = self.__create_zip_stream(stream_map)
            self.return_value = zip_stream
            self.add_info('Worklist printing completed.')

    def __create_zip_stream(self, stream_map):
        """
        Fetches the file name for each stream and generates a zip archive
        stream. The names for the files are the worklist labels.
        """
        self.add_debug('Create zip stream ...')

        sorted_streams = dict()
        for job_index in sorted(self._transfer_jobs.keys()):
            worklist_label = self._transfer_jobs[job_index].\
                             planned_worklist.label
            if sorted_streams.has_key(worklist_label):
                worklist_map = sorted_streams[worklist_label]
            else:
                worklist_map = dict()
                sorted_streams[worklist_label] = worklist_map
            worklist_map[job_index] = stream_map[job_index]

        file_map = dict()
        for worklist_label, worklist_map in sorted_streams.iteritems():
            merged_stream = merge_csv_streams(worklist_map)
            file_name = '%s.csv' % worklist_label
            file_map[file_name] = merged_stream

        zip_stream = StringIO()
        create_zip_archive(zip_stream, file_map)
        return zip_stream


class CustomLiquidTransferExecutor(_CustomLiquidTransferTool):
    """
    Performs the DB updates (executed worklist generation) for custom liquid
    transfer worklist series.

    **Return value:** list of :class:`ExecutedWorklist` objects
    """
    NAME = 'Custom Liquid Transfer Executor'


    def __init__(self, stream, user, **kw):
        """
        Constructor:

        :param stream: The custom transfer XLS file as stream.

        :param user: The user conducting the execution.
        :type user: :class:`thelma.models.user.User`
        """
        _CustomLiquidTransferTool.__init__(self, stream=stream)

        #: The user conducting the execution.
        self.user = user

    def _check_input(self):
        _CustomLiquidTransferTool._check_input(self)
        self._check_input_class('user', self.user, User)

    def _execute_task(self):
        """
        Uses a :class:`SeriesExecutor`.
        """
        self.add_debug('Execute worklists ...')

        executor = SeriesExecutor(transfer_jobs=self._transfer_jobs.values(),
                                  user=self.user, log=self.log)
        executed_map = executor.get_result()

        if executed_map is None:
            msg = 'Error when running serial worklist execution!'
            self.add_error(msg)
        else:
            self.return_value = executed_map.values()
            self.add_info('Worklist execution completed.')
