"""
Tube transfer related resources

AAB
"""
from everest.resources.base import Member
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from thelma.interfaces import IRack
from thelma.interfaces import IRackPosition
from thelma.interfaces import ITube
from thelma.interfaces import ITubeTransfer
from thelma.interfaces import IUser
from thelma.resources.base import RELATION_BASE_URL


__docformat__ = 'reStructuredText en'

__all__ = ['TubeTransferMember',
           'TubeTransferWorklistMember',
           ]

class TubeTransferMember(Member):

    relation = '%s/tube-transfers' % RELATION_BASE_URL

    tube = member_attribute(ITube, 'tube')
    source_rack = member_attribute(IRack, 'source_rack')
    source_position = member_attribute(IRackPosition, 'source_position')
    target_rack = member_attribute(IRack, 'target_rack')
    target_position = member_attribute(IRackPosition, 'target_position')

    @property
    def title(self):
        entity = self.get_entity()
        return str(entity.id)


class TubeTransferWorklistMember(Member):

    relation = '%s/tube-transfer-worklists' % RELATION_BASE_URL

    user = member_attribute(IUser, 'user')
    tube_transfers = collection_attribute(ITubeTransfer, 'tube_transfers')

    @property
    def title(self):
        entity = self.get_entity()
        return str(entity.id)
