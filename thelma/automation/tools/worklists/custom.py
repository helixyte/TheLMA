"""
Tools dealing with custom transfers.

AAB
"""
from thelma.automation.handlers.sampletransfer \
    import GenericSampleTransferPlanParserHandler
from thelma.automation.tools.worklists.base import TRANSFER_ROLES
from thelma.automation.tools.worklists.series import SampleDilutionJob
from thelma.automation.tools.worklists.series import SampleTransferJob
from thelma.automation.tools.worklists.series import SerialWriterExecutorTool
from thelma.automation.utils.base import add_list_map_element
from thelma.entities.liquidtransfer import TRANSFER_TYPES

__docformat__ = 'reStructuredText en'

__all__ = ['CustomLiquidTransferTool']


#: TODO: think about how to add rack sample transfers

class CustomLiquidTransferTool(SerialWriterExecutorTool):
    """
    An base tool for tools dealing with custom liquid transfer worklist
    series.

    **Return Value:** a zip stream for for printing mode or executed worklists
        for execution mode (can be overwritten)
    """
    NAME = 'Custom Liquid Transfer Writer/Executor'

    #: The file name for potential Cybio transfers.
    FILE_NAME_CYBIO = 'cybio_transfer.txt'

    def __init__(self, stream, mode, user, **kw):
        """
        Constructor:

        :param stream: The custom transfer XLS file as stream.

        :param mode: :attr:`MODE_EXECUTE` or :attr:`MODE_PRINT_WORKLISTS`
        :type mode: str

        :param user: The user who conducts the DB update (required for
            execution mode).
        :type user: :class:`thelma.entities.user.User`
        :default user: *None*
        """
        SerialWriterExecutorTool.__init__(self, mode=mode, user=user, **kw)

        #: The custom transfer XLS file as stream.
        self.stream = stream

        #: The :class:`WorklistSeries` generate by the parser.
        self._worklist_series = None
        #: The :class:RackOrReservoirItem` for each rack or reservoir in the
        #: worklist series.
        self.__rors = None
        #: The source and targets :class:RackOrReservoirItem` for each worklist.
        self.__transfer_roles = None

    def reset(self):
        SerialWriterExecutorTool.reset(self)
        self._worklist_series = None
        self.__rors = None
        self.__transfer_roles = dict()

    def _create_transfer_jobs(self):
        self.add_info('Start custom liquid transfer processing ...')
        if not self.has_errors(): self.__parse_file()
        if not self.has_errors(): self.__sort_transfer_roles()
        if not self.has_errors(): self.__generate_transfer_jobs()

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        SerialWriterExecutorTool._check_input(self)
        if self.stream is None:
            msg = 'The stream must not be None!'
            self.add_error(msg)

    def __parse_file(self):
        """
        The parser returns a worklist series and the :attr:`__ror_map`.
        """
        self.add_debug('Parse file ...')

        handler = GenericSampleTransferPlanParserHandler(
                                            self.stream,
                                            allow_rack_creation=False,
                                            parent=self)
        self._worklist_series = handler.get_result()
        if self._worklist_series is None:
            msg = 'Error when trying to parse file!'
            self.add_error(msg)
        else:
            self.__rors = handler.get_racks_and_reservoir_items()

    def __sort_transfer_roles(self):
        # Obtains the source and target for each worklist.
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
        # Sets the passed RackOrReservoirItem as source or target for the
        # given worklist.
        if self.__transfer_roles.has_key(worklist.label):
            role_map = self.__transfer_roles[worklist.label]
        else:
            role_map = dict()
            self.__transfer_roles[worklist.label] = role_map
        add_list_map_element(role_map, role, ror)

    def __generate_transfer_jobs(self):
        # The type of the worklist is derived from its first planned liquid
        # transfer.
        self.add_debug('Create transfer jobs ...')
        self._transfer_jobs = dict()
        for worklist in self._worklist_series.get_sorted_worklists():
            role_map = self.__transfer_roles[worklist.label]
            sources = sorted(role_map[TRANSFER_ROLES.SOURCE])
            targets = sorted(role_map[TRANSFER_ROLES.TARGET])
            for src_ror in sources:
                for trg_ror in targets:
                    self.__create_transfer_job(worklist, src_ror, trg_ror)

    def __create_transfer_job(self, worklist, src_ror, trg_ror):
        # Helper function creating a new transfer job. The job indices are
        # sequential.
        job_index = len(self._transfer_jobs)
        transfer_type = worklist.planned_liquid_transfers[0].transfer_type
        if transfer_type == TRANSFER_TYPES.SAMPLE_DILUTION:
            job = SampleDilutionJob(index=job_index,
                            planned_worklist=worklist,
                            target_rack=trg_ror.rack,
                            reservoir_specs=src_ror.reservoir_specs,
                            source_rack_barcode=src_ror.barcode)
        elif transfer_type == TRANSFER_TYPES.SAMPLE_TRANSFER:
            job = SampleTransferJob(index=job_index,
                            planned_worklist=worklist,
                            target_rack=trg_ror.rack,
                            source_rack=src_ror.rack)
        self._transfer_jobs[job_index] = job

    def _get_file_map(self, merged_stream_map, rack_transfer_stream):
        """
        The names for the files are the worklist labels. The rack stream
        is
        """
        file_map = dict()
        if rack_transfer_stream is not None:
            file_map[self.FILE_NAME_CYBIO] = rack_transfer_stream
        for worklist_label, stream in merged_stream_map.iteritems():
            fn = '%s.csv' % (worklist_label)
            file_map[fn] = stream
        return file_map
