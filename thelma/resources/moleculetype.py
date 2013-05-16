"""
Molecule type resource.

NP
"""

from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import terminal_attribute
from everest.querying.specifications import AscendingOrderSpecification
from thelma.resources.base import RELATION_BASE_URL
from everest.resources.descriptors import collection_attribute
from thelma.interfaces import IChemicalStructure


__docformat__ = 'reStructuredText en'

__all__ = ['MoleculeTypeCollection',
           'MoleculeTypeMember',
           ]


class MoleculeTypeMember(Member):
    relation = "%s/molecule-type" % RELATION_BASE_URL
    title = attribute_alias('name')
    name = terminal_attribute(str, 'name')
    description = terminal_attribute(str, 'description')
    thaw_time = terminal_attribute(float, 'thaw_time')
    modifications = collection_attribute(IChemicalStructure ,
                                         'modifications')


class MoleculeTypeCollection(Collection):
    title = 'Molecule Types'
    root_name = 'molecule-types'
    description = 'Manage molecule types'
    default_order = AscendingOrderSpecification('name')
