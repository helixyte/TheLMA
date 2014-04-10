"""
Deals with the final tube picking for lab ISOs.

AAB
"""
from everest.entities.utils import get_root_aggregate
from everest.querying.specifications import cntd
from thelma.automation.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.tools.base import SessionTool
from thelma.automation.tools.iso.lab.stockrack.base import StockTubeContainer
from thelma.automation.tools.stock.base import RackLocationQuery
from thelma.automation.tools.stock.base import STOCK_DEAD_VOLUME
from thelma.automation.tools.stock.tubepicking import SinglePoolQuery
from thelma.automation.tools.stock.tubepicking import TubeCandidate
from thelma.automation.utils.base import add_list_map_element
from thelma.automation.utils.base import are_equal_values
from thelma.automation.utils.base import get_trimmed_string
from thelma.automation.utils.base import is_smaller_than
from thelma.interfaces import ITube
from thelma.models.moleculedesign import MoleculeDesignPool
from thelma.models.sample import StockSample


__docformat__ = 'reStructuredText en'

__all__ = ['LabIsoXL20TubePicker']


class LabIsoXL20TubePicker(SessionTool):
    """
    Checks whether the stock tube scheduled by the :class:`LabIsoBuilder` are
    still valid and replaces them by other tubes, if necessary.

    **Return Value:** The updated :class:`StockTubeContainer` objects (with a
        tube candidate added).
    """
    NAME = 'Lab ISO Tube Finder'

    def __init__(self, stock_tube_containers, excluded_racks=None,
                 requested_tubes=None, parent=None):
        """
        Constructor.

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
        SessionTool.__init__(self, parent=parent)
        #: The container items should contain all target positions for the
        #: stock transfer.
        self.stock_tube_containers = stock_tube_containers
        if excluded_racks is None:
            excluded_racks = []
        #: A list of barcodes from stock racks that shall not be used for
        #: molecule design picking.
        self.excluded_racks = excluded_racks
        if requested_tubes is None:
            requested_tubes = []
        #: A list of barcodes from stock tubes that are supposed to be used
        #: (for fixed positions).
        self.requested_tubes = requested_tubes
        #: The tube aggregate is used to check tubes for specified tube
        #: barcodes.
        self.__tube_agg = None
        #: Maps molecule design pools onto pool IDs.
        self.__pool_map = None
        #: The molecule design pools of the requested tubes.
        self.__requested_tube_map = None
        #: The required volume for each pool *in ul* without stock dead volume.
        self.__volume_map = None
        #: Stores stock tube containers for tubes that need to be replaced.
        self.__replaced_tube_containers = None
        #: Stores message infos for tubes that have been replaced because the
        #: original rack has been excluded mapped onto pool IDs.
        self.__excluded_tubes = None
        #: The tubes (that have not been replaced) mapped onto tube barcodes.
        self.__tube_map = None
        #: Contains pools for which no tube has been found.
        self.__missing_pools = None
        # Intermediate warning and error messages
        self.__insuffient_volume_requested = None
        self.__insuffient_volume_scheduled = None
        self.__conc_mismatch_requested = None
        self.__conc_mismatch_scheduled = None

    def reset(self):
        SessionTool.reset(self)
        self.__tube_agg = get_root_aggregate(ITube)
        self.__pool_map = dict()
        self.__requested_tube_map = dict()
        self.__volume_map = dict()
        self.__replaced_tube_containers = []
        self.__excluded_tubes = dict()
        self.__tube_map = dict()
        self.__insuffient_volume_requested = dict()
        self.__insuffient_volume_scheduled = dict()
        self.__conc_mismatch_requested = []
        self.__conc_mismatch_scheduled = []
        self.__missing_pools = []

    def run(self):
        self.reset()
        self.add_info('Start tube verification for lab ISO ...')
        self.__check_input()
        if not self.has_errors():
            self.__create_pool_and_volume_map()
        if not self.has_errors():
            self.__check_requested_tubes()
        if not self.has_errors():
            self.__check_scheduled_tubes()
        if not self.has_errors() and len(self.__replaced_tube_containers) > 0:
            self.__find_new_tubes()
        if not self.has_errors():
            self.__record_messages()
            self.__fetch_rack_locations()
        if not self.has_errors():
            self.add_info('Tube selection completed.')
            self.return_value = self.stock_tube_containers

    def get_missing_pools(self):
        """
        Returns the pools for which there was no valid tube in the DB.
        """
        return self._get_additional_value(self.__missing_pools)

    def __check_input(self):
        """
        Checks the initialisation types.
        """
        self._check_input_map_classes(self.stock_tube_containers,
                    'stock tube container map', 'pool', MoleculeDesignPool,
                    'stock tube container', StockTubeContainer)

        self._check_input_list_classes('excluded rack', self.excluded_racks,
                                       basestring, may_be_empty=True)
        if self._check_input_list_classes('requested tube', self.requested_tubes,
                                          basestring, may_be_empty=True):
            self.requested_tubes = set(self.requested_tubes)

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
        candidate_map = self.__get_tube_candidates_for_tubes(
                                            self.requested_tubes, 'requested')

        multiple_tubes = []
        expec_pool_ids = set(self.__pool_map.keys())
        unexpected_pools = []

        for pool_id, candidates in candidate_map.iteritems():
            tube_list = []
            for candidate in candidates:
                tube_list.append(candidate.tube_barcode)
            if not self.__pool_map.has_key(pool_id):
                info = '%i (tubes: %s)' % (pool_id,
                                           self._get_joined_str(tube_list))
                unexpected_pools.append(info)
                continue
            if len(candidates) > 1:
                info = 'pool: %s (tubes: %s)' % (pool_id,
                        self._get_joined_str(tube_list))
                multiple_tubes.append(info)
            for candidate in candidates:
                if self.__accept_tube_candidate(candidate,
                                    self.__conc_mismatch_requested,
                                    self.__insuffient_volume_requested):
                    break

        if len(multiple_tubes) > 0:
            msg = 'You have requested multiple tubes for the same ' \
                  'molecule design pool ID! Details: %s.' \
                  % (self._get_joined_str(multiple_tubes))
            self.add_warning(msg)
        if len(unexpected_pools) > 0:
            msg = 'The following tube you have requested have samples ' \
                  'for pool that are not processed in this step: %s. ' \
                  'Processed pool IDs: %s.' \
                  % (self._get_joined_str(unexpected_pools),
                     self._get_joined_str(expec_pool_ids, is_strs=False))
            self.add_warning(msg)

    def __check_scheduled_tube_replacement(self):
        """
        Checks whether there are scheduled tubes that have been replaced by
        requested ones.
        """
        replaced_tubes = []
        for container in self.stock_tube_containers.values():
            if container.tube_candidate is None: continue
            pool_id = container.pool.id
            requested_tube = container.tube_candidate.tube_barcode
            if not requested_tube == container.requested_tube_barcode:
                info = 'MD pool: %s, requested: %s, scheduled: %s' \
                       % (pool_id, str(requested_tube),
                          str(container.requested_tube_barcode))
                replaced_tubes.append(info)
                container.requested_tube_barcode = requested_tube

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
            if stock_tube_container.tube_candidate is not None: continue
            barcodes.append(stock_tube_container.requested_tube_barcode)

        candidate_map = self.__get_tube_candidates_for_tubes(barcodes,
                                                             'scheduled')
        for pool, container in self.stock_tube_containers.iteritems():
            if container.tube_candidate is not None: continue
            pool_id = pool.id
            if not candidate_map.has_key(pool_id):
                self.__replaced_tube_containers.append(pool_id)
                continue
            candidates = candidate_map[pool_id]
            picked_candidate = None
            for candidate in candidates:
                if self.__accept_tube_candidate(candidate,
                            self.__conc_mismatch_scheduled,
                            self.__insuffient_volume_scheduled):
                    picked_candidate = candidate
                    break
            if picked_candidate is None:
                self.__replaced_tube_containers.append(pool_id)

    def __find_new_tubes(self):
        """
        Finds tubes for pool that do not have a tube candidate yet.
        """
        self.add_debug('Find tubes for missing pools ...')

        for pool_id in self.__replaced_tube_containers:
            pool = self.__pool_map[pool_id]
            container = self.stock_tube_containers[pool]
            required_volume = self.__volume_map[pool_id]
            query = SinglePoolQuery(pool_id=pool_id,
                            concentration=container.get_stock_concentration(),
                            minimum_volume=required_volume)
            self._run_query(query, None)
            candidates = query.get_query_results()
            while len(candidates) > 0:
                candidate = candidates.pop(0)
                tube_barcode = candidate.tube_barcode
                if candidate.rack_barcode in self.excluded_racks:
                    add_list_map_element(self.__excluded_tubes, pool_id,
                                         tube_barcode, as_set=True)
                else:
                    container.tube_candidate = candidate
                    candidate.set_pool(container.pool)
                    break
            if container.tube_candidate is None:
                self.__missing_pools.append(container.pool)

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

        self.__record_insufficient_volume_message(
                            self.__insuffient_volume_requested, 'requested')
        self.__record_insufficient_volume_message(
                            self.__insuffient_volume_scheduled, 'scheduled')

        conc_mismatch_base_msg = 'The following %s tubes have been ignored ' \
            'because they concentration does not match the expected stock ' \
            'concentration: %s.'
        if len(self.__conc_mismatch_requested):
            self.add_warning(conc_mismatch_base_msg % ('requested',
                       self._get_joined_str(self.__conc_mismatch_requested)))
        if len(self.__conc_mismatch_scheduled):
            self.add_warning(conc_mismatch_base_msg % ('scheduled',
                       self._get_joined_str(self.__conc_mismatch_scheduled)))

        if len(self.__excluded_tubes) > 0:
            details = []
            for pool_id, old_tube_barcodes in self.__excluded_tubes.iteritems():
                old_barcodes = self._get_joined_str(old_tube_barcodes,
                                                    separator='-')
                pool = self.__pool_map[pool_id]
                container = self.stock_tube_containers[pool]
                if container.tube_candidate is None:
                    new_tube_barcode = 'could not be replaced'
                else:
                    new_tube_barcode = container.tube_candidate.tube_barcode
                info = '%i (replaced by: %s, excluded tubes: %s)' \
                        % (pool_id, new_tube_barcode, old_barcodes)
                details.append(info)
            msg = 'Some scheduled tubes had to be replaced or removed ' \
                  'because their current racks have been excluded: %s. ' \
                  'Excluded racks: %s.' % (self._get_joined_str(details),
                   self._get_joined_str(self.excluded_racks))
            self.add_warning(msg)

    def __record_insufficient_volume_message(self, error_map, tube_type):
        """
        Helper method. Records a warning for tubes that were replaced because
        they do not contain enough volume anymore.
        """
        if len(error_map) > 0:
            details = []
            for pool_id, params in error_map.iteritems():
                pool = self.__pool_map[pool_id]
                container = self.stock_tube_containers[pool]
                if container.tube_candidate is None:
                    params.append('could not be replaced')
                else:
                    new_tube_barcode = container.tube_candidate.tube_barcode
                    params.append(new_tube_barcode)
                info = '%s (required: %s ul, found: %s, replaced by: %s)' \
                        % tuple(params)
                details.append(info)
            msg = 'Some %s tubes had to be replaced because their ' \
                  'volume was not sufficient anymore: %s.' \
                   % (tube_type, self._get_joined_str(details))
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

    def __get_tube_candidates_for_tubes(self, tube_barcodes, tube_type):
        """
        As far as possible we use the tube aggregate to fetch tubes from the
        DB. The tubes for the barcodes are converted into :class:`TubeCandidate`
        objects and mapped onto pools.
        Valid tubes must contain stock samples and be managed.
        """
        self.__tube_agg.filter = cntd(barcode=tube_barcodes)
        iterator = self.__tube_agg.iterator()
        candidate_map = dict()
        no_stock_sample = []
        not_managed = []
        while True:
            try:
                tube = iterator.next()
            except StopIteration:
                break
            else:
                if not tube.item_status == ITEM_STATUS_NAMES.MANAGED.upper():
                    not_managed.append(tube.barcode)
                    continue
                sample = tube.sample
                if not isinstance(sample, StockSample):
                    no_stock_sample.append(tube.barcode)
                    continue
                pool = sample.molecule_design_pool
                tc = TubeCandidate(pool_id=pool.id,
                                   rack_barcode=tube.location.rack.barcode,
                                   rack_position=tube.location.position,
                                   tube_barcode=tube.barcode,
                                   concentration=sample.concentration,
                                   volume=sample.volume)
                # we could store the pool itself to (instead of its ID), but
                # for some reason the pool entities are not recognised as equal
                add_list_map_element(candidate_map, pool.id, tc)
                self.__tube_map[tube.barcode] = tube

        if len(no_stock_sample) > 0:
            msg = 'The following %s tubes do not contain stock ' \
                  'samples: %s! The referring tubes are replaced, if ' \
                  'possible.' % (tube_type,
                                 self._get_joined_str(no_stock_sample))
            self.add_warning(msg)
        if len(not_managed) > 0:
            msg = 'The following %s tubes are not managed: %s. They ' \
                  'are replaced, if possible.' \
                   % (tube_type, self._get_joined_str(not_managed))
            self.add_warning(msg)

        not_found = []
        for tube_barcode in tube_barcodes:
            if not self.__tube_map.has_key(tube_barcode):
                not_found.append(tube_barcode)
        if len(not_found) > 0:
            msg = 'The following %s tubes have not been found in the DB: %s.' \
                  % (tube_type, self._get_joined_str(not_found))
            self.add_warning(msg)

        return candidate_map

    def __accept_tube_candidate(self, tube_candidate, conc_mismatch_list,
                                insufficent_vol_map):
        """
        A valid tube container must have a matching concentration,
        contain sufficent volume and must be excluded via the rack barcode.
        Accepted candidates are assigned to the referring containers.
        """
        pool_id = tube_candidate.pool_id
        pool = self.__pool_map[pool_id]
        container = self.stock_tube_containers[pool]
        if not self.__stock_concentration_match(tube_candidate, container,
                                    conc_mismatch_list): return False
        required_vol = self.__volume_map[pool_id] + STOCK_DEAD_VOLUME
        if is_smaller_than(tube_candidate.volume, required_vol):
            params = [tube_candidate.tube_barcode,
                      get_trimmed_string(required_vol),
                      get_trimmed_string(tube_candidate.volume)]
            insufficent_vol_map[pool_id] = params
            return False
        if tube_candidate.rack_barcode in self.excluded_racks:
            add_list_map_element(self.__excluded_tubes, pool_id,
                                 tube_candidate.tube_barcode, as_set=True)
            return False
        else:
            tube_candidate.set_pool(container.pool)
            container.tube_candidate = tube_candidate
            return True

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

    def _look_for_missing_candidates(self):
        """
        We have already done that in :func:`__find_new_tubes`.
        """
        pass
