"""
The classes in this module serve the creation of an ISO for a pool stock sample
creation process.

The following tasks need to be performed:

 * check current state of the stock racks provided
 * create ISO sample stock rack (barcodes is provided)
 * create worklists for the ISO sample stock racks (sample transfer from
   single-molecule-design stock rack to pool stock rack)
 * create tube handler worklists
 * create layout overview file
 * create sample transfer robot files
 * upload data to a ticket

AAB
"""
from datetime import datetime
from everest.entities.utils import get_root_aggregate
from everest.querying.specifications import cntd
from everest.repositories.rdb.utils import as_slug_expression
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.libcreation.base import LibraryLayout
from thelma.automation.tools.libcreation.base import LibraryLayoutConverter
from thelma.automation.tools.poolcreation.base \
    import calculate_single_design_stock_transfer_volume_for_library
from thelma.automation.tools.poolcreation.generation \
    import PoolCreationWorklistGenerator
from thelma.automation.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.tools.semiconstants import get_positions_for_shape
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import get_trimmed_string
from thelma.automation.tools.utils.base import is_valid_number
from thelma.automation.tools.worklists.tubehandler import TubeTransferData
from thelma.automation.tools.worklists.tubehandler import XL20WorklistWriter
from thelma.automation.tools.writers import CsvColumnParameters
from thelma.automation.tools.writers import CsvWriter
from thelma.automation.tools.writers import TxtWriter
from thelma.interfaces import IMoleculeDesignLibrary
from thelma.interfaces import ITube
from thelma.interfaces import ITubeRack
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import IsoSampleStockRack
from thelma.models.library import LibraryCreationIso
from thelma.models.liquidtransfer import PlannedContainerTransfer
from thelma.models.liquidtransfer import PlannedWorklist
import logging

__docformat__ = 'reStructuredText en'

__all__ = ['PoolCreationWorklistWriter',
           'PoolCreationXL20ReportWriter',
           'PoolCreationCyBioOverviewWriter',
           'PoolCreationIsoLayoutWriter']


class PoolCreationWorklistWriter(BaseAutomationTool):
    """
    Writes the worklists files for a pool stock sample creation ISO.
    This comprises:

    - 1 tube handler worklist
    - 1 tube handler report
    - layout data file
    - overview file

    :Note: The files for the CyBio worklists cannot be generated here, because
        this requires the stock tubes to be transferred.

    **Return Value:** The worklist files as zip stream (mapped onto file names).
    """

    NAME = 'Library Creation Worklist Writer'

    #: Label for the worklists of the pool sample stock racks. The label
    #: will be appended by the source rack barcodes.
    SAMPLE_STOCK_WORKLIST_LABEL = 'from_'
    #: The delimiter for the source rack barcodes in the label of the
    #: stock transfer worklists.
    SAMPLE_STOCK_WORKLIST_DELIMITER = '-'

    #: File name for a tube handler worklist file. The placeholder contain
    #: the layout number and the ISO request name.
    FILE_NAME_XL20_WORKLIST = '%s-%s_xl20_worklist.csv'
    #: File name for a tube handler worklist file. The placeholder contain
    #: the layout number and the ISO request name.
    FILE_NAME_XL20_REPORT = '%s-%s_xl20_report.csv'
    #: File name for the CyBio instructions info file. The placeholders
    #: contain the layout number and the ISO request name.
    FILE_NAME_CYBIO = '%s-%s-CyBio_instructions.txt'
    #: File name for the layout data file. The placeholder contains the ISO
    #: label.
    FILE_NAME_LAYOUT = '%s_layout.csv'

    def __init__(self, pool_creation_iso, tube_destination_racks,
                 pool_stock_rack_barcode,
                 logging_level=logging.WARNING, add_default_handlers=False):
        """
        Constructor:

        :param pool_creation_iso: The pool creation ISO for which to
            generate the worklist files.
        :type pool_creation_iso:
            :class:`thelma.models.library.LibraryCreationIso`

        :param tube_destination_racks: The barcodes for the destination
            racks for the single molecule design tubes (these racks have to be
            empty).
        :type tube_destination_racks: list of barcodes (:class:`basestring`)

        :param pool_stock_rack_barcode: The barcodes for the new pool stock rack
            (this rack has to have empty tubes in defined positions).
        :type pool_stock_rack_barcode: :class:`basestring`

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

        #: The pool creation ISO for which to generate the worklist files.
        self.pool_creation_iso = pool_creation_iso
        #: The barcodes for the destination racks for the single molecule
        #: design tubes (these racks have to be empty).
        self.tube_destination_racks = tube_destination_racks
        #: The barcodes for the new pool stock rack (this rack has to have
        #: empty tubes in defined positions).
        self.pool_stock_rack_barcode = pool_stock_rack_barcode
        #: The plate set label of the ISO request the ISO belongs to.

        self.iso_request_label = None
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
        #: The library layout for the ISO.
        self.__library_layout = None
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
        self.iso_request_label = None
        self.layout_number = None
        self.__stock_take_out_volume = None
        self.__buffer_volume = None
        self.__rack_map = dict()
        self.__library_layout = None
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
        if not self.has_errors(): self.__get_library_layout()
        if not self.has_errors(): self.__write_layout_file()
        if not self.has_errors():
            self.__check_tube_destination_racks()
            self.__check_pool_stock_rack()
        if not self.has_errors(): self.__create_sample_stock_rack()
        if not self.has_errors(): self.__fetch_tube_locations()
        if not self.has_errors(): self.__write_tube_handler_files()
        if not self.has_errors(): self.__write_cybio_overview_file()
        if not self.has_errors():
            self.return_value = self.__file_map
            self.add_info('Worklist file generation completed.')

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')

        if self._check_input_class('pool creation ISO',
                            self.pool_creation_iso, LibraryCreationIso):
            status = self.pool_creation_iso.status
            if not status == ISO_STATUS.QUEUED:
                msg = 'Unexpected ISO status: "%s"' % (status)
                self.add_error(msg)
            self.iso_request_label = self.pool_creation_iso.iso_request.\
                                     plate_set_label
            self.layout_number = self.pool_creation_iso.layout_number

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

    def __set_volumes(self):
        """
        Sets the stock take out volume and the buffer volume. These number are
        derived from the buffer worklist and the library. The buffer volume
        could also be determined from the library data - the below approach
        has been chosen because it comprises some additional checks.
        """
        worklist_series = self.pool_creation_iso.iso_request.worklist_series
        if worklist_series is None:
            msg = 'Unable to find worklist series for ISO request!'
            self.add_error(msg)
        elif not len(worklist_series) == 1:
            msg = 'The worklist series of the ISO request has an unexpected ' \
                  'length (%i, expected: 1).' % (len(worklist_series))
            self.add_error(msg)
        else:
            try:
                buffer_wl = worklist_series.get_worklist_for_index(
                           PoolCreationWorklistGenerator.BUFFER_WORKLIST_INDEX)
            except ValueError as e:
                self.add_error(e)
            else:
                volume = None
                for pcd in buffer_wl.planned_transfers:
                    if volume is None:
                        volume = pcd.volume
                    elif not pcd.volume == volume:
                        msg = 'There are different volumes in the buffer ' \
                              'dilution worklist!'
                        self.add_error(msg)
                        break
                if not self.has_errors() and not volume is None:
                    self.__buffer_volume = volume * VOLUME_CONVERSION_FACTOR

        # TODO: The library could be linked to the ISO
        lib_agg = get_root_aggregate(IMoleculeDesignLibrary)
        lib_name = self.pool_creation_iso.iso_request.plate_set_label
        lib = lib_agg.get_by_slug(as_slug_expression(lib_name))
        if lib is None:
            msg = 'Did not find molecule design library "%s" in the DB. ' \
                  'The name is guessed from the name of the ISO request.' \
                  % (lib_name)
            self.add_error(msg)
        else:
            try:
                self.__stock_take_out_volume = \
                    calculate_single_design_stock_transfer_volume_for_library(
                                                     pool_creation_library=lib)
            except ValueError as e:
                msg = 'Unable to determine stock transfer volume: %s' % (e)
                self.add_error(msg)

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

    def __get_library_layout(self):
        """
        Fetches the library layout and determines empty layout positions
        (ignored positions for worklists).
        """
        self.add_debug('Fetch library layout ...')

        converter = LibraryLayoutConverter(log=self.log,
                            rack_layout=self.pool_creation_iso.rack_layout)
        self.__library_layout = converter.get_result()

        if self.__library_layout is None:
            msg = 'Error when trying to convert library layout.'
            self.add_error(msg)
        else:
            layout_positions = self.__library_layout.get_positions()
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

        #TODO: The number of designs should be stored in the library, too.
        for lib_pos in self.__library_layout.working_positions():
            number_designs = len(lib_pos.stock_tube_barcodes)

        if not len(self.tube_destination_racks) == number_designs:
            msg = 'You need to provide %i empty racks. You have provided ' \
                  '%i barcodes.' % (number_designs,
                                    len(self.tube_destination_racks))
            self.add_error(msg)

        for barcode in self.tube_destination_racks:
            rack = self.__rack_map[barcode]
            if len(rack.containers) > 0: not_empty.append(barcode)

        if len(not_empty) > 0:
            msg = 'The following tube destination racks you have chosen are ' \
                  'not empty: %s.' % (', '.join(sorted(not_empty)))
            self.add_error(msg)

    def __check_pool_stock_rack(self):
        """
        Checks whether the pool stock rack complies with there assumed library
        positions and whether all tubes are empty.
        """
        self.add_debug('Check pool stock racks ...')

        pool_rack = self.__rack_map[self.pool_stock_rack_barcode]
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

    def __create_sample_stock_rack(self):
        """
        Creates the ISO sample stock rack (= the pool stock rack).
        In case of update we have to modify the existing entities.
        """
        self.add_debug('Create pool stock racks ...')

        worklist = self.__create_takeout_worklist()
        issrs = self.pool_creation_iso.iso_sample_stock_racks

        if len(issrs) < 1:
            pool_rack = self.__rack_map[self.pool_stock_rack_barcode]
            IsoSampleStockRack(iso=self.pool_creation_iso,
                               rack=pool_rack, sector_index=0,
                               planned_worklist=worklist)
        elif len(issrs) > 1:
            msg = 'There are too many ISO sample stock racks for this ISOs.' \
                  'Please check and reduce the number to 1 or less.'
            self.add_error(msg)
        else:
            issr = issrs[0]
            issr.worklist = worklist
            issr.rack = pool_rack

    def __create_takeout_worklist(self):
        """
        Creates the container transfer for the stock sample worklist (this
        is in theory a 1-to-1 rack transfer, but since the sources are tubes
        that can be moved we use container transfers instead).
        """
        self.add_debug('Create stock take out worklists ...')

        volume = self.__stock_take_out_volume / VOLUME_CONVERSION_FACTOR

        wl_label = self.SAMPLE_STOCK_WORKLIST_LABEL \
                   + (self.SAMPLE_STOCK_WORKLIST_DELIMITER.join(
                                                self.tube_destination_racks))
        worklist = PlannedWorklist(label=wl_label)
        for rack_pos in self.__library_layout.get_positions():
            pct = PlannedContainerTransfer(volume=volume,
                                           source_position=rack_pos,
                                           target_position=rack_pos)
            worklist.planned_transfers.append(pct)

        return worklist

    def __fetch_tube_locations(self):
        """
        Fetches the rack barcode amd tube location for every scheduled tube.
        """
        self.add_debug('Fetch tube locations ...')

        self.__fetch_tubes()

        if not self.has_errors():
            source_racks = set()
            for tube in self.__tube_map.values():
                source_rack = tube.location.rack
                source_racks.add(source_rack)

            self.__get_rack_locations(source_racks)
            self.__create_tube_transfers()

    def __fetch_tubes(self):
        """
        Fetches tube (for location data), from the the DB. Uses the tube
        barcodes from the library layouts.
        """
        self.add_debug('Fetch tubes ...')

        tube_barcodes = []
        for lib_pos in self.__library_layout.working_positions():
            for barcode in lib_pos.stock_tube_barcodes:
                tube_barcodes.append(barcode)

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

    def __create_tube_transfers(self):
        """
        Assign the tube data items to target positions and create tube
        transfer data items for them.
        """
        self.add_debug('Create tube transfer data ...')

        for rack_pos, lib_pos in self.__library_layout.iterpositions():
            tube_barcodes = lib_pos.stock_tube_barcodes
            for i in range(len(tube_barcodes)):
                tube_barcode = tube_barcodes[i]
                tube = self.__tube_map[tube_barcode]
                tube_rack = tube.location.rack
                target_rack_barcode = self.tube_destination_racks[i]
                ttd = TubeTransferData(tube_barcode=tube_barcode,
                                       src_rack_barcode=tube_rack.barcode,
                                       src_pos=tube.location.position,
                                       trg_rack_barcode=target_rack_barcode,
                                       trg_pos=rack_pos)
                self.__tube_transfers.append(ttd)

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

    def __write_tube_handler_files(self):
        """
        Creates the tube handler worklists and report files for every
        quadrant.
        """
        self.add_debug('Write XL20 files ...')

        worklist_writer = XL20WorklistWriter(log=self.log,
                                             tube_transfers=self.__tube_transfers)
        worklist_stream = worklist_writer.get_result()
        if worklist_stream is None:
            msg = 'Error when trying to write tube handler worklist file.'
            self.add_error(msg)
        else:
            fn = self.FILE_NAME_XL20_WORKLIST % (self.iso_request_label,
                                                 self.layout_number)
            self.__file_map[fn] = worklist_stream

        report_writer = PoolCreationXL20ReportWriter(log=self.log,
                tube_transfers=self.__tube_transfers,
                iso_request_name=self.iso_request_label,
                layout_number=self.layout_number,
                take_out_volume=self.__stock_take_out_volume,
                source_rack_locations=self.__source_rack_locations)
        report_stream = report_writer.get_result()
        if report_stream is None:
            msg = 'Error when trying to write tube handler report.'
            self.add_error(msg)
        else:
            fn = self.FILE_NAME_XL20_REPORT % (self.iso_request_label,
                                               self.layout_number)
            self.__file_map[fn] = report_stream

    def __write_layout_file(self):
        """
        Generates a file that summarizes the ISO layout data in a CSV file.
        """
        writer = PoolCreationIsoLayoutWriter(log=self.log,
                                     pool_creation_layout=self.__library_layout)
        layout_stream = writer.get_result()
        if layout_stream is None:
            msg = 'Error when trying to generate layout data file.'
            self.add_error(msg)
        else:
            fn = self.FILE_NAME_LAYOUT % (self.pool_creation_iso.label)
            self.__file_map[fn] = layout_stream

    def __write_cybio_overview_file(self):
        """
        Generates the file stream with the CyBio instructions. This file is
        not created by a normal series worklist file writer because the tubes
        for the first steck (pool generation) are not in place yet.
        """
        self.add_debug('Generate CyBio info file ...')

        writer = PoolCreationCyBioOverviewWriter(log=self.log,
                        pool_creation_iso=self.pool_creation_iso,
                        pool_stock_rack_barcode=self.pool_stock_rack_barcode,
                        tube_destination_racks=self.tube_destination_racks,
                        take_out_volume=self.__stock_take_out_volume,
                        buffer_volume=self.__buffer_volume)
        stream = writer.get_result()

        if stream is None:
            msg = 'Error when trying to write CyBio info file.'
            self.add_error(msg)
        else:
            fn = self.FILE_NAME_CYBIO % (self.iso_request_label,
                                         self.layout_number)
            self.__file_map[fn] = stream


class PoolCreationXL20ReportWriter(TxtWriter):
    """
    Generates an overview for the tube handling in a pool stock sample
    creation ISO.

    **Return Value:** stream (TXT)
    """
    NAME = 'Pool Creation XL20 Report Writer'

    #: The main headline of the file.
    BASE_MAIN_HEADER = 'XL20 Worklist Generation Report / %s / %s'

    #: The header text for the general section.
    GENERAL_HEADER = 'General Settings'
    #: This line presents the library name.
    LABEL_LINE = 'ISO for Pool Creation ISO request: %s'
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

    def __init__(self, log, tube_transfers, iso_request_name, layout_number,
                 source_rack_locations, take_out_volume):
        """
        Constructor:

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param tube_transfers: Define which tube goes where.
        :type tube_transfers: :class:`TubeTransfer`

        :param iso_request_name: The ISO request we are dealing with.
        :type iso_request_name: :class:`str`

        :param layout_number: the layout for which we are creating racks
        :type layout_number: :class:`int`

        :param source_rack_locations: Maps rack locations onto rack barcodes.
        :type source_rack_locations: :class:`dict`

        :param take_out_volume: The volume to be transferred (for the single
            molecule design samples) in ul.
        :type take_out_volume: positive number
        """
        TxtWriter.__init__(self, log=log)

        #: Define which tube goes where.
        self.tube_transfers = tube_transfers
        #: The ISO request we are dealing with.
        self.iso_request_name = iso_request_name
        #: The layout for which we are creating racks
        self.layout_number = layout_number
        #: Maps rack locations onto rack barcodes.
        self.source_rack_locations = source_rack_locations
        #: The volume to be transferred (for the single molecule design samples)
        #: in ul.
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

        self._check_input_class('ISO request name', self.iso_request_name,
                                basestring)
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
        The general section contains library name, sector index, layout number
        and the number of tubes.
        """
        self._write_headline(self.GENERAL_HEADER, preceding_blank_lines=1)

        general_lines = [self.LABEL_LINE % (self.iso_request_name),
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


class PoolCreationCyBioOverviewWriter(TxtWriter):
    """
    This tools writes an CyBio overview file for the CyBio steps involved in
    the creation of new pool sample stock racks.
    We do not use the normal series worklist writer here, because the stock
    tubes for the single molecule designs are not the right positions yet,
    and thus, the writer would fail.

    **Return Value:** stream (TXT)
    """

    NAME = 'Pool Creation CyBio Writer'

    #: Header for the pool creation section.
    HEADER_POOL_CREATION = 'Pool Creation'

    #: Base line for transfer volumes.
    VOLUME_LINE = 'Volume: %.1f ul'
    #: Base line for buffer volumes.
    BUFFER_LINE = 'Assumed buffer volume: %.1f ul'

    #: Base line for source racks (plural, for pool creation).
    SOURCE_LINE_PLURAL = 'Source racks: %s'
    #: Base line for target racks (singlular)
    TARGET_LINE = 'Target rack: %s'


    def __init__(self, log, pool_creation_iso, pool_stock_rack_barcode,
                 tube_destination_racks, take_out_volume, buffer_volume):
        """
        Constructor:

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param pool_creation_iso: The pool creation ISO for which to
            generate the file.
        :type pool_creation_iso:
            :class:`thelma.models.library.LibraryCreationIso`

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

        #: The pool creation ISO for which to generate the file.
        self.pool_creation_iso = pool_creation_iso
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

        if self._check_input_class('pool creation ISO',
                            self.pool_creation_iso, LibraryCreationIso):
            status = self.pool_creation_iso.status
            if not status == ISO_STATUS.QUEUED:
                msg = 'Unexpected ISO status: "%s"' % (status)
                self.add_error(msg)

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

        lines = []

        volume_line = self.VOLUME_LINE % (self.take_out_volume)
        volume_line += ' each'
        lines.append(volume_line)

        buffer_line = self.BUFFER_LINE % (self.buffer_volume)
        lines.append(buffer_line)

        src_line = self.SOURCE_LINE_PLURAL \
                  % (', '.join(sorted(self.tube_destination_racks)))
        lines.append(src_line)

        trg_line = self.TARGET_LINE % (self.pool_stock_rack_barcode)
        lines.append(trg_line)

        self._write_body_lines(lines)


class PoolCreationIsoLayoutWriter(CsvWriter):
    """
    Generates an overview file containing the layout data for a particular
    library creation ISO.

    **Return Value:** stream (CSV format)
    """
    NAME = 'Pool Creation ISO Layout Writer'

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
        :type pool_creation_layout: :class:`LibraryLayout`

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        CsvWriter.__init__(self, log=log)

        #: The layout of the pool creation ISO.
        self.pool_creation_layout = pool_creation_layout

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
        if self._check_input_class('ISO layout',
                                   self.pool_creation_layout, LibraryLayout):
            self.__store_values()
            self.__generate_columns()

    def __store_values(self):
        """
        Fetches and stores the values for the columns.
        """
        self.add_debug('Store column values ...')

        for lib_pos in self.pool_creation_layout.get_sorted_working_positions():
            self.__position_values.append(lib_pos.rack_position.label)
            self.__pool_values.append(lib_pos.pool.id)
            self.__md_values.append(
                            lib_pos.get_molecule_designs_tag_value())
            self.__tube_values.append(
                            lib_pos.get_stock_barcodes_tag_value())

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