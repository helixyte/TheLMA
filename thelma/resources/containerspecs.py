"""
Container specs resource.

NP
"""

from everest.querying.specifications import AscendingOrderSpecification
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.interfaces import IOrganization
from thelma.interfaces import IRackSpecs
from thelma.resources.base import RELATION_BASE_URL

__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2012-11-12 12:45:24 +0100 (Mon, 12 Nov 2012) $'
__revision__ = '$Rev: 12945 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/resources/container#$'

__all__ = ['ContainerSpecsCollection',
           'ContainerSpecsMember',
           'TubeSpecsMember',
           'WellSpecsMember',
           ]


class ContainerSpecsMember(Member):
    relation = "%s/container-specs" % RELATION_BASE_URL
    title = attribute_alias('label')
    label = terminal_attribute(str, 'label')
    description = terminal_attribute(str, 'description')
    max_volume = terminal_attribute(float, 'max_volume')
    dead_volume = terminal_attribute(float, 'dead_volume')
    manufacturer = member_attribute(IOrganization, 'manufacturer')


class TubeSpecsMember(ContainerSpecsMember):
    relation = "%s/tube-specs" % RELATION_BASE_URL
    tube_rack_specs = \
        collection_attribute(IRackSpecs, 'tube_rack_specs', is_nested=False)


class WellSpecsMember(ContainerSpecsMember):
    relation = "%s/well-specs" % RELATION_BASE_URL


class ContainerSpecsCollection(Collection):
    title = 'Container Specs'
    root_name = 'container-specs'
    description = 'Manage container specifications'
    default_order = AscendingOrderSpecification('label')


class TubeSpecsCollection(ContainerSpecsCollection):
    title = 'Tube and Well Specs'
    root_name = 'tube-specs'
    description = 'Manage tube and well specifications'


class WellSpecsCollection(ContainerSpecsCollection):
    title = 'Well Specs'
    root_name = 'well-specs'
    description = 'Manage well specifications'
    default_order = AscendingOrderSpecification('label')
