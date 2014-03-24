"""
Tools involved the execution of pool stock sample creation worklists.

AAB
"""
from thelma.automation.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.semiconstants import get_positions_for_shape
from thelma.automation.semiconstants import get_reservoir_spec
from thelma.automation.tools.iso.base import IsoRackContainer
from thelma.automation.tools.iso.base import StockRackLayoutConverter
from thelma.automation.tools.iso.base import StockRackVerifier
from thelma.automation.tools.iso.base import StockTransferWriterExecutor
from thelma.automation.tools.iso.poolcreation.base \
    import PoolCreationStockRackLayoutConverter
from thelma.automation.tools.iso.poolcreation.base \
    import SingleDesignStockRackLayoutConverter
from thelma.automation.tools.iso.poolcreation.base \
    import StockSampleCreationLayout
from thelma.automation.tools.iso.poolcreation.base \
    import StockSampleCreationLayoutConverter
from thelma.automation.tools.iso.poolcreation.base import LABELS
from thelma.automation.tools.iso.poolcreation.generation \
    import StockSampleCreationWorklistGenerator
from thelma.automation.tools.iso.tracreporting import IsoStockTransferReporter
from thelma.automation.tools.worklists.series import SampleDilutionJob
from thelma.automation.tools.worklists.series import SampleTransferJob
from thelma.automation.tools.writers import CsvColumnParameters
from thelma.automation.tools.writers import CsvWriter
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.utils.base import add_list_map_element
from thelma.automation.utils.base import get_trimmed_string
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import StockSampleCreationIso
from thelma.models.liquidtransfer import ExecutedWorklist

__docformat__ = 'reStructuredText en'

__all__ = ['StockSampleCreationExecutor',
           '_StockSampleCreationStockLogFileWriter',
           'StockSampleCreationStockTransferReporter']


class StockSampleCreationExecutor(StockTransferWriterExecutor):
    """
    Executes the worklist file for a pool stock sample creation ISO.
    This comprises both buffer dilution and stock transfer.

    **Return Value:** the updated ISO
    """
    NAME = 'Stock Sample Creation Executor'

    ENTITY_CLS = StockSampleCreationIso

    #: The barcode for the buffer source reservoir.
    BUFFER_RESERVOIR_BARCODE = 'buffer'

    _MODES = [StockTransferWriterExecutor.MODE_EXECUTE]

    def __init__(self, iso, user, **kw):
        """
        Constructor:

        :param iso: The stock sample creation ISO for which to execute the
            worklists.
        :type iso: :class:`thelma.models.iso.StockSampleCreationIso`

        :param user: The user conducting the execution.
        :type user: :class:`thelma.models.user.User`
        """
        StockTransferWriterExecutor.__init__(self, user=user, entity=iso,
                            mode=StockTransferWriterExecutor.MODE_EXECUTE, **kw)

        #: The stock sample creation layout for this ISO.
        self.__ssc_layout = None

        #: The :class:`IsoRackContainer` for each stock rack mapped onto
        #: rack marker.
        self.__rack_containers = None
        #: The stock rack that serves as target rack (:class:`IsoStockRack`).
        self.__pool_stock_rack = None

        #: The stock transfer worklist is the only worklist in the stock rack
        #: series.
        self.__stock_transfer_worklist = None

        #: The indices for the rack transfer jobs mapped onto the worklist
        #: they belong to.
        self.__rack_transfer_indices = None
        #: Positions without ISO positions (i.e. without transfer).
        self.__ignore_positions = None

    def reset(self):
        StockTransferWriterExecutor.reset(self)
        self.__ssc_layout = None
        self.__rack_containers = dict()
        self.__pool_stock_rack = None
        self.__stock_transfer_worklist = None
        self.__rack_transfer_indices = dict()
        self.__ignore_positions = []

    def _create_transfer_jobs(self):
        """
        Executes the pool creation worklists.
        """
        if not self.has_errors(): self.__get_layout()
        if not self.has_errors(): self.__get_racks()
        if not self.has_errors(): self.__create_buffer_transfer_job()
        if not self.has_errors(): self.__create_stock_transfer_jobs()

    def get_stock_sample_creation_layout(self):
        """
        Returns the working layout containing the molecule design pool ID data
        (for reporting).
        """
        return self._get_additional_value(self.__ssc_layout)

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        StockTransferWriterExecutor._check_input(self)
        if not self.has_errors() and \
                                not self.entity.status == ISO_STATUS.QUEUED:
            msg = 'Unexpected ISO status: "%s"' % (self.entity.status)
            self.add_error(msg)

    def __get_layout(self):
        """
        Fetches the stock sample layout and sorts its positions into quadrants.
        """
        self.add_debug('Fetch stock sample layout ...')

        converter = StockSampleCreationLayoutConverter(log=self.log,
                                           rack_layout=self.entity.rack_layout)
        self.__ssc_layout = converter.get_result()

        if self.__ssc_layout is None:
            msg = 'Error when trying to convert stock sample creation ISO ' \
                  'layout.'
            self.add_error(msg)
        else:
            ssc_positions = self.__ssc_layout.get_positions()
            for rack_pos in get_positions_for_shape(RACK_SHAPE_NAMES.SHAPE_96):
                if not rack_pos in ssc_positions:
                    self.__ignore_positions.append(rack_pos)

    def __get_racks(self):
        """
        Fetches the ISO stock rack and the single molecule stock racks
        (barcodes for the single design racks are found in the worklist labels).
        """
        self.add_debug('Fetch stock racks ...')

        isrs = self.entity.iso_stock_racks
        for isr in isrs:
            label = isr.label
            label_values = self._run_and_record_error(
                        meth=LABELS.parse_stock_rack_label,
                        base_msg='Error when trying to parse stock rack ' \
                                 'label "%s"' % (isr.label),
                        error_types=IndexError,
                        **dict(stock_rack_label=label))
            if label_values is None: continue
            rack_marker = label_values[LABELS.MARKER_RACK_MARKER]
            if rack_marker == LABELS.ROLE_POOL_STOCK:
                if self.__pool_stock_rack is not None:
                    msg = 'There are several pool stock racks for this ISO!'
                    self.add_error(msg)
                    break
                self.__pool_stock_rack = isr
            else:
                rack_container = IsoRackContainer(rack=isr.rack,
                                 rack_marker=rack_marker, label=label)
                self.__rack_containers[rack_marker] = rack_container

        number_designs = self.entity.iso_request.number_designs
        exp_lengths = ((number_designs + 1), 2)
        if not len(isrs) in exp_lengths:
            msg = 'There is an unexpected number of stock racks ' \
                  'attached to this ISO (%i). There should be %s! ' \
                  % (len(isrs), self._get_joined_str(exp_lengths, is_strs=False,
                                          sort_items=False, separator=' or '))
            self.add_error(msg)
            return None
        elif self.__pool_stock_rack is None and not self.has_errors():
            msg = 'There is no pool stock rack for this ISO!'
            self.add_error(msg)
        elif self.__pool_stock_rack is not None:
            ws = self.__pool_stock_rack.worklist_series
            if len(ws) > 1:
                msg = 'The stock rack worklist series has an unexpected ' \
                      'length (%i instead of 1)!' % (len(ws))
                self.add_error(msg)
                return None
            self.__stock_transfer_worklist = ws.get_sorted_worklists()[0]

    def __create_buffer_transfer_job(self):
        """
        Creates the transfer job for the buffer worklist.
        """
        self.add_debug('Create buffer transfer jobs ...')

        worklist_series = self.entity.iso_request.worklist_series
        buffer_worklist = worklist_series.get_worklist_for_index(
                  StockSampleCreationWorklistGenerator.BUFFER_WORKLIST_INDEX)

        rs = get_reservoir_spec(RESERVOIR_SPECS_NAMES.FALCON_MANUAL)
        job_index = len(self._transfer_jobs)
        cdj = SampleDilutionJob(index=job_index,
                             planned_worklist=buffer_worklist,
                             target_rack=self.__pool_stock_rack.rack,
                             reservoir_specs=rs,
                             source_rack_barcode=self.BUFFER_RESERVOIR_BARCODE,
                             ignored_positions=self.__ignore_positions)
        self._transfer_jobs[job_index] = cdj

    def __create_stock_transfer_jobs(self):
        """
        Creates the transfer jobs for the pool creation. We do not need
        to regard potential empty (ignored) positions here, because the
        worklist creation is already based on the library layout.
        """
        self.add_debug('Create pool creation transfer jobs ...')

        for rack_container in self.__rack_containers.values():
            job_index = len(self._transfer_jobs)
            stj = SampleTransferJob(index=job_index,
                    planned_worklist=self.__stock_transfer_worklist,
                    target_rack=self.__pool_stock_rack.rack,
                    source_rack=rack_container.rack)
            self._transfer_jobs[job_index] = stj

    def _verify_stock_racks(self):
        """
        We convert the layouts separately because the layout have different
        types. Also the pool stock rack is checked separately because the
        referring tubes must all be empty.
        """
        self.__verify_pool_stock_rack()
        num_stock_racks = len(self.entity.iso_stock_racks)
        incompatible = []
        for isr in self.entity.iso_stock_racks:
            layout = None
            kw = dict(log=self.log, rack_layout=isr.rack_layout)
            rack_name = '%s (%s)' % (isr.rack.barcode, isr.label)
            if isr.label == self.__pool_stock_rack.label:
                continue # has been checked separately
            elif num_stock_racks == 2:
                converter_cls = SingleDesignStockRackLayoutConverter
            else:
                converter_cls = StockRackLayoutConverter
            converter = converter_cls(**kw)
            layout = converter.get_result()
            if layout is None:
                msg = 'Error when trying to convert stock rack layout for ' \
                      'rack %s!' % (rack_name)
                self.add_error(msg)
            else:
                verifier = StockRackVerifier(log=self.log, stock_rack=isr,
                                             stock_rack_layout=layout)
                compatible = verifier.get_result()
                if compatible is None:
                    msg = 'Error when trying to verify stock rack %s.' \
                           % (rack_name)
                    self.add_error(msg)
                elif not compatible:
                    incompatible.append(rack_name)

        if len(incompatible) > 0:
            msg = 'The following stock racks are not compatible: %s.' \
                   % (self._get_joined_str(incompatible))
            self.add_error(msg)

    def __verify_pool_stock_rack(self):
        """
        Makes sure there are empty tubes in all required positions and none
        in positions that must be empty.
        """
        converter = PoolCreationStockRackLayoutConverter(log=self.log,
                             rack_layout=self.__pool_stock_rack.rack_layout)
        layout = converter.get_result()
        if layout is None:
            msg = 'Error when trying to convert pool stock rack layout!'
            self.add_error(msg)
        else:
            additional_tubes = []
            non_empty_tube = []
            positions = layout.get_positions()
            tube_positions = set()
            rack = self.__pool_stock_rack.rack
            for tube in rack.containers:
                rack_pos = tube.location.position
                tube_positions.add(rack_pos)
                info = '%s (%s)' % (tube.barcode, rack_pos.label)
                if not rack_pos in positions:
                    additional_tubes.append(info)
                elif not tube.sample is None:
                    non_empty_tube.append(info)
            missing_tube = []
            for rack_pos in get_positions_for_shape(layout.shape):
                sr_pos = layout.get_working_position(rack_pos)
                if sr_pos is None:
                    continue
                elif rack_pos not in tube_positions:
                    missing_tube.append(rack_pos.label)

            if len(additional_tubes) > 0:
                msg = 'There are unexpected tubes in the pool stock rack ' \
                      '(%s): %s. Please remove them and try again.' \
                      % (rack.barcode, self._get_joined_str(additional_tubes))
                self.add_error(msg)
            if len(non_empty_tube) > 0:
                msg = 'The following tubes in the pool stock rack (%s) are ' \
                      'not empty: %s. Please replace them by empty tubes and ' \
                      'try again.' % (rack.barcode,
                                      self._get_joined_str(non_empty_tube))
                self.add_error(msg)
            if len(missing_tube) > 0:
                msg = 'There are tubes missing in the following positions ' \
                      'of the pool stock rack (%s): %s.' % (rack.barcode,
                       self._get_joined_str(missing_tube))
                self.add_error(msg)

    def _check_for_previous_execution(self):
        if len(self.__stock_transfer_worklist.executed_worklists) > 0:
            msg = 'The stock transfer has already been executed before.'
            self.add_error(msg)

    def _extract_executed_stock_worklists(self, executed_worklists):
        """
        The worklists are recognized by label.
        """
        exp_label = self.__stock_transfer_worklist.label
        for ew in executed_worklists:
            if ew.planned_worklist.label == exp_label:
                self._executed_stock_worklists.append(ew)

    def _update_iso_status(self):
        self.entity.status = ISO_STATUS.DONE
        self.__create_stock_samples()

    def __create_stock_samples(self):
        """
        Converts the new pool samples into :class:`StockSample` entities.

        We also compare expected and found molecule designs again. This has
        in theory already been done by the verifier. However, we have done a
        transfer in between and we want to exclude the (slight) chance that
        something went wrong during this process since afterwards it will hardly
        be possible to reconstruct the course of events and in case of the
        stock we better double-check.
        """
        self.add_debug('Generate stock samples ...')

        mismatch = []
        diff_supplier = []

        for tube in self.__pool_stock_rack.rack.containers:
            sample = tube.sample
            if sample is None: continue
            # check whether expected pool
            rack_pos = tube.location.position
            ssc_pos = self.__ssc_layout.get_working_position(rack_pos)
            pool = ssc_pos.pool
            exp_mds = set()
            for md in pool: exp_mds.add(md.id)
            found_mds = set()
            suppliers = set()
            for sm in sample.sample_molecules:
                md_id = sm.molecule.molecule_design.id
                found_mds.add(md_id)
                suppliers.add(sm.molecule.supplier)
            if not exp_mds == found_mds:
                info = '%s (pool: %s, expected designs: %s, found designs: ' \
                       '%s)' % (rack_pos, pool,
                        self._get_joined_str(exp_mds, is_strs=False,
                                             separator='-'),
                        self._get_joined_str(found_mds, is_strs=False,
                                             separator='-'))
                mismatch.append(info)
                continue
            if len(suppliers) > 1:
                info = '%s (pool: %s, found: %s)' % (rack_pos, pool,
                       ', '.join(sorted([str(s.name) for s in suppliers])))
                diff_supplier.append(info)
                continue
            else:
                sample.convert_to_stock_sample()

        if len(mismatch) > 0:
            msg = 'The molecule designs for the following stock sample do ' \
                  'not match the expected designs for this sample. This ' \
                  'should not happen. Talk to the IT department, please. ' \
                  'Details: %s.' % (','.join(sorted(mismatch)))
            self.add_error(msg)
        if len(diff_supplier) > 0:
            msg = 'The designs for some of the pools originate from ' \
                  'different suppliers: %s.' \
                   % (', '.join(sorted(diff_supplier)))
            self.add_error(msg)

    #pylint: disable=W0613
    def _get_file_map(self, merged_stream_map, rack_transfer_stream):
        """
        We do not need to implement this method because printing mode is not
        not allowed anyway.
        """
        self.add_error('Printing mode is not allowed for this tool!')
    #pylint: disable=W0613


class StockSampleCreationStockTransferReporter(IsoStockTransferReporter):
    """
    A special reporter for stock sample creation ISOs.

    **Return Value:** The log file as stream (arg 0) and comment (arg 1)s
    """
    EXECUTOR_CLS = StockSampleCreationExecutor

    def __init__(self, executor, **kw):
        """
        Constructor:

        :param executor: The executor tool (after run has been completed).
        :type executor: :class:`_LabIsoWriterExecutorTool`
        """
        IsoStockTransferReporter.__init__(self, executor=executor, **kw)

        #: The stock sample creation layout for this ISO.
        self.__ssc_layout = None

    def reset(self):
        IsoStockTransferReporter.reset(self)
        self.__ssc_layout = None

    def _fetch_executor_data(self):
        IsoStockTransferReporter._fetch_executor_data(self)
        self.__ssc_layout = self.executor.get_stock_sample_creation_layout()
        self._check_input_class('layout', self.__ssc_layout,
                                StockSampleCreationLayout)

    def _set_ticket_id(self):
        """
        The ticket ID is attached to the stock sample creation ISO.
        """
        self._ticket_number = self.executor.entity.ticket_number

    def _get_sample_type_str(self):
        return 'new pooled stock samples'

    def _get_rack_str(self):
        """
        The rack string looks different, we use new ISO stock rack
        (instead of the preparation plate).
        """
        rack = self.executor.entity.iso_stock_racks[0].rack
        rack_str = "'''New pool stock rack:''' %s" % (rack.barcode)
        return rack_str

    def _get_log_file_writer(self):
        """
        For stock sample creation ISOs we use a special writer, the
        :class:`StockSampleCreationStockLogFileWriter`.
        """
        writer = _StockSampleCreationStockLogFileWriter(log=self.log,
                    stock_sample_creation_layout=self.__ssc_layout,
                    executed_worklists=self._executed_stock_worklists)
        return writer


class _StockSampleCreationStockLogFileWriter(CsvWriter):
    """
    Creates a log file after each pool creation stock transfer. The log
    file contains molecule design pools, molecule designs, stock tube barcodes
    and volumes and the barcode and positions in the target rack.

    **Return Value:** file stream (CSV format)
    """
    NAME = 'Stock Sample Creation Stock Transfer Log File Writer'

    #: The index for the molecule design pool ID column.
    POOL_INDEX = 0
    #: The header for the molecule design pool ID column.
    POOL_HEADER = 'Pool ID'

    #: The index for the single molecule design pool ID column.
    MOLECULE_DESIGN_INDEX = 1
    #: The header for the molecule design pool ID column.
    MOLECULE_DESIGN_HEADER = 'Molecule Design ID'

    #: The index for the tube barcode column.
    TUBE_BARCODE_INDEX = 2
    #: The header for the tube barcode column.
    TUBE_BARCODE_HEADER = 'Stock Tube Barcode'

    #: The index for the volume column.
    VOLUME_INDEX = 3
    #: The header for the volume column.
    VOLUME_HEADER = 'Volume (ul)'

    #: The index for the target rack barcode column.
    TARGET_RACK_BARCODE_INDEX = 4
    #: The header for the target rack barcode column.
    TARGET_RACK_BARCODE_HEADER = 'Target Rack Barcode'

    #: The index for the target position column.
    TARGET_POSITION_INDEX = 5
    #: The header for the target position column.
    TARGET_POSITION_HEADER = 'Target Position'


    def __init__(self, stock_sample_creation_layout, executed_worklists, log):
        """
        Constructor:

        :param stock_sample_creation_layout: The working_layout containing the
            molecule design pool data.
        :type stock_sample_creation_layout: :class:`StockSampleCreationLayout`

        :param executed_worklists: The executed worklists that have been
            generated by the executor (mapped onto transfer job indices).
        :type executed_worklists: :class:`dict`

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        CsvWriter.__init__(self, log=log)

        #: The executed worklists that have been generated by the executor.
        self.executed_worklists = executed_worklists
        #: The working layout containing the molecule design pool data.
        self.stock_sample_creation_layout = stock_sample_creation_layout

        #: Stores the values for the molecule design pool ID column.
        self.__pool_values = None
        #: Stores the values for the single molecule design IDs column.
        self.__md_values = None
        #: Stores the values for the tube barcode column.
        self.__tube_barcode_values = None
        #: Stores the values for the volume column.
        self.__volume_values = None
        #: Stores the values for the target rack barcode column.
        self.__trg_rack_barcode_values = None
        #: Stores the values for the target position column.
        self.__trg_position_values = None

    def reset(self):
        CsvWriter.reset(self)
        self.__pool_values = []
        self.__md_values = []
        self.__tube_barcode_values = []
        self.__volume_values = []
        self.__trg_rack_barcode_values = []
        self.__trg_position_values = []

    def _init_column_map_list(self):
        """
        Creates the :attr:`_column_map_list`
        """
        self.add_info('Start log file generation ...')

        self.__check_input()
        if not self.has_errors(): self.__store_column_values()
        if not self.has_errors(): self.__generate_column_maps()

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')

        self._check_input_list_classes('executed_worklist',
                            self.executed_worklists, ExecutedWorklist)

        self._check_input_class('stock sample creation layout',
                                self.stock_sample_creation_layout,
                                StockSampleCreationLayout)

    def __store_column_values(self):
        """
        Store the values for the columns.
        """
        self.add_debug('Store values ...')

        target_rack_map = dict()
        for ew in self.executed_worklists:
            for elt in ew.executed_liquid_transfers:
                target_rack_barcode = elt.target_container.location.rack.barcode
                if not target_rack_map.has_key(target_rack_barcode):
                    target_rack_map[target_rack_barcode] = []
                target_rack_map[target_rack_barcode].append(elt)

        barcodes = sorted(target_rack_map.keys())
        well_containers = set()

        for target_rack_barcode in barcodes:
            non_single_md_src_pool = []

            executed_transfers = target_rack_map[target_rack_barcode]
            pool_map = self.__get_sorted_executed_transfers(executed_transfers,
                                                            target_rack_barcode)
            if self.has_errors(): break

            pools = sorted(pool_map.keys(), cmp=lambda p1, p2:
                                            cmp(p1.id, p2.id))
            for pool in pools:
                elts = pool_map[pool]
                for elt in elts:
                    plt = elt.planned_liquid_transfer
                    self.__pool_values.append(get_trimmed_string(pool.id))
                    volume = plt.volume * VOLUME_CONVERSION_FACTOR
                    self.__volume_values.append(get_trimmed_string(volume))
                    self.__trg_rack_barcode_values.append(target_rack_barcode)
                    trg_label = plt.target_position.label
                    self.__trg_position_values.append(trg_label)

                    src_tube = elt.source_container
                    self.__tube_barcode_values.append(src_tube.barcode)
                    md_id = self.__get_molecule_design_id(src_tube)
                    if md_id is None:
                        info = '%s (rack %s)' % (src_tube.barcode,
                                                 target_rack_barcode)
                        non_single_md_src_pool.append(info)
                    else:
                        self.__md_values.append(get_trimmed_string(md_id))

            if len(non_single_md_src_pool) > 0:
                msg = 'Some source container contain more than one ' \
                      'molecule design: %s.' \
                       % (self._get_joined_str(non_single_md_src_pool))
                self.add_error(msg)

        if len(well_containers) > 0:
            msg = 'Some source containers in the worklists are wells: %s!' \
                   % (self._get_joined_str(well_containers))
            self.add_error(msg)

    def __get_sorted_executed_transfers(self, executed_transfers,
                                        target_rack_barcode):
        """
        Sorts the executed transfer of a worklist by pool and source
        tube barcode.
        """
        pool_map = dict()
        no_pools = set()

        for elt in executed_transfers:
            rack_pos = elt.target_container.location.position
            ssc_pos = self.stock_sample_creation_layout.get_working_position(
                                                                    rack_pos)
            if ssc_pos is None:
                info = '%s (rack %s)' % (rack_pos.label, target_rack_barcode)
                no_pools.add(info)
                continue
            pool = ssc_pos.pool
            add_list_map_element(pool_map, pool, elt)

        if len(no_pools) > 0:
            msg = 'Could not find molecule design pools for the following ' \
                  'target positions: %s.' % (self._get_joined_str(no_pools))
            self.add_error(msg)

        for pool, elts in pool_map.iteritems():
            elts.sort(cmp=lambda elt1, elt2: cmp(
                                            elt1.source_container.barcode,
                                            elt2.source_container.barcode))
        return pool_map

    def __get_molecule_design_id(self, tube):
        """
        Returns the molecule design for a single molecule design pool stock
        tube.
        """
        sms = tube.sample.sample_molecules
        if not len(sms) == 1: return None
        sm = sms[0]
        return sm.molecule.molecule_design.id

    def __generate_column_maps(self):
        """
        Initialises the CsvColumnParameters object for the
        :attr:`_column_map_list`.
        """
        pool_column = CsvColumnParameters(self.POOL_INDEX, self.POOL_HEADER,
                    self.__pool_values)
        md_column = CsvColumnParameters(self.MOLECULE_DESIGN_INDEX,
                    self.MOLECULE_DESIGN_HEADER, self.__md_values)
        tube_column = CsvColumnParameters(self.TUBE_BARCODE_INDEX,
                    self.TUBE_BARCODE_HEADER, self.__tube_barcode_values)
        volume_column = CsvColumnParameters(self.VOLUME_INDEX,
                    self.VOLUME_HEADER, self.__volume_values)
        rack_barcode_column = CsvColumnParameters(
                    self.TARGET_RACK_BARCODE_INDEX,
                    self.TARGET_RACK_BARCODE_HEADER,
                    self.__trg_rack_barcode_values)
        rack_position_column = CsvColumnParameters(self.TARGET_POSITION_INDEX,
                    self.TARGET_POSITION_HEADER, self.__trg_position_values)

        self._column_map_list = [pool_column, md_column, tube_column,
                                 volume_column, rack_barcode_column,
                                 rack_position_column]
