"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Classes and queries involved in tube picking. The purpose is to find a tube
for a particular molecule design pool that can be used for an ISO. For this,
the stock sample must have a certain concentration and a certain minimum volume.

If there are several stock tubes available, it is possible to optimize the
tube picking. In this case the tube picker will choose the tube with the
lowest volume. If the number of pools is large, it is
also possible to try to minimize the number of stock racks used instead.

AAB
"""
from collections import OrderedDict

from sqlalchemy.orm.collections import InstrumentedSet

from thelma.tools.semiconstants import get_rack_position_from_indices
from thelma.tools.base import SessionTool
from thelma.tools.stock.base import STOCK_DEAD_VOLUME
from thelma.tools.stock.base import STOCK_ITEM_STATUS
from thelma.tools.stock.base import get_stock_tube_specs_db_term
from thelma.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.tools.utils.base import CustomQuery
from thelma.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.tools.utils.base import add_list_map_element
from thelma.tools.utils.base import create_in_term_for_db_queries
from thelma.tools.utils.base import is_valid_number
from thelma.entities.moleculedesign import MoleculeDesignPool


__docformat__ = 'reStructuredText en'

__all__ = ['StockSampleQuery',
           'TubePoolQuery',
           'TubeCandidate',
           'TubePickingQuery',
           'SinglePoolQuery',
           'MultiPoolQuery',
           'OptimizingQuery',
           'TubePicker']


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
    AND c.item_status = '%s'
    '''

    RESULT_COLLECTION_CLS = dict

    __POOL_COL_NAME = 'pool_id'
    __STOCK_SAMPLE_COL_NAME = 'stock_sample_id'

    COLUMN_NAMES = [__POOL_COL_NAME, __STOCK_SAMPLE_COL_NAME]

    __POOL_INDEX = COLUMN_NAMES.index(__POOL_COL_NAME)
    __STOCK_SAMPLE_INDEX = COLUMN_NAMES.index(__STOCK_SAMPLE_COL_NAME)

    def __init__(self, pool_ids, concentration, minimum_volume=None):
        """
        Constructor:

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
        CustomQuery.__init__(self)
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


class TubePoolQuery(CustomQuery):
    """
    This query is used to find the pool IDs for a set of tubes.

    The results are stored in a dictionary (pool IDs mapped onto tube barcodes).
    """
    QUERY_TEMPLATE = 'SELECT ss.molecule_design_set_id AS pool_id, ' \
                     ' t.barcode AS tube_barcode ' \
                     'FROM stock_sample ss, sample s, tube t ' \
                     'WHERE ss.sample_id = s.sample_id ' \
                     'AND s.container_id = t.container_id ' \
                     'AND t.barcode IN %s;'

    __POOL_COL_NAME = 'pool_id'
    __TUBE_BARCODE_COL_NAME = 'tube_barcode'

    COLUMN_NAMES = [__POOL_COL_NAME, __TUBE_BARCODE_COL_NAME]

    __POOL_INDEX = COLUMN_NAMES.index(__POOL_COL_NAME)
    __TUBE_BARCODE_INDEX = COLUMN_NAMES.index(__TUBE_BARCODE_COL_NAME)

    RESULT_COLLECTION_CLS = dict

    def __init__(self, tube_barcodes):
        """
        Constructor:

        :param requested_tubes: A list of barcodes from stock tubes.
        :type requested_tubes: :class:`list`
        """
        CustomQuery.__init__(self)

        #: A list of barcodes from stock tubes.
        self.tube_barcodes = tube_barcodes

    def _get_params_for_sql_statement(self):
        return create_in_term_for_db_queries(self.tube_barcodes, as_string=True)

    def _store_result(self, result_record):
        pool_id = result_record[self.__POOL_INDEX]
        tube_barcode = result_record[self.__TUBE_BARCODE_INDEX]
        self._results[tube_barcode] = pool_id


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

        self.__pool = None

    @property
    def pool_id(self):
        return self.__pool_id

    def get_pool(self):
        """
        Returns the pool as :class:`MoleculeDesignPool` entity (if it has
        been set before).
        """
        return self.__pool

    def set_pool(self, pool):
        """
        Sets the :class:`MoleculeDesignPool` entity. It must match the
        pool ID of the candidate otherwise a ValueError is raised.
        The pool could also be fetched via an aggregate, but this will take
        a long time if there is a large number of tube candidates.

        :param pool: The molecule design pool entity.
        :type pool: :class:`thelma.entities.moleculedesign.MoleculeDesignPool`
        :raises ValueError: If the ID of the pool does not match the candidate
            pool ID.
        """
        if not pool.id == self.__pool_id:
            msg = 'The pool does not have the expected ID (%i instead of %i).' \
                  % (pool.id, self.__pool_id)
            raise ValueError(msg)
        self.__pool = pool

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
    CANDIDATE_CLS = TubeCandidate

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

        for i in range(len(self.COLUMN_NAMES)):
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
    SELECT t.barcode AS tube_barcode, s.volume AS volume,
        rp.row_index AS row_index, rp.column_index AS column_index, r.barcode AS rack_barcode,
        ss.concentration AS concentration,
        ss.molecule_design_set_id AS pool_id
    FROM stock_sample ss, sample s, container c, tube t,
        container_specs cs, tube_location tl, rack_position rp, rack r
    WHERE ss.molecule_design_set_id %s %s
    AND ss.sample_id = s.sample_id
    AND ss.concentration = %s
    AND s.volume >= %s
    AND t.container_id = s.container_id
    AND c.container_id = t.container_id
    AND c.item_status = '%s'
    AND c.container_specs_id = cs.container_specs_id
    AND cs.name IN %s
    AND tl.container_id = c.container_id
    AND rp.rack_position_id = tl.rack_position_id
    AND tl.rack_id = r.rack_id
    '''

    COLUMN_NAMES = ['tube_barcode', 'volume', 'row_index', 'column_index',
                    'rack_barcode', 'concentration', 'pool_id']

    CANDIDATE_CLS = TubeCandidate

    def __init__(self, concentration, minimum_volume=None):
        """
        Constructor:

        :param concentration: The concentration of the stock sample *in nM*.
        :type concentration: positive number, unit nM

        :param minimum_volume: The minimum volume the tube must have *in ul* -
            the dead volume of the stock is added to it automatically.
            If you do pass a minimum volume all tubes are accepted.
        :type minimum_volume: positive number, unit ul
        """
        TubePickingQuery.__init__(self)

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

    The query results are a list of valid :class:`TubeCandidate` objects.
    """

    _POOL_OPERATOR = '='

    RESULT_COLLECTION_CLS = list

    def __init__(self, pool_id, concentration, minimum_volume=None):
        """
        Constructor:

        :param pool_id: The ID of the molecule design pool you need a tuube for.
        :type pool_id: :class:`int`

        :param concentration: The concentration of the stock sample *in nM*.
        :type concentration: positive number, unit nM

        :param minimum_volume: The minimum volume the tube must have *in ul* -
            the dead volume of the stock is added to it automatically.
            If you do pass a minimum volume all tubes are accepted.
        :type minimum_volume: positive number, unit ul
        """
        _PoolQuery.__init__(self, concentration=concentration,
                            minimum_volume=minimum_volume)
        #: The ID of the molecule design pool you need a tube for.
        self.pool_id = pool_id

    def _get_pool_id_term(self):
        return self.pool_id

    def _store_result(self, result_record):
        """
        Since there is only one pool we do not need to map the candidates.
        """
        candidate = self._create_candidate_from_query_result(result_record)
        self._results.append(candidate)


class MultiPoolQuery(_PoolQuery):
    """
    Used if there is you look for tube for several particular molecule
    design pool but do not require a rack number minimisation.
    """

    _POOL_OPERATOR = 'IN'

    def __init__(self, pool_ids, concentration, minimum_volume=None):
        """
        Constructor:

        :param pool_ids: The ID of the molecule design pools you need tubes for.
        :type pool_ids: iterable of :class:`int`

        :param concentration: The concentration of the stock sample *in nM*.
        :type concentration: positive number, unit nM

        :param minimum_volume: The minimum volume the tube must have *in ul* -
            the dead volume of the stock is added to it automatically.
            If you do pass a minimum volume all tubes are accepted.
        :type minimum_volume: positive number, unit ul
        """
        _PoolQuery.__init__(self, concentration=concentration,
                            minimum_volume=minimum_volume)

        #: The ID of the molecule design pools you need tubes for.
        self.pool_ids = pool_ids

    def _get_pool_id_term(self):
        return create_in_term_for_db_queries(self.pool_ids)


class OptimizingQuery(TubePickingQuery):
    """
    Optimized query for picking candidate tubes for an ISO from the stock.

    The optimization aims to minimize the number of source racks to use for
    an ISO.

    By default, the results are stored in a list (as :class:`TubeCandidates`)
    in the order of appearance.
    """
    RESULT_COLLECTION_CLS = list

    # The tricky part in this query is how the ranking score is computed:
    # We order the candidate samples by the number of distinct candidate
    # molecule design IDs found on each rack holding any of the candidate
    # samples. This minimizes the number of racks to pull from the stock.
    # Note that the nested GROUP BY statements are cleverly avoidig a
    # DISTINCT clause in the count expression for the desired count.
    QUERY_TEMPLATE = '''
    SELECT DISTINCT stock_sample.molecule_design_set_id AS pool_id,
           rack_tube_counts.rack_barcode AS rack_barcode,
           rack_position.row_index AS row_index,
           rack_position.column_index AS column_index,
           tube.barcode AS tube_barcode,
           rack_tube_counts.desired_count AS total_candidates,
           stock_sample.concentration AS concentration,
           sample.volume AS volume
    FROM stock_sample, sample, tube, tube_location, rack_position,
         (SELECT tmp.rack_id, tmp.rack_barcode AS rack_barcode,
                   COUNT(tmp.mds_cnt) AS desired_count
          FROM (SELECT xr.rack_id, xr.barcode AS rack_barcode,
                       xmds.molecule_design_set_id as mds_cnt
          FROM rack xr
          INNER JOIN tube_location xtl ON xtl.rack_id=xr.rack_id
          INNER JOIN sample xs ON xs.container_id=xtl.container_id
          INNER JOIN stock_sample xss ON xss.sample_id=xs.sample_id
          INNER JOIN molecule_design_set xmds
              ON xmds.molecule_design_set_id=xss.molecule_design_set_id
          WHERE xss.sample_id IN %s
          GROUP BY xr.rack_id, xmds.molecule_design_set_id
          HAVING COUNT(xtl.container_id) > 0 ) AS tmp
          GROUP BY tmp.rack_id, tmp.rack_barcode ) AS rack_tube_counts
    WHERE tube.container_id = tube_location.container_id
    AND rack_position.rack_position_id = tube_location.rack_position_id
    AND tube_location.rack_id = rack_tube_counts.rack_id
    AND tube.container_id = sample.container_id
    AND sample.sample_id = stock_sample.sample_id
    AND sample.sample_id IN %s
    ORDER BY rack_tube_counts.desired_count desc,
        rack_tube_counts.rack_barcode;
    '''

    COLUMN_NAMES = ['pool_id', 'rack_barcode', 'row_index', 'column_index',
                    'tube_barcode', 'total_candidates', 'concentration',
                    'volume']

    IGNORE_COLUMNS = ['total_candidates']

    def __init__(self, sample_ids):
        """
        Constructor:

        :param session: The DB session to be used.

        :param sample_ids: The stock sample IDs that have been found in
            former queries (e.g. the :class:`StockSampleQuery`).
        :type sample_ids: collection of :class:`int`
        """
        TubePickingQuery.__init__(self)
        #: The IDs for the single molecule design pool stock samples.
        self.sample_ids = sample_ids

    def _get_params_for_sql_statement(self):
        sample_str = create_in_term_for_db_queries(self.sample_ids)
        return (sample_str, sample_str)

    def _store_result(self, result_record):
        candidate = self._create_candidate_from_query_result(result_record)
        self._results.append(candidate)


class TubePicker(SessionTool):
    """
    A base tool that picks tube for a set of molecule design pools and one
    concentration. It is possible to exclude certain racks and request special
    tubes.
    By default, candidates are ordered by request status (priority one) and
    volume (priority two).

    Subclasses may also add filter criteria.

    **Return Value:** the candidates objects
    """
    NAME = 'Tube Picker'

    def __init__(self, molecule_design_pools, stock_concentration,
                 take_out_volume=None, excluded_racks=None,
                 requested_tubes=None, parent=None):
        """
        Constructor.

        :param set molecule_design_pools: Set of molecule design pools
            (:class:`thelma.entities.moleculedesign.MoleculeDesignPool`) for
            which to run the query.
        :type molecule_design_pools: :class:`set` of molecule design pools

        :param int stock_concentration: The stock concentration for the pools
            in nM (positive number).
        :param int take_out_volume: The volume that shall be removed from the
            stock sample *in ul* (positive number; may be *None*, in which
            case we do not filter for at least stock dead volume).
        :param list excluded_racks: List of barcodes from stock racks that shall
            not be used for molecule design picking.
        :param list requested_tubes: List of barcodes from stock tubes that are
            supposed to be used.
        """
        SessionTool.__init__(self, parent=parent)
        self.molecule_design_pools = molecule_design_pools
        self.stock_concentration = stock_concentration
        self.take_out_volume = take_out_volume
        if excluded_racks is None:
            excluded_racks = []
        self.excluded_racks = excluded_racks
        if requested_tubes is None:
            requested_tubes = []
        self.requested_tubes = requested_tubes
        #: The pools mapped onto their IDs.
        self._pool_map = None
        #: Stores the suitable stock sample IDs for the pools. The results are
        #: determined by the :class:`SINGLE_POOL_QUERY`.
        self._stock_samples = None
        #: Returns all candidates in the same order as in the query result.
        #: Use :func:`get_unsorted_candidates` to access this list.
        self._unsorted_candidates = None
        #: The picked candidates ordered by pools.
        self._picked_candidates = None

    def get_unsorted_candidates(self):
        """
        Returns all candidates in the same order as in the query result.
        """
        return self._get_additional_value(self._unsorted_candidates)

    def reset(self):
        SessionTool.reset(self)
        self._pool_map = dict()
        self._stock_samples = []
        self._unsorted_candidates = []
        self._picked_candidates = OrderedDict()

    def run(self):
        self.reset()
        self.add_info('Start tube picking ...')
        self._check_input()
        if not self.has_errors():
            self._create_pool_map()
        if not self.has_errors():
            self._get_stock_samples()
        if not self.has_errors() and len(self._stock_samples) > 0:
            self._run_optimizer()
        if not self.has_errors():
            self._look_for_missing_candidates()
        if not self.has_errors():
            self.return_value = self._picked_candidates
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
        self._check_input_list_classes('excluded rack', self.excluded_racks,
                                       basestring, may_be_empty=True)
        if self._check_input_list_classes('requested tube',
                    self.requested_tubes, basestring, may_be_empty=True):
            self.requested_tubes = set(self.requested_tubes)

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
        query = StockSampleQuery(pool_ids=self._pool_map.keys(),
                                 concentration=self.stock_concentration,
                                 minimum_volume=self.take_out_volume)
        self._run_query(query, 'Error when trying to query stock samples: ')
        if not self.has_errors():
            sample_map = query.get_query_results()
            found_pools = set()

            for pool_id, stock_sample_ids in sample_map.iteritems():
                found_pools.add(pool_id)
                self._stock_samples.extend(stock_sample_ids)

            if len(found_pools) < 1:
                msg = 'Did not find any candidate!'
                self.add_error(msg)
            elif not len(found_pools) == len(self._pool_map):
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
        query = OptimizingQuery(sample_ids=self._stock_samples)
        self._run_query(query, 'Error when trying to run optimizing query: ')
        if not self.has_errors():
            self._unsorted_candidates = query.get_query_results()
            for candidate in self._unsorted_candidates:
                if candidate.rack_barcode in self.excluded_racks:
                    continue
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
        By default, requested tubes come first.
        """
        if isinstance(self._picked_candidates, dict):
            for pool, candidates in self._picked_candidates.iteritems():
                sorted_candidates = self.__sort_candidate_list(candidates)
                self._picked_candidates[pool] = sorted_candidates
        else:
            self._picked_candidates = self.__sort_candidate_list(
                                                    self._picked_candidates)

    def __sort_candidate_list(self, candidates):
        # Helper method sorting the given list of candidates.
        # Requested tubes come first. The remaining tubes are sorted by volume.
        requested = []
        not_requested = []
        for candidate in candidates:
            if candidate.tube_barcode in self.requested_tubes:
                clist = requested
            else:
                clist = not_requested
            clist.append(candidate)
        return requested + not_requested

    def _look_for_missing_candidates(self):
        """
        By default we check whether there is a candidate for each requested
        molecule design pool.
        """
        found_pools = set()
        if isinstance(self._picked_candidates, dict):
            for pool, candidates in self._picked_candidates.iteritems():
                if len(candidates) > 0:
                    found_pools.add(pool)
        else:
            for candidate in self._picked_candidates:
                found_pools.add(candidate.pool)

        if not len(found_pools) == len(self.molecule_design_pools):
            diff = []
            for pool in self.molecule_design_pools:
                if not pool in found_pools: diff.append(pool)
            msg = 'Unable to find valid tubes for the following pools: ' \
                  '%s.' % (self._get_joined_str(diff, is_strs=False))
            self.add_warning(msg)
