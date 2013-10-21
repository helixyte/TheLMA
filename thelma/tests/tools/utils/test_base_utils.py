"""
tool base utils testing

AAB Aug 12, 2011
"""

from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.utils.base import add_list_map_element
from thelma.automation.utils.base import are_equal_values
from thelma.automation.utils.base import create_in_term_for_db_queries
from thelma.automation.utils.base import get_converted_number
from thelma.automation.utils.base import get_nested_dict
from thelma.automation.utils.base import get_trimmed_string
from thelma.automation.utils.base import is_larger_than
from thelma.automation.utils.base import is_smaller_than
from thelma.automation.utils.base import is_valid_number
from thelma.automation.utils.base import round_up
from thelma.automation.utils.base import sort_rack_positions
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase


class ToolUtilsFunctionsTestCase(ToolsAndUtilsTestCase):

    def test_are_equal_values(self):
        a = 1.00001
        b = 1.00002
        c = 1.002
        self.assert_true(are_equal_values(a, b))
        self.assert_false(are_equal_values(a, c))

    def test_is_smaller_than(self):
        a = 1.00001
        b = 1.00002
        c = 1.002
        self.assert_false(is_smaller_than(a, b))
        self.assert_true(is_smaller_than(a, c))
        self.assert_false(is_smaller_than(a, a))

    def test_is_larger_than(self):
        a = 1.00001
        b = 1.00002
        c = 1.002
        self.assert_false(is_larger_than(b, a))
        self.assert_true(is_larger_than(c, a))
        self.assert_false(is_larger_than(a, a))

    def test_rack_position_sorting(self):
        a1_pos = get_rack_position_from_label('A1')
        a2_pos = get_rack_position_from_label('A2')
        a10_pos = get_rack_position_from_label('A10')
        a12_pos = get_rack_position_from_label('A12')
        b1_pos = get_rack_position_from_label('B1')
        test_list = [b1_pos, a10_pos, a2_pos, a12_pos, a1_pos]
        sorted_list = sort_rack_positions(test_list)
        self.assert_equal(len(sorted_list), len(test_list))
        self.assert_equal(sorted_list[0], a1_pos)
        self.assert_equal(sorted_list[1], a2_pos)
        self.assert_equal(sorted_list[2], a10_pos)
        self.assert_equal(sorted_list[3], a12_pos)
        self.assert_equal(sorted_list[4], b1_pos)

    def test_is_valid_number(self):
        self.assert_true(is_valid_number('4'))
        self.assert_true(is_valid_number('4.0'))
        self.assert_true(is_valid_number(4))
        self.assert_true(is_valid_number(4.2))
        self.assert_false(is_valid_number('0'))
        self.assert_false(is_valid_number(-4))
        self.assert_false(is_valid_number('-4'))
        self.assert_true(is_valid_number(-4, positive=False))
        self.assert_true(is_valid_number('-4', positive=False))
        self.assert_true(is_valid_number('0', may_be_zero=True))
        self.assert_true(is_valid_number('4', may_be_zero=True))
        self.assert_true(is_valid_number('-4', may_be_zero=True,
                                         positive=False))
        self.assert_true(is_valid_number('4', is_integer=True))
        self.assert_true(is_valid_number('4.0', is_integer=True))
        self.assert_false(is_valid_number('4.2', is_integer=True))
        self.assert_false(is_valid_number(4.2, is_integer=True))

    def test_get_converted_number(self):
        self.assert_equal(get_converted_number('4'), 4.0)
        self.assert_equal(get_converted_number('4.2'), 4.2)
        self.assert_equal(get_converted_number('4', is_integer=True), 4)
        self.assert_equal(get_converted_number('4.2', is_integer=True), '4.2')
        self.assert_equal(get_converted_number(4), 4)
        self.assert_equal(get_converted_number(4.2), 4.2)
        self.assert_equal(get_converted_number('test'), 'test')

    def test_get_trimmed_string(self):
        self.assert_equal(get_trimmed_string(4), '4')
        self.assert_equal(get_trimmed_string(4.0), '4')
        self.assert_equal(get_trimmed_string('test:value'), 'test:value')

    def test_round_up(self):
        self.assert_equal(round_up(1.344), 1.4)
        self.assert_equal(round_up(1.1), 1.1)
        self.assert_equal(round_up(1.344, decimal_places=2), 1.35)
        self.assert_equal(round_up(84.1, 0), 85)

    def test_create_in_term_for_db_queries(self):
        values = [3, 4]
        self.assert_equal(create_in_term_for_db_queries(values), '(3, 4)')
        self.assert_equal(create_in_term_for_db_queries(values, as_string=True),
                          '(\'3\', \'4\')')

    def test_add_list_map_element(self):
        value_map = dict()
        self.assert_equal(len(value_map), 0)
        add_list_map_element(value_map, 1, 'string1')
        self.assert_equal(len(value_map), 1)
        self.assert_equal(value_map[1], ['string1'])
        add_list_map_element(value_map, 1, 'string2')
        self.assert_equal(len(value_map), 1)
        self.assert_equal(value_map[1], ['string1', 'string2'])

    def test_get_nested_dict(self):
        parent_dict = dict()
        key1 = 1
        key2 = 2
        dict1 = {'example' : 'dict'}
        parent_dict[key1] = dict1
        self.assert_false(parent_dict.has_key(key2))
        self.assert_equal(get_nested_dict(parent_dict, key1), dict1)
        self.assert_equal(get_nested_dict(parent_dict, key2), {})
        self.assert_true(parent_dict.has_key(key2))

