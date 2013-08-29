"""
Deals with the final tube picking for lab ISOs.

AAB
"""
from thelma.automation.tools.base import SessionTool
from thelma.automation.tools.stock.tubepicking import TubePoolQuery
from thelma.automation.tools.utils.base import add_list_map_element
from thelma.models.moleculedesign import MoleculeDesignPool
from thelma.automation.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import are_equal_values
from thelma.automation.tools.stock.tubepicking import TubePickingQuery
from thelma.automation.tools.utils.base import create_in_term_for_db_queries
from thelma.automation.tools.utils.base import get_trimmed_string
from thelma.automation.tools.stock.base import STOCK_DEAD_VOLUME
from thelma.automation.tools.utils.base import is_smaller_than
from thelma.automation.tools.stock.tubepicking import SinglePoolQuery
from thelma.automation.tools.stock.base import RackLocationQuery
from thelma.automation.tools.iso.lab.base import LABELS


__docformat__ = 'reStructuredText en'

__all__ = ['StockTubeContainer',
           'LabIsoXL20TubePicker',
           '_LabIsoTubeConfirmationQuery']


class StockTubeContainer(object):
    """
    Helper storage class representing a (requested and/or picked) stock tube.
    """

    def __init__(self, pool, position_type, requested_tube_barcode,
                 expected_rack_barcode, final_position_copy_number):
        """
        Constructor:

        :param pool: The molecule design pool the stock tube sample should
            contain.
        :type pool: :class:`thelma.models.moleculedesign.MoleculeDesignPool`

        :param position_type: The types of the positions in the layouts
            (must be the same for all positions).
        :type position_type: see :class:`MoleculeDesignPoolParameters`

        :param requested_tube_barcode: The barcode of the tube scheduled
            by the :class:`LabIsoBuilder`.
        :type requested_tube_barcode: :class:`basestring`

        :param expected_rack_barcode: The barcode of the rack that the
            scheduled tube is expected in.
        :type expected_rack_barcode: :class:`basestring`

        :param final_position_copy_number: The number of target copies for
            each final plate position (number of ISOs for ISO jobs).
        :type final_position_copy_number: positive :class:`int`
        """
        #: The molecule design pool the stock tube sample should contain.
        self.__pool = pool
        #: The types of the layouts must be the same for all positions.
        self.__position_type = position_type
        #: The barcode of the tube scheduled by the :class:`LabIsoBuilder`.
        self.requested_tube_barcode = requested_tube_barcode
        #: The barcode of the rack that the scheduled tube is expected in.
        self.__exp_rack_barcode = expected_rack_barcode
        #: The target preparation plate position mapped onto plate labels.
        self.__prep_positions = dict()
        #: The target final plate positions.
        self.__final_positions = []
        #: The number of copies for the final positions (default: 1).
        self.__final_position_copy_number = final_position_copy_number

        #: The picked tube candidate for this pool.
        self.tube_candidate = None
        #: The name of the barcoded location the rack is stored at (name and
        #: index).
        self.location = None

    @property
    def pool(self):
        """
        The molecule design pool the stock tube sample should contain
        (:class:`thelma.models.moleculedesign.MoleculeDesignPool`).
        """
        return self.__pool

    @property
    def position_type(self):
        """
        The types of the layouts must be the same for all positions.
        """
        return self.__position_type

    @property
    def expected_rack_barcode(self):
        """
        The barcode of the rack that the scheduled tube is expected in.
        """
        return self.__exp_rack_barcode

    @classmethod
    def from_plate_position(cls, plate_pos, final_position_copy_number):
        """
        Factory method creating a stock tube container from an
        :class:`IsoPlatePosition`.
        """
        kw = dict(pool=plate_pos.molecule_design_pool,
                  position_type=plate_pos.position_type,
                  requested_tube_barcode=plate_pos.stock_tube_barcode,
                  expected_rack_barcode=plate_pos.stock_rack_barcode,
                  final_position_copy_number=final_position_copy_number)
        return cls(**kw)

    @property
    def plate_target_positions(self):
        """
        Returns the target positions mapped onto plate labels. The plate
        label for the final layout is :attr:`LAEBLS.ROLE_FINAL`.
        """
        target_positions = {LABELS.ROLE_FINAL : self.__final_positions}
        target_positions.update(self.__prep_positions)
        return target_positions

    def get_all_target_positions(self):
        """
        Returns all target positions for all plates.
        """
        all_positions = self.__final_positions
        for positions in self.__prep_positions.values():
            all_positions.extend(positions)
        return all_positions

    def get_total_required_volume(self):
        """
        Returns the total volume that needs to be taken from the stock *in ul*.
        """
        volume = 0
        for plate_positions in self.__prep_positions.values():
            for plate_pos in plate_positions:
                volume += plate_pos.get_stock_takeout_volume()
        for plate_positions in self.__final_positions:
            for plate_pos in plate_positions:
                volume += (plate_pos.get_stock_takeout_volume() \
                           * self.__final_position_copy_number)
        return volume

    def get_first_plate(self):
        """
        Returns the label of the first plate. The is the name of the lowest
        preparation plate (if there is any), otherwise the final layout marker
        is returned.
        """
        if len(self.__prep_positions) > 0:
            prep_plates = sorted(self.__prep_positions.keys())
            return prep_plates[0]
        else:
            return LABELS.ROLE_FINAL

    def get_stock_concentration(self):
        """
        Returns the default stock concentration for the pool *in nM*.
        """
        return round(self.__pool.default_stock_concentration \
                     * CONCENTRATION_CONVERSION_FACTOR, 1)

    def add_preparation_position(self, plate_label, plate_pos):
        """
        Registers a target preparation position for this stock tube (used later
        to generated planned worklists).
        """
        add_list_map_element(self.__prep_positions, plate_label, plate_pos)

    def add_final_position(self, plate_pos):
        """
        Registers a target final plate position for this stock tube (used later
        to generated planned worklists).
        """
        self.__final_positions.append(plate_pos)

    def __hash__(self):
        return hash(self.__pool)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__pool == other.pool

    def __str__(self):
        return self.__pool

    def __repr__(self):
        str_format = '<%s pool: %s>'
        params = (self.__class__.__name__, self.__pool)
        return str_format % params


class LabIsoXL20TubePicker(SessionTool):
    """
    Checks whether the stock tube scheduled by the :class:`LabIsoBuilder` are
    still valid and replaces them by other tubes, if necessary.

    **Return Value:** The updated :class:`StockTubeContainer` objects (with a
        tube candidate added).
    """
    NAME = 'Lab ISO Tube Finder'

    def __init__(self, log, stock_tube_containers, excluded_racks=None,
                 requested_tubes=None):
        """
        Constructor:

        :param log: The log to record events.
        :type log: :class:`thelma.ThelmaLog`

        :param stock_tube_containers: The container items should contain all
            target positions for the stock transfer. They must be mapped on
            the pool.
        :type stock_tube_containers: map of :class:`StockTubeContainer`

        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for molecule design picking.
        :type excluded_racks: A list of rack barcodes

        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of tube barcodes.
        """
        SessionTool.__init__(self, log=log)

        #: The container items should contain all target positions for the
        #: stock transfer.
        self.stock_tube_containers = stock_tube_containers

        if excluded_racks is None: excluded_racks = []
        #: A list of barcodes from stock racks that shall not be used for
        #: molecule design picking.
        self.excluded_racks = excluded_racks

        if requested_tubes is None: requested_tubes = []
        #: A list of barcodes from stock tubes that are supposed to be used
        #: (for fixed positions).
        self.requested_tubes = set(requested_tubes)

        #: Maps molecule design pools onto pool IDs.
        self.__pool_map = None
        #: The molecule design pools of the requested tubes.
        self.__requested_tube_map = None
        #: The required volume for each pool *in ul* without stock dead volume.
        self.__volume_map = None

        #:Stores stock tube containers for tubes that need to be replaced.
        self.__replaced_tube_containers = None

        #: Stores message infos for tubes that have been replaced due to
        #: insufficient volume mapped onto pool IDs.
        self.__insuffient_volume = None
        #: Stores message infos for tubes that have been replaced because the
        #: original rack has been excluded mapped onto pool IDs.
        self.__excluded_tubes = None

    def reset(self):
        SessionTool.reset(self)
        self.__pool_map = dict()
        self.__requested_tube_map = dict()
        self.__volume_map = dict()
        self.__replaced_tube_containers = []
        self.__insuffient_volume = dict()
        self.__excluded_tubes = dict()

    def run(self):
        self.reset()
        self.add_info('Start tube verification for lab ISO ...')

        self.__check_input()
        if not self.has_errors(): self.__check_requested_tubes()
        if not self.has_errors(): self.__check_scheduled_tubes()
        if not self.has_errors() and len(self.__replaced_tube_containers) > 0:
            self.__find_new_tubes()
        if not self.has_errors():
            self.__record_messages()
            self.__fetch_rack_locations()
        if not self.has_errors():
            self.add_info('Tube selection completed.')
            self.return_value = self.stock_tube_containers

    def __check_input(self):
        """
        Checks the initialisation types.
        """
        self._check_input_map_classes(self.stock_tube_containers,
                    'stock tube container map', 'pool', MoleculeDesignPool,
                    'stock tube container', StockTubeContainer)

        self._check_input_list_classes('excluded rack', self.excluded_racks,
                                       basestring, may_be_empty=True)
        self._check_input_list_classes('requested tube', self.requested_tubes,
                                       basestring, may_be_empty=True)

    def __create_pool_and_volume_map(self):
        """
        Maps molecule design pool entity onto pool IDs.
        """
        for pool, container in self.stock_tube_containers.iteritems():
            self.__pool_map[pool.id] = pool
            self.__volume_map[pool.id] = container.get_total_required_volume()

    def __check_requested_tubes(self):
        """
        Makes sure the requested tubes make sense in the context of the
        stock tube containers.
        """
        if len(self.requested_tubes) > len(self.stock_tube_containers):
            msg = 'There are more requested tubes (%i) than molecule design ' \
                  'pool IDs (%s)!' % (len(self.requested_tubes),
                                      len(self.stock_tube_containers))
            self.add_warning(msg)

        if len(self.requested_tubes) > 0:
            self.__check_requested_tube_pools()
            self.__check_scheduled_tube_replacement()

    def __check_requested_tube_pools(self):
        """
        Checks whether the pools in the requested tubes comply with the
        passed stock sample containers and creates a map containing the
        molecule design pools for all requested tubes.
        """
        query = TubePoolQuery(tube_barcodes=self.requested_tubes)
        self._run_query(query, 'Error when trying to find pools for ' \
                               'requested tubes: ')

        if not self.has_errors():

            not_found = []
            tube_map = query.get_query_results()
            pool_map = dict()
            for tube_barcode in self.requested_tubes:
                if not tube_map.has_key(tube_barcode):
                    not_found.append(tube_barcode)
                else:
                    pool_id = tube_map[tube_barcode]
                    add_list_map_element(pool_map, pool_id, tube_barcode)

            if len(not_found) > 0:
                msg = 'The following requested tubes could not be found in the ' \
                      'DB: %s.' % (not_found)
                self.add_error(msg)

            expec_pool_ids = set(self.__pool_map.keys())
            multiple_tubes = []
            unexpec_pools = []
            for pool_id, tube_list in pool_map.iteritems():
                picked_tube = sorted(tube_list)[0]
                if len(tube_list) > 1:
                    info = 'pool: %s (tubes: %s, picked: %s)' % (pool_id,
                                        ', '.join(tube_list), picked_tube)
                    multiple_tubes.append(info)
                if not pool_id in expec_pool_ids:
                    unexpec_pools.append(pool_id)
                self.__requested_tube_map[pool_id] = tube_list[0]

            if len(multiple_tubes) > 0:
                msg = 'You have requested multiple tubes for the same ' \
                      'molecule design pool ID! Details: %s.' \
                      % (', '.join(multiple_tubes))
                self.add_warning(msg)
            if len(unexpec_pools) > 0:
                msg = 'The following tube you have requested have samples ' \
                      'for pool that are processed in this step: %s. ' \
                      'Processed pool IDs: %s.' \
                      % (', '.join([str(pi) for pi in sorted(unexpec_pools)]),
                         ', '.join([str(pi) for pi in \
                                    sorted(self.__pool_map.keys())]))
                self.add_warning(msg)

    def __check_scheduled_tube_replacement(self):
        """
        Checks whether there are scheduled tubes that have been replaced by
        requested ones.
        """
        replaced_tubes = []
        for container in self.stock_tube_containers.values():
            pool_id = container.pool.id
            if not self.__requested_tube_map.has_key(pool_id): continue
            req_tube = self.__requested_tube_map[pool_id]
            if not req_tube == container.requested_tube_barcode:
                info = 'MD pool: %s, requested: %s, scheduled: %s' \
                       % (pool_id, str(req_tube),
                          str(container.requested_tube_barcode))
                replaced_tubes.append(info)
                container.requested_tube_barcode = req_tube

        if len(replaced_tubes) > 0:
            msg = 'Some requested tubes differ from the ones scheduled ' \
                  'during ISO generation (%i molecule design pool(s)). The ' \
                  'scheduled tubes are replaced by the requested ones. ' \
                  'Details: %s.' % (len(replaced_tubes),
                                    ' - '.join(sorted(replaced_tubes)))
            self.add_warning(msg)

    def __check_scheduled_tubes(self):
        """
        Checks whether the scheduled tubes still contain enough volume.
        """
        self.add_debug('Check scheduled tubes ...')

        barcodes = []
        for stock_tube_container in self.stock_tube_containers.values():
            barcodes.append(stock_tube_container.requested_tube_barcode)
        query = _LabIsoTubeConfirmationQuery(tube_barcodes=barcodes)
        self._run_query(query, base_error_msg='Error when trying to confirm ' \
                              'scheduled tubes via DB query: ')

        if not self.has_errors():
            candidate_map = query.get_query_results()
            conc_mismatch = []

            for pool_id, candidate in candidate_map.iteritems():
                pool = self.__pool_map[pool_id]
                container = self.stock_tube_containers[pool]
                tube_barcode = container.requested_tube_barcode
                if not self.__stock_concentration_match(candidate, container,
                                                        conc_mismatch): continue
                required_volume = self.__volume_map[pool_id] + STOCK_DEAD_VOLUME
                if is_smaller_than(candidate.volume, required_volume):
                    params = [tube_barcode, get_trimmed_string(required_volume),
                              get_trimmed_string(candidate.volume)]
                    self.__insuffient_volume[pool_id] = params
                    self.__replaced_tube_containers.append(container)
                    continue
                if candidate.rack_barcode in self.excluded_racks:
                    self.__excluded_tubes[pool_id] = tube_barcode
                    self.__replaced_tube_containers.append(container)
                else:
                    container.tube_candidate = candidate

    def __stock_concentration_match(self, candidate, container, error_list):
        """
        Makes sure tube candidate and stock tube container expect the same
        stock concentration.
        """
        container_conc = container.get_stock_concentration()
        candidate_conc = candidate.concentration
        if not are_equal_values(container_conc, candidate_conc):
            info = '%s (pool: %i, expected: %s nM, found at tube: %s nM)' \
                   % (candidate.tube_barcode, candidate.pool_id,
                      get_trimmed_string(container_conc),
                      get_trimmed_string(candidate_conc))
            error_list.append(info)
            return False
        else:
            return True

    def __find_new_tubes(self):
        """
        Finds tubes for pool that do not have a tube candidate yet.
        """
        self.add_debug('Find tubes for missing pools ...')

        for container in self.__replaced_tube_containers:
            pool_id = container.pool.id
            required_volume = self.__volume_map[pool_id]
            query = SinglePoolQuery(pool_id=pool_id,
                                    concentration=container.get_stock_sample,
                                    minimum_volume=required_volume)
            self._run_query(query, None)
            candidates = query.get_query_results()
            while len(candidates) > 0:
                candidate = candidates.pop(0)
                tube_barcode = candidate.tube_barcode
                if candidate.rack_barcode in self.excluded_racks:
                    add_list_map_element(self.__excluded_tubes, pool_id,
                                         tube_barcode)
                    continue
                elif self.__requested_tube_map[pool_id]:
                    container.tube_candidate = candidate
                    break
                elif container.tube_candidate is None:
                    container.tube_candidate = candidate

    def __record_messages(self):
        """
        Records warnings, if scheduled tubes have been moved and if tubes have
        been changed.
        """
        moved_tubes = []
        for container in self.stock_tube_containers.values():
            if container.tube_candidate is None: continue
            exp_rack = container.expected_rack_barcode
            exp_tube = container.requested_tube_barcode
            used_rack = container.tube_candidate.rack_barcode
            used_tube = container.tube_candidate.tube_barcode
            if used_tube == exp_tube and not (used_rack == exp_rack):
                info = '%s (from rack %s to %s)' % (used_tube, exp_rack,
                                                    used_rack)
                moved_tubes.append(info)
        if len(moved_tubes) > 0:
            msg = 'The following tubes have been moved since the generation ' \
                  'of the ISO: %s.' % (', '.join(sorted(moved_tubes)))
            self.add_warning(msg)

        if len(self.__insuffient_volume) > 0:
            details = []
            for pool_id, params in self.__insuffient_volume.iteritems():
                pool = self.__pool_map[pool_id]
                container = self.stock_tube_containers[pool]
                if container.tube_candidate is None:
                    params.append('could not be replaced')
                else:
                    new_tube_barcode = container.tube_candidate.tube_barcode
                    params.append(new_tube_barcode)
                info = '%s (required: %s ul, found: %s, replaced by: %s)' \
                        % params
                details.append(info)
            msg = 'Some scheduled tubes had to be replaced because their ' \
                  'volume was not sufficient anymore: %s.' \
                   % (', '.join(sorted(details)))
            self.add_warning(msg)

        if len(self.__excluded_tubes) > 0:
            details = []
            for pool_id, old_tube_barcode in self.__excluded_tubes.iteritems():
                pool = self.__pool_map[pool_id]
                container = self.stock_tube_containers[pool]
                if container.tube_candidate is None:
                    new_tube_barcode = 'could not be replaced'
                else:
                    new_tube_barcode = container.tube_candidate.tube_barcode
                info = '%s (replaced by: %s)' % (old_tube_barcode,
                                                 new_tube_barcode)
                details.append(info)
            msg = 'Some scheduled tubes had to be replaced because their ' \
                  'current racks have been excluded: %s. Excluded racks: %s.' \
                  % (', '.join(sorted(details)), ', '.join(self.excluded_racks))
            self.add_warning(msg)

    def __fetch_rack_locations(self):
        """
        Searches and adds the location for the selected candidates.
        """
        self.add_debug('Fetch stock rack locations ...')

        rack_barcodes = dict()
        for container in self.stock_tube_containers.values():
            if container.tube_candidate is None: continue
            rack_barcode = container.tube_candidate.rack_barcode
            add_list_map_element(rack_barcodes, rack_barcode, container)

        query = None
        if len(rack_barcodes) > 0:
            query = RackLocationQuery(rack_barcodes=rack_barcodes.keys())
            self._run_query(query, base_error_msg='Error when trying to ' \
                                                  'fetch rack locations: ')
        if not self.has_errors() and not query is None:
            results = query.get_query_results()
            for rack_barcode, location in results.iteritems():
                for container in rack_barcodes[rack_barcode]:
                    container.location = location


class _LabIsoTubeConfirmationQuery(TubePickingQuery):
    """
    This query is used to check whether the volume of the tubes  scheduled by
    the :class:`LabIsoBuilder` is still sufficient.

    The results are converted into tube candidates (:class:`TubeCandidate`).
    The candidates collection is dictionary (candidate are mapped onto pool ID).
    """
    QUERY_TEMPLATE = '''
    SELECT s.volume AS stock_volume,
        r.barcode AS rack_barcode,
        rc.row AS row_index,
        rc.col AS column_index,
        cb.barcode AS tube_barcode,
        ss.concentration AS stock_concentration
    FROM container c, container_barcode cb, rack r, containment rc, sample s,
        stock_sample ss
    WHERE cb.barcode IN '%s'
    AND s.container_id = cb.container_id
    AND s.sample_id = ss.sample_id
    AND c.container_id = cb.container_id
    AND c.item_status = '%s'
    AND rc.held_id = c.container_id
    AND r.rack_id = rc.holder_id;
    '''

    COLUMN_NAMES = ['stock_volume', 'rack_barcode', 'row_index', 'column_index',
                    'tube_barcode', 'stock_concentration']

    def __init__(self, tube_barcodes):
        """
        Constructor:

        :param tube_barcodes: The barcodes of the tubes picked by the
            :class:`LabIsoBuilder`.
        :type tube_barcodes: list of :class:`basestring`
        """
        TubePickingQuery.__init__(self)

        #: The barcodes of the tubes picked by the :class:`LabIsoBuilder`.
        self.tube_barcodes = tube_barcodes

    def _get_params_for_sql_statement(self):
        return create_in_term_for_db_queries(self.tube_barcodes, as_string=True)

    def _store_result(self, result_record):
        """
        There should only be one candidate for each pool.
        """
        candidate = self._create_candidate_from_query_result(result_record)
        pool_id = candidate.pool_id
        if self._results.has_key(pool_id): #pylint: disable=E1101
            tube_barcodes = [candidate.tube_barcode,
                             self._results[pool_id].tube_barcode]
            msg = 'There are several candidates for pool %i: %s!' \
                  % (pool_id, ', '.join(sorted(tube_barcodes)))
            raise ValueError(msg)
        else:
            self._results[pool_id] = candidate

