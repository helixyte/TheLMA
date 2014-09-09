from everest.repositories.rdb.testing import check_attributes
from everest.repositories.rdb.testing import persist
from thelma.tests.entity.conftest import TestEntityBase


class TestSubprojectEntity(TestEntityBase):

    def test_init(self, subproject_fac):
        sp = subproject_fac()
        check_attributes(sp, subproject_fac.init_kw)

    def test_persist(self, nested_session, subproject_fac):
        sp = subproject_fac()
        persist(nested_session, sp, subproject_fac.init_kw, True)
