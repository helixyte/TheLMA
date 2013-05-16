"""
Rack layout resource.

AAB, 01st Aug 2011
"""

from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from thelma.resources.base import RELATION_BASE_URL
from thelma.interfaces import IRackShape
from thelma.interfaces import ITaggedRackPositionSet

__docformat__ = 'reStructuredText en'

__author__ = 'Anna-Antonia Berger'
__date__ = '$Date:  $'
__revision__ = '$Rev:  $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/resources/racklayou#$'

__all__ = ['RackLayoutCollection',
           'RackLayoutMember',
           ]


class RackLayoutMember(Member):
    relation = '%s/rack-layout' % RELATION_BASE_URL

    @property
    def title(self):
        return str(self.id)

    shape = member_attribute(IRackShape, 'shape')
    tagged_rack_position_sets = \
                    collection_attribute(ITaggedRackPositionSet,
                                         'tagged_rack_position_sets')

#    @property
#    def rack(self):
#        tags = []
#        for tp in self.tagged_rack_position_sets:
#            tags.append(tp)
#        return tags

    def __getitem__(self, name):
        if name == 'tagged-rack-position-sets':
            return self.tagged_rack_position_sets
        else:
            raise KeyError(name)


class RackLayoutCollection(Collection):
    title = 'Rack Layouts'
    root_name = 'rack-layouts'
    description = 'Manage rack layouts'