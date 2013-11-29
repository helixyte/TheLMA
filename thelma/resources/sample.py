"""
Sample resource.

FOG, Jul 04, 2011
"""

from datetime import datetime
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.interfaces import IContainer
from thelma.interfaces import IMoleculeDesign
from thelma.interfaces import IOrganization
from thelma.interfaces import ISample
from thelma.interfaces import ISampleMolecule
from thelma.resources.base import RELATION_BASE_URL
from thelma.interfaces import IMoleculeType
from thelma.interfaces import ISupplierMoleculeDesign
#from thelma.interfaces import IMoleculeDesignPool

__docformat__ = 'reStructuredText en'

__author__ = 'F Oliver Gathmann'
__date__ = '$Date: 2013-02-12 09:16:49 +0100 (Tue, 12 Feb 2013) $'
__revision__ = '$Rev: 13137 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/resources/sample.py $'

__all__ = ['MoleculeCollection',
           'MoleculeMember',
           'SampleMember',
           'SampleMoleculeCollection',
           'SampleMoleculeMember',
           'StockSampleMember',
           ]


class SampleMoleculeMember(Member):
    relation = "%s/samplemolecule" % RELATION_BASE_URL
    concentration = terminal_attribute(float, 'concentration')
    freeze_thaw_cycles = terminal_attribute(int, 'freeze_thaw_cycles')
    insert_date = terminal_attribute(datetime, 'molecule.insert_date')
    molecule_design_id = terminal_attribute(int, 'molecule.molecule_design.id')
    checkout_date = terminal_attribute(datetime, 'checkout_date')
    product_id = terminal_attribute(str, 'molecule.product_id')
    supplier_molecule_design = \
            member_attribute(ISupplierMoleculeDesign,
                             'molecule.supplier_molecule_design')
    supplier = member_attribute(IOrganization, 'molecule.supplier')


class SampleMoleculeCollection(Collection):
    title = 'Sample Molecules'
    root_name = 'sample-molecules'
    description = 'Manage sample molecules'


class SampleMember(Member):
    relation = "%s/sample" % RELATION_BASE_URL
    volume = terminal_attribute(float, 'volume')
    container = member_attribute(IContainer, 'container')
    sample_molecules = collection_attribute(ISampleMolecule,
                                            'sample_molecules')
    molecule_design_pool_id = terminal_attribute(int,
                                                 'molecule_design_pool_id')
#    molecule_design_pool = member_attribute(IMoleculeDesignPool,
#                                            'molecule_design_pool')


class StockSampleMember(SampleMember):
    relation = "%s/stocksample" % RELATION_BASE_URL
    supplier = member_attribute(IOrganization, 'supplier')
    molecule_type = member_attribute(IMoleculeType, 'molecule_type')
    concentration = terminal_attribute(float, 'concentration')
    product_id = terminal_attribute(str, 'product_id')


class MoleculeMember(Member):
    relation = "%s/molecule" % RELATION_BASE_URL
    molecule_design = member_attribute(IMoleculeDesign, 'molecule_design')
    molecule_design_id = terminal_attribute(int, 'molecule_design.id')
    supplier = member_attribute(IOrganization, 'supplier')
    product_id = terminal_attribute(str,
                                    'supplier_molecule_design.product_id')
    insert_date = terminal_attribute(datetime, 'insert_date')
    samples = collection_attribute(ISample, 'samples')


class MoleculeCollection(Collection):
    title = 'Molecules'
    root_name = 'molecules'
    description = 'Manage molecules'
