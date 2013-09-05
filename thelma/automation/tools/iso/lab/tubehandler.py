"""
Tubehandler related tools in lab ISO processing.

AAB
"""
from StringIO import StringIO
from datetime import datetime
from everest.entities.utils import get_root_aggregate
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.dummies import XL20Dummy
from thelma.automation.tools.iso.base import StockRackLayout
from thelma.automation.tools.iso.base import StockRackPosition
from thelma.automation.tools.iso.lab.base import FinalLabIsoLayout
from thelma.automation.tools.iso.lab.base import FinalLabIsoLayoutConverter
from thelma.automation.tools.iso.lab.base import LABELS
from thelma.automation.tools.iso.lab.base import LabIsoPrepLayoutConverter
from thelma.automation.tools.iso.lab.base import LabIsoRackContainer
from thelma.automation.tools.iso.lab.base import create_instructions_writer
from thelma.automation.tools.iso.lab.tubepicking import LabIsoXL20TubePicker
from thelma.automation.tools.iso.lab.tubepicking import StockTubeContainer
from thelma.automation.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.tools.semiconstants import get_positions_for_shape
from thelma.automation.tools.utils.base import FIXED_POSITION_TYPE
from thelma.automation.tools.utils.base import add_list_map_element
from thelma.automation.tools.utils.racksector import RackSectorTranslator
from thelma.automation.tools.worklists.optimiser import BiomekLayoutOptimizer
from thelma.automation.tools.worklists.optimiser import TransferItem
from thelma.automation.tools.worklists.tubehandler import BaseXL20WorklistWriter
from thelma.automation.tools.writers import LINEBREAK_CHAR
from thelma.automation.tools.writers import TxtWriter
from thelma.automation.tools.writers import create_zip_archive
from thelma.interfaces import ITubeRack
from thelma.models.iso import IsoJobStockRack
from thelma.models.iso import IsoSectorStockRack
from thelma.models.iso import IsoStockRack
from thelma.models.iso import LabIso
from thelma.models.job import IsoJob
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.liquidtransfer import WorklistSeries
from thelma.models.moleculedesign import MoleculeDesignPool
from thelma.models.rack import RackShape

__docformat__ = 'reStructuredText en'

__all__ = ['_XL20WorklistGenerator',
           'LabIsoJobXL20WorklistGenerator',
           'LabIsoXL20WorklistGenerator',
           'LabIsoStockTransferItem',
           'LabIsoStockRackOptimizer',
           'LabIsoXL20WorklistWriter',
           'LabIsoXL20SummaryWriter',
           ]


class _XL20WorklistGenerator(BaseAutomationTool):
    """
    This tool generates a zip archive that contains worklists for the tube
    handler (XL20) and some overview and report files. If the
    :param:`include_dummy_output` flag is set, an additional file containing
    the output from the XL20 dummy writer is added.

    At this, it generate stock rack entities and conducts checks on DB level.
    The output is a zip archive

    **Return Value:** A zip archive with two files (worklist and reports);
    """

    #: The entity class supported by this generator.
    _ENTITY_CLS = None

    #: The file name of the XL20 worklist file contains the barcode and rack
    #: marker for the stock rack it deals with.
    FILE_NAME_XL20_WORKLIST = '%s_%s_xl20_worklist.csv'
    #: The file name for the XL20 summary file contains the entity label.
    FILE_NAME_XL20_SUMMARY = '%s_xl20_summary.txt'
    #: The file name for the instructions contains the entity label.
    FILE_NAME_INSTRUCTIONS = '%s_instructions.txt'
    #: The dummy output file names contain the barcode and rack marker for
    #: the stock racks they deal with.
    FILE_NAME_DUMMY = '%s_%s_dummy_xl20_output.tpo'

    def __init__(self, entity, destination_rack_barcodes,
                 excluded_racks=None, requested_tubes=None,
                 include_dummy_output=False, **kw):
        """
        Constructor:

        :param entity: The ISO or the ISO job for which to generate the files
            and the racks.
        :type entity: :class:`LabIso` or :class:`IsoJob`
            (see :attr:`_ENTITY_CLS).

        :param destination_rack_barcodes: The barcodes for the destination
            racks (the rack the tubes shall be transferred to).
        :type destination_rack_barcodes: list of barcodes (:class:`basestring`)

        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for molecule design picking.
        :type excluded_racks: A list of rack barcodes

        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of rack barcodes.

        :param include_dummy_output: Flag indicating if the
            `thelma.tools.dummies.XL20Dummy` output writer should be run
            at the end of the worklist generation. The resulting output file
            is then included in the zip file.
        :type include_dummy_output: :class:`bool`
        :default include_dummy_output: *False*
        """
        BaseAutomationTool.__init__(self, depending=False, **kw)

        #: The ISO or the ISO job for which to generate the files and the racks.
        self.entity = entity
        #: The barcodes of the racks the tubes shall be transferred to.
        self.destination_rack_barcodes = destination_rack_barcodes

        #: A list of barcodes from stock racks that shall not be used for
        #: molecule design picking.
        self.excluded_racks = excluded_racks
        if excluded_racks is None: self.excluded_racks = []
        #: A list of barcodes from stock tubes that are supposed to be used.
        self.requested_tubes = requested_tubes
        if requested_tubes is None: self.requested_tubes = []
        #: Flag indicating if the file from the dummy output writer should be
        #: included in the output zip file.
        self.include_dummy_output = include_dummy_output

        #: The lab ISO requests the entity belongs to.
        self._iso_request = None
        #: Maps tube racks onto barcodes (required for stock racks).
        self.__barcode_map = None

        #: The :class:`LabIsoRackContainer` for each involved plate or rack
        #: mapped onto label
        self.__rack_containers = None
        #: The ISO plate layouts of the ISO (job) plates mapped onto plate
        #: labels. For the final plate layout there is only one layout
        #: (mapped onto the :attr:`LABELS.ROLE_FINAL` marker).
        self._plate_layouts = None
        #: The stock tube items mapped onto pools.
        self._stock_tube_containers = None

        #: Stores the stock tube container items for each stock rack (marker).
        self._tubes_by_rack = dict()
        #: The stock rack layout for each stock rack (marker).
        self._stock_rack_layouts = dict()
        #: The worklist series for the stock transfers mapped onto stock
        #: rack label.
        self.__stock_transfer_series = None

        #: The stream for each generated file mapped onto file name.
        self.__stream_map = None
        #: The zip stream wrapped around the two files.
        self.__zip_stream = None

    def reset(self):
        BaseAutomationTool.reset(self)
        self._iso_request = None
        self.__barcode_map = dict()
        self.__rack_containers = dict()
        self._plate_layouts = dict()
        self._tubes_by_rack = dict()
        self._stock_rack_layouts = dict()
        self._stock_tube_containers = dict()
        self.__stock_transfer_series = dict()
        self.__stream_map = dict()
        self.__zip_stream = None

    def run(self):
        self.reset()
        self.add_info('Start planning XL20 run ...')

        self._check_input()
        if not self.has_errors():
            self.__get_tube_racks()
            self._get_layouts()
        if not self.has_errors(): self._find_starting_wells()
        if not self.has_errors(): self.__find_stock_tubes()
        if not self.has_errors(): self.__add_stock_racks()
        if not self.has_errors(): self.__write_streams()
        if not self.has_errors():
            self.__create_zip_archive()
            self.return_value = self.__zip_stream
            self.add_info('File generation completed.')

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')

        if self._check_input_class('entity', self.entity, self._ENTITY_CLS):
            self._iso_request = self.entity.iso_request
        self._check_input_class('"include dummy output" flag',
                                self.include_dummy_output, bool)
        self._check_input_list_classes('destination rack barcode',
                                    self.destination_rack_barcodes, basestring)
        self._check_input_list_classes('excluded rack', self.excluded_racks,
                                       basestring, may_be_empty=True)
        self._check_input_list_classes('requested tube', self.requested_tubes,
                                       basestring, may_be_empty=True)

    def __get_tube_racks(self):
        """
        Fetches the tube racks for the passed barcodes from the DB.
        """
        self.add_debug('Fetch racks for barcodes ...')

        non_empty = []
        tube_rack_agg = get_root_aggregate(ITubeRack)

        for barcode in self.destination_rack_barcodes:
            if len(barcode) < 1: continue
            rack = tube_rack_agg.get_by_slug(barcode)
            if rack is None:
                msg = 'Rack %s has not been found in the DB!' % (barcode)
                self.add_error(msg)
            elif len(rack.containers) > 0:
                non_empty.append(barcode)
            else:
                self.__barcode_map[barcode] = rack

        if len(non_empty) > 0:
            non_empty.sort()
            msg = 'The following racks you have chosen are not empty: %s.' \
                  % (', '.join(non_empty))
            self.add_error(msg)

        if not self.has_errors() and \
                    (len(self.__barcode_map) < self.entity.number_stock_racks):
            msg = 'The number of stock rack barcodes is too low! ' \
                  'Expected: %i, found: %i.' % (self.entity.number_stock_racks,
                                                len(self.__barcode_map))
            self.add_error(msg)

    def _get_layouts(self):
        """
        Fetches the layouts of each plate involved in the generation of
        the :attr:`entity`.
        """
        raise NotImplementedError('Abstract method.')

    def _store_plate_layout(self, label, converter, error_label):
        """
        Helper function running the passed converter. In case of failure, an
        error message is recorded. Otherwise the resulting layouts is stored
        in the :attr:`_plate_layouts` map.
        """
        layout = converter.get_result()
        if layout is None:
            msg = 'Error when trying to convert layout for %s.' % (error_label)
            self.add_error(msg)
        else:
            self._plate_layouts[label] = layout

    def _store_final_plate_data(self, iso):
        """
        Helper function creating and storing a rack container of all final
        plates of an ISO. The rack markers for aliquot and library plates
        need to be distinguished.
        """
        for fp in iso.final_plates:
            self._store_rack_container(fp.rack, role=LABELS.ROLE_FINAL)

    def _store_rack_container(self, rack, role, label=None, rack_marker=None):
        """
        Helper function creating a :class:`LabIsoRackContainer` for a
        rack. The containers are store in the :attr:`_rack_containers` map.
        """
        rack_container = LabIsoRackContainer(rack=rack, label=label, role=role,
                                             rack_marker=rack_marker)
        self.__rack_containers[label] = rack_container

    def _find_starting_wells(self):
        """
        Searches the stored layouts for starting wells. The data is stored in
        :class:`StockTubeContainer` objects.
        """
        self.add_debug('Search for starting wells ...')

        final_layout_copy_number = self._get_final_layout_copy_number()
        for plate_label, layout in self._plate_layouts.iteritems():
            is_final_plate = isinstance(layout, FinalLabIsoLayout)
            for_job = isinstance(self.entity, IsoJob)
            for plate_pos in layout.get_sorted_working_positions():
                if not plate_pos.is_starting_well: continue
                if is_final_plate and not (plate_pos.for_job == for_job):
                    continue
                pool = plate_pos.molecule_design_pool
                if self._stock_tube_containers.has_key(pool):
                    container = self._stock_tube_containers[pool]
                else:
                    container = StockTubeContainer.from_plate_position(
                                            plate_pos, final_layout_copy_number)
                    self._stock_tube_containers[pool] = container
                if is_final_plate:
                    container.add_final_position(plate_pos)
                else:
                    container.add_preparation_position(plate_label, plate_pos)

    def _get_final_layout_copy_number(self):
        """
        Returns the number of copies for the final ISO plate. This should be
        at least the number of aliquot ordered.
        """
        raise NotImplementedError('Abstract method.')

    def __find_stock_tubes(self):
        """
        Checks whether the schedule tubes are still sufficient. If not, the
        regarding tubes are replaced.
        """
        self.add_debug('Check stock tubes ...')

        picker = LabIsoXL20TubePicker(log=self.log,
                    stock_tube_containers=self._stock_tube_containers,
                    excluded_racks=self.excluded_racks,
                    requested_tubes=self.requested_tubes)

        self._stock_tube_containers = picker.get_result()
        if self._stock_tube_containers is None:
            msg = 'Error when trying to pick stock tubes.'
            self.add_error(msg)
        else:
            missing_pools = []
            for container in self._stock_tube_containers:
                if container.tube_candidate is None:
                    missing_pools.append(container.pool)
            if len(missing_pools) > 0:
                self._react_on_missing_pools(missing_pools)

    def _react_on_missing_pools(self, missing_pools):
        """
        Deals with molecule design pools for which there was no tube picked.
        """
        raise NotImplementedError('Abstract method.')

    def __add_stock_racks(self):
        """
        Each stock rack needs a layout and a worklist series.
        """
        self.add_debug('Attach stock racks ...')

        self.__sort_tubes_into_stock_racks()
        self._create_stock_rack_layouts()
        self.__create_stock_rack_worklist_series()
        self.__create_stock_racks()

    def __sort_tubes_into_stock_racks(self):
        """
        Collects the stock tube containers for each stock rack. The referring
        data is stored in the plate position. We use the first plate position
        of each container - even if the data is inconsistent this does not
        matter because so far nothing else depends on it.
        """
        for container in self._stock_tube_containers.values():
            if container.tube_candidate is None: continue
            plate_pos = container.get_all_plate_positions()[0]
            add_list_map_element(self._tubes_by_rack,
                                 plate_pos.stock_rack_marker, container)

    def _create_stock_rack_layouts(self):
        """
        Generates the :class:`StockRackLayout` for each stock rack.
        """
        raise NotImplementedError('Abstract method.')

    def _create_stock_rack_layouts_with_biomek(self):
        """
        If the rack shapes for all target layouts are the same, we can use
        optimise the layout for Biomek speed. Otherwise, we try to assign
        similar positions.
        """
        for sr_marker, containers in self._tubes_by_rack.iteritems():
            if self.__optimize_stock_rack_layout(sr_marker, containers):
                continue
            self.__find_other_biomek_stock_rack_layout(containers, sr_marker)

    def __optimize_stock_rack_layout(self, stock_rack_marker, containers):
        """
        Checks whether all target plate shapes for the given stock rack are
        equal. If so, we can optimise the layout.
        """
        rack_shape = None
        for container in containers:
            for plate_label in container.plate_target_positions.keys():
                layout = self._plate_layouts[plate_label]
                if rack_shape is None:
                    rack_shape = layout.shape
                elif not rack_shape == layout.shape:
                    return False

        optimizer = LabIsoStockRackOptimizer(log=self.log,
                                    stock_tube_containers=containers,
                                    target_rack_shape=rack_shape)
        stock_rack_layout = optimizer.get_result()
        if stock_rack_layout is None:
            msg = 'Error when trying to optimise layout for stock rack "%s"!' \
                   % (stock_rack_marker)
            self.add_error(msg)
        else:
            self._stock_rack_layouts[stock_rack_marker] = stock_rack_layout
        return True

    def __find_other_biomek_stock_rack_layout(self, containers,
                                              stock_rack_marker):
        """
        This function is used if we want to use the Biomek and the target plates
        for a stock rack have different shapes. Before assigning positions we
        try to find and score preferred positions for each pool.
        """
        pref_positions, transfer_targets = \
                    self.__find_preferred_stock_rack_positions(containers)

        # sort pools by score
        score_pos_map = dict()
        for pool, pref_map in pref_positions.iteritems():
            for pref_pos, score in pref_map.iteritems():
                if score_pos_map.has_key(score):
                    pool_map = score_pos_map[score]
                else:
                    pool_map = dict()
                    score_pos_map[score] = pool
                add_list_map_element(pool_map, pref_pos, pool)

        # assign preferred positions to pools if possible
        assigned_pools = dict()
        remaining_pools = set(pref_positions.keys())
        for score in sorted(score_pos_map.keys()):
            pool_map = score_pos_map[score]
            for pref_pos, pools in pool_map.iteritems():
                pool_applicants = []
                for pool in pools:
                    if pool in remaining_pools:
                        pool_applicants.append(pool)
                if len(pool_applicants) < 1: continue
                pool_applicants.sort(cmp=lambda p1, p2: cmp(p1.id, p2.id))
                pool = pool_applicants[0]
                assigned_pools[pool] = pref_pos
                remaining_pools.remove(pool)

        # Find positions for other pools
        all_positions = get_positions_for_shape(RACK_SHAPE_NAMES.SHAPE_96)
        used_positions = set(assigned_pools.values())
        for pool in remaining_pools:
            rack_pos = all_positions.pop(0)
            if rack_pos in used_positions: continue
            assigned_pools[pool] = rack_pos

        # Create layout
        stock_rack_layout = StockRackLayout()
        for pool, rack_pos in assigned_pools.iteritems():
            tube_barcode = self._stock_tube_containers[pool].tube_candidate.\
                           tube_barcode
            sr_pos = StockRackPosition(rack_position=rack_pos,
                           molecule_design_pool=pool, tube_barcode=tube_barcode,
                           transfer_targets=transfer_targets[pool])
            stock_rack_layout.add_position(sr_pos)

        self._stock_rack_layouts[stock_rack_marker] = stock_rack_layout

    def __find_preferred_stock_rack_positions(self, containers):
        """
        Finds the preferred positions and transfer targets for each pool
        (used if the target plates for a stock rack have different shapes.)
        """
        translation_map = dict() # The 96-well position for each 384-well pos.
        for sector_index in range(4):
            translator = RackSectorTranslator(number_sectors=4,
                      source_sector_index=0, target_sector_index=sector_index,
                      enforce_type=RackSectorTranslator.ONE_TO_MANY)
            for pos96 in get_positions_for_shape(RACK_SHAPE_NAMES.SHAPE_96):
                pos384 = translator.translate(pos96)
                translation_map[pos384] = pos96

        pref_positions = dict() # the preferred rack positions for each pool
        transfer_targets = dict() # the transfer targets for each pool
        for container in containers:
            tts = []
            pref_positions = dict()
            for plate_label, positions in container.plate_target_positions.\
                                          iteritems():
                layout = self._plate_layouts[plate_label]
                translate = (layout.shape.name == RACK_SHAPE_NAMES.SHAPE_384)
                for plate_pos in positions:
                    rack_pos = plate_pos.rack_position
                    tts.append(plate_pos.as_transfer_target())
                    if translate:
                        pref_pos = translation_map[rack_pos]
                    else:
                        pref_pos = rack_pos
                    if not pref_positions.has_key(pref_pos):
                        pref_positions[pref_pos] = 0
                    pref_positions[pref_pos] += 1
            transfer_targets[container.pool] = tts
            pref_positions[container.pool] = pref_positions

        return pref_positions, transfer_targets

    def __create_stock_rack_worklist_series(self):
        """
        The transfer for each worklist series are derived from the stock
        rack layouts.
        """
        ticket_number = self._iso_request.experiment_metadata.ticket_number
        for sr_marker, sr_layout in self._stock_rack_layouts.iteritems():
            worklist_series = WorklistSeries()
            for rack_marker in self.__get_sorted_plate_markers():
                transfers = []
                for sr_pos in sr_layout.get_working_positions():
                    psts = sr_pos.get_planned_sample_transfers(rack_marker)
                    transfers.extend(psts)
                if len(transfers) < 1: continue
                wl_index = len(worklist_series)
                wl_label = LABELS.create_worklist_label(ticket_number,
                                 worklist_number=wl_index,
                                 target_rack_marker=rack_marker,
                                 source_rack_marker=sr_marker)
                worklist = PlannedWorklist(label=wl_label,
                               transfer_type=TRANSFER_TYPES.SAMPLE_TRANSFER,
                               planned_liquid_transfers=transfers)
                worklist_series.add_worklist(wl_index, worklist)
            self.__stock_transfer_series[sr_marker] = worklist_series

    def __get_sorted_plate_markers(self):
        """
        The final ISO plate is the last one. Its key in the layout is list
        is the :attr:`LABELS.ROLE_FINAL` marker, they are therefore not found
        in the rack container map (which uses labels as keys).
        Preparation plates are ordered by name.
        """
        ordered_labels = []
        final_labels = []
        for plate_label in self._plate_layouts.keys():
            if self.__rack_containers.has_key(plate_label):
                rack_container = self.__rack_containers[plate_label]
                ordered_labels.append(rack_container.rack_marker)
            else:
                # final plates are mapped on plate labels in the rack container
                # map and and on the role solely in the layout map
                final_labels.append(plate_label)

        return sorted(ordered_labels) + sorted(final_labels)

    def __create_stock_racks(self):
        """
        The worklist series and rack layouts have already been generated.
        """
        stock_racks = []
        sorted_barcodes = []
        for barcode in sorted(self.destination_rack_barcodes):
            sorted_barcodes.append(barcode)
        for stock_rack_marker in sorted(self._stock_rack_layouts.keys()):
            barcode = sorted_barcodes.pop(0)
            kw = self.__get_stock_rack_base_kw(stock_rack_marker, barcode)
            stock_rack = self._create_stock_rack_entity(stock_rack_marker, kw)
            stock_racks.append(stock_rack)
            self._store_rack_container(stock_rack.rack, LABELS.ROLE_STOCK,
                                       stock_rack.label)
        self.entity.iso_job_stock_racks = stock_racks

        raise NotImplementedError('Abstract method.')

    def __get_stock_rack_base_kw(self, stock_rack_marker, rack_barcode):
        """
        Helper function returning the keyword dictionary for a
        :class:`StockRack` entity. It contains values for all shared keywords.
        """
        tube_rack = self.__barcode_map[rack_barcode]
        rack_layout = self._stock_rack_layouts[stock_rack_marker].\
                      create_rack_layout()
        return dict(rack=tube_rack, rack_layout=rack_layout,
               worklist_series=self.__stock_transfer_series[stock_rack_marker])

    def _create_stock_rack_entity(self, stock_rack_marker, base_kw):
        """
        Creates and returns the stock rack entity for the passed stock rack
        marker. The common stock rack keywords and values are already part
        of the :param:`base_kw`.
        """
        raise NotImplementedError('Abstract method.')

    def __write_streams(self):
        """
        Writes the XL20 worklists, XL20 summary, the instructions file
        (if requested) the dummy XL20 output file.
        """
        self.add_debug('Write streams ...')

        # XL20 worklists and dummy output
        for rack_label, rack_container in self.__rack_containers.iteritems():
            if not rack_container.role == LABELS.ROLE_STOCK: continue
            rack_marker = rack_container.rack_marker
            barcode = rack_container.rack.barcode
            fn = self.FILE_NAME_XL20_WORKLIST % (barcode, rack_label)
            xl20_writer = LabIsoXL20WorklistWriter(log=self.log,
                      rack_barcode=barcode,
                      stock_rack_layout=self._stock_rack_layouts[rack_marker],
                      stock_tube_containers=self._tubes_by_rack[rack_marker])
            msg = 'Error when trying to write XL20 worklist stream for ' \
                  'rack "%s"!' % (rack_marker)
            xl20_stream = self.__generate_stream(xl20_writer, fn, error_msg=msg)
            if (not self.include_dummy_output or xl20_stream is None): continue
            dummy_writer = XL20Dummy(xl20_worklist_stream=xl20_stream,
                                     log=self.log)
            dummy_fn = self.FILE_NAME_DUMMY % (barcode, rack_label)
            dummy_msg = 'Error when trying to write dummy output stream for ' \
                        'rack "%s"!' % (rack_marker)
            self.__generate_stream(dummy_writer, dummy_fn, dummy_msg)

        # XL20 summary
        summary_writer = LabIsoXL20SummaryWriter(log=self.log,
                    entity=self.entity,
                    stock_tube_containers=self._stock_tube_containers,
                    stock_rack_layouts=self._stock_rack_layouts,
                    excluded_racks=self.excluded_racks,
                    requested_tubes=self.requested_tubes)
        summary_fn = self.FILE_NAME_XL20_SUMMARY % (self.entity.label)
        summary_msg = 'Error when trying to write summary stream!'
        self.__generate_stream(summary_writer, summary_fn, summary_msg)

        # Instructions
        kw = dict(log=self.log, entity=self.entity,
                   iso_request=self._iso_request,
                   rack_containers=self.__rack_containers.values())
        instructions_writer = create_instructions_writer(**kw)
        instruction_fn = self.FILE_NAME_INSTRUCTIONS % (self.entity.label)
        instruction_msg = 'Error when trying to write instruction stream!'
        self.__generate_stream(instructions_writer, instruction_fn,
                               instruction_msg)

    def __generate_stream(self, writer, file_name, error_msg):
        """
        Helper method running the passed writer and recording an error message
        if the run fails.
        """
        file_stream = writer.get_result()
        if file_stream is None:
            self.add_error(error_msg)
            return None
        else:
            self.__stream_map[file_name] = file_stream
            return file_stream

    def __create_zip_archive(self):
        """
        Creates a zip archive containing the generated streams.
        """
        self.__zip_stream = StringIO()
        create_zip_archive(self.__zip_stream, stream_map=self.__stream_map)


class LabIsoJobXL20WorklistGenerator(_XL20WorklistGenerator):
    """
    Generates XL20 files and overview files for an lab ISO job.

    **Return Value:** A zip archive with two files (worklist and reports);
    """
    _ENTITY_CLS = IsoJob

    def _get_layouts(self):
        """
        The final layouts for all ISOs are compared and then a reference
        layout is picked. There might be job preparation plates as well.
        """
        for prep_plate in self.entity.iso_job_preparation_plates:
            converter = LabIsoPrepLayoutConverter(log=self.log,
                                            rack_layout=prep_plate.rack_layout)
            plate_label = prep_plate.rack.label
            error_label = 'job preparation plate "%s"' % (prep_plate.rack.label)
            self._store_plate_layout(plate_label, converter, error_label)
            self._store_rack_container(prep_plate.rack,
                                       LABELS.ROLE_PREPARATION_JOB, plate_label)

        final_layouts = dict()
        for iso in self.entity.isos:
            converter = FinalLabIsoLayoutConverter(log=self.log,
                                            rack_layout=iso.rack_layout)
            error_label = 'final plate layout for ISO "%s"' % (iso.label)
            self._store_plate_layout(iso.label, converter, error_label)
            self._store_final_plate_data(iso)
            final_layouts[iso.label] = self._plate_layouts[iso.label]

        self.__compare_final_layouts(final_layouts)

    def __compare_final_layouts(self, final_layouts):
        """
        Assures that the job positions for all final layouts are equal
        and chooses a references ISO. The reference ISO will replace the
        final ISO layout for the different ISOs in the :attr:`_plate_layouts`
        map. The references layout can be accessed via
        :attr:`LABELS.ROLE_FINAL`.
        """
        reference_positions = None
        reference_iso = None
        differing_isos = []
        for iso_label in sorted(final_layouts.keys()):
            final_layout = final_layouts[iso_label]
            job_positions = []
            for final_pos in final_layout.get_sorted_working_positions():
                if final_pos.from_job and final_pos.is_starting_well:
                    job_positions.append(final_pos)
            if reference_positions is None:
                reference_positions = job_positions
                reference_iso = iso_label
            elif not reference_positions == job_positions:
                differing_isos.append(iso_label)

        if len(differing_isos) > 0:
            msg = 'The final layout for the ISOs in this job differ! ' \
                  'Reference ISO: %s. Differing ISOs: %s.' \
                  % (reference_iso, ', '.join(differing_isos))
            self.add_error(msg)
        else:
            final_role = LABELS.ROLE_FINAL
            self._plate_layouts[final_role] = final_layout[reference_iso]
            for iso_label in final_layouts.keys():
                del self._plate_layouts[iso_label]

    def _find_starting_wells(self):
        _XL20WorklistGenerator._find_starting_wells(self)

        if len(self._stock_tube_containers) < 1:
            msg = 'You do not need an XL20 worklist for this ISO job because ' \
                  'all pools are prepared directly via the ISO processing.'
            self.add_error(msg)

    def _get_final_layout_copy_number(self):
        """
        The copy number of ISO jobs is the number of ISOs times the number
        of aliquots.
        """
        return self._iso_request.number_aliquots * len(self.entity.isos)

    def _react_on_missing_pools(self, missing_pools):
        """
        All pools are controls. Thus, pools without stock tube are not allowed.
        """
        msg = 'For some control molecule design pools there are no valid ' \
              'stock tubes available: %s.' % (sorted(missing_pools))
        self.add_error(msg)

    def _create_stock_rack_layouts(self):
        """
        Job samples are always transferred with the Biomek.
        """
        self._create_stock_rack_layouts_with_biomek()

    def _create_stock_rack_entity(self, stock_rack_marker, base_kw):
        """
        All stock racks are :class:`IsoJobStockRack` entities
        """
        base_kw['iso_job'] = base_kw
        return IsoJobStockRack(**base_kw)


class LabIsoXL20WorklistGenerator(_XL20WorklistGenerator):
    """
    Generates XL20 files and overview files for an lab ISO job.

    **Return Value:** A zip archive with two files (worklist and reports);
    """
    _ENTITY_CLS = LabIso

    def __init__(self, entity, destination_rack_barcodes,
                 excluded_racks=None, requested_tubes=None,
                 include_dummy_output=False, **kw):
        """
        Constructor:

        :param entity: The ISO job for which to generate the files and the racks.
        :type entity: :class:`thelma.models.job.LabIso`

       :param destination_rack_barcodes: The barcodes for the destination
            racks (the rack the tubes shall be transferred to).
        :type destination_rack_barcodes: list of barcodes (:class:`basestring`)

        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for molecule design picking.
        :type excluded_racks: A list of rack barcodes

        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of rack barcodes.

        :param include_dummy_output: Flag indicating if the
            `thelma.tools.dummies.XL20Dummy` output writer should be run
            at the end of the worklist generation. The resulting output file
            is then included in the zip file.
        :type include_dummy_output: :class:`bool`
        :default include_dummy_output: *False*
        """
        _XL20WorklistGenerator.__init__(self, entity=entity,
                    destination_rack_barcodes=destination_rack_barcodes,
                    excluded_racks=excluded_racks,
                    requested_tubes=requested_tubes,
                    include_dummy_output=include_dummy_output, **kw)

        #: Stores the sector index for each stock rack marker. Stock racks
        #: without particular sector are not included.
        self.__stock_rack_sectors = None

    def reset(self):
        _XL20WorklistGenerator.reset(self)
        self.__stock_rack_sectors = dict()

    def _get_layouts(self):
        """
        There is one final layout for the ISO. There can be preparation plates
        as well.
        """
        for prep_plate in self.entity.iso_preparation_plates:
            converter = LabIsoPrepLayoutConverter(log=self.log,
                                            rack_layout=prep_plate.rack_layout)
            plate_label = prep_plate.rack.label
            error_label = 'ISO preparation plate "%s"' % (prep_plate.rack.label)
            self._store_plate_layout(plate_label, converter, error_label)
            self._store_rack_container(prep_plate.rack,
                                       LABELS.ROLE_PREPARATION_ISO, plate_label)

        converter = FinalLabIsoLayoutConverter(log=self.log,
                                            rack_layout=self.entity.rack_layout)
        self._store_plate_layout(LABELS.ROLE_FINAL, converter,
                                 'final ISO plate layout')
        self._store_final_plate_data(self.entity)

    def _get_final_layout_copy_number(self):
        """
        The copy number of lab ISOs is the number of aliquots.
        """
        return self._iso_request.number_aliquots

    def _react_on_missing_pools(self, missing_pools):
        """
        Fixed position must not miss. Floating positions are inactivated
        (that means they are inactivated in the layouts and removed from
        the ISO pool set). Also the stock tube containers without a candidate
        need to be deleted.
        """
        floating_pools = []
        fixed_pools = []
        adj_plates = set()
        for pool in missing_pools:
            stock_tube_container = self._stock_tube_containers[pool]
            if stock_tube_container.position_type == FIXED_POSITION_TYPE:
                fixed_pools.append(pool.id)
            else:
                for plate_label, positions in stock_tube_container.\
                                            plate_target_positions.iteritems():
                    adj_plates.add(plate_label)
                    for plate_pos in positions:
                        plate_pos.inactivate()
                floating_pools.append(pool.id)
                self.entity.molecule_design_pool_set.remove_pool(pool)

        if len(fixed_pools) > 0:
            msg = 'Unable to find stock tubes for the following fixed ' \
                  '(control) positions: %s.' \
                   % (', '.join([str(pi) for pi in sorted(fixed_pools)]))
            self.add_error(msg)
        elif len(floating_pools) > 0:
            msg = 'Unable to stock tubes for the following floating ' \
                  'positions: %s. The positions are put back into the queue.' \
                  % (', '.join([str(pi) for pi in sorted(floating_pools)]))
            self.add_error(msg)
            # Store adjusted layouts.
            if LABELS.ROLE_FINAL in adj_plates:
                layout = self._plate_layouts[LABELS.ROLE_FINAL]
                self.entity.rack_layout = layout.create_rack_layout()
            for prep_plate in self.entity.iso_preparation_plates:
                if prep_plate.rack.label in adj_plates:
                    layout = self._plate_layouts[prep_plate.rack.label]
                    prep_plate.rack_layout = layout.create_rack_layout()

        for pool in missing_pools:
            del self._stock_tube_containers[pool]

    def _create_stock_rack_layouts(self):
        """
        If the starting wells have sector data, there is one stock rack for
        each (distinct) rack sector (several rack can share the same pool
        combination).
        Otherwise the samples are transferred independently (with the BioMek).
        """
        self.__get_sectors_for_stock_racks()

        if len(self.__stock_rack_sectors) < 1:
            self._create_stock_rack_layouts_with_biomek()
        else:
            iso_layout = self._plate_layouts[LABELS.ROLE_FINAL]
            if iso_layout.shape.name == RACK_SHAPE_NAMES.SHAPE_96:
                # the position in the stock rack and final plate is the same
                if len(self._stock_rack_layouts) > 1 or \
                                            len(self._tubes_by_rack) > 1:
                    msg = 'There is more than one rack sector although ' \
                          'the final ISO plate is only a 96-well plate!'
                    self.add_error(msg)
                number_sectors = 1
            else:
                number_sectors = 4
            self.__create_sector_stock_rack_layouts(number_sectors)

    def __get_sectors_for_stock_racks(self):
        """
        The target rack sectors for a rack marker must be consistent for all
        stock tube containers for this rack. *None* is a valid sector index.
        """
        inconsistent = []
        for rack_marker, containers in self._tubes_by_rack.iteritems():
            ref_sectors = None
            for container in containers:
                sectors = set()
                for plate_pos in container.get_all_target_positions():
                    sectors.add(plate_pos.sector_index)
                if ref_sectors is None:
                    ref_sectors = sectors
                elif not ref_sectors == sectors:
                    inconsistent.append(rack_marker)
                    break
            if None in ref_sectors:
                if len(ref_sectors) > 1:
                    msg = 'Inconsistent sector data for stock rack "%s"! ' \
                          'Some position have a sector index, others do not.' \
                           % (rack_marker)
                    self.add_error(msg)
            else:
                self.__stock_rack_sectors[rack_marker] = ref_sectors

        if len(inconsistent) > 0:
            msg = 'The planned sector indices for the following stock racks ' \
                  'are inconsistent!' % (', '.join(sorted(inconsistent)))
            self.add_error(msg)

    def __create_sector_stock_rack_layouts(self, number_sectors):
        """
        If the final ISO plate is a 96-well final ISO plate, we use the
        rack position, otherwise we translate the position.
        """
        for rack_marker, sectors in self.__stock_rack_sectors.iteritems():
            layout = StockRackLayout()
            containers = self._tubes_by_rack[rack_marker]
            sector_index = sorted(sectors)[0]
            translator = RackSectorTranslator(number_sectors=4,
                      source_sector_index=sector_index, target_sector_index=0,
                      enforce_type=RackSectorTranslator.ONE_TO_MANY)
            for container in containers:
                tts = []
                stock_pos = None
                for plate_pos in container.get_all_target_positions():
                    tts.append(plate_pos.as_transfer_target())
                    if stock_pos is None: continue
                    if number_sectors == 1:
                        stock_pos = plate_pos.rack_position
                    else:
                        stock_pos = translator.translate(plate_pos.rack_position)
                tube_barcode = container.tube_candidate.tube_barcode
                sr_pos = StockRackPosition(rack_position=stock_pos,
                               molecule_design_pool=container.pool,
                               tube_barcode=tube_barcode,
                               transfer_targets=tts)
                layout.add_position(sr_pos)

    def _create_stock_rack_entity(self, stock_rack_marker, base_kw):
        """
        The stock rack can be :class:`IsoStockRack` or
        :class:`IsoSectorStockRack` objects. If there are several final plate
        sectors for a sector stock rack the lowest index is used.
        """
        base_kw['iso'] = self.entity
        if self.__stock_rack_sectors.has_key(stock_rack_marker):
            sectors = self.__stock_rack_sectors[stock_rack_marker]
            base_kw['sector_index'] = min(sectors)
            stock_rack_cls = IsoSectorStockRack
        else:
            stock_rack_cls = IsoStockRack
        return stock_rack_cls(**base_kw)


class LabIsoStockTransferItem(TransferItem):
    """
    Transfer items for the stock transfer in lab ISOs. The source positions
    are :class:`StockRackPosition` objects, the targets are
    :class:`LabIsoPosition` objects.
    """
    def _get_hash_value(self):
        return self.working_pos.molecule_design_pool.id


class LabIsoStockRackOptimizer(BiomekLayoutOptimizer):
    """
    A Biomek layout optimizer for stock racks that are used to fill lab ISO
    plates. The target plates must all have the same rack shape.

    The hash value for the assignments is the pool ID.

    **Return Value:** The optimised stock rack layout.
    """
    NAME = 'Lab ISO Stock Rack Optimiser'

    SOURCE_LAYOUT_CLS = StockRackLayout
    TRANSFER_ITEM_CLASS = LabIsoStockTransferItem

    def __init__(self, log, stock_tube_containers, target_rack_shape):
        """
        Constructor:

        :param log: The ThelmaLog you want to write in.
        :type log: :class:`thelma.ThelmaLog`

        :param stock_tube_containers: The stock tube containers mapped onto
            pools. Each container must have a tube candidate.
        :type stock_tube_containers: map

        :param target_rack_shape: The shape of the target plates.
        :type target_rack_shape: :class:`thelma.models.rack.RackShape`

        :param stock_rack_marker: The stock rack marker for his
        :type stock_rack_marker: :class:`str`
        """
        BiomekLayoutOptimizer.__init__(self, log=log)
        #: The stock tube containers mapped onto pools.
        self.stock_tube_containers = stock_tube_containers
        #: The shape of the target plates.
        self.target_rack_shape = target_rack_shape

        #: Stores the transfer targets for each pool.
        self.__transfer_targets = None

    def reset(self):
        BiomekLayoutOptimizer.reset(self)
        self.__transfer_targets = dict()

    def _check_input(self):
        self._check_input_map_classes(self.stock_tube_containers,
                    'stock tube container map', 'pool', MoleculeDesignPool,
                    'stock tube container', StockTubeContainer)
        self._check_input_class('target rack shape', self.target_rack_shape,
                                RackShape)

    def _find_hash_values(self):
        """
        The hash value is the pool ID. The plate with the most target positions
        gets the lowest index.
        """
        self.add_debug('Collect molecule design pools ... ')

        column_maps = dict()
        pos_counts = dict()

        no_tube_candidate = []

        for pool, container in self.stock_tube_containers.iteritems():
            if container.tube_candidate is None:
                no_tube_candidate.append(pool.id)
                continue
            self._hash_values.add(pool.id)
            tts = []
            for plate, positions in container.plate_target_positions.iteritems():
                if column_maps.has_key(plate):
                    column_map = column_maps[plate]
                else:
                    column_map = dict()
                    column_maps[plate] = column_map
                    pos_counts[plate] = 0
                for plate_pos in positions:
                    trg_pos = plate_pos.rack_position
                    col_index = trg_pos.column_index
                    add_list_map_element(column_map, col_index, plate_pos)
                    pos_counts[plate] += 1
                    tts.append(plate_pos.as_transfer_target())
            self.__transfer_targets[pool] = tts

        if len(no_tube_candidate) > 0:
            msg = 'There are no stock tube candidates for the following ' \
                  'pools: %s!' % (', '.join([str(pi) for pi \
                                             in sorted(no_tube_candidate)]))
            self.add_error(msg)
        else:
            plates_by_count = dict()
            for plate, pos_count in pos_counts.iteritems():
                add_list_map_element(plates_by_count, pos_count, plate)
            for pos_count in sorted(plates_by_count.keys()):
                plates = plates_by_count[pos_count]
                for plate in plates:
                    i = len(self._column_maps)
                    column_map = column_maps[plate]
                    self._column_maps[i] = column_map

    def _get_target_layout_shape(self):
        return self.target_rack_shape

    def _create_one_to_one_map(self):
        """
        The target positions for all plates in a container must be equal,
        otherwise one-to-one sorting is aborted.
        """

        sr_map = dict() # stock rack position onto rack position
        for pool, container in self.stock_tube_containers.iteritems():
            rack_pos = None
            tts = self.__transfer_targets[pool]
            for plate_pos in container.get_all_target_positions():
                trg_pos = plate_pos.rack_position
                if rack_pos is None:
                    trg_pos = rack_pos
                elif not trg_pos == rack_pos:
                    return None
            if sr_map.has_key(rack_pos): return None
            sr_pos = StockRackPosition(rack_position=rack_pos,
                           molecule_design_pool=pool,
                           tube_barcode=container.tube_candidate.tube_barcode,
                           transfer_targets=tts)
            sr_map[rack_pos] = sr_pos

        return sr_map

    def _add_source_position(self, rack_pos, working_pos):
        """
        Creates a new stock rack position. The transfer targets have already
        been created before during hash value determination.
        """
        pool = working_pos.molecule_design_pool
        tts = self.__transfer_targets[pool]
        tube_barcode = self.stock_tube_containers[pool].tube_candidate.\
                       tube_barcode
        sr_pos = StockRackPosition(rack_position=rack_pos, transfer_targets=tts,
                        molecule_design_pool=pool, tube_barcode=tube_barcode)
        return sr_pos


class LabIsoXL20WorklistWriter(BaseXL20WorklistWriter):
    """
    This tool writes a worklist for the XL20 (tube handler) for a particular
    stock rack in the lab ISO process.

    **Return Value:** the XL20 worklist as stream
    """
    NAME = 'Lab ISO XL20 Worklist Writer'

    def __init__(self, log, rack_barcode, stock_rack_layout,
                 stock_tube_containers):
        """
        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param log: The barcode of the target rack (= the stock rack).
        :type log: :class:`basestring`

        :param stock_rack_layout: Contains the target positions for each pool.
        :type stock_rack_layout: :class:`StockRackLayout`

        :param stock_tube_containers: The stock tube container for each pool
            in the layout.
        :type stock_tube_containers: map
        """
        BaseXL20WorklistWriter.__init__(self, log=log)

        #: The barcode of the target rack (= the stock rack).
        self.rack_barcode = rack_barcode
        #: Contains the target positions for each pool.
        self.stock_rack_layout = stock_rack_layout
        #: The stock tube container for each pool in the layout.
        self.stock_tube_containers = stock_tube_containers

    def _check_input(self):
        self._check_input_class('destination rack barcode', self.rack_barcode,
                                basestring)
        self._check_input_class('stock rack layout', self.stock_rack_layout,
                                StockRackLayout)
        self._check_input_map_classes(self.stock_tube_containers,
                    'stock tube container map', 'pool', MoleculeDesignPool,
                    'stock tube container', StockTubeContainer)

    def _store_column_values(self):
        """
        The target positions are stored in the layout, the source data is
        stored in the containers. The data can be combined via the pool.
        """
        no_container = []

        for sr_pos in self.stock_rack_layout.get_sorted_working_positions():
            pool = sr_pos.molecule_design_pool
            if not self.stock_tube_containers.has_key(pool):
                no_container.append(pool.id)
                continue
            container = self.stock_tube_containers[pool]
            tube_candidate = container.tube_candidate
            self._source_position_values.append(tube_candidate.rack_position)
            self._source_rack_values.append(tube_candidate.rack_barcode)
            self._tube_barcode_values.append(tube_candidate.tube_barcode)
            self._dest_rack_values.append(self.rack_barcode)
            self._dest_position_values.append(sr_pos.rack_position)


class LabIsoXL20SummaryWriter(TxtWriter):
    """
    This tool generates an summary about the XL20 runs scheduled for this
    ISO or ISO job.

    **Return Value:** The summary as stream (TXT)
    """
    NAME = 'Lab ISO XL20 Summary Writer'

    #: The main headline of the file.
    BASE_MAIN_HEADER = 'XL20 Worklist Generation Report / %s / %s'
    #: The header text for the general section.
    GENERAL_HEADER = 'General Settings'
    #: This line presents the ISO or ISO job label.
    LABEL_LINE = '%s: %s'
    #: To be filled into the :attr:`LABEL_LINE` if the report is created for
    #: an ISO.
    ISO_MARKER = 'ISO'
    #: To be filled into the :attr:`LABEL_LINE` if the report is created for
    #: an ISO job.
    ISO_JOB_MARKER = 'ISO job'
    #: This line presents the total number of stock tubes used.
    TUBE_NO_BASE_LINE = 'Total number of tubes: %i'
    #: This is title for the volumes section (part of the \'general\' section).
    VOLUME_TITLE = 'Volumes'
    #: The volume part of the general section body.
    VOLUME_BASE_LINE = '%.1f ul: %s'

    #: The header text for the destination racks section.
    DESTINATION_RACKS_HEADER = 'Destination Racks'
    #: The body for the destination racks section.
    DESTINATION_RACK_BASE_LINE = '%s: %s (number of tubes: %i%s)'
    #: Is added to the destination base line if the stock rack is a sector
    #: stock rack.
    DESTINATION_SECTOR_ADDITION = ', sector: %s'

    #: The header text for the excluded racks section.
    EXCLUDED_RACKS_HEADER = 'Excluded Racks'
    #: The body for the excluded racks section.
    EXCLUDED_RACKS_BASE_LINE = '%s'
    #: Is used if there are no exlcuded racks.
    NO_EXCLUDED_RACKS_MARKER = 'no excluded racks'

    #: The header text for the  requested tubes section.
    REQUESTED_TUBES_HEADER = 'Requested Tubes'
    #: The body for the requested tubes section.
    REQUESTED_TUBES_BASE_LINE = '%s'
    #: Is used if no tubes have been requested.
    NO_REQUESTED_TUBES_MARKER = 'no requested tubes'

    #: The header for the source racks section.
    SOURCE_RACKS_HEADER = 'Source Racks'
    #: The body for the source racks section.
    SOURCE_RACKS_BASE_LINE = '%s (%s)'

    #: The header for the warning section.
    WARNING_HEADER = 'Warnings'
    #: The body for the warnings section.
    WARNING_BASE_LINE = '%s'
    #: Is used if no warnings have occurred.
    NO_WARNING_MARKER = 'no warnings'

    def __init__(self, log, entity, stock_tube_containers,
                 stock_rack_layouts, excluded_racks, requested_tubes):
        """
        Constructor:

        :param log: The ThelmaLog you want to write in.
        :type log: :class:`thelma.ThelmaLog`

        :param entity: The ISO or the ISO job for which to generate the summary.
        :type entity: :class:`LabIso` or :class:`IsoJob`

        :param stock_tube_containers: Contain the tube candidates (= tube
            transfer source) data mapped onto stock rack markers.
        :type stock_tube_containers: map

        :param stock_rack_layouts: Contain the target positions for each pool
             mapped onto stock rack markers.
        :type stock_rack_layouts: map

        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for molecule design picking.
        :type excluded_racks: A list of rack barcodes

        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of rack barcodes.
        """
        TxtWriter.__init__(self, log=log)

        #: The ISO or the ISO job for which to generate the summary.
        self.entity = entity
        #: A list of barcodes from stock racks that shall not be used for
        #: molecule design picking.
        self.excluded_racks = excluded_racks
        if excluded_racks is None: self.excluded_racks = []
        #: A list of barcodes from stock tubes that are supposed to be used.
        self.requested_tubes = requested_tubes
        if requested_tubes is None: self.requested_tubes = []
        #: Contain the tube candidates (= tube transfer source) data.
        self.stock_tube_containers = stock_tube_containers
        #: Contains the target positions for each pool.
        self.stock_rack_layouts = stock_rack_layouts

    def _check_input(self):
        if not isinstance(self.entity, (LabIso, IsoJob)):
            msg = 'The entity must either be a %s or an %s object ' \
                  '(obtained: %s)!' % (LabIso.__name__, IsoJob.__name__,
                                       self.entity.__class__.__name__)
            self.add_error(msg)
        self._check_input_map_classes(self.stock_tube_containers,
                    'stock tube container map', 'pool', MoleculeDesignPool,
                    'stock tube container', StockTubeContainer)
        self._check_input_map_classes(self.stock_rack_layouts,
                    'stock rack layout map', 'stock rack marker', str,
                    'stock rack layout', StockRackLayout)
        self._check_input_list_classes('excluded rack', self.excluded_racks,
                                       basestring, may_be_empty=True)
        self._check_input_list_classes('requested tube', self.requested_tubes,
                                       basestring, may_be_empty=True)

    def _write_stream_content(self):
        """
        We have the following sections: General, destination racks,
        excluded racks, requested tubes, source racks, warnings.
        """
        self.add_debug('Write stream ...')

        self.__write_main_headline()
        self.__write_general_section()
        self.__write_destination_racks_section()
        self.__write_excluded_racks_section()
        self.__write_requested_tubes_section()
        self.__write_source_racks_section()
        self.__write_warning_section()

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
        Writes the GENERAL section.
        """
        self._write_headline(self.GENERAL_HEADER, preceding_blank_lines=1)

        volumes_part = self.__create_volumes_part()
        if isinstance(self.entity, LabIso):
            marker = self.ISO_MARKER
        else:
            marker = self.ISO_JOB_MARKER
        label_line = self.LABEL_LINE % (marker, self.entity.label)
        tube_line = self.TUBE_NO_BASE_LINE % (len(self.stock_tube_containers))

        general_lines = [label_line,
                         tube_line,
                         '',
                         self.VOLUME_TITLE,
                         volumes_part]
        self._write_body_lines(general_lines)

    def __create_volumes_part(self):
        """
        Creates the volumes part for the main section.
        """
        vol_map = dict()

        for container in self.stock_tube_containers.values():
            total_volume = container.get_total_required_volume()
            add_list_map_element(vol_map, total_volume, container.pool.id)

        volume_lines = []
        for volume, pool_ids in vol_map.iteritems():
            pool_list_string = ', '.join(
                                [str(pool_id) for pool_id in sorted(pool_ids)])
            volume_line = self.VOLUME_BASE_LINE % (volume, pool_list_string)
            volume_lines.append(volume_line)

        return LINEBREAK_CHAR.join(volume_lines)

    def __write_destination_racks_section(self):
        """
        Writes the destination rack section.
        """
        self._write_headline(self.DESTINATION_RACKS_HEADER)

        destination_lines = []

        if isinstance(self.entity, IsoJob):
            stock_racks = self.entity.iso_job_stock_racks
        else:
            stock_racks = self.entity.iso_stock_racks \
                          + self.entity.iso_sector_stock_racks

        for stock_rack in stock_racks:
            barcode = stock_rack.rack.barcode
            label = stock_rack.label
            values = LABELS.parse_rack_label(label)
            rack_marker = values[LABELS.MARKER_RACK_MARKER]
            layout = self.stock_rack_layouts[rack_marker]
            add = ''
            if isinstance(stock_rack, IsoSectorStockRack):
                add = self.DESTINATION_SECTOR_ADDITION % (
                                                    stock_rack.sector_index + 1)
            line = self.DESTINATION_RACK_BASE_LINE % (stock_rack.label, barcode,
                                                      len(layout), add)
            destination_lines.append(line)
        self._write_body_lines(line_list=destination_lines)

    def __write_excluded_racks_section(self):
        """
        Writes the excluded racks section.
        """
        self._write_headline(self.EXCLUDED_RACKS_HEADER)

        if len(self.excluded_racks) < 1:
            lines = [self.EXCLUDED_RACKS_BASE_LINE \
                     % (self.NO_EXCLUDED_RACKS_MARKER)]
        else:
            lines = []
            for rack in self.excluded_racks:
                lines.append(self.EXCLUDED_RACKS_BASE_LINE % (rack))

        self._write_body_lines(line_list=lines)

    def __write_requested_tubes_section(self):
        """
        Writes the requested tubes section.
        """
        self._write_headline(self.REQUESTED_TUBES_HEADER)

        if self.requested_tubes is None or len(self.requested_tubes) < 1:
            lines = [self.REQUESTED_TUBES_BASE_LINE \
                     % (self.NO_REQUESTED_TUBES_MARKER)]
        else:
            lines = []
            for tube in self.requested_tubes:
                lines.append(self.REQUESTED_TUBES_BASE_LINE % (tube))

        self._write_body_lines(lines)

    def __write_source_racks_section(self):
        """
        Writes the source rack section.
        """
        self._write_headline(self.SOURCE_RACKS_HEADER)

        location_map = dict()
        for container in self.stock_tube_containers.values():
            tube_candidate = container.tube_candidate
            rack_barcode = tube_candidate.rack_barcode
            if location_map.has_key(rack_barcode): continue
            location = tube_candidate.location
            if location is None: location = 'unknown location'
            location_map[rack_barcode] = location

        lines = []
        for rack_barcode in sorted(location_map.keys()):
            location = location_map[rack_barcode]
            line = self.SOURCE_RACKS_BASE_LINE % (rack_barcode, location)
            lines.append(line)

        self._write_body_lines(lines)

    def __write_warning_section(self):
        """
        Writes the warning section.
        """
        self._write_headline(self.WARNING_HEADER)

        warnings = self.log.get_messages()
        if len(warnings) < 1:
            lines = [self.WARNING_BASE_LINE % (self.NO_WARNING_MARKER)]
        else:
            lines = []
            for warning in warnings:
                lines.append(self.WARNING_BASE_LINE % (warning))

        self._write_body_lines(lines)
