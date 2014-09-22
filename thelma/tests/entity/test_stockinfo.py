from everest.repositories.rdb.testing import check_attributes
from thelma.tests.entity.conftest import TestEntityBase


class TestStockInfoEntity(TestEntityBase):

    def test_init(self, stock_info_fac):
        si = stock_info_fac()
        check_attributes(si, stock_info_fac.init_kw)
