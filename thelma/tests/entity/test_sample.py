from thelma.tests.entity.conftest import TestEntityBase
from everest.repositories.rdb.testing import check_attributes
from everest.repositories.rdb.testing import persist


class TestMoleculeEntity(TestEntityBase):

    def test_init(self, molecule_fac):
        mol = molecule_fac()
        check_attributes(mol, molecule_fac.init_kw)

    def test_persist(self, nested_session, molecule_fac):
        mol = molecule_fac()
        persist(nested_session, mol, molecule_fac.init_kw, True)


class TestSampleEntity(TestEntityBase):

    def test_init(self, sample_fac):
        spl = sample_fac()
        check_attributes(spl, sample_fac.init_kw)

    def test_persist(self, nested_session, sample_fac):
        spl = sample_fac()
        persist(nested_session, spl, sample_fac.init_kw, True)


class TestSampleMoleculeEntity(TestEntityBase):

    def test_init(self, sample_molecule_fac):
        sm = sample_molecule_fac()
        check_attributes(sm, sample_molecule_fac.init_kw)

    def test_persist(self, nested_session, sample_molecule_fac):
        sm = sample_molecule_fac()
        persist(nested_session, sm, sample_molecule_fac.init_kw, True)


class TestStockSampleEntity(TestEntityBase):

    def test_init(self, stock_sample_fac):
        sspl = stock_sample_fac()
        check_attributes(sspl, stock_sample_fac.init_kw)

    def test_persist(self, nested_session, stock_sample_fac):
        sspl = stock_sample_fac()
        persist(nested_session, sspl, stock_sample_fac.init_kw, True)

    def test_convert_from_sample(self, nested_session, tube_fac,
                                 molecule_fac):
        container = tube_fac()
        sample = container.make_sample(1e-5)
        molecule = molecule_fac()
        sm = sample.make_sample_molecule(molecule, 1e-5)
        assert sm in sample.sample_molecules
        # Needs to be in the session or else the conversion will fail.
        nested_session.add(type(sample), sample)
        sample.convert_to_stock_sample()
        attrs = dict(id=sample.id,
                     supplier=sample.supplier,
                     molecule_design_pool=sample.molecule_design_pool,
                     concentration=sample.concentration,
                     molecule_type=sample.molecule_type
                     )
        persist(nested_session, sample, attrs, True)
