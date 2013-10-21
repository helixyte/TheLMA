"""
:Date: 1st Aug 2011
:Author: AAB, berger at cenix-bioscience dot com

.. currentmodule:: thelma.automation.tools.metadata.generation

This is the handler for molecule design lists in Excel sheets. It is a
component of the :class:`ExperimentMetadataGenerator`.

"""

from everest.entities.utils import get_root_aggregate
from everest.querying.specifications import cntd
from thelma.automation.handlers.base import BaseParserHandler
from thelma.automation.parsers.experimentpoolset import ExperimentPoolSetParser
from thelma.automation.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.interfaces import IMoleculeDesignPool
from thelma.models.moleculedesign import MoleculeDesignPoolSet

__docformat__ = 'reStructuredText en'

__all__ = ['ExperimentPoolSetParserHandler',
           ]

class ExperimentPoolSetParserHandler(BaseParserHandler):
    """
    This is the handler for molecule design lists in Excel sheets.
    """
    NAME = 'Experiment Pool Set Parser Handler'

    MODEL_CLASS = MoleculeDesignPoolSet
    _PARSER_CLS = ExperimentPoolSetParser

    def __init__(self, stream, log):
        """
        Constructor:

        :param stream: stream of the file to be parsed
        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        """

        BaseParserHandler.__init__(self, log, stream=stream)

        #: The molecule type of the molecule design pools.
        self.__molecule_type = None
        #: The stock concentration for the pools (must all be the same).
        self.__stock_concentration = None

    def get_stock_concentration(self):
        """
        Returns the stock concentration for the pools of the set (in nM).
        """
        if self.return_value is None: return None
        return self.__stock_concentration

    def _convert_results_to_model_entity(self):
        """
        Creates the MoleculeDesignSet object used as output value.
        """
        self.add_info('Converting IDs into objects ...')

        molecule_design_pools = self.__get_molecule_design_pools()

        if not self.has_errors():
            pool_set = MoleculeDesignPoolSet(
                            molecule_type=self.__molecule_type,
                            molecule_design_pools=set(molecule_design_pools))
            self.return_value = pool_set
            self.add_info('Molecule design pool set creation complete.')

    def __get_molecule_design_pools(self):
        """
        Returns the molecule design pool objects for the specified IDs.
        """
        self.add_debug('Checks validity of the molecule design pool IDs ...')

        ids = self.parser.molecule_design_pool_ids
        agg = get_root_aggregate(IMoleculeDesignPool)
        agg.filter = cntd(molecule_design_set_id=ids)

        db_ids = set()
        molecule_design_pools = set()
        stock_concentrations = set()

        iterator = agg.iterator()
        while True:
            try:
                md_pool = iterator.next()
            except StopIteration:
                break
            else:
                if self.__molecule_type is None:
                    self.__molecule_type = md_pool.molecule_type
                else:
                    if not self.__molecule_type == md_pool.molecule_type:
                        msg = 'There is more than one molecule type in the ' \
                              'the molecule design set ("%s" and "%s")!' \
                              % (self.__molecule_type.name,
                                 md_pool.molecule_type.name)
                        self.add_error(msg)
                        return None

                molecule_design_pools.add(md_pool)
                db_ids.add(md_pool.id)
                stock_conc = md_pool.default_stock_concentration \
                             * CONCENTRATION_CONVERSION_FACTOR
                stock_concentrations.add(stock_conc)

        if not len(molecule_design_pools) == len(ids):
            unknown_molecule_design_pools = []
            for pool_id in ids:
                if not pool_id in db_ids:
                    unknown_molecule_design_pools.append(pool_id)
            msg = 'The following molecule design pool IDs have not be found ' \
                  'in the DB: %s' % (unknown_molecule_design_pools)
            self.add_error(msg)

        if len(stock_concentrations) > 1:
            conc = sorted(list(stock_concentrations))
            msg = 'The pools in the set have different stock concentrations: ' \
                  '(shown in nM): %s.' % (', '.join([str(c) for c in conc]))
            self.add_error(msg)
        else:
            self.__stock_concentration = list(stock_concentrations)[0]

        return molecule_design_pools
