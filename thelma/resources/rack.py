"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Rack resource.
"""
from datetime import datetime

from everest.constants import CARDINALITIES
from everest.querying.specifications import DescendingOrderSpecification
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.interfaces import IItemStatus
from thelma.interfaces import ILocation
from thelma.interfaces import IRackPosition
from thelma.interfaces import IRackSpecs
from thelma.interfaces import ITube
from thelma.interfaces import IWell
from thelma.resources.base import RELATION_BASE_URL


__docformat__ = 'reStructuredText en'
__all__ = ['PlateCollection',
           'PlateMember',
           'RackCollection',
           'RackMember',
           'RackPositionMember',
           'RackPositionSetCollection',
           'RackPositionSetMember',
           'RackShapeCollection',
           'RackShapeMember',
           'TubeRackCollection',
           'TubeRackMember',
           ]


class RackMember(Member):
    relation = "%s/rack" % RELATION_BASE_URL
    label = terminal_attribute(str, 'label')
    barcode = terminal_attribute(str, 'barcode')
    comment = terminal_attribute(str, 'comment')
    creation_date = terminal_attribute(datetime, 'creation_date')
    status = member_attribute(IItemStatus, 'status')
    location = member_attribute(ILocation, 'location')
    total_containers = terminal_attribute(int, 'total_containers')
    specs = member_attribute(IRackSpecs, 'specs')

    @property
    def title(self):
        entity = self.get_entity()
        return '%s - %s' % (entity.barcode, entity.label or 'NO LABEL')

    @property
    def type(self):
        return self.get_entity().rack_type


class TubeRackMember(RackMember):
    relation = "%s/tube-rack" % RELATION_BASE_URL
    containers = collection_attribute(ITube, 'containers', backref='rack')

    def __getitem__(self, name):
        if name == 'tubes':
            result = self.containers
        elif name == 'shape':
            result = self.specs.shape
        else:
            result = RackMember.__getitem__(self, name)
        return result


class PlateMember(RackMember):
    relation = "%s/plate" % RELATION_BASE_URL
    containers = collection_attribute(IWell, 'containers', backref='rack')

    def __getitem__(self, name):
        if name == 'wells':
            result = self.containers
        else:
            result = RackMember.__getitem__(self, name)
        return result


class RackCollection(Collection):
    title = 'Racks'
    root_name = 'racks'
    description = 'Manage tube racks and plates'
    default_order = DescendingOrderSpecification('creation_date')


# FIXME: This awaits better handling of polymorphic collections
class PlateCollection(RackCollection):
    # "Pure" plate collections.
    title = 'Plates'
    root_name = 'plates'


class TubeRackCollection(RackCollection):
    # "Pure" tube rack collections.
    title = 'Tuberacks'
    root_name = 'tube-racks'


class RackShapeMember(Member):
    relation = "%s/rack-shape" % RELATION_BASE_URL
    id = terminal_attribute(str, 'id') # rack shape IDs are *strings*.
    name = terminal_attribute(str, 'name')
    label = terminal_attribute(str, 'label')
    number_rows = terminal_attribute(int, 'number_rows')
    number_columns = terminal_attribute(int, 'number_columns')
    title = attribute_alias('label')


class RackShapeCollection(Collection):
    title = 'Rack Shapes'
    root_name = 'rack-shapes'
    description = 'Rack shapes'


class RackPositionMember(Member):
    relation = "%s/rack-position" % RELATION_BASE_URL
    label = terminal_attribute(str, 'label')
    row_index = terminal_attribute(int, 'row_index')
    column_index = terminal_attribute(int, 'column_index')
    title = attribute_alias('label')


class RackPositionSetMember(Member):
    relation = "%s/rack-position-set" % RELATION_BASE_URL
    rack_positions = \
        collection_attribute(IRackPosition, 'positions',
                             cardinality=CARDINALITIES.MANYTOMANY)


class RackPositionSetCollection(Collection):
    title = 'Rack Position Sets'
    root_name = 'rack-position-sets'
    description = 'Rack position Sets.'
