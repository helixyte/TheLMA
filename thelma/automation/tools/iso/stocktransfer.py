"""
Verifiers, writer and executors for stock transfers (transfer of liquid from
a stock tube into a plate).

AAB, Jan 2012
"""
from StringIO import StringIO
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.iso.prep_utils import IsoControlRackLayout
from thelma.automation.tools.iso.prep_utils import IsoControlRackLayoutConverter
from thelma.automation.tools.iso.prep_utils import PrepIsoLayout
from thelma.automation.tools.iso.prep_utils import PrepIsoLayoutConverter
from thelma.automation.tools.iso.stockworklist \
    import StockTransferWorklistGenerator
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.tools.utils.base import add_list_map_element
from thelma.automation.tools.utils.verifier import BaseRackVerifier
from thelma.automation.tools.worklists.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.worklists.series import ContainerTransferJob
from thelma.automation.tools.worklists.series import RackTransferJob
from thelma.automation.tools.worklists.series import SeriesExecutor
from thelma.automation.tools.worklists.series import SeriesWorklistWriter
from thelma.automation.tools.worklists.series import create_rack_sector_stream
from thelma.automation.tools.writers import TxtWriter
from thelma.automation.tools.writers import create_zip_archive
from thelma.automation.tools.writers import merge_csv_streams
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import Iso
from thelma.models.iso import IsoSampleStockRack
from thelma.models.job import IsoJob
from thelma.models.liquidtransfer import PlannedRackTransfer
from thelma.models.rack import Plate
from thelma.models.rack import TubeRack
from thelma.models.user import User
import logging


__docformat__ = 'reStructuredText en'

__all__ = ['StockTransferExecutor',
           'IsoControlStockRackTool',
           'IsoControlStockRackVerifier',
           'IsoControlStockRackExecutor',
           'IsoControlStockRackWorklistWriter',
           'IsoSampleStockRackTool',
           'IsoSampleStockRackVerifier',
           'IsoSampleStockRackJobCreator',
           'IsoSampleStockRackExecutor',
           'IsoSampleStockRackWorklistWriter',
           ]




class StockTransferExecutor(BaseAutomationTool): #pylint: disable=W0223
    """
    This is sort of an interface for tool conducting stock transfers.
    This class is sort of an add-on. It is not supposed to be used as single
    super class.
    """

    #: The entity treated by the subclass (ISO or ISO job).
    ENTITY_CLS = None

    def __init__(self, user, entity, log): #pylint: disable=W0231
        """
        Constructor:

        :param user: The user conducting the update.
        :type user: :class:`thelma.models.user.User`
        """
        #: The user conducting the execution.
        self.user = user
        #: The entity the transfer will be attached to (ISO or ISO job).
        self.entity = entity
        #: The log to write into.
        self.log = log

        #: The executed worklists that have been generated (for reporting).
        self._executed_worklists = None

    def reset(self):
        """
        Resets the executed worklists.
        """
        self._executed_worklists = None

    def _check_input(self):
        """
        Checks the user.
        """
        self._check_input_class('user', self.user, User)
        self._check_input_class('entity', self.entity, self.ENTITY_CLS)

    def get_executed_stock_worklists(self):
        """
        Returns the executed worklists that have been generated (for reporting).
        """
        if self.return_value is None: return None
        return self._executed_worklists

    def get_working_layout(self):
        """
        Returns the working layout containing the molecule design ID data
        (for reporting).
        """
        raise NotImplementedError('Abstract method')

    def _execute_worklists(self, transfer_jobs):
        """
        Executes the create transfer jobs (as series).
        """
        self.add_debug('Prepare worklist execution ...')

        self._check_for_previous_execution()
        if not self.has_errors():
            series_executor = SeriesExecutor(transfer_jobs=transfer_jobs,
                                             user=self.user, log=self.log)
            self._executed_worklists = series_executor.get_result()
            if self._executed_worklists is None:
                msg = 'Error during serial worklist execution!'
                self.add_error(msg)

        if not self.has_errors():
            self._update_iso_status()
            self.return_value = self.entity
            self.add_info('Worklist execution completed.')

    def _check_for_previous_execution(self):
        """
        Makes sure the worklists have not been executed before.
        """
        self.add_error('Abstract method: _check_for_previous_execution()')

    def _update_iso_status(self):
        """
        Sets the status of the ISO.
        """
        self.add_error('Abstract method: _update_iso_status()')


class IsoControlStockRackTool(BaseAutomationTool):
    """
    A base class for tools dealing with ISO control stock racks (executor
    and worklist generator). The tool covers the verification of the stored
    stock tube. The subclass launch different series tools.

    **Return Value:** depending on the subclass
    """

    def __init__(self, iso_job, logging_level=logging.WARNING,
                 add_default_handlers=False):
        """
        Constructor:

        :param iso_job: The ISO job containing the ISO control rack.
        :type iso_job: :class:`thelma.models.job.IsoJob`

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

        #: The ISO job containing the ISO control rack.
        self.iso_job = iso_job

        #: The control rack layout for the job.
        self._control_layout = None
        #: The stock rack that has been prepared for this job.
        self._stock_rack = None
        #: The preparation plates mapped onto the labels of the ISOs they
        #: belong to.
        self._preparation_plates = None
        #: The planned worklist for the transfers.
        self._planned_worklist = None
        #: The transfer jobs for the series tool.
        self._transfer_jobs = None

    def reset(self):
        """
        Resets all values except for initialisation values.
        """
        BaseAutomationTool.reset(self)
        self._control_layout = None
        self._stock_rack = None
        self._planned_worklist = None
        self._preparation_plates = dict()
        self._transfer_jobs = []

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start ISO control rack tool ...')

        self._check_input()
        if not self.has_errors(): self.__fetch_racks_and_worklist()
        if not self.has_errors(): self.__convert_control_layout()
        if not self.has_errors(): self.__verify_stock_rack()
        if not self.has_errors(): self.__create_transfer_jobs()
        if not self.has_errors(): self._execute_task()

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')
        if self._check_input_class('ISO job', self.iso_job, IsoJob):
            if len(self.iso_job) < 1:
                msg = 'There are no ISOs in this ISO job!'
                self.add_error(msg)

    def __fetch_racks_and_worklist(self):
        """
        Fetches the control stock rack and the preparation plates for this job
        and the planned worklist for the transfer.
        """
        self.add_debug('Fetch rack ...')

        icsr = self.iso_job.iso_control_stock_rack
        if icsr is None:
            msg = 'Could not find ISO control stock rack for this ISO job.'
            self.add_error(msg)
        elif icsr.rack is None:
            msg = 'Could not find tube rack for this ISO control stock rack!'
            self.add_error(msg)
        elif icsr.planned_worklist is None:
            msg = 'Could not find planned worklist for this ISO control rack!'
            self.add_error(msg)
        else:
            self._stock_rack = icsr.rack
            self._planned_worklist = icsr.planned_worklist

        no_prep_plate = []
        for iso in self.iso_job.isos:
            prep_plate = iso.preparation_plate
            if prep_plate is None:
                no_prep_plate.append(iso.label)
                continue
            self._preparation_plates[iso.label] = prep_plate

        if len(no_prep_plate) > 0:
            msg = 'The following ISO do not have preparation plates: %s!' \
                  % (no_prep_plate)
            self.add_error(msg)

    def __convert_control_layout(self):
        """
        Converts the rack layout for the control rack into a working layout.
        """

        rack_layout = self.iso_job.iso_control_stock_rack.rack_layout
        if rack_layout is None:
            msg = 'Could not find rack layout for the ISO control stock rack!'
            self.add_error(msg)
        else:
            converter = IsoControlRackLayoutConverter(log=self.log,
                                        rack_layout=rack_layout)
            self._control_layout = converter.get_result()
            if self._control_layout is None:
                msg = 'Error when trying to convert control rack layout!'
                self.add_error(msg)

    def __verify_stock_rack(self):
        """
        Verifies the :attr:`_stock_rack` in its current state.
        """
        self.add_debug('Verify stock rack ...')

        verifier = IsoControlStockRackVerifier(stock_rack=self._stock_rack,
                         control_layout=self._control_layout, log=self.log)
        compatible = verifier.get_result()
        if compatible is None:
            msg = 'Error in the verifier!'
            self.add_error(msg)
        elif not compatible:
            msg = 'The stock rack is not compatible with the ISO job!'
            self.add_error(msg)

    def __create_transfer_jobs(self):
        """
        Creates the transfer jobs for the series executor (one for each
        ISO preparation plate.)
        """
        self.add_debug('Create transfer jobs ...')

        iso_labels = self._preparation_plates.keys()
        iso_labels.sort()

        counter = 0
        for iso_label in iso_labels:
            preparation_plate = self._preparation_plates[iso_label]
            transfer_job = ContainerTransferJob(index=counter,
                                planned_worklist=self._planned_worklist,
                                target_rack=preparation_plate,
                                source_rack=self._stock_rack,
                                is_biomek_transfer=True)
            transfer_job.min_transfer_volume = 1
            self._transfer_jobs.append(transfer_job)
            counter += 1

    def _execute_task(self):
        """
        This is the actual task carried out by the specific subclass.
        """
        self.add_error('Abstract method: _execute_task()')


class IsoControlStockRackVerifier(BaseRackVerifier):
    """
    This tools verifies whether a stock rack (after rearrangment of stock tubes)
    is compliant to the control layout of the passed ISO job.

    **Return Value:** boolean
    """

    NAME = 'ISO Control Stock Rack Verifier'

    RACK_CLS = TubeRack
    LAYOUT_CLS = IsoControlRackLayout

    def __init__(self, stock_rack, control_layout, log):
        """
        Constructor:

        :param stock_rack: The rack to be checked.
        :type stock_rack: :class:`thelma.models.rack.TubeRack`

        :param iso_job: The ISO job containing the control rack layout.
        :type iso_job: :class:`thelma.models.job.IsoJob`

        :param log: The log the write in.
        :type log: :class:`thelma.ThelmaLog`
        """
        BaseRackVerifier.__init__(self, rack=stock_rack,
                                  reference_layout=control_layout,
                                  record_success=False,
                                  log=log)

        #: Maps stock samples pools onto pool IDs.
        self.__pool_map = None

    def _check_input(self):
        BaseRackVerifier._check_input(self)
        self.__pool_map = None

    def _fetch_expected_layout(self):
        """
        Fetches the expected layout (the control rack layout of the ISO job).
        """
        self.add_error('Not implemented: _fetch_expected_layout()')

    def _get_exp_pos_molecule_design_ids(self, exp_pos):
        """
        Gets the molecule design ID expected for a working layout
        position.
        """
        if self.__pool_map is None:
            self.__pool_map = self.reference_layout.get_pools()

        if exp_pos is None:
            return None
        else:
            pool_id = exp_pos.molecule_design_pool_id
            md_pool = self.__pool_map[pool_id]
            return self._get_ids_for_pool(md_pool)


class IsoControlStockRackExecutor(IsoControlStockRackTool,
                                  StockTransferExecutor):
    """
    This tool executes a container transfer worklist for the
    transfer of stock solution from an control stock rack to the
    preparation plates of the ISOs belonging to the according ISO job.

    **Return Value:** the updated ISO job
    """

    NAME = 'ISO Control Transfer Executor'

    ENTITY_CLS = IsoJob

    def __init__(self, iso_job, user, logging_level=logging.WARNING,
                 add_default_handlers=False):
        """
        Constructor:

        :param iso_job: The ISO job containing the ISO control rack.
        :type iso_job: :class:`thelma.models.job.IsoJob`

        :param user: The user conducting the update.
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
        IsoControlStockRackTool.__init__(self, iso_job=iso_job,
                            logging_level=logging_level,
                            add_default_handlers=add_default_handlers)
        StockTransferExecutor.__init__(self, user=user,
                                       entity=iso_job, log=self.log)

    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        IsoControlStockRackTool.reset(self)
        StockTransferExecutor.reset(self)

    def get_working_layout(self):
        """
        Returns the working layout (control layout) containing the molecule
        design ID data (for reporting).
        """
        if self.return_value is None: return None
        return self._control_layout

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        IsoControlStockRackTool._check_input(self)
        StockTransferExecutor._check_input(self)

    def _execute_task(self):
        """
        Executes the create transfer jobs (as series).
        """
        self._execute_worklists(transfer_jobs=self._transfer_jobs)

    def _check_for_previous_execution(self):
        """
        Makes sure the worklists have not been executed before.
        """
        self.add_debug('Check for previous execution ...')

        if len(self._planned_worklist.executed_worklists) > 0:
            msg = 'The stock transfer has already been executed!'
            self.add_error(msg)
        else:
            for iso in self.iso_job.isos:
                if not iso.status == ISO_STATUS.QUEUED:
                    msg = 'Unexpected status "%s" for ISO "%s". Expected: ' \
                          '"%s".' % (iso.status, iso.label, ISO_STATUS.QUEUED)
                    self.add_error(msg)
                    break

    def _update_iso_status(self):
        """
        Sets the status of all involved ISOs to 'prepared'.
        """
        self.add_debug('Update ISO status ...')

        for iso in self.iso_job.isos:
            iso.status = ISO_STATUS.PREPARED


class IsoControlStockRackWorklistWriter(IsoControlStockRackTool):
    """
    This tool executes a container transfer worklist for the
    transfer of stock solution from an control stock rack to the
    preparation plates of the ISOs belonging to the according ISO job.

    **Return Value:** Biomek worklist as zip stream (CSV).
    """

    NAME = 'ISO Control Transfer Writer'

    #: The file name for the BioMek worklist file. The first part of the file
    #: name will be the ISO job label.
    BIOMEK_FILE_NAME = '%s_control_stock_transfer.csv'
    #: The file name for the overview file. The first part of the file
    #: name will be the ISO job label.
    INFO_FILE_NAME = '%s_control_stock_transfer_overview.txt'

    #: The minimum volume to be taken out of the stock (a special Biomek case).
    MIN_BIOMEK_STOCK_TRANSFER_VOLUME = 1

    def __init__(self, iso_job, logging_level=logging.WARNING,
                 add_default_handlers=False):
        """
        Constructor:

        :param iso_job: The ISO job containing the ISO control rack.
        :type iso_job: :class:`thelma.models.job.IsoJob`

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """
        IsoControlStockRackTool.__init__(self, iso_job=iso_job,
                                 logging_level=logging_level,
                                 add_default_handlers=add_default_handlers)

        #: The stream map created by the series tool.
        self.__stream_map = None
        #: The different stream merged into one file.
        self.__merged_stream = None
        #: The zip stream wrapped aournd the merged stream.
        self.__zip_stream = None

        #: The overview file.
        self.__overview_stream = None

    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        IsoControlStockRackTool.reset(self)
        self.__stream_map = None
        self.__merged_stream = None
        self.__zip_stream = None
        self.__overview_stream = None

    def _execute_task(self):
        """
        Create the transfer jobs for the transfer and executes them.
        """
        self.add_debug('Prepare worklist execution ...')

        self.__create_overview_stream()

        if not self.has_errors():
            series_writer = SeriesWorklistWriter(log=self.log,
                                            transfer_jobs=self._transfer_jobs)
            self.__stream_map = series_writer.get_result()
            if self.__stream_map is None:
                msg = 'Error during serial worklist file generation!'
                self.add_error(msg)
            else:
                self.__merged_stream = merge_csv_streams(self.__stream_map)

        if not self.has_errors():
            self.__create_zip_archive()
            self.return_value = self.__zip_stream
            self.add_info('Worklist file creation completed.')

    def __create_overview_stream(self):
        """
        Creates the stream for the overview file.
        """
        self.add_debug('Create overview stream ...')

        prep_plate_barcodes = []
        for prep_plate in self._preparation_plates.values():
            prep_plate_barcodes.append(prep_plate.barcode)
        prep_plate_barcodes.sort()

        writer = IsoControlTransferOverviewWriter(stock_rack=self._stock_rack,
                        preparation_plates_barcodes=prep_plate_barcodes,
                        control_layout=self._control_layout, log=self.log)
        self.__overview_stream = writer.get_result()

        if self.__overview_stream is None:
            msg = 'Error when trying to generate overview file.'
            self.add_error(msg)

    def __create_zip_archive(self):
        """
        Creates the zip file for the output.
        """
        self.add_debug('Create zip file ...')

        self.__zip_stream = StringIO()

        zip_fn = self.BIOMEK_FILE_NAME % (self.iso_job.label)
        zip_map = {zip_fn : self.__merged_stream}

        info_fn = self.INFO_FILE_NAME % (self.iso_job.label)
        zip_map[info_fn] = self.__overview_stream

        create_zip_archive(zip_stream=self.__zip_stream, stream_map=zip_map)


class IsoControlTransferOverviewWriter(TxtWriter):
    """
    Creates the overview file for the control stock transfer.

    **Return Value:** file stream (TXT format)
    """
    NAME = 'ISO Control Overview File Writer'

    def __init__(self, stock_rack, preparation_plates_barcodes, control_layout,
                 log):
        """
        Constructor:

        :param stock_rack: The stock rack containing the stock tubes (verified).
        :type stock_rack: :class:`thelma.models.rack.TubeRack`

        :param preparation_plates_barcodes: The barcodes of the preparation
            plates of the ISOs belonging to the ISO job.
        :type preparation_plates_barcodes: :class:`list` of
            :class:`thelma.models.rack.Plate` objects

        :param control_layout: The control layout of the stock rack.
        :type control_layout: :class:`IsoControlRackLayout`

        :param log: The log the write in.
        :type log: :class:`thelma.ThelmaLog`
        """
        TxtWriter.__init__(self, log=log)

        #: The stock rack containing the stock tubes (verified).
        self.stock_rack = stock_rack
        #: The preparation plates barcodes of the ISOs belonging to the ISO job.
        self.prep_plate_barcodes = preparation_plates_barcodes
        #: The control layout of the stock rack.
        self.control_layout = control_layout

    def _check_input(self):
        """
        Checks if the tools has obtained correct input values.
        """
        self.add_debug('Check input ...')

        self._check_input_class('stock rack', self.stock_rack, TubeRack)
        self._check_input_class('control layout', self.control_layout,
                                IsoControlRackLayout)

        if self._check_input_class('preparation plates list',
                                   self.prep_plate_barcodes, list):
            for prep_plate in self.prep_plate_barcodes:
                if not self._check_input_class('barcode', prep_plate,
                                               basestring): break

    def _write_stream_content(self):
        """
        Writes into the streams.
        """

        self._write_headline(header_text='Transfers', preceding_blank_lines=0,
                             trailing_blank_lines=2)
        self.__write_transfer_part()

        self._write_headline(header_text='Stock Rack')
        self._write_body_lines(['%s' % (self.stock_rack.barcode)])

        self._write_headline(header_text='Preparation Plates')
        self._write_body_lines(self.prep_plate_barcodes)

    def __write_transfer_part(self):
        """
        Writes the transfer part of the file.
        """
        tube_barcode_map = dict()
        for tube in self.stock_rack.containers:
            pos_label = tube.location.position.label
            tube_barcode_map[pos_label] = tube.barcode

        transfer_part = []
        table_head = 'Source Position\tVolume\tTarget Position\tTube Barcode'
        transfer_part.append(table_head)

        for control_pos in self.control_layout.get_sorted_working_positions():
            src_label = control_pos.rack_position.label
            tube_barcode = tube_barcode_map[src_label]
            for tt in control_pos.transfer_targets:
                lin = '%s\t%.1f\t%s\t%s' % (src_label, tt.transfer_volume,
                                            tt.position_label, tube_barcode)
                transfer_part.append(lin)

        self._write_body_lines(transfer_part)


class IsoSampleStockRackTool(BaseAutomationTool):
    """
    A base class for tools dealing with ISO control stock racks (executor
    and worklist generator). The tool covers the verification of the stored
    stock tube. The subclasses launch different series tools.

    **Return Value:** depending on the subclass
    """

    def __init__(self, iso, log=None, logging_level=logging.WARNING,
                 add_default_handlers=False):
        """
        Constructor:

        :param iso: The ISO whose samples to transfer.
        :type iso: :class:`thelma.models.iso.Iso`

        :param log: The ThelmaLog you want to write into. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """
        if log is None:
            depending = False
        else:
            depending = True

        BaseAutomationTool.__init__(self, logging_level=logging_level,
                                    add_default_handlers=add_default_handlers,
                                    depending=depending, log=log)

        #: The ISO whose samples to transfer.
        self.iso = iso

        #: The preparation layout of the ISO.
        self._preparation_layout = None
        #: The preparation plate of the ISO.
        self._preparation_plate = None
        #: The ISO sample stock racks mapped onto rack sectors.
        self._sample_stock_racks = None

        #: The transfer jobs for the series tool.
        self._transfer_jobs = None

    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        BaseAutomationTool.reset(self)
        self._preparation_layout = None
        self._preparation_plate = None
        self._sample_stock_racks = dict()
        self._transfer_jobs = []

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start ISO sample stock rack tool ...')

        self._check_input()
        if not self.has_errors(): self.__get_preparation_layout()
        if not self.has_errors(): self.__fetch_stock_racks_and_prep_plate()
        if not self.has_errors(): self.__verify_stock_racks()
        if not self.has_errors(): self.__create_transfer_jobs()
        if not self.has_errors(): self._execute_task()

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')
        self._check_input_class('ISO', self.iso, Iso)

    def __get_preparation_layout(self):
        """
        Converts the rack layout of the ISO into a preparation layout.
        """
        self.add_debug('Get preparation layout ...')

        converter = PrepIsoLayoutConverter(rack_layout=self.iso.rack_layout,
                                           log=self.log)
        self._preparation_layout = converter.get_result()

        if self._preparation_layout is None:
            msg = 'Error when trying to convert preparation layout.'
            self.add_error(msg)

    def __fetch_stock_racks_and_prep_plate(self):
        """
        Fetches the ISO sample stock racks for the
        """
        self.add_debug('Fetch ISO sample stock racks ...')

        for issr in self.iso.iso_sample_stock_racks:
            sector_index = issr.sector_index
            self._sample_stock_racks[sector_index] = issr

        if len(self._sample_stock_racks) < 1:
            msg = 'There are no ISO sample stock racks for this ISO!'
            self.add_error(msg)

        self._preparation_plate = self.iso.preparation_plate
        if self._preparation_plate is None:
            msg = 'There is no preparation plate for this ISO!'
            self.add_error(msg)

    def __verify_stock_racks(self):
        """
        Verifies the sample stock racks in its current state.
        """
        self.add_debug('Verify stock racks ...')

        verifier = IsoSampleStockRackVerifier(log=self.log,
                        preparation_layout=self._preparation_layout,
                        sample_stock_racks=self._sample_stock_racks)

        compatible = verifier.get_result()
        if compatible is None:
            msg = 'Error in the verifier!'
            self.add_error(msg)
        elif not compatible:
            msg = 'The stock racks are not compatible with the ISO!'
            self.add_error(msg)

    def __create_transfer_jobs(self):
        """
        Creates the transfer jobs for the series executor (one for each
        sample stock rack.)
        """
        self.add_debug('Create transfer jobs ...')

        job_creator = IsoSampleStockRackJobCreator(log=self.log,
                            sample_stock_racks=self._sample_stock_racks,
                            preparation_plate=self._preparation_plate)
        self._transfer_jobs = job_creator.get_result()

        if self._transfer_jobs is None:
            msg = 'Error when trying to create transfer jobs.'
            self.add_error(msg)

    def _execute_task(self):
        """
        This is the actual task carried out by the specific subclass.
        """
        self.add_error('Abstract method: _execute_task()')


class IsoSampleStockRackVerifier(BaseAutomationTool):
    """
    Verifies the validity of the sample stock rack for an 384-well ISO. The
    association of is made base on the tranfer worklists.

    **Return Value: ** boolean
    """

    NAME = 'ISO Sample Stock Rack Verifier'

    def __init__(self, preparation_layout, sample_stock_racks, log):
        """
        Constructor:

        :param preparation_layout: The preparation layout of the ISO.
        :type preparation_layout: :class:`PrepIsoLayout`

        :param sample_stock_racks: The ISO sample stock racks for this
            ISO sorted by rack sector.
        :type sample_stock_racks: :class:`dict` with :class:`int` as key and
            :class:`thelma.models.iso.IsoSampleStockRack` as value

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        BaseAutomationTool.__init__(self, log=log)

        #: The preparation layout of the ISO.
        self.preparation_layout = preparation_layout
        #: Maps sample stock racks onto sectors.
        self.sample_stock_racks = sample_stock_racks

        #: Records the preparation positions that have been checked.
        self.__checked_prep_positions = None

    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        BaseAutomationTool.reset(self)
        self.__checked_prep_positions = set()

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start ISO sample stock rack verification ...')

        self.__check_input()

        if not self.has_errors():

            self.return_value = True
            for sector_index, issr in self.sample_stock_racks.iteritems():
                is_valid = self.__is_valid_sample_stock_rack(sector_index,
                                                             issr)
                if is_valid is None:
                    self.return_value = None
                    break
                elif not is_valid:
                    self.return_value = False

        if not self.has_errors():
            self.return_value = self.__check_completeness()
            self.add_info('Verification completed.')

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')

        self._check_input_class('preparation layout', self.preparation_layout,
                                PrepIsoLayout)

        if self._check_input_class('sample stock rack map',
                                   self.sample_stock_racks, dict):
            for sector_index, issr in self.sample_stock_racks.iteritems():
                if not self._check_input_class('sector index', sector_index,
                                               int): break
                if not self._check_input_class('sample stock rack', issr,
                                               IsoSampleStockRack): break

    def __is_valid_sample_stock_rack(self, sector_index, issr):
        """
        Compares the given sample stock rack with the preparation layout
        (using the transfer worklist).
        """
        stock_rack = issr.rack
        if stock_rack is None:
            msg = 'The stock rack for sector %i is missing!' \
                  % (sector_index + 1)
            self.add_error(msg)
            return None

        md_map = self.__get_tube_rack_map(stock_rack)
        if md_map is None: return None
        pool_map = self.preparation_layout.get_pools()

        additional_mds = set()
        missing_mds = []
        mismatching_mds = []

        for pct in issr.planned_worklist.planned_transfers:
            source_pos = pct.source_position
            target_pos = pct.target_position
            self.__checked_prep_positions.add(target_pos)

            prep_pos = self.preparation_layout.get_working_position(target_pos)
            if prep_pos is None:
                pool_id = None
            elif prep_pos.is_mock or prep_pos.is_inactivated:
                pool_id = None
            else:
                pool_id = prep_pos.molecule_design_pool_id

            if pool_id is None:
                if not md_map.has_key(source_pos): continue
                ids = []
                for md in md_map[source_pos]: ids.append(str(md.id))
                info = '%s (md: %s)' % (source_pos.label, '-'.join(sorted(ids)))
                additional_mds.add(info)
            else:
                if not md_map.has_key(source_pos):
                    info = '%s (expected pool: %s)' % (source_pos.label,
                                                       pool_id)
                    missing_mds.append(info)
                    continue
                rack_mds = md_map[source_pos]
                md_pool = pool_map[pool_id]
                if not self.__check_pool_equality(md_pool, rack_mds):
                    exp_ids = []
                    for md in md_pool.molecule_designs: exp_ids.append(md.id)
                    exp_mds = '-'.join(sorted(
                                            [str(md_id) for md_id in exp_ids]))
                    found_mds = '-'.join(sorted(
                                            [str(md_id) for md_id in rack_mds]))
                    info = '%s (expected: %s, found: %s)' % (source_pos.label,
                                                             exp_mds, found_mds)
                    mismatching_mds.append(info)
                del md_map[source_pos]

        for source_pos, md_ids in md_map.iteritems():
            info = '%s (md: %s)' % (source_pos.label, '-'.join(sorted(
                                            [str(md_id) for md_id in md_ids])))
            additional_mds.add(info)

        is_valid = True

        if len(additional_mds) > 0:
            msg = 'There are molecule designs for positions that should be ' \
                  'empty in the stock tube rack %s (sector %i): %s.' \
                  % (stock_rack.barcode, (sector_index + 1),
                     ' - '.join(additional_mds))
            self.add_error(msg)
            is_valid = False

        if len(missing_mds) > 0:
            msg = 'Some molecule designs expected for stock tube rack %s ' \
                  '(sector %i) are missing: %s.' % (stock_rack.barcode,
                            (sector_index + 1), ' - '.join(missing_mds))
            self.add_error(msg)
            is_valid = False

        if len(mismatching_mds) > 0:
            msg = 'Some molecule designs in stock tube rack %s (sector %i) ' \
                  'do not match the expected molecule design: %s.' \
                  % (stock_rack.barcode, (sector_index + 1), mismatching_mds)
            self.add_error(msg)
            is_valid = False

        return is_valid

    def __get_tube_rack_map(self, stock_rack):
        """
        Maps the molecule designs of the given stock tube rack onto rack
        positions.
        """

        if not stock_rack.rack_shape.name == RACK_SHAPE_NAMES.SHAPE_96:
            msg = 'Unsupported rack shape "%s" for stock tube rack.' \
                   % (stock_rack.rack_shape.name)
            self.add_error(msg)
            return None

        md_map = dict()
        for container in stock_rack.containers:
            rack_pos = container.location.position
            sample = container.sample
            if sample is None: continue
            sample_molecules = sample.sample_molecules
            if len(sample_molecules) < 1: continue
            for sm in sample_molecules:
                add_list_map_element(md_map, rack_pos,
                                     sm.molecule.molecule_design)

        return md_map

    def __check_pool_equality(self, md_pool, rack_mds):
        """
        Compares the molecule designs found for a rack position to the
        molecule designs of a pool.
        """
        if len(md_pool.molecule_designs) != len(rack_mds): return False

        for md in md_pool.molecule_designs:
            if not md in rack_mds: return False

        return True

    def __check_completeness(self):
        """
        Makes sure that all starting preparation positions have been checked.
        """

        # Filter mocks and controls
        pool_map = dict()
        for rack_pos, prep_pos in self.preparation_layout.iterpositions():
            if not prep_pos.parent_well is None: continue
            if prep_pos.is_mock or prep_pos.is_inactivated: continue
            if not rack_pos in self.__checked_prep_positions:
                pool_id = prep_pos.molecule_design_pool_id
                if not pool_map.has_key(pool_id):
                    pool_map[pool_id] = rack_pos.label
                else:
                    pool_map[pool_id] = None

        missing_prep_positions = []
        for pos_label in pool_map.values():
            if pos_label is None: continue
            missing_prep_positions.append(pos_label)

        if len(missing_prep_positions) > 0:
            missing_prep_positions.sort()
            msg = 'The following preparation positions are not covered by ' \
                  'a stock rack: %s.' \
                  % (','.join(sorted(missing_prep_positions)))
            self.add_error(msg)
            return False

        return True


class IsoSampleStockRackJobCreator(BaseAutomationTool):
    """
    Creates the transfer jobs for the transfer of samples from the stock
    racks to the preparation plates.

    **Return Value:** List of transfer jobs
    """

    NAME = 'ISO Sample Stock Transfer Jobs Creator'

    def __init__(self, sample_stock_racks, preparation_plate, log):
        """
        Constructor:

        :param sample_stock_racks: The ISO sample stock racks for this
            ISO sorted by rack sector.
        :type sample_stock_racks: :class:`dict` with :class:`int` as key and
            :class:`thelma.models.iso.IsoSampleStockRack` as value

        :param preparation_plate: The preparation plate of the ISO.
        :type preparation_plate: :class:`thelma.model.rack.Plate

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        BaseAutomationTool.__init__(self, log=log)

        #: Maps sample stock racks onto sectors.
        self.sample_stock_racks = sample_stock_racks
        #: The preparation plate of the ISO.
        self.preparation_plate = preparation_plate

        #: The transfer jobs for the series tool.
        self._transfer_jobs = None

    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        BaseAutomationTool.reset(self)
        self._transfer_jobs = []

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start transfer job creation ...')

        self.__check_input()
        if not self.has_errors(): self.__check_job()
        if not self.has_errors():
            self.__create_transfer_jobs()
            self.return_value = self._transfer_jobs
            self.add_info('Transfer job creation completed.')

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')

        self._check_input_class('preparation plate', self.preparation_plate,
                                Plate)
        if self._check_input_class('sample stock rack map',
                                   self.sample_stock_racks, dict):
            for sector_index, issr in self.sample_stock_racks.iteritems():
                if not self._check_input_class('sector index', sector_index,
                                               int): break
                if not self._check_input_class('sample stock rack', issr,
                                               IsoSampleStockRack): break
            if len(self.sample_stock_racks) < 1:
                msg = 'There are no sample stock racks for this ISO!'
                self.add_error(msg)

    def __check_job(self):
        """
        Checks whether the stock transfer for the controls (if applicable) has
        already been executed.
        """
        self.add_debug('Check ISO job ...')

        issr = self.sample_stock_racks.values()[0]
        iso_job = issr.iso.iso_job
        icsr = iso_job.iso_control_stock_rack

        missing_execution = True
        if icsr is None:
            if issr.iso.rack_layout.shape.name == RACK_SHAPE_NAMES.SHAPE_96:
                missing_execution = False
            elif len(self.sample_stock_racks) == 1 and \
                        not issr.iso.iso_request.experiment_metadata_type.id \
                        == EXPERIMENT_SCENARIOS.SCREENING:
                missing_execution = False
        else:
            prep_plate_status = self.preparation_plate.status.name
            if prep_plate_status == ITEM_STATUS_NAMES.MANAGED:
                missing_execution = False
            worklist = icsr.planned_worklist
            if len(worklist.executed_worklists) > 0:
                missing_execution = False

        if missing_execution:
            msg = 'The sample stock transfers for this ISO cannot be ' \
                  'processed yet because the control have not been ' \
                  'transferred to the preparation plate so far.'
            self.add_error(msg)

    def __create_transfer_jobs(self):
        """
        Creates the transfer jobs.
        """
        self.add_debug('Create transfer jobs ...')

        sectors = self.sample_stock_racks.keys()
        sectors.sort()

        for sector_index in sectors:
            stock_rack = self.sample_stock_racks[sector_index].rack
            worklist = self.sample_stock_racks[sector_index].planned_worklist
            transfer_job = ContainerTransferJob(index=sector_index,
                                planned_worklist=worklist,
                                target_rack=self.preparation_plate,
                                source_rack=stock_rack,
                                is_biomek_transfer=True)
            transfer_job.min_transfer_volume = 1
            self._transfer_jobs.append(transfer_job)


class IsoSampleStockRackExecutor(IsoSampleStockRackTool,
                                 StockTransferExecutor):
    """
    This tool executes a container transfer worklist for the
    transfer of stock solution from the sample stock rack of an ISO
    to the preparation plate.

    **Return Value:** the updated ISO
    """

    NAME = 'ISO Sample Transfer Executor'

    ENTITY_CLS = Iso

    def __init__(self, iso, user, logging_level=logging.WARNING,
                 add_default_handlers=False):
        """
        Constructor:

        :param iso: The ISO whose samples to transfer.
        :type iso: :class:`thelma.models.job.Iso`

        :param user: The user conducting the update.
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
        IsoSampleStockRackTool.__init__(self, iso=iso, log=None,
                            logging_level=logging_level,
                            add_default_handlers=add_default_handlers)
        StockTransferExecutor.__init__(self, user=user,
                                       entity=iso, log=self.log)

    def reset(self):
        """
        Resets all values except for initialisation values.
        """
        IsoSampleStockRackTool.reset(self)
        StockTransferExecutor.reset(self)

    def get_working_layout(self):
        """
        Returns the working layout (preparation layout) containing the molecule
        design ID data (for reporting).
        """
        if self.return_value is None: return None
        return self._preparation_layout

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        IsoSampleStockRackTool._check_input(self)
        StockTransferExecutor._check_input(self)

    def _execute_task(self):
        """
        Executes the create transfer jobs (as series).
        """
        self._execute_worklists(transfer_jobs=self._transfer_jobs)

    def _check_for_previous_execution(self):
        """
        Makes sure the worklists have not been executed before.
        """
        self.add_debug('Check for previous execution ...')

        for issr in self._sample_stock_racks.values():
            if len(issr.planned_worklist.executed_worklists) > 0:
                msg = 'The stock transfer has already been executed!'
                self.add_error(msg)
                break

        if not self.has_errors():
            expected_status = (ISO_STATUS.QUEUED, ISO_STATUS.PREPARED)
            if not self.iso.status in expected_status:
                msg = 'Unexpected ISO status: "%s".' % (self.iso.status)
                self.add_error(msg)

    def _update_iso_status(self):
        """
        Sets the status of all involved ISOs to 'in_progress'.
        """
        em_type_id = self.iso.iso_request.experiment_metadata_type.id

        if em_type_id == EXPERIMENT_SCENARIOS.ORDER_ONLY:
            iso_status = ISO_STATUS.DONE
        elif em_type_id == EXPERIMENT_SCENARIOS.MANUAL \
                and self.iso.iso_request.worklist_series is None:
            iso_status = ISO_STATUS.DONE
        else:
            iso_status = ISO_STATUS.IN_PROGRESS

        self.iso.status = iso_status


class IsoSampleStockRackWorklistWriter(IsoSampleStockRackTool):
    """
    This tool executes a container transfer worklist for the
    transfer of stock solution from sample stock rack of an ISO to the
    preparation plate of the ISO.

    **Return Value:** Biomek worklist as zip stream (CSV).
    """

    NAME = 'ISO Sample Transfer Writer'

    #: The file name for the BioMek worklist file. The first part of the file
    #: name will be the ISO label
    BIOMEK_FILE_NAME = '%s_sample_stock_transfer_biomek.csv'
    #: The file name for the CyBio info file. The first part of the file
    #: name will be the ISO label.
    CYBIO_FILE_NAME = '%s_sample_stock_transfer_cybio.txt'

    #: The minimum volume to be taken out of the stock (a special Biomek case).
    MIN_BIOMEK_STOCK_TRANSFER_VOLUME = 1

    def __init__(self, iso, log=None,
                 logging_level=logging.WARNING,
                 add_default_handlers=False):
        """
        Constructor:

        :param iso: The ISO whose samples to transfer.
        :type iso: :class:`thelma.models.job.Iso`

        :param log: The ThelmaLog you want to write into. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """
        IsoSampleStockRackTool.__init__(self, iso=iso, log=log,
                                 logging_level=logging_level,
                                 add_default_handlers=add_default_handlers)

        #: The zip stream wrapped aournd the merged stream.
        self.__zip_stream = None
        #: The different stream merged into one file.
        self.__merged_stream = None
        #: The zip map for the zip archive.
        self.__zip_map = None

        #: The CyBio overview stream (only if it is a CyBio transfer).
        self.__cybio_stream = None


    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        IsoSampleStockRackTool.reset(self)
        self.__zip_stream = None
        self.__zip_map = dict()
        self.__merged_stream = None
        self.__cybio_stream = None

    def get_zip_map(self):
        """
        Returns the zip map for the archive (for use in other writers).
        """
        if self.return_value is None:
            return None
        else:
            for stream in self.__zip_map.values(): stream.seek(0)
            return self.__zip_map

    def _execute_task(self):
        """
        Creates the worklists files and stores them in a zip archive.
        """
        self.add_debug('Prepare worklist execution ...')

        self._check_for_biomek_marker()
        if not self.has_errors():
            series_writer = SeriesWorklistWriter(log=self.log,
                                            transfer_jobs=self._transfer_jobs)
            stream_map = series_writer.get_result()
            if stream_map is None:
                msg = 'Error during serial worklist file generation.'
                self.add_error(msg)

        if not self.has_errors():
            self.__create_zip_archive(stream_map)
            self.return_value = self.__zip_stream
            self.add_info('Worklist file creation completed.')

    def _check_for_biomek_marker(self):
        """
        Checks whether the worklist is intended to be conducted for a Biomek.
        """
        for_cybio = False
        if len(self._transfer_jobs) > 1:
            for_cybio = True
        else:
            worklist_label = self._transfer_jobs[0].planned_worklist.label
            if not StockTransferWorklistGenerator.BIOMEK_MARKER \
                                                        in worklist_label:
                for_cybio = True

        if for_cybio: self.__create_cybio_info_file()

    def __create_cybio_info_file(self):
        """
        Creates rack transfer jobs for the stock transfer and creates a
        cybio info file for them.
        """
        self.add_debug('Create CyBio info file ...')

        rack_transfer_jobs = dict()
        multiple_volumes = []

        for sector_index, issr in self._sample_stock_racks.iteritems():
            worklist = issr.planned_worklist
            volumes = set()
            for pct in worklist.planned_transfers:
                volumes.add(pct.volume * VOLUME_CONVERSION_FACTOR)
            if len(volumes) > 1:
                info = '%s (sector: %i, sample stock rack %s)!' \
                       % (list(volumes), sector_index, issr.rack.barcode)
                multiple_volumes.append(info)
                continue

            if len(volumes) < 1: continue
            volume = list(volumes)[0] / VOLUME_CONVERSION_FACTOR
            prt = PlannedRackTransfer(volume=volume, sector_number=4,
                        source_sector_index=0, target_sector_index=sector_index)
            rt_job = RackTransferJob(index=sector_index,
                                planned_rack_transfer=prt,
                                target_rack=self._preparation_plate,
                                source_rack=issr.rack)
            sector_number = sector_index + 1
            rack_transfer_jobs[sector_number] = rt_job

        if len(multiple_volumes) > 0:
            msg = 'Unable to create CyBio file because some rack sectors ' \
                  'have more than one volume: %s. Do you want to continue?' \
                  % (multiple_volumes)
            self.add_warning(msg)
        else:
            self.__cybio_stream = create_rack_sector_stream(log=self.log,
                                                job_map=rack_transfer_jobs)
            if self.__cybio_stream is None:
                msg = 'Unable to create CyBio file. Do you want to continue?'
                self.add_warning(msg)

    def __create_zip_archive(self, stream_map):
        """
        Creates the zip file for the output.
        """
        self.add_debug('Create zip file ...')

        self.__zip_stream = StringIO()

        zip_fn = self.BIOMEK_FILE_NAME % (self.iso.label)
        if len(stream_map) == 1:
            stream = stream_map.values()[0]
            self.__zip_map[zip_fn] = stream
        else:
            self.__merged_stream = merge_csv_streams(stream_map)
            self.__zip_map[zip_fn] = self.__merged_stream

        if not self.__cybio_stream is None:
            zip_fn = self.CYBIO_FILE_NAME % (self.iso.label)
            self.__zip_map[zip_fn] = self.__cybio_stream

        create_zip_archive(zip_stream=self.__zip_stream,
                           stream_map=self.__zip_map)
