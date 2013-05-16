"""
thelma.models.utils unit tests.

NP
"""

from everest.testing import Pep8CompliantTestCase
from thelma.models.utils import label_from_number
from thelma.models.utils import number_from_label

__docformat__ = 'reStructuredText en'

__author__ = 'Nikos Papagrigoriou'
__date__ = '$Date: 2011-11-10 12:55:22 +0100 (Thu, 10 Nov 2011) $'
__revision__ = '$Rev: 12254 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/tests/models/test_u#$'

__all__ = ['LabelFromNumberTestCase',
           'NumberFromLabelTestCase']


class LabelFromNumberTestCase(Pep8CompliantTestCase):

    def test_basic(self):
        self.assert_equals('AG', label_from_number(33))


class NumberFromLabelTestCase(Pep8CompliantTestCase):

    def test_basic(self):
        self.assert_equals(33, number_from_label('ag'))
