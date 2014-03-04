"""
Tissue resource.
"""

from everest.querying.specifications import AscendingOrderSpecification
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import terminal_attribute
from thelma.resources.base import RELATION_BASE_URL


__docformat__ = 'reStructuredText en'

__all__ = ['TissueCollection',
           'TissueMember',
           ]


class TissueMember(Member):
    relation = "%s/species" % RELATION_BASE_URL
    title = attribute_alias('label')
    label = terminal_attribute(str, 'label')

class TissueCollection(Collection):
    title = 'Tissue'
    root_name = 'tissue'
    description = 'Manage tissue'
    default_order = AscendingOrderSpecification('label')
