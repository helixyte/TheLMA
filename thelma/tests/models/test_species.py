'''
Created on May 25, 2011

@author: berger
'''

from everest.testing import RdbContextManager
from everest.testing import check_attributes
from thelma.models.species import Species
from thelma.testing import ThelmaModelTestCase


class SpeciesModelTest(ThelmaModelTestCase):

    model_class = Species

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.genus_name = 'Homo'
        self.species_name = 'sapiens'
        self.common_name = 'human'
        self.acronym = 'HS'
        self.ncbi_tax_id = 9606

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.genus_name
        del self.species_name
        del self.common_name
        del self.acronym
        del self.ncbi_tax_id

    def test_load_10_species(self):
        with RdbContextManager() as session:
            query = session.query(self.model_class)
            species = query.limit(5).all()
            self.assert_equal(len(species), 5)

    def test_species_values(self):
        with RdbContextManager() as session:
            s = session.query(self.model_class).filter_by(id=3).one()
            attrs = dict(id=3,
                         genus_name='Mus',
                         species_name='musculus',
                         common_name='mouse',
                         acronym='MM',
                         ncbi_tax_id=10090)
            check_attributes(s, attrs)

    def test_species_init(self):
        species = Species(self.genus_name, self.species_name, self.common_name,
                          self.acronym, self.ncbi_tax_id)
        self.assert_not_equal(species, None)
        attr = dict(genus_name=self.genus_name,
                    species_name=self.species_name,
                    acronym=self.acronym,
                    common_name=self.common_name,
                    ncbi_tax_id=self.ncbi_tax_id)
        for attr_name, wanted_value in attr.iteritems():
            self.assert_equal(getattr(species, attr_name), wanted_value)
        self.assert_equal(len(species.genes), 0)
        self.assert_not_equal(species.slug, None)

    def test_species_slug(self):
        name = 'Default Human'
        name_slug = 'default-human'
        species = Species(self.genus_name, self.species_name, name,
                          self.acronym, self.ncbi_tax_id)
        self.assert_not_equal(species.slug, name)
        self.assert_equal(species.slug, name_slug)

    def test_species_equality(self):
        species1 = Species(self.genus_name, self.species_name, self.common_name,
                           self.acronym, self.ncbi_tax_id)
        species2 = Species(self.genus_name, self.species_name, self.common_name,
                           self.acronym, self.ncbi_tax_id)
        species3 = Species('other_genus', self.species_name, self.common_name,
                           self.acronym, self.ncbi_tax_id)
        species4 = Species(self.genus_name, 'other_species', self.common_name,
                           self.acronym, self.ncbi_tax_id)
        species5 = Species(self.genus_name, self.species_name, 'other_name',
                           self.acronym, self.ncbi_tax_id)
        species6 = Species(self.genus_name, self.species_name, self.common_name,
                           'other_ACR', self.ncbi_tax_id)
        species7 = Species(self.genus_name, self.species_name, self.common_name,
                           self.acronym, 8117)
        self.assert_equal(species1, species2)
        self.assert_equal(species1, species3)
        self.assert_equal(species1, species4)
        self.assert_not_equal(species1, species5)
        self.assert_equal(species1, species6)
        self.assert_equal(species1, species7)
        self.assert_not_equal(species1, self.common_name)
