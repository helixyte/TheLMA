"""
Created on May 25, 2011

@author: berger
"""

from everest.testing import RdbContextManager
from everest.testing import check_attributes
from thelma.interfaces import IGene
from thelma.models.gene import Gene
from thelma.models.gene import Target
from thelma.models.gene import TargetSet
from thelma.models.gene import Transcript
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


class TranscriptModelTest(ThelmaModelTestCase):
    model_class = Transcript

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.accession = 'NM_7319'
        self.gene = self._get_entity(IGene)

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.accession
        del self.gene

    def test_load_10_transcripts(self):
        with RdbContextManager() as session:
            query = session.query(self.model_class).limit(10)
            transcripts = query.all()
            self.assert_equal(len(transcripts), 10)

# FIXME: reenable once we have new transcript data #pylint:disable=W0511
#    def test_transcript_values(self):
#        tr = self._session.query(self.model_class).filter_by(id=13659).one()
#        g = self._session.query(Gene).filter_by(id=81339).one()
#        sp = self._session.query(Species).filter_by(id=2).one()
#        attributes = dict(id=13659,
#                          accession='CG10002-RA',
#                          slug='cg10002-ra',
#                          gene=g,
#                          species=sp)
#        check_attributes(tr, attributes)

    def test_transcript_init(self):
        transcript = Transcript(self.accession, self.gene)
        self.assert_not_equal(transcript, None)
        attributes = dict(accession=self.accession,
                          gene=self.gene,
                          species=self.gene.species)
        check_attributes(transcript, attributes)
        self.assert_not_equal(transcript.slug, None)
        self.assert_equal(transcript.id, None)

    def test_transcript_slug(self):
        acc_slug = 'nm-7319'
        transcript = Transcript(self.accession, self.gene)
        self.assert_not_equal(transcript.slug, self.accession)
        self.assert_equal(transcript.slug, acc_slug)

    def test_transcript_equality(self):
        t1 = Transcript(self.accession, self.gene)
        t2 = Transcript(self.accession, self.gene)
        t3 = Transcript('NM-98786', self.gene)
        other_gene = Gene('123', 'geneA', self.gene.species)
        t4 = Transcript(self.accession, other_gene)
        self.assert_equal(t1, t2)
        self.assert_not_equal(t1, t3)
        self.assert_equal(t1, t4)
        self.assert_not_equal(t1, self.accession)


class TargetModelTest(ThelmaModelTestCase):
    model_class = Target

#    def test_load_10_targets(self):
#        query = self._session.query(self.model_class)
#        targets = query.limit(10).all()
#        self.assert_equal(len(targets), 10)

#    def test_create_target(self):
#        md = self._session.query(MoleculeDesign).filter_by(id=11).one()
#        tr = self._session.query(Transcript).filter_by(id=13659).one()
#        attrs = dict(transcript=tr, molecule_design=md)
#        self._test_model_attributes(Target, attrs)

    def test_target_init(self):
        transcript = self._create_transcript(accession='NM_678')
        target = Target(transcript, None)
        self.assert_not_equal(target, None)
        self.assert_equal(target.id, None)
        self.assert_equal(target.slug, None)
        self.assert_equal(target.molecule_design, None)
        self.assert_equal(target.transcript, transcript)

    def test_target_equality(self):
        t1 = self._create_transcript(accession='NM_01')
        t2 = self._create_transcript(accession='NM_02')
        md = None
        target1 = Target(t1, md)
        target2 = Target(t1, md)
        target3 = Target(t2, md)
        self.assert_equal(target1, target2)
        self.assert_not_equal(target1, target3)
        self.assert_not_equal(target1, t1)


class TargetSetModelTest(ThelmaModelTestCase):
    model_class = TargetSet

#    def test_load_10_target_sets(self):
#        query = self._session.query(self.model_class)
#        target_sets = query.limit(10).all()
#        self.assert_equal(len(target_sets), 10)

    def test_target_set_init(self):
        target1 = Target(self._create_transcript(accession='NM_01'), None)
        target2 = Target(self._create_transcript(accession='NM_02'), None)
        targets = set([target1, target2])
        ts = TargetSet('label', targets)
        self.assert_not_equal(ts, None)
        self.assert_true(len(ts.targets) == 2)

    def test_target_set_equality(self):
        target1 = Target(self._create_transcript(accession='NM_01'), None)
        target2 = Target(self._create_transcript(accession='NM_02'), None)
        targets = set([target1, target2])
        ts1 = TargetSet('label', targets)
        ts2 = TargetSet('label', targets)
        ts3 = TargetSet('label', set([target1]))
        self.assert_equal(ts1, ts2)
        self.assert_not_equal(ts1, ts3)
        self.assert_not_equal(ts1, target1)
