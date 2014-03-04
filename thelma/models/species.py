"""
Species model classes.

NP, AAB
"""

from everest.entities.base import Entity
from everest.entities.utils import slug_from_string

__docformat__ = 'reStructuredText en'

__all__ = ['Species']

class Species(Entity):
    """
    Represents a species.

    **Equality Condition**: equal :attr:`name`
    """

    #: The name of genus.
    genus_name = None
    #: The name of the Species.
    species_name = None
    #: The common English name of the species.
    common_name = None
    #: An abbreviation.
    acronym = None
    #: The taxological ID from the NCBI.
    ncbi_tax_id = None
    #: A list of genes (:class:`thelma.models.gene.Genes`)
    #: stored in the database for this species.
    genes = []
    #: A list of cell lines (:class:`thelma.models.gene.CellLine`)
    #: stored in the database that are derived from this tissue.
    cell_lines = []

    def __init__(self, genus_name, species_name, common_name, acronym,
                 ncbi_tax_id, genes=None, cell_lines=None, **kw):
        Entity.__init__(self, **kw)
        self.genus_name = genus_name
        self.species_name = species_name
        self.common_name = common_name
        self.acronym = acronym
        self.ncbi_tax_id = ncbi_tax_id
        if genes is None:
            genes = []
        self.genes = genes
        if cell_lines is None:
            cell_lines = []
        self.cell_lines = cell_lines

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`common_name`.
        return slug_from_string(self.common_name)

    def __eq__(self, other):
        return (isinstance(other, Species) \
                and self.common_name == other.common_name)

    def __str__(self):
        return self.common_name

    def __repr__(self):
        str_format = '<%s id: %s, genus_name: %s, species_name: %s, ' \
                     'common_name: %s, acronym: %s, ncbi_tax_id: %s>'
        params = (self.__class__.__name__, self.id, self.genus_name,
                  self.species_name, self.common_name, self.acronym,
                  self.ncbi_tax_id)
        return str_format % params
