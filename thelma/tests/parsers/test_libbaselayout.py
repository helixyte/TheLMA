"""
Tests the library base layout parser and handler.

AAB
"""
from thelma.automation.handlers.libbaselayout \
    import LibraryBaseLayoutParserHandler
from thelma.automation.parsers.libbaselayout import LibraryBaseLayoutParser
from thelma.automation.semiconstants import get_384_rack_shape
from thelma.automation.semiconstants import get_rack_position_from_indices
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.tests.tools.tooltestingutils import ParsingTestCase


class LibraryBaseLayoutInputTestCase(ParsingTestCase):

    def set_up(self):
        ParsingTestCase.set_up(self)
        self.TEST_FILE_PATH = 'thelma:tests/parsers/libbaselayout/'
        self.VALID_FILE = 'valid_file.xls'

    def _get_expected_rack_shape(self):
        return get_384_rack_shape()

    def _get_expected_positions(self):
        labels = ['B2', 'B3', 'B4', 'B5', 'C2', 'C5', 'D2', 'D3', 'D4', 'D5']
        rack_positions = []
        for label in labels:
            rack_pos = get_rack_position_from_label(label)
            rack_positions.append(rack_pos)
        return rack_positions


class LibraryBaseLayoutParserTestCase(LibraryBaseLayoutInputTestCase):

    def _create_tool(self):
        self.tool = LibraryBaseLayoutParser(stream=self.stream, log=self.log)

    def _test_invalid_file(self, file_name, msg):
        self._continue_setup(file_name)
        self.tool.parse()
        self.assert_true(self.tool.has_errors())
        self._check_error_messages(msg)

    def test_result(self):
        self._continue_setup()
        self.tool.parse()
        self.assert_false(self.tool.has_errors())
        tool_shape = self.tool.shape
        exp_shape = self._get_expected_rack_shape()
        self.assert_equal(tool_shape.row_number, exp_shape.number_rows)
        self.assert_equal(tool_shape.column_number, exp_shape.number_columns)
        exp_positions = self._get_expected_positions()
        found_positions = []
        for rack_pos_container in self.tool.contained_wells:
            rack_pos = get_rack_position_from_indices(
                rack_pos_container.row_index, rack_pos_container.column_index)
            found_positions.append(rack_pos)
        self._compare_pos_sets(exp_positions, found_positions)

    def test_missing_sheet(self):
        self._test_invalid_file('missing_sheet.xls',
                                'There is no sheet called "Base Layout"')

    def test_mislocated_layout(self):
        self._test_invalid_file('misslocated.xls',
                                'Error when trying to locate the layout')

    def test_invalid_rack_shape(self):
        self._test_invalid_file('invalid_shape.xls',
                                'Invalid layout block shape (16x23)')


class LibraryBaseLayoutParserHandlerTestCase(LibraryBaseLayoutInputTestCase):

    def _create_tool(self):
        self.tool = LibraryBaseLayoutParserHandler(log=self.log,
                                                   stream=self.stream)

    def test_result(self):
        self._continue_setup()
        bl = self.tool.get_result()
        self.assert_is_not_none(bl)
        self.assert_equal(bl.shape, self._get_expected_rack_shape())
        exp_positions = self._get_expected_positions()
        self._compare_pos_sets(bl.get_positions(), exp_positions)
        self.assert_equal(len(bl.get_tags()), 1)

    def test_empty(self):
        self._test_invalid_file('empty.xls',
                                'The specified base layout is empty!')
