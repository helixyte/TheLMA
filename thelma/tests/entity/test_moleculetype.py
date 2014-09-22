from everest.entities.utils import slug_from_string
from everest.repositories.rdb.testing import check_attributes
from everest.repositories.rdb.testing import persist
from thelma.tests.entity.conftest import TestEntityBase


class TestMoleculeTypeEntity(TestEntityBase):

    def test_init(self, molecule_type_fac):
        mt = molecule_type_fac()
        check_attributes(mt, molecule_type_fac.init_kw)
        assert mt.slug == slug_from_string(mt.name)

    def test_persist(self, nested_session, molecule_type_fac):
        mt = molecule_type_fac()
        persist(nested_session, mt, molecule_type_fac.init_kw, True)
