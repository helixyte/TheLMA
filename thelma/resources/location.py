"""
Location resource.

NP
"""

from everest.querying.specifications import AscendingOrderSpecification
from everest.representers.dataelements import DataElementAttributeProxy
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.interfaces import IDevice
from thelma.interfaces import IRack
from thelma.resources.base import RELATION_BASE_URL

__docformat__ = 'reStructuredText en'

__all__ = ['LocationCollection',
           'LocationMember']


class LocationMember(Member):
    relation = "%s/location" % RELATION_BASE_URL

    @property
    def title(self):
        entity = self.get_entity()
        return '%s: %s' % (entity.type, entity.label)

    name = terminal_attribute(str, 'name')
    label = terminal_attribute(str, 'label')
    barcode = terminal_attribute(str, 'barcode')
    type = terminal_attribute(str, 'type')
    device = member_attribute(IDevice, 'device')
    index = terminal_attribute(int, 'index')
    rack = member_attribute(IRack, 'rack')
    empty = terminal_attribute(bool, 'empty')

    def update_from_data(self, data_element):
        prx = DataElementAttributeProxy(data_element)
        loc = self.get_entity()
        if prx.rack is None:
            loc.checkout_rack()
        else:
            loc.checkin_rack(prx.rack.get_entity())


class LocationCollection(Collection):
    title = 'Locations'
    root_name = 'locations'
    description = 'Manage locations where racks are held'
    default_order = AscendingOrderSpecification('type') \
                    & AscendingOrderSpecification('label')