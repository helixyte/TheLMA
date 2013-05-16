"""
Class for worklist series support.

AAB
"""
from StringIO import StringIO
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.utils.racksector import RackSectorTranslator
from thelma.automation.tools.worklists.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.worklists.execution import WorklistExecutor
from thelma.automation.tools.worklists.biomek \
    import ContainerDilutionWorklistWriter
from thelma.automation.tools.worklists.biomek \
    import ContainerTransferWorklistWriter
from thelma.automation.tools.worklists.execution \
    import ContainerDilutionWorklistExecutor
from thelma.automation.tools.worklists.execution \
    import ContainerTransferWorklistExecutor
from thelma.automation.tools.worklists.execution \
    import RackTransferExecutor
from thelma.automation.tools.writers import LINEBREAK_CHAR
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.user import User
from thelma.models.utils import get_user



__docformat__ = 'reStructuredText en'

__all__ = ['TransferJob',
           'ContainerDilutionJob',
           'ContainerTransferJob',
           'RackTransferJob',
           'SeriesTool',
           'SeriesWorklistWriter',
           'SeriesExecutor']


class TransferJob(object):
    """
    A helper class storing target and source data for a worklist file generation
    or a transfer execution (to provide data for serial executors or
    file generators).

    :Note: There are no checks carried out here.
    """

    #: The transfer type supported by this class
    #: (see :class:`thelma.models.liquidtransfer.TRANSFER_TYPES`).
    SUPPORTED_TRANSFER_TYPE = None

    def __init__(self, index, target_rack, is_biomek_transfer=False):
        """
        Constructor:

        :param index: The index of the transfer job within the series.
        :type index: :class:`int`
        :param target_rack: The rack taking up the volumes.
        :type target_rack: :class:`thelma.models.rack.Rack`
        :param is_biomek_transfer: Is this supposed to be a Biomek transfer?
        :type is_biomek_transfer: :class:`bool`
        :default is_biomek_transfer: *False*
        """

        #: The index of the transfer job within the series.
        self.index = index
        #: The rack into which the volumes will be dispensed.
        self.target_rack = target_rack
        #: Is this supposed to be a Biomek transfer?
        self.is_biomek_transfer = is_biomek_transfer

        #: Overwrites the minimum transfer volume of a writer (if not None).
        self.min_transfer_volume = None
        #: Overwrites the maximum transfer volume of a writer (if not None).
        self.max_transfer_volume = None

    def get_kw_for_worklist_writer(self, log):
        """
        Returns a keywords map that can be used to initialise a worklist writer.
        """
        kw = dict()

        kw['target_rack'] = self.target_rack
        kw['log'] = log
        return kw

    def get_kw_for_executor(self, log, user):
        """
        Returns a keywords map that can be used to initialise an executor.
        """
        kw = dict()

        kw['user'] = user
        kw['log'] = log
        kw['target_rack'] = self.target_rack
        return kw


class ContainerDilutionJob(TransferJob):
    """
    A transfer job for a planned container dilutions.

    :Note: There are no checks carried out here.
    """

    SUPPORTED_TRANSFER_TYPE = TRANSFER_TYPES.CONTAINER_DILUTION

    def __init__(self, index, planned_worklist, target_rack, reservoir_specs,
                 source_rack_barcode=None, ignored_positions=None,
                 is_biomek_transfer=False):
        """
        Constructor:

        :param index: The index of the transfer job within the series.
        :type index: :class:`int`
        :param planned_worklist: The worklist containing the planned transfers.
        :type planned_worklist:
            :class:`thelma.models.liquidtransfer.PlannedWorklist`
        :param target_rack: The rack taking up the volumes.
        :type target_rack: :class:`thelma.models.rack.Rack`
        :param reservoir_specs: The specs for the source reservoir or rack.
        :type reservoir_specs:
            :class:`thelma.models.liquidtransfer.ResevoirSpecs`
        :param source_rack_barcode: The barcode of the source reservoir or
            rack (only required for worklist file generation.
        :type source_rack_barcode: :class:`basestring`
        :param ignored_positions: A list of rack positions whose planned
            transfers should be ignored (refers to target positions).
        :type ignored_positions: :class:`list` of :class:`RackPosition`
        :param is_biomek_transfer: Is this supposed to be a Biomek transfer?
        :type is_biomek_transfer: :class:`bool`
        :default is_biomek_transfer: *False*
        """
        TransferJob.__init__(self, index=index, target_rack=target_rack,
                             is_biomek_transfer=is_biomek_transfer)

        #: The worklist containing the planned transfers.
        self.planned_worklist = planned_worklist
        #: The specs for the source reservoir or rack.
        self.reservoir_specs = reservoir_specs
        #: The barcode of the source reservoir or rack.
        self.source_rack_barcode = source_rack_barcode
        #: A list of rack positions whose planned transfers should be
        #: ignored (refers to target positions).
        self.ignored_positions = ignored_positions

    def get_kw_for_worklist_writer(self, log):
        """
        Returns a keywords map that can be used to initialise a worklist writer.
        """
        kw = TransferJob.get_kw_for_worklist_writer(self, log=log)

        kw['planned_worklist'] = self.planned_worklist
        kw['reservoir_specs'] = self.reservoir_specs
        kw['source_rack_barcode'] = self.source_rack_barcode
        kw['ignored_positions'] = self.ignored_positions

        return kw

    def get_kw_for_executor(self, log, user):
        """
        Returns a keywords map that can be used to initialise an executor.
        """
        kw = TransferJob.get_kw_for_executor(self, log=log, user=user)

        kw['planned_worklist'] = self.planned_worklist
        kw['reservoir_specs'] = self.reservoir_specs
        kw['ignored_positions'] = self.ignored_positions
        kw['is_biomek_transfer'] = self.is_biomek_transfer

        return kw

    def __repr__(self):
        str_format = '<%s index: %i, label: %s, target rack: %s, reservoir ' \
                     'specs: %s, source rack barcode: %s>'
        params = (self.__class__.__name__, self.index,
                  self.planned_worklist.label, self.target_rack.barcode,
                  self.reservoir_specs, self.source_rack_barcode)
        return str_format % params


class ContainerTransferJob(TransferJob):
    """
    A transfer job for a planned container transfers.

    :Note: There are no checks carried out here.
    """

    SUPPORTED_TRANSFER_TYPE = TRANSFER_TYPES.CONTAINER_TRANSFER

    def __init__(self, index, planned_worklist, target_rack, source_rack,
                 ignored_positions=None, is_biomek_transfer=False):
        """
        Constructor:

        :param index: The index of the transfer job within the series.
        :type index: :class:`int`
        :param planned_worklist: The worklist containing the planned transfers.
        :type planned_worklist:
            :class:`thelma.models.liquidtransfer.PlannedWorklist`
        :param target_rack: The rack taking up the volumes.
        :type target_rack: :class:`thelma.models.rack.Rack`
        :param source_rack: The rack providing the volumes.
        :type source_rack: :class:`thelma.models.rack.Rack`
        :param ignored_positions: A list of rack positions whose planned
            transfers should be ignored (refers to target positions).
        :type ignored_positions: :class:`list` of :class:`RackPosition`
        :param is_biomek_transfer: Is this supposed to be a Biomek transfer?
        :type is_biomek_transfer: :class:`bool`
        :default is_biomek_transfer: *False*
        """
        TransferJob.__init__(self, index=index, target_rack=target_rack,
                             is_biomek_transfer=is_biomek_transfer)

         #: The worklist containing the planned transfers.
        self.planned_worklist = planned_worklist
        #: The rack providing the volumes.
        self.source_rack = source_rack
        #: A list of rack positions whose planned transfers should be
        #: ignored (refers to target positions).
        self.ignored_positions = ignored_positions

    def get_kw_for_worklist_writer(self, log):
        """
        Returns a keywords map that can be used to initialise a worklist writer.
        """
        kw = TransferJob.get_kw_for_worklist_writer(self, log=log)

        kw['planned_worklist'] = self.planned_worklist
        kw['source_rack'] = self.source_rack
        kw['ignored_positions'] = self.ignored_positions

        return kw

    def get_kw_for_executor(self, log, user):
        """
        Returns a keywords map that can be used to initialise an executor.
        """
        kw = TransferJob.get_kw_for_executor(self, log=log, user=user)

        kw['planned_worklist'] = self.planned_worklist
        kw['source_rack'] = self.source_rack
        kw['ignored_positions'] = self.ignored_positions
        kw['is_biomek_transfer'] = self.is_biomek_transfer

        return kw

    def __repr__(self):
        str_format = '<%s index: %s, label: %s, target rack: %s, ' \
                     'source rack: %s>'
        params = (self.__class__.__name__, self.index,
                  self.planned_worklist.label, self.target_rack.barcode,
                  self.source_rack.barcode)
        return str_format % params


class RackTransferJob(TransferJob):
    """
    A transfer job for a planned container transfers.

    :Note: There are no checks carried out here.
    """

    SUPPORTED_TRANSFER_TYPE = TRANSFER_TYPES.RACK_TRANSFER

    def __init__(self, index, planned_rack_transfer, target_rack, source_rack):
        """
        Constructor:

        :param index: The index of the transfer job within the series.
        :type index: :class:`int`
        :param planned_rack_transfer: The data for the planned transfer.
        :type planned_rack_transfer:
            :class:`thelma.models.liquidtransfer.PlannedRackTransfer`
        :param target_rack: The rack taking up the volumes.
        :type target_rack: :class:`thelma.models.rack.Rack`
        :param source_rack: The rack providing the volumes.
        :type source_rack: :class:`thelma.models.rack.Rack`
        """
        TransferJob.__init__(self, index=index, target_rack=target_rack,
                             is_biomek_transfer=False)

         #: The worklist containing the planned transfers.
        self.planned_rack_transfer = planned_rack_transfer
        #: The rack providing the volumes.
        self.source_rack = source_rack

    def get_kw_for_worklist_writer(self, log):
        """
        Returns a keywords map that can be used to initialise a worklist writer.
        """
        raise NotImplementedError('No worklists for rack transfers.')

    def get_kw_for_executor(self, log, user):
        """
        Returns a keywords map that can be used to initialise an executor.
        """
        kw = TransferJob.get_kw_for_executor(self, log=log, user=user)

        kw['planned_rack_transfer'] = self.planned_rack_transfer
        kw['source_rack'] = self.source_rack

        return kw

    def __repr__(self):
        str_format = '<%s index: %s, target rack: %s, source rack: %s>'
        params = (self.__class__.__name__, self.index,
                  self.target_rack.barcode, self.source_rack.barcode)
        return str_format % params


class SeriesTool(BaseAutomationTool):
    """
    This abstract tool is the base for all worklist series tools (serial
    generation of worklist files and serial execution).
    The use of such a tool is required if the tasks for the series depend
    on one another, e.g. because the volume of for a later source well must
    be provided first.

    The tool take a list of :class:`TransferJob` objects.
    """

    def __init__(self, transfer_jobs, log, user=None):
        """
        Constructor:

        :param transfer_jobs: A list of transfer job to be carried out
            one after the other.
        :type transfer_jobs: :class:`list` of :class:`TransferJob` objects
        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`
        :param user: The user used for the simulated executions.
        :type user: :class:`thelma.models.user.User`
        :default user: None
        """
        BaseAutomationTool.__init__(self, log=log)

        #: A list of transfer job to be carried out one after the other.
        self.transfer_jobs = transfer_jobs

        #: The transfer jobs sorted by index.
        self._job_map = None
        #: Stores all involved real racks (mapped onto their barcode).
        self._barcode_map = None

        #: The user used for the simulated executions.
        self.user = user

    def reset(self):
        """
        Resets all attributes except for initialisation values.
        """
        BaseAutomationTool.reset(self)
        self._job_map = dict()
        self._barcode_map = dict()

    def run(self):
        """
        Runs the tool.
        """
        self.reset()

        self._check_input()
        if not self.has_errors(): self.__create_job_map()
        if not self.has_errors(): self._execute_task()

    def _check_input(self):
        """
        Checks the input values.
        """
        self.add_debug('Check input ...')

        self._check_input_class('user', self.user, User)

        if self._check_input_class('transfer job list', self.transfer_jobs,
                                       list):
            for transfer_job in self.transfer_jobs:
                if not self._check_input_class('transfer job', transfer_job,
                                               TransferJob): break

    def __create_job_map(self):
        """
        Creates the :attr:`_job_map` which maps transfer jobs onto job indices.
        """
        self.add_debug('Create job map ...')

        for transfer_job in self.transfer_jobs:
            if self._job_map.has_key(transfer_job.index):
                msg = 'Duplicate job index: %s!' % (transfer_job.index)
                self.add_error(msg)
            else:
                self._job_map[transfer_job.index] = transfer_job

    def _execute_task(self):
        """
        The tasks performed by the specific tool.
        """
        self.add_error('Abstract method: _execute_task()')

    def _update_racks(self, transfer_job):
        """
        Replaces the rack of an transfer job by updated racks.
        """
        target_barcode = transfer_job.target_rack.barcode
        if self._barcode_map.has_key(target_barcode):
            transfer_job.target_rack = self._barcode_map[target_barcode]

        if isinstance(transfer_job, (ContainerTransferJob, RackTransferJob)):
            source_barcode = transfer_job.source_rack.barcode
            if self._barcode_map.has_key(source_barcode):
                transfer_job.source_rack = self._barcode_map[source_barcode]

        return transfer_job

    def _execute_job(self, transfer_job):
        """
        Executes a transfer job.
        """

        if isinstance(transfer_job, ContainerDilutionJob):
            executor_cls = ContainerDilutionWorklistExecutor
        elif isinstance(transfer_job, ContainerTransferJob):
            executor_cls = ContainerTransferWorklistExecutor
        elif isinstance(transfer_job, RackTransferJob):
            executor_cls = RackTransferExecutor

        kw = transfer_job.get_kw_for_executor(log=self.log, user=self.user)
        executor = executor_cls(**kw)
        if not transfer_job.min_transfer_volume is None:
            if isinstance(executor, WorklistExecutor):
                executor.is_biomek_transfer = False
            executor.set_minimum_transfer_volume(
                                            transfer_job.min_transfer_volume)
        if not transfer_job.max_transfer_volume is None:
            if isinstance(executor, WorklistExecutor):
                executor.is_biomek_transfer = False
            executor.is_biomek_transfer = False
            executor.set_maximum_transfer_volume(
                                            transfer_job.max_transfer_volume)

        executed_item = executor.get_result()
        if executed_item is None:
            msg = 'Error when trying to execute transfer job: %s.' \
                   % (transfer_job)
            self.add_error(msg)
            return None
        else:
            target_rack = executor.target_rack
            self._barcode_map[target_rack.barcode] = target_rack
            try:
                source_rack = executor.source_rack
            except AttributeError:
                pass
            else:
                self._barcode_map[source_rack] = source_rack
            return executed_item


class SeriesWorklistWriter(SeriesTool):
    """
    This tool creates worklist files for a whole series of planned worklists.
    It is required to use (in contrast to the use of single worklist writers)
    if the worklist of a series depend on one another, e.g. because the volumes
    for a later source well must be provided first.

    Hence, between two worklists, the tool will run a executor to update
    the rack data. However, the changes of the rack will not be passed to the
    DB.

    :Note: The worklists must be provided as :class:`TransferJob` objects.

    **Return Value:** A map with key = job index, value = worklist stream.
    """

    NAME = 'Series Worklist Writer'

    def __init__(self, transfer_jobs, log):
        """
        Constructor:

        :param transfer_jobs: A list of transfer job to be carried out
            one after the other.
        :type transfer_jobs: :class:`list` of :class:`TransferJob` objects
        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        SeriesTool.__init__(self, transfer_jobs=transfer_jobs, user=None,
                            log=log)

        #: Stores the generated streams (mapped onto indices).
        self._stream_map = None
        #: The stream for the rack transfers (if there are any).
        self._rack_transfer_stream = None
        #: The index of the first rack transfer job (if any, there might be
        #: several, however they all share one file).
        self._rack_transfer_index = None
        #: The number of rack transfer that have occurred so far.
        self._rack_transfer_count = None

        #: The user used for the simulated executions.
        self.user = get_user('it')

    def reset(self):
        """
        Resets all attributes except for initialisation values.
        """
        SeriesTool.reset(self)
        self._stream_map = dict()
        self._rack_transfer_stream = None
        self._rack_transfer_index = None
        self._rack_transfer_count = 0

    def _execute_task(self):
        """
        The tasks performed by the specific tool (worklist generation).
        """
        self.add_info('Start series worklist file generation ...')

        self.__write_worklists()
        if not self.has_errors():
            if not self._rack_transfer_stream is None:
                self._rack_transfer_stream.seek(0)
                self._stream_map[self._rack_transfer_index] = \
                                    self._rack_transfer_stream
            self.return_value = self._stream_map
            self.add_info('Series worklist generation completed.')

    def __write_worklists(self):
        """
        Writes the worklists files for the passed jobss (in the right order;
        execution is carried out after each worklist stream creation).
        """
        self.add_debug('Write Worklists ...')

        indices = self._job_map.keys()
        indices.sort()
        last_index = indices[-1]

        for job_index in indices:
            transfer_job = self._job_map[job_index]
            transfer_job = self._update_racks(transfer_job)

            # Write worklist
            writer = self.__get_writer(transfer_job)
            if writer is None and isinstance(transfer_job, RackTransferJob):
                # Rack transfers are treated differently.
                self.__write_rack_transfer_section(transfer_job)
            elif not writer is None:
                stream = writer.get_result()
                if stream is None:
                    msg = 'Error when trying to generate file for worklist ' \
                          '"%s".' % (transfer_job.planned_worklist.label)
                    self.add_error(msg)
                    break
                else:
                    self._stream_map[job_index] = stream
            # Even if there is no worklist writer for this case, it might
            # be that we have to execute the transfer as part of the series.

            # Execute changes (to prepare for the next worklist).
            if job_index == last_index: break # no execution necessary
            executed_item = self._execute_job(transfer_job)
            if executed_item is None: break

    def __get_writer(self, transfer_job):
        """
        Returns the writer for the given transfer job.
        """

        if isinstance(transfer_job, RackTransferJob):
            # No single writers so far
            return None

        elif isinstance(transfer_job, ContainerDilutionJob):
            if transfer_job.is_biomek_transfer:
                writer_cls = ContainerDilutionWorklistWriter
            else:
                # No other writers so far
                return None

        elif isinstance(transfer_job, ContainerTransferJob):
            if transfer_job.is_biomek_transfer:
                writer_cls = ContainerTransferWorklistWriter
            else:
                # No other writers so far
                return None

        kw = transfer_job.get_kw_for_worklist_writer(log=self.log)
        writer = writer_cls(**kw)

        if not transfer_job.min_transfer_volume is None:
            writer.set_minimum_transfer_volume(transfer_job.min_transfer_volume)
        if not transfer_job.max_transfer_volume is None:
            writer.set_maximum_transfer_volume(transfer_job.max_transfer_volume)

        return writer

    def __write_rack_transfer_section(self, rack_transfer_job):
        """
        Writes a section for the rack transfer stream (and initialises it
        if necessary).
        """
        if self._rack_transfer_stream is None:
            self._rack_transfer_stream = StringIO()
            self._rack_transfer_index = rack_transfer_job.index

        self._rack_transfer_count += 1
        writer = RackTransferSectionWriter(log=self.log,
                                    step_number=self._rack_transfer_count,
                                    rack_transfer_job=rack_transfer_job)
        paragraph = writer.get_result()
        if paragraph is None:
            msg = 'Error when trying to generate section for rack ' \
                  'transfer job %s.' % (rack_transfer_job)
            self.add_error(msg)
        else:
            self._rack_transfer_stream.write(paragraph)


class SeriesExecutor(SeriesTool):
    """
    This tool executes for a whole series of worklists and/or planned transfers
    (rack transfers). It is required to use (in contrast to the use of single
    executor) if the worklist of a series depend on one another, e.g. because
    the volumes for a later source well must be provided first.

    :Note: The planned transfers or worklists must be provided as
        :class:`TransferJob` objects.

    **Return Value:** A map with key = job index, value = executed item.
    """

    NAME = 'Series Executor'

    def __init__(self, transfer_jobs, user, log):
        """
        :param transfer_jobs: A list of transfer job to be carried out
            one after the other.
        :type transfer_jobs: :class:`list` of :class:`TransferJob` objects

        :param user: The user used for the simulated executions.
        :type user: :class:`thelma.models.user.User`

        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        SeriesTool.__init__(self, transfer_jobs=transfer_jobs,
                            log=log, user=user)

        #: Stores results of the transfer job execution (mapped onto indices).
        self._execution_map = None

    def reset(self):
        """
        Resets all attributes except for initialisation values.
        """
        SeriesTool.reset(self)
        self._execution_map = dict()

    def _execute_task(self):
        """
        The tasks performed by the specific tool (planned transfer execution).
        """
        self.add_info('Start series execution ...')

        indices = self._job_map.keys()
        indices.sort()

        for job_index in indices:
            transfer_job = self._job_map[job_index]
            transfer_job = self._update_racks(transfer_job)

            executed_item = self._execute_job(transfer_job)
            if executed_item is None: break
            self._execution_map[job_index] = executed_item

        if not self.has_errors():
            self.return_value = self._execution_map
            self.add_info('Series execution completed.')


class RackTransferWriter(SeriesTool):
    """
    Creates an overview file for a list of rack transfer jobs.

    :Note: This writer will not conduct any checks.

    **Return Value:** Stream for an TXT file.
    """

    NAME = 'Rack Transfer Writer'

    #: This line marks a new transfer.
    HEAD_LINE = 'STEP %i:'
    #: The source data line.
    FROM_LINE = 'FROM: rack %s'
    #: The target data line.
    TO_LINE = 'TO: rack %s'
    #: The sector data is added to the line if there is more than one
    #: sector in the transfer.
    SECTOR_ADDITION = ' sector %i'
    #: The volume line.
    VOLUME_LINE = 'volume: %.1f ul'

    def __init__(self, rack_transfer_jobs, log):
        """
        Constructor:

        :param rack_transfer_jobs: The rack transfer jobs of the series.
        :type rack_transfer_jobs: :class:`list`

        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        SeriesTool.__init__(self, transfer_jobs=rack_transfer_jobs,
                            log=log, user=None)

        #: The stream for the TXT file.
        self.__stream = None

        #: Counts the number of Cybio steps.
        self.__step_counter = None

        #: The user used for the simulated executions.
        self.user = get_user('it')

    def reset(self):
        """
        Resets all attributes except for initialisation values.
        """
        SeriesTool.reset(self)
        self.__stream = None
        self.__step_counter = 0

    def _check_input(self):
        """
        Checks if the tools has obtained correct input values.
        """
        SeriesTool._check_input(self)

        if self._check_input_class('rack transfer jobs list',
                                   self.transfer_jobs, list):
            for rtj in self.transfer_jobs:
                if not self._check_input_class('rack transfer job', rtj,
                                               RackTransferJob): break

    def _execute_task(self):
        """
        The tasks performed by the specific tool (rack transfer overview
        generation).
        """
        self.add_info('Start rack transfer file generation ...')

        self.__stream = StringIO()
        self.__write_content()
        if not self.has_errors():
            self.return_value = self.__stream
            self.add_info('File creation completed.')

    def __write_content(self):
        """
        Writes the file content.
        """

        indices = self._job_map.keys()
        indices.sort()
        for job_index in indices:
            rack_transfer_job = self._job_map[job_index]
            rack_transfer_job = self._update_racks(rack_transfer_job)
            self.__write_rack_transfer_job_record(rack_transfer_job)

            # Execute changes (to prepare for the next worklist).
            executed_item = self._execute_job(rack_transfer_job)
            if executed_item is None: break

        self.__stream.seek(0)

    def __write_rack_transfer_job_record(self, rack_transfer_job):
        """
        Adds an rack transfer record to the stream.
        """
        self.__step_counter += 1

        writer = RackTransferSectionWriter(step_number=self.__step_counter,
                                           rack_transfer_job=rack_transfer_job,
                                           log=self.log)
        paragraph = writer.get_result()
        if paragraph is None:
            msg = 'Error when trying to write paragraph for rack transfer %s.' \
                  % (rack_transfer_job)
            self.add_error(msg)
        else:
            self.__stream.write(paragraph)


class RackTransferSectionWriter(BaseAutomationTool):
    """
    Writes a section for a single rack transfer.

    :Note: There are no checks carried out here.

    **Return Value:** string
    """

    NAME = 'Rack Transfer Section Writer'

    #: This line marks a new transfer.
    HEAD_LINE = 'STEP %i:'
    #: The source data line.
    FROM_LINE = 'FROM: rack %s'
    #: The target data line.
    TO_LINE = 'TO: rack %s'
    #: The sector data is added to the line if there is more than one
    #: sector in the transfer.
    SECTOR_ADDITION = ' sector %i'
    #: The volume line.
    VOLUME_LINE = 'volume: %.1f ul'

    def __init__(self, step_number, rack_transfer_job, log):
        """
        Constructor:

        :param step_number: The step number (of all rack transfers in
            the series).
        :type step_number: :class:`int`

        :param rack_transfer_job: The job to write down.
        :type rack_transfer_job: :class:`RackTransferJob`

        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        BaseAutomationTool.__init__(self, log=log)

        #: The step (of all rack transfers in teh series).
        self.step_number = step_number
        #: The job to write down.
        self.rack_transfer_job = rack_transfer_job

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Write rack transfer job section ...')

        self.__check_input()
        if not self.has_errors():
            self.return_value = self.__write_section()
            self.add_info('Section completed.')

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input ...')
        self._check_input_class('step number', self.step_number, int)
        self._check_input_class('rack transfer job', self.rack_transfer_job,
                                RackTransferJob)

    def __write_section(self):
        """
        Writes the section.
        """
        self.add_debug('Write section ...')

        prt = self.rack_transfer_job.planned_rack_transfer
        head_line = self.HEAD_LINE % (self.step_number)
        from_line = self.FROM_LINE % (self.rack_transfer_job.source_rack.barcode)
        to_line = self.TO_LINE % (self.rack_transfer_job.target_rack.barcode)
        volume_line = self.VOLUME_LINE % (prt.volume * VOLUME_CONVERSION_FACTOR)

        translation_type = RackSectorTranslator.get_translation_behaviour(
                    source_shape=self.rack_transfer_job.source_rack.rack_shape,
                    target_shape=self.rack_transfer_job.target_rack.rack_shape,
                    number_sectors=prt.sector_number)

        if prt.sector_number > 1:
            if not translation_type == RackSectorTranslator.MANY_TO_ONE:
                src_addition = self.SECTOR_ADDITION \
                                % (prt.source_sector_index + 1)
                from_line += src_addition
            if not translation_type == RackSectorTranslator.ONE_TO_MANY:
                trg_addition = self.SECTOR_ADDITION \
                               % (prt.target_sector_index + 1)
                to_line += trg_addition

        paragraph = head_line + (2 * LINEBREAK_CHAR)
        paragraph += (from_line + LINEBREAK_CHAR)
        paragraph += (to_line + LINEBREAK_CHAR)
        paragraph += (volume_line + LINEBREAK_CHAR)
        paragraph += (2 * LINEBREAK_CHAR) # spacer

        return paragraph


def create_rack_sector_stream(job_map, log):
    """
    Creates a stream for containing the rack sector info section for the
    passed transfer jobs. The jobs are sorted by the map key before writing.

    :Note: This function does almost the same like the
        :class:`RackTransferWriter`. However there are no checks and transfer
        executions in this function.

    :param job_map: The rack transfer jobs mapped onto a key that can be used
        for sorting.
    :type job_map: :class:`dict`
    :return: stream
    """
    stream = StringIO()

    indices = job_map.keys()
    indices.sort()
    rack_transfer_counter = 0
    for i in indices:
        rack_transfer_counter += 1
        writer = RackTransferSectionWriter(step_number=rack_transfer_counter,
                                        log=log, rack_transfer_job=job_map[i])
        paragraph = writer.get_result()
        if paragraph is None: return None
        stream.write(paragraph)

    stream.seek(0)
    return stream
