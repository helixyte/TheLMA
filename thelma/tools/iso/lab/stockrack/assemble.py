"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Tools that assemble new stock racks for entities (using the XL20) involved
in ISO processing.

AAB
"""
from StringIO import StringIO
from datetime import datetime
from thelma.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.tools.semiconstants import get_positions_for_shape
from thelma.tools.dummies import XL20Dummy
from thelma.tools.iso.base import StockRackLayout
from thelma.tools.iso.base import StockRackPosition
from thelma.tools.iso.lab.base import LABELS
from thelma.tools.iso.lab.base import create_instructions_writer
from thelma.tools.stock.base import get_stock_rack_size
from thelma.tools.stock.base import get_stock_rack_shape
from thelma.tools.writers import merge_csv_streams
from thelma.tools.iso.lab.stockrack.base \
    import _StockRackAssignerIsoJob
from thelma.tools.iso.lab.stockrack.base \
    import _StockRackAssignerLabIso
from thelma.tools.iso.lab.stockrack.base import StockTubeContainer
from thelma.tools.iso.lab.stockrack.base import _StockRackAssigner
from thelma.tools.iso.lab.stockrack.tubepicking \
    import LabIsoXL20TubePicker
from thelma.tools.worklists.optimiser import BiomekLayoutOptimizer
from thelma.tools.worklists.optimiser import TransferItem
from thelma.tools.worklists.tubehandler import BaseXL20WorklistWriter
from thelma.tools.writers import LINEBREAK_CHAR
from thelma.tools.writers import TxtWriter
from thelma.tools.writers import create_zip_archive
from thelma.tools.utils.base import add_list_map_element
from thelma.tools.utils.base import get_trimmed_string
from thelma.tools.utils.layouts import FIXED_POSITION_TYPE
from thelma.tools.utils.racksector import RackSectorTranslator
from thelma.entities.iso import IsoSectorStockRack
from thelma.entities.iso import LabIso
from thelma.entities.job import IsoJob
from thelma.entities.moleculedesign import MoleculeDesignPool
from thelma.entities.rack import RackShape

__docformat__ = 'reStructuredText en'

__all__ = ['_StockRackAssembler',
           'StockRackAssemblerIsoJob',
           'StockRackAssemblerLabIso',
           'LabIsoXL20WorklistWriter',
           'LabIsoXL20SummaryWriter',
           'LabIsoStockTransferItem',
           'LabIsoStockRackOptimizer']


class _StockRackAssembler(_StockRackAssigner):
    """
    This tool generates a zip archive that contains worklists for the tube
    handler (XL20) and some overview and report files.
    With the files you can assemble the sotck racks for a lab ISO entity.

    If the :param:`include_dummy_output` flag is set, an additional file
    containing the output from the XL20 dummy writer is added.

    At this, it generate stock rack entities and conducts checks on DB level.
    The output is a zip archive

    **Return Value:** A zip archive with two files (worklist and reports)
    """

    #: The file name of the XL20 worklist file contains the entity label.
    FILE_NAME_XL20_WORKLIST = '%s_xl20_worklist.csv'
    #: The file name for the XL20 summary file contains the entity label.
    FILE_NAME_XL20_SUMMARY = '%s_xl20_summary.txt'
    #: The file name for the instructions contains the entity label.
    FILE_NAME_INSTRUCTIONS = '%s_instructions.txt'
    #: The dummy output file names contains the entity label.
    FILE_NAME_DUMMY = '%s_dummy_xl20_output.tpo'

    def __init__(self, entity, rack_barcodes,
                 excluded_racks=None, requested_tubes=None,
                 include_dummy_output=False, **kw):
        """
        Constructor:

        :param entity: The ISO or the ISO job for which to generate the files
            and the racks.
        :type entity: :class:`LabIso` or :class:`IsoJob`
            (see :attr:`_ENTITY_CLS).

        :param rack_barcodes: The barcodes for the destination racks (the
            rack the tubes shall be transferred to).
        :type rack_barcodes: list of barcodes (:class:`basestring`)

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
        _StockRackAssigner.__init__(self, entity=entity,
                                    rack_barcodes=rack_barcodes, **kw)

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

        #: Stores the stock tube container items for each required pool
        #: sorted by stock rack (marker).
        self._tubes_by_rack = dict()

        #: The stream for each generated file mapped onto file name.
        self.__stream_map = None
        #: The zip stream wrapped around the two files.
        self.__zip_stream = None

    def reset(self):
        _StockRackAssigner.reset(self)
        self._tubes_by_rack = dict()
        self.__stream_map = dict()
        self.__zip_stream = None

    def _check_input(self):
        _StockRackAssigner._check_input(self)
        self._check_input_class('"include dummy output" flag',
                                self.include_dummy_output, bool)
        self._check_input_list_classes('excluded rack', self.excluded_racks,
                                       basestring, may_be_empty=True)
        self._check_input_list_classes('requested tube', self.requested_tubes,
                                       basestring, may_be_empty=True)

    def _get_tube_racks(self):
        """
        The tube destination racks must be empty.
        """
        _StockRackAssigner._get_tube_racks(self)

        non_empty = []
        for barcode, rack in self._barcode_map.iteritems():
            if len(rack.containers) > 0:
                non_empty.append(str(barcode))

        if len(non_empty) > 0:
            non_empty.sort()
            msg = 'The following racks you have chosen are not empty: %s.' \
                  % (self._get_joined_str(non_empty))
            self.add_error(msg)

    def _find_stock_tubes(self):
        """
        Checks whether the schedule tubes are still sufficient. If not, the
        regarding tubes are replaced.
        """
        self.add_debug('Check stock tubes ...')

        picker = LabIsoXL20TubePicker(
                    stock_tube_containers=self._stock_tube_containers,
                    excluded_racks=self.excluded_racks,
                    requested_tubes=self.requested_tubes,
                    parent=self)

        self._stock_tube_containers = picker.get_result()
        if self._stock_tube_containers is None:
            msg = 'Error when trying to pick stock tubes.'
            self.add_error(msg)
        else:
            missing_pools = picker.get_missing_pools()
            if len(missing_pools) > 0:
                self._react_on_missing_pools(missing_pools)

    def _react_on_missing_pools(self, missing_pools):
        """
        Deals with molecule design pools for which there was no tube picked.
        """
        raise NotImplementedError('Abstract method.')

    def _create_stock_rack_layouts(self):
        """
        Before we can start generating the layouts, we have to sort the
        picked tubes. The positions for the tubes can be assigned freely
        (optimization is attempted).
        """
        self.__sort_tubes_into_stock_racks()
        self._find_stock_rack_layouts()

    def __sort_tubes_into_stock_racks(self):
        """
        Collects the stock tube containers for each stock rack. The referring
        data is stored in the plate position. We use the first plate position
        of each container - even if the data is inconsistent this does not
        matter because so far nothing else depends on it.
        """
        for container in self._stock_tube_containers.values():
            if container.tube_candidate is None: continue
            plate_pos = container.get_all_target_positions()[0]
            add_list_map_element(self._tubes_by_rack,
                                 plate_pos.stock_rack_marker, container)

    def _find_stock_rack_layouts(self):
        """
        Generates the actual :class:`StockRackLayout` and tries to find
        the best position for each tube.
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

        marker_map = dict()
        for plate_label, rack_container in self._rack_containers.iteritems():
            marker_map[plate_label] = rack_container.rack_marker
#            if rack_container.role == LABELS.ROLE_PREPARATION_ISO:
#                marker_map[]
#            else:
#                marker_map[plate_label] = rack_container.rack_marker


        container_map = self._sort_stock_tube_containers_by_pool(containers)
        optimizer = LabIsoStockRackOptimizer(
                                    stock_tube_containers=container_map,
                                    target_rack_shape=rack_shape,
                                    rack_marker_map=marker_map,
                                    parent=self)
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
            for pref_pos_key, score in pref_map.iteritems():
                if score_pos_map.has_key(score):
                    pool_map = score_pos_map[score]
                else:
                    pool_map = dict()
                    score_pos_map[score] = pool_map
                add_list_map_element(pool_map, pref_pos_key, pool)

        # assign preferred positions to pools if possible
        # FIXME: This is hideously inefficient.
        assigned_pools = dict()
        remaining_pools = set(pref_positions.keys())
        used_positions = set()
        for score in sorted(score_pos_map.keys()):
            pool_map = score_pos_map[score]
            for pref_pos_key, pools in pool_map.iteritems():
                pool_applicants = []
                for pool in pools:
                    if pool in remaining_pools:
                        pool_applicants.append(pool)
                if len(pool_applicants) < 1:
                    continue
                pool_applicants.sort(cmp=lambda p1, p2: cmp(p1.id, p2.id))
                pool = pool_applicants[0]
                pref_pos = pref_pos_key[-1]
                if not pref_pos in used_positions:
                    assigned_pools[pool] = pref_pos
                    remaining_pools.remove(pool)
                    used_positions.add(pref_pos)
        # Find positions for pools without preferred position or with
        # duplicate positions.
        remaining_positions = \
            sorted(set(get_positions_for_shape(RACK_SHAPE_NAMES.SHAPE_96))
                    .difference(used_positions))
        for pool in remaining_pools:
            if len(remaining_positions) > 0:
                rack_pos = remaining_positions.pop(0)
                assigned_pools[pool] = rack_pos
            # FIXME: Should this record an error if not all pools can be
            #        assigned to positions?
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
                      behaviour=RackSectorTranslator.MANY_TO_ONE)
            for pos96 in get_positions_for_shape(RACK_SHAPE_NAMES.SHAPE_96):
                pos384 = translator.translate(pos96)
                translation_map[pos384] = pos96

        pref_positions = dict() # the preferred rack positions for each pool
        transfer_targets = dict() # the transfer targets for each pool
        for container in containers:
            tts = []
            cnt_pref_positions = dict()
            for plate_label, positions in container.plate_target_positions.\
                                          iteritems():
                layout = self._plate_layouts[plate_label]
                # For some reason, the rack container map has the marker as
                # a key for final (aliquot) plates.
                if plate_label != LABELS.ROLE_FINAL:
                    trg_plate_marker = \
                        self._rack_containers[plate_label].rack_marker
                else:
                    trg_plate_marker = plate_label
                translate = (layout.shape.name == RACK_SHAPE_NAMES.SHAPE_384)
                for plate_pos in positions:
                    rack_pos = plate_pos.rack_position
                    tts.append(plate_pos.as_transfer_target(trg_plate_marker))
                    if translate:
                        pref_pos = translation_map[rack_pos]
                    else:
                        pref_pos = rack_pos
                    key = (trg_plate_marker, pref_pos)
                    if not cnt_pref_positions.has_key(key):
                        cnt_pref_positions[key] = 0
                    cnt_pref_positions[key] += 1
            transfer_targets[container.pool] = tts
            pref_positions[container.pool] = cnt_pref_positions

        return pref_positions, transfer_targets

    def _get_stock_rack_map(self):
        """
        The racks are simply sorted by barcode.
        """
        sorted_barcodes = []
        for barcode in sorted(self.rack_barcodes):
            sorted_barcodes.append(barcode)
        stock_rack_map = dict()
        for stock_rack_marker in sorted(self._stock_rack_layouts.keys()):
            barcode = sorted_barcodes.pop(0)
            stock_rack_map[stock_rack_marker] = barcode
        return stock_rack_map

    def _create_output(self):
        """
        The output is a zip archive stream containing XL20 worklists and
        some report files.
        """
        self.__write_streams()
        if not self.has_errors():
            self.__create_zip_archive()
            self.return_value = self.__zip_stream
            self.add_info('File generation completed.')

    def __write_streams(self):
        """
        Writes the XL20 worklists, XL20 summary, the instructions file
        (if requested) the dummy XL20 output file.
        """
        self.add_debug('Write streams ...')

        # XL20 worklists and dummy output
        xl20_worklists = dict()
        for rack_container in self._rack_containers.values():
            if not rack_container.role == LABELS.ROLE_STOCK: continue
            rack_marker = rack_container.rack_marker
            barcode = rack_container.rack.barcode
            container_map = self._sort_stock_tube_containers_by_pool(
                                            self._tubes_by_rack[rack_marker])
            xl20_writer = LabIsoXL20WorklistWriter(
                      rack_barcode=barcode,
                      stock_rack_layout=self._stock_rack_layouts[rack_marker],
                      stock_tube_containers=container_map,
                      parent=self)
            msg = 'Error when trying to write XL20 worklist stream for ' \
                  'rack "%s"!' % (rack_marker)
            xl20_stream = self.__generate_stream(xl20_writer, None,
                                                 error_msg=msg)
            if xl20_stream is None: continue
            xl20_worklists[rack_marker] = xl20_stream
        merged_stream = merge_csv_streams(xl20_worklists)
        wl_fn = self.FILE_NAME_XL20_WORKLIST % (self.entity.label)
        self.__stream_map[wl_fn] = merged_stream

        # dummy output
        if self.include_dummy_output:
            dummy_writer = XL20Dummy(xl20_worklist_stream=merged_stream,
                                     parent=self)
            dummy_msg = 'Error when trying to write dummy output stream for ' \
                        'rack "%s"!' % (rack_marker)
            self.__generate_stream(dummy_writer, self.FILE_NAME_DUMMY,
                                   dummy_msg)


        # XL20 summary
        summary_writer = LabIsoXL20SummaryWriter(
                    entity=self.entity,
                    stock_tube_containers=self._stock_tube_containers,
                    stock_rack_layouts=self._stock_rack_layouts,
                    excluded_racks=self.excluded_racks,
                    requested_tubes=self.requested_tubes,
                    parent=self)
        summary_msg = 'Error when trying to write summary stream!'
        self.__generate_stream(summary_writer, self.FILE_NAME_XL20_SUMMARY,
                               summary_msg)

        # Instructions
        kw = dict(entity=self.entity,
                  iso_request=self._iso_request,
                  rack_containers=self._rack_containers.values(),
                  parent=self)
        instructions_writer = create_instructions_writer(**kw)
        instruction_msg = 'Error when trying to write instruction stream!'
        self.__generate_stream(instructions_writer,
                               self.FILE_NAME_INSTRUCTIONS, instruction_msg)

    def __generate_stream(self, writer, name_suffix, error_msg):
        """
        Helper method running the passed writer and recording an error message
        if the run fails.
        """
        file_stream = writer.get_result()
        if file_stream is None:
            self.add_error(error_msg)
            return None
        elif not name_suffix is None:
            file_name = name_suffix % (self.entity.label)
            self.__stream_map[file_name] = file_stream
        return file_stream

    def __create_zip_archive(self):
        """
        Creates a zip archive containing the generated streams.
        """
        self.__zip_stream = StringIO()
        create_zip_archive(self.__zip_stream, stream_map=self.__stream_map)


class StockRackAssemblerIsoJob(_StockRackAssembler, _StockRackAssignerIsoJob):
    """
    Generates XL20 files and overview files that serve the assembly of
    new lab ISO job stock racks.

    **Return Value:** A zip archive with two files (worklist and reports);
    """
    NAME = 'Lab ISO Job Stock Rack Assembler'

    #pylint: disable=W0231
    def __init__(self, iso_job, rack_barcodes,
                 excluded_racks=None, requested_tubes=None,
                 include_dummy_output=False, **kw):
        """
        Constructor:

        :param iso_job: The ISO job for which to assemble the racks.
        :type iso_job: :class:`IsoJob`

        :param rack_barcodes: The barcodes for the destination racks (the
            rack the tubes shall be transferred to).
        :type rack_barcodes: list of barcodes (:class:`basestring`)

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
        _StockRackAssembler.__init__(self, entity=iso_job,
                                     rack_barcodes=rack_barcodes,
                                     excluded_racks=excluded_racks,
                                     requested_tubes=requested_tubes,
                                     include_dummy_output=include_dummy_output,
                                     **kw)
        #pylint: disable=W0231

    def reset(self):
        _StockRackAssembler.reset(self)

    def _check_input(self):
        _StockRackAssembler._check_input(self)

    def _get_layouts(self):
        _StockRackAssignerIsoJob._get_layouts(self)

    def _find_starting_wells(self):
        _StockRackAssignerIsoJob._find_starting_wells(self)

    def _find_stock_tubes(self):
        _StockRackAssembler._find_stock_tubes(self)

    def _react_on_missing_pools(self, missing_pools):
        """
        All pools are controls. Thus, pools without stock tube are not allowed.
        """
        msg = 'For some control molecule design pools there are no valid ' \
              'stock tubes available: %s.' \
               % (self._get_joined_str(missing_pools, is_strs=False))
        self.add_error(msg)

    def _create_stock_rack_layouts(self):
        _StockRackAssembler._create_stock_rack_layouts(self)

    def _find_stock_rack_layouts(self):
        """
        Job samples are always transferred with the Biomek.
        """
        self._create_stock_rack_layouts_with_biomek()

    def _get_stock_transfer_pipetting_specs(self): # pylint:disable=W0201
        return _StockRackAssignerIsoJob._get_stock_transfer_pipetting_specs(
                                                                        self)

    def _clear_entity_stock_racks(self):
        _StockRackAssignerIsoJob._clear_entity_stock_racks(self)

    def _create_stock_rack_entity(self, stock_rack_marker, base_kw):
        return _StockRackAssignerIsoJob._create_stock_rack_entity(self, #pylint: disable=W0201
                                        stock_rack_marker, base_kw)

    def _create_output(self):
        _StockRackAssembler._create_output(self)


class StockRackAssemblerLabIso(_StockRackAssembler, _StockRackAssignerLabIso):
    """
    Generates XL20 files and overview files that serve the assembly of
    new lab ISO stock racks.

    **Return Value:** A zip archive with two files (worklist and reports);
    """
    NAME = 'Lab ISO Stock Rack Assembler'

    #pylint: disable=W0231, W0201
    def __init__(self, lab_iso, rack_barcodes,
                 excluded_racks=None, requested_tubes=None,
                 include_dummy_output=False, **kw):
        """
        Constructor:

        :param lab_iso: The ISO job for which to assemble the racks.
        :type lab_iso: :class:`IsoJob`

        :param rack_barcodes: The barcodes for the destination racks (the
            rack the tubes shall be transferred to).
        :type rack_barcodes: list of barcodes (:class:`basestring`)

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
        _StockRackAssembler.__init__(self, entity=lab_iso,
                                     rack_barcodes=rack_barcodes,
                                     excluded_racks=excluded_racks,
                                     requested_tubes=requested_tubes,
                                     include_dummy_output=include_dummy_output,
                                     **kw)
        self._complete_init()
        #pylint: disable=W0231, W0201

    def reset(self):
        _StockRackAssembler.reset(self)
        _StockRackAssignerLabIso.reset(self)

    def _check_input(self):
        _StockRackAssembler._check_input(self)
        _StockRackAssignerLabIso._check_input(self)

    def _get_layouts(self):
        _StockRackAssignerLabIso._get_layouts(self)

    def _find_stock_tubes(self):
        _StockRackAssembler._find_stock_tubes(self)

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
                   % (self._get_joined_str(fixed_pools, is_strs=False))
            self.add_error(msg)
        elif len(floating_pools) > 0:
            msg = 'Unable to find stock tubes for the following floating ' \
                  'positions: %s. The positions are put back into the queue.' \
                  % (self._get_joined_str(floating_pools, is_strs=False))
            self.add_warning(msg)
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

    def _find_stock_rack_layouts(self):
        """
        If the starting wells have sector data, there is one stock rack for
        each (distinct) rack sector (several rack can share the same pool
        combination).
        Otherwise the samples are transferred independently (with the BioMek).
        """
        self.__get_sectors_for_stock_racks()

        if len(self._stock_rack_sectors) < 1:
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
            self.__create_sector_stock_rack_layouts()

    def __get_sectors_for_stock_racks(self):
        """
        The target rack sectors for a rack marker must be consistent for all
        stock tube containers for this rack. *None* is a valid sector index.
        Controls with a
        """
        self._stock_rack_sectors = dict()
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
                self._stock_rack_sectors[rack_marker] = ref_sectors

        if len(inconsistent) > 0:
            msg = 'The planned sector indices for the following stock racks ' \
                  'are inconsistent: %s!' % (self._get_joined_str(inconsistent))
            self.add_error(msg)

    def __create_sector_stock_rack_layouts(self):
        """
        For an 384-well target plate, we need to translate the target
        position. In 96-well layouts, translation is not required.
        """
        for rack_marker, sectors in self._stock_rack_sectors.iteritems():
            layout = StockRackLayout()
            containers = self._tubes_by_rack[rack_marker]
            sector_index = sorted(sectors)[0]
            translator = RackSectorTranslator(number_sectors=4,
                      source_sector_index=sector_index, target_sector_index=0,
                      behaviour=RackSectorTranslator.ONE_TO_MANY)
            for container in containers:
                tts = []
                stock_pos = None
                for plate_label, positions in container.plate_target_positions.\
                                          iteritems():
                    shape = self._plate_layouts[plate_label].shape
                    translate = True
                    if shape.name == RACK_SHAPE_NAMES.SHAPE_96:
                        translate = False
                    if self._rack_containers.has_key(plate_label):
                        trg_marker = self._rack_containers[plate_label].\
                                     rack_marker
                    else:
                        trg_marker = LABELS.ROLE_FINAL
                    for plate_pos in positions:
                        tts.append(plate_pos.as_transfer_target(trg_marker))
                        if not stock_pos is None: continue
                        if translate:
                            stock_pos = translator.translate(
                                                      plate_pos.rack_position)
                        else:
                            stock_pos = plate_pos.rack_position
                    tube_barcode = container.tube_candidate.tube_barcode
                    sr_pos = StockRackPosition(rack_position=stock_pos,
                                   molecule_design_pool=container.pool,
                                   tube_barcode=tube_barcode,
                                   transfer_targets=tts)
                    layout.add_position(sr_pos)
            if len(layout) > 0:
                self._stock_rack_layouts[rack_marker] = layout

    def _get_stock_transfer_pipetting_specs(self):
        return _StockRackAssignerLabIso._get_stock_transfer_pipetting_specs(
                                                                        self)

    def _clear_entity_stock_racks(self):
        _StockRackAssignerLabIso._clear_entity_stock_racks(self)

    def _create_stock_rack_entity(self, stock_rack_marker, base_kw):
        return _StockRackAssignerLabIso._create_stock_rack_entity(self,
                                        stock_rack_marker, base_kw)


class LabIsoXL20WorklistWriter(BaseXL20WorklistWriter):
    """
    This tool writes a worklist for the XL20 (tube handler) for a particular
    stock rack in the lab ISO process.

    **Return Value:** the XL20 worklist as stream
    """
    NAME = 'Lab ISO XL20 Worklist Writer'

    def __init__(self, rack_barcode, stock_rack_layout,
                 stock_tube_containers, parent=None):
        """
        Constructor.

        :param stock_rack_layout: Contains the target positions for each pool.
        :type stock_rack_layout: :class:`StockRackLayout`
        :param stock_tube_containers: The stock tube container for each pool
            in the layout.
        :type stock_tube_containers: map
        """
        BaseXL20WorklistWriter.__init__(self, parent=parent)
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
    VOLUME_BASE_LINE = '%s ul: %s'
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

    def __init__(self, entity, stock_tube_containers,
                 stock_rack_layouts, excluded_racks, requested_tubes,
                 parent=None):
        """
        Constructor.

        :param entity: The ISO or the ISO job for which to generate the summary.
        :type entity: :class:`LabIso` or :class:`IsoJob`
        :param dict stock_tube_containers: Contain the tube candidates (= tube
            transfer source) data mapped onto pools.
        :param dict stock_rack_layouts: Contain the target positions for each pool
             mapped onto stock rack markers.
        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for molecule design picking.
        :type excluded_racks: A list of rack barcodes
        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of rack barcodes.
        """
        TxtWriter.__init__(self, parent=parent)
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
        excluded racks, requested tubes, source racks.
        """
        self.add_debug('Write stream ...')

        self.__write_main_headline()
        self.__write_general_section()
        self.__write_destination_racks_section()
        self.__write_excluded_racks_section()
        self.__write_requested_tubes_section()
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
            pool_list_string = self._get_joined_str(pool_ids, is_strs=False)
            volume_line = self.VOLUME_BASE_LINE % (get_trimmed_string(volume),
                                                   pool_list_string)
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

        stock_racks.sort(cmp=lambda sr1, sr2: cmp(sr1.rack.barcode,
                                                  sr2.rack.barcode))
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
            location = container.location
            if location is None: location = 'unknown location'
            location_map[rack_barcode] = location

        lines = []
        for rack_barcode in sorted(location_map.keys()):
            location = location_map[rack_barcode]
            line = self.SOURCE_RACKS_BASE_LINE % (rack_barcode, location)
            lines.append(line)

        self._write_body_lines(lines)


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

    def __init__(self, stock_tube_containers, target_rack_shape,
                 rack_marker_map, parent=None):
        """
        Constructor.

        :param dict stock_tube_containers: The stock tube containers mapped
            onto pools. Each container must have a tube candidate.
        :param target_rack_shape: The shape of the target plates.
        :type target_rack_shape: :class:`thelma.entities.rack.RackShape`
        :param str stock_rack_marker: The rack marker for each rack label that
            can occur in the :attr:`stock_tube_containers`.
        :param dict rack_marker_map: The rack marker for each plate label that
            can occur in the stock tube containers.
        """
        BiomekLayoutOptimizer.__init__(self, parent=parent)
        #: The stock tube containers mapped onto pools.
        self.stock_tube_containers = stock_tube_containers
        #: The shape of the target plates.
        self.target_rack_shape = target_rack_shape
        #: The rack marker for each plate label that can occur in the
        #: :attr:`stock_tube_containers`.
        self.rack_marker_map = rack_marker_map
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
        self._check_input_map_classes(self.rack_marker_map, 'rack marker map',
                    'plate label', basestring, 'rack marker', basestring)

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
            for plate_label, positions in container.plate_target_positions.\
                                                                iteritems():
                if plate_label == LABELS.ROLE_FINAL:
                    rack_marker = plate_label
                else:
                    rack_marker = self.rack_marker_map[plate_label]
                if column_maps.has_key(plate_label):
                    column_map = column_maps[plate_label]
                else:
                    column_map = dict()
                    column_maps[plate_label] = column_map
                    pos_counts[plate_label] = 0
                for plate_pos in positions:
                    trg_pos = plate_pos.rack_position
                    col_index = trg_pos.column_index
                    add_list_map_element(column_map, col_index, plate_pos)
                    pos_counts[plate_label] += 1
                    tts.append(plate_pos.as_transfer_target(rack_marker))
            self.__transfer_targets[pool] = tts

        if len(no_tube_candidate) > 0:
            msg = 'There are no stock tube candidates for the following ' \
                  'pools: %s!' % (self._get_joined_str(no_tube_candidate,
                                                       is_strs=False))
            self.add_error(msg)
        else:
            plates_by_count = dict()
            for plate, pos_count in pos_counts.iteritems():
                add_list_map_element(plates_by_count, pos_count, plate)
            for pos_count in sorted(plates_by_count.keys(), reverse=True):
                plates = plates_by_count[pos_count]
                for plate in plates:
                    i = len(self._column_maps)
                    column_map = column_maps[plate]
                    self._column_maps[i] = column_map

    def _init_source_layout(self, source_layout_shape):
        """
        Stock rack layouts can only be 96-well layouts.
        """
        if not source_layout_shape == get_stock_rack_shape():
            msg = 'The number of source positions (%i) exceeds the number ' \
                  'of available positions in a stock rack (%i). This is a ' \
                  'programming error. Talk to the IT department, please.' \
                   % (len(self._hash_values), get_stock_rack_size())
            self.add_error(msg)
        return self.SOURCE_LAYOUT_CLS()

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
                    rack_pos = trg_pos
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
        self._source_layout.add_position(sr_pos)
        return sr_pos
