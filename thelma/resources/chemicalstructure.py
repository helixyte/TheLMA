"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Chemical structure resource.
"""
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.interfaces import IChemicalStructureType
from thelma.interfaces import IMoleculeDesign
from thelma.interfaces import IMoleculeType
from thelma.resources.base import RELATION_BASE_URL


__docformat__ = 'reStructuredText en'
__all__ = ['ChemicalStructureMember',
           'ChemicalStructureTypeMember',
           ]


class ChemicalStructureTypeMember(Member):
    relation = "%s/chemical-structure-type" % RELATION_BASE_URL
    name = terminal_attribute(str, 'name')
    label = terminal_attribute(str, 'label')
    molecule_types = collection_attribute(IMoleculeType, 'molecule_types')
    title = attribute_alias('label')


class ChemicalStructureMember(Member):
    relation = "%s/chemical-structure" % RELATION_BASE_URL
    molecule_designs = collection_attribute(IMoleculeDesign,
                                            'molecule_designs')
    structure_type = member_attribute(IChemicalStructureType,
                                      'structure_type')
    representation = terminal_attribute(str, 'representation')
    structure_type_id = terminal_attribute(str, 'structure_type_id')
    title = attribute_alias('representation')
