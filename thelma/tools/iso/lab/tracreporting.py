"""
Tools that report to stock transfers involved in lab ISO preparation.

AAB
"""
from thelma.tools.iso.base import StockRackLayout
from thelma.tools.iso.lab.processing import _LabIsoWriterExecutorTool
from thelma.tools.iso.tracreporting import IsoStockTransferReporter
from thelma.tools.writers import CsvColumnParameters
from thelma.tools.writers import CsvWriter
from thelma.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.tools.utils.base import add_list_map_element
from thelma.tools.utils.base import get_trimmed_string
from thelma.entities.container import Tube
from thelma.entities.liquidtransfer import ExecutedWorklist
from thelma.entities.job import IsoJob
from thelma.tools.iso.lab.base import LAB_ISO_ORDERS


__docformat__ = 'reStructuredText en'

__all__ = ['LabIsoStockTransferReporter',
           'LabIsoStockTransferLogFileWriter']


class LabIsoStockTransferReporter(IsoStockTransferReporter): # pylint: disable=W0223
    """
    A special stock ISO stock transfer reporter for lab ISOs and ISO jobs.

    **Return Value:** The log file as stream (arg 0) and comment (arg 1)
    """
    EXECUTOR_CLS = _LabIsoWriterExecutorTool
    #: The sample type string if all transferred pools are controls (fixed).
    SAMPLE_TYPE_CONTROLS = 'controls'
    #: The sample type string if all transferred pools are samples (floating).
    SAMPLE_TYPE_SAMPLES = 'samples'
    #: The sample type string if there are both controls (fixed) and samples
    #: (floatings) among the transferred pools.
    SAMPLE_TYPE_BOTH = '%s and %s' % (SAMPLE_TYPE_CONTROLS, SAMPLE_TYPE_SAMPLES)

    def __init__(self, executor, parent=None):
        IsoStockTransferReporter.__init__(self, executor, parent=parent)
        #: The stock rack layouts mapped onto stock rack barcodes.
        self.__stock_rack_data = None

    def reset(self):
        IsoStockTransferReporter.reset(self)
        self.__stock_rack_data = None

    def _fetch_executor_data(self):
        IsoStockTransferReporter._fetch_executor_data(self)
        self.__stock_rack_data = self.executor.get_stock_rack_data()
        self._check_input_map_classes(self.__stock_rack_data,
                      'stock rack layout map', 'stock rack barcode', basestring,
                      'stock rack layout', StockRackLayout)

    def _get_log_file_writer(self):
        """
        By default, we use the :class:`StockTransferLogFileWriter`.
        """
        writer = LabIsoStockTransferLogFileWriter(
                            stock_rack_data=self.__stock_rack_data,
                            executed_worklists=self._executed_stock_worklists,
                            parent=self)
        return writer

    def _set_ticket_id(self):
        iso_request = self.executor.entity.iso_request
        self._ticket_number = iso_request.experiment_metadata.ticket_number

    def _get_sample_type_str(self):
        if self.executor.ENTITY_CLS == IsoJob:
            return self.SAMPLE_TYPE_CONTROLS
        processing_order = LAB_ISO_ORDERS.get_order(self.executor.entity)
        if processing_order == LAB_ISO_ORDERS.NO_ISO:
            return self.SAMPLE_TYPE_CONTROLS
        pool_set = self.executor.entity.molecule_design_pool_set
        if pool_set is None:
            return self.SAMPLE_TYPE_CONTROLS
        if processing_order == LAB_ISO_ORDERS.NO_JOB:
            # but we do have a pool set
            return self.SAMPLE_TYPE_BOTH
        else:
            return self.SAMPLE_TYPE_SAMPLES

    def _get_rack_str(self):
        """
        The target racks are contained in the executed worklists.
        In case of jobs the plates cannot be sorted by ISOs though because
        the ISO label cannot always be parsed from the plate labels.
        """
        plates = set()
        for executed_worklist in self._executed_stock_worklists:
            for elt in executed_worklist:
                trg_rack = elt.target_container.rack.barcode
                plates.add(trg_rack)

        return '\'\'\'Target plates:\'\'\' %s' % (self._get_joined_str(plates))


class LabIsoStockTransferLogFileWriter(CsvWriter):
    """
    Creates a log file after each stock transfer. The log file contains
    molecule designs, stock tube barcodes and volumes and the barcode and
    position in the target rack.

    **Return Value:** file stream (CSV format)
    """
    NAME = 'Stock Transfer Log File Writer'
    #: The index for the molecule design pool ID column.
    MOLECULE_DESIGN_POOL_INDEX = 0
    #: The header for the molecule design pool ID column.
    MOLECULE_DESIGN_POOL_HEADER = 'Molecule Design Pool ID'
    #: The index for the tube barcode column.
    TUBE_BARCODE_INDEX = 1
    #: The header for the tube barcode column.
    TUBE_BARCODE_HEADER = 'Stock Tube Barcode'
    #: The index for the volume column.
    VOLUME_INDEX = 2
    #: The header for the volume column.
    VOLUME_HEADER = 'Volume (ul)'
    #: The index for the target rack barcode column.
    TARGET_RACK_BARCODE_INDEX = 3
    #: The header for the target rack barcode column.
    TARGET_RACK_BARCODE_HEADER = 'Target Rack Barcode'
    #: The index for the target position column.
    TARGET_POSITION_INDEX = 4
    #: The header for the target position column.
    TARGET_POSITION_HEADER = 'Target Position'

    def __init__(self, stock_rack_data, executed_worklists, parent=None):
        """
        Constructor.

        :param stock_rack_data: The stock rack layouts are required to
            fetch the pool for a transfer mapped onto their barcodes.
        :type stock_rack_data: :class:`dict` with barcode as key and
            :class:`StockRackLayout` as value
        :param executed_worklists: The stock transfer executed worklists that
            have been generated by the executor.
        :type executed_worklists: :class:`list`
        """
        CsvWriter.__init__(self, parent=parent)
        #: The executed worklists that have been generated by the executor
        #: (mapped onto transfer job indices).
        self.executed_worklists = executed_worklists
        #: The stock rack layouts are required to fetch the pool for a
        #: transfer mapped onto their barcodes.
        self.stock_rack_data = stock_rack_data
        #: Stores the values for the molecule design pool ID column.
        self.__pool_values = None
        #: Stores the values for the tube barcode column.
        self.__tube_barcode_values = None
        #: Stores the values for the volume column.
        self.__volume_values = None
        #: Stores the values for the target rack barcode column.
        self.__trg_rack_barcode_values = None
        #: Stores the values for the target position column.
        self.__trg_position_values = None

    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        CsvWriter.reset(self)
        self.__pool_values = []
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
        if not self.has_errors():
            self.__store_column_values()
        if not self.has_errors():
            self.__generate_column_maps()

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')

        self._check_input_list_classes('executed worklist',
                      self.executed_worklists, ExecutedWorklist)
        self._check_input_map_classes(self.stock_rack_data,
                      'stock rack layout map', 'stock rack barcode',
                      basestring, 'stock rack layout', StockRackLayout)

    def __store_column_values(self):
        # Store the values for the columns.
        self.add_debug('Store values ...')
        source_rack_map = dict()
        for ew in self.executed_worklists:
            for elt in ew:
                source_rack_barcode = elt.source_container.rack.barcode
                add_list_map_element(source_rack_map, source_rack_barcode,
                                     elt)
        well_containers = dict()
        missing_layouts = []
        sorted_elts = dict()
        for source_rack_barcode in sorted(source_rack_map.keys()):
            executed_transfers = source_rack_map[source_rack_barcode]
            if not self.stock_rack_data.has_key(source_rack_barcode):
                missing_layouts.append(source_rack_barcode)
                continue
            layout = self.stock_rack_data[source_rack_barcode]
            pool_map = self.__get_sorted_executed_transfers(
                                                executed_transfers,
                                                layout, source_rack_barcode)
            if self.has_errors(): break
            for pool_id, elts in pool_map.iteritems():
                sorted_elts[pool_id] = elts
        for pool_id in sorted(sorted_elts.keys()):
            elts = sorted_elts[pool_id]
            for elt in elts:
                self.__pool_values.append(get_trimmed_string(pool_id))
                source_container = elt.source_container
                plt = elt.planned_liquid_transfer
                if not isinstance(source_container, Tube):
                    pos_label = plt.source_position.label
                    add_list_map_element(well_containers,
                            source_container.rack.barcode, pos_label)
                    continue
                self.__tube_barcode_values.append(source_container.barcode)
                volume = plt.volume * VOLUME_CONVERSION_FACTOR
                self.__volume_values.append(get_trimmed_string(volume))
                self.__trg_rack_barcode_values.append(elt.target_container.\
                                                      location.rack.barcode)
                self.__trg_position_values.append(plt.target_position.label)

        if len(well_containers) > 0:
            msg = 'Some source containers in the worklists are wells: %s!' \
                   % (self._get_joined_map_str(well_containers,
                                               'plate %s (positions %s)'))
            self.add_error(msg)
        if len(missing_layouts) > 0:
            msg = 'Unable to find the layouts for the following stock ' \
                  'racks: %s.' % (self._get_joined_str(missing_layouts))
            self.add_error(msg)

    def __get_sorted_executed_transfers(self, executed_liquid_transfers,
                                        stock_rack_layout, rack_barcode):
        # Sorts executed transfer of a worklist by molecule design pool ID.
        pool_map = dict()
        no_pools = set()
        for elt in executed_liquid_transfers:
            rack_pos = elt.planned_liquid_transfer.source_position
            sr_pos = stock_rack_layout.get_working_position(rack_pos)
            if sr_pos is None:
                no_pools.add(rack_pos.label)
                continue
            pool_id = sr_pos.molecule_design_pool.id
            add_list_map_element(pool_map, pool_id, elt)
        if len(no_pools) > 0:
            msg = 'Could not find molecule design pools for the following ' \
                  'source positions in rack %s: %s.' % (rack_barcode,
                  self._get_joined_str(no_pools, is_strs=False))
            self.add_error(msg)
        else:
            for elts in pool_map.values():
                elts.sort(cmp=lambda elt1, elt2: cmp(
                            elt1.planned_liquid_transfer.target_position,
                            elt2.planned_liquid_transfer.target_position))
                elts.sort(cmp=lambda elt1, elt2: cmp(
                            elt1.target_container.rack.barcode,
                            elt2.target_container.rack.barcode))
        return pool_map

    def __generate_column_maps(self):
        # Initialises the CsvColumnParameters object for the
        # :attr:`_column_map_list`.
        pool_column = CsvColumnParameters(self.MOLECULE_DESIGN_POOL_INDEX,
                    self.MOLECULE_DESIGN_POOL_HEADER, self.__pool_values)
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

        self._column_map_list = [pool_column, tube_column, volume_column,
                                 rack_barcode_column, rack_position_column]


