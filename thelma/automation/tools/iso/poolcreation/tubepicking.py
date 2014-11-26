"""
Deals with tube picking optimisation for pool stock sample creations.

AAB
"""
from thelma.automation.tools.stock.tubepicking import OptimizingQuery
from thelma.automation.tools.stock.tubepicking import TubePicker
from thelma.automation.utils.base import CustomQuery
from thelma.automation.utils.base import add_list_map_element
from thelma.automation.utils.base import create_in_term_for_db_queries
from collections import OrderedDict

__docformat__ = 'reStructuredText en'

__all__ = ['StockSampleCreationTubePicker',
           'PoolCandidate',
           'SingleDesignPoolQuery',
           'PoolGenerationOptimizationQuery']


class StockSampleCreationTubePicker(TubePicker):
    """
    Picks tubes for the single design pools the new pool stock samples will
    be composed of.

    :Note: Unlike as in the super class the picked candidates are passed as
    list.

    **Return Value:** the :class:`PoolCandidate` objects in the order
        of completion (as list)
    """
    NAME = 'Stock Sample Creation Optimizer'

    def __init__(self, molecule_design_pools, single_design_concentration,
                 take_out_volume, excluded_racks=None, requested_tubes=None,
                 parent=None):
        TubePicker.__init__(self, molecule_design_pools,
                            single_design_concentration,
                            take_out_volume=take_out_volume,
                            excluded_racks=excluded_racks,
                            requested_tubes=requested_tubes,
                            parent=parent)
        #: The pool candidates mapped onto pool IDs.
        self.__pool_candidates = None
        #: Maps multi-pool IDs onto molecule design IDs. ATTENTION: a multi
        #: molecule design pool can point to several set pools! For this reason,
        #: multi-pool IDs are stored in lists.
        self.__md_map = None
        #: Maps molecule design IDs onto single molecule design pool IDs.
        self.__single_pool_map = None
        #: If an siRNA is used in several pools this map will store the data
        #: of which ISO candidate has been used for which one.
        self.__multi_pool_tube_candidates = None
        #: Set of IDs that have been picked.
        self.__picked_pool_ids = None

    def reset(self):
        TubePicker.reset(self)
        self._picked_candidates = []
        self.__pool_candidates = {}
        self.__md_map = dict()
        self.__single_pool_map = dict()
        self.__multi_pool_tube_candidates = dict()
        self.__picked_pool_ids = set()

    def _create_pool_map(self):
        """
        We do not look for stock samples for the new pools but for the single
        design pools they are composed of.
        """
        self.__create_pool_candidates()
        self.__get_single_pools()

    def __create_pool_candidates(self):
        # Initialises empty pool candidates (without stock sample data and
        #candidates) for every pool to be generate.
        self.add_debug('Initialise library candidates ...')
        for pool in self.molecule_design_pools:
            pool_cand = PoolCandidate(pool)
            self.__pool_candidates[pool.id] = pool_cand
            for md_id in pool_cand.get_molecule_design_ids():
                add_list_map_element(self.__md_map, md_id, pool.id)

    def __get_single_pools(self):
        # Determines the single pool (ID) for each requested molecule design.
        # Uses the :class:`SingleDesignPoolQuery`.
        self.add_debug('Get single molecule design pool ...')
        query = \
            SingleDesignPoolQuery(molecule_design_ids=self.__md_map.keys())
        self._run_query(query,
                        base_error_msg='Error when trying to query ' \
                                        'single molecule design pools: ')
        if not self.has_errors():
            self.__single_pool_map = query.get_query_results()
            if not len(self.__single_pool_map) == len(self.__md_map):
                missing_ids = []
                for md_id in self.__md_map.keys():
                    if not self.__single_pool_map.has_key(md_id):
                        missing_ids.append(md_id)
                msg = 'Could not find single molecule design pool for the ' \
                      'following molecule designs: %s.' % (', '.join(
                                [str(md_id) for md_id in sorted(missing_ids)]))
                self.add_error(msg)
            else:
                self._pool_map = self.__single_pool_map

    def _store_candidate_data(self, tube_candidate):
        # Adds an ISO candidate to an library candidate and moves the
        # library candidate once it is completed.
        single_pool_id = tube_candidate.pool_id
        md_id = self.__single_pool_map[single_pool_id]
        pool_ids = self.__md_map[md_id]
        if len(pool_ids) == 1:
            pool_id = pool_ids[0]
        else:
            for ambi_pool_id in pool_ids:
                pool_id = None
                if not self.__multi_pool_tube_candidates.has_key(ambi_pool_id):
                    self.__multi_pool_tube_candidates[ambi_pool_id] = \
                                                            tube_candidate
                    pool_id = ambi_pool_id
                if pool_id is None:
                    pool_id = pool_ids[0]
        pool_cand = self.__pool_candidates[pool_id]
        is_requested = tube_candidate.tube_barcode in self.requested_tubes
        if not pool_cand.has_tube_candidate(md_id):
            pool_cand.set_tube_candidate(md_id, tube_candidate)
        elif is_requested:
            pool_cand.replace_candidate(md_id, tube_candidate)
        if pool_cand.is_completed() \
           and not pool_cand.pool_id in self.__picked_pool_ids:
            self.__picked_pool_ids.add(pool_cand.pool_id)
            self._picked_candidates.append(pool_cand)

    def _sort_candidates(self):
        """
        In this case the picked candidate are :class:`PoolCandidate` object.
        We do not need to sort them anymore because they have already been
        sorted by the order of completion.
        """
        pass


class PoolCandidate(object):
    """
    A helper class storing the single design candidates for one particular pool
    (storage class, all values can only be set once).
    """
    def __init__(self, pool):
        """
        Constructor.

        :param pool: The molecule design pools this candidate aims to create.
        :type pool:
            :class:`thelma.entities.moleculedesign.MoleculeDesignPool`
        """
        #: The molecule design pools this candidate aims to create.
        self.__pool = pool
        #: Maps single molecule design pools (stock sample pools) onto
        #: molecule design IDs (design of the :attr:`pool`).
        self.__single_pools = dict()
        #: Maps tube candidates onto molecule design IDs.
        self.__candidates = OrderedDict()
        for md in self.__pool:
            md_id = md.id
            self.__single_pools[md_id] = None
            self.__candidates[md_id] = None

    @property
    def pool(self):
        """
        The molecule design pools this candidate aims to create.
        """
        return self.__pool

    @property
    def pool_id(self):
        return self.__pool.id

    def get_molecule_design_ids(self):
        """
        Returns the IDs of the molecule designs that are part of the pool
        to be created.
        """
        return self.__single_pools.keys()

    def has_tube_candidate(self, md_id):
        """
        Checks whether there is already a candidate for this molecule design
        ID.

        :raises KeyError: If the molecule design is not part of the
            pool to create.
        :raises AttributeError: If the candidate has already been set.
        """
        if not self.__candidates.has_key(md_id):
            msg = 'Molecule design %i is not part of pool %i!' \
                   % (md_id, self.__pool.id)
            raise KeyError(msg)
        return (self.__candidates[md_id] is not None)

    def set_tube_candidate(self, md_id, candidate):
        """
        Sets the tube stock sample candidate for a molecule design of the
        :attr:`pool`.

        :param int md_id: The ID of a molecule design in the pool to create.
        :param candidate: The candidate for this molecule design.
        :type candidate: :class:`IsoCandidate`
        :Note: Use :func:`has_tube_candidate` to check whether there is already
            a candidate.
        :raises AttributeError: If the candidate has already been set.
        """
        if self.__candidates[md_id] is not None:
            msg = 'The candidate for molecule design %i has already been set ' \
                  '(library pool %i).' % (md_id, self.__pool.id)
            raise AttributeError(msg)
        if self.__candidates[md_id] is None:
            self.__candidates[md_id] = candidate

    def replace_candidate(self, md_id, candidate):
        """
        Replaces the ISO stock sample candidate for a molecule design of the
        :attr:`pool` with the given candidate (use for requested tubes).
        """
        self.__candidates[md_id] = candidate

    def is_completed(self):
        """
        Checks whether there are ISO candidates for all molecule designs in
        the pool to create.
        """
        result = True
        for candidate in self.__candidates.values():
            if candidate is None:
                result = False
                break
        return result

    def get_tube_barcodes(self):
        """
        Returns the tube barcodes for the single molecule design stock tubes
        (in the order of molecule design IDs).
        """
        barcodes = []
        for md_id in sorted(self.__candidates.keys()):
            candidate = self.__candidates[md_id]
            if candidate is None:
                continue
            barcodes.append(candidate.tube_barcode)
        return barcodes

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
                other.pool.id == self.__pool.id

    def __str__(self):
        return self.__pool.id

    def __repr__(self):
        str_format = '<%s library pool: %i, mds: %s>'
        params = (self.__class__.__name__, self.__pool.id,
                  '-'.join([str(md_id) for md_id in self.__candidates.keys()]))
        return str_format % params

    def __getattr__(self, attr):
        if attr in ('tube_barcode', 'rack_barcode', 'rack_position', 'volume'):
            # This emulates a "normal" tube candidates for pools that are
            # made up of only one single design.
            if len(self.__candidates) > 1:
                raise AttributeError(attr)
            return getattr(self.__candidates.values()[0], attr)
        else:
            raise AttributeError(attr)


class SingleDesignPoolQuery(CustomQuery):
    """
    This query is used to find single molecule design pools for all molecule
    designs of the library.

    The results are stored in a dictionary (single design IDs mapped onto
    pool IDs).
    """
    QUERY_TEMPLATE = '''
    SELECT mdp.molecule_design_set_id AS pool_id,
           mdsm.molecule_design_id AS molecule_design_id
    FROM molecule_design_pool mdp,
        molecule_design_set_member mdsm
    WHERE mdp.number_designs = 1
    AND mdp.molecule_design_set_id = mdsm.molecule_design_set_id
    AND mdsm.molecule_design_id IN %s'''

    __POOL_ID_COL_NAME = 'pool_id'
    __MOLECULE_DESIGN_COL_NAME = 'molecule_design_id'

    COLUMN_NAMES = [__POOL_ID_COL_NAME, __MOLECULE_DESIGN_COL_NAME]
    RESULT_COLLECTION_CLS = dict

    __POOL_ID_INDEX = COLUMN_NAMES.index(__POOL_ID_COL_NAME)
    __MOLECULE_DESIGN_INDEX = COLUMN_NAMES.index(__MOLECULE_DESIGN_COL_NAME)

    def __init__(self, molecule_design_ids):
        """
        Constructor:

        :param molecule_design_ids: The molecule design IDs for which you
            want to find the pool IDs.
        :type molecule_design_ids: :class:`list`
        """
        CustomQuery.__init__(self)
        #: The molecule design IDs for which you want to find the pool IDs.
        self.molecule_design_ids = molecule_design_ids

    def _get_params_for_sql_statement(self):
        return create_in_term_for_db_queries(self.molecule_design_ids)

    def _store_result(self, result_record):
        pool_id = result_record[self.__POOL_ID_INDEX]
        md_id = result_record[self.__MOLECULE_DESIGN_INDEX]
        self._results[pool_id] = md_id


class PoolGenerationOptimizationQuery(OptimizingQuery):
    pass

#    """
#    This :class:`TubePickingQuery` aims find tubes for the single molecule
#    design pools required to generate the pools. At this, it tries to
#    minimise the number of racks that have to be used in the stock.
#
#    Unlike as in the normal :class:`OptimizingQuery` we do not care for
#    sample volumes.
#
#    The results are converted into :class:`TubeCandidates` and stored in
#    a list.
#    """
#
#    QUERY_TEMPLATE = '''
#    SELECT DISTINCT stock_sample.molecule_design_set_id AS pool_id,
#           rack_tube_counts.rack_barcode AS rack_barcode,
#           containment.row AS row_index,
#           containment.col AS column_index,
#           container_barcode.barcode AS tube_barcode,
#           rack_tube_counts.desired_count AS total_candidates,
#           stock_sample.concentration AS concentration
#    FROM stock_sample, sample, container, container_barcode, containment,
#         (SELECT xr.rack_id, xr.barcode AS rack_barcode,
#                   COUNT(xc.container_id) AS desired_count
#          FROM rack xr, containment xrc, container xc, sample xs,
#               stock_sample xss
#          WHERE xr.rack_id = xrc.holder_id
#          AND xc.container_id = xrc.held_id
#          AND xc.container_id = xs.container_id
#          AND xs.sample_id = xss.sample_id
#          AND xs.sample_id IN %s
#          GROUP BY xr.rack_id, xr.barcode
#          HAVING COUNT(xc.container_id) > 0 ) AS rack_tube_counts
#    WHERE container.container_id = containment.held_id
#    AND containment.holder_id = rack_tube_counts.rack_id
#    AND container.container_id = sample.container_id
#    AND container_barcode.container_id = container.container_id
#    AND sample.sample_id = stock_sample.sample_id
#    AND sample.sample_id IN %s
#    ORDER BY rack_tube_counts.desired_count desc,
#        rack_tube_counts.rack_barcode;'''
#
#    COLUMN_NAMES = ['pool_id', 'rack_barcode', 'row_index', 'column_index',
#                    'tube_barcode', 'total_candidates', 'concentration']
