"""
Device type resource.

NP
"""

from everest.querying.specifications import AscendingOrderSpecification
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.interfaces import IDevice
from thelma.resources.base import RELATION_BASE_URL

__docformat__ = 'reStructuredText en'
__all__ = ['DeviceTypeCollection',
           'DeviceTypeMember',
           ]


class DeviceTypeMember(Member):
    relation = "%s/device-type" % RELATION_BASE_URL
    title = attribute_alias('label')
    name = terminal_attribute(str, 'name')
    label = terminal_attribute(str, 'label')
    devices = collection_attribute(IDevice, 'devices', backref='type')

    def update(self, member):
        super(DeviceTypeMember, self).update(member)
        self.get_entity().name = member.get_entity().name
        self.label = member.label


class DeviceTypeCollection(Collection):
    title = 'Device Types'
    root_name = 'device-types'
    description = 'Manage device types'
    default_order = AscendingOrderSpecification('label')
