from thelma.entities.utils import label_from_number
from thelma.entities.utils import number_from_label


class TestLabelFromNumber(object):

    def test_basic(self):
        assert 'AG' == label_from_number(33)


class TestNumberFromLabel(object):

    def test_basic(self):
        assert number_from_label('ag') == 33
