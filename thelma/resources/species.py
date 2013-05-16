"""
Species resource.

NP
"""

from everest.querying.specifications import AscendingOrderSpecification
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import terminal_attribute
from thelma.resources.base import RELATION_BASE_URL


__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2013-02-12 09:16:49 +0100 (Tue, 12 Feb 2013) $'
__revision__ = '$Rev: 13137 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/resources/species.p#$'

__all__ = ['SpeciesCollection',
           'SpeciesMember',
           ]


class SpeciesMember(Member):
    relation = "%s/species" % RELATION_BASE_URL
    title = attribute_alias('common_name')
    genus_name = terminal_attribute(str, 'genus_name')
    species_name = terminal_attribute(str, 'species_name')
    common_name = terminal_attribute(str, 'common_name')
    acronym = terminal_attribute(str, 'acronym')
    ncbi_tax_id = terminal_attribute(int, 'ncbi_tax_id')

class SpeciesCollection(Collection):
    title = 'Species'
    root_name = 'species'
    description = 'Manage species'
    default_order = AscendingOrderSpecification('genus_name') \
                    & AscendingOrderSpecification('species_name')
