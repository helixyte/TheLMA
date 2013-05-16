"""
Stock info model classes.

NP, AAB
"""

from everest.entities.base import Entity

__docformat__ = 'reStructuredText en'

__all__ = ['StockInfo']


class StockInfo(Entity):
    """
    Information on stock samples.

    Stock info items report on the availability of stock sample tubes
    per molecule design pool ID and concentration.
    """

    #: The molecule design set requested for this stock info item.
    #: (:class:`thelma.models.moleculedesign.MoleculeDesignPool`)
    molecule_design_pool = None
    #: A list of genes (:class:`thelma.models.gene.Gene`) targeted by the
    #: designs in the pool.
    genes = None
    #: The concentration requested for this stock info item.
    concentration = None
    #: The total number of candidate tubes matching this stock
    #: info item.
    total_tubes = None
    #: The combined volume of all candidate tubes matching this stock info
    #: item.
    total_volume = None
    #: The minimum acceptable volume for candidates matching this stock info
    #: item.
    minimum_volume = None
    #: The maximum acceptable volume for candidates matching this stock info
    #: item.
    maximum_volume = None
    #: The molecule type (:class:`thelma.models.moleculetype.MoleculeType`)
    #: for the molecule designs in this stock info item..
    molecule_type = None

    def __init__(self, molecule_design_pool, molecule_type, concentration,
                 total_tubes, total_volume, minimum_volume, maximum_volume,
                 **kw):
        Entity.__init__(self, **kw)
        self.molecule_design_pool = molecule_design_pool
        self.molecule_type = molecule_type
        self.concentration = concentration
        self.total_tubes = total_tubes
        self.total_volume = total_volume
        self.minimum_volume = minimum_volume
        self.maximum_volume = maximum_volume
        self.genes = []

    @property
    def slug(self):
        return self.id

    def __eq__(self, other):
        """Equality operator

        Equality is based on the slug.
        """
        return (isinstance(other, StockInfo) and self.slug == other.slug)

    def __str__(self):
        return self.slug
