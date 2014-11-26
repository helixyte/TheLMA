"""
This handler converts the results of the library member parser into a
molecule design set (:class:`thelma.entities.molecule.MoleculeDesignSet`).
The handler tries to determine the stock sample molecule design ID
for every molecule design set. If there is no ID, a new ID is created.

AAB
"""
from everest.entities.utils import get_root_aggregate
from everest.querying.specifications import cntd
from thelma.automation.handlers.base import BaseParserHandler
from thelma.automation.parsers.poolcreationset import PoolCreationSetParser
from thelma.automation.tools.stock.base import get_default_stock_concentration
from thelma.automation.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.utils.base import get_trimmed_string
from thelma.interfaces import IMoleculeDesign
from thelma.interfaces import IMoleculeDesignPool
from thelma.entities.moleculedesign import MoleculeDesignPool
from thelma.entities.moleculedesign import MoleculeDesignPoolSet


__docformat__ = 'reStructuredText en'

__all__ = ['PoolCreationSetParserHandler',
           ]

class PoolCreationSetParserHandler(BaseParserHandler):
    """
    Converts the results of the :class:`PoolCreationSetParser` into a
    :class:`MoleculeDesignPoolSet`.

    **Return Value:** :class:`MoleculeDesignPoolSet`
    """
    NAME = 'Stock Sample Pool Order Parser Handler'
    _PARSER_CLS = PoolCreationSetParser

    def __init__(self, stream, parent=None):
        BaseParserHandler.__init__(self, stream=stream, parent=parent)
        #: The number of molecule designs per cell (list).
        self.__number_molecule_designs = None
        #: The expected molecule type for all molecule designs in the library.
        self.__molecule_type = None
        #: Maps molecule designs onto molecule design IDs.
        self.__md_map = None
        #: Maps pools onto pool IDs.
        self.__pool_map = None
        #: Stores set of single molecule design for which we still have to
        #: find the pool ID.
        self.__pools_to_find = None
        #: Contains the molecule design pool sets for the final
        #: ISO request pool set.
        self.__pools = None
        # Intermediate error storage.
        self.__invalid_number_designs = None
        self.__invalid_molecule_type = None

    def reset(self):
        BaseParserHandler.reset(self)
        self.__number_molecule_designs = None
        self.__molecule_type = None
        self.__md_map = dict()
        self.__pool_map = dict()
        self.__pools = set()
        self.__pools_to_find = []
        self.__invalid_number_designs = []
        self.__invalid_molecule_type = []

    def get_number_designs(self):
        """
        Returns the number of designs per pool or *None* if there is an error.
        """
        return self._get_additional_value(self.__number_molecule_designs)

    def get_molecule_type(self):
        """
        Returns the molecule type or *None* if there is an error.
        """
        return self._get_additional_value(self.__molecule_type)

    def _convert_results_to_entity(self):
        self.add_info('Convert parser results ...')
        if not self.has_errors():
            self.__get_molecule_designs_and_pools()
        if not self.has_errors():
            self.__check_consistency()
        if not self.has_errors():
            self.__get_missing_molecule_design_pools()
        if not self.has_errors():
            self.return_value = \
                MoleculeDesignPoolSet(self.__molecule_type,
                                      molecule_design_pools=self.__pools)
            self.add_info('Conversion completed.')

    def __get_molecule_designs_and_pools(self):
        # Fetches the molecule designs for all molecule design IDs and pools for
        # all found pools.
        self.add_debug('Fetch molecule designs and pools for IDs ...')
        found_md_ids = set()
        found_pool_ids = set()
        i = 0
        while True:
            i += 1
            md_ids, pool_id = self.__get_ids_for_row(i)
            if md_ids is None and pool_id is None: break
            if pool_id is not None: found_pool_ids.add(pool_id)
            if md_ids is None: continue
            for md_id in md_ids: found_md_ids.add(md_id)
        if len(found_md_ids) > 0:
            md_filter = cntd(molecule_design_id=found_md_ids)
            self.__fetch_entities(IMoleculeDesign, md_filter, found_md_ids,
                                  'molecule design', self.__md_map)
        if len(found_pool_ids) > 0:
            pool_filter = cntd(molecule_design_set_id=found_pool_ids)
            self.__fetch_entities(IMoleculeDesignPool, pool_filter,
                                  found_pool_ids, 'pool', self.__pool_map)

    def __fetch_entities(self, interface, agg_filter, ids, entity_name, lookup):
        # Convenience method fetch the entities for the given IDs from the DB.
        # Also records errors if an ID is unknown
        agg = get_root_aggregate(interface)
        agg.filter = agg_filter
        for ent in agg:
            lookup[ent.id] = ent
        missing_ids = []
        for exp_id in ids:
            if not lookup.has_key(exp_id):
                missing_ids.append(exp_id)
        if len(missing_ids) > 0:
            msg = 'Unable to find %ss for the following IDs in the DB: %s.' \
                  % (entity_name,
                     ', '.join([get_trimmed_string(eid) for eid \
                                in sorted(missing_ids)]))
            self.add_error(msg)

    def __get_ids_for_row(self, row_index):
        # Convenience method fetching the IDs (if there are any) stated in the
        # given row.
        md_ids = None
        if self.parser.molecule_design_lists.has_key(row_index):
            md_ids = self.parser.molecule_design_lists[row_index]
        pool_id = None
        if self.parser.pool_ids.has_key(row_index):
            pool_id = self.parser.pool_ids[row_index]
        return md_ids, pool_id

    def __check_consistency(self):
        # Makes sure the number of designs and molecule types are common for
        # all designs and pools and that pools and design match each other.
        mismatch = []
        i = 0
        while True:
            i += 1
            md_ids, pool_id = self.__get_ids_for_row(i)
            if md_ids is None and pool_id is None:
                break
            if self.__pool_map.has_key(pool_id):
                pool = self.__pool_map[pool_id]
                self.__check_number_designs(pool.number_designs, i)
                self.__check_molecule_type(pool.molecule_type, i)
                exp_ids = [md.id for md in pool]
                if not md_ids is None and sorted(exp_ids) != sorted(md_ids):
                    info = '%i (expected: %s, found in file: %s)' \
                            % (pool_id,
                               '-'.join([str(ei) for ei in sorted(exp_ids)]),
                               '-'.join([str(ei) for ei in sorted(md_ids)]))
                    mismatch.append(info)
                else:
                    self.__pools.add(pool)
            else:
                self.__pools_to_find.append(md_ids)
            if not md_ids is None:
                self.__check_number_designs(len(md_ids), i)
                for md_id in md_ids:
                    md = self.__md_map[md_id]
                    self.__check_molecule_type(md.molecule_type, i)
        if len(mismatch) > 0:
            msg = 'In some rows the pools and the molecule designs you have ' \
                  'ordered to not match: %s.' % (', '.join(mismatch)) # no sort
            self.add_error(msg)
        if len(self.__invalid_number_designs) > 0:
            msg = 'The number of molecule designs must be the same for all ' \
                  'pools. The number of designs for the first pool is %i. ' \
                  'The pools in the following rows have different numbers: ' \
                  '%s.' % (self.__number_molecule_designs,
                   ', '.join([str(rn) for rn in self.__invalid_number_designs]))
            self.add_error(msg)
        if len(self.__invalid_molecule_type) > 0:
            msg = 'The molecule type must be the same for all pools. The ' \
                  'molecule type for the first pools is %s. The pools in the ' \
                  'following rows have different molecule types: %s.' \
                  % (self.__molecule_type,
                    ', '.join([str(rn) for rn in self.__invalid_molecule_type]))
            self.add_error(msg)

    def __check_number_designs(self, number_designs, row_index):
        # The number of designs must be the same for all pools.
        if self.__number_molecule_designs is None:
            self.__number_molecule_designs = number_designs
        elif not self.__number_molecule_designs == number_designs:
            self.__invalid_number_designs.append((row_index + 1))

    def __check_molecule_type(self, molecule_type, row_index):
        # The molecule type must be the same for all pools.
        if self.__molecule_type is None:
            self.__molecule_type = molecule_type
        elif not self.__molecule_type == molecule_type:
            self.__invalid_molecule_type.append((row_index + 1))

    def __get_missing_molecule_design_pools(self):
        # Fetches or creates the molecule design pools for the rows in which
        # there are only molecule designs given
        # (invokes :func:`MoleculeDesignPool.create_from_data`).
        self.add_debug('Find pool IDs for molecule design sets ...')
        stock_conc = (get_default_stock_concentration(
                             molecule_type=self.__molecule_type,
                             number_designs=self.__number_molecule_designs)) \
                             / CONCENTRATION_CONVERSION_FACTOR
        for md_ids in self.__pools_to_find:
            mds = set([self.__md_map[md_id] for md_id in md_ids])
            mdp_data = dict(molecule_designs=mds,
                            default_stock_concentration=stock_conc)
            pool = MoleculeDesignPool.create_from_data(mdp_data)
            self.__pools.add(pool)
