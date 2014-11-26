"""
Gene entity classes.

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
    #: Accession number.
    accession = None
    #: Gene locus name.
    locus_name = None
    #: Species for this gene (:class:`thelma.entities.species.Species`).
    species = None
    #: List of molecule designs targeting this gene.
    #: (:class:`thelma.entities.moleculedesign.MoleculeDesign`)
    molecule_designs = []
    #: List of molecule design pools targeting this gene.
    #: (:class:`thelma.entities.moleculedesign.MoleculeDesignPool`)
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
        return (isinstance(other, Gene) and self.accession == other.accession)

    def __str__(self):
        return self.accession

    def __repr__(self):
        str_format = '<%s accession: %s, locus_name: %s, species: %s>'
        params = (self.__class__.__name__, self.accession, self.locus_name,
                  self.species)
        return str_format % params
