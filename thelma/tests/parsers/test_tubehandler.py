"""
Tests for classes involved in tubehandler output file parsing.

AAB
"""
from datetime import datetime

from pkg_resources import resource_filename # pylint: disable=E0611,F0401
import pytz

from everest.repositories.rdb.testing import RdbContextManager
from everest.repositories.rdb.testing import check_attributes
from thelma.automation.handlers.tubehandler import XL20OutputParserHandler
from thelma.automation.parsers.tubehandler import XL20OutputParser
from thelma.automation.parsers.tubehandler import XL20TransferParsingContainer
from thelma.automation.semiconstants import get_item_status_managed
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.interfaces import ITubeRackSpecs
from thelma.interfaces import ITubeSpecs
from thelma.models.container import ContainerLocation
from thelma.models.container import Tube
from thelma.models.rack import TubeRack
from thelma.tests.tools.tooltestingutils import ParsingTestCase
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase


class XL20TransferParsingContainerTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.line = '100115091408,25,01/15/10,09:29:13,09999999,A01,09999998,' \
                    'C03,1013589325,1013589325,0.0,,test error'

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.line

    def __get_init_data(self):
        line_values = self.line.split(XL20OutputParser.SEPARATOR)
        return dict(parser=XL20OutputParser(stream=None),
                    line_index=3, line_values=line_values)

    def __get_expected_attributes(self):
        return dict(line_number=4,
                    source_rack_barcode='09999999',
                    source_position_label='A01',
                    target_rack_barcode='09999998',
                    target_position_label='C03',
                    tube_barcode='1013589325',
                    timestamp=datetime(2010, 1, 15, 8, 29, 13,
                                       tzinfo=pytz.UTC))

    def test_init(self):
        kw = self.__get_init_data()
        pc = XL20TransferParsingContainer(**kw)
        self.assert_is_not_none(pc)
        attrs = self.__get_expected_attributes()
        check_attributes(pc, attrs)

    def test_invalid_date_format(self):
        self.line = '100115091408,25,01-15-10,09:29:13,09999999,A01,09999998,' \
                    'C03,1013589325,1013589325,0.0,,test error'
        kw = self.__get_init_data()
        pc = XL20TransferParsingContainer(**kw)
        self.assert_is_not_none(pc)
        attrs = self.__get_expected_attributes()
        attrs['timestamp'] = None
        check_attributes(pc, attrs)



class XL20OutputTestCase(ParsingTestCase):

    def set_up(self):
        ParsingTestCase.set_up(self)
        self.TEST_FILE_PATH = 'thelma:tests/parsers/tubehandler/'
        self.VALID_FILE = 'valid_file.txt'
        # line number, src rack barcode, src position, target rack barcode,
        # trg position, tube barcode, seconds for timestamp
        self.result_data = {
                28 : ['09999998', 'D06', '09999999', 'C04', '10001', 13],
                30 : ['09999997', 'D04', '09999999', 'C05', '10002', 20]}

    def tear_down(self):
        ParsingTestCase.tear_down(self)
        del self.result_data

    def _read_file(self, file_name, as_stream):
        fn = self.TEST_FILE_PATH + file_name
        f = resource_filename(*fn.split(':'))
        stream = open(f, 'rb')
        if as_stream:
            self.stream = stream
        else:
            self.stream = stream.read()


class XL20OutputParserTestCase(XL20OutputTestCase):

    def _create_tool(self):
        self.tool = XL20OutputParser(self.stream)

    def __continue_setup(self, file_name=None, as_stream=True):
        if file_name is None: file_name = self.VALID_FILE
        self._read_file(file_name, as_stream)
        self._create_tool()

    def __test_and_expect_errors(self, file_name, msg):
        self.__continue_setup(file_name)
        self.tool.run()
        self.assert_true(self.tool.has_errors())
        self._check_error_messages(msg)

    def __check_result(self):
        self.tool.run()
        self.assert_true(self.tool.has_run)
        self.assert_false(self.tool.has_errors())
        transfers = self.tool.xl20_transfers
        self.assert_equal(len(transfers), len(self.result_data))
        for transfer_container in transfers:
            exp_data = self.result_data[transfer_container.line_number]
            expected_timestamp = datetime(2010, 1, 15, 8, 29, exp_data[5],
                                          tzinfo=pytz.UTC)
            self.assert_equal(transfer_container.source_rack_barcode,
                              exp_data[0])
            self.assert_equal(transfer_container.source_position_label,
                              exp_data[1])
            self.assert_equal(transfer_container.target_rack_barcode,
                              exp_data[2])
            self.assert_equal(transfer_container.target_position_label,
                              exp_data[3])
            self.assert_equal(transfer_container.tube_barcode, exp_data[4])
            self.assert_equal(transfer_container.timestamp, expected_timestamp)

    def test_result_stream(self):
        self.__continue_setup(as_stream=True)
        self.__check_result()

    def test_result_content(self):
        self.__continue_setup(as_stream=False)
        self.__check_result()

    def test_result_with_error_message(self):
        self.__continue_setup(file_name='valid_file_with_error.txt')
        self.__check_result()
        self._check_warning_messages('Some lines contain error messages: ' \
                                     'line 28 ("some, error, message")')

    def test_result_inconsistent_barcodes(self):
        self.__continue_setup(file_name='inconsistent_barcodes.txt')
        self.__check_result()
        self._check_warning_messages('Attention! Expected tube barcode and ' \
                'the tube barcode actually found do not always match. ' \
                'Details: line 28 (10001 (expected) and 100 (found))')

    def test_invalid_source(self):
        self.__continue_setup()
        self.stream = 123
        self._create_tool()
        self.tool.run()
        self.assert_true(self.tool.has_errors())
        self._check_error_messages('Unknown type for stream')

    def test_different_line_breaks(self):
        self.__continue_setup(file_name='different_line_breaks.txt')
        self.__check_result()

    def test_incomplete_line(self):
        self.__test_and_expect_errors('incomplete_line.txt',
                        'The following lines are shorter than expected:')

    def test_invalid_timestamp(self):
        self.__test_and_expect_errors('invalid_timestamp.txt',
                        'Could not parse the timestamp for the following ' \
                        'lines: line 28 (01-15-10, 09:29:13)')


class XL20OutputParserHandlerTestCase(XL20OutputTestCase):

    def set_up(self):
        XL20OutputTestCase.set_up(self)
        self.racks = dict()

    def tear_down(self):
        XL20OutputTestCase.tear_down(self)
        del self.racks

    def _create_tool(self):
        self.tool = XL20OutputParserHandler(self.stream)

    def __continue_setup(self, session, file_name=None):
        if file_name is None: file_name = self.VALID_FILE
        self._read_file(file_name, as_stream=True)
        self.__create_racks(session)
        self.__create_tubes(session)
        self._create_tool()

    def __create_racks(self, session):
        rack_barcodes = set()
        for transfer_data in self.result_data.values():
            rack_barcodes.add(transfer_data[0])
            rack_barcodes.add(transfer_data[2])
        tube_rack_specs = self._get_entity(ITubeRackSpecs)
        status = get_item_status_managed()
        for barcode in rack_barcodes:
            tube_rack = TubeRack(label=barcode, specs=tube_rack_specs,
                                 status=status, barcode=barcode)
            self.racks[barcode] = tube_rack
            session.add(type(tube_rack), tube_rack)

    def __create_tubes(self, session):
        tube_barcodes = dict()
        for transfer_data in self.result_data.values():
            tube_barcode = transfer_data[4]
            src_rack_barcode = transfer_data[0]
            src_pos_label = transfer_data[1]
            tube_barcodes[tube_barcode] = (src_rack_barcode, src_pos_label)
        tube_specs = self._get_entity(ITubeSpecs)
        status = get_item_status_managed()
        for tube_barcode, location in tube_barcodes.iteritems():
            tube = Tube(specs=tube_specs, status=status, barcode=tube_barcode)
            rack_barcode = location[0]
            rack = self.racks[rack_barcode]
            rack_pos = get_rack_position_from_label(location[1])
            ContainerLocation(container=tube, rack=rack, position=rack_pos)
            rack.containers.append(tube)
            session.add(type(tube), tube)
        session.commit()

    def _test_and_expect_errors(self, msg=None):
        XL20OutputTestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_timestamp())

    def test_result(self):
        with RdbContextManager() as session:
            self.__continue_setup(session)
            tube_transfers = self.tool.get_result()
            self.assert_is_not_none(tube_transfers)
            # check timestamp
            timestamp = self.tool.get_timestamp()
            self.assert_is_not_none(timestamp)
            expected_timestamp = datetime(2010, 1, 15, 8, 29, 13,
                                          tzinfo=pytz.UTC)
            self.assert_equal(expected_timestamp, timestamp)
            # check tube transfers
            self.assert_equal(len(tube_transfers), len(self.result_data))
            for tt in tube_transfers:
                tube_barcode = tt.tube.barcode
                has_been_found = False
                for transfer_data in self.result_data.values():
                    if not transfer_data[4] == tube_barcode: continue
                    self.assert_equal(tt.source_rack.barcode, transfer_data[0])
                    exp_src_pos = get_rack_position_from_label(transfer_data[1])
                    self.assert_equal(tt.source_position, exp_src_pos)
                    self.assert_equal(tt.target_rack.barcode, transfer_data[2])
                    exp_trg_pos = get_rack_position_from_label(transfer_data[3])
                    self.assert_equal(tt.target_position, exp_trg_pos)
                    has_been_found = True
                self.assert_true(has_been_found)

    def test_unknown_rack(self):
        self.result_data[28][0] = '09999996'
        self.result_data[30][0] = '09999996'
        with RdbContextManager() as session:
            self.__continue_setup(session)
            self._test_and_expect_errors('Could not find a database record ' \
                        'for the following rack barcodes: 09999997, 09999998.')

    def test_mismatching_tube(self):
        self.result_data[28][4] = '10003'
        with RdbContextManager() as session:
            self.__continue_setup(session)
            self._test_and_expect_errors('Some positions contain unexpected ' \
                        'tubes: D6 in 09999998 (found: 10003, expected: 10001)')

    def test_missing_tubes(self):
        self.result_data[28][1] = 'D07'
        with RdbContextManager() as session:
            self.__continue_setup(session)
            self._test_and_expect_errors('Some tubes have not been found at ' \
                    'the positions at which they were expected: 10001 ' \
                    '(09999998 D6).')

    def test_invalid_label(self):
        with RdbContextManager() as session:
            self.__continue_setup(session, 'invalid_position_label.txt')
            self._test_and_expect_errors('The following position labels are ' \
                                     'invalid: CC')
