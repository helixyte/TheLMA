"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Stock info entity classes.
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
    #: (:class:`thelma.entities.moleculedesign.MoleculeDesignPool`)
    molecule_design_pool = None
    #: A list of genes (:class:`thelma.entities.gene.Gene`) targeted by the
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
    #: The molecule type (:class:`thelma.entities.moleculetype.MoleculeType`)
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

    def __str__(self):
        return self.slug
