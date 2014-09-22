from everest.entities.utils import slug_from_string
from everest.repositories.rdb.testing import check_attributes
from everest.repositories.rdb.testing import persist
from thelma.tests.entity.conftest import TestEntityBase


class TestBarcodedLocationEntity(TestEntityBase):

    def test_init(self, barcoded_location_fac):
        bl = barcoded_location_fac()
        check_attributes(bl, barcoded_location_fac.init_kw)
        assert bl.rack is None
        assert bl.slug == slug_from_string(bl.name)

    def test_persist(self, nested_session, barcoded_location_fac):
        bl = barcoded_location_fac()
        kw = barcoded_location_fac.init_kw
        # FIXME: This should not be necessary.
        bl.type = kw['type'] = bl.type.name
        persist(nested_session, bl, kw, True)


class TestBarcodedLocationTypeEntity(TestEntityBase):

    def test_init(self, barcoded_location_type_fac):
        bl = barcoded_location_type_fac()
        check_attributes(bl, barcoded_location_type_fac.init_kw)
        assert bl.slug == slug_from_string(bl.name)
