"""
Chemical structure resource.
"""
from everest.resources.base import Member
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.interfaces import IMoleculeDesign
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import IOrganization
from thelma.resources.base import RELATION_BASE_URL

__docformat__ = 'reStructuredText en'
__all__ = ['PooledSupplierMoleculeDesignMember',
           'SingleSupplierMoleculeDesignMember',
           'SupplierMoleculeDesignMember',
           ]


class SupplierMoleculeDesignMember(Member):
    relation = "%s/supplier-moleculedesign" % RELATION_BASE_URL
    product_id = terminal_attribute(str, 'product_id')
    supplier = member_attribute(IOrganization, 'supplier')
    is_current = terminal_attribute(bool, 'is_current')


class SingleSupplierMoleculeDesignMember(SupplierMoleculeDesignMember):
    relation = "%s/single-supplier-moleculedesign" % RELATION_BASE_URL
    molecule_design = member_attribute(IMoleculeDesign, 'molecule_design')


class PooledSupplierMoleculeDesignMember(SupplierMoleculeDesignMember):
    relation = "%s/pooled-supplier-moleculedesign" % RELATION_BASE_URL
    molecule_design_pool = member_attribute(IMoleculeDesignPool,
                                            'molecule_design_pool')
