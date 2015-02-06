"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Contains tools involved in tube picking optimization for library creations.

AAB
"""
from sqlalchemy.orm.collections import InstrumentedSet

from everest.repositories.rdb import Session
from thelma.tools.base import BaseTool
from thelma.tools.stock.base import STOCK_DEAD_VOLUME
from thelma.tools.stock.base import STOCK_ITEM_STATUS
from thelma.tools.utils.base import add_list_map_element
from thelma.tools.utils.base import create_in_term_for_db_queries
from thelma.tools.utils.base import is_valid_number
from thelma.entities.moleculedesign import MoleculeDesignPool
from thelma.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.tools.utils.base import VOLUME_CONVERSION_FACTOR


__docformat__ = 'reStructuredText en'

__all__ = ['LibraryCreationTubePicker',
           'LibraryCandidate',
           'SINGLE_POOL_QUERY',
           'LIBRARY_OPTIMIZATION_QUERY']


class LibraryCreationTubePicker(BaseTool):
    """
    Runs the optimization query for the given set of molecule designs.
    The tool also picks tubes.

    **Return Value:** the :class:`LibraryCandidate` objects in the order
        of completion
    """
    NAME = 'Library Creation Optimizer'

    def __init__(self, molecule_design_pools, stock_concentration,
                 take_out_volume,
                 excluded_racks=None, requested_tubes=None, parent=None):
        """
        Constructor.

        :param molecule_design_pools: The molecule design pool IDs for which
            to run the query.
        :type molecule_design_pools: :class:`set` of molecule design pool IDs
        :param int stock_concentration: The stock concentration of the single
            molecule design pools for the library in nM (positive number).
        :param int take_out_volume: The volume that shall be removed from the
            single molecule design stock in ul (positive number).
        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of tube barcodes.
        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for molecule design picking.
        :type excluded_racks: A list of rack barcodes
        """
        BaseTool.__init__(self, parent=parent)
        #: The molecule design pool IDs for which to run the query.
        self.molecule_design_pools = molecule_design_pools
        #: The stock concentration of the single molecule design pools for
        #: the library in nM.
        self.stock_concentration = stock_concentration
        #: The volume that shall be removed from the single molecule design
        #: stock in ul.
        self.take_out_volume = take_out_volume
        if excluded_racks is None: excluded_racks = []
        #: A list of barcodes from stock racks that shall not be used for
        #: molecule design picking.
        self.excluded_racks = excluded_racks
        if requested_tubes is None: requested_tubes = []
        #: A list of barcodes from stock tubes that are supposed to be used
        #: (for fixed positions).
        self.requested_tubes = requested_tubes
        #: The DB session used for the queries.
        self.__session = None
        #: The library candidated mapped onto pool IDs.
        self.__library_candidates = None
        #: Maps library pool IDs onto molecule design IDs. ATTENTION: a molecule
        #: design pool can point to several library pools! For this reason,
        #: library pool IDs are stored in lists.
        self.__md_map = None
        #: Maps molecule design IDs onto single molecule design pool IDs.
        self.__single_pool_map = None
        #: Stores the suitable stock sample IDs for the single molecule
        #: designs pools used to create the library pools. The results are
        #: determined by the :class:`SINGLE_POOL_QUERY`.
        self.__stock_samples = None

        #: The picked library candidates for the pools in the order of
        #: completion.
        self.__picked_candidates = None

        #: If an siRNA is used in several pools this map will store the data
        #: of which ISO candidate has been used for which one.
        self.__multi_pool_iso_candidates = None

    def reset(self):
        BaseTool.reset(self)
        self.__library_candidates = {}
        self.__md_map = dict()
        self.__picked_candidates = []
        self.__stock_samples = []
        self.__single_pool_map = dict()
        self.__multi_pool_iso_candidates = dict()

    def run(self):
        """
        Runs the optimizer and picks tubes.
        """
        self.reset()
        self.add_info('Start library tube picking optimization ...')

        self.__check_input()
        if not self.has_errors():
            self.__initialize_session()
            self.__create_library_candidates()
            self.__get_single_pools()
        if not self.has_errors():
            self.__get_stock_samples()
        if not self.has_errors():
            self.__run_optimizer()
        if not self.has_errors():
            self.return_value = self.__picked_candidates
            self.add_info('Candidate picking completed.')

    def __initialize_session(self):
        """
        Initializes a session for ORM operations.
        """
        self.__session = Session()

    def __check_input(self):
        """
        Checks the input values.
        """
        self.add_debug('Check input values ...')

        if isinstance(self.molecule_design_pools, (InstrumentedSet, list)):
            for pool in self.molecule_design_pools:
                self._check_input_class('library pool', pool,
                                        MoleculeDesignPool)
            if len(self.molecule_design_pools) < 1:
                msg = 'The pool list is empty!'
                self.add_error(msg)
        else:
            msg = 'The library pool list must be a list or an ' \
                  'InstrumentedSet (obtained: %s).' % \
                  (self.molecule_design_pools.__class__.__name__)
            self.add_error(msg)

        if not is_valid_number(self.stock_concentration):
            msg = 'The stock concentration must be a positive number ' \
                  '(obtained: %s).' % (self.stock_concentration)
            self.add_error(msg)
        if not is_valid_number(self.take_out_volume):
            msg = 'The stock take out volume must be a positive number ' \
                  '(obtained: %s).' % (self.take_out_volume)
            self.add_error(msg)

        if self._check_input_class('excluded racks list',
                                       self.excluded_racks, list):
            for excl_rack in self.excluded_racks:
                if not self._check_input_class('excluded rack barcode',
                                               excl_rack, basestring): break
        if self._check_input_class('requested tubes list',
                                       self.requested_tubes, list):
            for req_tube in self.requested_tubes:
                if not self._check_input_class('requested tube barcode',
                                               req_tube, basestring): break

    def __create_library_candidates(self):
        """
        Initialises empty library candidates (without stock sample data and
        candidates) for every library pool.
        """
        self.add_debug('Initialise library candidates ...')

        for pool in self.molecule_design_pools:
            libcand = LibraryCandidate(pool)
            self.__library_candidates[pool.id] = libcand
            for md_id in libcand.get_molecule_design_ids():
                add_list_map_element(self.__md_map, md_id, pool.id)

    def __get_single_pools(self):
        """
        Determines the single pool (ID) or each requested molecule design.
        """
        self.add_debug('Get single molecule design pool ...')

        md_str = create_in_term_for_db_queries(self.__md_map.keys())
        query_statement = SINGLE_POOL_QUERY.QUERY_TEMPLATE % (md_str)

        results = self.__session.query(*SINGLE_POOL_QUERY.QUERY_RESULTS).\
                                       from_statement(query_statement).all()

        for record in results:
            md_id = record[SINGLE_POOL_QUERY.MOLECULE_DESIGN_INDEX]
            pool_id = record[SINGLE_POOL_QUERY.POOL_INDEX]
            self.__single_pool_map[pool_id] = md_id

        if not len(self.__single_pool_map) == len(self.__md_map):
            missing_ids = []
            for md_id in self.__md_map.keys():
                if not self.__single_pool_map.has_key(md_id):
                    missing_ids.append(md_id)
            msg = 'Could not find single molecule design pool for the ' \
                  'following molecule designs: %s.' % (', '.join(
                            [str(md_id) for md_id in sorted(missing_ids)]))
            self.add_error(msg)

    def __get_stock_samples(self):
        """
        Determines suitable stock samples for the molecule designs required
        to create the pools. Suitable tubes must be managed, have a stock
        concentration and a certain minimum volume.
        """
        self.add_debug('Get stock samples ...')

        conc = self.stock_concentration / CONCENTRATION_CONVERSION_FACTOR
        volume = (self.take_out_volume + STOCK_DEAD_VOLUME) \
                 / VOLUME_CONVERSION_FACTOR
        pool_str = create_in_term_for_db_queries(self.__single_pool_map.keys())

        query_statement = STOCK_SAMPLE_QUERY.QUERY_TEMPLATE % (
                                    pool_str, conc, volume, STOCK_ITEM_STATUS)
        results = self.__session.query(*STOCK_SAMPLE_QUERY.QUERY_RESULTS).\
                  from_statement(query_statement).all()

        found_pools = set()
        for record in results:
            stock_sample_id = record[STOCK_SAMPLE_QUERY.STOCK_SAMPLE_INDEX]
            self.__stock_samples.append(stock_sample_id)
            pool_id = record[STOCK_SAMPLE_QUERY.POOL_INDEX]
            found_pools.add(pool_id)

        if len(found_pools) < 1:
            msg = 'Did not find any suitable stock sample!'
            self.add_error(msg)
        elif not len(found_pools) == len(self.__single_pool_map):
            missing_pools = []
            for pool_id, md_id in self.__single_pool_map.iteritems():
                if not pool_id in found_pools:
                    missing_pools.append('%s (md: %s)' % (pool_id, md_id))
            msg = 'Could not find suitable source stock tubes for the ' \
                  'following molecule design pools: %s.' \
                  % (', '.join(sorted(missing_pools)))
            self.add_warning(msg)

    def __run_optimizer(self):
        """
        Runs the optimizing query and allocates the results to the library
        candidates.
        """
        self.add_debug('Run optimizer ...')

        sample_str = create_in_term_for_db_queries(self.__stock_samples)
        query_statement = LIBRARY_OPTIMIZATION_QUERY.QUERY_TEMPLATE % (
                                                        sample_str, sample_str)

        results = self.__session.query(
                            *LIBRARY_OPTIMIZATION_QUERY.QUERY_RESULT_VALUES).\
                            from_statement(query_statement).all()

        for record in results:
            iso_candidate = IsoCandidate.create_from_query_result(record)
            if iso_candidate.rack_barcode in self.excluded_racks: continue
            self.__store_candidate_data(iso_candidate)

        if len(self.__picked_candidates) < 1:
            msg = 'Did not find any library candidate!'
            self.add_error(msg)

    def __store_candidate_data(self, iso_candidate):
        """
        Adds an ISO candidate to an library candidate and moves the
        library candidate once it is completed.
        """
        single_pool_id = iso_candidate.pool_id
        md_id = self.__single_pool_map[single_pool_id]
        pool_ids = self.__md_map[md_id]
        if len(pool_ids) == 1:
            pool_id = pool_ids[0]
        else:
            for ambi_pool_id in pool_ids:
                pool_id = None
                if not self.__multi_pool_iso_candidates.has_key(ambi_pool_id):
                    self.__multi_pool_iso_candidates[ambi_pool_id] = \
                                        iso_candidate
                    pool_id = ambi_pool_id
                if pool_id is None:
                    pool_id = pool_ids[0]

        libcand = self.__library_candidates[pool_id]
        is_requested = iso_candidate.container_barcode in self.requested_tubes

        if not libcand.has_iso_candidate(md_id):
            libcand.set_iso_candidate(md_id, iso_candidate)
        elif is_requested:
            libcand.replace_candidate(md_id, iso_candidate)

        if libcand.is_completed() and not libcand in self.__picked_candidates:
            self.__picked_candidates.append(libcand)


class LibraryCandidate(object):
    """
    A helper class storing the ISO candidates for one particular pool
    (storage class, all values can only be set once).
    """

    def __init__(self, pool):
        """
        Constructor:

        :param pool: The molecule design pools this candidate aims to create.
        :type pool:
            :class:`thelma.entities.moleculedesign.MoleculeDesignPool`
        """
        #: The molecule design pools this candidate aims to create.
        self.__pool = pool
        #: Maps single molecule design pools (stock sample pools) onto
        #: molecule design IDs (design of the :attr:`pool`).
        self.__single_pools = dict()
        #: Maps ISO candidates onto molecule design IDs.
        self.__candidates = dict()

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

    def get_molecule_design_ids(self):
        """
        Returns the IDs of the molecule designs that are part of the pool
        to be created.
        """
        return self.__single_pools.keys()

    def has_iso_candidate(self, md_id):
        """
        Checks whether there is alreay a candidate for this molecule design
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

    def set_iso_candidate(self, md_id, candidate):
        """
        Sets the ISO stock sample candidate for a molecule design of the
        :attr:`pool`.

        :param md_id: The ID of a molecule design in the pool to create.
        :type md_id: :class:`int`

        :param candidate: The candidate for this molecule design.
        :type candidate: :class:`IsoCandidate`

        :Note: Use :func:`has_iso_candidate` to check whether there is already
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
        for candidate in self.__candidates.values():
            if candidate is None: return False

        return True

    def get_tube_barcodes(self):
        """
        Returns the tube barcodes for the single molecule design stock tubes
        (in the order of molecule design IDs).
        """
        barcodes = []
        for md_id in sorted(self.__candidates.keys()):
            candidate = self.__candidates[md_id]
            barcodes.append(candidate.container_barcode)

        return barcodes

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
                other.pool.id == self.__pool.id

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __str__(self):
        return self.__pool.id

    def __repr__(self):
        str_format = '<%s library pool: %i, mds: %s>'
        params = (self.__class__.__name__, self.__pool.id,
                  '-'.join([str(md_id) for md_id in self.__candidates.keys()]))
        return str_format % params


class SINGLE_POOL_QUERY(object):
    """
    This query is used to find single molecule design pools for all molecule
    designs of the library.
    """

    #: the query template
    QUERY_TEMPLATE = '''
    SELECT ssmds.molecule_design_set_id AS pool_id,
           mdsm.molecule_design_id AS molecule_design_id
    FROM molecule_design_pool ssmds,
        molecule_design_set_member mdsm
    WHERE ssmds.number_designs = 1
    AND ssmds.molecule_design_set_id = mdsm.molecule_design_set_id
    AND mdsm.molecule_design_id IN %s'''

    #: The key for the molecule design pool ID.
    POOL_KEY = 'pool_id'
    #: The key for the molecule design ID.
    MOLECULE_DESIGN_KEY = 'molecule_design_id'

    #: A tuple containing the query result specifications in the right order
    #: (required for the :class:`Query` object built by the ORM).
    QUERY_RESULTS = (POOL_KEY, MOLECULE_DESIGN_KEY)

    #: The index for the molecule design pool ID in the query result.
    POOL_INDEX = QUERY_RESULTS.index(POOL_KEY)
    #: The index for the molecule design ID in the query result.
    MOLECULE_DESIGN_INDEX = QUERY_RESULTS.index(MOLECULE_DESIGN_KEY)


class STOCK_SAMPLE_QUERY(object):
    """
    This query is used to find suitable stock samples for the molecule designs
    of library pools.
    """
    #: the query template
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

    #: The key for the molecule design pool ID.
    POOL_KEY = 'pool_id'
    #: The key for the stock sample ID.
    STOCK_SAMPLE_KEY = 'stock_sample_id'

    #: A tuple containing the query result specifications in the right order
    #: (required for the :class:`Query` object built by the ORM).
    QUERY_RESULTS = (POOL_KEY, STOCK_SAMPLE_KEY)

    #: The index for the molecule design pool ID in the query result.
    POOL_INDEX = QUERY_RESULTS.index(POOL_KEY)
    #: The index for the stock sample ID in the query result.
    STOCK_SAMPLE_INDEX = QUERY_RESULTS.index(STOCK_SAMPLE_KEY)


class LIBRARY_OPTIMIZATION_QUERY(OPTIMIZATION_QUERY):
    """
    This query is used to minimize the number of racks that is taken out
    of the stock.
    """

    #: the query template
    QUERY_TEMPLATE = '''
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
