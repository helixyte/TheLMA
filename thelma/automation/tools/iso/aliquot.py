"""
Creation, worklist writing and execution of additional aliquot plates
after ISO processing.

Additional aliquot plates can only be created for 384-well screening scenarios.
The worklist tools deal only with the sample transfer into the aliquot plates.
Buffer addition and dilution are assumed to have taken place at that stage.

AAB
"""
from StringIO import StringIO
from thelma.automation.tools.iso.isoprocessing import IsoProcessingTool
from thelma.automation.tools.iso.processingworklist \
    import IsoAliquotBufferWorklistGenerator
from thelma.automation.tools.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.tools.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.tools.semiconstants import get_item_status_future
from thelma.automation.tools.semiconstants import get_reservoir_spec
from thelma.automation.tools.worklists.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.worklists.series import ContainerDilutionJob
from thelma.automation.tools.worklists.series import RackTransferJob
from thelma.automation.tools.worklists.series import SeriesExecutor
from thelma.automation.tools.worklists.series import SeriesWorklistWriter
from thelma.automation.tools.writers import create_zip_archive
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import IsoAliquotPlate
from thelma.models.liquidtransfer import ExecutedWorklist
from thelma.models.user import User
import logging

__docformat__ = 'reStructuredText en'

__all__ = ['IsoAliquotCreator',
           'IsoAliquotTool',
           'IsoAliquotWorklistWriter',
           'IsoAliquotExecutor']


class IsoAliquotCreator(IsoProcessingTool):
    """
    Creates another aliquot for an ISO (if there is still enough liquid left
    in the preparation plate).

    :Note: Additional plates are marker by the addition of a marker in their
        plate label. The marker is a constant stored as
        :attr:`thelma.models.iso.IsoAliquotPlate.ADDITIONAL_PLATE_MARKER`)

    **Return Value:** updated ISO
    """
    NAME = 'ISO Aliquot Creator'

    def __init__(self, iso, logging_level=logging.WARNING,
                 add_default_handlers=False):
        """
        Constructor:

        :param iso: The ISO for which to create the aliquot.
        :type iso: :class:`thelma.models.iso.Iso`

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """
        IsoProcessingTool.__init__(self, iso=iso,
                                   logging_level=logging_level,
                                   add_default_handlers=add_default_handlers)

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start aliquot creation ...')

        self._check_input()
        if not self.has_errors():
            self._fetch_preparation_data()
            self._fetch_aliquot_plates()
        if not self.has_errors(): self._determine_scenario()
        if not self.has_errors(): self.__check_worklist_series_execution()
        if not self.has_errors(): self._fetch_processing_series()
        if not self.has_errors(): self.__create_aliquot_plate()
        if not self.has_errors():
            self.iso.status = ISO_STATUS.REOPENED
            self.return_value = self.iso
            self.add_info('Aliquot creation completed.')

    def _determine_scenario(self):
        """
        Determines the ISO scenario.
        """
        IsoProcessingTool._determine_scenario(self)

        if not self._is_384_screening:
            msg = 'Aliquots can only be created for 384-well screening ISOs!'
            self.add_error(msg)

    def __check_worklist_series_execution(self):
        """
        Makes sure the ISO processing worklist has been executed before.
        Since we cannot determine this directly (all ISOs of a request share
        the same worklists) we use the status of the other aliquot plates
        to determine the status.
        """
        self.add_debug('Check for worklist series execution ...')

        for plate in self._aliquot_plates:
            if plate.status.name == ITEM_STATUS_NAMES.FUTURE:
                msg = 'You cannot create an additional aliquot plates as ' \
                      'long as you have not executed the ISO processing ' \
                      'series for all other aliquot plates!'
                self.add_error(msg)
                break

    def __create_aliquot_plate(self):
        """
        Creates the aliquot plate.
        """
        self.add_debug('Create aliquot plate ...')

        plate_specs = self.__get_aliquot_plate_specs()

        if not plate_specs is None:
            self.__check_preparation_plate_volumes(plate_specs)
            if not self.has_errors():
                label = '%s%i_%s' % (IsoAliquotPlate.ADDITIONAL_PLATE_MARKER,
                                     (len(self._aliquot_plates) + 1),
                                     self.iso.label)
                plate = plate_specs.create_rack(label=label,
                                                status=get_item_status_future())
                IsoAliquotPlate(iso=self.iso, plate=plate)

    def __check_preparation_plate_volumes(self, plate_specs):
        """
        Checks whether there is still enough volume in the preparation plate.
        """
        self.add_debug('Check preparation plate volumes ...')

        worklist = self._get_aliquot_transfer_worklist()
        prt = worklist.planned_transfers[0]
        transfer_volume = prt.volume * VOLUME_CONVERSION_FACTOR
        required_volume = plate_specs.well_specs.dead_volume \
                          * VOLUME_CONVERSION_FACTOR \
                          + transfer_volume

        no_sample = []
        not_enough_volume = []
        for container in self._preparation_plate.containers:
            rack_pos = container.location.position
            prep_pos = self._preparation_layout.get_working_position(rack_pos)
            if prep_pos is None: continue
            if prep_pos.is_inactivated: continue

            sample = container.sample
            if sample is None:
                no_sample.append(rack_pos.label)
                continue

            sample_volume = sample.volume * VOLUME_CONVERSION_FACTOR
            if (sample_volume - required_volume) < -0.01:
                info = '%s (%.1f ul)' % (rack_pos.label, sample_volume)
                not_enough_volume.append(info)

        if len(no_sample) > 0:
            msg = 'Some wells in the preparation plate do not contain a ' \
                  'sample although there should be one: %s.' % (no_sample)
            self.add_error(msg)
        if len(not_enough_volume) > 0:
            msg = 'The following well do not contain enough volume for ' \
                  'another aliquot plate anymore: %s. Required volume: ' \
                  '%1.f ul. ' % (not_enough_volume, required_volume)
            self.add_error(msg)

    def __get_aliquot_plate_specs(self):
        """
        Fetches the plate specs for the new aliquot plate from one of the
        existing aliquot plates.
        """
        self.add_debug('Fetch plate specs ...')

        plate_specs_set = set()

        for plate in self._aliquot_plates:
            plate_specs_set.add(plate.specs)

        if len(plate_specs_set) > 1:
            msg = 'The existing aliquot plates have different plate specs: ' \
                  '%s!' % (list(plate_specs_set))
            self.add_error(msg)
            return None
        else:
            return list(plate_specs_set)[0]


class IsoAliquotTool(IsoProcessingTool):
    """
    A base class for ISO aliquot tools fetching the ISO data and generating
    the required transfer jobs. The data will be used by a subclass
    (DB execution or generation of robot worklist files).

    There is two jobs: The transfer job deals with the transer of sample from
    the preparation plate to the aliquot plate where is the buffer job deals
    with the addition of buffer to aliquot plate. The buffer job is only
    required if there are different sample concentrations in the preparation
    plate and the aliquot plate (this information has already determined
    before - if the worklist is not required it has not been generated).

    **Return Value:** Depending on the subclass.
    """

    #: The job index for the transfer job.
    TRANSFER_JOB_INDEX = 0
    #: The job index for the buffer job.
    BUFFER_JOB_INDEX = 1

    def __init__(self, iso, barcode, logging_level=logging.WARNING,
                 add_default_handlers=False):
        """
        Constructor:

        :param iso: The ISO to use.
        :type iso: :class:`thelma.models.iso.Iso`

        :param barcode: The barcode of the addressed aliquot plate.
        :type barcode: :class:`basestring`

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """

        IsoProcessingTool.__init__(self, iso=iso,
                                   logging_level=logging_level,
                                   add_default_handlers=add_default_handlers)

        #: The barcode of the addressed aliquot plate.
        self.barcode = barcode
        #: The aliquot plate for which to generate the worklist files
        #: (:class:`thelma.models.automation.Plate`).
        self._aliquot_plate = None

        #: The worklist for the transfer of sample from the preparation plate
        #: to aliquot plates.
        self._transfer_worklist = None
        #: The worklist for the addition of buffer into the aliquot plate
        #: (applies only to cases with different concentrations in both plates).
        self._aliquot_buffer_worklist = None

        #: The transfer jobs for the aliquot processing.
        self._transfer_jobs = None

    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        IsoProcessingTool.reset(self)
        self._aliquot_plate = None
        self._transfer_worklist = None
        self._aliquot_buffer_worklist = None
        self._transfer_jobs = []

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start worklist file creation ...')

        self._check_input()
        if not self.has_errors(): self.__get_iso_aliquot_plate()
        if not self.has_errors():
            self._fetch_preparation_data()
            self._fetch_processing_series()
        if not self.has_errors():
            self._find_ignored_positions()
            self._transfer_worklist = self._get_aliquot_transfer_worklist()
            self._get_aliquot_buffer_worklist()
        if not self.has_errors():
            self._create_transfer_jobs()
            self._execute_task()

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        IsoProcessingTool._check_input(self)
        self._check_input_class('barcode', self.barcode, basestring)

    def __get_iso_aliquot_plate(self):
        """
        Fetches the ISO aliquot plate for the given barcode.
        """
        self.add_debug('Fetch ISO aliquot plate ...')

        for iap in self.iso.iso_aliquot_plates:
            plate = iap.plate
            if plate.barcode == str(self.barcode):
                self._aliquot_plate = plate
                break

        if self._aliquot_plate is None:
            msg = 'There is no aliquot plate with the barcode "%s" in ' \
                  'this ISO!' % (self.barcode)
            self.add_error(msg)

    def _get_aliquot_buffer_worklist(self):
        """
        Fetches the worklist for the addition of buffer into the aliquot plate
        (if there is any).
        """
        self.add_debug('Fetch aliquot buffer worklist ...')

        for worklist in self._processing_series:
            if IsoAliquotBufferWorklistGenerator.WORKLIST_SUFFIX \
                                                        in worklist.label:
                self._aliquot_buffer_worklist = worklist

    def _create_transfer_jobs(self):
        """
        Generates the transfer jobs.
        """
        self.add_debug('Generate transfer jobs ...')

        prt = self._transfer_worklist.planned_transfers[0]
        transfer_job = RackTransferJob(index=self.TRANSFER_JOB_INDEX,
                                   planned_rack_transfer=prt,
                                   target_rack=self._aliquot_plate,
                                   source_rack=self._preparation_plate)
        self._transfer_jobs.append(transfer_job)

        if not self._aliquot_buffer_worklist is None:
            quarter_rs = get_reservoir_spec(
                                        RESERVOIR_SPECS_NAMES.QUARTER_MODULAR)
            buffer_job = ContainerDilutionJob(index=self.BUFFER_JOB_INDEX,
                        planned_worklist=self._aliquot_buffer_worklist,
                        target_rack=self._aliquot_plate,
                        reservoir_specs=quarter_rs,
                        source_rack_barcode=self.ALIQUOT_BUFFER_PLATE_BARCODE,
                        ignored_positions=self._ignored_positions,
                        is_biomek_transfer=True)
            self._transfer_jobs.append(buffer_job)

    def _execute_task(self):
        """
        This is the actual task carried out by the specific subclass.
        """
        self.add_error('Abstract method: _execute_task()')


class IsoAliquotWorklistWriter(IsoAliquotTool):
    """
    This tool generates worklist files for an ISO aliquot that has been created
    later.

    **Return Value:** The worklist files as zip stream.
    """

    NAME = 'ISO Aliquot Worklist Writer'

    def __init__(self, iso, barcode, logging_level=logging.WARNING,
                 add_default_handlers=False):
        """
        Constructor:

        :param iso: The ISO to use.
        :type iso: :class:`thelma.models.iso.Iso`

        :param barcode: The barcode of the addressed aliquot plate.
        :type barcode: :class:`basestring`

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """
        IsoAliquotTool.__init__(self, iso=iso, barcode=barcode,
                                logging_level=logging_level,
                                add_default_handlers=add_default_handlers)

        #: The streams for the ISO processing series mapped onto job indices.
        self.__stream_map = None
        #: The zip stream containing the zip archive.
        self.__zip_stream = None

    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        IsoAliquotTool.reset(self)
        self.__stream_map = None
        self.__zip_stream = None

    def _execute_task(self):
        """
        This is the actual task carried out by the specific subclass.
        """
        self.add_info('Start worklist file generation ...')

        if self._aliquot_buffer_worklist is not None:
            msg = 'Attention! The transfer from the preparation plate to the ' \
                  'aliquot plates includes a dilution. You have to add ' \
                  'buffer to the aliquot plates (see files for details)!'
            self.add_warning(msg)

        self.__create_streams()
        if not self.has_errors():
            self.__create_zip_archive()
            self.return_value = self.__zip_stream
            self.add_info('Worklist file generation completed.')

    def __create_streams(self):
        """
        Creates the output streams.
        """
        self.add_debug('Create ouput streams ...')

        # Streams for non rack transfers.
        series_writer = SeriesWorklistWriter(transfer_jobs=self._transfer_jobs,
                                             log=self.log)
        self.__stream_map = series_writer.get_result()
        if self.__stream_map is None:
            msg = 'Error during serial worklist file generation.'
            self.add_error(msg)

    def __create_zip_archive(self):
        """
        Creates and fill the zip archive.
        """
        self.add_debug('Create zip archive.')

        zip_map = dict()

        cybio_fn = self.CYBIO_FILE_SUFFIX % (self._aliquot_plate.label)
        zip_map[cybio_fn] = self.__stream_map[self.TRANSFER_JOB_INDEX]

        if not self._aliquot_buffer_worklist is None:
            buffer_fn = self.ALIQUOT_BUFFER_FILE_SUFFIX \
                        % (self._aliquot_plate.label)
            zip_map[buffer_fn] = self.__stream_map[self.BUFFER_JOB_INDEX]

        self.__zip_stream = StringIO()
        create_zip_archive(zip_stream=self.__zip_stream, stream_map=zip_map)


class IsoAliquotExecutor(IsoAliquotTool):
    """
    This tool executes worklists for an ISO aliquot that has been created
    later.

    **Return Value:** updated ISO
    """

    NAME = 'ISO Aliquot Executor'

    def __init__(self, iso, barcode, user,
                 logging_level=logging.WARNING,
                 add_default_handlers=False):
        """
        Constructor:

        :param iso: The ISO to use.
        :type iso: :class:`thelma.models.iso.Iso`

        :param barcode: The barcode of the addressed aliquot plate.
        :type barcode: :class:`basestring`

        :param user: The user conducting the execution.
        :type user: :class:`thelma.models.user.User`

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """
        IsoAliquotTool.__init__(self, iso=iso, barcode=barcode,
                                logging_level=logging_level,
                                add_default_handlers=add_default_handlers)

        #: The user conducting the execution.
        self.user = user

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        IsoAliquotTool._check_input(self)
        self._check_input_class('user', self.user, User)

    def _execute_task(self):
        """
        This is the actual task carried out by the specific subclass.
        """
        self.add_info('Start transfer execution ...')

        self.__check_for_previous_execution()
        if not self.has_errors():
            executor = SeriesExecutor(transfer_jobs=self._transfer_jobs,
                                      user=self.user, log=self.log)
            executed_items = executor.get_result()

            if executed_items is None:
                msg = 'Error during serial transfer execution.'
                self.add_error(msg)
            else:
                executed_rt = executed_items[self.TRANSFER_JOB_INDEX]
                ExecutedWorklist(planned_worklist=self._transfer_worklist,
                                 executed_transfers=[executed_rt])
                self.return_value = self.iso
                self.add_info('Transfer execution completed.')

    def __check_for_previous_execution(self):
        """
        Makes sure the execution has not taken place before
        (Searching for executed worklist does not help here, since all ISOs
        share the same series. Thus, we check the status of the aliquot plates.)
        """
        self.add_debug('Check for previous execution ...')

        if self._aliquot_plate.status.name == ITEM_STATUS_NAMES.MANAGED:
            msg = 'The transfer for this aliquot plate has already been ' \
                  'executed before!'
            self.add_error(msg)

        if not self.has_errors():
            if not self.iso.status == ISO_STATUS.REOPENED:
                msg = 'Unexpected ISO status: "%s". Expected: "%s".' \
                      % (self.iso.status, ISO_STATUS.REOPENED)
                self.add_error(msg)
