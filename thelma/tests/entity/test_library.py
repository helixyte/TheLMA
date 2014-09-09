from everest.repositories.rdb.testing import check_attributes
from everest.repositories.rdb.testing import persist
from thelma.tests.entity.conftest import TestEntityBase


class TestMoleculeDesignLibraryEntity(TestEntityBase):

    def test_init(self, molecule_design_library_fac):
        mdl = molecule_design_library_fac()
        check_attributes(mdl, molecule_design_library_fac.init_kw)
        assert len(mdl.library_plates) == 0

    def test_persist(self, nested_session, molecule_design_library_fac):
        mdl = molecule_design_library_fac()
        persist(nested_session, mdl, molecule_design_library_fac.init_kw,
                True)


class TestLibraryPlateEntity(TestEntityBase):

    def test_init(self, library_plate_fac):
        lp = library_plate_fac()
        check_attributes(lp, library_plate_fac.init_kw)

    def test_persist(self, nested_session, library_plate_fac):
        lp = library_plate_fac()
        persist(nested_session, lp, library_plate_fac.init_kw, True)

    def test_persist_with_iso(self, nested_session, library_plate_fac,
                              lab_iso_fac):
        kw = library_plate_fac.init_kw
        kw['lab_iso'] = lab_iso_fac()
        lp = library_plate_fac(**kw)
        persist(nested_session, lp, kw, True)
