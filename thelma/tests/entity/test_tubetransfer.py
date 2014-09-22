from everest.repositories.rdb.testing import check_attributes
from everest.repositories.rdb.testing import persist
from thelma.tests.entity.conftest import TestEntityBase


class TestTubeTransferEntity(TestEntityBase):

    def test_init(self, tube_transfer_fac):
        tt = tube_transfer_fac()
        check_attributes(tt, tube_transfer_fac.init_kw)

    def test_persist(self, nested_session, tube_transfer_fac):
        tt = tube_transfer_fac()
        persist(nested_session, tt, tube_transfer_fac.init_kw, True)


class TestTubeTransferWorklistEntity(TestEntityBase):

    def test_init(self, tube_transfer_worklist_fac):
        ttwl = tube_transfer_worklist_fac()
        check_attributes(ttwl, tube_transfer_worklist_fac.init_kw)

    def test_persist(self, nested_session, tube_transfer_worklist_fac):
        ttwl = tube_transfer_worklist_fac()
        persist(nested_session, ttwl, tube_transfer_worklist_fac.init_kw,
                True)
