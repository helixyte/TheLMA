"""
Tests for classes and constants involved in pool stock samples creation tasks.

AAB
"""
from thelma.automation.tools.poolcreation.base \
    import calculate_single_design_stock_transfer_volume
from thelma.automation.tools.poolcreation.base \
    import calculate_single_design_stock_transfer_volume_for_library
from thelma.automation.tools.worklists.base \
    import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.worklists.base import VOLUME_CONVERSION_FACTOR
from thelma.interfaces import IMoleculeDesignPool
from thelma.models.library import MoleculeDesignLibrary
from thelma.models.moleculedesign import MoleculeDesignPoolSet
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase

class PoolCreationBaseFunctionTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.target_volume = 30
        self.target_concentration = 10000
        self.stock_conc = 50000
        self.number_designs = 3

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.target_volume
        del self.target_concentration
        del self.stock_conc
        del self.number_designs

    def test_calculate_single_design_stock_transfer_volume(self):
        kw = dict(target_volume=self.target_volume,
                  target_concentration=self.target_concentration,
                  number_designs=self.number_designs,
                  stock_concentration=self.stock_conc)
        meth = calculate_single_design_stock_transfer_volume
        self.assert_equal(meth(**kw), 2)
        kw['target_volume'] = self.target_volume * 2
        self.assert_equal(meth(**kw), 4)
        kw['target_volume'] = 10
        self.assert_raises(ValueError, meth, **kw)
        kw['target_volume'] = self.target_volume
        kw['target_concentration'] = self.stock_conc * 5
        self.assert_raises(ValueError, meth, **kw)

    def test_calculate_single_design_stock_transfer_volume_for_library(self):
        pool = self._get_entity(IMoleculeDesignPool)
        pool_set = MoleculeDesignPoolSet(molecule_type=pool.molecule_type,
                                         molecule_design_pools=set([pool]))
        lib = MoleculeDesignLibrary(molecule_design_pool_set=pool_set,
            label='testlib',
            final_volume=self.target_volume / VOLUME_CONVERSION_FACTOR,
            final_concentration=self.target_concentration \
                / CONCENTRATION_CONVERSION_FACTOR)
        kw = dict(pool_creation_library=lib)
        meth = calculate_single_design_stock_transfer_volume_for_library
        self.assert_equal(meth(**kw), 2)
        kw['single_design_stock_concentration'] = self.stock_conc
        self.assert_equal(meth(**kw), 2)
        kw['single_design_stock_concentration'] = self.stock_conc / 2
        self.assert_equal(meth(**kw), 4)

