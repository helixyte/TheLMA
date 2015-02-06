"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Molecule type resource.
"""
from everest.querying.specifications import AscendingOrderSpecification
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.interfaces import IChemicalStructure
from thelma.resources.base import RELATION_BASE_URL


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
