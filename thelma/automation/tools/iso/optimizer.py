"""
These classes run the the optimisation query for the ISO creation. It aims
to minimise the number of stock rack that have to be taken from the DB.

AAB
"""

from everest.repositories.rdb import Session
from sqlalchemy.orm.exc import NoResultFound
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.iso.prep_utils import PrepIsoLayout
from thelma.automation.tools.iso.prep_utils import get_stock_takeout_volume
from thelma.automation.tools.semiconstants import get_rack_position_from_indices
from thelma.automation.tools.stock.base import STOCK_DEAD_VOLUME
from thelma.automation.tools.stock.base import STOCK_ITEM_STATUS
from thelma.automation.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import add_list_map_element
from thelma.automation.tools.utils.base import create_in_term_for_db_queries
from thelma.automation.tools.utils.iso import IsoPosition


__docformat__ = 'reStructuredText en'

__all__ = ['IsoOptimizer',
           'OPTIMIZATION_QUERY',
           'IsoCandidate']


class IsoOptimizer(BaseAutomationTool):
    """
    Runs the optimisation query for the given set of molecule design pools.

    **Return Value:** The ISO candidates of the query result
        (in unchanged order).
    """

    NAME = 'ISO Optimizer'

    def __init__(self, molecule_design_pools, preparation_layout, log,
                 excluded_racks=None):
        """
        Constructor:

        :param molecule_design_pools: The molecule design pool IDs for which
            to run the query.
        :type molecule_design_pools: :class:`set` of molecule design pool IDs

        :param preparation_layout: The (abstract) preparation layout for
            the ISO request.
        :type preparation_layout: :class:`preparation_layout`

        :param log: The log to record events.
        :type log: :class:`thelma.ThelmaLog`

        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for molecule design picking.
        :type excluded_racks: A list of rack barcodes
        """
        BaseAutomationTool.__init__(self, log=log)

        #: The molecule design pool IDs for which to run the query.
        self.molecule_design_pools = molecule_design_pools
        #: The (abstract) preparation layout for the ISO request.
        self.prep_layout = preparation_layout

        if excluded_racks is None: excluded_racks = []
        #: A list of barcodes from stock racks that shall not be used for
        #: molecule design picking.
        self.excluded_racks = excluded_racks

        #: The DB session used for the queries.
        self.__session = None

        #: All available stock sample for the queued molecule design pools
        #: (filtered by supplier, if applicable).
        self.__stock_samples = None

        #: The ISO candidates for each molecule design in unchaged order.
        self.__candidates = None

    def reset(self):
        """
        Resets the initialisation values.
        """
        BaseAutomationTool.reset(self)
        self.__session = None
        self.__stock_samples = []
        self.__candidates = []

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Optimisation query is prepared ...')
        self.__check_input()
        if not self.has_errors():
            self.__initialize_session()
            self.__get_stock_sample_ids()
        if not self.has_errors():
            self.__run_query()
        if not self.has_errors():
            self.return_value = self.__candidates
            self.add_info('Query run completed.')

    def __initialize_session(self):
        """
        Initialises a session for ORM operations.
        """
        self.__session = Session()

    def __check_input(self):
        """
        Checks the input values.
        """
        self.add_debug('Check input values ...')

        self._check_input_class('preparation plate layout', self.prep_layout,
                                PrepIsoLayout)

        if self._check_input_class('molecule design pool list',
                                   self.molecule_design_pools, set):
            for pool_id in self.molecule_design_pools:
                if not self._check_input_class('molecule design pool ID',
                                               pool_id, int): break
            if len(self.molecule_design_pools) < 1:
                self.add_error('The molecule design pool list is empty!')

        if self._check_input_class('excluded racks list',
                                       self.excluded_racks, list):
            for excl_rack in self.excluded_racks:
                if not self._check_input_class('excluded rack barcode',
                                               excl_rack, basestring): break

    def __get_stock_sample_ids(self):
        """
        Runs as DB query fetching all stock samples available for the pools.
        """
        self.add_debug('Get stock sample IDs ...')

        base_query = 'SELECT stock_sample.sample_id FROM stock_sample ' \
                     'WHERE stock_sample.molecule_design_set_id IN %s'

        supplier_map = self.__sort_pools_by_supplier()
        for supplier_id, pool_ids in supplier_map.iteritems():
            pool_tuple = create_in_term_for_db_queries(pool_ids)
            query_statement = base_query % (pool_tuple)
            if supplier_id != IsoPosition.ANY_SUPPLIER_INDICATOR:
                supplier_constraint = ' AND stock_sample.supplier_id = %i' \
                                     % (supplier_id)
                query_statement += supplier_constraint

            results = self.__session.query('sample_id').from_statement(
                                        query_statement).all()
            for record in results:
                self.__stock_samples.append(record[0])

        if len(self.__stock_samples) < 1:
            msg = 'Could not find stock sample IDs for the given molecule ' \
                  'design pools and suppliers!'
            self.add_error(msg)

    def __sort_pools_by_supplier(self):
        """
        Pools without supplier specification are marked with 'any'.
        """
        sorted_pools = dict()

        supplier_map = self.prep_layout.get_supplier_map()
        for pool_id in self.molecule_design_pools:
            if supplier_map.has_key(pool_id):
                supplier_id = supplier_map[pool_id]
            else:
                supplier_id = IsoPosition.ANY_SUPPLIER_INDICATOR
            add_list_map_element(sorted_pools, supplier_id, pool_id)

        return sorted_pools

    def __run_query(self):
        """
        Prepares and sends the optimisation query.
        """
        self.add_debug('Run optimisation query ...')
        params = self.__fetch_query_parameters()
        opt_query = OPTIMIZATION_QUERY.QUERY_TEMPLATE % (params)
        query_values = OPTIMIZATION_QUERY.QUERY_RESULT_VALUES

        no_result_msg = 'The optimisation query did not return any result.'

        try:
            #pylint: disable=W0142
            results = self.__session.query(*query_values).\
                                        from_statement(opt_query).all()
            #pylint: enable=W0142
        except NoResultFound:
            self.add_error(no_result_msg)
        else:
            for record in results:
                candidate = IsoCandidate.create_from_query_result(record)
                if not candidate.rack_barcode in self.excluded_racks:
                    self.__candidates.append(candidate)

        if len(self.__candidates) < 1: self.add_error(no_result_msg)

    def __fetch_query_parameters(self):
        """
        Creates a tuple containing the values to be inserted into the
        SQL optimisation query template.
        """

        # fetch all parameters
        vol_in_ul = self.__get_volume()
        concentration_clause = self.__get_stock_concentration_clause()
        volume = vol_in_ul / VOLUME_CONVERSION_FACTOR
        sample_string = create_in_term_for_db_queries(self.__stock_samples)

        base_params = (STOCK_ITEM_STATUS, sample_string, concentration_clause,
                       volume)

        # compile parameters
        params_list = []
        for param in base_params: params_list.append(param)
        for param in base_params: params_list.append(param)
        return tuple(params_list)

    def __get_volume(self):
        """
        Determines the largest volume needed.
        """
        floating_volume = STOCK_DEAD_VOLUME
        fixed_volume = STOCK_DEAD_VOLUME

        prep_layout_pools = set()
        for prep_pos in self.prep_layout.working_positions():
            if prep_pos.is_mock: continue
            if not prep_pos.parent_well is None: continue
            if prep_pos.is_floating:
                volume = get_stock_takeout_volume(
                            stock_concentration=self.prep_layout.\
                                                floating_stock_concentration,
                            required_volume=prep_pos.required_volume,
                            concentration=prep_pos.prep_concentration)
                floating_volume = max(floating_volume, volume)
            else:
                volume = prep_pos.get_stock_takeout_volume()
                pool_id = prep_pos.molecule_design_pool_id
                if not pool_id in self.molecule_design_pools: continue
                prep_layout_pools.add(pool_id)
                fixed_volume = max(fixed_volume, volume)

        fixed_only = True
        floating_only = True
        for pool_id in self.molecule_design_pools:
            if not pool_id in prep_layout_pools:
                fixed_only = False
            else:
                floating_only = False

        if fixed_only:
            return fixed_volume
        elif floating_only:
            return floating_volume
        else:
            volume = max(fixed_volume, floating_volume)
            return volume

    def __get_stock_concentration_clause(self):
        """
        There is two different clauses, depending on whether we have one
        or several different stock concentrations.
        """
        self.add_debug('Determine stock concentration ...')

        concentrations = set()
        if not self.prep_layout.floating_stock_concentration is None:
            concentrations.add(self.prep_layout.floating_stock_concentration)

        for prep_pos in self.prep_layout.working_positions():
            if not prep_pos.is_fixed: continue
            stock_conc = prep_pos.stock_concentration
            if not stock_conc is None:
                concentrations.add(stock_conc)

        if len(concentrations) == 1:
            conc = list(concentrations)[0] / CONCENTRATION_CONVERSION_FACTOR
            clause = OPTIMIZATION_QUERY.CONCENTRATION_EQUALS_CLAUSE % (conc)
        else:
            corr_values = []
            for conc in concentrations:
                corr_values.append(conc / CONCENTRATION_CONVERSION_FACTOR)
            in_tuple = create_in_term_for_db_queries(corr_values)
            clause = OPTIMIZATION_QUERY.CONCENTRATION_IN_CLAUSE % (in_tuple)
        return clause


class OPTIMIZATION_QUERY(object):

    #: the query template
    QUERY_TEMPLATE = '''\
    SELECT DISTINCT stock_sample.molecule_design_set_id AS pool_id,
           rack_tube_counts.rack_barcode AS rack_barcode,
           containment.row AS row_index,
           containment.col AS column_index,
           container_barcode.barcode AS container_barcode,
           rack_tube_counts.desired_count AS total_candidates,
           stock_sample.concentration AS concentration
    FROM stock_sample, sample, container, container_barcode, containment,
         (SELECT xr.rack_id, xr.barcode AS rack_barcode,
                   COUNT(xc.container_id) AS desired_count
          FROM rack xr, containment xrc, container xc, sample xs,
               stock_sample xss
          WHERE xr.rack_id = xrc.holder_id
          AND xc.container_id = xrc.held_id
          AND xc.item_status = \'%s\'
          AND xc.container_id = xs.container_id
          AND xs.sample_id = xss.sample_id
          AND xs.sample_id IN %s
          AND xss.concentration %s
          AND xs.volume >= %s
          GROUP BY xr.rack_id, xr.barcode
          HAVING COUNT(xc.container_id) > 0 ) AS rack_tube_counts
    WHERE container.container_id = containment.held_id
    AND containment.holder_id = rack_tube_counts.rack_id
    AND container.container_id = sample.container_id
    AND container.item_status = \'%s\'
    AND container_barcode.container_id = container.container_id
    AND sample.sample_id = stock_sample.sample_id
    AND sample.sample_id IN %s
    AND stock_sample.concentration %s
    AND sample.volume >= %s
    ORDER BY rack_tube_counts.desired_count desc, rack_tube_counts.rack_barcode;
    '''

    #: The key for molecule design pool IDs.
    POOL_KEY = 'pool_id'
    #: The key for rack barcodes.
    RACK_BARCODE_KEY = 'rack_barcode'
    #: The key for the row of an container location (rack position).
    CONTAINER_LOCATION_ROW_KEY = 'row_index'
    #: The key for the column of an container location (rack position).
    CONTAINER_LOCATION_COLUMN_KEY = 'column_index'
    #: The key for the tube barcode.
    TUBE_BARCODE_KEY = 'container_barcode'
    #: The key for the total number of candidates.
    CANDIDATE_NUMBER_KEY = 'total_candidates'
    #: The key for the concentration of the candidate.
    CONCENTRATION_KEY = 'concentration'

    #: A tuple containing the query result specifications in the right order
    #: (required for the :class:`Query` object built by the ORM).
    QUERY_RESULT_VALUES = (POOL_KEY,
                           RACK_BARCODE_KEY,
                           CONTAINER_LOCATION_ROW_KEY,
                           CONTAINER_LOCATION_COLUMN_KEY,
                           TUBE_BARCODE_KEY,
                           CANDIDATE_NUMBER_KEY,
                           CONCENTRATION_KEY)

    #: The index of molecule design pool IDs in the query result.
    POOL_INDEX = QUERY_RESULT_VALUES.index(POOL_KEY)
    #: The index for rack barcodes in the query result.
    RACK_BARCODE_INDEX = QUERY_RESULT_VALUES.index(RACK_BARCODE_KEY)
    #: The index for the row of an container location (rack position) in the
    #: query result.
    CONTAINER_LOCATION_ROW_INDEX = \
                        QUERY_RESULT_VALUES.index(CONTAINER_LOCATION_ROW_KEY)
    #: The index for the column of an container location (rack position) in
    #: the query result..
    CONTAINER_LOCATION_COLUMN_INDEX = \
                    QUERY_RESULT_VALUES.index(CONTAINER_LOCATION_COLUMN_KEY)
    #: The index for the tube barcode in the query result..
    TUBE_BARCODE_INDEX = QUERY_RESULT_VALUES.index(TUBE_BARCODE_KEY)
    #: The index for the total number of candidates in the query result.
    CANDIDATE_NUMBER_INDEX = QUERY_RESULT_VALUES.index(CANDIDATE_NUMBER_KEY)
    #: The index for the tube concentration in the query result.
    CONCENTRATION_INDEX = QUERY_RESULT_VALUES.index(CONCENTRATION_KEY)

    #: The concentration clause if all molecules have the same stock
    #: concentration (equals clause).
    CONCENTRATION_EQUALS_CLAUSE = '= %s'
    #: The concentration clause used if there are different stock
    #: concentrations (in clause).
    CONCENTRATION_IN_CLAUSE = 'IN %s'


class IsoCandidate(object):
    """
    A candidate's results derived from an optimisation query.
    """

    def __init__(self, pool_id, rack_barcode, rack_position,
                 container_barcode, concentration):
        """
        Constructor. Attributes are immutable.
        """
        self.__pool_id = pool_id
        self.__rack_barcode = rack_barcode
        self.__rack_position = rack_position
        self.__container_barcode = container_barcode
        self.__concentration = concentration * CONCENTRATION_CONVERSION_FACTOR

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
    def container_barcode(self):
        return self.__container_barcode

    @property
    def concentration(self):
        return self.__concentration

    @classmethod
    def create_from_query_result(cls, result_record):
        """
        Factory method creating a IsoCandidate instance from an
        optimisation query result record.
        """

        pool_id = result_record[OPTIMIZATION_QUERY.POOL_INDEX]
        rack_barcode = result_record[OPTIMIZATION_QUERY.RACK_BARCODE_INDEX]
        row = result_record[OPTIMIZATION_QUERY.CONTAINER_LOCATION_ROW_INDEX]
        column = result_record[OPTIMIZATION_QUERY.CONTAINER_LOCATION_COLUMN_INDEX]
        rack_position = get_rack_position_from_indices(row, column)
        container_barcode = result_record[OPTIMIZATION_QUERY.TUBE_BARCODE_INDEX]
        concentration = result_record[OPTIMIZATION_QUERY.CONCENTRATION_INDEX]

        iso_candidate = IsoCandidate(pool_id, rack_barcode, rack_position,
                                     container_barcode, concentration)
        return iso_candidate

    def __str__(self):
        return '%i-%s' % (self.__pool_id, self.__rack_barcode)

    def __repr__(self):
        str_format = '<IsoCandidate molecule design pool ID: %i, ' \
                     'rack barcode: %s, rack position: %s, container ' \
                     'barcode: %s, concentration: %s nM>'
        params = (self.__pool_id, self.__rack_barcode, self.__rack_position,
                  self.__container_barcode, self.__concentration)
        return str_format % params

    def __eq__(self, other):
        return isinstance(other, IsoCandidate) \
            and other.pool_id == self.__pool_id \
            and other.rack_barcode == self.__rack_barcode \
            and other.rack_position == self.__rack_position \
            and other.container_barcode == self.__container_barcode \
            and other.concentration == self.__concentration

    def __ne__(self, other):
        return not (self.__eq__(other))


class IsoVolumeSpecificOptimizer(BaseAutomationTool):
    """
    This special optimizer runs a query for each volume found instead of
    using the maximum volume.

    :Note: This class is a hack that should become expendable due to the
    ISO processing revision.

    **Return Value:** The ISO candidates of the query result
        (in unchanged order).
    """
    NAME = 'ISO Volume Specific Optimizer'

    def __init__(self, molecule_design_pools, preparation_layout, log,
                 excluded_racks=None):
        """
        Constructor:

        :param molecule_design_pools: The molecule design pool IDs for which
            to run the query.
        :type molecule_design_pools: :class:`set` of molecule design pool IDs

        :param preparation_layout: The (abstract) preparation layout for
            the ISO request.
        :type preparation_layout: :class:`preparation_layout`

        :param log: The log to record events.
        :type log: :class:`thelma.ThelmaLog`

        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for molecule design picking.
        :type excluded_racks: A list of rack barcodes
        """
        BaseAutomationTool.__init__(self, log=log)

        #: The molecule design pool IDs for which to run the query.
        self.molecule_design_pools = molecule_design_pools
        #: The (abstract) preparation layout for the ISO request.
        self.prep_layout = preparation_layout

        if excluded_racks is None: excluded_racks = []
        #: A list of barcodes from stock racks that shall not be used for
        #: molecule design picking.
        self.excluded_racks = excluded_racks

        #: The DB session used for the queries.
        self.__session = None

        #: All available stock samples for the queued molecule design pools
        #: (filtered by supplier, if applicable) mapped onto pool IDs.
        self.__stock_samples = None

        #: The pool ID for each take out volume.
        self.__volume_map = None

        #: The ISO candidates for each molecule design in unchaged order.
        self.__candidates = None

    def reset(self):
        """
        Resets the initialisation values.
        """
        BaseAutomationTool.reset(self)
        self.__session = None
        self.__stock_samples = dict()
        self.__candidates = []
        self.__volume_map = dict()

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Optimisation query is prepared ...')
        self.__check_input()
        if not self.has_errors():
            self.__initialize_session()
            self.__get_stock_sample_ids()
        if not self.has_errors():
            self.__sort_by_volumes()
        if not self.has_errors():
            self.__run_queries()
        if not self.has_errors():
            self.return_value = self.__candidates
            self.add_info('Query run completed.')

    def __initialize_session(self):
        """
        Initialises a session for ORM operations.
        """
        self.__session = Session()

    def __check_input(self):
        """
        Checks the input values.
        """
        self.add_debug('Check input values ...')

        self._check_input_class('preparation plate layout', self.prep_layout,
                                PrepIsoLayout)

        if self._check_input_class('molecule design pool list',
                                   self.molecule_design_pools, set):
            for pool_id in self.molecule_design_pools:
                if not self._check_input_class('molecule design pool ID',
                                               pool_id, int): break
            if len(self.molecule_design_pools) < 1:
                self.add_error('The molecule design pool list is empty!')

        if self._check_input_class('excluded racks list',
                                       self.excluded_racks, list):
            for excl_rack in self.excluded_racks:
                if not self._check_input_class('excluded rack barcode',
                                               excl_rack, basestring): break

    def __get_stock_sample_ids(self):
        """
        Runs as DB query fetching all stock samples available for the pools.
        """
        self.add_debug('Get stock sample IDs ...')

        base_query = 'SELECT stock_sample.sample_id AS sample_id, ' \
                     '  stock_sample.molecule_design_set_id AS pool_id ' \
                     'FROM stock_sample ' \
                     'WHERE stock_sample.molecule_design_set_id IN %s'
        result_values = ('sample_id', 'pool_id')

        supplier_map = self.__sort_pools_by_supplier()
        for supplier_id, pool_ids in supplier_map.iteritems():
            pool_tuple = create_in_term_for_db_queries(pool_ids)
            query_statement = base_query % (pool_tuple)
            if supplier_id != IsoPosition.ANY_SUPPLIER_INDICATOR:
                supplier_constraint = ' AND stock_sample.supplier_id = %i' \
                                     % (supplier_id)
                query_statement += supplier_constraint

            results = self.__session.query(*result_values).from_statement(
                                           query_statement).all()
            for record in results:
                sample_id = record[0]
                pool_id = record[1]
                add_list_map_element(self.__stock_samples, pool_id, sample_id)

        if len(self.__stock_samples) < 1:
            msg = 'Could not find stock sample IDs for the given molecule ' \
                  'design pools and suppliers!'
            self.add_error(msg)

    def __sort_pools_by_supplier(self):
        """
        Pools without supplier specification are marked with 'any'.
        """
        sorted_pools = dict()

        supplier_map = self.prep_layout.get_supplier_map()
        for pool_id in self.molecule_design_pools:
            if supplier_map.has_key(pool_id):
                supplier_id = supplier_map[pool_id]
            else:
                supplier_id = IsoPosition.ANY_SUPPLIER_INDICATOR
            add_list_map_element(sorted_pools, supplier_id, pool_id)

        return sorted_pools

    def __sort_by_volumes(self):
        """
        Gets the take out volume for each pool.
        """
        self.add_debug('Sort by volumes ...')

        is_floating = []
        volumes = dict()

        for prep_pos in self.prep_layout.working_positions():
            if prep_pos.is_mock: continue
            pool_id = prep_pos.molecule_design_pool_id
            if not pool_id in self.molecule_design_pools: continue
            if prep_pos.is_floating:
                is_floating.append(pool_id)
                continue
            volume = prep_pos.get_stock_takeout_volume()
            if volume is None: continue # happens if not a starting well
            if not volumes.has_key(pool_id):
                volumes[pool_id] = STOCK_DEAD_VOLUME
            volumes[pool_id] += volume

        if len(is_floating) > 0:
            msg = 'Volume specific optimizing is not allowed for floating ' \
                   'positions. The following pools belongt to floating ' \
                   'positions: %s.' \
                   % (', '.join([str(pi) for pi in sorted(is_floating)]))
            self.add_error(msg)
        else:
            for pool_id, volume in volumes.iteritems():
                add_list_map_element(self.__volume_map, volume, pool_id)

    def __run_queries(self):
        """
        Prepares and sends the optimisation query.
        """
        self.add_debug('Run optimisation queries ...')

        no_result_msg = 'The optimisation query did not return any result.'
        for volume, pool_ids in self.__volume_map.iteritems():
            params = self.__fetch_query_parameters(volume, pool_ids)
            opt_query = OPTIMIZATION_QUERY.QUERY_TEMPLATE % (params)
            query_values = OPTIMIZATION_QUERY.QUERY_RESULT_VALUES

            try:
                #pylint: disable=W0142
                results = self.__session.query(*query_values).\
                                            from_statement(opt_query).all()
                #pylint: enable=W0142
            except NoResultFound:
                self.add_error(no_result_msg)
            else:
                for record in results:
                    candidate = IsoCandidate.create_from_query_result(record)
                    if not candidate.rack_barcode in self.excluded_racks:
                        self.__candidates.append(candidate)

        if len(self.__candidates) < 1: self.add_error(no_result_msg)

    def __fetch_query_parameters(self, volume_in_ul, pool_ids):
        """
        Creates a tuple containing the values to be inserted into the
        SQL optimisation query template.
        """
        # fetch all parameters
        concentration_clause = self.__get_stock_concentration_clause(pool_ids)
        volume = volume_in_ul / VOLUME_CONVERSION_FACTOR
        query_sample_ids = []
        for pool_id in pool_ids:
            query_sample_ids.extend(self.__stock_samples[pool_id])
        sample_string = create_in_term_for_db_queries(query_sample_ids)

        base_params = (STOCK_ITEM_STATUS, sample_string, concentration_clause,
                       volume)

        # compile parameters
        params_list = []
        for param in base_params: params_list.append(param)
        for param in base_params: params_list.append(param)
        return tuple(params_list)

    def __get_volume(self):
        """
        Determines the largest volume needed.
        """
        floating_volume = 0
        fixed_volume = 0

        prep_layout_pools = set()
        for prep_pos in self.prep_layout.working_positions():
            if prep_pos.is_mock: continue
            if not prep_pos.parent_well is None: continue
            if prep_pos.is_floating:
                volume = get_stock_takeout_volume(
                            stock_concentration=self.prep_layout.\
                                                floating_stock_concentration,
                            required_volume=prep_pos.required_volume,
                            concentration=prep_pos.prep_concentration)
                floating_volume = max(floating_volume, volume)
            else:
                volume = prep_pos.get_stock_takeout_volume()
                pool_id = prep_pos.molecule_design_pool_id
                if not pool_id in self.molecule_design_pools: continue
                prep_layout_pools.add(pool_id)
                fixed_volume = max(fixed_volume, volume)

        fixed_only = True
        floating_only = True
        for pool_id in self.molecule_design_pools:
            if not pool_id in prep_layout_pools:
                fixed_only = False
            else:
                floating_only = False

        if fixed_only:
            return fixed_volume
        elif floating_only:
            return floating_volume
        else:
            volume = max(fixed_volume, floating_volume)
            return volume

    def __get_stock_concentration_clause(self, pool_ids):
        """
        There is two different clauses, depending on whether we have one
        or several different stock concentrations.
        """
        self.add_debug('Determine stock concentration ...')

        concentrations = set()
        for prep_pos in self.prep_layout.working_positions():
            if not prep_pos.molecule_design_pool_id in pool_ids: continue
            stock_conc = prep_pos.stock_concentration
            if not stock_conc is None: concentrations.add(stock_conc)

        if len(concentrations) == 1:
            conc = list(concentrations)[0] / CONCENTRATION_CONVERSION_FACTOR
            clause = OPTIMIZATION_QUERY.CONCENTRATION_EQUALS_CLAUSE % (conc)
        else:
            corr_values = []
            for conc in concentrations:
                corr_values.append(conc / CONCENTRATION_CONVERSION_FACTOR)
            in_tuple = create_in_term_for_db_queries(corr_values)
            clause = OPTIMIZATION_QUERY.CONCENTRATION_IN_CLAUSE % (in_tuple)
        return clause
