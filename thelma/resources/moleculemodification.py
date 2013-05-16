"""
Molecule modification resource.

NP
"""

from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import terminal_attribute
from thelma.resources.base import RELATION_BASE_URL
from everest.querying.specifications import AscendingOrderSpecification
from everest.resources.descriptors import attribute_alias


__docformat__ = 'reStructuredText en'

__author__ = 'Tobias Rothe'
__date__ = '$Date: 2013-02-12 09:16:49 +0100 (Tue, 12 Feb 2013) $'
__revision__ = '$Rev: 13137 $'
__source__ = '$URL: http://svn/cenix/TheLMA/trunk/thelma/resources/moleculemodification.py $'

__all__ = ['MoleculeModificationCollection',
           'MoleculeModificationMember',
           ]


class MoleculeModificationMember(Member):
    relation = "%s/molecule-modification" % RELATION_BASE_URL
    title = attribute_alias('name')
    name = terminal_attribute(str, 'name')


class MoleculeModificationCollection(Collection):
    title = 'Molecule Modifications'
    root_name = 'molecule-modifications'
    description = 'Manage molecule modifications'
    default_order = AscendingOrderSpecification('name')
