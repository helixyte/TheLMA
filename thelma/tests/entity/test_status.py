from everest.repositories.rdb.testing import check_attributes
from everest.repositories.rdb.testing import persist
from thelma.tests.entity.conftest import TestEntityBase
from everest.entities.utils import slug_from_string


class TestItemStatusEntity(TestEntityBase):
    def test_init(self, item_status_fac):
        its = item_status_fac()
        check_attributes(its, item_status_fac.init_kw)
        assert its.slug == slug_from_string(its.name)

    def test_persist(self, nested_session, item_status_fac):
        its = item_status_fac()
        persist(nested_session, its, item_status_fac.init_kw, True)
