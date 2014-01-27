'''
Created on Jun 20, 2011

@author: berger
'''

from everest.repositories.rdb.testing import RdbContextManager
from everest.repositories.rdb.testing import check_attributes
from thelma.models.moleculetype import MOLECULE_TYPE_IDS
from thelma.models.moleculetype import MoleculeType
from thelma.models.stockinfo import StockInfo
from thelma.testing import ThelmaModelTestCase


class StockInfoModelTest(ThelmaModelTestCase):

    model_class = StockInfo

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.molecule_design_pool = self._create_molecule_design_pool()
        self.concentration = 10
        self.total_tubes = 4
        self.min_vol = 5
        self.max_vol = 20
        self.total_volume = 135
        self.molecule_type = self._create_molecule_type(
                                                name=MOLECULE_TYPE_IDS.SIRNA)
        self.init_data = dict(molecule_design_pool=self.molecule_design_pool,
                              molecule_type=self.molecule_type,
                              concentration=self.concentration,
                              total_tubes=self.total_tubes,
                              total_volume=self.total_volume,
                              minimum_volume=self.min_vol,
                              maximum_volume=self.max_vol)

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.molecule_design_pool
        del self.concentration
        del self.total_tubes
        del self.min_vol
        del self.max_vol
        del self.total_volume
        del self.molecule_type
        del self.init_data

    def test_load_100_sirnas(self):
        with RdbContextManager() as session:
            mt = session.query(MoleculeType).filter_by(id='SIRNA').one()
            clause = StockInfo.molecule_type == mt
            infos = session.query(StockInfo).filter(clause).limit(100).all()
            self.assert_equal(len(infos), 100)

    def test_stockinfo_init(self):
        si = StockInfo(self.molecule_design_pool, self.molecule_type,
                       self.concentration, self.total_tubes,
                       self.total_volume, self.min_vol, self.max_vol)
        self.assert_false(si is False)
        check_attributes(si, self.init_data)
