"""
This handler converts the results of the library member parser into a
molecule design set (:class:`thelma.entities.molecule.MoleculeDesignSet`).
At this, the handler tries to determine the stock sample molecule design ID
for every molecule design set. If there is no ID, a new ID is created.

AAB
"""
from everest.entities.utils import get_root_aggregate
from everest.querying.specifications import cntd
from thelma.tools.handlers.base import BaseParserHandler
from thelma.tools.parsers.libmembers import LibraryMemberParser
from thelma.interfaces import IMoleculeDesignPool
from thelma.entities.moleculedesign import MoleculeDesignPoolSet
from thelma.entities.moleculetype import MoleculeType


__docformat__ = 'reStructuredText en'

__all__ = ['LibraryMemberParserHandler',
           ]


class LibraryMemberParserHandler(BaseParserHandler):
    """
    Converts the results of the :class:`LibraryMemberParser` into a
    :class:`MoleculeDesignSet`.

    **Return Value:** :class:`PoolSet`
    """
    NAME = 'Library Member Parser Handler'

    _PARSER_CLS = LibraryMemberParser

    def __init__(self, stream, number_molecule_designs, molecule_type,
                 parent=None):
        """
        Constructor.

        :param int number_molecule_designs: The number of molecule designs
            per cell (list).
        :param molecule_type: The expected molecule type for all molecule
            designs in the library.
        :type molecule_type: :class:`thelma.entities.moleculetype.MoleculeType`
        """
        BaseParserHandler.__init__(self, stream=stream, parent=parent)
        self.number_molecule_designs = number_molecule_designs
        self.molecule_type = molecule_type
        #: Map molecule design ID -> molecule design.
        self.__md_map = None
        #: Contains the stock sample molecule design sets for the final
        #: library pool set.
        self.__library_sets = None

    def reset(self):
        BaseParserHandler.reset(self)
        self.__md_map = dict()
        self.__library_sets = set()

    def _convert_results_to_entity(self):
        self.add_info('Convert parser results ...')
        self.__check_input()
        if not self.has_errors():
            self.__get_molecule_design_pools()
        if not self.has_errors():
            self.return_value = MoleculeDesignPoolSet(
                                    molecule_type=self.molecule_type,
                                    molecule_design_pools=self.__library_sets)
            self.add_info('Conversion completed.')

    def __check_input(self):
        self._check_input_class('number molecule designs',
                                self.number_molecule_designs, int)
        self._check_input_class('molecule type', self.molecule_type,
                                MoleculeType)

    def __get_molecule_design_pools(self):
        self.add_debug('Fetch molecule design pools for IDs ...')
        invalid_length = []
        found_md_ids = set()
        for md_ids in self.parser.molecule_design_lists:
            if len(md_ids) != self.number_molecule_designs:
                invalid_length.append(
                                    '-'.join([str(md_id) for md_id in md_ids]))
                continue
            for md_id in md_ids:
                found_md_ids.add(md_id)
        if len(invalid_length) > 0:
            msg = 'Some of the specified molecule design pools do not ' \
                  'have the expected number of molecule designs (%i): %s.' \
                   % (self.number_molecule_designs, ', '.join(invalid_length))
            self.add_error(msg)
            return
        invalid_type = []
        agg = get_root_aggregate(IMoleculeDesignPool)
        agg.filter = cntd(molecule_design_id=found_md_ids)
        iterator = agg.iterator()
        while True:
            try:
                md = iterator.next()
            except StopIteration:
                break
            else:
                if md.molecule_type != self.molecule_type:
                    invalid_type.append(md.id)
                self.__md_map[md.id] = md
        # Search for missing molecule designs.
        if len(found_md_ids) != len(self.__md_map):
            diff = found_md_ids.symmetric_difference(self.__md_map.keys())
            diff = sorted(list(diff))
            msg = 'The following molecule designs could not be found in ' \
                  'the DB: %s.' % (', '.join([str(md_id) for md_id in diff]))
            self.add_error(msg)
        if len(invalid_type) > 0:
            msg = 'The molecule designs in the list have different molecule ' \
                  'types. Expected: %s. Others (molecule designs): %s.' \
                  % (self.molecule_type,
                     ', '.join([str(md_id) for md_id in sorted(invalid_type)]))
            self.add_error(msg)
