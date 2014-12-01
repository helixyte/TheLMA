"""
Device resource.
"""
from everest.querying.specifications import AscendingOrderSpecification
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.interfaces import IDeviceType
from thelma.interfaces import IOrganization
from thelma.resources.base import RELATION_BASE_URL

__docformat__ = 'reStructuredText en'
__all__ = ['DeviceCollection',
           'DeviceMember',
           ]


class DeviceMember(Member):
    relation = "%s/device" % RELATION_BASE_URL
    title = attribute_alias('label')
    name = terminal_attribute(str, 'name')
    label = terminal_attribute(str, 'label')
    model = terminal_attribute(str, 'model')
    type = member_attribute(IDeviceType, 'type')
    manufacturer = member_attribute(IOrganization, 'manufacturer')

    def update(self, member):
        super(DeviceMember, self).update(member)
        # FIXME: this looks hacky. pylint: disable=W0511
        self.get_entity().name = member.get_entity().name
        self.label = member.label
        self.model = member.model
        self.type = member.type
        self.manufacturer = member.manufacturer


class DeviceCollection(Collection):
    title = 'Devices'
    root_name = 'devices'
    description = 'Manage devices'
    default_order = AscendingOrderSpecification('type.label') \
                    & AscendingOrderSpecification('label')
