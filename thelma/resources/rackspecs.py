"""
Rack specs resource.

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
from thelma.interfaces import IRackShape
from thelma.interfaces import ITubeSpecs
from thelma.interfaces import IWellSpecs
from thelma.resources.base import RELATION_BASE_URL


__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2013-02-12 09:16:49 +0100 (Tue, 12 Feb 2013) $'
__revision__ = '$Rev: 13137 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/resources/rackspecs#$'

__all__ = ['PlateSpecsCollection',
           'PlateSpecsMember',
           'RackSpecsCollection',
           'RackSpecsMember',
           'TubeRackSpecsCollection',
           'TubeRackSpecsMember',
           ]


class RackSpecsMember(Member):
    relation = "%s/rack-specs" % RELATION_BASE_URL
    title = attribute_alias('label')
    label = terminal_attribute(str, 'label')
    shape = member_attribute(IRackShape, 'shape')
    manufacturer = member_attribute(IOrganization, 'manufacturer')
    has_tubes = terminal_attribute(bool, 'has_tubes')


class TubeRackSpecsMember(RackSpecsMember):
    relation = "%s/tube-rack-specs" % RELATION_BASE_URL
    tube_specs = collection_attribute(ITubeSpecs, 'tube_specs',
                                      is_nested=False)


class PlateSpecsMember(RackSpecsMember):
    relation = "%s/plate-specs" % RELATION_BASE_URL
    well_specs = member_attribute(IWellSpecs, 'well_specs')


class RackSpecsCollection(Collection):
    title = 'Rack Specs'
    root_name = 'rack-specs'
    description = 'Manage rack specifications'
    default_order = AscendingOrderSpecification('label')


class TubeRackSpecsCollection(Collection):
    title = 'Tube Rack Specs'
    root_name = 'tube-rack-specs'
    description = 'Manage tube rack specifications'
    default_order = AscendingOrderSpecification('label')


class PlateSpecsCollection(Collection):
    title = 'Plate Specs'
    root_name = 'plate-specs'
    description = 'Manage plate specifications'
    default_order = AscendingOrderSpecification('label')
