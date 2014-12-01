"""
Subproject resource.
"""
from datetime import datetime

from everest.querying.specifications import AscendingOrderSpecification
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.interfaces import IProject
from thelma.resources.base import RELATION_BASE_URL


__docformat__ = 'reStructuredText en'
__all__ = ['SubprojectCollection',
           'SubprojectMember',
           ]


class SubprojectMember(Member):
    relation = "%s/subproject" % RELATION_BASE_URL
    label = terminal_attribute(str, 'label')
    project = member_attribute(IProject, 'project')
    creation_date = terminal_attribute(datetime, 'creation_date')
    active = terminal_attribute(bool, 'active')

    @property
    def title(self):
        # The title is formed from the project's and the subproject's label
        # and does not need to be persisted or exposed.
        return self.get_entity().title

    def update(self, member):
        super(SubprojectMember, self).update(member)
        self.label = member.label
        self.active = member.active


class SubprojectCollection(Collection):
    title = 'Sub Projects'
    root_name = 'subprojects'
    description = 'Manage subprojects'
    default_order = AscendingOrderSpecification('project.label') \
                    & AscendingOrderSpecification('label')

