"""
Created on May 25, 2011

@author: berger
"""

from everest.repositories.rdb.testing import RdbContextManager
from everest.repositories.rdb.testing import check_attributes
from thelma.models.gene import Gene
from thelma.models.species import Species
from thelma.testing import ThelmaModelTestCase


class GeneModelTest(ThelmaModelTestCase):
    model_class = Gene

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.accession = '641519'
        self.locus_name = 'Defb29'
        self.species = self._create_species()

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.accession
        del self.locus_name
        del self.species

    def test_load_10_genes(self):
        with RdbContextManager() as session:
            query = session.query(self.model_class).limit(10)
            genes = query.all()
            self.assert_equal(len(genes), 10)

    def test_gene_values(self):
        with RdbContextManager() as session:
            gene = session.query(self.model_class).filter_by(id=81339).one()
            sp = session.query(Species).filter_by(id=3).one()
            attributes = dict(id=81339,
                              accession='259086',
                              slug='259086',
                              locus_name='Olfr609',
                              species=sp)
            check_attributes(gene, attributes)
            for md in gene.molecule_designs:
                self.assert_true(gene in md.genes)

    def test_gene_init(self):
        gene = Gene(self.accession, self.locus_name, self.species)
        self.assert_not_equal(gene, None)
        attributes = dict(accession=self.accession,
                         locus_name=self.locus_name,
                         species=self.species)
        check_attributes(gene, attributes)
        self.assert_not_equal(gene.slug, None)

    def test_gene_slug(self):
        accession = 'A2 34'
        acc_slug = 'a2-34'
        gene = Gene(accession, self.locus_name, self.species)
        self.assert_not_equal(gene.slug, accession)
        self.assert_equal(gene.slug, acc_slug)

    def test_gene_equality(self):
        id1 = 1
        id2 = 2
        gene1 = Gene(self.accession, self.locus_name, self.species)
        gene1.id = id1
        gene2 = Gene(self.accession, self.locus_name, self.species)
        gene2.id = id2
        gene3 = Gene('123', self.locus_name, self.species)
        gene3.id = id1
        gene4 = Gene(self.accession, 'L1', self.species)
        gene4.id = id1
        species2 = Species('Homo', 'cenixiensis', 'human', 'HC', 10000)
        gene5 = Gene(self.accession, self.locus_name, species2)
        gene5.id = id1
        self.assert_equal(gene1, gene2)
        self.assert_not_equal(gene1, gene3)
        self.assert_equal(gene1, gene4)
        self.assert_equal(gene1, gene5)
        self.assert_not_equal(gene1, id1)
