'''
Created on May 25, 2011

@author: berger
'''

from thelma.models.moleculemodification import MoleculeModification
from thelma.models.moleculetype import MOLECULE_TYPE_IDS
from thelma.testing import ThelmaModelTestCase


class MoleculeModificationModelsTest(ThelmaModelTestCase):


    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.name = 'ethylation'
        self.molecule_type = self._create_molecule_type()

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.name
        del self.molecule_type

    def test_molecule_modification_init(self):
        mm = MoleculeModification(self.name, self.molecule_type)
        self.assert_not_equal(mm, None)
        self.assert_equal(mm.name, self.name)
        self.assert_equal(mm.molecule_type, self.molecule_type)

    def test_molecule_modification_equality(self):
        mt2 = self._create_molecule_type(name=MOLECULE_TYPE_IDS.GOLD)
        mm1 = MoleculeModification(self.name, self.molecule_type)
        mm2 = MoleculeModification(self.name, self.molecule_type)
        mm3 = MoleculeModification('watered', self.molecule_type)
        mm4 = MoleculeModification(self.name, mt2)
        self.assert_equal(mm1, mm2)
        self.assert_not_equal(mm1, mm3)
        self.assert_not_equal(mm1, mm4)
        self.assert_not_equal(mm1, self.molecule_type)
        self.assert_not_equal(mm1, self.name)
