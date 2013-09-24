"""
The classes in this module is takes part in the processing of stock samples
creation ISOs. It mainly deals with the generation of robot worklists. To this
end, it also assigns stock racks to the ISOs (including transfer worklists).

The following tasks are covered here:

 * fetch stock racks for the given barcode and check their states
 * assign ISO stock rack (this rack will take up the new pool stock samples)
 * create stock transfer worklists (sample transfer from single-molecule-design
     stock rack to pool stock rack)
 * create tube handler worklists
 * create layout overview file
 * create sample transfer robot files

The data can be uploaded to the corresponding trac ticket. However, this task
is taken over from an external trac tool.

AAB
"""
from datetime import datetime
from everest.entities.utils import get_root_aggregate
from everest.querying.specifications import cntd
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.iso.base import IsoRackContainer
from thelma.automation.tools.iso.base import StockRackLayout
from thelma.automation.tools.worklists.base import EmptyPositionManager
from thelma.automation.tools.semiconstants import PIPETTING_SPECS_NAMES
from thelma.automation.tools.iso.base import StockRackPosition
from thelma.automation.tools.utils.layouts import TransferTarget
from thelma.automation.tools.iso.poolcreation.base \
    import PoolCreationStockRackPosition
from thelma.automation.tools.iso.poolcreation.base \
    import StockSampleCreationLayout
from thelma.automation.tools.iso.poolcreation.base \
    import StockSampleCreationLayoutConverter
from thelma.automation.tools.iso.poolcreation.base import LABELS
from thelma.automation.tools.iso.poolcreation.base import VolumeCalculator
from thelma.automation.tools.iso.poolcreation.generation \
    import StockSampleCreationWorklistGenerator
from thelma.automation.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_pipetting_specs_cybio
from thelma.automation.tools.semiconstants import get_positions_for_shape
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import get_trimmed_string
from thelma.automation.tools.utils.base import is_valid_number
from thelma.automation.tools.utils.base import round_up
from thelma.automation.tools.worklists.tubehandler import TubeTransferData
from thelma.automation.tools.worklists.tubehandler import XL20WorklistWriter
from thelma.automation.tools.writers import CsvColumnParameters
from thelma.automation.tools.writers import CsvWriter
from thelma.automation.tools.writers import TxtWriter
from thelma.interfaces import ITube
from thelma.interfaces import ITubeRack
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import IsoStockRack
from thelma.models.iso import StockSampleCreationIso
from thelma.models.liquidtransfer import PlannedSampleTransfer
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.liquidtransfer import WorklistSeries

__docformat__ = 'reStructuredText en'

__all__ = ['StockSampleCreationWorklistWriter',
           'StockSampleCreationXL20ReportWriter',
           'StockSampleCreationInstructionsWriter',
           'StockSampleCreationIsoLayoutWriter']


class StockSampleCreationWorklistWriter(BaseAutomationTool):
    """
    Writes the worklists files for a pool stock sample creation ISO.
    This comprises:

    - 1 tube handler worklist
    - 1 tube handler report
    - layout data file
    - overview file

    The tool also assigns the ISO stock rack for the pool rack (the rack that
    will contain the pools to be created) and the destination racks
    (the target racks for the single molecule design pool).

    :Note: The files for the CyBio worklists cannot be generated here, because
        this requires the stock tubes to be transferred.

    **Return Value:** The generated files as streams (mapped onto file names).
    """

    NAME = 'Stock Sample Creation Worklist Writer'

    #: File name for a tube handler worklist file. The placeholder contains
    #: the ISO label.
    FILE_NAME_XL20_WORKLIST = '%s_xl20_worklist.csv'
    #: File name for a tube handler worklist file. The placeholder contains
    #: the ISO label.
    FILE_NAME_XL20_REPORT = '%s_xl20_summary.csv'
    #: File name for the CyBio instructions info file. The placeholders contains
    #: the ISO label.
    FILE_NAME_INSTRUCTIONS = '%s_instructions.txt'
    #: File name for the layout data file. The placeholder contains the ISO
    #: label.
    FILE_NAME_LAYOUT = '%s_layout.csv'

    def __init__(self, iso, tube_destination_racks, pool_stock_rack_barcode,
                 use_single_source_rack=False, **kw):
        """
        Constructor:

        :param iso: The pool stock sample creation ISO for which to generate
            the worklist files.
        :type iso: :class:`thelma.models.iso.StockSampleCreationIso`

        :param tube_destination_racks: The barcodes for the destination
            racks for the single molecule design tubes (these racks have to be
            empty).
        :type tube_destination_racks: list of barcodes (:class:`basestring`)

        :param pool_stock_rack_barcode: The barcodes for the new pool stock rack
            (this rack has to have empty tubes in defined positions).
        :type pool_stock_rack_barcode: :class:`basestring`

        :param use_single_source_rack: If there are only few pools to be
            created the user might want to use a single stock rack.
        :type use_single_source_rack: :class:`bool`
        :default use_single_source_rack: *False*
        """
        BaseAutomationTool.__init__(self, depending=False, **kw)

        #: The pool creation ISO for which to generate the worklist files.
        self.iso = iso
        #: The barcodes for the destination racks for the single molecule
        #: design tubes (these racks have to be empty).
        self.tube_destination_racks = tube_destination_racks
        #: The barcodes for the new pool stock rack (this rack has to have
        #: empty tubes in defined positions).
        self.pool_stock_rack_barcode = pool_stock_rack_barcode
        #: If there are only dew pools to be created the user might want to
        #: use a single stock rack.
        self.use_single_source_rack = use_single_source_rack
        #: The layout number of the ISO.
        self.layout_number = None

        #: The volume that is taken from the stock (transfer of single molecule
        #: design solution).
        self.__stock_take_out_volume = None
        #: The buffer volume that has to be added to each pool stock tube to
        #: generate the request dilution.
        self.__buffer_volume = None

        #: Stores the generated file streams (mapped onto file names).
        self.__file_map = None

        #: Maps tube racks onto barcodes.
        self.__rack_map = None
        #: The :class:`IsoRackContainer` for each involved stock rack mapped
        #; onto rack barcodes.
        self.__rack_containers = None

        #: The :class:`StockSampleCreationLayout` for the ISO.
        self.__ssc_layout = None
        #: The :class:`StockRackLayout` objects for the tube destination racks
        #: mapped onto rack barcode.
        self.__dest_rack_layouts = None

        #: Contains positions for which we do not want to generate a pool
        #: (because there are not enough pools to fill a 8x12 rack).
        self.__ignored_positions = None

        #: Maps tube onto tube barcodes.
        self.__tube_map = dict()
        #: The tube transfer data items for the tube handler worklist writer.
        self.__tube_transfers = None
        #: Stores the rack location for each source rack (single molecule
        #: design pools).
        self.__source_rack_locations = None

    def reset(self):
        BaseAutomationTool.reset(self)
        self.layout_number = None
        self.__stock_take_out_volume = None
        self.__buffer_volume = None
        self.__rack_map = dict()
        self.__rack_containers = dict()
        self.__ssc_layout = None
        self.__dest_rack_layouts = dict()
        self.__ignored_positions = []
        self.__tube_map = dict()
        self.__tube_transfers = []
        self.__file_map = dict()
        self.__source_rack_locations = dict()

    def run(self):
        """
        Creates the worklist files.
        """
        self.reset()
        self.add_info('Start worklist file generation ...')
        self.__check_input()
        if not self.has_errors(): self.__set_volumes()
        if not self.has_errors(): self.__get_tube_racks()
        if not self.has_errors(): self.__get_layout()
        if not self.has_errors(): self.__write_layout_file()
        if not self.has_errors():
            self.__check_tube_destination_racks()
            self.__check_pool_stock_rack()
        if not self.has_errors(): self.__fetch_tube_locations()
        if not self.has_errors(): self.__write_tube_handler_files()
        if not self.has_errors() and self.use_single_source_rack:
            self.__write_instructions_file()
        if not self.has_errors(): self.__create_stock_racks()
        if not self.has_errors():
            self.return_value = self.__file_map
            self.add_info('Worklist file generation completed.')

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')

        if self._check_input_class('ISO', self.iso, StockSampleCreationIso):
            status = self.iso.status
            if not status == ISO_STATUS.QUEUED:
                msg = 'Unexpected ISO status: "%s"' % (status)
                self.add_error(msg)
            self.layout_number = self.iso.layout_number

        self._check_input_list_classes('tube destination rack list',
                                       self.tube_destination_racks, basestring)
        self._check_input_class('pool stock rack barcode',
                                self.pool_stock_rack_barcode, basestring)
        self._check_input_class('"use single source rack " flag',
                                self.use_single_source_rack, bool)

    def __set_volumes(self):
        """
        Sets the stock take out volume and the buffer volume. These number are
        derived from the buffer worklist and the ISO request. The buffer volume
        could also be determined from the ISO request data - the below approach
        has been chosen because it comprises some additional checks.
        """
        worklist_series = self.iso.iso_request.worklist_series
        if worklist_series is None:
            msg = 'Unable to find worklist series for ISO request!'
            self.add_error(msg)
        elif not len(worklist_series) == 1:
            msg = 'The worklist series of the ISO request has an unexpected ' \
                  'length (%i, expected: 1).' % (len(worklist_series))
            self.add_error(msg)
        else:
            kw = dict(wl_index=\
                    StockSampleCreationWorklistGenerator.BUFFER_WORKLIST_INDEX)
            buffer_wl = self._run_and_record_error(error_type=ValueError,
                    meth=worklist_series.get_worklist_for_index,
                    base_msg='Error when trying to determine buffer volume: ',
                    **kw)
            if buffer_wl is not None:
                volume = None
                for psd in buffer_wl.planned_liquid_transfers:
                    if volume is None:
                        volume = psd.volume
                    elif not psd.volume == volume:
                        msg = 'There are different volumes in the buffer ' \
                              'dilution worklist!'
                        self.add_error(msg)
                        break
                if not self.has_errors() and not volume is None:
                    self.__buffer_volume = volume * VOLUME_CONVERSION_FACTOR

        volume_calculator = VolumeCalculator.from_iso_request(
                                            iso_request=self.iso.iso_request)
        self._run_and_record_error(volume_calculator.calculate,
                       base_msg='Unable to determine stock transfer volume: ',
                       error_type=ValueError)
        self.__stock_take_out_volume = volume_calculator.\
                                       get_single_design_stock_transfer_volume()

    def __get_tube_racks(self):
        """
        Fetches the tubes rack for the rack barcodes.
        """
        self.add_debug('Fetch tube racks ...')

        tube_rack_agg = get_root_aggregate(ITubeRack)
        not_found = []

        pool_rack = tube_rack_agg.get_by_slug(self.pool_stock_rack_barcode)
        if pool_rack is None:
            not_found.append(self.pool_stock_rack_barcode)
        else:
            self.__rack_map[self.pool_stock_rack_barcode] = pool_rack

        for barcode in self.tube_destination_racks:
            rack = tube_rack_agg.get_by_slug(barcode)
            if rack is None:
                not_found.append(barcode)
            else:
                self.__rack_map[barcode] = rack

        if len(not_found) > 0:
            msg = 'The following racks have not been found in the DB: %s!' \
                  % (', '.join(sorted(not_found)))
            self.add_error(msg)

    def __get_layout(self):
        """
        Fetches the stock sample creation layout and determines empty layout
        positions (ignored positions for worklists).
        """
        self.add_debug('Fetch stock sample creation layout ...')

        converter = StockSampleCreationLayoutConverter(log=self.log,
                                            rack_layout=self.iso.rack_layout)
        self.__ssc_layout = converter.get_result()

        if self.__ssc_layout is None:
            msg = 'Error when trying to convert stock sample creation layout.'
            self.add_error(msg)
        else:
            layout_positions = self.__ssc_layout.get_positions()
            for rack_pos in get_positions_for_shape(RACK_SHAPE_NAMES.SHAPE_96):
                if not rack_pos in layout_positions:
                    self.__ignored_positions.append(rack_pos)

    def __check_tube_destination_racks(self):
        """
        Makes sure there is the right number of tube destination racks and
        that all racks are empty.
        """
        self.add_debug('Check tube destination racks ...')

        not_empty = []

        number_designs = self.iso.iso_request.number_designs
        if self.use_single_source_rack:
            if len(self.tube_destination_racks) > 1:
                msg = 'There is more than one barcode for tube destination ' \
                      'list. Will use the smallest one.'
                self.add_warning(msg)
            allowed_pools = round_up(
                            len(self.__ssc_layout) / float(number_designs), 0)
            if allowed_pools > get_96_rack_shape().size:
                msg = 'One rack is not sufficient to take up all tubes ' \
                      '(%i tubes). Try again without requesting a single ' \
                      'source rack.'
                self.add_error(msg)

        elif not len(self.tube_destination_racks) == number_designs:
            msg = 'You need to provide %i empty racks. You have provided ' \
                  '%i barcodes.' % (number_designs,
                                    len(self.tube_destination_racks))
            self.add_error(msg)

        for barcode in sorted(self.tube_destination_racks):
            rack = self.__rack_map[barcode]
            if len(rack.containers) > 0: not_empty.append(barcode)
            if self.use_single_source_rack:
                rack_number = None
            else:
                rack_number = len(self.__rack_containers) + 1
            rack_marker = LABELS.create_rack_marker(
                                LABELS.ROLE_SINGLE_DESIGN_STOCK, rack_number)
            self._store_rack_container(rack, rack_marker)
            self.__dest_rack_layouts[barcode] = StockRackLayout()

        if len(not_empty) > 0:
            msg = 'The following tube destination racks you have chosen are ' \
                  'not empty: %s.' % (', '.join(sorted(not_empty)))
            self.add_error(msg)

    def __check_pool_stock_rack(self):
        """
        Checks whether the pool stock rack complies with there assumed
        (= not ignored) layout positions and whether all tubes are empty.
        """
        self.add_debug('Check pool stock racks ...')

        pool_rack = self.__rack_map[self.pool_stock_rack_barcode]
        self._store_rack_container(pool_rack, LABELS.ROLE_POOL_STOCK)
        tube_map = dict()
        for tube in pool_rack.containers:
            tube_map[tube.location.position] = tube

        tube_missing = []
        not_empty = []
        add_tube = []

        for rack_pos in get_positions_for_shape(pool_rack.rack_shape):
            if not rack_pos in self.__ignored_positions:
                if not tube_map.has_key(rack_pos):
                    tube_missing.append(rack_pos.label)
                    continue
                tube = tube_map[rack_pos]
                if tube.sample is None:
                    continue
                elif tube.sample.volume > 0:
                    not_empty.append(rack_pos.label)
            elif tube_map.has_key(rack_pos):
                add_tube.append(rack_pos.label)

        if len(tube_missing) > 0:
            msg = 'There are some tubes missing in the pool stock rack (%s): ' \
                  '%s.' % (self.pool_stock_rack_barcode,
                           ', '.join(sorted(tube_missing)))
            self.add_error(msg)
        if len(not_empty) > 0:
            msg = 'Some tubes in the pool stock rack (%s) which are not ' \
                  'empty: %s.' % (self.pool_stock_rack_barcode,
                                  ', '.join(sorted(not_empty)))
            self.add_error(msg)
        if len(add_tube) > 0:
            msg = 'There are some tubes in the pool stock rack (%s) that are ' \
                  'located in positions that should be empty: %s. Please ' \
                  'remove the tubes before continuing.' \
                  % (self.pool_stock_rack_barcode, ', '.join(sorted(add_tube)))
            self.add_warning(msg)

    def _store_rack_container(self, rack, rack_marker):
        """
        Convenience method registering a rack as rack container.
        """
        stock_rack_label = LABELS.create_stock_rack_label(self.iso.label,
                                                          rack_marker)
        rack_container = IsoRackContainer(rack=rack, rack_marker=rack_marker,
                                          label=stock_rack_label)
        self.__rack_containers[rack.barcode] = rack_container

    def __fetch_tube_locations(self):
        """
        Fetches the rack barcode amd tube location for every scheduled tube.
        Also generates :class:`TubeTransferData` and destination rack
        :class:`StockRackPosition` positions.
        """
        self.add_debug('Fetch tube locations ...')

        self.__fetch_tubes()

        if not self.has_errors():
            source_racks = set()
            for tube in self.__tube_map.values():
                source_rack = tube.location.rack
                source_racks.add(source_rack)

            self.__get_rack_locations(source_racks)
            if self.use_single_source_rack:
                self.__create_tube_transfers_for_single_source_rack()
            else:
                self.__create_tube_transfers_for_sectors()

    def __fetch_tubes(self):
        """
        Fetches tube (for location data), from the the DB. Uses the tube
        barcodes from the stock sample creation layouts.
        """
        self.add_debug('Fetch tubes ...')

        tube_barcodes = []
        for ssc_pos in self.__ssc_layout.working_positions():
            tube_barcodes.extend(ssc_pos.stock_tube_barcodes)

        tube_agg = get_root_aggregate(ITube)
        tube_agg.filter = cntd(barcode=tube_barcodes)
        iterator = tube_agg.iterator()
        while True:
            try:
                tube = iterator.next()
            except StopIteration:
                break
            else:
                self.__tube_map[tube.barcode] = tube

        if not len(tube_barcodes) == len(self.__tube_map):
            missing_tubes = []
            for tube_barcode in tube_barcodes:
                if not self.__tube_map.has_key(tube_barcode):
                    missing_tubes.append(tube_barcode)
            msg = 'Could not find tubes for the following tube barcodes: %s.' \
                  % (', '.join(sorted(missing_tubes)))
            self.add_error(msg)

    def __get_rack_locations(self, source_racks):
        """
        Returns a map that stores the rack location for each source rack
        (DB query).
        """
        self.add_debug('Fetch rack locations ...')

        for src_rack in source_racks:
            barcode = src_rack.barcode
            loc = src_rack.location
            if loc is None:
                self.__source_rack_locations[barcode] = 'not found'
                continue
            name = loc.name
            index = loc.index
            if index is None or len(index) < 1:
                self.__source_rack_locations[barcode] = name
            else:
                self.__source_rack_locations[barcode] = '%s, index: %s' \
                                                         % (name, index)

    def __create_tube_transfers_for_sectors(self):
        """
        Assign the tube data items to target positions and create tube
        transfer data items for them. The tubes for each pool to be generated
        are placed in the same rack position but onto different source racks.
        """
        for rack_pos, ssc_pos in self.__ssc_layout.iterpositions():
            tube_barcodes = ssc_pos.stock_tube_barcodes
            for i in range(len(tube_barcodes)):
                tube_barcode = tube_barcodes[i]
                trg_rack_barcode = self.tube_destination_racks[i]
                self.__store_tube_transfer(tube_barcode, trg_rack_barcode,
                                          rack_pos)
                self.__create_stock_rack_position(ssc_pos, tube_barcode,
                                                  rack_pos, trg_rack_barcode)

    def __create_tube_transfers_for_single_source_rack(self):
        """
        Assign the tube data items to target positions and create tube
        transfer data items for them. The tubes for each pool to be generated
        are placed in different rack position but onto the same source racks.
        """
        pos_manager = EmptyPositionManager(get_96_rack_shape())
        trg_rack_barcode = self.tube_destination_racks[0]
        for ssc_pos in self.__ssc_layout.get_sorted_working_positions():
            tube_barcodes = ssc_pos.stock_tube_barcodes
            for i in range(len(tube_barcodes)):
                src_pos = pos_manager.get_empty_position()
                tube_barcode = tube_barcodes[i]
                self.__store_tube_transfer(tube_barcode, trg_rack_barcode,
                                           src_pos)
                self.__create_stock_rack_position(ssc_pos, tube_barcode,
                                                  src_pos, trg_rack_barcode)

    def __store_tube_transfer(self, tube_barcode, trg_rack_barcode, rack_pos):
        """
        Convenience method creating and storing a :class:`TubeTransferData`
        object and a :class:`StockRackPosition`for the tube.
        """
        tube = self.__tube_map[tube_barcode]
        ttd = TubeTransferData(tube_barcode=tube_barcode,
                               src_rack_barcode=tube.rack.barcode,
                               src_pos=tube.position,
                               trg_rack_barcode=trg_rack_barcode,
                               trg_pos=rack_pos)
        self.__tube_transfers.append(ttd)

    def __create_stock_rack_position(self, ssc_pos, tube_barcode, src_rack_pos,
                                     trg_rack_barcode):
        """
        Convenience method creating and storing a tube destination
        :class:`StockRackPosition` for a source tube.
        """
        layout = self.__dest_rack_layouts[trg_rack_barcode]
        tt = TransferTarget(rack_position=ssc_pos.rack_position,
                            transfer_volume=self.__stock_take_out_volume,
                            target_rack_marker=LABELS.ROLE_POOL_STOCK)
        sr_pos = StockRackPosition(rack_position=src_rack_pos,
                                   molecule_design_pool=ssc_pos.pool,
                                   tube_barcode=tube_barcode,
                                   transfer_targets=[tt])
        layout.add_position(sr_pos)

    def __write_tube_handler_files(self):
        """
        Creates the tube handler worklists and report files.
        """
        self.add_debug('Write XL20 files ...')

        worklist_writer = XL20WorklistWriter(log=self.log,
                                         tube_transfers=self.__tube_transfers)
        worklist_stream = worklist_writer.get_result()
        if worklist_stream is None:
            msg = 'Error when trying to write tube handler worklist file.'
            self.add_error(msg)
        else:
            fn = self.FILE_NAME_XL20_WORKLIST % (self.iso.label)
            self.__file_map[fn] = worklist_stream

        report_writer = StockSampleCreationXL20ReportWriter(log=self.log,
                tube_transfers=self.__tube_transfers,
                iso_label=self.iso.label,
                layout_number=self.layout_number,
                take_out_volume=self.__stock_take_out_volume,
                source_rack_locations=self.__source_rack_locations)
        report_stream = report_writer.get_result()
        if report_stream is None:
            msg = 'Error when trying to write tube handler report.'
            self.add_error(msg)
        else:
            fn = self.FILE_NAME_XL20_REPORT % (self.iso.label)
            self.__file_map[fn] = report_stream

    def __write_layout_file(self):
        """
        Generates a file that summarises the ISO layout data in a CSV file.
        """
        writer = StockSampleCreationIsoLayoutWriter(log=self.log,
                                     pool_creation_layout=self.__ssc_layout)
        layout_stream = writer.get_result()
        if layout_stream is None:
            msg = 'Error when trying to generate layout data file.'
            self.add_error(msg)
        else:
            fn = self.FILE_NAME_LAYOUT % (self.iso.label)
            self.__file_map[fn] = layout_stream

    def __write_instructions_file(self):
        """
        Generates the file stream with the preparation instructions.
        """
        self.add_debug('Generate CyBio info file ...')

        writer = StockSampleCreationInstructionsWriter(log=self.log,
                        pool_stock_rack_barcode=self.pool_stock_rack_barcode,
                        tube_destination_racks=self.tube_destination_racks,
                        take_out_volume=self.__stock_take_out_volume,
                        buffer_volume=self.__buffer_volume)
        stream = writer.get_result()

        if stream is None:
            msg = 'Error when trying to write CyBio info file.'
            self.add_error(msg)
        else:
            fn = self.FILE_NAME_INSTRUCTIONS % (self.iso.label)
            self.__file_map[fn] = stream

    def __create_stock_racks(self):
        """
        Both the tube destination racks and the pool stock rack are stored
        as :class:`IsoStockRack` entities. Their function can be distinguished
        by the label.
        The worklist series is shared by all stock racks.
        """
        self.add_debug('Create pool stock racks ...')

        worklist_series = self.__create_takeout_worklist_series()
        self.__create_pool_stock_rack(worklist_series)

    def __create_takeout_worklist_series(self):
        """
        Creates the container transfers for the stock sample worklist (this
        is in theory a 1-to-1 rack transfer, but since the sources are tubes
        that can be moved we use container transfers instead).
        The worklist is wrapped into a worklist series.
        """
        self.add_debug('Create stock take out worklists ...')

        volume = self.__stock_take_out_volume / VOLUME_CONVERSION_FACTOR

        wl_label = LABELS.create_stock_transfer_worklist_label(self.iso.label)
        worklist = PlannedWorklist(label=wl_label,
                                   pipetting_specs=get_pipetting_specs_cybio(),
                                   transfer_type=TRANSFER_TYPES.SAMPLE_TRANSFER)
        for rack_pos in self.__ssc_layout.get_positions():
            pst = PlannedSampleTransfer(volume=volume,
                                        source_position=rack_pos,
                                        target_position=rack_pos)
            worklist.planned_liquid_transfers.append(pst)

        ws = WorklistSeries()
        ws.add_worklist(0, worklist)
        return ws

    def __create_stock_rack(self, worklist_series, rack, rack_layout,
                            stock_rack_label):
        """
        Helper method creating a new stock rack entity or updating an
        existing one. The match is made via the label.
        """
        stock_rack = None
        for isr in self.iso.iso_stock_racks:
            if isr.label == stock_rack_label:
                stock_rack = isr
                break

        if stock_rack is None:
            IsoStockRack(iso=self.iso, rack=rack, rack_layout=rack_layout,
                         worklist_series=worklist_series,
                         label=stock_rack_label)
        else:
            stock_rack.worklist_series = worklist_series
            stock_rack.rack = rack
            stock_rack.rack_layout = rack_layout

    def __create_pool_stock_rack(self, worklist_series):
        """
        Creates the ISO stock rack for the pool stock rack.
        """
        pool_rack = self.__rack_map[self.pool_stock_rack_barcode]
        rack_layout = self.__create_pool_stock_rack_layout(pool_rack)
        label = LABELS.create_stock_rack_label(self.iso.label,
                                               LABELS.ROLE_POOL_STOCK)
        self.__create_stock_rack(worklist_series, pool_rack, rack_layout, label)

    def __create_pool_stock_rack_layout(self, pool_rack):
        """
        The layouts stores pool and tube data for the pool stock rack that
        will take up the new pools.
        """
        stock_rack_layout = StockRackLayout()
        for tube in pool_rack.containers:
            rack_pos = tube.location.position
            ssc_pos = self.__ssc_layout.get_working_position(rack_pos)
            if ssc_pos is None: continue
            stock_rack_pos = PoolCreationStockRackPosition(
                           molecule_design_pool=ssc_pos.molecule_design_pool,
                           tube_barcode=tube.barcode, rack_position=rack_pos)
            stock_rack_layout.add_position(stock_rack_pos)

        return stock_rack_layout.create_rack_layout()

    def __create_single_design_stock_racks(self, worklist_series):
        """
        Creates the ISO stock rack for the tube destination racks. The layouts
        have already been generated during tube location finding.
        """
        for barcode in self.tube_destination_racks:
            rack_container = self.__rack_containers[barcode]
            layout = self.__dest_rack_layouts[barcode]
            self.__create_stock_rack(worklist_series, rack_container.rack,
                                     rack_layout=layout.create_rack_layout,
                                     stock_rack_label=rack_container.label)


class StockSampleCreationXL20ReportWriter(TxtWriter):
    """
    Generates an overview for the tube handling in a pool stock sample
    creation ISO.

    **Return Value:** stream (TXT)
    """
    NAME = 'Stock Sample Creation XL20 Report Writer'

    #: The main headline of the file.
    BASE_MAIN_HEADER = 'XL20 Worklist Generation Report / %s / %s'

    #: The header text for the general section.
    GENERAL_HEADER = 'General Settings'
    #: This line presents the ISO label.
    LABEL_LINE = 'ISO: %s'
    #: This line presents the layout number.
    LAYOUT_NUMBER_LINE = 'Layout number: %i'
    #: This line presents the total number of stock tubes used.
    TUBE_NO_LINE = 'Total number of tubes: %i'
    #: This line presents the transfer volume.
    VOLUME_LINE = 'Volume: %.1f ul'

    #: The header text for the destination racks section.
    DESTINATION_RACKS_HEADER = 'Destination Racks'
    #: The body for the destination racks section.
    DESTINATION_RACK_BASE_LINE = '%s'

    #: The header for the source racks section.
    SOURCE_RACKS_HEADER = 'Source Racks'
    #: The body for the source racks section.
    SOURCE_RACKS_BASE_LINE = '%s (%s)'

    def __init__(self, log, tube_transfers, iso_label, layout_number,
                 source_rack_locations, take_out_volume):
        """
        Constructor:

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param tube_transfers: Define which tube goes where.
        :type tube_transfers: :class:`TubeTransfer`

        :param iso_label: The label of the ISO we are dealing with.
        :type iso_label: :class:`str`

        :param layout_number: the layout for which we are creating racks
        :type layout_number: :class:`int`

        :param source_rack_locations: Maps rack locations onto rack barcodes.
        :type source_rack_locations: :class:`dict`

        :param take_out_volume: The volume to be transferred (for the single
            molecule design samples) *in ul*.
        :type take_out_volume: positive number
        """
        TxtWriter.__init__(self, log=log)

        #: Define which tube goes where.
        self.tube_transfers = tube_transfers
        #: The label of the ISO we are dealing with.
        self.iso_label = iso_label
        #: The layout for which we are creating racks
        self.layout_number = layout_number
        #: Maps rack locations onto rack barcodes.
        self.source_rack_locations = source_rack_locations
        #: The volume to be transferred (for the single molecule design samples)
        #: *in ul*.
        self.take_out_volume = take_out_volume

    def _check_input(self):
        """
        Checks if the tools has obtained correct input values.
        """
        if self._check_input_class('tube transfer list', self.tube_transfers,
                                   list):
            for ttd in self.tube_transfers:
                if not self._check_input_class('tube transfer', ttd,
                                               TubeTransferData): break

        self._check_input_class('ISO label', self.iso_label, basestring)
        self._check_input_class('layout number', self.layout_number, int)

        self._check_input_class('rack location map',
                                self.source_rack_locations, dict)

        if not is_valid_number(self.take_out_volume):
            msg = 'The stock take out volume must be a positive number ' \
                  '(obtained: %s).' % (self.take_out_volume)
            self.add_error(msg)

    def _write_stream_content(self):
        """
        Writes into the streams.
        """
        self.add_debug('Write stream ...')

        self.__write_main_headline()
        self.__write_general_section()
        self.__write_destination_racks_section()
        self.__write_source_racks_section()

    def __write_main_headline(self):
        """
        Writes the main head line.
        """
        now = datetime.now()
        date_string = now.strftime('%d.%m.%Y')
        time_string = now.strftime('%H:%M')
        main_headline = self.BASE_MAIN_HEADER % (date_string, time_string)
        self._write_headline(main_headline, underline_char='=',
                             preceding_blank_lines=0, trailing_blank_lines=1)

    def __write_general_section(self):
        """
        The general section contains ISO label, layout number and the number
        of tubes.
        """
        self._write_headline(self.GENERAL_HEADER, preceding_blank_lines=1)

        general_lines = [self.LABEL_LINE % (self.iso_label),
                         self.LAYOUT_NUMBER_LINE % (self.layout_number),
                         self.TUBE_NO_LINE % (len(self.tube_transfers)),
                         self.VOLUME_LINE % (self.take_out_volume)]
        self._write_body_lines(general_lines)

    def __write_destination_racks_section(self):
        """
        Writes the destination rack section.
        """
        barcodes = set()
        for ttd in self.tube_transfers:
            barcodes.add(ttd.trg_rack_barcode)

        self._write_headline(self.DESTINATION_RACKS_HEADER)
        lines = []
        for barcode in barcodes:
            lines.append(self.DESTINATION_RACK_BASE_LINE % (barcode))
        self._write_body_lines(lines)

    def __write_source_racks_section(self):
        """
        Writes the source rack section.
        """
        barcodes = set()
        for ttd in self.tube_transfers:
            barcodes.add(ttd.src_rack_barcode)
        sorted_barcodes = sorted(list(barcodes))

        self._write_headline(self.SOURCE_RACKS_HEADER)
        lines = []
        for barcode in sorted_barcodes:
            loc = self.source_rack_locations[barcode]
            if loc is None: loc = 'unknown location'
            lines.append(self.SOURCE_RACKS_BASE_LINE % (barcode, loc))
        self._write_body_lines(lines)


class StockSampleCreationInstructionsWriter(TxtWriter):
    """
    This tools writes an CyBio overview file for the CyBio steps involved in
    the creation of new pool sample stock racks.
    We do not use the normal series worklist writer here, because the stock
    tubes for the single molecule designs are not the right positions yet,
    and thus, the writer would fail.

    **Return Value:** stream (TXT)
    """
    NAME = 'Stock Sample Creation CyBio Writer'

    #: Header for the pool creation section.
    HEADER_POOL_CREATION = 'Pool Creation'

    #: Base line for transfer volumes.
    VOLUME_LINE = 'Volume: %.1f ul each'
    #: Base line for buffer volumes.
    BUFFER_LINE = 'Assumed buffer volume: %.1f ul'

    #: Base line for source racks (tube destination racks).
    SOURCE_LINE = 'Source rack(s): %s'
    #: Base line for target rack (new pool stock rack)
    TARGET_LINE = 'Target rack: %s'
    #: Base line for the robot to be used.
    ROBOT_LINE = 'Use %s robot for stock transfers.'

    def __init__(self, log, pool_stock_rack_barcode, tube_destination_racks,
                 take_out_volume, buffer_volume):
        """
        Constructor:

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param tube_destination_racks: The barcodes for the destination
            racks for the single molecule design tube (these racks have to be
            empty).
        :type tube_destination_racks: lists of barcodes (:class:`basestring`)

        :param pool_stock_rack_barcode: The barcode for the new pool stock rack
            (this racks has to have empty tubes in defined positions).
        :type pool_stock_rack_barcode: :class:`basestring`

        :param take_out_volume: The volume to be transferred (for the single
            molecule design samples) in ul.
        :type take_out_volume: positive number

        :param buffer_volume: The buffer volume in the new stock tubes in ul.
        :type buffer_volume: positive number
        """
        TxtWriter.__init__(self, log=log)

        #: The barcodes for the destination, rack for the single molecule
        #: design tubes.
        self.tube_destination_racks = tube_destination_racks
        #: The barcode for the new pool stock rack.
        self.pool_stock_rack_barcode = pool_stock_rack_barcode
        #: The volume to be transferred (for the single molecule design samples)
        #: in ul.
        self.take_out_volume = take_out_volume
        #: The buffer volume in the new stock tubes in ul.
        self.buffer_volume = buffer_volume

    def _check_input(self):
        self.add_debug('Check input values ...')

        if self._check_input_class('tube destination rack map',
                                   self.tube_destination_racks, list):
            for barcode in self.tube_destination_racks:
                if not self._check_input_class(
                       'barcode for a tube destination rack',
                        barcode, basestring): break
            if not len(self.tube_destination_racks) > 0:
                msg = 'There are no barcodes in the destination rack map!'
                self.add_error(msg)

        self._check_input_class('pool stock rack barcode',
                                self.pool_stock_rack_barcode, basestring)

        numbers = {self.take_out_volume : 'stock take out volume',
                   self.buffer_volume : 'buffer volume'}
        for value, name in numbers.iteritems():
            if not is_valid_number(value):
                msg = 'The %s must be a positive number (obtained: %s).' \
                      % (name, get_trimmed_string(value))
                self.add_error(msg)

    def _write_stream_content(self):
        self.add_debug('Write stream ...')

        self._write_headline(header_text=self.HEADER_POOL_CREATION,
                             preceding_blank_lines=0)


        volume_line = self.VOLUME_LINE % (self.take_out_volume)
        buffer_line = self.BUFFER_LINE % (self.buffer_volume)
        src_line = self.SOURCE_LINE \
                  % (self._get_joined_str(self.tube_destination_racks))
        trg_line = self.TARGET_LINE % (self.pool_stock_rack_barcode)
        if len(self.tube_destination_racks) == 1:
            use_robot = PIPETTING_SPECS_NAMES.CYBIO
        else:
            use_robot = 'Biomek (stock transfer setting)'
        robot_line = self.ROBOT_LINE % (use_robot)

        lines = [volume_line, buffer_line, src_line, trg_line, robot_line]
        self._write_body_lines(lines)


class StockSampleCreationIsoLayoutWriter(CsvWriter):
    """
    Generates an overview file containing the layout data for a particular
    stock sample creation ISO.

    **Return Value:** stream (CSV format)
    """
    NAME = 'Stock Sample Creation Layout Writer'

    #: The header for the rack position column.
    POSITION_HEADER = 'Rack Position'
    #: The header for the molecule design pool column.
    POOL_HEADER = 'Pool ID'
    #: The header for the molecule design column.
    MOLECULE_DESIGN_HEADER = 'Molecule Design IDs'
    #: The header for the stock tube barcode column.
    TUBE_HEADER = 'Stock Tubes'

    #: The index for the rack position column.
    POSITION_INDEX = 0
    #: The index for the molecule design pool column.
    POOL_INDEX = 1
    #: The index for the molecule design column.
    MOLECULE_DESIGN_INDEX = 2
    #: The index for the stock tube barcode column.
    TUBE_INDEX = 3

    def __init__(self, pool_creation_layout, log):
        """
        Constructor:

        :param pool_creation_layout: The layout of the pool creation ISO.
        :type pool_creation_layout: :class:`StockSampleCreationLayout`

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        CsvWriter.__init__(self, log=log)

        #: The layout of the pool stock sample creation ISO.
        self.ssc_layout = pool_creation_layout

        #: The values for the columns.
        self.__position_values = None
        self.__pool_values = None
        self.__md_values = None
        self.__tube_values = None

    def reset(self):
        CsvWriter.reset(self)
        self.__position_values = []
        self.__pool_values = []
        self.__md_values = []
        self.__tube_values = []

    def _init_column_map_list(self):
        if self._check_input_class('ISO layout', self.ssc_layout,
                                   StockSampleCreationLayout):
            self.__store_values()
            self.__generate_columns()

    def __store_values(self):
        """
        Fetches and stores the values for the columns.
        """
        self.add_debug('Store column values ...')

        for ssc_pos in self.ssc_layout.get_sorted_working_positions():
            self.__position_values.append(ssc_pos.rack_position.label)
            self.__pool_values.append(ssc_pos.pool.id)
            self.__md_values.append(ssc_pos.get_molecule_designs_tag_value())
            self.__tube_values.append(ssc_pos.get_stock_barcodes_tag_value())

    def __generate_columns(self):
        """
        Generates the :attr:`_column_map_list`
        """
        pos_column = CsvColumnParameters(self.POSITION_INDEX,
                                self.POSITION_HEADER, self.__position_values)
        pool_column = CsvColumnParameters(self.POOL_INDEX, self.POOL_HEADER,
                                self.__pool_values)
        md_column = CsvColumnParameters(self.MOLECULE_DESIGN_INDEX,
                                self.MOLECULE_DESIGN_HEADER, self.__md_values)
        tube_column = CsvColumnParameters(self.TUBE_INDEX, self.TUBE_HEADER,
                                self.__tube_values)
        self._column_map_list = [pos_column, pool_column, md_column,
                                 tube_column]
