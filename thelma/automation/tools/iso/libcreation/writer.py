"""
Worklist writer for library creation ISOs.
"""
from datetime import datetime
from operator import add

from everest.entities.utils import get_root_aggregate
from everest.querying.specifications import cntd
from thelma.automation.semiconstants import get_pipetting_specs_cybio
from thelma.automation.tools.base import BaseTool
from thelma.automation.tools.dummies import XL20Dummy
from thelma.automation.tools.iso.libcreation.base import LABELS
from thelma.automation.tools.iso.libcreation.base import \
    DEFAULT_POOL_STOCK_RACK_CONCENTRATION
from thelma.automation.tools.iso.libcreation.base import \
    LibraryLayoutConverter
from thelma.automation.tools.iso.libcreation.base import \
    get_pool_buffer_volume
from thelma.automation.tools.iso.libcreation.base import \
    get_pool_transfer_volume
from thelma.automation.tools.iso.libcreation.base import \
    get_preparation_plate_transfer_volume
from thelma.automation.tools.worklists.tubehandler import TubeTransferData
from thelma.automation.tools.worklists.tubehandler import XL20WorklistWriter
from thelma.automation.tools.writers import LINEBREAK_CHAR
from thelma.automation.tools.writers import TxtWriter
from thelma.automation.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.utils.racksector import RackSectorTranslator
from thelma.interfaces import ITube
from thelma.interfaces import ITubeRack
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import IsoSectorStockRack
from thelma.models.iso import StockSampleCreationIso
from thelma.models.liquidtransfer import PlannedRackSampleTransfer
from thelma.models.liquidtransfer import PlannedSampleTransfer
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.liquidtransfer import WorklistSeries


__docformat__ = 'reStructuredText en'
__all__ = ['LibraryCreationIsoWorklistWriter',
           ]


class LibraryCreationIsoWorklistWriter(BaseTool):
    """
    Writes the worklist files and creates or updates all stock racks
    for a library creation ISO.
    """
    NAME = 'Library Creation Worklist Writer'
    #: File name for the tube handler worklist file. The placeholder contain
    #: the layout number, the library name and the quadrant number.
    FILE_NAME_XL20_WORKLIST = '%s-%s_xl20_worklist_Q%s.csv'
    #: File name for the tube handler dummy output file. Placeholders like
    #: for the XL20 worklist file name.
    FILE_NAME_XL20_DUMMY_OUTPUT = '%s-%s_xl20_dummy_output_Q%s.tpo'
    #: File name for a tube handler worklist file. The placeholder contain
    #: the layout number, the library name and the quadrant number.
    FILE_NAME_XL20_REPORT = '%s-%s_xl20_report_Q%s.txt'
    #: File name for the CyBio instructions info file. The placeholders
    #: contain the layout number and the the library name.
    FILE_NAME_CYBIO = '%s-%s-CyBio_instructions.txt'

    def __init__(self, iso, single_stock_racks, pool_stock_racks=None,
                 include_dummy_output=False, parent=None):
        """
        Constructor.

        :param list single_stock_racks: Barcodes for single stock racks (must
            be empty).
        :param list pool_stock_racks: Optional pool stock rack barcodes.
            Each pool stock rack is expected to contain empty tubes in the
            expected positions.
        :param bool include_dummy_output: Flag indicating if the writer should
            return a dummy output file for the tube transfers.
        """
        BaseTool.__init__(self, parent=parent)
        self.iso = iso
        self.single_stock_racks = single_stock_racks
        self.pool_stock_racks = pool_stock_racks
        self.include_dummy_output = include_dummy_output
        #: Pool stock rack buffer volume in ul.
        self.__pool_stock_rack_buffer_volume = None
        #: Map tube rack barcode -> tube rack.
        self.__tube_rack_map = None
        #: Map sector index -> single stock rack barcodes.
        self.__single_stock_rack_map = None
        #: Map sector index -> pool stock rack barcode.
        self.__pool_stock_rack_map = None
        #: Map rack barcode -> location string.
        self.__source_rack_locations = None

    def reset(self):
        BaseTool.reset(self)
        self.__pool_stock_rack_buffer_volume = None
        self.__tube_rack_map = {}
        self.__source_rack_locations = {}
        self.__single_stock_rack_map = {}
        self.__pool_stock_rack_map = None

    def run(self):
        self.reset()
        self.__check_input()
        if not self.has_errors():
            self.__tube_rack_map = self.__get_tube_racks()
        if not self.has_errors():
            self.__single_stock_rack_map = self.__check_single_stock_racks()
        if not self.has_errors() and not self.pool_stock_racks is None:
            self.__pool_stock_rack_map = self.__check_pool_stock_racks()
        if not self.has_errors():
            stock_tube_transfer_map = self.__process_transfers()
        if not self.has_errors():
            file_map = {}
            self.__build_tube_handler_files(stock_tube_transfer_map,
                                            file_map)
        if not self.has_errors():
            self.__build_cybio_overview_file(file_map)
        if not self.has_errors():
            self.return_value = file_map
            self.add_info('Worklist file generation completed.')

    def __check_input(self):
        self.add_debug('Checking parameters.')
        try:
            assert isinstance(self.iso, StockSampleCreationIso) \
                   , 'Invalid ISO.'
            assert isinstance(self.single_stock_racks, list) \
                   , 'Invalid single stock rack list.'
            assert len([type(val) for val in self.single_stock_racks
                        if not type(val) in (str, unicode)]) \
                    == 0, 'Invalid single stock rack list values.'
            assert len(self.single_stock_racks) \
                    % self.iso.iso_request.number_designs == 0 \
                    , 'The number of single stock rack barcodes must be a ' \
                      'multiple of the number of designs per pool.'
            assert len(self.single_stock_racks) > 0 \
                   , 'Missing single stock rack rack barcodes.'
            if not self.pool_stock_racks is None:
                assert isinstance(self.pool_stock_racks, list) \
                       , 'Invalid pool stock rack list.'
                assert len([type(val) for val in self.pool_stock_racks
                            if not type(val) in (str, unicode)]) \
                        == 0, 'Invalid pool stock rack list values.'
                assert len(self.pool_stock_racks) > 0 \
                       , 'Missing pool stock rack barcodes.'
        except AssertionError, err:
            self.add_error(str(err))

    def __get_tube_racks(self):
        self.add_debug('Fetching tube racks.')
        tube_rack_agg = get_root_aggregate(ITubeRack)
        query_bcs = self.single_stock_racks
        if not self.pool_stock_racks is None:
            query_bcs.extend(self.pool_stock_racks)
        tube_rack_agg.filter = cntd(barcode=query_bcs)
        rack_map = dict([(tr.barcode, tr) for tr in tube_rack_agg])
        bcs_not_found = set(rack_map.keys()).symmetric_difference(query_bcs)
        if len(bcs_not_found) > 0:
            msg = 'The following racks have not been found in the DB: %s!' \
                  % (', '.join(sorted(bcs_not_found)))
            self.add_error(msg)
        return rack_map

    def __check_single_stock_racks(self):
        # Makes sure there is the right number of tube destination racks for
        # each quadrant and that all racks are empty. Also, builds a map
        # sector index -> single stock rack barcodes.
        self.add_debug('Checking single stock racks.')
        racks_with_tubes = []
        n_designs = self.iso.iso_request.number_designs
        single_stock_rack_map = {}
        for sec_idx in range(len(self.single_stock_racks) / n_designs):
            sec_bcs = \
                self.single_stock_racks[sec_idx * n_designs :
                                        sec_idx * n_designs + n_designs]
            racks_with_tubes.extend([r for r in [self.__tube_rack_map[bc]
                                                 for bc in sec_bcs]
                                     if len(r.containers) > 0])
            single_stock_rack_map[sec_idx] = sec_bcs
        if len(racks_with_tubes) > 0:
            msg = 'The following tube destination racks you have chosen are ' \
                  'not empty: %s.' % \
                  (', '.join(sorted([r.barcode for r in racks_with_tubes])))
            self.add_error(msg)
        return single_stock_rack_map

    def __check_pool_stock_racks(self):
        # Ensures that the new pool tube racks have tubes in the expected
        # positions using the layout of the sector preparation plates. Also
        # builds a map sector index -> pool stock rack barcode.
        self.add_debug('Checking new pool tube racks.')
        pool_stock_rack_map = {}
        for ispp in self.iso.iso_sector_preparation_plates:
            trl = RackSectorTranslator(4, ispp.sector_index, 0,
                                       behaviour=
                                            RackSectorTranslator.MANY_TO_ONE)
            exp_poss = ispp.rack_layout.get_positions()
            pool_stock_rack_bc = self.pool_stock_racks[ispp.sector_index]
            pool_stock_rack_map[ispp.sector_index] = pool_stock_rack_bc
            new_tube_rack = self.__tube_rack_map[pool_stock_rack_bc]
            tube_map = dict([(trl.translate(t.location.position), t)
                             for t in new_tube_rack.containers])
            missing_poss = set(exp_poss).difference(tube_map.keys())
            if len(missing_poss) > 0:
                msg = 'There are some tubes missing in the new stock rack ' \
                      'for sector %i (%s): %s.' \
                      % (ispp.sector_index, new_tube_rack.barcode,
                         ', '.join(sorted([p.label for p in missing_poss])))
                self.add_error(msg)
            extra_poss = set(tube_map.keys()).difference(exp_poss)
            if len(extra_poss) > 0:
                msg = 'There are some empty tubes in the new stock rack ' \
                      'for sector %i in positions which should be empty: ' \
                      ' %s. ' \
                      % (ispp.sector_index,
                         ', '.join(sorted([p.label for p in extra_poss])))
                self.add_warning(msg)
            not_empty = [t.location.position
                         for t in tube_map.values()
                         if not t.sample is None and t.sample.volume > 0]
            if len(not_empty) > 0:
                msg = 'Some tubes in the new stock rack for sector %i are ' \
                      'not empty: %s.' \
                      % (ispp.sector_index,
                         ', '.join([p.label for p in not_empty]))
                self.add_error(msg)
        return pool_stock_rack_map

    def __process_transfers(self):
        # Stock racks are processed per quadrant as follows:
        #   a) Create a working layout from the prep plate layout;
        #   b) Process the single design stock racks (one per design).
        #   c) Process the pool stock rack (if necessary);
        # Map sector index -> tube transfers.
        stock_tube_transfer_map = {}
        for ispp in self.iso.iso_sector_preparation_plates:
            # The sector prep plate's layout contains the library positions
            # and tube information.
            converter = LibraryLayoutConverter(ispp.rack_layout, parent=self)
            sec_layout = converter.get_result()
            stts = self.__process_single_design_transfers(ispp.sector_index,
                                                          sec_layout)
            stock_tube_transfer_map[ispp.sector_index] = stts
            if not self.pool_stock_racks is None:
                self.__process_pool_transfers(ispp.sector_index, sec_layout)
        return stock_tube_transfer_map

    def __process_single_design_transfers(self, sector_index, sector_layout):
        stock_transfer_volume = self.iso.iso_request.stock_volume
        wl_label = LABELS.create_sector_stock_transfer_worklist_label(
                                            self.iso.label,
                                            LABELS.ROLE_SINGLE_DESIGN_STOCK,
                                            sector_index)
        wl_series = self.__make_stock_rack_worklist_series(
                                                    wl_label,
                                                    stock_transfer_volume,
                                                    sector_layout)
        tube_map = self.__get_tube_map_for_sector(sector_layout)
        sector_tube_transfers = []
        sdssr_barcodes = self.__single_stock_rack_map[sector_index]
        for design_number, sdssr_barcode in enumerate(sdssr_barcodes):
            tube_transfers = self.__build_tube_transfers(
                                                    design_number,
                                                    sdssr_barcode,
                                                    sector_layout,
                                                    tube_map)
            sector_tube_transfers.extend(tube_transfers)
            if len(sdssr_barcodes) == 1:
                # Setting the design number to None shortens worklist and
                # stock rack labels.
                design_number = None
            self.__process_stock_rack(LABELS.ROLE_SINGLE_DESIGN_STOCK,
                                      sector_index,
                                      design_number,
                                      sdssr_barcode,
                                      wl_series,
                                      sector_layout)
        return sector_tube_transfers

    def __process_pool_transfers(self, sector_index, sector_layout):
        pp_vol = self.iso.iso_request.preparation_plate_volume \
                 * VOLUME_CONVERSION_FACTOR
        # Create a worklist series for the stock transfer.
        wl_label = LABELS.create_sector_stock_transfer_worklist_label(
                                                    self.iso.label,
                                                    LABELS.ROLE_POOL_STOCK,
                                                    sector_index)
        prep_transfer_volume = get_preparation_plate_transfer_volume(
                                        preparation_plate_volume=pp_vol) \
                                / VOLUME_CONVERSION_FACTOR
        wl_series = self.__make_stock_rack_worklist_series(
                                                    wl_label,
                                                    prep_transfer_volume,
                                                    None)
        # Process the new pool rack.
        self.__process_stock_rack(
                        LABELS.ROLE_POOL_STOCK,
                        sector_index,
                        None,
                        self.__pool_stock_rack_map[sector_index],
                        wl_series,
                        sector_layout)

    def __get_tube_map_for_sector(self, layout):
        # We fetch all tubes for the given sector layout in one go.
        tube_agg = get_root_aggregate(ITube)
        tube_agg.filter = \
            cntd(barcode=reduce(add, [pos.stock_tube_barcodes
                                      for pos in
                                      layout.get_sorted_working_positions()])
                 )
        return (dict([(t.barcode, t) for t in iter(tube_agg)]))

    def __make_stock_rack_worklist_series(self, label, volume, layout):
        # Builds a sector 0 -> sector 0 rack transfer worklist series.
        pip_specs_cy = get_pipetting_specs_cybio()
        wl_series = WorklistSeries()
        psts = []
        if layout is None:
            # Rack transfer (only for pool stock rack -> prep plate transfer).
            pst = PlannedRackSampleTransfer.get_entity(volume, 1, 0, 0)
            psts.append(pst)
            pwl_type = TRANSFER_TYPES.RACK_SAMPLE_TRANSFER
        else:
            # Sample transfers (for single stock transfer).
            for rack_pos in layout.get_positions():
                pst = PlannedSampleTransfer.get_entity(volume, rack_pos,
                                                       rack_pos)
                psts.append(pst)
            pwl_type = TRANSFER_TYPES.SAMPLE_TRANSFER
        wl = PlannedWorklist(label, pwl_type,
                             pip_specs_cy, planned_liquid_transfers=psts)
        wl_series.add_worklist(0, wl)
        return wl_series

    def __build_tube_transfers(self, design_number, tube_rack_barcode,
                               layout, tube_map):
        tube_transfers = []
        for rack_pos, wrk_pos in layout.iterpositions():
            tube_barcode = wrk_pos.stock_tube_barcodes[design_number]
            tube = tube_map[tube_barcode]
            # While we have the source rack at hand, we record its location
            # so we can write it out to the report file later.
            self.__record_source_rack_location(tube.rack)
            ttd = TubeTransferData(tube_barcode, tube.rack.barcode,
                                   tube.position, tube_rack_barcode,
                                   rack_pos)
            tube_transfers.append(ttd)
        return tube_transfers

    def __record_source_rack_location(self, source_rack):
        if not source_rack.barcode in self.__source_rack_locations:
            loc = source_rack.location
            if loc is None:
                loc_str = 'not found'
            elif loc.index in (None, ''):
                loc_str = loc.name
            else:
                loc_str = '%s, index: %s' % (loc.name, loc.index)
            self.__source_rack_locations[source_rack.barcode] = loc_str

    def __process_stock_rack(self, role, sector_index, design_number,
                             tube_rack_barcode, worklist_series,
                             working_rack_layout):
        label = LABELS.create_sector_stock_rack_label(
                                                self.iso.label,
                                                role,
                                                sector_index,
                                                design_number=design_number)
        tube_rack = self.__tube_rack_map[tube_rack_barcode]
        rack_layout = working_rack_layout.create_rack_layout()
        # Check if we have an existing stock rack to update, using the
        # label to find it.
        exst_isrs = [isr for isr in self.iso.iso_stock_racks
                     if isr.label == label]
        if len(exst_isrs) == 1:
            exst_isr = exst_isrs[0]
            exst_isr.worklist_series = worklist_series
            exst_isr.rack = tube_rack
            exst_isr.rack_layout = rack_layout
        elif len(exst_isrs) == 0:
            # FIXME: Using instantiation for side effects.
            IsoSectorStockRack(self.iso, sector_index, label, tube_rack,
                               rack_layout, worklist_series)
        else:
            self.add_error('More than one stock rack have the same '
                           'label (%s).' % exst_isrs[0].label)

    def __build_tube_handler_files(self, stock_tube_transfer_map, file_map):
        self.add_debug('Creating XL20 files.')
        for sec_idx, tube_transfers in stock_tube_transfer_map.iteritems():
            self.__build_tube_handler_files_for_transfers(tube_transfers,
                                                          file_map,
                                                          sec_idx + 1)
        # Generate single tube handler and report files for all quadrants
        # (simplifies processing).
        all_tube_transfers = reduce(add, stock_tube_transfer_map.values())
        self.__build_tube_handler_files_for_transfers(all_tube_transfers,
                                                      file_map, None)

    def __build_tube_handler_files_for_transfers(self, tube_transfers,
                                                 file_map, sector_index):
        if sector_index is None:
            filename_suffix = 'all'
        else:
            filename_suffix = str(sector_index)
        fn_params = (self.iso.iso_request.label,
                     self.iso.layout_number,
                     filename_suffix
                     )
        worklist_writer = XL20WorklistWriter(tube_transfers, parent=self)
        worklist_stream = worklist_writer.get_result()
        fn_wl = self.FILE_NAME_XL20_WORKLIST % fn_params
        if worklist_stream is None:
            msg = 'Error when trying to write tube handler worklist ' \
                  '(%s, %s, %s).' % fn_params
            self.add_error(msg)
        else:
            file_map[fn_wl] = worklist_stream
            if self.include_dummy_output:
                dummy_writer = XL20Dummy(worklist_stream, parent=self)
                dummy_output_stream = dummy_writer.get_result()
                if dummy_output_stream is None:
                    msg = 'Error trying to generate dummy tube handler ' \
                          'output (%s, %s, %s).' % fn_params
                    self.add_error(msg)
                else:
                    fn_dummy_output = \
                        self.FILE_NAME_XL20_DUMMY_OUTPUT % fn_params
                    file_map[fn_dummy_output] = dummy_output_stream
        report_writer = LibraryCreationXL20ReportWriter(
                            self.iso,
                            tube_transfers,
                            self.__source_rack_locations,
                            sector_index=sector_index,
                            has_pool_stock_racks=
                                not self.pool_stock_racks is None,
                            parent=self)
        report_stream = report_writer.get_result()
        if report_stream is None:
            msg = 'Error when trying to write tube handler report ' \
                  '(%s, %s, %s).' % fn_params
            self.add_error(msg)
        else:
            fn = self.FILE_NAME_XL20_REPORT % fn_params
            file_map[fn] = report_stream


    def __build_cybio_overview_file(self, file_map):
        self.add_debug('Creating Cybio overview file.')
        self.add_debug('Generate CyBio info file ...')
        writer = LibraryCreationCyBioOverviewWriter(
                                    self.iso,
                                    self.__single_stock_rack_map,
                                    pool_stock_rack_map=
                                                self.__pool_stock_rack_map,
                                    parent=self)
        stream = writer.get_result()
        if stream is None:
            msg = 'Error when trying to write CyBio info file.'
            self.add_error(msg)
        else:
            fn = self.FILE_NAME_CYBIO \
                 % (self.iso.iso_request.label, self.iso.layout_number)
            file_map[fn] = stream


class LibraryCreationXL20ReportWriter(TxtWriter):
    """
    Generates an overview for the tube handling in a library creation ISO.

    **Return Value:** stream (TXT)
    """
    NAME = 'Library Creation XL20 Report Writer'
    #: The main headline of the file.
    BASE_MAIN_HEADER = 'XL20 Worklist Generation Report / %s / %s'
    #: The header text for the general section.
    GENERAL_HEADER = 'General Settings'
    #: This line presents the library name.
    LIBRARY_LINE = 'ISO for Library: %s'
    #: This line presents the layout number.
    LAYOUT_NUMBER_LINE = 'Layout number: %i'
    #: This line presents the quadrant number.
    SECTOR_NUMBER_LINE = 'Sector number: %i'
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
    def __init__(self, iso, tube_transfers,
                 source_rack_locations, sector_index=None,
                 has_pool_stock_racks=True, parent=None):
        """
        Constructor.

        :param iso: The library creation ISO for which to
            generate the file.
        :type iso:
            :class:`thelma.models.iso.StockSampleCreationIso`
        :param tube_transfers: Define which tube goes where.
        :type tube_transfers: :class:`TubeTransfer`#
        :param int sector_index: Sector of the rack being created. If this
            is not given, no sector information will be included in the
            header.
        :param dict source_rack_locations: Map rack barcode -> rack location.
        :param bool has_pool_stock_racks: Flag indicating if the ISO being
            processed will create stock pool racks.
        """
        TxtWriter.__init__(self, parent=None)
        self.tube_transfers = tube_transfers
        self.iso = iso
        self.source_rack_locations = source_rack_locations
        self.sector_index = sector_index
        self.has_pool_stock_racks = has_pool_stock_racks

    def _check_input(self):
        if self._check_input_class('library creation ISO',
                            self.iso, StockSampleCreationIso):
            status = self.iso.status
            if status != ISO_STATUS.QUEUED:
                msg = 'Unexpected ISO status: "%s"' % (status)
                self.add_error(msg)
        if self._check_input_class('tube transfer list', self.tube_transfers,
                                   list):
            for ttd in self.tube_transfers:
                if not self._check_input_class('tube transfer', ttd,
                                               TubeTransferData): break
        if not self.sector_index is None:
            self._check_input_class('sector index', self.sector_index, int)
        self._check_input_class('rack location map',
                                self.source_rack_locations, dict)

    def _write_stream_content(self):
        self.add_debug('Write stream ...')
        self.__write_main_headline()
        self.__write_general_section()
        self.__write_destination_racks_section()
        self.__write_source_racks_section()

    def __write_main_headline(self):
        # Writes the main head line.
        now = datetime.now()
        date_string = now.strftime('%d.%m.%Y')
        time_string = now.strftime('%H:%M')
        main_headline = self.BASE_MAIN_HEADER % (date_string, time_string)
        self._write_headline(main_headline, underline_char='=',
                             preceding_blank_lines=0, trailing_blank_lines=1)

    def __write_general_section(self):
        # The general section contains library name, layout number, sector
        # index, number of tubes, and transfer volume.
        if self.has_pool_stock_racks:
            vol = get_pool_transfer_volume(
                        number_designs=self.iso.iso_request.number_designs)
        else:
            pp_vol = self.iso.iso_request.preparation_plate_volume \
                     * VOLUME_CONVERSION_FACTOR
            src_conc = self.iso.iso_request.stock_concentration \
                       * CONCENTRATION_CONVERSION_FACTOR
            vol = get_preparation_plate_transfer_volume(
                                            source_concentration=src_conc,
                                            preparation_plate_volume=pp_vol)
        self._write_headline(self.GENERAL_HEADER, preceding_blank_lines=1)
        general_lines = [self.LIBRARY_LINE % self.iso.iso_request.label,
                         self.LAYOUT_NUMBER_LINE % self.iso.layout_number]
        if not self.sector_index is None:
            general_lines.append(
                         self.SECTOR_NUMBER_LINE % (self.sector_index + 1))
        general_lines.extend([self.TUBE_NO_LINE % len(self.tube_transfers),
                              self.VOLUME_LINE % vol])
        self._write_body_lines(general_lines)

    def __write_destination_racks_section(self):
        # Writes the destination rack section.
        barcodes = set()
        for ttd in self.tube_transfers:
            barcodes.add(ttd.trg_rack_barcode)
        self._write_headline(self.DESTINATION_RACKS_HEADER)
        lines = []
        for barcode in barcodes:
            lines.append(self.DESTINATION_RACK_BASE_LINE % (barcode))
        self._write_body_lines(lines)

    def __write_source_racks_section(self):
        # Writes the source rack section.
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


class LibraryCreationCyBioOverviewWriter(TxtWriter):
    """
    This tool writes a CyBio overview file for the CyBio steps involved in
    the creation of library plates.

    We do not use the normal series worklist writer here because the stock
    tubes for the single molecule designs are not the right positions yet.

    **Return Value:** stream (TXT)
    """
    NAME = 'Library Creation CyBio Writer'
    #: Header for the pool creation section.
    HEADER_POOL_CREATION = 'Pool Creation'
    #: Header for the preparation plate transfer section.
    HEADER_PREP_CREATION = 'Transfer from Stock Rack to Preparation Plates'
    #: Header for the aliquot transfer section.
    HEADER_ALIQUOT_TRANSFER = 'Transfer to Library Aliquot Plates'
    #: Base line for transfer volumes.
    VOLUME_LINE = 'Volume: %.1f ul'
    #: Base line for buffer volumes.
    BUFFER_LINE = 'Assumed buffer volume: %.1f ul'
    #: Base line for source racks (singular, for prep plate creation)
    SOURCE_LINE = 'Source rack: %s'
    #: Base line for source racks (plural, for pool creation).
    SOURCE_LINE_PLURAL = 'Source racks: %s'
    #: Base line for target racks (singlular)
    TARGET_LINE = 'Target rack: %s'
    #: Base line for target racks (plural, for aliquot section).
    TARGET_LINE_PLURAL = 'Target racks: %s'
    #: Base line for quadrant depcitions.
    QUADRANT_LINE = 'Q%i:'

    def __init__(self, iso, single_stock_rack_map, pool_stock_rack_map=None,
                 parent=None):
        """
        Constructor.

        :param iso: The library creation ISO for which to
            generate the file.
        :type iso:
            :class:`thelma.models.iso.StockSampleCreationIso`
        :param dict single_stock_rack_map: The barcodes for the destination
            rack for the single molecule design tube (these racks have to be
            empty).
        :param dict pool_stock_rack_map: The barcodes for the pool stock racks
            (these racks have to have empty tubes in defined positions).
        """
        TxtWriter.__init__(self, parent=parent)
        self.iso = iso
        self.single_stock_rack_map = single_stock_rack_map
        self.pool_stock_rack_map = pool_stock_rack_map
        #: Sector preparation plates.
        self.__sector_prep_plate_map = None

    def reset(self):
        TxtWriter.reset(self)
        self.__sector_prep_plate_map = dict()

    def _check_input(self):
        self.add_debug('Check input values ...')
        if self._check_input_class('library creation ISO',
                            self.iso, StockSampleCreationIso):
            status = self.iso.status
            if status != ISO_STATUS.QUEUED:
                msg = 'Unexpected ISO status: "%s"' % (status)
                self.add_error(msg)
        if self._check_input_class('tube destination rack map',
                                   self.single_stock_rack_map, dict):
            for sector_index, barcode_list in \
                                    self.single_stock_rack_map.iteritems():
                if not self._check_input_class(
                        'sector index in the tube destination map',
                         sector_index, int): break
                if not self._check_input_class(
                        'barcode list in the tube destination map',
                        barcode_list, list): break
            if not len(self.single_stock_rack_map) > 0:
                msg = 'There are no barcodes in the destination rack map!'
                self.add_error(msg)
        if not self.pool_stock_rack_map is None \
           and self._check_input_class('pool stock rack map',
                                   self.pool_stock_rack_map, dict):
            for sector_index, barcode in self.pool_stock_rack_map.iteritems():
                if not self._check_input_class(
                        'sector index in the pool stock rack map',
                         sector_index, int): break
                if not self._check_input_class(
                        'barcode in the pool stock rack map',
                        barcode, basestring): break
            if not len(self.pool_stock_rack_map) > 0:
                msg = 'There are no barcodes in the pool stock rack map!'
                self.add_error(msg)

    def _write_stream_content(self):
        """
        Writes into the streams.
        """
        self.add_debug('Write stream ...')
        if not self.pool_stock_rack_map is None:
            self.__write_pool_creation_section()
        self.__get_sector_preparation_plates()
        self.__write_prep_creation_section()
        self.__write_aliquot_section()

    def __write_pool_creation_section(self):
        # This is the stock transfer part (creating pools from single molecule
        # designs).
        self.add_debug('Writing pool section.')
        self._write_headline(header_text=self.HEADER_POOL_CREATION,
                             preceding_blank_lines=0)
        lines = []
        volume_line = self.VOLUME_LINE \
            % get_pool_transfer_volume(number_designs=
                                         self.iso.iso_request.number_designs)
        volume_line += ' each'
        lines.append(volume_line)
        buffer_line = self.BUFFER_LINE % get_pool_buffer_volume()
        lines.append(buffer_line)
        for sector_index in sorted(self.single_stock_rack_map.keys()):
            lines.append('')
            lines.append(self.QUADRANT_LINE % (sector_index + 1))
            barcodes = self.single_stock_rack_map[sector_index]
            target_rack = self.pool_stock_rack_map[sector_index]
            src_line = self.SOURCE_LINE_PLURAL % (', '.join(sorted(barcodes)))
            lines.append(src_line)
            lines.append(self.TARGET_LINE % (target_rack))
        self._write_body_lines(lines)

    def __get_sector_preparation_plates(self):
        # Builds a map sector index -> library preparation plate.
        for ispp in self.iso.iso_sector_preparation_plates:
            self.__sector_prep_plate_map[ispp.sector_index] = ispp.rack

    def __write_prep_creation_section(self):
        # This part deals with the transfer to the preparation plates.
        self.add_debug('Writing preparation plate section.')
        self._write_headline(header_text=self.HEADER_PREP_CREATION)
        pp_vol = self.iso.iso_request.preparation_plate_volume \
                 * VOLUME_CONVERSION_FACTOR
        if not self.pool_stock_rack_map is None:
            src_conc = DEFAULT_POOL_STOCK_RACK_CONCENTRATION
            src_rack_map = self.pool_stock_rack_map
        else:
            src_conc = self.iso.iso_request.stock_concentration \
                       * CONCENTRATION_CONVERSION_FACTOR
            src_rack_map = dict([(idx, bcs[0])
                                 for (idx, bcs) in
                                 self.single_stock_rack_map.items()
                                 if idx in self.__sector_prep_plate_map])
        trf_vol = get_preparation_plate_transfer_volume(
                                            source_concentration=src_conc,
                                            preparation_plate_volume=pp_vol)
        volume_line = self.VOLUME_LINE % trf_vol
        lines = [volume_line]
        buffer_volume = pp_vol - trf_vol
        buffer_line = self.BUFFER_LINE % buffer_volume
        lines.append(buffer_line)
        for sector_index in sorted(src_rack_map.keys()):
            lines.append('')
            lines.append(self.QUADRANT_LINE % (sector_index + 1))
            pool_barcode = src_rack_map[sector_index]
            prep_plate = self.__sector_prep_plate_map[sector_index]
            src_term = '%s (%s)' % (prep_plate.barcode, prep_plate.label)
            lines.append(self.SOURCE_LINE % pool_barcode)
            lines.append(self.TARGET_LINE % src_term)
        self._write_body_lines(lines)

    def __write_aliquot_section(self):
        # This part deals with the transfer from preparation plates to
        # aliquot plates.
        self.add_debug('Writing aliquot transfer section.')
        self._write_headline(self.HEADER_ALIQUOT_TRANSFER)
        lines = []
        lines.append(self.SOURCE_LINE_PLURAL % '')
        for sector_index in sorted(self.__sector_prep_plate_map.keys()):
            line = self.QUADRANT_LINE % (sector_index + 1)
            prep_plate = self.__sector_prep_plate_map[sector_index]
            src_term = ' %s (%s)' % (prep_plate.barcode, prep_plate.label)
            line += '%s' % (src_term)
            lines.append(line)
        aliquot_plates = dict()
        for iap in self.iso.iso_aliquot_plates:
            plate = iap.rack
            aliquot_plates[plate.label] = plate.barcode
        lines.append(LINEBREAK_CHAR)
        lines.append(self.TARGET_LINE_PLURAL % '')
        for label in sorted(aliquot_plates.keys()):
            barcode = aliquot_plates[label]
            trg_term = '%s (%s)' % (barcode, label)
            lines.append(trg_term)
        self._write_body_lines(lines)
