'''
Created on Jun 20, 2011

@author: berger
'''
from everest.repositories.rdb.testing import RdbContextManager
from everest.repositories.rdb.testing import check_attributes
from everest.repositories.rdb.testing import persist
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import IMoleculeType
from thelma.models.chemicalstructure import CompoundChemicalStructure
from thelma.models.chemicalstructure import ModificationChemicalStructure
from thelma.models.gene import Gene
from thelma.models.moleculedesign import CompoundDesign
from thelma.models.moleculedesign import DoubleStrandedDesign
from thelma.models.moleculedesign import MOLECULE_DESIGN_SET_TYPES
from thelma.models.moleculedesign import MoleculeDesign
from thelma.models.moleculedesign import MoleculeDesignSet
from thelma.models.moleculedesign import MoleculeDesignPoolSet
from thelma.models.moleculedesign import SiRnaDesign
from thelma.models.moleculedesign import SingleStrandedDesign
from thelma.models.moleculetype import MOLECULE_TYPE_IDS
from thelma.models.moleculetype import MoleculeType
from thelma.testing import ThelmaModelTestCase
from thelma.interfaces import IMoleculeDesign
from thelma.models.moleculedesign import MoleculeDesignPool


class MoleculeDesignModelTest(ThelmaModelTestCase):

    model_class = MoleculeDesign

    def test_load_10_molecule_designs(self):
        with RdbContextManager() as session:
            query = session.query(self.model_class)
            molecule_designs = query.limit(10).all()
            self.assert_equal(len(molecule_designs), 10)

    def test_molecule_design_values(self):
        with RdbContextManager() as session:
            md = session.query(self.model_class).filter_by(id=11).one()
            mt = session.query(MoleculeType).filter_by(id='SIRNA').one()
            g = session.query(Gene).filter_by(id=39952).one()
            attrs = dict(id=11, molecule_type=mt, genes=[g])
            check_attributes(md, attrs)
            for gn in md.genes:
                self.assert_true(md in gn.molecule_designs)

    def test_molecule_design_init(self):
        molecule_type = self._create_molecule_type()
        self.assert_raises(NotImplementedError, MoleculeDesign,
                           molecule_type, [])


class SingleStrandedMoleculeDesignTest(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.molecule_type = self._create_molecule_type()
        self.molecule_mod = ModificationChemicalStructure('defaultMod')
        self.seq = self._create_rna_sequence(representation='ATCG')

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.molecule_type
        del self.molecule_mod

    def test_ss_molecule_design_init(self):
        self.assert_raises(NotImplementedError, SingleStrandedDesign,
                           self.molecule_type,
                           chemical_structures=[self.seq, self.molecule_mod])


class DoubleStrandedMoleculeDesignTest(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.molecule_type = self._create_molecule_type()
        self.molecule_mod = ModificationChemicalStructure('defaultMod')
        self.seq1 = self._create_rna_sequence(representation='ATCG')
        self.seq2 = self._create_rna_sequence(representation='TCGAT')

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.molecule_type
        del self.molecule_mod
        del self.seq1
        del self.seq2

    def test_ds_molecule_design_init(self):
        self.assert_raises(NotImplementedError, DoubleStrandedDesign,
                           self.molecule_type,
                           chemical_structures=
                                [self.seq1, self.seq2, self.molecule_mod])


class SiRnaDesignModelTest(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.molecule_type = self._create_molecule_type(
                                                name=MOLECULE_TYPE_IDS.SIRNA)
        self.molecule_mod = ModificationChemicalStructure('defaultMod')
        self.seq1 = self._create_rna_sequence(representation='ATCG')
        self.seq2 = self._create_rna_sequence(representation='TCGAT')
        self.init_data = dict(molecule_type=self.molecule_type,
                              chemical_structures=
                                [self.seq1, self.seq2, self.molecule_mod])

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.molecule_type
        del self.molecule_mod
        del self.seq1
        del self.seq2
        del self.init_data

    def test_sirna_init(self):
        sirna = SiRnaDesign(**self.init_data)
        self.assert_not_equal(sirna, None)
        check_attributes(sirna, self.init_data)
        self.assert_equal(len(sirna.genes), 0)

    def test_wrong_molecule_type(self):
        wrong_type = self._create_molecule_type(name=MOLECULE_TYPE_IDS.SSDNA)
        self.assert_raises(ValueError, SiRnaDesign,
                           wrong_type,
                           chemical_structures=
                                    [self.seq1, self.seq2, self.molecule_mod])


class CompoundDesignModelTest(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.smiles = 'CH3-CH2OH'
        self.smiles = CompoundChemicalStructure('CH3-CH2OH')
        self.molecule_type = self._create_molecule_type(
                                            name=MOLECULE_TYPE_IDS.COMPOUND)
        self.init_data = dict(molecule_type=self.molecule_type,
                              chemical_structures=[self.smiles])

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.smiles
        del self.molecule_type
        del self.init_data

    def test_compound_init(self):
        cd = CompoundDesign(self.molecule_type, [self.smiles])
        self.assert_false(cd is None)
        check_attributes(cd, self.init_data)

    def test_wrong_molecule_type(self):
        wrong_type = self._create_molecule_type(name=MOLECULE_TYPE_IDS.SSDNA)
        tup = (wrong_type, self.smiles)
        self.assert_raises(ValueError, CompoundDesign, *tup) # pylint: disable=W0142


class MoleculeDesignSetModelTest(ThelmaModelTestCase):

    def test_init(self):
        md_set = set()
        md_set.add(self._get_entity(IMoleculeDesign, '213458'))
        mds = MoleculeDesignSet(molecule_designs=md_set)
        self.assert_is_not_none(mds)
        self.assert_equal(mds.set_type, MOLECULE_DESIGN_SET_TYPES.STANDARD)

class MoleculeDesignPoolModelTest(ThelmaModelTestCase):

    model_class = MoleculeDesignPool

    def test_load_2_molecule_design_pools(self):
        with RdbContextManager() as session:
            query = session.query(self.model_class)
            molecule_design_sets = query.limit(2).all()
            self.assert_equal(len(molecule_design_sets), 2)


class PoolSetModelTest(ThelmaModelTestCase):

    model_class = MoleculeDesignPoolSet

    def __get_data(self):
        molecule_type = self._get_entity(IMoleculeType)
        pool = self._get_entity(IMoleculeDesignPool)
        return dict(molecule_type=molecule_type,
                    molecule_design_pools=set([pool]))

    def test_init(self):
        attrs = self.__get_data()
        ps = self._create_molecule_design_pool_set(**attrs)
        self.assert_is_not_none(ps)
        check_attributes(ps, attrs)

    def test_persist(self):
        with RdbContextManager() as session:
            attrs = self.__get_data()
            persist(session, self.model_class, attrs, True)
