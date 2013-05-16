"""
FOG Mar 29, 2011
"""

from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.interfaces import IRackPositionSet
from thelma.interfaces import ITag
from thelma.resources.base import RELATION_BASE_URL


__docformat__ = 'reStructuredText en'

__author__ = 'F Oliver Gathmann'
__date__ = '$Date: 2013-02-12 09:16:49 +0100 (Tue, 12 Feb 2013) $'
__revision__ = '$Rev: 13137 $'
__source__ = '$URL::                                                          $'

__all__ = ['TagCollection',
           'TagMember',
           'TaggedRackPositionSetCollection',
           'TaggedRackPositionSetMember',
           ]


class TagMember(Member):
    relation = "%s/tag" % RELATION_BASE_URL
#    title = attribute_alias('slug')
    domain = terminal_attribute(str, 'domain')
    predicate = terminal_attribute(str, 'predicate')
    value = terminal_attribute(str, 'value')


class TagCollection(Collection):
    title = 'Tags'
    root_name = 'tags'
    description = 'Manage tags.'


class TaggedRackPositionSetMember(Member):
    relation = "%s/tagged-rack-position-set" % RELATION_BASE_URL
    tags = collection_attribute(ITag, 'tags')
    rack_position_set = member_attribute(IRackPositionSet, 'rack_position_set')

#    @property
#    def positions(self):
#        positions = set()
#        for position in self.get_entity().rack_position_set:
#            positions.add(position)
#        return self.get_entity().tags


class TaggedRackPositionSetCollection(Collection):
    title = 'TaggedRackPositionSets'
    root_name = 'tagged-rack-position-sets'
    description = 'Manage Tagged Rack Position Sets.'
