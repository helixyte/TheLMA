#"""
#The classes in this module serve the creation of an ISO for a library creation
#process.
#
#The following tasks need to be performed:
#
# * split library layout into quadrants
# * check current state of the stock racks provided
# * create ISO sample stock rack for each quadrant (barcodes are provided)
# * create worklists for the ISO sample stock racks (sample transfer from
#   single-molecule-design stock rack to pool stock rack) for each quadrant
# * create tube handler worklists
# * create sample transfer robot files
# * upload data to a ticket
#
#AAB
#"""
#from datetime import datetime
#from everest.entities.utils import get_root_aggregate
#from everest.querying.specifications import cntd
#from thelma.automation.tools.base import BaseAutomationTool
#from thelma.automation.tools.libcreation.base \
#    import MOLECULE_DESIGN_TRANSFER_VOLUME
#from thelma.automation.tools.libcreation.base \
#    import get_source_plate_transfer_volume
#from thelma.automation.tools.libcreation.base \
#    import get_stock_pool_buffer_volume
#from thelma.automation.tools.libcreation.base import LibraryLayoutConverter
#from thelma.automation.tools.libcreation.base import NUMBER_MOLECULE_DESIGNS
#from thelma.automation.tools.libcreation.base import NUMBER_SECTORS
#from thelma.automation.tools.libcreation.base import PREPARATION_PLATE_VOLUME
#from thelma.automation.tools.semiconstants import get_positions_for_shape
#from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
#from thelma.automation.tools.utils.racksector import QuadrantIterator
#from thelma.automation.tools.utils.racksector import RackSectorTranslator
#from thelma.automation.tools.worklists.tubehandler import TubeTransferData
#from thelma.automation.tools.worklists.tubehandler import XL20WorklistWriter
#from thelma.automation.tools.writers import LINEBREAK_CHAR
#from thelma.automation.tools.writers import TxtWriter
#from thelma.interfaces import ITube
#from thelma.interfaces import ITubeRack
#from thelma.models.iso import ISO_STATUS
#from thelma.models.iso import IsoSampleStockRack
#from thelma.models.library import LibraryCreationIso
#from thelma.models.liquidtransfer import PlannedContainerTransfer
#from thelma.models.liquidtransfer import PlannedWorklist
#import logging
#
#__docformat__ = 'reStructuredText en'
#
#__all__ = ['LibraryCreationWorklistWriter',
#           'LibraryCreationXL20ReportWriter',
#           'LibraryCreationCyBioOverviewWriter']
#
#
#class LibraryCreationWorklistWriter(BaseAutomationTool):
#    """
#    Writes the worklist files for a library creation ISO. This comprises:
#
#    - 4 tube handler worklists (one for each quadrant)
#    - 4 tube handler reports (one for each quadrant)
#    - overview file
#
#    :Note: The files for the CyBio worklists cannot be generated here, because
#        this requires the stock tubes to be transferred.
#
#    **Return Value:** The worklist files as zip stream (mapped onto file names).
#    """
#
#    NAME = 'Library Creation Worklist Writer'
#
#    #: Label for the worklists of the pool sample stock racks. The label
#    #: will be appended by the source rack barcodes.
#    SAMPLE_STOCK_WORKLIST_LABEL = 'from_'
#    #: The delimiter for the source rack barcodes in the label of the
#    #: stock transfer worklists.
#    SAMPLE_STOCK_WORKLIST_DELIMITER = '-'
#
#    #: File name for a tube handler worklist file. The placeholder contain
#    #: the layout number, the library name and the quadrant number.
#    FILE_NAME_XL20_WORKLIST = '%s-%s_xl20_worklist_Q%i.csv'
#    #: File name for a tube handler worklist file. The placeholder contain
#    #: the layout number, the library name and the quadrant number.
#    FILE_NAME_XL20_REPORT = '%s-%s_xl20_report_Q%i.txt'
#    #: File name for the CyBio instructions info file. The placeholders
#    #: contain the layout number and the the library name.
#    FILE_NAME_CYBIO = '%s-%s-CyBio_instructions.txt'
#
#    def __init__(self, library_creation_iso, tube_destination_racks,
#                 pool_stock_racks):
#        """
#        Constructor:
#
#        :param library_creation_iso: The library creation ISO for which to
#            generate the worklist files.
#        :type library_creation_iso:
#            :class:`thelma.models.library.LibraryCreationIso`
#
#        :param tube_destination_racks: The barcodes for the destination
#            rack for the single molecule design tube (these racks have to be
#            empty).
#        :type tube_destination_racks: map of barcode lists
#            (:class:`basestring`) mapped onto sector indices.
#
#        :param pool_stock_racks: The barcodes for the pool stock racks
#            (these racks have to have empty tubes in defined positions).
#        :type pool_stock_racks: map of barcodes
#            (:class:`basestring`) mapped onto sector indices.
#        """
#        BaseAutomationTool.__init__(self, depending=False)
#
#        #: The library creation ISO for which to generate the worklist files.
#        self.library_creation_iso = library_creation_iso
#        #: The barcodes for the destination rack for the single molecule
#        #: design tube (these racks have to be empty).
#        self.tube_destination_racks = tube_destination_racks
#        #: The barcodes for the pool stock racks rack for the single molecule
#        #: design tube (these racks have to have empty tubes in defined
#        #: positions).
#        self.pool_stock_racks = pool_stock_racks
#
#        #: The name of the library that is created here.
#        self.library_name = None
#        #: The layout number of the ISO.
#        self.layout_number = None
#
#        #: Stores the generated file streams (mapped onto file names).
#        self.__file_map = None
#
#        #: Maps tube racks onto barcodes.
#        self.__rack_map = None
#        #: The library layout for the ISO.
#        self.__library_layout = None
#        #: Maps library position onto sector indices.
#        self.__library_sectors = None
#        #: Maps translated library position onto sector indices.
#        self.__translated_sectors = None
#
#        #: Maps tube onto tube barcodes.
#        self.__tube_map = dict()
#        #: The tube transfer data items for the tube handler worklist writer
#        #: sorted by sector index.
#        self.__tube_transfers = None
#        #: Stores the rack location for each source rack (single molecule
#        #: design pools).
#        self.__source_rack_locations = None
#
#    def reset(self):
#        BaseAutomationTool.reset(self)
#        self.library_name = None
#        self.layout_number = None
#        self.__rack_map = dict()
#        self.__library_layout = None
#        self.__library_sectors = None
#        self.__translated_sectors = dict()
#        self.__tube_map = dict()
#        self.__tube_transfers = dict()
#        self.__file_map = dict()
#        self.__source_rack_locations = dict()
#
#    def run(self):
#        """
#        Creates the worklist files.
#        """
#        self.reset()
#        self.add_info('Start worklist file generation ...')
#        self.__check_input()
#        if not self.has_errors(): self.__get_tube_racks()
#        if not self.has_errors(): self.__get_library_layout()
##        if not self.has_errors(): self.__find_ignored_positions()
#        if not self.has_errors():
#            self.__check_tube_destination_racks()
#            self.__check_pool_stock_racks()
#        if not self.has_errors(): self.__create_sample_stock_racks()
#        if not self.has_errors(): self.__fetch_tube_locations()
#        if not self.has_errors(): self.__write_tube_handler_files()
#        if not self.has_errors(): self.__write_cybio_overview_file()
#        if not self.has_errors():
#            self.return_value = self.__file_map
#            self.add_info('Worklist file generation completed.')
#
#    def __check_input(self):
#        """
#        Checks the initialisation values.
#        """
#        self.add_debug('Check input values ...')
#
#        if self._check_input_class('library creation ISO',
#                            self.library_creation_iso, LibraryCreationIso):
#            status = self.library_creation_iso.status
#            if not status == ISO_STATUS.QUEUED:
#                msg = 'Unexpected ISO status: "%s"' % (status)
#                self.add_error(msg)
#            self.library_name = self.library_creation_iso.iso_request.\
#                                plate_set_label
#            self.layout_number = self.library_creation_iso.layout_number
#
#        if self._check_input_class('tube destination rack map',
#                                   self.tube_destination_racks, dict):
#            for sector_index, barcode_list in \
#                                    self.tube_destination_racks.iteritems():
#                if not self._check_input_class(
#                        'sector index in the tube destination map',
#                         sector_index, int): break
#                if not self._check_input_class(
#                        'barcode list in the tube destination map',
#                        barcode_list, list): break
#            if not len(self.tube_destination_racks) > 0:
#                msg = 'There are no barcodes in the destination rack map!'
#                self.add_error(msg)
#
#        if self._check_input_class('pool stock rack map', self.pool_stock_racks,
#                                   dict):
#            for sector_index, barcode in self.pool_stock_racks.iteritems():
#                if not self._check_input_class(
#                        'sector index in the pool stock rack map',
#                         sector_index, int): break
#                if not self._check_input_class(
#                        'barcode in the pool stock rack map',
#                        barcode, basestring): break
#            if not len(self.pool_stock_racks) > 0:
#                msg = 'There are no barcodes in the pool stock rack map!'
#                self.add_error(msg)
#
#    def __get_tube_racks(self):
#        """
#        Fetches the tubes rack for the rack barcodes.
#        """
#        self.add_debug('Fetch tube racks ...')
#
#        tube_rack_agg = get_root_aggregate(ITubeRack)
#        not_found = []
#
#        for barcode in self.pool_stock_racks.values():
#            rack = tube_rack_agg.get_by_slug(barcode)
#            if rack is None:
#                not_found.append(barcode)
#            else:
#                self.__rack_map[barcode] = rack
#
#        for barcode_list in self.tube_destination_racks.values():
#            for barcode in barcode_list:
#                rack = tube_rack_agg.get_by_slug(barcode)
#                if rack is None:
#                    not_found.append(barcode)
#                else:
#                    self.__rack_map[barcode] = rack
#
#        if len(not_found) > 0:
#            msg = 'The following racks have not been found in the DB: %s!' \
#                  % (', '.join(sorted(not_found)))
#            self.add_error(msg)
#
#    def __get_library_layout(self):
#        """
#        Fetches the library layout and sorts its positions into quadrants.
#        """
#        self.add_debug('Fetch library layout ...')
#
#        converter = LibraryLayoutConverter(log=self.log,
#                            rack_layout=self.library_creation_iso.rack_layout)
#        self.__library_layout = converter.get_result()
#
#        if self.__library_layout is None:
#            msg = 'Error when trying to convert library layout.'
#            self.add_error(msg)
#        else:
#            self.__library_sectors = QuadrantIterator.sort_into_sectors(
#                                    working_layout=self.__library_layout,
#                                    number_sectors=NUMBER_SECTORS)
#            del_sectors = []
#            for sector_index, positions in self.__library_sectors.iteritems():
#                if len(positions) < 1:
#                    del_sectors.append(sector_index)
#                    continue
#                translator = RackSectorTranslator(number_sectors=NUMBER_SECTORS,
#                                source_sector_index=sector_index,
#                                target_sector_index=0,
#                                enforce_type=RackSectorTranslator.ONE_TO_MANY)
#                translated_positions = []
#                for lib_pos in positions:
#                    translated_pos = translator.translate(lib_pos.rack_position)
#                    translated_positions.append(translated_pos)
#                self.__translated_sectors[sector_index] = translated_positions
#            for sector_index in del_sectors:
#                del self.__library_sectors[sector_index]
#
#    def __check_tube_destination_racks(self):
#        """
#        Makes sure there is the right number of tube destination racks for
#        each quadrant and that all racks are empty.
#        """
#        self.add_debug('Check tube destination racks ...')
#
#        not_empty = []
#
#        for sector_index, barcodes in self.tube_destination_racks.iteritems():
#            if not self.__library_sectors.has_key(sector_index): continue
#            if not len(barcodes) >= NUMBER_MOLECULE_DESIGNS:
#                msg = 'You need to provide %i empty racks for each rack ' \
#                      'sector. For sector %i you have only provided ' \
#                      '%i barcodes.' % (NUMBER_MOLECULE_DESIGNS,
#                                        (sector_index + 1), len(barcodes))
#                self.add_error(msg)
#
#            for barcode in barcodes:
#                rack = self.__rack_map[barcode]
#                if len(rack.containers) > 0: not_empty.append(barcode)
#
#        if len(not_empty) > 0:
#            msg = 'The following tube destination racks you have chosen are ' \
#                  'not empty: %s.' % (', '.join(sorted(not_empty)))
#            self.add_error(msg)
#
#    def __check_pool_stock_racks(self):
#        """
#        Checks whether the pool stock comply with there assumed sector layouts
#        and whether all tubes are empty.
#        """
#        self.add_debug('Check pool stock racks ...')
#
#        for sector_index, positions in self.__translated_sectors.iteritems():
#            if not self.pool_stock_racks.has_key(sector_index):
#                msg = 'Please provide a pool stock rack for sector %i!' \
#                      % (sector_index + 1)
#                self.add_error(msg)
#                break
#
#            barcode = self.pool_stock_racks[sector_index]
#            rack = self.__rack_map[barcode]
#            tube_map = dict()
#            for tube in rack.containers: tube_map[tube.location.position] = tube
#
#            tube_missing = []
#            not_empty = []
#            add_tube = []
#
#            for rack_pos in get_positions_for_shape(rack.rack_shape):
#                if rack_pos in positions:
#                    if not tube_map.has_key(rack_pos):
#                        tube_missing.append(rack_pos.label)
#                        continue
#                    tube = tube_map[rack_pos]
#                    if tube.sample is None:
#                        continue
#                    elif tube.sample.volume > 0:
#                        not_empty.append(rack_pos.label)
#                elif tube_map.has_key(rack_pos):
#                    add_tube.append(rack_pos.label)
#
#            if len(tube_missing) > 0:
#                msg = 'There are some tubes missing in the pool stock rack ' \
#                      'for sector %i (%s): %s.' % ((sector_index + 1),
#                       barcode, ', '.join(sorted(tube_missing)))
#                self.add_error(msg)
#            if len(not_empty) > 0:
#                msg = 'Some tubes in the pool stock rack for sector %i (%s) ' \
#                      'are not empty: %s.' % ((sector_index + 1), barcode,
#                                              ', '.join(sorted(not_empty)))
#                self.add_error(msg)
#            if len(add_tube) > 0:
#                msg = 'There are some tubes in the stock rack for sector %i ' \
#                      '(%s) that are located in positions that should be ' \
#                      'empty: %s.' % ((sector_index + 1), barcode,
#                                      ', '.join(sorted(add_tube)))
#                self.add_warning(msg)
#
#    def __create_sample_stock_racks(self):
#        """
#        Creates the ISO sample stock rack (= the pool stock racks) for the
#        library. The stock rack list of the ISO has to be reset before
#        (in case of update).
#        """
#        self.add_debug('Create pool stock racks ...')
#
#        worklists = self.__create_takeout_worklists()
#        issrs = self.library_creation_iso.iso_sample_stock_racks
#
#        if len(issrs) < 1:
#            for sector_index, barcode in self.pool_stock_racks.iteritems():
#                if not worklists.has_key(sector_index): continue
#                rack = self.__rack_map[barcode]
#                worklist = worklists[sector_index]
#                IsoSampleStockRack(iso=self.library_creation_iso,
#                                   rack=rack, sector_index=sector_index,
#                                   planned_worklist=worklist)
#        else:
#            for issr in issrs:
#                issr.worklist = worklists[issr.sector_index]
#                barcode = self.pool_stock_racks[issr.sector_index]
#                issr.rack = self.__rack_map[barcode]
#
#    def __create_takeout_worklists(self):
#        """
#        Creates the container transfer for the stock sample worklists (this
#        is in theory a 1-to-1 rack transfer, but since the sources are tubes
#        that can be moved we use container transfers instead).
#        """
#        self.add_debug('Create stock take out worklists ...')
#
#        worklists = dict()
#
#        volume = MOLECULE_DESIGN_TRANSFER_VOLUME / VOLUME_CONVERSION_FACTOR
#
#        for sector_index in self.pool_stock_racks.keys():
#            if not self.__translated_sectors.has_key(sector_index): continue
#            positions = self.__translated_sectors[sector_index]
#            dest_rack_barcodes = self.tube_destination_racks[sector_index]
#            label = self.SAMPLE_STOCK_WORKLIST_LABEL \
#                    + (self.SAMPLE_STOCK_WORKLIST_DELIMITER.join(
#                                                            dest_rack_barcodes))
#            worklist = PlannedWorklist(label=label)
#            for rack_pos in positions:
#                pct = PlannedContainerTransfer(volume=volume,
#                            source_position=rack_pos,
#                            target_position=rack_pos)
#                worklist.planned_transfers.append(pct)
#
#            worklists[sector_index] = worklist
#
#        return worklists
#
#    def __fetch_tube_locations(self):
#        """
#        Fetches the rack barcode amd tube location for every scheduled tube.
#        """
#        self.add_debug('Fetch tube locations ...')
#
#        self.__fetch_tubes()
#
#        if not self.has_errors():
#            source_racks = set()
#            for tube in self.__tube_map.values():
#                source_rack = tube.location.rack
#                source_racks.add(source_rack)
#
#            self.__get_rack_locations(source_racks)
#            self.__create_tube_transfers()
#
#    def __fetch_tubes(self):
#        """
#        Fetches tube (for location data), from the the DB. Uses the tube
#        barcodes from the library layouts.
#        """
#        self.add_debug('Fetch tubes ...')
#
#        tube_barcodes = []
#        for lib_pos in self.__library_layout.working_positions():
#            for barcode in lib_pos.stock_tube_barcodes:
#                tube_barcodes.append(barcode)
#
#        tube_agg = get_root_aggregate(ITube)
#        tube_agg.filter = cntd(barcode=tube_barcodes)
#        iterator = tube_agg.iterator()
#        while True:
#            try:
#                tube = iterator.next()
#            except StopIteration:
#                break
#            else:
#                self.__tube_map[tube.barcode] = tube
#
#        if not len(tube_barcodes) == len(self.__tube_map):
#            missing_tubes = []
#            for tube_barcode in tube_barcodes:
#                if not self.__tube_map.has_key(tube_barcode):
#                    missing_tubes.append(tube_barcode)
#            msg = 'Could not find tubes for the following tube barcodes: %s.' \
#                  % (', '.join(sorted(missing_tubes)))
#            self.add_error(msg)
#
#    def __create_tube_transfers(self):
#        """
#        Assign the tube data items to target positions and create tube
#        transfer data items for them.
#        """
#        self.add_debug('Create tube transfer data ...')
#
#        for sector_index, positions in self.__library_sectors.iteritems():
#
#            translator = RackSectorTranslator(number_sectors=NUMBER_SECTORS,
#                        source_sector_index=sector_index,
#                        target_sector_index=0,
#                        enforce_type=RackSectorTranslator.ONE_TO_MANY)
#            rack_barcodes = self.tube_destination_racks[sector_index]
#            tube_transfers = []
#
#            for lib_pos in positions:
#                target_pos_384 = lib_pos.rack_position
#                target_pos_96 = translator.translate(target_pos_384)
#                for i in range(NUMBER_MOLECULE_DESIGNS):
#                    tube_barcode = lib_pos.stock_tube_barcodes[i]
#                    tube = self.__tube_map[tube_barcode]
#                    tube_pos = tube.location.position
#                    tube_rack = tube.location.rack
#                    target_rack_barcode = rack_barcodes[i]
#                    ttd = TubeTransferData(tube_barcode=tube_barcode,
#                                    src_rack_barcode=tube_rack.barcode,
#                                    src_pos=tube_pos,
#                                    trg_rack_barcode=target_rack_barcode,
#                                    trg_pos=target_pos_96)
#                    tube_transfers.append(ttd)
#
#            self.__tube_transfers[sector_index] = tube_transfers
#
#    def __get_rack_locations(self, source_racks):
#        """
#        Returns a map that stores the rack location for each source rack
#        (DB query).
#        """
#        self.add_debug('Fetch rack locations ...')
#
#        for src_rack in source_racks:
#            barcode = src_rack.barcode
#            loc = src_rack.location
#            if loc is None:
#                self.__source_rack_locations[barcode] = 'not found'
#                continue
#            name = loc.name
#            index = loc.index
#            if index is None or len(index) < 1:
#                self.__source_rack_locations[barcode] = name
#            else:
#                self.__source_rack_locations[barcode] = '%s, index: %s' \
#                                                         % (name, index)
#
#    def __write_tube_handler_files(self):
#        """
#        Creates the tube handler worklists and report files for every
#        quadrant.
#        """
#        self.add_debug('Write XL20 files ...')
#
#        for sector_index, tube_transfers in self.__tube_transfers.iteritems():
#
#            worklist_writer = XL20WorklistWriter(log=self.log,
#                                                 tube_transfers=tube_transfers)
#            worklist_stream = worklist_writer.get_result()
#            if worklist_stream is None:
#                msg = 'Error when trying to write tube handler worklist ' \
#                      'file for sector %i.' % (sector_index + 1)
#                self.add_error(msg)
#            else:
#                fn = self.FILE_NAME_XL20_WORKLIST % (self.library_name,
#                                        self.layout_number, (sector_index + 1))
#                self.__file_map[fn] = worklist_stream
#
#            report_writer = LibraryCreationXL20ReportWriter(log=self.log,
#                    tube_transfers=tube_transfers,
#                    library_name=self.library_name,
#                    layout_number=self.layout_number,
#                    sector_index=sector_index,
#                    source_rack_locations=self.__source_rack_locations)
#            report_stream = report_writer.get_result()
#            if report_stream is None:
#                msg = 'Error when trying to write tube handler report for ' \
#                      'sector %i.' % (sector_index + 1)
#                self.add_error(msg)
#            else:
#                fn = self.FILE_NAME_XL20_REPORT % (self.library_name,
#                                        self.layout_number, (sector_index + 1))
#                self.__file_map[fn] = report_stream
#
#    def __write_cybio_overview_file(self):
#        """
#        Generates the file stream with the CyBio instructions. This file is
#        not created by a normal series worklist file writer because the tubes
#        for the first steck (pool generation) are not in place yet.
#        """
#        self.add_debug('Generate CyBio info file ...')
#
#        writer = LibraryCreationCyBioOverviewWriter(log=self.log,
#                        library_creation_iso=self.library_creation_iso,
#                        pool_stock_racks=self.pool_stock_racks,
#                        tube_destination_racks=self.tube_destination_racks)
#        stream = writer.get_result()
#
#        if stream is None:
#            msg = 'Error when trying to write CyBio info file.'
#            self.add_error(msg)
#        else:
#            fn = self.FILE_NAME_CYBIO % (self.library_name, self.layout_number)
#            self.__file_map[fn] = stream
#
#
#class LibraryCreationXL20ReportWriter(TxtWriter):
#    """
#    Generates an overview for the tube handling of a particular quadrant
#    in a library creation ISO.
#
#    **Return Value:** stream (TXT)
#    """
#    NAME = 'Library Creation XL20 Report Writer'
#
#    #: The main headline of the file.
#    BASE_MAIN_HEADER = 'XL20 Worklist Generation Report / %s / %s'
#
#    #: The header text for the general section.
#    GENERAL_HEADER = 'General Settings'
#    #: This line presents the library name.
#    LIBRARY_LINE = 'ISO for Library: %s'
#    #: This line presents the layout number.
#    LAYOUT_NUMBER_LINE = 'Layout number: %i'
#    #: This line presents the quadrant number.
#    SECTOR_NUMBER_LINE = 'Sector number: %i'
#    #: This line presents the total number of stock tubes used.
#    TUBE_NO_LINE = 'Total number of tubes: %i'
#    #: This line presents the transfer volume.
#    VOLUME_LINE = 'Volume: %.1f ul'
#
#    #: The header text for the destination racks section.
#    DESTINATION_RACKS_HEADER = 'Destination Racks'
#    #: The body for the destination racks section.
#    DESTINATION_RACK_BASE_LINE = '%s'
#
#    #: The header for the source racks section.
#    SOURCE_RACKS_HEADER = 'Source Racks'
#    #: The body for the source racks section.
#    SOURCE_RACKS_BASE_LINE = '%s (%s)'
#
#    def __init__(self, log, tube_transfers, library_name, layout_number,
#                 sector_index, source_rack_locations):
#        """
#        Constructor:
#
#        :param log: The log to write into.
#        :type log: :class:`thelma.ThelmaLog`
#
#        :param tube_transfers: Define which tube goes where.
#        :type tube_transfers: :class:`TubeTransfer`
#
#        :param library_name: The library we are creating.
#        :type library_name: :class:`str`
#
#        :param layout_number: the layout for which we are creating racks
#        :type layout_number: :class:`int`
#
#        :param sector_index: The sector we are dealing with.
#        :type sector_index: :class:`int`
#
#        :param source_rack_locations: Maps rack locations onto rack barcodes.
#        :type source_rack_locations: :class:`dict`
#        """
#        TxtWriter.__init__(self, log=log)
#
#        #: Define which tube goes where.
#        self.tube_transfers = tube_transfers
#        #: The library we are creating.
#        self.library_name = library_name
#        #: The layout for which we are creating racks
#        self.layout_number = layout_number
#        #: The sector we are dealing with.
#        self.sector_index = sector_index
#        #: Maps rack locations onto rack barcodes.
#        self.source_rack_locations = source_rack_locations
#
#    def _check_input(self):
#        """
#        Checks if the tools has obtained correct input values.
#        """
#        if self._check_input_class('tube transfer list', self.tube_transfers,
#                                   list):
#            for ttd in self.tube_transfers:
#                if not self._check_input_class('tube transfer', ttd,
#                                               TubeTransferData): break
#
#        self._check_input_class('library name', self.library_name, basestring)
#        self._check_input_class('layout number', self.layout_number, int)
#        self._check_input_class('sector index', self.sector_index, int)
#
#        self._check_input_class('rack location map',
#                                self.source_rack_locations, dict)
#
#    def _write_stream_content(self):
#        """
#        Writes into the streams.
#        """
#        self.add_debug('Write stream ...')
#
#        self.__write_main_headline()
#        self.__write_general_section()
#        self.__write_destination_racks_section()
#        self.__write_source_racks_section()
#
#    def __write_main_headline(self):
#        """
#        Writes the main head line.
#        """
#        now = datetime.now()
#        date_string = now.strftime('%d.%m.%Y')
#        time_string = now.strftime('%H:%M')
#        main_headline = self.BASE_MAIN_HEADER % (date_string, time_string)
#        self._write_headline(main_headline, underline_char='=',
#                             preceding_blank_lines=0, trailing_blank_lines=1)
#
#    def __write_general_section(self):
#        """
#        The general section contains library name, sector index, layout number
#        and the number of tubes.
#        """
#        self._write_headline(self.GENERAL_HEADER, preceding_blank_lines=1)
#
#        general_lines = [self.LIBRARY_LINE % (self.library_name),
#                         self.LAYOUT_NUMBER_LINE % (self.layout_number),
#                         self.SECTOR_NUMBER_LINE % (self.sector_index + 1),
#                         self.TUBE_NO_LINE % (len(self.tube_transfers)),
#                         self.VOLUME_LINE % (MOLECULE_DESIGN_TRANSFER_VOLUME)]
#        self._write_body_lines(general_lines)
#
#    def __write_destination_racks_section(self):
#        """
#        Writes the destination rack section.
#        """
#        barcodes = set()
#        for ttd in self.tube_transfers:
#            barcodes.add(ttd.trg_rack_barcode)
#
#        self._write_headline(self.DESTINATION_RACKS_HEADER)
#        lines = []
#        for barcode in barcodes:
#            lines.append(self.DESTINATION_RACK_BASE_LINE % (barcode))
#        self._write_body_lines(lines)
#
#    def __write_source_racks_section(self):
#        """
#        Writes the source rack section.
#        """
#        barcodes = set()
#        for ttd in self.tube_transfers:
#            barcodes.add(ttd.src_rack_barcode)
#        sorted_barcodes = sorted(list(barcodes))
#
#        self._write_headline(self.SOURCE_RACKS_HEADER)
#        lines = []
#        for barcode in sorted_barcodes:
#            loc = self.source_rack_locations[barcode]
#            if loc is None: loc = 'unknown location'
#            lines.append(self.SOURCE_RACKS_BASE_LINE % (barcode, loc))
#        self._write_body_lines(lines)
#
#
#class LibraryCreationCyBioOverviewWriter(TxtWriter):
#    """
#    This tools writes an CyBio overview file for the CyBio steps involved in
#    the creation of library plates. We do not use the normal series worklist
#    writer here, because the stock tubes for the single molecule designs
#    are not the right positions yet, and thus, the writer would fail.
#
#    **Return Value:** stream (TXT)
#    """
#
#    NAME = 'Library Creation CyBio Writer'
#
#    #: Header for the pool creation section.
#    HEADER_POOL_CREATION = 'Pool Creation'
#    #: Header for the preparation plate transfer section.
#    HEADER_SOURCE_CREATION = 'Transfer from Stock Rack to Preparation Plates'
#    #: Header for the aliquot transfer section.
#    HEADER_ALIQUOT_TRANSFER = 'Transfer to Library Aliquot Plates'
#
#    #: Base line for transfer volumes.
#    VOLUME_LINE = 'Volume: %.1f ul'
#    #: Base line for buffer volumes.
#    BUFFER_LINE = 'Assumed buffer volume: %.1f ul'
#
#    #: Base line for source racks (singular, for prep plate creation)
#    SOURCE_LINE = 'Source rack: %s'
#    #: Base line for source racks (plural, for pool creation).
#    SOURCE_LINE_PLURAL = 'Source racks: %s'
#    #: Base line for target racks (singlular)
#    TARGET_LINE = 'Target rack: %s'
#    #: Base line for target racks (plural, for aliquot section).
#    TARGET_LINE_PLURAL = 'Target racks: %s'
#    #: Base line for quadrant depcitions.
#    QUADRANT_LINE = 'Q%i:'
#
#
#    def __init__(self, log, library_creation_iso, pool_stock_racks,
#                 tube_destination_racks):
#        """
#        Constructor:
#
#        :param log: The log to write into.
#        :type log: :class:`thelma.ThelmaLog`
#
#        :param library_creation_iso: The library creation ISO for which to
#            generate the file.
#        :type library_creation_iso:
#            :class:`thelma.models.library.LibraryCreationIso`
#
#        :param tube_destination_racks: The barcodes for the destination
#            rack for the single molecule design tube (these racks have to be
#            empty).
#        :type tube_destination_racks: map of barcode lists
#            (:class:`basestring`) mapped onto sector indices.
#
#        :param pool_stock_racks: The barcodes for the pool stock racks
#            (these racks have to have empty tubes in defined positions).
#        :type pool_stock_racks: map of barcodes
#            (:class:`basestring`) mapped onto sector indices.
#        """
#        TxtWriter.__init__(self, log=log)
#
#        #: The library creation ISO for which to generate the file.
#        self.library_creation_iso = library_creation_iso
#        #: The barcodes for the destination, rack for the single molecule
#        #: design tubes.
#        self.tube_destination_racks = tube_destination_racks
#        #: The barcodes for the pool stock racks.
#        self.pool_stock_racks = pool_stock_racks
#
#        #: The library source (preparation) plates mapped onto
#        #: rack sectors.
#        self.__source_plates = None
#
#    def reset(self):
#        TxtWriter.reset(self)
#        self.__source_plates = dict()
#
#    def _check_input(self):
#        self.add_debug('Check input values ...')
#
#        if self._check_input_class('library creation ISO',
#                            self.library_creation_iso, LibraryCreationIso):
#            status = self.library_creation_iso.status
#            if not status == ISO_STATUS.QUEUED:
#                msg = 'Unexpected ISO status: "%s"' % (status)
#                self.add_error(msg)
#
#        if self._check_input_class('tube destination rack map',
#                                   self.tube_destination_racks, dict):
#            for sector_index, barcode_list in \
#                                    self.tube_destination_racks.iteritems():
#                if not self._check_input_class(
#                        'sector index in the tube destination map',
#                         sector_index, int): break
#                if not self._check_input_class(
#                        'barcode list in the tube destination map',
#                        barcode_list, list): break
#            if not len(self.tube_destination_racks) > 0:
#                msg = 'There are no barcodes in the destination rack map!'
#                self.add_error(msg)
#
#        if self._check_input_class('pool stock rack map', self.pool_stock_racks,
#                                   dict):
#            for sector_index, barcode in self.pool_stock_racks.iteritems():
#                if not self._check_input_class(
#                        'sector index in the pool stock rack map',
#                         sector_index, int): break
#                if not self._check_input_class(
#                        'barcode in the pool stock rack map',
#                        barcode, basestring): break
#            if not len(self.pool_stock_racks) > 0:
#                msg = 'There are no barcodes in the pool stock rack map!'
#                self.add_error(msg)
#
#    def _write_stream_content(self):
#        """
#        Writes into the streams.
#        """
#        self.add_debug('Write stream ...')
#
#        self.__write_pool_creation_section()
#        self.__get_source_plates()
#        self.__write_prep_creation_section()
#        self.__write_aliquot_part()
#
#    def __write_pool_creation_section(self):
#        """
#        This is the stock transfer part (creating pools from single molecule
#        designs).
#        """
#        self.add_debug('Create pool section ...')
#
#        self._write_headline(header_text=self.HEADER_POOL_CREATION,
#                             preceding_blank_lines=0)
#
#        lines = []
#
#        volume_line = self.VOLUME_LINE % (MOLECULE_DESIGN_TRANSFER_VOLUME)
#        volume_line += ' each'
#        lines.append(volume_line)
#
#        buffer_line = self.BUFFER_LINE % get_stock_pool_buffer_volume()
#        lines.append(buffer_line)
#
#        for sector_index in sorted(self.tube_destination_racks.keys()):
#            lines.append('')
#            lines.append(self.QUADRANT_LINE % (sector_index + 1))
#            barcodes = self.tube_destination_racks[sector_index]
#            target_rack = self.pool_stock_racks[sector_index]
#            src_line = self.SOURCE_LINE_PLURAL % (', '.join(sorted(barcodes)))
#            lines.append(src_line)
#            lines.append(self.TARGET_LINE % (target_rack))
#
#        self._write_body_lines(lines)
#
#    def __get_source_plates(self):
#        """
#        Maps library source (preparation) plate barcodes onto sector indices.
#        """
#        for lsp in self.library_creation_iso.library_source_plates:
#            self.__source_plates[lsp.sector_index] = lsp.plate
#
#    def __write_prep_creation_section(self):
#        """
#        This part deals with the transfer from pool stock racks to preparation
#        (source) plates.
#        """
#        self.add_debug('Create source plate section ...')
#
#        self._write_headline(header_text=self.HEADER_SOURCE_CREATION)
#
#        lines = []
#
#        transfer_volume = get_source_plate_transfer_volume()
#        volume_line = self.VOLUME_LINE % (transfer_volume)
#        lines.append(volume_line)
#
#        buffer_volume = PREPARATION_PLATE_VOLUME - transfer_volume
#        buffer_line = self.BUFFER_LINE % buffer_volume
#        lines.append(buffer_line)
#
#        for sector_index in sorted(self.pool_stock_racks.keys()):
#            lines.append('')
#            lines.append(self.QUADRANT_LINE % (sector_index + 1))
#            pool_barcode = self.pool_stock_racks[sector_index]
#            src_plate = self.__source_plates[sector_index]
#            src_term = '%s (%s)' % (src_plate.barcode, src_plate.label)
#            lines.append(self.SOURCE_LINE % (pool_barcode))
#            lines.append(self.TARGET_LINE % (src_term))
#
#        self._write_body_lines(lines)
#
#    def __write_aliquot_part(self):
#        """
#        This part deals with the transfer from pool stock racks to preparation
#        (source) plates.
#        """
#        self.add_debug('Write aliquot transfer section ...')
#
#        self._write_headline(self.HEADER_ALIQUOT_TRANSFER)
#
#        lines = []
#        lines.append(self.SOURCE_LINE_PLURAL % '')
#        for sector_index in sorted(self.__source_plates.keys()):
#            line = self.QUADRANT_LINE % ((sector_index + 1))
#            src_plate = self.__source_plates[sector_index]
#            src_term = ' %s (%s)' % (src_plate.barcode, src_plate.label)
#            line += '%s' % (src_term)
#            lines.append(line)
#
#        aliquot_plates = dict()
#        for iap in self.library_creation_iso.iso_aliquot_plates:
#            plate = iap.plate
#            aliquot_plates[plate.label] = plate.barcode
#
#        lines.append(LINEBREAK_CHAR)
#        lines.append(self.TARGET_LINE_PLURAL % '')
#        for label in sorted(aliquot_plates.keys()):
#            barcode = aliquot_plates[label]
#            trg_term = '%s (%s)' % (barcode, label)
#            lines.append(trg_term)
#
#        self._write_body_lines(lines)
