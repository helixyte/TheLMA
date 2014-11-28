"""
Organization resource.

NP
"""

from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import terminal_attribute
from everest.querying.specifications import AscendingOrderSpecification
from thelma.resources.base import RELATION_BASE_URL


__docformat__ = 'reStructuredText en'


__all__ = ['OrganizationCollection',
           'OrganizationMember',
           ]


class OrganizationMember(Member):
    """
    """
    relation = "%s/organization" % RELATION_BASE_URL
    title = attribute_alias('name')
    name = terminal_attribute(str, 'name')


class OrganizationCollection(Collection):
    title = 'Organizations'
    root_name = 'organizations'
    description = 'Manage Organizations'
    default_order = AscendingOrderSpecification('name')
