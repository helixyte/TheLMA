import pytest

from everest.repositories.rdb.testing import check_attributes
from everest.repositories.rdb.testing import persist
from thelma.tests.entity.conftest import TestEntityBase


class TestNucleicAcidChemicalStructureEntity(TestEntityBase):

    def test_init(self, nucleic_acid_chemical_structure_fac):
        na_cs = nucleic_acid_chemical_structure_fac()
        check_attributes(na_cs, nucleic_acid_chemical_structure_fac.init_kw)

    @pytest.mark.parametrize('kw', [dict(representation='ATGTCTEA')])
    def test_init_invalid(self, nucleic_acid_chemical_structure_fac, kw):
        with pytest.raises(ValueError):
            nucleic_acid_chemical_structure_fac(**kw)

    @pytest.mark.parametrize('kw1,kw2,result',
                             [(dict(id=-1), dict(id=-1), True),
                              (dict(id=-1),
                               dict(id=-1, representation='CTATAU'), False)])
    def test_equality(self, nucleic_acid_chemical_structure_fac, kw1, kw2,
                      result):
        cs1 = nucleic_acid_chemical_structure_fac(**kw1)
        cs2 = nucleic_acid_chemical_structure_fac(**kw2)
        assert (cs1 == cs2) is result

    def test_persist(self, nested_session,
                     nucleic_acid_chemical_structure_fac):
        na_cs = nucleic_acid_chemical_structure_fac()
        persist(nested_session, na_cs,
                nucleic_acid_chemical_structure_fac.init_kw, True)

