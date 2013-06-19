"""
These tools deals with the ISO processing worklist series
(generation of BioMek worklists and DB execution) and the generation
and processing of additional aliquot plates.

The series is created during ISO generation. It comprises the addition of
buffer, the conduction of dilutions within the preparation plate (optional)
and the transfer of sample from the preparation to the aliquot plates. The
stock transfer of sample can be covered as well, however, the referring
worklists are stored in the corresponding sample stock rack entities.

In manual optimisation scenarios the series covers only the addition of buffer
(and potentially the addition of samples from the stock), if a dilution is
required. If there is no dilution required the series is *None*.

AAB
"""
from StringIO import StringIO
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.iso.prep_utils import PrepIsoLayoutConverter
from thelma.automation.tools.iso.processingworklist \
    import IsoAliquotBufferWorklistGenerator
from thelma.automation.tools.iso.stocktransfer \
    import IsoSampleStockRackJobCreator
from thelma.automation.tools.iso.stocktransfer \
    import IsoSampleStockRackWorklistWriter
from thelma.automation.tools.iso.stocktransfer import IsoSampleStockRackVerifier
from thelma.automation.tools.iso.stocktransfer import StockTransferExecutor
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.tools.semiconstants import PIPETTING_SPECS_NAMES
from thelma.automation.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.tools.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.tools.semiconstants import get_reservoir_spec
from thelma.automation.tools.worklists.series import ContainerDilutionJob
from thelma.automation.tools.worklists.series import ContainerTransferJob
from thelma.automation.tools.worklists.series import RackTransferJob
from thelma.automation.tools.worklists.series import SeriesExecutor
from thelma.automation.tools.worklists.series import SeriesWorklistWriter
from thelma.automation.tools.writers import create_zip_archive
from thelma.automation.tools.writers import merge_csv_streams
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import Iso
from thelma.models.liquidtransfer import ExecutedRackTransfer
from thelma.models.liquidtransfer import ExecutedWorklist
import logging

__docformat__ = 'reStructuredText en'

__all__ = ['IsoProcessingTool',
           'IsoProcessingSeriesTool',
           'IsoProcessingWorklistWriter',
           'IsoProcessingExecutor']


class IsoProcessingTool(BaseAutomationTool): #pylint: disable=W0223
    """
    A base class for ISO processing and ISO aliquot tools. It provides methods
    for the fetching of ISO data but no :func:`run` method.

    **Return Value:** Depending on the subclass.
    """

    #: The barcode for the (temporary) annealing buffer plate.
    ALIQUOT_BUFFER_PLATE_BARCODE = 'aliquot_buffer_plate'

    #: The suffix for the file name of the aliquot buffer CSV worklist (which
    #: deals with addition of annealing buffer into the aliquot plates - applies
    #: only to 384-well screening ISO which separate preparation
    #: concentrations). The first part of the file name will be the ISO label.
    ALIQUOT_BUFFER_FILE_SUFFIX = '%s_aliquot_buffer.csv'
    #: The suffix for the file name of the cybio file (only applicable if there
    #: is a rack transfer in the worklist series (384-well screening ISOs only).
    # The first part of the file name fill be the ISO label.
    CYBIO_FILE_SUFFIX = '%s_cybio_transfers.txt'

    #: In these experiment types we do not have to have an aliquot plate.
    NO_ALIQUOT_PLATE_TYPES = [EXPERIMENT_SCENARIOS.MANUAL,
                              EXPERIMENT_SCENARIOS.ORDER_ONLY]


    def __init__(self, iso, logging_level=logging.WARNING,
                 add_default_handlers=False):
        """
        Constructor:

        :param iso: The ISO to use.
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
        BaseAutomationTool.__init__(self, logging_level=logging_level,
                                    add_default_handlers=add_default_handlers,
                                    depending=False)

        #: The ISO to use.
        self.iso = iso


        #: In 384-well screening cases, you can order additional aliquot plates.
        self._is_384_screening = None
        #: In some experiment types there might be no aliquot plates or no
        #: processing worklist series at all.
        self._experiment_type = None

        #: The preparation layout of the ISO.
        self._preparation_layout = None
        #: The preparation plate of the (:class:`thelma.model.rack.Plate).
        self._preparation_plate = None
        #: The aliquot plates of the ISO (:class:`thelma.model.rack.Plate).
        self._aliquot_plates = None

        #: The worklist series for the ISO processing.
        self._processing_series = None
        #: A list of rack position to be ignore during execution or worklist
        #: generation. The rack position are floating position for which
        #: there were no molecule design pools left anymore.
        self._ignored_positions = None

    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        BaseAutomationTool.reset(self)
        self._experiment_type = None
        self._is_384_screening = None
        self._preparation_layout = None
        self._preparation_plate = None
        self._aliquot_plates = []
        self._processing_series = None
        self._ignored_positions = []

    def _check_input(self):
        """
        Checks the initialisation values ...
        """
        self.add_debug('Check input values ...')
        self._check_input_class('ISO', self.iso, Iso)

    def _fetch_preparation_data(self):
        """
        Fetches the preparation plate, the aliquot plates and the
        preparation layout.
        """
        self.add_debug('Fetch preparation data ...')

        converter = PrepIsoLayoutConverter(rack_layout=self.iso.rack_layout,
                                           log=self.log)
        self._preparation_layout = converter.get_result()
        if self._preparation_layout is None:
            msg = 'Error when trying to convert preparation plate layout.'
            self.add_error(msg)

        self._preparation_plate = self.iso.preparation_plate
        if self._preparation_plate is None:
            msg = 'Could not find preparation plate for this ISO!'
            self.add_error(msg)

    def _fetch_aliquot_plates(self):
        """
        Fetches the aliquot plates for the ISO.
        """
        self.add_debug('Fetch aliquot plates ...')

        for iap in self.iso.iso_aliquot_plates:
            plate = iap.plate
            if plate is None:
                msg = 'Invalid aliquot plate!'
                self.add_error(msg)
                break
            self._aliquot_plates.append(iap.plate)

        must_have_aliquot_plate = not (self._experiment_type.id \
                                       in self.NO_ALIQUOT_PLATE_TYPES)
        if len(self._aliquot_plates) < 1 and must_have_aliquot_plate:
            msg = 'Could not find aliquot plates for this ISO!'
            self.add_error(msg)

    def _fetch_processing_series(self):
        """
        Fetches the ISO processing series
        """
        self._processing_series = self.iso.iso_request.worklist_series

        must_have_wl_series = not (self._experiment_type.id \
                                   in self.NO_ALIQUOT_PLATE_TYPES)

        if self._processing_series is None and not must_have_wl_series:
            pass
        elif self._processing_series is None and must_have_wl_series:
            msg = 'There is no processing series for this ISO request!'
            self.add_error(msg)
        elif len(self._processing_series) < 2 and must_have_wl_series:
            msg = 'The processing series for this ISO request is incomplete ' \
                  '(length: %i).' % (len(self._processing_series))
            self.add_error(msg)

    def _determine_scenario(self):
        """
        Determines the ISO scenario.
        """
        self.add_debug('Determine scenario ...')

        self._experiment_type = self.iso.iso_request.experiment_metadata_type

        if self._experiment_type.id in self.NO_ALIQUOT_PLATE_TYPES:
            self._is_384_screening = False
        elif self._preparation_layout.shape.name == RACK_SHAPE_NAMES.SHAPE_96:
            self._is_384_screening = False
        else:
            if self._experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
                self._is_384_screening = True
            else:
                self._is_384_screening = False

    def _find_ignored_positions(self):
        """
        Finds floating position for which there are no floating molecule pools
        left anymore (comparison with buffer dilution worklist).
        """
        self.add_debug('Find empty floating positions ...')

        buffer_worklist = None
        worklist_map = dict()

        if self._processing_series is not None:
            for wl in self._processing_series: worklist_map[wl.index] = wl
            buffer_worklist = worklist_map[min(worklist_map.keys())]
            for pcd in buffer_worklist.planned_transfers:
                rack_pos = pcd.target_position
                prep_pos = self._preparation_layout.get_working_position(
                                                                    rack_pos)
                if prep_pos is None:
                    self._ignored_positions.append(rack_pos)
                elif prep_pos.is_inactivated:
                    self._ignored_positions.append(rack_pos)

    def _get_aliquot_transfer_worklist(self):
        """
        Get the planned worklist for the transfer of samples from the
        preparation plate to the aliquot plate in screening cases. The referring
        worklist is always the last one in the series.
        """
        self.add_debug('Fetch aliquot rack transfer  ...')

        worklist_map = dict()
        for worklist in self._processing_series:
            worklist_map[worklist.index] = worklist

        transfer_index = max(worklist_map.keys())
        transfer_worklist = worklist_map[transfer_index]

        if len(transfer_worklist.planned_transfers) > 1:
            msg = 'There is more than one transfer in the transfer worklist!'
            self.add_error(msg)
            return None

        return transfer_worklist


class IsoProcessingSeriesTool(IsoProcessingTool):
    """
    A base class for ISO series processing tools fetching the ISO data. The
    data will be used by an series tool run (DB execution or generation of
    robot worklist files).

    :Note: The stock transfer might be included in the execution. However,
        an output file is *not* created (use the
        IsoSampleStockRackWorklistWriter for that purpose.)

    **Return Value:** Depending on the subclass.
    """

    #: The barcode for the (temporary) annealing buffer plate.
    ANNEALING_BUFFER_PLATE_BARCODE = 'buffer_plate'

    #: Shall warnings be recorded?
    RECORD_WARNINGS = True

    #: The maximum number of transfer jobs that might be included.
    MAX_NUMBER_TRANSFER_JOBS = 4

    def __init__(self, iso, logging_level=logging.WARNING,
                 add_default_handlers=False):
        """
        Constructor:

        :param iso: The ISO to process.
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

        #: Shall the stock transfer jobs be included?
        self._including_stock_transfer = None
        #: The ISO sample stock racks mapped onto sector indices.
        self.__sample_stock_racks = None

        #: The transfer jobs for the series
        self._transfer_jobs = None

        #: The index of the first rack transfer job (384-well screening only).
        self._first_rack_transfer_index = None

        #: The job indices of the aliquot transfer jobs (applies only if there
        #: is more than one aliquot plate).
        self._aliquot_transfer_job_indices = None
        #: The job indices for the aliquot buffer dilution jobs (applies only
        #: for 384-well screening cases with aliquot dilutions).
        self._aliquot_buffer_job_indices = None

    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        IsoProcessingTool.reset(self)
        self._including_stock_transfer = True
        self.__sample_stock_racks = dict()
        self._transfer_jobs = []
        self._first_rack_transfer_index = None
        self._aliquot_transfer_job_indices = []
        self._aliquot_buffer_job_indices = []

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start ISO processing tool ...')

        self._check_input()
        if not self.has_errors(): self._fetch_preparation_data()
        if not self.has_errors(): self._determine_scenario()
        if not self.has_errors():
            self._fetch_aliquot_plates()
            self.__fetch_stock_data()
            self._fetch_processing_series()
        if not self.has_errors():
            self.__determine_state()
            self._find_ignored_positions()
        if not self.has_errors() and self._including_stock_transfer:
            self.__verify_stock_racks()
            if not self.has_errors(): self._fetch_stock_transfer_jobs()
        if not self.has_errors() and not self._processing_series is None:
            if self._experiment_type.id == EXPERIMENT_SCENARIOS.MANUAL:
                self.__create_transfer_jobs_for_manual()
            else:
                self.__create_transfer_jobs()

        if not self.has_errors() and len(self._transfer_jobs) < 1:
            msg = 'This ISO does not require further processing. The ' \
                  'preparation plate can be passed to the lab directly.'
            self.add_error(msg)

        if not self.has_errors(): self._execute_task()

    def __fetch_stock_data(self):
        """
        Fetches the data required for the stock transfer.
        """
        self.add_debug('Fetch stock data ...')

        for issr in self.iso.iso_sample_stock_racks:
            sector_index = issr.sector_index
            self.__sample_stock_racks[sector_index] = issr

        if len(self.__sample_stock_racks) < 1:
            msg = 'There are no ISO sample stock racks for this ISO!'
            self.add_error(msg)

    def __determine_state(self):
        """
        Determines whether the stock transfer has already been conducted.
        The stock transfer is supposed to be executed if there the preparation
        plate is not having a future state or if there are executed worklists
        in an ISO sample stock rack.
        """
        self.add_debug('Determine preparation plate status ...')

        if self._preparation_plate.status.name == ITEM_STATUS_NAMES.FUTURE:
            self._including_stock_transfer = True
        else:
            include = True
            for issr in self.__sample_stock_racks.values():
                if len(issr.planned_worklist.executed_worklists) > 0:
                    include = False
                    break
            self._including_stock_transfer = include

        if not self._including_stock_transfer and \
                    self._experiment_type.id == EXPERIMENT_SCENARIOS.ORDER_ONLY:
            msg = 'The transfer from the stock to preparation plate has ' \
                  'already taken place for this ISO. ISOs for "%s" scenarios ' \
                  'are already completed with this step and do not require ' \
                  'further processing.' % (self._experiment_type.display_name)
            self.add_error(msg)

        self.add_info('Include stock transfer: %s' \
                      % self._including_stock_transfer)

    def __verify_stock_racks(self):
        """
        Verifies the ISO sample stock racks.
        """
        self.add_debug('Verify ISO sample stock racks ...')

        verifier = IsoSampleStockRackVerifier(log=self.log,
                        preparation_layout=self._preparation_layout,
                        sample_stock_racks=self.__sample_stock_racks)

        compatible = verifier.get_result()
        if compatible is None:
            msg = 'Error in the stock rack verifier!'
            self.add_error(msg)
        elif not compatible:
            msg = 'The stock racks are not compatible with the ISO!'
            self.add_error(msg)

    def _fetch_stock_transfer_jobs(self):
        """
        Fetches the stock transfer jobs.
        """
        self.add_debug('Get stock transfer job ...')

        job_creator = IsoSampleStockRackJobCreator(log=self.log,
                            sample_stock_racks=self.__sample_stock_racks,
                            preparation_plate=self._preparation_plate)
        self._transfer_jobs = job_creator.get_result()

        if self._transfer_jobs is None:
            msg = 'Error when trying to generate stock transfer jobs.'
            self.add_error(msg)

    def __create_transfer_jobs_for_manual(self):
        """
        Creates the transfer jobs for manual optimisation cases.
        """
        self.add_debug('Create transfer jobs for manual optimisation ...')

        if not len(self._processing_series) == 1:
            msg = 'There unknown worklists in the worklists series.'
            self.add_error(msg)
        else:
            worklist = self._processing_series.planned_worklists[0]
            quarter_rs = get_reservoir_spec(
                                    RESERVOIR_SPECS_NAMES.QUARTER_MODULAR)
            transfer_job = ContainerDilutionJob(
                        index=self.MAX_NUMBER_TRANSFER_JOBS,
                        planned_worklist=worklist,
                        target_rack=self._preparation_plate,
                        reservoir_specs=quarter_rs,
                        source_rack_barcode=self.ANNEALING_BUFFER_PLATE_BARCODE,
                        pipetting_specs=PIPETTING_SPECS_NAMES.BIOMEK)
            transfer_job.min_transfer_volume = 1
            self._transfer_jobs.append(transfer_job)

    def __create_transfer_jobs(self):
        """
        Creates the transfer jobs for the transfer tool following.
        """
        self.add_debug('Create series transfer jobs ...')

        job_index_modifier = self.MAX_NUMBER_TRANSFER_JOBS
        quarter_rs = get_reservoir_spec(RESERVOIR_SPECS_NAMES.QUARTER_MODULAR)

        sorted_worklists = dict()
        for worklist in self._processing_series:
            sorted_worklists[worklist.index] = worklist

        wl_indices = sorted_worklists.keys()
        wl_indices.sort()

        has_screening_dilutions = False
        has_aliquot_dilution = False
        last_index = wl_indices[-1]
        for wl_index in wl_indices:
            worklist = sorted_worklists[wl_index]
            job_index = wl_index + job_index_modifier
            if wl_index == 0: # buffer dilution
                transfer_job = ContainerDilutionJob(index=job_index,
                        planned_worklist=worklist,
                        target_rack=self._preparation_plate,
                        reservoir_specs=quarter_rs,
                        source_rack_barcode=self.ANNEALING_BUFFER_PLATE_BARCODE,
                        ignored_positions=self._ignored_positions,
                        pipetting_specs=PIPETTING_SPECS_NAMES.BIOMEK)
            elif wl_index == last_index:
                continue # aliquot plate transfers are done later
            elif IsoAliquotBufferWorklistGenerator.WORKLIST_SUFFIX \
                                                        in worklist.label:
                has_aliquot_dilution = True
                continue # aliquot dilution plates are done later
            elif not self._is_384_screening:
                # optimisation dilutions are container transfer worklists
                transfer_job = ContainerTransferJob(index=job_index,
                        planned_worklist=worklist,
                        target_rack=self._preparation_plate,
                        source_rack=self._preparation_plate,
                        ignored_positions=self._ignored_positions,
                        pipetting_specs=PIPETTING_SPECS_NAMES.BIOMEK)
            else:
                has_screening_dilutions = True
                if self._first_rack_transfer_index is None:
                    self._first_rack_transfer_index = job_index
                # screening dilution are rack transfers
                for prt in worklist.planned_transfers:
                    rt_job = RackTransferJob(index=job_index,
                            planned_rack_transfer=prt,
                            target_rack=self._preparation_plate,
                            source_rack=self._preparation_plate)
                    self._transfer_jobs.append(rt_job)
                    job_index += 1
                    job_index_modifier += 1
                continue

            self._transfer_jobs.append(transfer_job)

        if has_screening_dilutions:
            msg = 'Attention! There is an dilution step that needs to ' \
                  'be carried out with the CyBio before the preparation ' \
                  'plate is replicated!'
            if self.RECORD_WARNINGS: self.add_warning(msg)
        if has_aliquot_dilution:
            msg = 'Attention! The transfer from the preparation plate to the ' \
                  'aliquot plates includes a dilution. You have to add ' \
                  'buffer to the aliquot plates (see files for details)!'
            if self.RECORD_WARNINGS: self.add_warning(msg)
            aliquot_buffer_worklist = sorted_worklists[(last_index - 1)]

        aliquot_worklist = sorted_worklists[last_index]
        for plate in self._aliquot_plates:
            job_index = last_index + job_index_modifier

            if self._is_384_screening:

                if has_aliquot_dilution:
                    buffer_job = ContainerDilutionJob(index=job_index,
                        planned_worklist=aliquot_buffer_worklist,
                        target_rack=plate,
                        reservoir_specs=quarter_rs,
                        source_rack_barcode=self.ALIQUOT_BUFFER_PLATE_BARCODE,
                        ignored_positions=self._ignored_positions,
                        pipetting_specs=PIPETTING_SPECS_NAMES.BIOMEK)
                    buffer_job.min_transfer_volume = 1
                    self._aliquot_buffer_job_indices.append(job_index)
                    job_index_modifier = self.__add_aliquot_job(buffer_job,
                                                        job_index_modifier)
                    job_index = last_index + job_index_modifier

                if self._first_rack_transfer_index is None:
                    self._first_rack_transfer_index = job_index
                transfer_job = RackTransferJob(index=job_index,
                    planned_rack_transfer=aliquot_worklist.planned_transfers[0],
                    target_rack=plate,
                    source_rack=self._preparation_plate)

            else:
                transfer_job = ContainerTransferJob(index=job_index,
                                planned_worklist=aliquot_worklist,
                                target_rack=plate,
                                source_rack=self._preparation_plate,
                                ignored_positions=self._ignored_positions,
                                pipetting_specs=PIPETTING_SPECS_NAMES.BIOMEK)

            job_index_modifier = self.__add_aliquot_job(transfer_job,
                                                        job_index_modifier)
            self._aliquot_transfer_job_indices.append(job_index)

    def __add_aliquot_job(self, job, job_index_modifier):
        """
        Adds a transfer job to the :attr:`_transfer_jobs` list and increments
        the job index modifier.
        """
        self._transfer_jobs.append(job)
        job_index_modifier += 1
        return job_index_modifier

    def _execute_task(self):
        """
        This is the actual task carried out by the specific subclass.
        """
        self.add_error('Abstract method: _execute_task()')


class IsoProcessingWorklistWriter(IsoProcessingSeriesTool):
    """
    This tool writes worklists for the ISO processing series.

    **Return Value:** The worklist files as zip stream.
    """

    NAME = 'ISO Processing Worklist Writer'

    #: The suffix for the file name of the second CSV worklist (which deals with
    #: addition of annealing buffer to the ISO preparation plate). The first
    #: part of the file name will be the ISO label.
    ANNEALING_FILE_SUFFIX = '%s_buffer.csv'
    #: The suffix for the file name of the CSV worklists dealing with the
    #: second step of ISO preparation processing (preparation of the dilution
    #: series). The first part of the file name will be the ISO label, the
    #: last part will be the step number (since there can be several worklists).
    DILUTION_SERIES_FILE_SUFFIX = '%s_dilution_series_%s.csv'
    #: The suffix for the file name of the last CSV worklist (which deals with
    #: the transfer of sample from the preparation plate to the ISO plate). The
    #: first part of the file name will be the ISO label.
    TRANSFER_FILE_SUFFIX = '%s_aliquot_transfer.csv'

    def __init__(self, iso, logging_level=logging.WARNING,
                 add_default_handlers=False):
        """
        Constructor:

        :param iso: The ISO to process.
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
        IsoProcessingSeriesTool.__init__(self, iso=iso,
                                logging_level=logging_level,
                                add_default_handlers=add_default_handlers)

        #: The zip stream containing the zip archive.
        self.__zip_stream = None

        #: The zip map for the stock transfer files (if applicable).
        self.__stock_zip_map = None

        #: The streams for the ISO processing series mapped onto job indices.
        self.__stream_map = None

        #: The merged aliquot buffer stream.
        self.__merged_aliquot_buffer_stream = None

    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        IsoProcessingSeriesTool.reset(self)
        self.__zip_stream = None
        self.__stock_zip_map = None
        self.__merged_aliquot_buffer_stream = None

    def _fetch_stock_transfer_jobs(self):
        """
        Executes the task for the stock transfer part.
        """
        IsoProcessingSeriesTool._fetch_stock_transfer_jobs(self)

        if not self.has_errors():
            writer = IsoSampleStockRackWorklistWriter(iso=self.iso,
                                                      log=self.log)
            writer.run()
            self.__stock_zip_map = writer.get_zip_map()

            if self.__stock_zip_map is None:
                msg = 'Error when trying to generate files for the sample ' \
                      'stock transfer.'
                self.add_error(msg)

    def _execute_task(self):
        """
        This is the actual task carried out by the specific subclass.
        """
        self.add_info('Start worklist file generation ...')

        self.__create_streams()
        if not self.has_errors():

            zip_map = dict()
            if not self.__stock_zip_map is None:
                zip_map = self.__stock_zip_map

            if self._experiment_type.id == EXPERIMENT_SCENARIOS.MANUAL:
                zip_map = self.__complete_zip_map_for_manual(zip_map)
            else:
                zip_map = self.__complete_full_zip_map(zip_map)

            self.__zip_stream = StringIO()
            create_zip_archive(zip_stream=self.__zip_stream, stream_map=zip_map)

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
        elif len(self._aliquot_buffer_job_indices) > 0:
            aliquot_buffer_streams = dict()
            for job_index in self._aliquot_buffer_job_indices:
                aliquot_buffer_streams[job_index] = self.__stream_map[job_index]
            self.__merged_aliquot_buffer_stream = merge_csv_streams(
                                            stream_map=aliquot_buffer_streams)

    def __complete_zip_map_for_manual(self, zip_map):
        """
        In manual cases there might only be a stock transfer worklist and
        (optionally) a buffer worklist.
        """
        stream_map_indices = self.__stream_map.keys()
        stream_map_indices.sort()
        for i in stream_map_indices:
            if i < self.MAX_NUMBER_TRANSFER_JOBS: continue
            buffer_fn = self.ANNEALING_FILE_SUFFIX % (self.iso.label)
            zip_map[buffer_fn] = self.__stream_map[i]

        return zip_map

    def __complete_full_zip_map(self, zip_map):
        """
        This contains the stock transfer file (if applicable) and the complete
        set of processing worklist series files.
        """
        self.add_debug('Create zip archive.')

        job_index_modifier = self.MAX_NUMBER_TRANSFER_JOBS

        stream_map_indices = self.__stream_map.keys()
        stream_map_indices.sort()
        for i in stream_map_indices:
            if i < job_index_modifier: continue
            stream = self.__stream_map[i]
            if i == job_index_modifier:
                buffer_fn = self.ANNEALING_FILE_SUFFIX % (self.iso.label)
                zip_map[buffer_fn] = stream
            elif i == self._first_rack_transfer_index:
                cybio_fn = self.CYBIO_FILE_SUFFIX % (self.iso.label)
                zip_map[cybio_fn] = stream
            elif i in self._aliquot_buffer_job_indices:
                ab_fn = self.ALIQUOT_BUFFER_FILE_SUFFIX % (self.iso.label)
                zip_map[ab_fn] = self.__merged_aliquot_buffer_stream
            elif i in self._aliquot_transfer_job_indices:
                transfer_fn = self.TRANSFER_FILE_SUFFIX % (self.iso.label)
                zip_map[transfer_fn] = stream
            else:
                dil_fn = self.DILUTION_SERIES_FILE_SUFFIX % (self.iso.label,
                                                    (i - job_index_modifier))
                zip_map[dil_fn] = stream

        return zip_map


class IsoProcessingExecutor(IsoProcessingSeriesTool,
                            StockTransferExecutor):
    """
    This tool executes worklists for the ISO processing series.

    **Return Value:** updated ISO
    """

    NAME = 'ISO Processing Worklist Writer'

    RECORD_WARNINGS = False

    #: For the :class:`StockTransferExecutor`.
    ENTITY_CLS = Iso

    def __init__(self, iso, user,
                 logging_level=logging.WARNING,
                 add_default_handlers=False):
        """
        Constructor:

        :param iso: The ISO to process.
        :type iso: :class:`thelma.models.iso.Iso`

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
        IsoProcessingSeriesTool.__init__(self, iso=iso,
                                logging_level=logging_level,
                                add_default_handlers=add_default_handlers)
        StockTransferExecutor.__init__(self, user=user, entity=iso,
                                       log=self.log)

    def reset(self):
        """
        Resets all values except for initialisation values.
        """
        IsoProcessingSeriesTool.reset(self)
        StockTransferExecutor.reset(self)

    def get_executed_stock_worklists(self):
        """
        Returns the executed worklists that *deal with the stock transfer*
        (for stock transfer reporting).
        We do not need to check whether there are stock transfer worklists
        because the reporting tools cancels the submission automatically
        if the length of the executed worklists list is below 1.
        """
        if self.return_value is None: return None

        stock_transfer_ews = dict()
        for job_index, ew in self._executed_worklists.iteritems():
            if job_index < self.MAX_NUMBER_TRANSFER_JOBS:
                stock_transfer_ews[job_index] = ew

        return stock_transfer_ews

    def get_working_layout(self):
        """
        Returns the working layout containing the molecule design pool ID data
        (for reporting).
        """
        if self.return_value is None: return None
        return self._preparation_layout

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        IsoProcessingSeriesTool._check_input(self)
        StockTransferExecutor.reset(self)

    def _execute_task(self):
        """
        This is the actual task carried out by the specific subclass
        (DB execution).
        """
        self.add_info('Start transfer execution ...')

        self._check_for_previous_execution()
        if not self.has_errors():
            executor = SeriesExecutor(transfer_jobs=self._transfer_jobs,
                                      user=self.user, log=self.log)
            self._executed_worklists = executor.get_result()
            if self._executed_worklists is None:
                msg = 'Error during serial transfer execution.'
                self.add_error(msg)
            else:
                self._update_iso_status()
                self.__create_executed_worklists_for_rack_transfers()
                self.return_value = self.iso
                self.add_info('Transfer execution completed.')

    def _check_for_previous_execution(self):
        """
        Makes sure the execution has not taken place before
        (Searching for executed worklist does not help here, since all ISOs
        share the same series. Thus, we check the status of the aliquot plates.)
        """
        self.add_debug('Check for previous execution ...')

        for plate in self._aliquot_plates:
            if plate.status.name == ITEM_STATUS_NAMES.MANAGED:
                msg = 'The ISO processing worklist series has already been ' \
                      'executed before!'
                self.add_error(msg)
                break

        if not self.has_errors():
            if self._including_stock_transfer:
                if self._is_384_screening:
                    expected_status = ISO_STATUS.PREPARED
                else:
                    expected_status = ISO_STATUS.QUEUED
            else:
                expected_status = ISO_STATUS.IN_PROGRESS
            if not self.iso.status == expected_status:
                msg = 'Unexpected ISO status: "%s". Expected status: "%s".' \
                      % (self.iso.status, expected_status)
                self.add_error(msg)

    def _update_iso_status(self):
        """
        Sets the status of all involved ISOs to 'done'.
        """
        self.iso.status = ISO_STATUS.DONE

    def __create_executed_worklists_for_rack_transfers(self):
        """
        Creates the executed worklists for the rack transfer jobs.
        """
        self.add_debug('Create executed rack transfer worklists ...')

        executed_items = self._executed_worklists
        worklists = dict()
        erts = dict()
        for item in executed_items.values():
            if not isinstance(item, ExecutedRackTransfer): continue
            planned_worklist = item.planned_transfer.planned_worklist
            if not worklists.has_key(planned_worklist.label):
                worklists[planned_worklist.label] = planned_worklist
                erts[planned_worklist.label] = []
            erts[planned_worklist.label].append(item)

        for worklist_label, planned_worklist in worklists.iteritems():
            executed_transfers = erts[worklist_label]
            ExecutedWorklist(planned_worklist=planned_worklist,
                             executed_transfers=executed_transfers)
