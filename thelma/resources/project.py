"""
Project resource.

TR
"""
from datetime import datetime
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from everest.querying.specifications import AscendingOrderSpecification
from thelma.interfaces import IOrganization
from thelma.interfaces import ISubproject
from thelma.interfaces import IUser
from thelma.resources.base import RELATION_BASE_URL

__docformat__ = 'reStructuredText en'


__all__ = ['ProjectCollection',
           'ProjectMember',
           ]


class ProjectMember(Member):
    relation = "%s/project" % RELATION_BASE_URL
    title = attribute_alias('label')
    label = terminal_attribute(str, 'label')
    creation_date = terminal_attribute(datetime, 'creation_date')
    leader = member_attribute(IUser, 'leader')
    customer = member_attribute(IOrganization, 'customer')
    subprojects = collection_attribute(ISubproject, 'subprojects')


class ProjectCollection(Collection):
    title = 'Projects'
    root_name = 'projects'
    description = 'Manage Projects'
    default_order = AscendingOrderSpecification('label')
