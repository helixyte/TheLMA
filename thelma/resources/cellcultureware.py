"""
Cell culture ware resource.
"""

from everest.querying.specifications import AscendingOrderSpecification
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.interfaces import IOrganization
from thelma.resources.base import RELATION_BASE_URL


__docformat__ = 'reStructuredText en'

__all__ = ['CellCultureWareCollection',
           'CellCultureWareMember',
           ]


class CellCultureWareMember(Member):
    relation = "%s/cell_culture_ware" % RELATION_BASE_URL
    title = attribute_alias('label')
    label = terminal_attribute(str, 'label')
    supplier = member_attribute(IOrganization, 'supplier_id')
    size = terminal_attribute(float, 'size')
    coating = terminal_attribute(str, 'coating')

class CellCultureWareCollection(Collection):
    title = 'CellCultureWares'
    root_name = 'cell_culture_wares'
    description = 'Manage cell culture wares'
    default_order = AscendingOrderSpecification('label')
