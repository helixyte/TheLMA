"""
Gene model classes.

NP, AAB
"""

from everest.entities.base import Entity
from everest.entities.utils import slug_from_string


__docformat__ = 'reStructuredText en'

__all__ = ['Gene',
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
