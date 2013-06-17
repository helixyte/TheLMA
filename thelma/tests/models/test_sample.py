'''
Created on Jun 20, 2011

@author: berger
'''
from everest.testing import RdbContextManager
from thelma.interfaces import IContainer
from thelma.models.sample import Molecule
from thelma.models.sample import Sample
from thelma.models.sample import SampleMolecule
from thelma.models.sample import StockSample
from thelma.testing import ThelmaModelTestCase


class MoleculeModelTest(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.supplier = self._create_organization()
        self.supplier.id = 4
        self.md = None # FIXME: add MoleculeDesign #pylint: disable=W0511

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.supplier
        del self.md

    def test_molecule_init(self):
        m = Molecule(self.md, self.supplier)
        self.assert_not_equal(m, None)
        self.assert_equal(m.supplier, self.supplier)
        #self.assert_equal(m.molecule_design, self.md)

    def test_molecule_equality(self):
        id1 = 1
        id2 = 2
        m1 = Molecule(self.md, self.supplier)
        m1.id = id1
        m2 = Molecule(self.md, self.supplier)
        m2.id = id2
        other_sup = self._create_organization(name='Abgene')
        other_sup.id = 27
        m3 = Molecule(self.md, other_sup)
        m3.id = id1
        self.assert_not_equal(m1, m2)
        self.assert_equal(m1, m3)
        self.assert_not_equal(m1, id1)


class SampleModelTest(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.volume = 10
        self.container = self._get_entity(IContainer)

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.volume

    def test_sample_init(self):
        sample = Sample(self.volume, self.container)
        self.assert_not_equal(sample, None)
        self.assert_equal(sample.volume, self.volume)
        self.assert_equal(sample.container, self.container)

    def test_sample_equality(self):
        id1 = 1
        id2 = 2
        # FIXME: Stricly speaking, we need three *different* containers here
        #        since a container can only have a single sample.
        s1 = Sample(self.volume, self.container)
        s1.id = id1
        s2 = Sample(self.volume, self.container)
        s2.id = id2
        s3 = Sample(20, self.container)
        s3.id = id1
        self.assert_not_equal(s1, s2)
        self.assert_equal(s1, s3)
        self.assert_not_equal(s1, id1)


class SampleMoleculeModelTest(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.supplier = self._create_organization()
        self.supplier.id = 4
        self.concentration = 5

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.supplier
        del self.concentration

    def test_sample_molecule_init(self):
        molecule = self._create_molecule()
        molecule.id = 1
        sample = self._create_sample()
        sample.id = 2
        sm = SampleMolecule(molecule, self.concentration)
        self.assert_false(sm is None)
        self.assert_equal(sm.molecule, molecule)
        self.assert_equal(sm.concentration, self.concentration)
        self.assert_equal(sm.freeze_thaw_cycles, 0)
        self.assert_equal(sm.sample, None)
        sm2 = SampleMolecule(molecule, self.concentration, sample)
        self.assert_equal(sm2.sample, sample)

    def test_sample_molecule_equality(self):
        molecule1 = self._create_molecule()
        molecule1.id = 1
        molecule2 = self._create_molecule()
        molecule2.id = 1
        molecule3 = self._create_molecule()
        molecule3.id = 2
        container = self._get_entity(IContainer)
        sample1 = self._create_sample(container=container)
        sample1.id = 1
        sample2 = self._create_sample(container=container)
        sample2.id = 1
        sample3 = self._create_sample(container=container)
        sample3.id = 3
        sm1 = SampleMolecule(molecule1, self.concentration, sample1)
        sm2 = SampleMolecule(molecule2, self.concentration, sample2)
        sm3 = SampleMolecule(molecule1, 20, sample1)
        sm4 = SampleMolecule(molecule3, self.concentration, sample1)
        sm5 = SampleMolecule(molecule1, self.concentration, sample3)
        self.assert_equal(sm1, sm2)
        self.assert_equal(sm1, sm3)
        self.assert_not_equal(sm1, sm4)
        self.assert_not_equal(sm1, sm5)
        self.assert_not_equal(sm1, self.concentration)


class StockSampleTestCase(ThelmaModelTestCase):
    def set_up(self):
        ThelmaModelTestCase.set_up(self)

    def test_convert_from_sample(self):
        with RdbContextManager() as session:
            container = self._create_tube()
            sample = container.make_sample(1e-5)
            molecule = self._create_molecule()
            sm = sample.make_sample_molecule(molecule, 1e-5)
            self.assert_true(sm in sample.sample_molecules)
            session.add(sample)
            sample.convert_to_stock_sample()
            session.commit()
            s_id = sample.id
            supl_id = sample.supplier.id
            s_mdp_id = sample.molecule_design_pool.id
            cnc = sample.concentration
            mt_id = sample.molecule_type.id
            session.expunge(sample)
            del sample
            spl_reloaded = session.query(Sample).filter_by(id=s_id).one()
            self.assert_true(isinstance(spl_reloaded, StockSample))
            self.assert_equal(spl_reloaded.molecule_design_pool.id, s_mdp_id)
            self.assert_equal(spl_reloaded.supplier.id, supl_id)
            self.assert_equal(spl_reloaded.molecule_type.id, mt_id)
            self.assert_equal(spl_reloaded.concentration, cnc)
