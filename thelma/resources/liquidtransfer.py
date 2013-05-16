"""
Liquid transfer resources.

AAB
"""

from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.resources.base import RELATION_BASE_URL
from thelma.interfaces import IRackShape

__docformat__ = 'reStructuredText en'

__author__ = 'Anna-Antonia Berger'

__all__ = ['ReservoirSpecsCollection',
           'ReservoirSpecsMember',
           ]


class ReservoirSpecsMember(Member):
    relation = '%s/reservoirspecs' % RELATION_BASE_URL
    name = terminal_attribute(str, 'name')
    rack_shape = member_attribute(IRackShape, 'rack_shape')
    max_volume = terminal_attribute(float, 'max_volume')
    dead_volume = terminal_attribute(float, 'dead_volume')

class ReservoirSpecsCollection(Collection):
    title = 'Reservoir Specs'
    root_name = 'reservoir-specs'
    description = 'Manage Reservoir Specs'


