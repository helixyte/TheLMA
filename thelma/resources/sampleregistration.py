"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Sample registration resources.

Created sNov 24, 2014
"""
from everest.resources.base import Member
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.interfaces import IChemicalStructure
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import IMoleculeDesignPoolRegistrationItem
from thelma.interfaces import IMoleculeDesignRegistrationItem
from thelma.interfaces import IMoleculeType
from thelma.interfaces import IOrganization
from thelma.interfaces import IRackPosition
from thelma.resources.base import RELATION_BASE_URL


__docformat__ = 'reStructuredText en'
__all__ = ['MoleculeDesignPoolRegistrationItemMember',
           'MoleculeDesignRegistrationItemMember',
           'SampleRegistrationItemMember',
           'SupplierSampleRegistrationItemMember',
           ]


class MoleculeDesignRegistrationItemMember(Member):
    relation = "%s/molecule-design-registration-item" % RELATION_BASE_URL
    molecule_type = member_attribute(IMoleculeType, 'molecule_type')
    chemical_structures = collection_attribute(IChemicalStructure,
                                               'chemical_structures')


class MoleculeDesignPoolRegistrationItemMember(Member):
    relation = "%s/molecule-design-pool-registration-item" % RELATION_BASE_URL
    molecule_type = member_attribute(IMoleculeType, 'molecule_type')
    molecule_design_registration_items = \
                collection_attribute(IMoleculeDesignRegistrationItem,
                                     'molecule_design_registration_items')


class SampleRegistrationItemMember(Member):
    relation = "%s/sample-registration-item" % RELATION_BASE_URL
    supplier = member_attribute(IOrganization, 'supplier')
    concentration = terminal_attribute(float, 'concentration')
    volume = terminal_attribute(float, 'volume')
    tube_barcode = terminal_attribute(str, 'tube_barcode')
    rack_barcode = terminal_attribute(str, 'rack_barcode')
    rack_position = member_attribute(IRackPosition, 'rack_position')
    molecule_design_pool = member_attribute(IMoleculeDesignPool,
                                            'molecule_design_pool')


class SupplierSampleRegistrationItemMember(SampleRegistrationItemMember):
    relation = "%s/supplier-sample-registration-item" % RELATION_BASE_URL
    supplier = member_attribute(IOrganization, 'supplier')
    product_id = terminal_attribute(str, 'product_id')
    concentration = terminal_attribute(float, 'concentration')
    volume = terminal_attribute(float, 'volume')
    tube_barcode = terminal_attribute(str, 'tube_barcode')
    rack_barcode = terminal_attribute(str, 'rack_barcode')
    rack_position = member_attribute(IRackPosition, 'rack_position')
    molecule_type = member_attribute(IMoleculeType, 'molecule_type')
    molecule_design_pool_registration_item = \
            member_attribute(IMoleculeDesignPoolRegistrationItem,
                             'molecule_design_pool_registration_item')
