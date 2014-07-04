"""
Trac reporting for library creation ISOs.
"""
from thelma.automation.tools.iso.libcreation.base import LibraryLayout
from thelma.automation.tools.iso.libcreation.executor import \
    LibraryCreationIsoExecutor
from thelma.automation.tools.iso.poolcreation.base import StockSampleCreationLayoutConverter
from thelma.automation.tools.iso.poolcreation.generation import \
    StockSampleCreationTicketGenerator
from thelma.automation.tools.iso.poolcreation.writer import \
    StockSampleCreationTicketWorklistUploader
from thelma.automation.tools.iso.tracreporting import IsoStockTransferReporter
from thelma.automation.tools.writers import CsvColumnParameters
from thelma.automation.tools.writers import CsvWriter
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.utils.base import add_list_map_element
from thelma.automation.utils.base import get_trimmed_string
from thelma.models.iso import IsoSectorStockRack
from thelma.models.liquidtransfer import ExecutedWorklist


__docformat__ = 'reStructuredText en'
__all__ = ['LibraryCreationStockLogFileWriter',
           'LibraryCreationStockTransferReporter',
           'LibraryCreationTicketGenerator',
           'LibraryCreationTicketWorklistUploader',
           ]


class LibraryCreationTicketGenerator(StockSampleCreationTicketGenerator):
    """
    Creates an library creation trac ticket for a new ISO.

    **Return Value:** ticket ID
    """
    NAME = 'Library Creation Ticket Creator'
    #: The value for the ticket summary (title).
    SUMMARY = 'Library Creation ISO (%s)'
    #: The description for the empty ticket.
    DESCRIPTION_TEMPLATE = "Autogenerated ticket for library creation ISO " \
                           "'''%s'''.\n\nLayout number: %i\n\n"


class LibraryCreationTicketWorklistUploader(
                                StockSampleCreationTicketWorklistUploader):
    """
    Uses the worklist files the generated by the
    :class:`LibraryCreationWorklistWriter` and sends them to the ticket
    of the library creation ISO.
    """
    NAME = 'Library Creation Ticket Worklist Uploader'
    #: File name for the zip file in the Trac.
    FILE_NAME = '%s-%i_robot_worklists.zip'

    def _make_filename(self, iso):
        return self.FILE_NAME % (iso.label, iso.layout_number)


class LibraryCreationStockTransferReporter(IsoStockTransferReporter):
    EXECUTOR_CLS = LibraryCreationIsoExecutor
    SAMPLE_TYPE = 'samples'

    def _set_ticket_id(self):
        """
        The ticket ID is attached to the library creation ISO.
        """
        self._ticket_number = self.executor.iso.ticket_number

    def _get_sample_type_str(self):
        """
        All library members are samples.
        """
        return self.SAMPLE_TYPE

    def _get_rack_str(self):
        """
        The plate string looks different, we have one plate per quadrant
        (instead of one plate for ISO).
        """
        rack_map = \
            dict([(issr.sector_index, issr.rack.barcode)
                  for issr in self.executor.iso.iso_sector_stock_racks])
        rack_data = ['%s (Q%s)' % (rack_map[si], si + 1)
                     for si in sorted(rack_map.keys())]
        return ', '.join(rack_data)

    def _get_log_file_writer(self):
        """
        For library creation ISOs we use a special writer, the
        :class:`LibraryCreationStockLogFileWriter`.
        """
        stock_rack_map = \
                dict([(issr.sector_index, issr)
                      for issr in self.executor.iso.iso_sector_stock_racks])
        writer = LibraryCreationStockLogFileWriter(
                                self.executor.get_working_layout(),
                                self._executed_stock_worklists,
                                stock_rack_map, parent=self)
        return writer


class LibraryCreationStockLogFileWriter(CsvWriter):
    # FIXME: There is a lot of duplicate code with the
    #        _StockSampleCreationStockLogFileWriter class.
    """
    Creates a log file after each library creation stock transfer.

    The log file contains molecule design pools, molecule designs, stock
    tube barcodes and volumes and the barcode and positions in the target
    rack.

    **Return Value:** file stream (CSV format)
    """
    NAME = 'Library Creation Stock Transfer Log File Writer'
    #: The index for the library molecule design pool ID column.
    LIBRARY_POOL_INDEX = 0
    #: The header for the library molecule design pool ID column.
    LIBRARY_POOL_HEADER = 'Library Pool ID'
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

    def __init__(self, library_layout, executed_worklists,
                 stock_rack_map, parent=None):
        """
        Constructor.

        :param library_layout: The working_layout containing the molecule
            design pool data.
        :type library_layout: :class:`LibraryLayout`
        :param list executed_worklists: The executed worklists that have been
            generated by the executor (mapped onto transfer job indices).
        """
        CsvWriter.__init__(self, parent=parent)
        self.executed_worklists = executed_worklists
        self.library_layout = library_layout
        self.stock_rack_map = stock_rack_map
        #: Map source rack barcode -> stock sample creation layout.
        self.__ssc_layout_map = None
        #: Stores the values for the library molecule design pool ID column.
        self.__lib_pool_values = None
        #: Stores the values for the library molecule design pool ID column.
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
        self.__ssc_layout_map = dict()
        self.__lib_pool_values = []
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
        if not self.has_errors():
            self.__init_layouts()
        if not self.has_errors():
            self.__store_column_values()
        if not self.has_errors():
            self.__generate_column_maps()

    def __check_input(self):
        # Checks the initialisation values.
        self.add_debug('Check input values ...')
        self._check_input_list_classes('executed_worklist',
                                       self.executed_worklists,
                                       ExecutedWorklist)
        self._check_input_class('library layout', self.library_layout,
                                LibraryLayout)
        if self._check_input_class('sample stock racks map',
                                   self.stock_rack_map, dict):
            for sector_index, issr in self.stock_rack_map.iteritems():
                if not self._check_input_class('sector index',
                                               sector_index, int):
                    break
                if not self._check_input_class('sample stock rack', issr,
                                               IsoSectorStockRack):
                    break

    def __init_layouts(self):
        # The translators are used to determine the rack position holding
        # the pool information.
        for issr in self.stock_rack_map.itervalues():
            cnv = StockSampleCreationLayoutConverter(issr.rack_layout,
                                                     parent=self)
            self.__ssc_layout_map[issr.rack.barcode] = cnv.get_result()

    def __store_column_values(self):
        # Store the values for the columns.
        self.add_debug('Store values ...')
        target_rack_map = dict()
        for ew in self.executed_worklists:
            for et in ew.executed_liquid_transfers:
                target_rack_barcode = et.target_container.location.rack.barcode
                if not target_rack_map.has_key(target_rack_barcode):
                    target_rack_map[target_rack_barcode] = []
                target_rack_map[target_rack_barcode].append(et)
        barcodes = sorted(target_rack_map.keys())
        well_containers = set()
        for target_rack_barcode in barcodes:
            non_single_md_src_pool = []
            executed_transfers = target_rack_map[target_rack_barcode]
            pool_map = self.__get_sorted_executed_transfers(executed_transfers,
                                                            target_rack_barcode)
            if self.has_errors():
                break
            pools = sorted(pool_map.keys(), key=lambda p: p.id)
            for pool in pools:
                ets = pool_map[pool]
                for et in ets:
                    plt = et.planned_liquid_transfer
                    self.__lib_pool_values.append(get_trimmed_string(pool.id))
                    volume = plt.volume * VOLUME_CONVERSION_FACTOR
                    self.__volume_values.append(get_trimmed_string(volume))
                    self.__trg_rack_barcode_values.append(target_rack_barcode)
                    trg_label = plt.target_position.label
                    self.__trg_position_values.append(trg_label)
                    src_tube = et.source_container
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
                      'molecule design: %s.' % (sorted(non_single_md_src_pool))
                self.add_error(msg)
        if len(well_containers) > 0:
            msg = 'Some source containers in the worklists are wells: %s!' \
                   % (self._get_joined_str(well_containers))
            self.add_error(msg)

    def __get_sorted_executed_transfers(self, executed_transfers,
                                        target_rack_barcode):
        # Sorts the executed transfer of a worklist by molecule design pool
        # ID.
        pool_map = dict()
        no_pools = set()
        for et in executed_transfers:
            ssc_layout = self.__ssc_layout_map[et.source_rack.barcode]
            rack_pos = et.target_container.location.position
            ssc_pos = ssc_layout.get_working_position(rack_pos)
            if ssc_pos is None:
                info = '%s (rack %s)' % (rack_pos.label, target_rack_barcode)
                no_pools.add(info)
                continue
            pool = ssc_pos.pool
            add_list_map_element(pool_map, pool, et)
        if len(no_pools) > 0:
            msg = 'Could not find molecule design pools for the following ' \
                  'target positions: %s.' % (self._get_joined_str(no_pools))
            self.add_error(msg)
        for ets in pool_map.itervalues():
            ets.sort(key=lambda et: et.source_container.barcode)
        return pool_map

    def __get_molecule_design_id(self, tube):
        # Returns the molecule design for a single molecule design pool stock
        # tube.
        sms = tube.sample.sample_molecules
        if not len(sms) == 1:
            return None
        sm = sms[0]
        return sm.molecule.molecule_design.id

    def __generate_column_maps(self):
        # Initializes the CsvColumnParameters object for the
        # :attr:`_column_map_list`.
        pool_column = CsvColumnParameters(self.LIBRARY_POOL_INDEX,
                                          self.LIBRARY_POOL_HEADER,
                                          self.__lib_pool_values)
        md_column = CsvColumnParameters(self.MOLECULE_DESIGN_INDEX,
                                        self.MOLECULE_DESIGN_HEADER,
                                        self.__md_values)
        tube_column = CsvColumnParameters(self.TUBE_BARCODE_INDEX,
                                          self.TUBE_BARCODE_HEADER,
                                          self.__tube_barcode_values)
        volume_column = CsvColumnParameters(self.VOLUME_INDEX,
                                            self.VOLUME_HEADER,
                                            self.__volume_values)
        rack_barcode_column = \
            CsvColumnParameters(self.TARGET_RACK_BARCODE_INDEX,
                                self.TARGET_RACK_BARCODE_HEADER,
                                self.__trg_rack_barcode_values)
        rack_position_column = \
            CsvColumnParameters(self.TARGET_POSITION_INDEX,
                                self.TARGET_POSITION_HEADER,
                                self.__trg_position_values)
        self._column_map_list = [pool_column, md_column, tube_column,
                                 volume_column, rack_barcode_column,
                                 rack_position_column]
