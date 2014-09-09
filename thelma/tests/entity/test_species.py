from everest.repositories.rdb.testing import check_attributes
from thelma.tests.entity.conftest import TestEntityBase
from everest.entities.utils import slug_from_string
from everest.repositories.rdb.testing import persist


class TestSpeciesEntity(TestEntityBase):

    def test_init(self, species_fac):
        spec = species_fac()
        check_attributes(spec, species_fac.init_kw)
        assert spec.slug == slug_from_string(spec.common_name)

    def test_persist(self, nested_session, species_fac):
        spec = species_fac()
        persist(nested_session, spec, species_fac.init_kw, True)
