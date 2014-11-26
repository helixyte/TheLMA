"""
The rack recyler allows to reuse stock racks.

AAB
"""
from thelma.automation.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.tools.iso.base import StockRackLayout
from thelma.automation.tools.iso.base import StockRackPosition
from thelma.automation.tools.iso.lab.base import LABELS
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.iso.lab.stockrack.base \
    import _StockRackAssignerIsoJob
from thelma.automation.tools.iso.lab.stockrack.base \
    import _StockRackAssignerLabIso
from thelma.automation.tools.iso.lab.stockrack.base import _StockRackAssigner
from thelma.automation.tools.stock.base import STOCK_DEAD_VOLUME
from thelma.automation.tools.stock.tubepicking import TubeCandidate
from thelma.automation.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.utils.base import add_list_map_element
from thelma.automation.utils.base import are_equal_values
from thelma.automation.utils.base import get_nested_dict
from thelma.automation.utils.base import get_trimmed_string
from thelma.automation.utils.base import is_smaller_than
from thelma.automation.utils.racksector import RackSectorTranslator
from thelma.entities.sample import StockSample

__docformat__ = 'reStructuredText en'

__all__ = ['_StockRackRecycler']


class _StockRackRecycler(_StockRackAssigner):
    """
    Assigns existing racks (with the tubes already in place) as stock
    racks for a lab ISO or ISO job entity.

    **Return Value:** The updated ISO job or ISO.
    """

    def __init__(self, entity, rack_barcodes, **kw):
        """
        Constructor:

        :param entity: The ISO or the ISO job to which to assign the racks.
        :type entity: :class:`LabIso` or :class:`IsoJob`
            (see :attr:`_ENTITY_CLS).

        :param rack_barcodes: The barcodes for the stock racks to be used.
        :type rack_barcodes: :class:`list`
        """
        _StockRackAssigner.__init__(self, entity=entity,
                                    rack_barcodes=rack_barcodes, **kw)

        #: The :class:`TubeCandidate` objects for each pool in the specified
        #: racks.
        self.__tube_candidates = None

        #: Stores the barcode for each stock rack marker.
        self._stock_rack_map = None

    def reset(self):
        _StockRackAssigner.reset(self)
        self.__tube_candidates = dict()
        self._stock_rack_map = dict()

    def _find_stock_tubes(self):
        """
        The racks must not container other tubes and volume and concentration
        for each tube must match the expected data. The position of the
        tubes is not checked, though.
        """
        self.add_debug('Check suggested stock racks ...')

        self.__create_tube_candidates()
        if not self.has_errors(): self.__check_and_assign_tube_candidates()
        if not self.has_errors(): self._check_position_contraints()

    def __create_tube_candidates(self):
        """
        Checks the tubes in the given racks and converts them into
        :class:`TubeCandidate` objects.

        Sample which are not stock samples or do not have a volume are ignored.
        The number of tubes found must match the number of stock tube
        containers.
        """
        no_stock_sample = dict()
        no_sample = dict()
        num_tubes = 0

        for barcode, rack in self._barcode_map.iteritems():
            for tube in rack.containers:
                stock_sample = tube.sample
                rack_pos = tube.rack_position
                num_tubes += 1
                tube_info = '%s (%s)' % (tube.barcode, rack_pos.label)
                if stock_sample is None:
                    add_list_map_element(no_sample, barcode, tube_info)
                    continue
                sample_vol = stock_sample.volume * VOLUME_CONVERSION_FACTOR
                if are_equal_values(sample_vol, 0):
                    add_list_map_element(no_sample, barcode, tube_info)
                    continue
                if not isinstance(stock_sample, StockSample):
                    add_list_map_element(no_stock_sample, barcode, tube_info)
                    continue
                pool = stock_sample.molecule_design_pool
                tc = TubeCandidate(pool_id=pool.id,
                                   rack_barcode=barcode,
                                   rack_position=rack_pos,
                                   tube_barcode=tube.barcode,
                                   concentration=stock_sample.concentration,
                                   volume=stock_sample.volume)
                self.__tube_candidates[pool] = tc

        if len(no_sample) > 0:
            rack_strs = []
            for barcode in sorted(no_sample.keys()):
                info_str = '%s (%s)' % (barcode, self._get_joined_str(
                                                 no_sample[barcode]))
                rack_strs.append(info_str)
            msg = 'In some racks there are empty tubes: %s. Please remove ' \
                  'them and try again.' % (' -- '.join(rack_strs))
            self.add_error(msg)
        if len(no_stock_sample) > 0:
            msg = 'The tubes in some of the racks you have specified contain ' \
                  'normal samples instead of stock samples. Talk to the ' \
                  'IT department, please. Details: %s.' \
                  % (self._get_joined_map_str(no_stock_sample))
            self.add_error(msg)

        exp_tube_num = len(self._stock_tube_containers)
        if not self.has_errors() and not exp_tube_num == num_tubes:
            msg = 'The number of tubes in the racks you have specified (%i) ' \
                  'is different from the expected one (%i). Remove all tubes ' \
                  'that are not required and add the missing ones or try ' \
                  'the generate a new stock rack.' % (num_tubes, exp_tube_num)
            self.add_error(msg)

    def __check_and_assign_tube_candidates(self):
        """
        Checks whether there is pool for each requested pool and whether
        volume and concentration match.
        """
        missing_pools = []
        invalid_conc = []
        invalid_vol = []

        for pool, container in self._stock_tube_containers.iteritems():
            if not self.__tube_candidates.has_key(pool):
                missing_pools.append(pool.id)
                continue
            candidate = self.__tube_candidates[pool]
            exp_stock_conc = pool.default_stock_concentration \
                             * CONCENTRATION_CONVERSION_FACTOR
            if not are_equal_values(candidate.concentration,
                                    exp_stock_conc):
                info = '%s (pool: %s, expected: %s nM, found: %s nM)' % (
                        candidate.tube_barcode, pool,
                        get_trimmed_string(exp_stock_conc),
                        get_trimmed_string(candidate.concentration))
                invalid_conc.append(info)
                continue
            required_vol = STOCK_DEAD_VOLUME \
                           + container.get_total_required_volume()
            if is_smaller_than(candidate.volume, required_vol):
                info = '%s (pool: %s, required: %s ul, found: %s ul)' % (
                        candidate.tube_barcode, pool,
                        get_trimmed_string(required_vol),
                        get_trimmed_string(candidate.volume))
                invalid_vol.append(info)
                continue
            container.tube_candidate = candidate

        if len(missing_pools) > 0:
            msg = 'Could not find tubes for the following pools: %s.' % (
                   self._get_joined_str(missing_pools, is_strs=False))
            self.add_error(msg)
        if len(invalid_conc) > 0:
            msg = 'The concentrations in some tubes do not match the ' \
                  'expected ones: %s.' % (self._get_joined_str(invalid_conc))
            self.add_error(msg)
        if len(invalid_vol) > 0:
            msg = 'The volumes in some tubes (dead volume included) are not ' \
                  'sufficient: %s.' % (self._get_joined_str(invalid_vol))
            self.add_error(msg)

    def _check_position_contraints(self):
        """
        Checks potential position constraints for the tube candidates
        (e.g. rack sector matching).
        Might allocate rack barcodes and rack markers.
        """
        raise NotImplementedError('Abstract method.')

    def _create_stock_rack_layouts(self):
        """
        Creates stock rack layout for each required rack (potential rack
        sector constraints are expected to be confirmed).
        The rack markers might not match the layout rack markers anymore
        but this does not matter, since further processing do not use the
        layout rack markers anymore.
        """
        marker_map = dict()
        for marker, rack_barcode in self._stock_rack_map.iteritems():
            marker_map[rack_barcode] = marker

        layouts = dict()

        used_rack_markers = set()
        for pool, container in self._stock_tube_containers.iteritems():
            tc = container.tube_candidate
            rack_barcode = tc.rack_barcode
            if marker_map.has_key(rack_barcode):
                rack_marker = marker_map[rack_barcode]
                if layouts.has_key(rack_barcode):
                    layout = layouts[rack_barcode]
                else:
                    layout = StockRackLayout()
                    layouts[rack_barcode] = layout
            else:
                rack_marker = container.stock_rack_marker
                if rack_marker in used_rack_markers:
                    nums = []
                    for marker in used_rack_markers:
                        value_parts = LABELS.parse_rack_marker(marker)
                        nums.append(value_parts[LABELS.MARKER_RACK_NUM])
                    new_num = max(nums) + 1
                    rack_marker = LABELS.create_rack_marker(LABELS.ROLE_STOCK,
                                                            new_num)
                marker_map[rack_barcode] = rack_marker
                layout = StockRackLayout()
                layouts[rack_barcode] = layout

            tts = []
            for plate_label, positions in container.plate_target_positions.\
                                          iteritems():
                if plate_label == LABELS.ROLE_FINAL:
                    trg_marker = plate_label
                else:
                    trg_marker = self._rack_containers[plate_label].rack_marker
                for plate_pos in positions:
                    tts.append(plate_pos.as_transfer_target(trg_marker))

            sr_pos = StockRackPosition(rack_position=tc.rack_position,
                                       molecule_design_pool=pool,
                                       tube_barcode=tc.tube_barcode,
                                       transfer_targets=tts)
            layout.add_position(sr_pos)

        for rack_barcode, marker in marker_map.iteritems():
            self._stock_rack_layouts[marker] = layouts[rack_barcode]
            if not self._stock_rack_map.has_key(marker):
                self._stock_rack_map[marker] = rack_barcode

    def _get_stock_rack_map(self):
        return self._stock_rack_map

    def _create_output(self):
        """
        There is nothing to be generated anymore. We only set the return value.
        """
        self.return_value = self.entity
        self.add_info('Stock racks assigning completed.')


class StockRackRecyclerIsoJob(_StockRackRecycler, _StockRackAssignerIsoJob):
    """
    Assigns existing racks (with the tubes already in place) as stock
    racks for a ISO job entity.

    **Return Value:** The updated ISO job.
    """
    NAME = 'Lab ISO Job Stock Rack Recycler'

    #pylint: disable=W0231
    def __init__(self, entity, rack_barcodes, **kw):
        """
        Constructor:

        :param entity: The ISO or the ISO job to which to assign the racks.
        :type entity: :class:`LabIso` or :class:`IsoJob`
            (see :attr:`_ENTITY_CLS).

        :param rack_barcodes: The barcodes for the stock racks to be used.
        :type rack_barcodes: :class:`list`
        """
        _StockRackRecycler.__init__(self, entity=entity,
                                    rack_barcodes=rack_barcodes, **kw)
    #pylint: enable=W0231

    def reset(self):
        _StockRackRecycler.reset(self)

    def _check_input(self):
        _StockRackRecycler._check_input(self)

    def _get_layouts(self):
        _StockRackAssignerIsoJob._get_layouts(self)

    def _find_starting_wells(self):
        _StockRackAssignerIsoJob._find_starting_wells(self)

    def _find_stock_tubes(self):
        _StockRackRecycler._find_stock_tubes(self)

    def _check_position_contraints(self):
        """
        All job samples are transferred with the BioMek, hence, there are
        no position constraints (although the layouts might not be optimized).
        """
        pass

    def _create_stock_rack_layouts(self):
        _StockRackRecycler._create_stock_rack_layouts(self)

    def _get_stock_transfer_pipetting_specs(self):
        return _StockRackAssignerIsoJob._get_stock_transfer_pipetting_specs(self)

    def _clear_entity_stock_racks(self):
        _StockRackAssignerIsoJob._clear_entity_stock_racks(self)

    def _create_stock_rack_entity(self, stock_rack_marker, base_kw):
        return _StockRackAssignerIsoJob._create_stock_rack_entity(self,
                                    stock_rack_marker, base_kw)

    def _create_output(self):
        _StockRackRecycler._create_output(self)


class StockRackRecyclerLabIso(_StockRackRecycler, _StockRackAssignerLabIso):
    """
    Assigns existing racks (with the tubes already in place) as stock
    racks for a lab ISO entity.

    **Return Value:** The updated lab ISO.
    """
    NAME = 'Lab ISO Stock Rack Recycler'

    #pylint: disable=W0231
    def __init__(self, entity, rack_barcodes, **kw):
        """
        Constructor:

        :param entity: The ISO or the ISO job to which to assign the racks.
        :type entity: :class:`LabIso` or :class:`IsoJob`
            (see :attr:`_ENTITY_CLS).

        :param rack_barcodes: The barcodes for the stock racks to be used.
        :type rack_barcodes: :class:`list`
        """
        _StockRackRecycler.__init__(self, entity=entity,
                                    rack_barcodes=rack_barcodes, **kw)
        self._complete_init()

        #: The :class:`RackSectorTranslator`s translating 384-well target
        #: plate positins into stock rack positions mapped onto source
        #: sector indices (for sector data only).
        self.__ssc_layout_map = None
    #pylint: enable=W0231

    def reset(self):
        _StockRackRecycler.reset(self)
        self.__ssc_layout_map = dict()

    def _check_input(self):
        _StockRackRecycler._check_input(self)

    def _get_layouts(self):
        _StockRackAssignerLabIso._get_layouts(self)

    def _find_stock_tubes(self):
        _StockRackRecycler._find_stock_tubes(self)

    def _check_position_contraints(self):
        """
        Samples that shall be transferred via the CyBio must be located in
        defined positions.
        If all positions are consistent, the stock rack barcodes and rack
        sectors are allocated.
        """
        inconsistent_sectors = []
        inconsistent_positions = []
        self._stock_rack_sectors = dict()

        expected_positions = self.__get_expected_sector_positions()
        if not expected_positions is None:
            for sector_index, sector_pools in expected_positions.iteritems():
                rack_barcode = None
                stock_rack_marker = None
                sector_positions = []
                for pool, exp_pos in sector_pools.iteritems():
                    container = self._stock_tube_containers[pool]
                    tc = container.tube_candidate
                    sector_positions.append(exp_pos)
                    if stock_rack_marker is None:
                        stock_rack_marker = container.stock_rack_marker
                    if rack_barcode is None:
                        rack_barcode = tc.rack_barcode
                    elif not rack_barcode == tc.rack_barcode:
                        inconsistent_sectors.append(sector_index)
                        break
                    if not exp_pos == tc.rack_position:
                        info = 'tube %s in rack %s (exp: %s, found: %s)' \
                               % (tc.tube_barcode, rack_barcode, exp_pos,
                                  tc.rack_position)
                        inconsistent_positions.append(info)
                        continue
                self._stock_rack_map[stock_rack_marker] = rack_barcode
                self._stock_rack_sectors[sector_index] = sector_positions

        if len(inconsistent_sectors) > 0:
            msg = 'The pools for the following sectors are spread over ' \
                  'several racks: %s!' % (self._get_joined_str(
                                          inconsistent_sectors, is_strs=False))
            self.add_error(msg)
        if len(inconsistent_positions) > 0:
            msg = 'The following tubes scheduled for the CyBio are located ' \
                  'in wrong positions: %s.' \
                   % (self._get_joined_str(inconsistent_positions))
            self.add_error(msg)

    def __get_expected_sector_positions(self):
        """
        Returns the expected position for each pool sorted by sector index.
        """
        inconsistent = []
        contains_non_sectors = False
        has_sectors = False
        expected_positions = dict()

        for pool, container in self._stock_tube_containers.iteritems():
            stock_rack_marker = container.stock_rack_marker
            for plate_label, positions in container.plate_target_positions.\
                                          iteritems():
                plate_layout = self._plate_layouts[plate_label]
                sector_positions = dict()
                for plate_pos in positions:
                    sector_index = plate_pos.sector_index
                    if sector_index is None:
                        contains_non_sectors = True
                        continue
                    elif not has_sectors:
                        has_sectors = True
                    add_list_map_element(sector_positions, sector_index,
                                         plate_pos)
                if len(sector_positions) < 1: continue
                exp_data = self.__get_expected_stock_rack_position(plate_layout,
                                                              sector_positions)
                if exp_data is None:
                    inconsistent.append(pool.id)
                else:
                    sector_index = exp_data[1]
                    self._stock_rack_sectors[stock_rack_marker] = sector_index
                    sector_pools = get_nested_dict(expected_positions,
                                                   sector_index)
                    exp_pos = exp_data[0]
                    sector_pools[pool] = exp_pos

        if contains_non_sectors and has_sectors:
            msg = 'The sector data for the layouts are inconsistent - some ' \
                  'sector indices for samples are None!'
            self.add_error(msg)
            return None
        if inconsistent:
            msg = 'The sector for the following pools are inconsistent ' \
                  'in the layouts: %s.' % (self._get_joined_str(inconsistent,
                                                                is_strs=False))
            self.add_error(msg)
            return None

        return expected_positions

    def __get_expected_stock_rack_position(self, plate_layout,
                                           sector_positions):
        """
        There can only be one positions, because otherwise the positions
        do not match the sectors.
        """
        stock_rack_positions = set()
        ref_sectors = set()

        for sector_index, positions in sector_positions.iteritems():
            ref_sectors.add(sector_index)
            if plate_layout.shape.name == RACK_SHAPE_NAMES.SHAPE_96:
                for plate_pos in positions:
                    stock_rack_positions.add(plate_pos.rack_position)

            else:
                if self.__ssc_layout_map.has_key(sector_index):
                    translator = self.__ssc_layout_map[sector_index]
                else:
                    translator = RackSectorTranslator(number_sectors=4,
                                    source_sector_index=sector_index,
                                    target_sector_index=0,
                                    behaviour=RackSectorTranslator.ONE_TO_MANY)
                    self.__ssc_layout_map[sector_index] = translator
                for plate_pos in positions:
                    base_msg = 'Error when trying to determine stock rack ' \
                               'position for position %s:' \
                               % (plate_pos.rack_position.label)
                    trans_pos = self._run_and_record_error(translator.translate,
                               base_msg, ValueError,
                               **dict(rack_position=plate_pos.rack_position))
                    if trans_pos is None: return None
                    stock_rack_positions.add(trans_pos)

        if len(stock_rack_positions) > 1: return None
        return (list(stock_rack_positions)[0], min(ref_sectors))

    def _create_stock_rack_layouts(self):
        _StockRackRecycler._create_stock_rack_layouts(self)

    def _get_stock_transfer_pipetting_specs(self):
        return _StockRackAssignerLabIso._get_stock_transfer_pipetting_specs(
                                                                        self)

    def _clear_entity_stock_racks(self):
        _StockRackAssignerLabIso._clear_entity_stock_racks(self)

    def _create_stock_rack_entity(self, stock_rack_marker, base_kw):
        return _StockRackAssignerLabIso._create_stock_rack_entity(self,
                                            stock_rack_marker, base_kw)

    def _create_output(self):
        _StockRackRecycler._create_output(self)
