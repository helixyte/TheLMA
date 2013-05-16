"""
Item status resource.

NP
"""

from everest.querying.specifications import DescendingOrderSpecification
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import terminal_attribute
from thelma.resources.base import RELATION_BASE_URL


__docformat__ = 'reStructuredText en'

__all__ = ['ItemStatusCollection',
           'ItemStatusMember']

class ItemStatusMember(Member):
    id = terminal_attribute(str, 'id') # IDs are strings for item status
    relation = "%s/item-status" % RELATION_BASE_URL
    title = attribute_alias('name')
    name = terminal_attribute(str, 'name')
    description = terminal_attribute(str, 'description')


class ItemStatusCollection(Collection):
    """
    """
    title = 'Item Statuses'
    root_name = 'item-statuses'
    description = 'Manage item statuses'
    default_order = DescendingOrderSpecification('name')
