"""
Gene model classes.

NP, AAB
"""

from everest.entities.base import Entity
from everest.entities.utils import slug_from_string


__docformat__ = 'reStructuredText en'

__all__ = ['Gene',
           'Target',
           'TargetSet',
           'Transcript',
           ]

class Gene(Entity):
    """
    This class represents particular genes.

    **Equality Condition**: equal :attr:`accession`
    """

    #: The accession number of that gene.
    accession = None
    #: The name of the gene locus.
    locus_name = None
    #: The species (:class:`thelma.models.species.Species`)
    #: this gene is taken from.
    species = None
    #: A list of molecule designs targeting this gene.
    #: (:class:`thelma.models.moleculedesign.MoleculeDesign`)
    #: targeting that gene.
    molecule_designs = []
    #: A list of molecule design pools targeting this gene.
    #: (:class:`thelma.models.moleculedesign.MoleculeDesignPool`)
    #: targeting that gene.
    molecule_design_pools = []

    def __init__(self, accession, locus_name, species,
                 molecule_designs=None, molecule_design_pools=None, **kw):
        Entity.__init__(self, **kw)
        self.accession = accession
        self.locus_name = locus_name
        self.species = species
        if molecule_designs is None:
            molecule_designs = []
        self.molecule_designs = molecule_designs
        if molecule_design_pools is None:
            molecule_design_pools = []
        self.molecule_design_pools = molecule_design_pools

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`accession`.
        return slug_from_string(self.accession)

    def __eq__(self, other):
        """Equality operator

        Equality is based on ID only
        """
        return (isinstance(other, Gene) and self.accession == other.accession)

    def __str__(self):
        return self.accession

    def __repr__(self):
        str_format = '<%s accession: %s, locus_name: %s, species: %s>'
        params = (self.__class__.__name__, self.accession, self.locus_name,
                  self.species)
        return str_format % params


class Transcript(Entity):
    """
    This class represents a particular transcript

    **Equality Condition**: equal :attr:`accession`
    """

    #: The accession of this transcript (:class:`string`).
    accession = None
    #: The gene this transcripts belongs to.
    gene = None
    #: The species (:class:`thelma.models.species.Species`) this transcript
    #: belongs to.
    species = None

    def __init__(self, accession, gene, **kw):
        Entity.__init__(self, **kw)
        self.accession = accession
        self.gene = gene
        self.species = self.gene.species

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`accession`.
        return slug_from_string(self.accession)

    def __eq__(self, other):
        return (isinstance(other, Transcript) \
                and other.accession == self.accession)

    def __str__(self):
        return self.accession

    def __repr__(self):
        str_format = '<%s, id: %s, accession: %s, gene: %s, species: %s>'
        params = (self.__class__.__name__, self.id, self.accession,
                  self.gene, self.species)
        return str_format % params


class Target(Entity):
    """
    This class represents a target for a screen or project.

    **Equality Condition**: equal :attr:`molecule_design` and :attr:`transcript`
    """

    #: The slug of a target object is derived from its :attr:`id`.
    slug = None
    #: This is the targeted transcript (:class:`Transcript`).
    transcript = None
    #: The molecule design (:attr:`thelma.models.moleculedesign.MoleculeDesign`)
    #: that is to affect the transcript.
    molecule_design = None

    def __init__(self, transcript, molecule_design, **kw):
        Entity.__init__(self, **kw)
        self.transcript = transcript
        self.molecule_design = molecule_design

    def __eq__(self, other):
        return (isinstance(other, Target) \
                and other.transcript == self.transcript \
                and other.molecule_design == self.molecule_design)

    def __str__(self):
        return '%i' % (self.id)

    def __repr__(self):
        str_format = '<%s, id: %s, transcript: %s, molecule design: %s>'
        params = (self.__class__.__name__, self.id, self.transcript,
                  self.molecule_design)
        return str_format % params


class TargetSet(Entity):
    """
    This class represents the targets for a molecule design set.

    **Equality Condition**: equal :attr:`id`
    """

    #: The label for this target set.
    label = None
    #: A set of targets (:class:`Target`).
    targets = None

    def __init__(self, label, targets, **kw):
        Entity.__init__(self, **kw)
        self.label = label
        self.targets = targets

    def __eq__(self, other):
        return isinstance(other, TargetSet) \
               and other.label == self.label \
               and other.targets == self.targets

    def __str__(self):
        return '%i' % (self.id)

    def __contains__(self, target):
        """
        Checks whether the target set contains a certain target.

        :param target: A target
        :type target: :class:`TargetSet`
        :return: :class:`boolean`
        """
        return target in self.targets

    def __iter__(self):
        return iter(self.targets)
