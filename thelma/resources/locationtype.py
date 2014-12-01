"""
Location type resource.
"""
from everest.querying.specifications import AscendingOrderSpecification
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import terminal_attribute
from thelma.resources.base import RELATION_BASE_URL


#from everest.resources.descriptors import collection_attribute
#from thelma.interfaces import ILocation
__docformat__ = 'reStructuredText en'
__all__ = ['LocationTypeCollection',
           'LocationTypeMember',
           ]


class LocationTypeMember(Member):
    relation = "%s/location-type" % RELATION_BASE_URL
    title = attribute_alias('name')
    name = terminal_attribute(str, 'name')
#    locations = collection_attribute('locations', ILocation,
#                                     backref_attr='type')


class LocationTypeCollection(Collection):
    title = 'Location Types'
    root_name = 'location-types'
    description = 'Manage location types'
    default_order = AscendingOrderSpecification('name')
