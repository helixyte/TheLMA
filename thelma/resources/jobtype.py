"""
Job type resource.

AAB, Jun 2011
"""

from everest.querying.specifications import DescendingOrderSpecification
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import terminal_attribute
from thelma.resources.base import RELATION_BASE_URL

__docformat__ = 'reStructuredText en'

__author__ = 'Anna-Antonia Berger'
__date__ = '$Date: 2011-06-16 09:59:40 +0200 (Thu, 16 Jun 2011) $'
__revision__ = '$Rev: 11970 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/resources/jobtype.py   $'

__all__ = ['JobTypeCollection',
           'JobTypeMember',
           ]


class JobTypeMember(Member):
    relation = '%s/job-type' % RELATION_BASE_URL
    title = attribute_alias('label')
    name = terminal_attribute(str, 'name')
    label = terminal_attribute(str, 'label')


class JobTypeCollection(Collection):
    title = 'Job Types'
    root_name = 'job-types'
    description = 'Manage job types'
    default_order = DescendingOrderSpecification('name')
