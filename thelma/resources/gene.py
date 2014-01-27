"""
Gene resource.

NP
"""

from everest.querying.specifications import AscendingOrderSpecification
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.interfaces import IMoleculeDesign
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import ISpecies
from thelma.resources.base import RELATION_BASE_URL
from everest.constants import CARDINALITIES


__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2013-02-12 09:16:49 +0100 (Tue, 12 Feb 2013) $'
__revision__ = '$Rev: 13137 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/resources/gene.py   $'

__all__ = ['GeneCollection',
           'GeneMember',
           ]


class GeneMember(Member):
    relation = "%s/gene" % RELATION_BASE_URL
    title = attribute_alias('locus_name')

    accession = terminal_attribute(str, 'accession')
    locus_name = terminal_attribute(str, 'locus_name')
#    nice_name = terminal_attribute('nice_name')
    species = member_attribute(ISpecies, 'species')
    molecule_designs = \
        collection_attribute(IMoleculeDesign,
                             'molecule_designs',
                             cardinality=CARDINALITIES.MANYTOMANY)
    molecule_design_pools = \
        collection_attribute(IMoleculeDesignPool,
                             'molecule_design_pools',
                             cardinality=CARDINALITIES.MANYTOMANY)


class GeneCollection(Collection):
    title = 'Genes'
    root_name = 'genes'
    description = 'Manage Genes'
    default_order = AscendingOrderSpecification('accession')
