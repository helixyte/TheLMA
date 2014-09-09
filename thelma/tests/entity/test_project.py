from everest.entities.utils import slug_from_string
from everest.repositories.rdb.testing import check_attributes
from everest.repositories.rdb.testing import persist
from thelma.tests.entity.conftest import TestEntityBase


class TestProjectEntity(TestEntityBase):
    def test_init(self, project_fac):
        proj = project_fac()
        check_attributes(proj, project_fac.init_kw)
        assert proj.slug == slug_from_string(proj.label)

    def test_persist(self, nested_session, project_fac):
        proj = project_fac()
        persist(nested_session, proj, project_fac.init_kw, True)
