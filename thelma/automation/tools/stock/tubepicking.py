"""
Classes and queries involved in tube picking. The purpose is to find a tube
for a particular molecule design pool that can be used for an ISO. For this,
the stock sample must have a certain concentration and a certain minimum volume.

If there are several stock tubes available, it is possible to optimize the
tube picking. In this case the tube picker will choose the tube with the
lowest volume. If the number of pools is large, it is
also possible to try to minimize the number of stock racks used instead.

AAB
"""
from everest.repositories.rdb import Session
from sqlalchemy.orm.collections import InstrumentedSet
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.semiconstants import get_rack_position_from_indices
from thelma.automation.tools.stock.base import STOCK_DEAD_VOLUME
from thelma.automation.tools.stock.base import STOCK_ITEM_STATUS
from thelma.automation.tools.stock.base import STOCK_TUBE_SPECS
from thelma.automation.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import CustomQuery
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import add_list_map_element
from thelma.automation.tools.utils.base import create_in_term_for_db_queries
from thelma.automation.tools.utils.base import is_valid_number
from thelma.models.moleculedesign import MoleculeDesignPool

__docformat__ = 'reStructuredText en'

__all__ = ['get_stock_tube_specs_db_term',
           'StockSampleQuery',
           'TubeCandidate',
           'TubePickingQuery']


def get_stock_tube_specs_db_term():
    """
    Returns a term that can be inserted into IN-clauses of DB queries
    (containing all valid specs for stock tubes).
    """
    return create_in_term_for_db_queries(STOCK_TUBE_SPECS, as_string=True)


class StockSampleQuery(CustomQuery):
    """
    This query is used to find suitable stock samples (as IDs) for a list of
    molecule designs pools.

    The results are stored in a dictionary (stock sample IDs mapped onto pool
    IDs).
    """
    QUERY_TEMPLATE = '''
    SELECT ss.molecule_design_set_id AS pool_id,
           ss.sample_id AS stock_sample_id
    FROM stock_sample ss, sample s, container c
    WHERE ss.molecule_design_set_id IN %s
    AND ss.concentration = %s
    AND s.sample_id = ss.sample_id
    AND s.volume >= %s
    AND c.container_id = s.container_id
    AND c.item_status = '%s';'''

    RESULT_COLLECTION_CLS = dict

    __POOL_COL_NAME = 'pool_id'
    __STOCK_SAMPLE_COL_NAME = 'stock_sample_id'

    COLUMN_NAMES = [__POOL_COL_NAME, __STOCK_SAMPLE_COL_NAME]

    __POOL_INDEX = COLUMN_NAMES.index(__POOL_COL_NAME)
    __STOCK_SAMPLE_INDEX = COLUMN_NAMES.index(__STOCK_SAMPLE_COL_NAME)

    def __init__(self, session, pool_ids, concentration, minimum_volume=None):
        """
        Constructor:

        :param session: The DB session to be used.

        :param pool_ids: The molecule design pool IDs for which you want to
            find stock samples.
        :type pool_ids: collection of :class:`int`

        :param concentration: The concentration of the stock sample *in nM*.
        :type concentration: positive number, unit nM

        :param minimum_volume: The minimum volume the tube must have *in ul* -
            the dead volume of the stock is added to it automatically.
            If you do pass a minimum volume all samples are accepted.
        :type minimum_volume: positive number, unit ul
        """
        CustomQuery.__init__(self, session=session)
        #: The molecule design pool IDs for which to find stock samples.
        self.pool_ids = pool_ids
        #: The concentration of the stock sample *in nM*.
        self.concentration = concentration
        #: The minimum volume the tube must have *in ul* - the dead volume of
        #: the stock is added to it automatically. If the minimum volume
        #: is None is is set to 0.
        self.minimum_volume = minimum_volume
        if minimum_volume is None:
            self.minimum_volume = 0

    def _get_params_for_sql_statement(self):
        pool_str = create_in_term_for_db_queries(self.pool_ids)
        conc = self.concentration / CONCENTRATION_CONVERSION_FACTOR
        vol = (self.minimum_volume + STOCK_DEAD_VOLUME) \
              / VOLUME_CONVERSION_FACTOR
        return (pool_str, conc, vol, STOCK_ITEM_STATUS)

    def _store_result(self, result_record):
        pool_id = result_record[self.__POOL_INDEX]
        stock_sample_id = result_record[self.__STOCK_SAMPLE_INDEX]
        add_list_map_element(self._results, pool_id, stock_sample_id)


class TubeCandidate(object):
    """
    Represents the result of an tube picking optimizing query, i.e. a tube
    that might be used for an ISO.

    All attributes are immutable.
    """
    def __init__(self, pool_id, rack_barcode, rack_position,
                 tube_barcode, concentration, volume=None):
        """
        Constructor. Attributes are immutable.
        """
        self.__pool_id = pool_id
        self.__rack_barcode = rack_barcode
        self.__rack_position = rack_position
        self.__tube_barcode = tube_barcode
        self.__concentration = concentration * CONCENTRATION_CONVERSION_FACTOR
        if volume is None:
            self.__volume = None
        else:
            self.__volume = volume * VOLUME_CONVERSION_FACTOR

    @property
    def pool_id(self):
        return self.__pool_id

    @property
    def rack_barcode(self):
        return self.__rack_barcode

    @property
    def rack_position(self):
        return self.__rack_position

    @property
    def tube_barcode(self):
        return self.__tube_barcode

    @property
    def concentration(self):
        return self.__concentration

    @property
    def volume(self):
        return self.__volume

    def __str__(self):
        return '%i-%s' % (self.__pool_id, self.__tube_barcode)

    def __repr__(self):
        str_format = '<IsoCandidate molecule design pool ID: %i, ' \
                     'rack barcode: %s, rack position: %s, container ' \
                     'barcode: %s, concentration: %s nM>'
        params = (self.__pool_id, self.__rack_barcode, self.__rack_position,
                  self.__tube_barcode, self.__concentration)
        return str_format % params

    def __eq__(self, other):
        return isinstance(other, self.__class__) \
            and other.pool_id == self.__pool_id \
            and other.rack_barcode == self.__rack_barcode \
            and other.rack_position == self.__rack_position \
            and other.tube_barcode == self.__tube_barcode \
            and other.concentration == self.__concentration


class TubePickingQuery(CustomQuery): # pylint: disable=W0223
    """
    An abstract class creating and running a DB query that picks stock tubes
    for a certain task.
    The results are converted into tube candidates (:class:`TubeCandidate`).
    The candidates collection is dictionary (candidates are mapped onto
    pool IDs).
    """
    #: The candidate type.
    CANDIDATE_CLS = None

    #: If *True* result values for the column names \'row_index\' and
    #: '\column_index\' are converted into a :class:`RackPosition` before
    #: they are passed to the candidate :func:`__init__` method.
    CONVERT_RACK_POSITION = True

    #: Contains result column names that shall be ignored (there presence
    #: in the select statement might still be required to enable sorting).
    IGNORE_COLUMNS = []

    RESULT_COLLECTION_CLS = dict

    def _store_result(self, result_record):
        """
        Results are converted into :class:`CANDIDATE_CLS` objects before
        storage. The
        """
        candidate = self._create_candidate_from_query_result(result_record)
        add_list_map_element(self._results, candidate.pool_id, candidate)

    def _create_candidate_from_query_result(self, result_record):
        """
        Converts a query result record into a candidate. By default all
        column names are used as keyword.

        If there \'row_index\' and \'column_index\' columns the two columns
        are converted into a rack position value (keyword \'rack_position\').
        """
        row_index = None
        column_index = None
        kw = dict()

        for i in range(self.COLUMN_NAMES):
            col_name = self.COLUMN_NAMES[i]
            if col_name in self.IGNORE_COLUMNS: continue
            value = result_record[i]
            if self.CONVERT_RACK_POSITION and col_name == 'row_index':
                row_index = value
            elif self.CONVERT_RACK_POSITION and col_name == 'column_index':
                column_index = value
            else:
                kw[col_name] = value

        if row_index is not None and column_index is not None:
            rack_pos = get_rack_position_from_indices(row_index=row_index,
                                                      column_index=column_index)
            kw['rack_position'] = rack_pos

        return self.CANDIDATE_CLS(**kw) #pylint: disable=E1102


class _PoolQuery(TubePickingQuery):
    """
    Used if there is you look for tubes for particular molecule design pools.
    """
    #: The operator to be inserted into the pool ID clause of the
    #: :attr:`QUERY_TEMPLATE`.
    _POOL_OPERATOR = None

    QUERY_TEMPLATE = '''
    SELECT cb.barcode AS tube_barcode, s.volume AS stock_volume,
        rc.row AS row_index, rc.col AS column_index, r.barcode AS rack_barcode,
        ss.concentration AS stock_concentration
    FROM stock_sample ss, sample s, container c, container_barcode cb,
        container_specs cs, containment rc, rack r
    WHERE ss.molecule_design_set_id %s %s
    AND ss.sample_id = s.sample_id
    AND ss.concentration = %s
    AND s.volume >= %s
    AND s.container_id = c.container_id
    AND c.item_status = '%s'
    AND c.container_id = cb.container_id
    AND c.container_specs_id = cs.container_specs_id
    AND cs.name IN %s
    AND rc.held_id = c.container_id
    AND rc.holder_id = r.rack_id;'''

    COLUMN_NAMES = ['tube_barcode', 'stock_volume', 'row_index',
                    'column_index', 'rack_barcode', 'stock_concentration']

    CANDIDATE_CLS = TubeCandidate

    def __init__(self, session, concentration, minimum_volume=None):
        """
        Constructor:

        :param session: The DB session to be used.

        :param concentration: The concentration of the stock sample *in nM*.
        :type concentration: positive number, unit nM

        :param minimum_volume: The minimum volume the tube must have *in ul* -
            the dead volume of the stock is added to it automatically.
            If you do pass a minimum volume all tubes are accepted.
        :type minimum_volume: positive number, unit ul
        """
        TubePickingQuery.__init__(self, session=session)

        #: The concentration of the stock sample *in nM*.
        self.concentration = concentration
        #: The minimum volume the tube must have *in ul* - the dead volume of
        #: the stock is added to it automatically. If the minimum volume
        #: is None is is set to 0.
        self.minimum_volume = minimum_volume
        if minimum_volume is None:
            self.minimum_volume = 0

    def _get_pool_id_term(self):
        """
        Returns the term for the pool clause (after the operator).
        """
        raise NotImplementedError('Abstract method.')

    def _get_params_for_sql_statement(self):
        """
        If there is no minimum volume specified, the minimum volume is set
        to 0.
        """
        pool_term = self._get_pool_id_term()
        conc = self.concentration / CONCENTRATION_CONVERSION_FACTOR
        vol = (self.minimum_volume + STOCK_DEAD_VOLUME) \
              / VOLUME_CONVERSION_FACTOR
        tube_specs_term = get_stock_tube_specs_db_term()

        return (self._POOL_OPERATOR, pool_term, conc, vol, STOCK_ITEM_STATUS,
                tube_specs_term)


class SinglePoolQuery(_PoolQuery):
    """
    Used if there is you look for a tube for one particular molecule
    design pool.
    """

    _POOL_OPERATOR = '='

    def __init__(self, session, pool_id, concentration, minimum_volume=None):
        """
        Constructor:

        :param session: The DB session to be used.

        :param pool_id: The ID of the molecule design pool you need a tuube for.
        :type pool_id: :class:`int`

        :param concentration: The concentration of the stock sample *in nM*.
        :type concentration: positive number, unit nM

        :param minimum_volume: The minimum volume the tube must have *in ul* -
            the dead volume of the stock is added to it automatically.
            If you do pass a minimum volume all tubes are accepted.
        :type minimum_volume: positive number, unit ul
        """
        _PoolQuery.__init__(self, session=session, concentration=concentration,
                            minimum_volume=minimum_volume)
        #: The ID of the molecule design pool you need a tuube for.
        self.pool_id = pool_id

    def _get_pool_id_term(self):
        return self.pool_id


class MultiPoolQuery(_PoolQuery):
    """
    Used if there is you look for tube for several particular molecule
    design pool but do not require a rack number minimisation.
    """

    _POOL_OPERATOR = 'IN'

    def __init__(self, session, pool_ids, concentration, minimum_volume=None):
        """
        Constructor:

        :param session: The DB session to be used.

        :param pool_ids: The ID of the molecule design pools you need tubes for.
        :type pool_ids: iterable of :class:`int`

        :param concentration: The concentration of the stock sample *in nM*.
        :type concentration: positive number, unit nM

        :param minimum_volume: The minimum volume the tube must have *in ul* -
            the dead volume of the stock is added to it automatically.
            If you do pass a minimum volume all tubes are accepted.
        :type minimum_volume: positive number, unit ul
        """
        _PoolQuery.__init__(self, session=session, concentration=concentration,
                            minimum_volume=minimum_volume)

        #: The ID of the molecule design pools you need tubes for.
        self.pool_ids = pool_ids

    def _get_pool_id_term(self):
        return create_in_term_for_db_queries(self.pool_ids)


class OptimizingQuery(TubePickingQuery):
    """
    An optimising query tries to find tubes for an ISO. At this, it tries to
    minimise the number of racks that have to be used in the stock.

    By default, the results are stored in a list (as :class:`TubeCandidates`)
    in the order of appearance.
    """
    RESULT_COLLECTION_CLS = list

    QUERY_TEMPLATE = '''
    SELECT DISTINCT stock_sample.molecule_design_set_id AS pool_id,
           rack_tube_counts.rack_barcode AS rack_barcode,
           containment.row AS row_index,
           containment.col AS column_index,
           container_barcode.barcode AS tube_barcode,
           rack_tube_counts.desired_count AS total_candidates,
           stock_sample.concentration AS concentration,
           sample.volume AS volume
    FROM stock_sample, sample, container, container_barcode, containment,
         (SELECT xr.rack_id, xr.barcode AS rack_barcode,
                   COUNT(xc.container_id) AS desired_count
          FROM rack xr, containment xrc, container xc, sample xs,
               stock_sample xss
          WHERE xr.rack_id = xrc.holder_id
          AND xc.container_id = xrc.held_id
          AND xc.container_id = xs.container_id
          AND xs.sample_id = xss.sample_id
          AND xs.sample_id IN %s
          GROUP BY xr.rack_id, xr.barcode
          HAVING COUNT(xc.container_id) > 0 ) AS rack_tube_counts
    WHERE container.container_id = containment.held_id
    AND containment.holder_id = rack_tube_counts.rack_id
    AND container.container_id = sample.container_id
    AND container_barcode.container_id = container.container_id
    AND sample.sample_id = stock_sample.sample_id
    AND sample.sample_id IN %s
    ORDER BY rack_tube_counts.desired_count desc,
        rack_tube_counts.rack_barcode;'''

    COLUMN_NAMES = ['pool_id', 'rack_barcode', 'row_index', 'column_index',
                    'tube_barcode', 'total_candidates', 'concentration',
                    'volume']

    IGNORE_COLUMNS = ['total_candidates']

    def __init__(self, session, sample_ids):
        """
        Constructor:

        :param session: The DB session to be used.

        :param sample_ids: The stock sample IDs that have been found in
            former queries (e.g. the :class:`StockSampleQuery`).
        :type sample_ids: collection of :class:`int`
        """
        TubePickingQuery.__init__(self, session=session)
        #: The IDs for the single molecule design pool stock samples.
        self.sample_ids = sample_ids

    def _get_params_for_sql_statement(self):
        sample_str = create_in_term_for_db_queries(self.sample_ids)
        return (sample_str, sample_str)

    def _store_result(self, result_record):
        candidate = self._create_candidate_from_query_result(result_record)
        self._results.append(candidate)


class TubePicker(BaseAutomationTool):
    """
    A base tool that picks tube for a set of molecule design pools and one
    concentration. It is possible to exclude certain racks and request special
    tubes.
    By default, candidates are ordered by request status (priority one) and
    volume (priority two).

    Subclasses may also add filter criteria.

    **Return Value:** the candidates objects
    """
    def __init__(self, log, molecule_design_pools, stock_concentration,
                 take_out_volume=None, excluded_racks=None,
                 requested_tubes=None):
        """
        Constructor:

        :param molecule_design_pools: The molecule design pool IDs for which
            to run the query.
        :type molecule_design_pools: :class:`set` of molecule design pool IDs

        :param stock_concentration: The stock concentration for the pools
            *in nM*.
        :type stock_concentration: :class:`int` (positive number)

        :param log: The log to record events.
        :type log: :class:`thelma.ThelmaLog`

        :param take_out_volume: The volume that shall be removed from the
            stock sample *in ul* - may be *None* (in this case we do not
            filter for at least stock dead volume).
        :type take_out_volume: :class:`int`

        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of tube barcodes.

        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for molecule design picking.
        :type excluded_racks: A list of rack barcodes
        """
        BaseAutomationTool.__init__(self, log=log)

        #: The molecule design pool IDs for which to run the query.
        self.molecule_design_pools = molecule_design_pools
        #: The stock concentration for the pools in nM.
        self.stock_concentration = stock_concentration
        #: The volume that shall be removed from the stock sample *in ul*
        #: - may be *None* (in this case we do not filter for at least stock
        #: dead volume).
        self.take_out_volume = take_out_volume

        if excluded_racks is None: excluded_racks = []
        #: A list of barcodes from stock racks that shall not be used for
        #: molecule design picking.
        self.excluded_racks = excluded_racks

        if requested_tubes is None: requested_tubes = []
        #: A list of barcodes from stock tubes that are supposed to be used
        #: (for fixed positions).
        self.requested_tubes = set(requested_tubes)

        #: The DB session used for the queries.
        self._session = None

        #: The pools mapped onto their IDs.
        self._pool_map = None
        #: Stores the suitable stock sample IDs for the pools. The results are
        #: determined by the :class:`SINGLE_POOL_QUERY`.
        self._stock_samples = None

        #: Returns all candidates in the same order as in the query result.
        #: Use :func:`get_unsorted_candidates` to acces this list.
        self._unsorted_candidates = None
        #: The picked candidates ordered by pools.
        self._picked_candidates = None

    def get_unsorted_candidates(self):
        """
        Returns all candidates in the same order as in the query result.
        """
        return self._get_additional_value(self._unsorted_candidates)

    def reset(self):
        BaseAutomationTool.reset(self)
        self._session = None
        self._pool_map = dict()
        self._stock_samples = []
        self._unsorted_candidates = []
        self._picked_candidates = dict()

    def run(self):
        self.reset()
        self.add_info('Start tube picking ...')

        self._check_input()
        if not self.has_errors(): self.__initialize_session()
        if not self.has_errors(): self._create_pool_map()
        if not self.has_errors(): self._get_stock_samples()
        if not self.has_errors(): self._run_optimizer()

        if not self.has_errors():
            self.return_value = self._picked_candidates
            del self._session
            self.add_info('Tube picker run completed.')

    def _check_input(self):
        """
        Checks the input values.
        """
        self.add_debug('Check input values ...')

        if isinstance(self.molecule_design_pools, (InstrumentedSet, list)):
            for pool in self.molecule_design_pools:
                self._check_input_class('molecule design pool', pool,
                                         MoleculeDesignPool)
            if len(self.molecule_design_pools) < 1:
                msg = 'The pool list is empty!'
                self.add_error(msg)
        else:
            msg = 'The pool list must be a list or an InstrumentedSet ' \
                  '(obtained: %s).' % \
                  (self.molecule_design_pools.__class__.__name__)
            self.add_error(msg)

        if not self.take_out_volume is None and \
                                not is_valid_number(self.take_out_volume):
            msg = 'The stock take out volume must be a positive number ' \
                  '(obtained: %s) or None.' % (self.take_out_volume)
            self.add_error(msg)

        if not is_valid_number(self.stock_concentration):
            msg = 'The stock concentration must be a positive number ' \
                  '(obtained: %s).' % (self.stock_concentration)
            self.add_error(msg)

        if self._check_input_class('excluded racks list',
                                       self.excluded_racks, list):
            for excl_rack in self.excluded_racks:
                if not self._check_input_class('excluded rack barcode',
                                               excl_rack, basestring): break
        if self._check_input_class('requested tubes list',
                                       self.requested_tubes, set):
            for req_tube in self.requested_tubes:
                if not self._check_input_class('requested tube barcode',
                                               req_tube, basestring): break

    def __initialize_session(self):
        """
        Initialises a session for ORM operations.
        """
        self._session = Session()

    def _create_pool_map(self):
        """
        Queries only return IDs that why we store a lookup.
        """
        for pool in self.molecule_design_pools:
            self._pool_map[pool.id] = pool

    def _get_stock_samples(self):
        """
        Determines suitable stock samples. Suitable tubes must be managed,
        and have the requested :attr:`stock_concentration`.
        """
        self.add_debug('Get stock samples ...')

        query = StockSampleQuery(session=self._session,
                                 pool_ids=self._pool_map.keys(),
                                 concentration=self.stock_concentration,
                                 minimum_volume=self.take_out_volume)
        self._run_and_record_error(query.run,
                       base_msg='Error when trying to query stock samples: ',
                       error_types=set(ValueError))

        if not self.has_errors():
            sample_map = query.get_query_results()
            found_pools = set()

            for pool_id, stock_sample_ids in sample_map.iteritems():
                found_pools.add(pool_id)
                self._stock_samples.extend(stock_sample_ids)

            if not len(found_pools) == len(self._pool_map):
                missing_pools = []
                for pool_id, md_id in self._pool_map.iteritems():
                    if not pool_id in found_pools:
                        missing_pools.append('%s (md: %s)' % (pool_id, md_id))
                msg = 'Could not find suitable source stock tubes for the ' \
                      'following molecule design pools: %s.' \
                      % (', '.join(sorted(missing_pools)))
                self.add_warning(msg)

    def _run_optimizer(self):
        """
        Runs the actual optimising query (by default we use the
        :class:`OptimizingQuery`).
        """
        self.add_debug('Run optimizing query ...')

        query = OptimizingQuery(session=self._session,
                                sample_ids=self._stock_samples)
        self._run_and_record_error(meth=query.run,
                        base_msg='Error when trying to run optimizing query: ',
                        error_types=set(ValueError))

        if not self.has_errors():
            candidates = query.get_query_results()
            for candidate in candidates:
                if candidate.rack_barcode in self.excluded_racks: continue
                self._store_candidate_data(candidate)

        if len(self._picked_candidates) < 1 and not self.has_errors():
            msg = 'Did not find any candidate!'
            self.add_error(msg)
        else:
            self._sort_candidates()

    def _store_candidate_data(self, candidate):
        """
        Stores the candidate in the :attr:`_picked_candidates` map. Subclasses
        may filter candidates here, too.
        """
        pool = self._pool_map[candidate.pool_id]
        add_list_map_element(self._picked_candidates, pool, candidate)

    def _sort_candidates(self):
        """
        By default, requested tubes come first. All other tubes are sorted
        by volume.
        """
        for pool, candidates in self._picked_candidates.iteritems():
            requested = []
            not_requested = []
            for candidate in candidates:
                if candidate.tube_barcode in self.requested_tubes:
                    clist = requested
                else:
                    clist = not_requested
                clist.append(candidate)
            sorted_candidates = self.__sort_by_volume(requested) \
                                + self.__sort_by_volume(not_requested)
            self._picked_candidates[pool] = sorted_candidates

    def __sort_by_volume(self, candidate_list):
        """
        Sorts the given candidates by volume (largest first).
        """
        sorted_candidates = []
        volume_map = dict()
        for candidate in candidate_list:
            add_list_map_element(volume_map, candidate.volume, candidate)
        for volume in sorted(volume_map.keys(), reverse=True):
            sorted_candidates.extend(volume_map[volume])
        return sorted_candidates

