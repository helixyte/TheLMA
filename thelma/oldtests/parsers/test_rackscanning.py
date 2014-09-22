"""
Tests the rack scanning output file parser und handler.

AAB
"""
from datetime import datetime
from everest.repositories.rdb.testing import check_attributes
from pkg_resources import resource_filename # pylint: disable=E0611,F0401
from thelma.automation.handlers.rackscanning import RackScanningLayout
from thelma.automation.handlers.rackscanning import \
                                            CenixRackScanningParserHandler
from thelma.automation.parsers.rackscanning import RackScanningParser
from thelma.automation.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.oldtests.tools.tooltestingutils import ParsingTestCase
from thelma.oldtests.tools.tooltestingutils import ToolsAndUtilsTestCase
import pytz


class RackScanningTestCase(ParsingTestCase):

    def set_up(self):
        ParsingTestCase.set_up(self)
        self.TEST_FILE_PATH = 'thelma:tests/parsers/rackscanning/'
        self.VALID_FILE = 'valid_file.txt'

    def _get_expected_barcode(self):
        return '02498606'

    def _get_expected_timestamp(self):
        return datetime(2012, 8, 23, 11, 42, 1, tzinfo=pytz.UTC)

    def _get_expected_position_barcodes(self):
        return dict(A01='1034998087', B01='1034998093', B07='1002768019',
                    C01='1016553593', C07='1016185283', D01='1016672497',
                    D07='1016203907', E01='1000327338', E07='1002828346',
                    F01='1002969286', F07='1002830011', G01='1000320824',
                    G07='1002783600', H01='1000320007', H07='1002852796')

    #pylint: disable=W0221
    def _continue_setup(self, file_name=None, as_stream=True): #pylint: disable=W0221
        if file_name is None: file_name = self.VALID_FILE
        self.__read_file(file_name, as_stream)
        self._create_tool()
    #pylint: enable=W0221

    def __read_file(self, file_name, as_stream):
        fn = self.TEST_FILE_PATH + file_name
        f = resource_filename(*fn.split(':'))
        stream = open(f, 'rb')
        if as_stream:
            self.stream = stream
        else:
            self.stream = stream.read()


class RackScanningParserTestCase(RackScanningTestCase):

    def _create_tool(self):
        self.tool = RackScanningParser(self.stream)

    def __test_and_expect_errors(self, file_name, msg):
        self._continue_setup(file_name)
        self.tool.run()
        self.assert_true(self.tool.has_errors())
        self._check_error_messages(msg)

    def __check_result(self):
        self.tool.run()
        self.assert_false(self.tool.has_errors())
        self.assert_equal(self.tool.rack_barcode, self._get_expected_barcode())
        self.assert_equal(self.tool.timestamp, self._get_expected_timestamp())
        expected_barcodes = self._get_expected_position_barcodes()
        tool_barcodes = self.tool.position_map
        self.assert_equal(len(tool_barcodes), 96)
        found_positions = []
        for pos_label, tube_barcode in tool_barcodes.iteritems():
            if not expected_barcodes.has_key(pos_label):
                self.assert_is_none(tube_barcode)
            else:
                self.assert_equal(tube_barcode, expected_barcodes[pos_label])
                found_positions.append(pos_label)
        found_positions.sort()
        exp_positions = expected_barcodes.keys()
        exp_positions.sort()
        self.assert_equal(found_positions, exp_positions)

    def test_result_stream(self):
        self._continue_setup(as_stream=True)
        self.__check_result()

    def test_result_content(self):
        self._continue_setup(as_stream=False)
        self.__check_result()

    def test_invalid_source(self):
        self._continue_setup()
        self.stream = 123
        self._create_tool()
        self.tool.run()
        self.assert_true(self.tool.has_errors())
        self._check_error_messages('Unknown type for stream')

    def test_different_line_breaks(self):
        self._continue_setup()
        self.__check_result()

    def test_invalid_timestamp(self):
        self.__test_and_expect_errors('invalid_timestamp.txt',
                                      'does not match format')

    def test_missing_timestamp(self):
        self.__test_and_expect_errors('missing_timestamp.txt',
                                      'Unable do find time stamp')

    def test_missing_rack_barcode(self):
        self.__test_and_expect_errors('missing_rack_barcode.txt',
                                      'Unable to find rack barcode')

    def test_no_separator(self):
        self.__test_and_expect_errors('no_separator.txt', 'Unexpected content')

    def test_additional_content(self):
        self.__test_and_expect_errors('additional_content.txt',
                                      'Unexpected content')

    def test_duplicate_position_label(self):
        self.__test_and_expect_errors('duplicate_position_label.txt',
                                      'Duplicate position label')


class CenixRackScanningParserHandlerTestCase(RackScanningTestCase):

    def _create_tool(self):
        self.tool = CenixRackScanningParserHandler(self.stream)

    def test_result(self):
        self._continue_setup()
        rsl = self.tool.get_result()
        self.assert_is_not_none(rsl)
        self.assert_equal(rsl.rack_barcode, self._get_expected_barcode())
        self.assert_equal(rsl.timestamp, self._get_expected_timestamp())
        result_data = self._get_expected_position_barcodes()
        self.assert_equal(len(result_data), len(rsl))
        for pos_label, tube_barcode in result_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            self.assert_equal(rsl.get_barcode_for_position(rack_pos),
                              tube_barcode)

    def test_invalid_rack_barcode(self):
        self._continue_setup('invalid_rack_barcode.txt')
        self._test_and_expect_errors('The barcode of the scanned rack ' \
                        '(2498606) does not match the rack barcode pattern')

    def test_invalid_label(self):
        self._continue_setup('invalid_label.txt')
        self._test_and_expect_errors('There are invalid labels in the file')

    def test_duplicate_position(self):
        self._continue_setup('duplicate_position.txt')
        self._test_and_expect_errors('Some position are specified multiple ' \
                                     'times')

    def test_duplicate_barcode(self):
        self._continue_setup('duplicate_barcode.txt')
        self._test_and_expect_errors('Some tubes appear multiple times')

    def test_position_of_range(self):
        self._continue_setup('position_out_of_range.txt')
        self._test_and_expect_errors('Some positions specified in the file ' \
                                     'are out of the range of a 96-well plate')


class RackScanningLayoutTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        # pos label, tube barcode
        self.position_data = dict(A1='1001', B2='1004', C3='1009')
        self.a1_pos = get_rack_position_from_label('A1')
        self.rack_barcode = '0999999'
        self.timestamp = datetime(2012, 8, 23, 12, 42, 1, tzinfo=pytz.UTC)

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.position_data
        del self.a1_pos
        del self.rack_barcode
        del self.timestamp

    def __get_init_data(self):
        return dict(rack_barcode=self.rack_barcode, timestamp=self.timestamp)

    def __create_test_layout(self):
        rsl = RackScanningLayout(**self.__get_init_data())
        for pos_label, tube_barcode in self.position_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            rsl.add_position(rack_pos, tube_barcode)
        return rsl

    def test_init(self):
        kw = self.__get_init_data()
        rsl = RackScanningLayout(**kw)
        self.assert_is_not_none(rsl)
        self.assert_equal(rsl.shape.name, RACK_SHAPE_NAMES.SHAPE_96)
        check_attributes(rsl, kw)

    def test_add_position(self):
        kw = self.__get_init_data()
        rsl = RackScanningLayout(**kw)
        self.assert_equal(len(rsl), 0)
        rsl.add_position(self.a1_pos, '1001')
        self.assert_equal(len(rsl), 1)
        # test errors
        h14_pos = get_rack_position_from_label('H14')
        self.assert_raises(IndexError, rsl.add_position, *(h14_pos, '1002'))
        self.assert_raises(ValueError, rsl.add_position, *(self.a1_pos, '1002'))
        a2_pos = get_rack_position_from_label('A2')
        self.assert_raises(ValueError, rsl.add_position, *(a2_pos, '1001'))

    def test_get_barcode_for_position(self):
        rsl = self.__create_test_layout()
        self.assert_equal(rsl.get_barcode_for_position(self.a1_pos),
                          self.position_data['A1'])
        a2_pos = get_rack_position_from_label('A2')
        self.assert_is_none(rsl.get_barcode_for_position(a2_pos))

    def test_get_positions(self):
        rsl = self.__create_test_layout()
        expected_positions = self.position_data.keys()
        layout_positions = rsl.get_positions()
        self.assert_equal(len(expected_positions), len(layout_positions))
        for rack_pos in layout_positions:
            self.assert_true(rack_pos.label in expected_positions)

    def test_get_tube_barcodes(self):
        rsl = self.__create_test_layout()
        expected_barcodes = self.position_data.values()
        layout_barcodes = rsl.get_tube_barcodes()
        expected_barcodes.sort()
        layout_barcodes.sort()
        self.assert_equal(expected_barcodes, layout_barcodes)

    def test_get_position_for_barcode(self):
        rsl = self.__create_test_layout()
        barcode = self.position_data['C3']
        rack_pos = rsl.get_position_for_barcode(barcode)
        self.assert_equal(rack_pos.label, 'C3')
        self.assert_is_none(rsl.get_position_for_barcode('1002'))

    def test_iterpositions(self):
        rsl = self.__create_test_layout()
        counter = 0
        for rack_pos, tube_barcode in rsl.iterpositions():
            counter += 1
            self.assert_equal(self.position_data[rack_pos.label], tube_barcode)
        self.assert_equal(counter, len(self.position_data))

    def test_equality(self):
        rsl1 = self.__create_test_layout()
        rsl2 = self.__create_test_layout()
        rsl3 = self.__create_test_layout()
        rsl3.rack_barcode = '099999990'
        rsl4 = self.__create_test_layout()
        rsl4.timestamp = datetime.now()
        self.position_data['C3'] = '1010'
        rsl5 = self.__create_test_layout()
        self.assert_equal(rsl1, rsl2)
        self.assert_equal(rsl1, rsl3)
        self.assert_equal(rsl1, rsl4)
        self.assert_not_equal(rsl1, rsl5)
        self.assert_not_equal(rsl1, self.rack_barcode)
