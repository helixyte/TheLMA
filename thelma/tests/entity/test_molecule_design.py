import pytest

from everest.repositories.rdb.testing import check_attributes
from everest.repositories.rdb.testing import persist
from thelma.entities.moleculedesign import DoubleStrandedDesign
from thelma.entities.moleculedesign import MoleculeDesign
from thelma.entities.moleculedesign import SingleStrandedDesign
from thelma.tests.entity.conftest import TestEntityBase


class TestMoleculeDesignEntity(TestEntityBase):
    def test_abstract(self):
        with pytest.raises(NotImplementedError):
            MoleculeDesign(None, None)
        with pytest.raises(NotImplementedError):
            SingleStrandedDesign(None)
        with pytest.raises(NotImplementedError):
            DoubleStrandedDesign(None)

    @pytest.mark.parametrize('fac_name',
                             ['compound_molecule_design_fac',
                              'sirna_molecule_design_fac',
                              ])
    def test_init(self, request, fac_name):
        fac = request.getfuncargvalue(fac_name)
        md = fac()
        check_attributes(md, fac.init_kw)

    @pytest.mark.parametrize('fac_name',
                             ['compound_molecule_design_fac',
                              'sirna_molecule_design_fac',
                              ])
    def test_persist(self, request, nested_session, fac_name):
        fac = request.getfuncargvalue(fac_name)
        md = fac()
        # The attribute check fails occasionally for molecules with more than
        # one chemical structure because the structures are kept in a list
        # and the retrieval order is undefined.
        persist(nested_session, md, fac.init_kw, False)


class TestMoleculeDesignSetEntity(TestEntityBase):

    def test_init(self, molecule_design_set_fac):
        mds = molecule_design_set_fac()
        check_attributes(mds, molecule_design_set_fac.init_kw)

    def test_persist(self, nested_session, molecule_design_set_fac):
        mds = molecule_design_set_fac()
        persist(nested_session, mds, molecule_design_set_fac.init_kw, True)


class TestMoleculeDesignPoolEntity(TestEntityBase):

    def test_init(self, molecule_design_pool_fac):
        mdp = molecule_design_pool_fac()
        check_attributes(mdp, molecule_design_pool_fac.init_kw)

    def test_persist(self, nested_session, molecule_design_pool_fac):
        mdp = molecule_design_pool_fac()
        persist(nested_session, mdp, molecule_design_pool_fac.init_kw, True)


class TestPoolSetEntity(TestEntityBase):

    def test_init(self, molecule_design_pool_set_fac):
        mdps = molecule_design_pool_set_fac()
        check_attributes(mdps, molecule_design_pool_set_fac.init_kw)

    def test_persist(self, nested_session, molecule_design_pool_set_fac):
        mdps = molecule_design_pool_set_fac()
        persist(nested_session, mdps, molecule_design_pool_set_fac.init_kw,
                True)
