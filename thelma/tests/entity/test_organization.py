from everest.entities.utils import slug_from_string
from everest.repositories.rdb.testing import check_attributes
from everest.repositories.rdb.testing import persist
from thelma.tests.entity.conftest import TestEntityBase


class TestOrganizationEntity(TestEntityBase):

    def test_init(self, organization_fac):
        org = organization_fac()
        check_attributes(org, organization_fac.init_kw)
        assert org.slug == slug_from_string(org.name)

    def test_persist(self, nested_session, organization_fac):
        org = organization_fac()
        persist(nested_session, org, organization_fac.init_kw, True)
