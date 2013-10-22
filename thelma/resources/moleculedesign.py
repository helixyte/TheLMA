"""
Molecule design resource.

NP
"""

from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.interfaces import IChemicalStructure
from thelma.interfaces import IGene
from thelma.interfaces import IMoleculeDesign
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import IMoleculeType
from thelma.interfaces import ISupplierMoleculeDesign
from thelma.resources.base import RELATION_BASE_URL
from everest.entities.interfaces import IEntity
from everest.constants import CARDINALITIES

__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2013-02-27 14:59:00 +0100 (Wed, 27 Feb 2013) $'
__revision__ = '$Rev: 13189 $'
__source__ = '$URL: http://svn/cenix/TheLMA/trunk/thelma/resources/moleculedesign.py $'

__all__ = ['MoleculeDesignCollection',
           'MoleculeDesignMember',
           'MoleculeDesignPoolMember',
           'MoleculeDesignPoolSetMember',
           'MoleculeDesignSetCollection',
           'MoleculeDesignSetMember',
           ]


class MoleculeDesignMember(Member):
    relation = "%s/molecule-design" % RELATION_BASE_URL

    @property
    def title(self):
        return str(self.id)

    molecule_type = member_attribute(IMoleculeType, 'molecule_type')
    chemical_structures = collection_attribute(IChemicalStructure,
                                               'chemical_structures')
    genes = collection_attribute(IGene, 'genes',
                                 cardinality=CARDINALITIES.MANYTOMANY)
    supplier_molecule_designs = \
            collection_attribute(ISupplierMoleculeDesign,
                                 'supplier_molecule_designs')


class MoleculeDesignCollection(Collection):
    title = 'Molecule Designs'
    root_name = 'molecule-designs'
    description = 'Manage molecule designs'


class MoleculeDesignSetMember(Member):
    """
    """
    relation = "%s/molecule-design-set" % RELATION_BASE_URL

    @property
    def title(self):
        return str(self.id)

    molecule_designs = collection_attribute(IMoleculeDesign,
                                            'molecule_designs')
    set_type = terminal_attribute(str, 'set_type')

    def update(self, data):
        if IEntity.providedBy(data): # pylint: disable=E1101
            self.get_entity().molecule_designs = data.molecule_designs
        else:
            Member.update(self, data)


class MoleculeDesignPoolMember(MoleculeDesignSetMember):
    """
    """
    relation = "%s/molecule-design-pool" % RELATION_BASE_URL

    molecule_type = member_attribute(IMoleculeType, 'molecule_type')
#    stock_samples = collection_attribute(IStockSample, 'stock_samples')
#    member_hash = terminal_attribute(str, 'member_hash')
    number_designs = terminal_attribute(int, 'number_designs')
    genes = collection_attribute(IGene, 'genes')
    supplier_molecule_designs = \
            collection_attribute(ISupplierMoleculeDesign,
                                 'supplier_molecule_designs')


class MoleculeDesignSetCollection(Collection):
    title = 'Molecule Design Sets'
    root_name = 'molecule-design-sets'
    description = 'Manage molecule design sets'


class MoleculeDesignPoolSetMember(Member):
    """
    """
    relation = "%s/molecule-design-pool-set" % RELATION_BASE_URL

    molecule_type = member_attribute(IMoleculeType, 'molecule_type')
    molecule_design_pools = collection_attribute(IMoleculeDesignPool,
                                                 'molecule_design_pools')

