"""
Container resources.

NP
"""
from everest.querying.specifications import AscendingOrderSpecification
from everest.querying.specifications import DescendingOrderSpecification
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.interfaces import IContainerSpecs
from thelma.interfaces import IItemStatus
from thelma.interfaces import ILocation
from thelma.interfaces import IRack
from thelma.interfaces import IRackPosition
from thelma.interfaces import IRackSpecs
from thelma.interfaces import ISampleMolecule
from thelma.resources.base import RELATION_BASE_URL
#from thelma.interfaces import IMoleculeDesignPool


__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2012-12-06 20:47:04 +0100 (Thu, 06 Dec 2012) $'
__revision__ = '$Rev: 12985 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/resources/container#$'

__all__ = ['TubeMember',
           'WellMember',
           ]


class ContainerMember(Member):
    relation = "%s/container" % RELATION_BASE_URL

    specs = member_attribute(IContainerSpecs, 'specs')
    location = member_attribute(ILocation, 'location.rack.location')
    position = member_attribute(IRackPosition, 'location.position')
    sample_volume = terminal_attribute(float, 'sample.volume')
    sample_molecules = collection_attribute(ISampleMolecule,
                                            'sample.sample_molecules',
                                            backref='sample.container')
    status = member_attribute(IItemStatus, 'status')
    sample_molecule_design_pool_id = \
                        terminal_attribute(str,
                                           'sample.molecule_design_pool_id')
    rack = member_attribute(IRack, 'location.rack')
    rack_specs = member_attribute(IRackSpecs, 'location.rack.specs')
#    sample_molecule_design_pool = member_attribute(
#                                    IMoleculeDesignPool,
#                                    'sample.molecule_design_pool')


class TubeMember(ContainerMember):
    relation = "%s/tube" % RELATION_BASE_URL

    @property
    def title(self):
        entity = self.get_entity()
        return '%s @ %s' % (entity.barcode or 'NO BARCODE', entity.location)

    barcode = terminal_attribute(str, 'barcode')


class WellMember(ContainerMember):
    relation = "%s/well" % RELATION_BASE_URL

    @property
    def title(self):
        return 'well @ %s' % self.get_entity().location


class ContainerCollection(Collection):
    title = 'Containers'
    root_name = 'containers'


class TubeCollection(ContainerCollection):
    title = 'Tubes'
    root_name = 'tubes'
    description = 'Manage 2D barcoded tubes'
    default_order = DescendingOrderSpecification('barcode')


class WellCollection(ContainerCollection):
    title = 'Wells'
    root_name = 'wells'
    description = 'Manage plate wells'
    default_limit = 1536
    max_limit = 1536
    default_order = DescendingOrderSpecification('rack.barcode') \
                    & AscendingOrderSpecification('position')
