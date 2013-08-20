'''
Created on May 25, 2011

@author: berger
'''

from thelma.models.moleculetype import MOLECULE_TYPE_IDS
from thelma.models.moleculetype import MoleculeType
from thelma.testing import ThelmaModelTestCase


class MoleculeTypeModelTest(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.name = 'siRNA'
        self.default_stock_concentration = 1e-4
        self.description = 'more about it'
        self.thaw_time = 1

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.name
        del self.description
        del self.thaw_time

    def test_molecule_type_init(self):
        mt = MoleculeType(self.name, self.default_stock_concentration,
                          description=self.description,
                          thaw_time=self.thaw_time)
        attr = dict(name=self.name,
                    default_stock_concentration=
                                    self.default_stock_concentration,
                    description=self.description,
                    thaw_time=self.thaw_time)
        self.assert_not_equal(mt, None)
        for attr_name, wanted_value in attr.iteritems():
            self.assert_equal(getattr(mt, attr_name), wanted_value)
        self.assert_not_equal(mt.slug, None)

    def test_molecule_type_slug(self):
        name = 'si RNA'
        slug = 'si-rna'
        mt = MoleculeType(name, 1e-4)
        mt.id = id
        self.assert_not_equal(mt.slug, name)
        self.assert_equal(mt.slug, slug)

    def test_molecule_type_equality(self):
        mt1 = MoleculeType(self.name, self.default_stock_concentration,
                           id=self.name)
        mt2 = MoleculeType(MOLECULE_TYPE_IDS.SIRNA, 5e-5)
        mt3 = MoleculeType(MOLECULE_TYPE_IDS.SIRNA, 5e-5)
        self.assert_not_equal(mt1, mt2)
        self.assert_equal(mt2, mt3)
        self.assert_not_equal(mt1, self.name)
