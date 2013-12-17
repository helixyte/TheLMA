"""
Class for worklist series support.

AAB
"""
from StringIO import StringIO
from thelma.automation.semiconstants import PIPETTING_SPECS_NAMES
from thelma.automation.semiconstants import get_pipetting_specs
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.semiconstants import PIPETTING_SPECS_NAMES
from thelma.automation.tools.worklists.biomek \
    import SampleDilutionWorklistWriter
from thelma.automation.tools.worklists.biomek \
    import SampleTransferWorklistWriter
from thelma.automation.tools.worklists.execution \
    import RackSampleTransferExecutor
from thelma.automation.tools.worklists.execution \
    import SampleDilutionWorklistExecutor
from thelma.automation.tools.worklists.execution \
    import SampleTransferWorklistExecutor
from thelma.automation.tools.writers import LINEBREAK_CHAR
from thelma.automation.tools.writers import create_zip_archive
from thelma.automation.tools.writers import merge_csv_streams
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.utils.racksector import RackSectorTranslator
from thelma.models.liquidtransfer import ExecutedWorklist
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.user import User
from thelma.models.utils import get_user



__docformat__ = 'reStructuredText en'

__all__ = ['_LiquidTransferJob',
           'SampleDilutionJob',
           'SampleTransferJob',
           'RackSampleTransferJob',
           '_SeriesTool',
           '_SeriesWorklistWriter',
           '_SeriesExecutor',
           'SerialWriterExecutorTool']


class _LiquidTransferJob(object):
    """
    A helper class storing target and source data for a worklist file generation
    or a transfer execution (to provide data for serial executors or
    file generators).

    :Note: There are no checks carried out here.
    """

    #: The transfer type supported by this class
    #: (see :class:`thelma.models.liquidtransfer.TRANSFER_TYPES`).
    SUPPORTED_TRANSFER_TYPE = None

    #: The executor class supported by this transfer job class.
    EXECUTOR_CLS = None

    #: The writer classes for the different pipetting techniques.
    WRITER_CLASSES = dict()

    def __init__(self, index, target_rack, pipetting_specs):
        """
        Constructor:

        :param index: The index of the transfer job within the series.
        :type index: :class:`int`

        :param target_rack: The rack taking up the volumes.
        :type target_rack: :class:`thelma.models.rack.Rack`

        :param pipetting_specs: Defines the properties (like the
            transfer volume range, etc.)
        :type pipetting_specs: :class:`basestring` (pipetting specs name) or
            :class:`thelma.models.liquidtransfer.PipettingSpecs`
        """

        #: The index of the transfer job within the series.
        self.index = index
        #: The rack into which the volumes will be dispensed.
        self.target_rack = target_rack

        if isinstance(pipetting_specs, basestring):
            pipetting_specs = get_pipetting_specs(pipetting_specs)
        #: The :class:`PipettingSpecs` to be used for this transfer.
        self.pipetting_specs = pipetting_specs

    def get_executor(self, log, user):
        """
        Returns an configured :class:`LiquidTransferExecutor`.

        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param user: The DB user executing the transfers.
        :type user: :class:`thelma.models.user.User`

        :return: configured :class:`LiquidTransferExecutor`
        """
        kw = self._get_kw_for_executor(log, user)
        return self.EXECUTOR_CLS(**kw) #pylint: disable=E1102

    def _get_kw_for_executor(self, log, user):
        """
        Returns a keywords map that can be used to initialise an executor.
        """
        kw = dict()

        kw['user'] = user
        kw['log'] = log
        kw['target_rack'] = self.target_rack
        kw['pipetting_specs'] = self.pipetting_specs
        return kw

    def get_worklist_writer(self, log):
        """
        Returns an configured :class:`WorklistWriter` (or *None* if there is
        no writer class registered for the used :attr:`pipetting_specs`).

        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param user: The DB user executing the transfers.
        :type user: :class:`thelma.models.user.User`

        :return: configured :class:`WorklistWriter`
        """
        ps_name = self.pipetting_specs.name
        if not self.WRITER_CLASSES.has_key(ps_name): return None
        writer_cls = self.WRITER_CLASSES[ps_name]
        if writer_cls is None: return None

        kw = self._get_kw_for_worklist_writer(log)
        return writer_cls(**kw)

    def _get_kw_for_worklist_writer(self, log):
        """
        Returns a keywords map that can be used to initialise a worklist writer.
        """
        kw = dict()

        kw['target_rack'] = self.target_rack
        kw['log'] = log
        kw['pipetting_specs'] = self.pipetting_specs
        return kw


class SampleDilutionJob(_LiquidTransferJob):
    """
    A transfer job for a planned sample dilutions.

    :Note: There are no checks carried out here.
    """

    SUPPORTED_TRANSFER_TYPE = TRANSFER_TYPES.SAMPLE_DILUTION
    EXECUTOR_CLS = SampleDilutionWorklistExecutor
    WRITER_CLASSES = {
          PIPETTING_SPECS_NAMES.BIOMEK : SampleDilutionWorklistWriter,
          PIPETTING_SPECS_NAMES.MANUAL : SampleDilutionWorklistWriter }

    def __init__(self, index, planned_worklist, target_rack, reservoir_specs,
                 source_rack_barcode=None, ignored_positions=None):
        """
        Constructor:

        :param index: The index of the transfer job within the series.
        :type index: :class:`int`

        :param planned_worklist: The worklist containing the planned liquid
            transfers.
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
        """
        _LiquidTransferJob.__init__(self, index=index, target_rack=target_rack,
                               pipetting_specs=planned_worklist.pipetting_specs)

        #: The worklist containing the planned liquid transfers.
        self.planned_worklist = planned_worklist
        #: The specs for the source reservoir or rack.
        self.reservoir_specs = reservoir_specs
        #: The barcode of the source reservoir or rack.
        self.source_rack_barcode = source_rack_barcode
        #: A list of rack positions whose planned liquid transfers should be
        #: ignored (refers to target positions).
        self.ignored_positions = ignored_positions

    def _get_kw_for_worklist_writer(self, log):
        """
        Returns a keywords map that can be used to initialise a worklist writer.
        """
        kw = _LiquidTransferJob._get_kw_for_worklist_writer(self, log=log)

        kw['planned_worklist'] = self.planned_worklist
        kw['reservoir_specs'] = self.reservoir_specs
        kw['source_rack_barcode'] = self.source_rack_barcode
        kw['ignored_positions'] = self.ignored_positions

        return kw

    def _get_kw_for_executor(self, log, user):
        """
        Returns a keywords map that can be used to initialise an executor.
        """
        kw = _LiquidTransferJob._get_kw_for_executor(self, log=log, user=user)

        kw['planned_worklist'] = self.planned_worklist
        kw['reservoir_specs'] = self.reservoir_specs
        kw['ignored_positions'] = self.ignored_positions

        return kw

    def __repr__(self):
        str_format = '<%s index: %i, label: %s, target rack: %s, reservoir ' \
                     'specs: %s, source rack barcode: %s>'
        params = (self.__class__.__name__, self.index,
                  self.planned_worklist.label, self.target_rack.barcode,
                  self.reservoir_specs, self.source_rack_barcode)
        return str_format % params


class SampleTransferJob(_LiquidTransferJob):
    """
    A transfer job for a planned sample transfers.

    :Note: There are no checks carried out here.
    """

    SUPPORTED_TRANSFER_TYPE = TRANSFER_TYPES.SAMPLE_TRANSFER
    EXECUTOR_CLS = SampleTransferWorklistExecutor
    WRITER_CLASSES = {
          PIPETTING_SPECS_NAMES.BIOMEK : SampleTransferWorklistWriter,
          PIPETTING_SPECS_NAMES.MANUAL : SampleTransferWorklistWriter,
          PIPETTING_SPECS_NAMES.BIOMEKSTOCK : SampleTransferWorklistWriter,
          PIPETTING_SPECS_NAMES.CYBIO : SampleTransferWorklistWriter}

    def __init__(self, index, planned_worklist, target_rack, source_rack,
                 ignored_positions=None):
        """
        Constructor:

        :param index: The index of the transfer job within the series.
        :type index: :class:`int`

        :param planned_worklist: The worklist containing the planned liquid
            transfers.
        :type planned_worklist:
            :class:`thelma.models.liquidtransfer.PlannedWorklist`

        :param target_rack: The rack taking up the volumes.
        :type target_rack: :class:`thelma.models.rack.Rack`

        :param source_rack: The rack providing the volumes.
        :type source_rack: :class:`thelma.models.rack.Rack`

        :param ignored_positions: A list of rack positions whose planned
            transfers should be ignored (refers to target positions).
        :type ignored_positions: :class:`list` of :class:`RackPosition`
        """
        _LiquidTransferJob.__init__(self, index=index, target_rack=target_rack,
                               pipetting_specs=planned_worklist.pipetting_specs)

         #: The worklist containing the planned liquid transfers.
        self.planned_worklist = planned_worklist
        #: The rack providing the volumes.
        self.source_rack = source_rack
        #: A list of rack positions whose planned liquid transfers should be
        #: ignored (refers to target positions).
        self.ignored_positions = ignored_positions

    def _get_kw_for_worklist_writer(self, log):
        """
        Returns a keywords map that can be used to initialise a worklist writer.
        """
        kw = _LiquidTransferJob._get_kw_for_worklist_writer(self, log=log)

        kw['planned_worklist'] = self.planned_worklist
        kw['source_rack'] = self.source_rack
        kw['ignored_positions'] = self.ignored_positions

        return kw

    def _get_kw_for_executor(self, log, user):
        """
        Returns a keywords map that can be used to initialise an executor.
        """
        kw = _LiquidTransferJob._get_kw_for_executor(self, log=log, user=user)

        kw['planned_worklist'] = self.planned_worklist
        kw['source_rack'] = self.source_rack
        kw['ignored_positions'] = self.ignored_positions

        return kw

    def __repr__(self):
        str_format = '<%s index: %s, label: %s, target rack: %s, ' \
                     'source rack: %s>'
        params = (self.__class__.__name__, self.index,
                  self.planned_worklist.label, self.target_rack.barcode,
                  self.source_rack.barcode)
        return str_format % params


class RackSampleTransferJob(_LiquidTransferJob):
    """
    A transfer job for a planned sample transfers. This sort of jobs
    is assumed to be performed by the CyBio.

    :Note: There are no checks carried out here.
    """

    SUPPORTED_TRANSFER_TYPE = TRANSFER_TYPES.RACK_SAMPLE_TRANSFER
    EXECUTOR_CLS = RackSampleTransferExecutor
    # no writer support

    def __init__(self, index, planned_rack_sample_transfer, target_rack,
                 source_rack):
        """
        Constructor:

        :param index: The index of the transfer job within the series.
        :type index: :class:`int`

        :param planned_rack_sample_transfer: The data for the planned liquid
            transfer.
        :type planned_rack_sample_transfer:
            :class:`thelma.models.liquidtransfer.PlannedRackSampleTransfer`

        :param target_rack: The rack taking up the volumes.
        :type target_rack: :class:`thelma.models.rack.Rack`

        :param source_rack: The rack providing the volumes.
        :type source_rack: :class:`thelma.models.rack.Rack`
        """
        _LiquidTransferJob.__init__(self, index=index, target_rack=target_rack,
                                   pipetting_specs=PIPETTING_SPECS_NAMES.CYBIO)

         #: The worklist containing the planned liquid transfers.
        self.planned_rack_sample_transfer = planned_rack_sample_transfer
        #: The rack providing the volumes.
        self.source_rack = source_rack

    def _get_kw_for_executor(self, log, user):
        """
        Returns a keywords map that can be used to initialise an executor.
        """
        kw = _LiquidTransferJob._get_kw_for_executor(self, log=log, user=user)

        kw['planned_rack_sample_transfer'] = self.planned_rack_sample_transfer
        kw['source_rack'] = self.source_rack

        return kw

    def _get_kw_for_worklist_writer(self, log):
        """
        They are no real worklist files for rack transfers but only sections
        in instruction files (which are handled separately).
        """
        raise NotImplementedError('No worklists for rack transfers.')

    def get_worklist_writer(self, log):
        """
        They are no real worklist files for rack transfers but only sections
        in instruction files (which are handled separately).
        """
        return None

    def __repr__(self):
        str_format = '<%s index: %s, target rack: %s, source rack: %s>'
        params = (self.__class__.__name__, self.index,
                  self.target_rack.barcode, self.source_rack.barcode)
        return str_format % params


class _SeriesTool(BaseAutomationTool):
    """
    This abstract tool is the base for all worklist series tools (serial
    generation of worklist files and serial execution).
    The use of such a tool is required if the tasks for the series depend
    on one another, e.g. because the volume of for a later source well must
    be provided first.

    The tool take a list of :class:`_LiquidTransferJob` objects.
    """

    def __init__(self, transfer_jobs, log, user=None):
        """
        Constructor:

        :param transfer_jobs: :class:`LiquidTransferJob` objects mapped onto
            job indices.
        :type transfer_jobs: :class:`dict`

        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param user: The user used for the simulated executions.
        :type user: :class:`thelma.models.user.User`
        :default user: None
        """
        BaseAutomationTool.__init__(self, log=log)

        #: :class:`LiquidTransferJob` objects mapped onto job indices.
        self.transfer_jobs = transfer_jobs

        #: Stores all involved real racks (mapped onto their barcode).
        self._barcode_map = None

        #: The user used for the simulated executions.
        self.user = user

    def reset(self):
        """
        Resets all attributes except for initialisation values.
        """
        BaseAutomationTool.reset(self)
        self._barcode_map = dict()

    def run(self):
        """
        Runs the tool.
        """
        self.reset()

        self._check_input()
        if not self.has_errors(): self._execute_task()

    def _check_input(self):
        """
        Checks the input values.
        """
        self.add_debug('Check input ...')

        self._check_input_class('user', self.user, User)
        self._check_input_map_classes(self.transfer_jobs, 'transfer job map',
                    'job index', int, 'transfer job', _LiquidTransferJob)

    def _execute_task(self):
        """
        The tasks performed by the specific tool.
        """
        raise NotImplementedError('Abstract method.')

    def _update_racks(self, transfer_job):
        """
        Replaces the rack of an transfer job by updated racks.
        """
        target_barcode = transfer_job.target_rack.barcode
        if self._barcode_map.has_key(target_barcode):
            transfer_job.target_rack = self._barcode_map[target_barcode]

        if isinstance(transfer_job, (SampleTransferJob, RackSampleTransferJob)):
            source_barcode = transfer_job.source_rack.barcode
            if self._barcode_map.has_key(source_barcode):
                transfer_job.source_rack = self._barcode_map[source_barcode]

        return transfer_job

    def _execute_job(self, transfer_job):
        """
        Executes a transfer job.
        """
        executor = transfer_job.get_executor(log=self.log, user=self.user)

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


class _SeriesWorklistWriter(_SeriesTool):
    """
    This tool creates worklist files for a whole series of planned worklists.
    It is required to use (in contrast to the use of single worklist writers)
    if the worklist of a series depend on one another, e.g. because the volumes
    for a later source well must be provided first.

    Hence, between two worklists, the tool will run a executor to update
    the rack data. However, the changes of the rack will not be passed to the
    DB.

    :Note: The worklists must be provided as :class:`_LiquidTransferJob`
        objects.

    **Return Value:** A map with key = job index, value = worklist stream.
    """

    NAME = 'Series Worklist Writer'

    def __init__(self, transfer_jobs, log):
        """
        Constructor:

        :param transfer_jobs: :class:`LiquidTransferJob` objects mapped onto
            job indices.
        :type transfer_jobs: :class:`dict`

        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        _SeriesTool.__init__(self, transfer_jobs=transfer_jobs, user=None,
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
        _SeriesTool.reset(self)
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

        last_index = max(self.transfer_jobs.keys())
        for job_index in sorted(self.transfer_jobs.keys()):
            transfer_job = self.transfer_jobs[job_index]
            transfer_job = self._update_racks(transfer_job)

            # Write worklist
            writer = self.__get_writer(transfer_job)
            if writer is None and isinstance(transfer_job,
                                             RackSampleTransferJob):
                # Rack transfers are treated differently.
                self.__write_rack_transfer_section(transfer_job)
            elif writer is None:
                msg = 'Unable to find a writer for transfer job "%s".' \
                      % (transfer_job)
                self.add_warning(msg)
            else:
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
        writer = transfer_job.get_worklist_writer(log=self.log)
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
        writer = RackSampleTransferSectionWriter(log=self.log,
                                    step_number=self._rack_transfer_count,
                                    rack_transfer_job=rack_transfer_job)
        paragraph = writer.get_result()
        if paragraph is None:
            msg = 'Error when trying to generate section for rack ' \
                  'transfer job %s.' % (rack_transfer_job)
            self.add_error(msg)
        else:
            self._rack_transfer_stream.write(paragraph)


class _SeriesExecutor(_SeriesTool):
    """
    This tool executes for a whole series of worklists and/or planned liquid
    transfers (rack transfers). It is required to use (in contrast to the use
    of single executor) if the worklist of a series depend on one another,
    e.g. because the volumes for a later source well must be provided first.

    :Note: The planned liquid transfers or worklists must be provided as
        :class:`_LiquidTransferJob` objects.

    **Return Value:** A map with key = job index, value = executed item.
    """

    NAME = 'Series Executor'

    def __init__(self, transfer_jobs, user, log):
        """
        Constructor:

        :param transfer_jobs: :class:`LiquidTransferJob` objects mapped onto
            job indices.
        :type transfer_jobs: :class:`dict`

        :param user: The user used for the simulated executions.
        :type user: :class:`thelma.models.user.User`

        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        _SeriesTool.__init__(self, transfer_jobs=transfer_jobs,
                             log=log, user=user)

        #: Stores results of the transfer job execution (mapped onto indices).
        self._execution_map = None

    def reset(self):
        """
        Resets all attributes except for initialisation values.
        """
        _SeriesTool.reset(self)
        self._execution_map = dict()

    def _execute_task(self):
        """
        The tasks performed by the specific tool (planned liquid transfer
        execution).
        """
        self.add_info('Start series execution ...')

        for job_index in sorted(self.transfer_jobs.keys()):
            transfer_job = self.transfer_jobs[job_index]
            transfer_job = self._update_racks(transfer_job)

            executed_item = self._execute_job(transfer_job)
            if executed_item is None: break
            self._execution_map[job_index] = executed_item

        if not self.has_errors():
            self.return_value = self._execution_map
            self.add_info('Series execution completed.')


class RackSampleTransferWriter(_SeriesTool):
    """
    Creates an overview file for a list of rack transfer jobs.

    :Note: This writer will not conduct any checks.

    **Return Value:** Stream for an TXT file.
    """

    NAME = 'Rack Sample Transfer Writer'

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

        :param rack_transfer_jobs: The rack transfer jobs of the series
            mapped onto job indices.
        :type rack_transfer_jobs: :class:`dict`

        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        _SeriesTool.__init__(self, transfer_jobs=rack_transfer_jobs,
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
        _SeriesTool.reset(self)
        self.__stream = None
        self.__step_counter = 0

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
        for job_index in sorted(self.transfer_jobs.keys()):
            rack_transfer_job = self.transfer_jobs[job_index]
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

        writer = RackSampleTransferSectionWriter(log=self.log,
                                        step_number=self.__step_counter,
                                        rack_transfer_job=rack_transfer_job)
        paragraph = writer.get_result()
        if paragraph is None:
            msg = 'Error when trying to write paragraph for rack transfer %s.' \
                  % (rack_transfer_job)
            self.add_error(msg)
        else:
            self.__stream.write(paragraph)


class RackSampleTransferSectionWriter(BaseAutomationTool):
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
        :type rack_transfer_job: :class:`RackSampleTransferJob`

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
                                RackSampleTransferJob)

    def __write_section(self):
        """
        Writes the section.
        """
        self.add_debug('Write section ...')

        prst = self.rack_transfer_job.planned_rack_sample_transfer
        head_line = self.HEAD_LINE % (self.step_number)
        from_line = self.FROM_LINE % (self.rack_transfer_job.source_rack.barcode)
        to_line = self.TO_LINE % (self.rack_transfer_job.target_rack.barcode)
        volume_line = self.VOLUME_LINE % (prst.volume \
                                          * VOLUME_CONVERSION_FACTOR)

        translation_type = RackSectorTranslator.get_translation_behaviour(
                    source_shape=self.rack_transfer_job.source_rack.rack_shape,
                    target_shape=self.rack_transfer_job.target_rack.rack_shape,
                    number_sectors=prst.number_sectors)

        if prst.number_sectors > 1:
            if not translation_type == RackSectorTranslator.MANY_TO_ONE:
                src_addition = self.SECTOR_ADDITION \
                                % (prst.source_sector_index + 1)
                from_line += src_addition
            if not translation_type == RackSectorTranslator.ONE_TO_MANY:
                trg_addition = self.SECTOR_ADDITION \
                               % (prst.target_sector_index + 1)
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
        :class:`RackSampleTransferWriter`. However there are no checks and transfer
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
        writer = RackSampleTransferSectionWriter(log=log,
                                        step_number=rack_transfer_counter,
                                        rack_transfer_job=job_map[i])
        paragraph = writer.get_result()
        if paragraph is None: return None
        stream.write(paragraph)

    stream.seek(0)
    return stream


class SerialWriterExecutorTool(BaseAutomationTool):
    """
    A abstract base class for tools that shall print or execute worklists
    of a series.

    The distinction works via mode (see :attr:`MODE_EXECUTE` and
    :attr:`MODE_PRINT_WORKLISTS`). Execution mode requires a user to be set.
    Printing modes silently ignores the user.

    **Return Value:** a zip stream for for printing mode or executed worklists
        for execution mode (can be overwritten)
    """

    #: Marks usage of execution mode.
    MODE_EXECUTE = 'execute'
    #: Marker for the usage of worklist printing mode.
    MODE_PRINT_WORKLISTS = 'print'

    #: All allowed modes (default: execute and print).
    _MODES = [MODE_EXECUTE, MODE_PRINT_WORKLISTS]
    #: This placeholder is used to mark streams and executed items for
    #: rack sample transfer jobs.
    _RACK_SAMPLE_TRANSFER_MARKER = 'rack_sample_transfer'

    def __init__(self, mode, user=None, **kw):
        """
        Constructor:

        :param mode: :attr:`MODE_EXECUTE` or :attr:`MODE_PRINT_WORKLISTS`
        :type mode: str

        :param user: The user who conducts the DB update (required for
            execution mode).
        :type user: :class:`thelma.models.user.User`
        :default user: *None*
        """
        BaseAutomationTool.__init__(self, depending=False, **kw)

        #: Print or execute?
        self.mode = mode
        #: Required for execution mode.
        self.user = user

        #: The transfer jobs mapped onto job indices.
        self._transfer_jobs = None
        #: The worklists for each rack sample transfer job index.
        self._rack_transfer_worklists = None
        #: The indices of all rack sample transfer jobs.
        self.__rack_transfer_indices = None

    def reset(self):
        BaseAutomationTool.reset(self)
        self._transfer_jobs = dict()
        self._rack_transfer_worklists = dict()
        self.__rack_transfer_indices = set()

    def run(self):
        self.reset()
        self._check_input()

        if not self.has_errors(): self._create_transfer_jobs()
        if not self.has_errors(): self.__get_rack_transfer_job_indices()
        if not self.has_errors():
            if self.mode == self.MODE_PRINT_WORKLISTS:
                self.__print_worklists()
            else:
                self._execute_worklists()

    @classmethod
    def create_writer(cls, **kw):
        """
        Factory method returning a serial writer/executor in writer mode.
        """
        return cls(mode=cls.MODE_PRINT_WORKLISTS, **kw)

    @classmethod
    def create_executor(cls, user, **kw):
        """
        Factory method returning a serial writer/executor in execution mode.
        """
        return cls(mode=cls.MODE_EXECUTE, user=user, **kw)

    def _check_input(self):
        """
        Checks the input values.
        """
        if self._check_input_class('mode', self.mode, str):
            if not self.mode in self._MODES:
                msg = 'Unexpected mode: %s. Allowed modes: %s.' % (self.mode,
                                                     ', '.join(self._MODES))
                self.add_error(msg)

        if not self.has_errors():
            if self.mode == self.MODE_EXECUTE:
                self._check_input_class('user', self.user, User)

    def _create_transfer_jobs(self):
        """
        The transfer jobs must be mapped onto job indices. For rack sample
        transfers you also have to record the worklist name
        (:attr:`_rack_transfer_worklists`).
        """
        raise NotImplementedError('Abstract method.')

    def __get_rack_transfer_job_indices(self):
        """
        Rack sample transfer job need be treated differently (they do not
        allow for CSV worklists and the executed items are single liquid
        transfers instead of worklists).
        """
        for job_index, transfer_job in self._transfer_jobs.iteritems():
            if isinstance(transfer_job, RackSampleTransferJob):
                self.__rack_transfer_indices.add(job_index)

    def __print_worklists(self):
        """
        Called in printing mode (:attr:`MODE_PRINT_WORKLISTS`). Non-rack
        worklist for the same worklist label are merged by default.
        """
        stream_map = self.__run_serial_writer()
        if not self.has_errors():
            merge_map = self._merge_streams(stream_map)
            rack_transfer_stream = self._get_rack_transfer_stream(stream_map)
        if not self.has_errors():
            file_map = self._get_file_map(merge_map, rack_transfer_stream)
        if not self.has_errors():
            zip_stream = StringIO()
            create_zip_archive(zip_stream, file_map)
            self.return_value = zip_stream
            self.add_info('Serial working print completed.')

    def __run_serial_writer(self):
        """
        Runs the seiral worklist writer.
        """
        writer = _SeriesWorklistWriter(transfer_jobs=self._transfer_jobs,
                                       log=self.log)
        stream_map = writer.get_result()

        if stream_map is None:
            msg = 'Error when running serial worklist printer.'
            self.add_error(msg)
            return None
        else:
            return stream_map

    def _merge_streams(self, stream_map):
        """
        By default, streams for the same worklist are merged.
        """
        sorted_streams = dict()
        for job_index, stream in stream_map.iteritems():
            if job_index in self.__rack_transfer_indices: continue
            transfer_job = self._transfer_jobs[job_index]
            worklist_label = transfer_job.planned_worklist.label
            if sorted_streams.has_key(worklist_label):
                worklist_map = sorted_streams[worklist_label]
            else:
                worklist_map = dict()
                sorted_streams[worklist_label] = worklist_map
            worklist_map[job_index] = stream

        merged_streams = dict()
        for worklist_label, worklist_map in sorted_streams.iteritems():
            merged_stream = merge_csv_streams(worklist_map)
            merged_streams[worklist_label] = merged_stream

        return merged_streams

    def _get_rack_transfer_stream(self, stream_map):
        """
        Returns the stream for the rack sample transfer jobs stream.
        There should be only one stream.
        """
        rack_transfer_streams = dict()
        for job_index in self.__rack_transfer_indices:
            if not stream_map.has_key(job_index): continue
            rack_transfer_streams[job_index] = stream_map[job_index]

        if len(rack_transfer_streams) > 1:
            msg = 'There is more than one rack transfer stream in the ' \
                  'stream map!'
            self.add_error(msg)
            return None

        if len(rack_transfer_streams) > 0:
            return rack_transfer_streams.values()[0]
        else:
            return None

    def _get_file_map(self, merged_stream_map, rack_sample_transfer_stream):
        """
        Returns a map containing the file name (key) for each the merged
        stream (value).
        The merged stream map is derived from :func:`_merge_streams`.
        By default, streams are mapped on the worklist label (merged).
        The rack sample transfer stream can be *None*.
        """
        raise NotImplementedError('Abstract method.')

    def _execute_worklists(self):
        """
        Called in execution mode (:attr:`MODE_PRINT_WORKLISTS`).
        The executed rack sample transfers have to be summarized to jobs
        first.
        """
        executed_worklists = self._get_executed_worklists()
        if executed_worklists is not None:
            self.return_value = executed_worklists
            self.add_info('Serial worklist execution completed.')

    def _get_executed_worklists(self):
        """
        Runs the :class:`_SeriesExecutor`.
        """
        executor = _SeriesExecutor(transfer_jobs=self._transfer_jobs,
                                   user=self.user, log=self.log)
        executed_items = executor.get_result()
        if executed_items is None:
            msg = 'Error when running serial worklist executor!'
            self.add_error(msg)
            return None
        else:
            return self.__get_executed_worklists(executed_items)

    def __get_executed_worklists(self, executed_items):
        """
        For rack sample job, the executor returns no worklists but executed
        liquid transfer. The worklists for the job must be registered in
        the :attr:`_rack_transfer_worklists` map by the subclass implementation.
        """
        executed_worklists = dict()
        other_worklists = []

        for job_index, executed_item in executed_items.iteritems():
            if not job_index in self.__rack_transfer_indices:
                other_worklists.append(executed_item)
                continue

            worklist = self._rack_transfer_worklists[job_index]
            worklist_label = worklist.label
            if executed_worklists.has_key(worklist_label):
                executed_worklist = executed_worklists[worklist]
            else:
                executed_worklist = ExecutedWorklist(worklist)
                executed_worklists[worklist_label] = executed_worklist
            elt = executed_items[job_index]
            executed_worklist.executed_liquid_transfers.append(elt)

        return other_worklists + executed_worklists.values()
