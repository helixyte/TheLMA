"""
Tests for dummy classes.

AAB
"""
from StringIO import StringIO
from datetime import datetime
from thelma.automation.parsers.tubehandler import XL20OutputParser
from thelma.automation.tools.dummies import XL20Dummy
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase
from thelma.automation.tools.writers import LINEBREAK_CHAR
from thelma.tests.tools.tooltestingutils import TestingLog


class XL20OutputFileCreatorTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.WL_PATH = 'thelma:tests/tools/worklists/xl20outputwriter/'
        self.log = TestingLog()
        self.worklist_stream = None
        self.worklist = \
        '''"Source Rack";"Source Position";"Tube Barcode";"Destination Rack";"Destination Position"
            "09999998";"A1";"1001";"09999977";"G1"
            "09999998";"A1";"1003";"09999978";"G1"
            "09999998";"C2";"1004";"09999977";"G2"
            "09999999";"B1";"1002";"09999976";"G1"'''
        self.exp_output = [
            ',,%s,%s,09999998,A1,09999977,G1,1001,1001,,,',
            ',,%s,%s,09999998,A1,09999978,G1,1003,1003,,,',
            ',,%s,%s,09999998,C2,09999977,G2,1004,1004,,,',
            ',,%s,%s,09999999,B1,09999976,G1,1002,1002,,,' ]

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.worklist
        del self.exp_output

    def _create_tool(self):
        self.tool = XL20Dummy(xl20_worklist_stream=self.worklist_stream,
                              log=self.log)

    def __continue_setup(self):
        self.worklist_stream = StringIO(self.worklist)
        self._create_tool()

    def test_result(self):
        self.__continue_setup()
        result = self.tool.get_result()
        self.assert_is_not_none(result)
        content = result.read()
        parser_cls = XL20OutputParser
        exp_date = datetime.now().strftime(parser_cls.DATE_FORMAT)
        lines = content.split(LINEBREAK_CHAR)
        found_lines = 0
        for i in range(len(lines)):
            rline = lines[i]
            if len(rline) < 1: continue # last empty line
            found_lines += 1
            tokens = rline.split(parser_cls.SEPARATOR)
            exp_line_pattern = self.exp_output[i]
            time_str = tokens[parser_cls.TIME_INDEX]
            exp_line = exp_line_pattern % (exp_date, time_str)
            self.assert_equal(rline, exp_line)
        self.assert_equal(found_lines, len(self.exp_output))

    def test_invalid_input_values(self):
        self.worklist_stream = None
        self._test_and_expect_errors('The input stream must be StringIO or a ' \
                                     'file type')

    def test_unknown_delimiter(self):
        self.worklist = \
        '''"Source Rack"--"Source Position"--"Tube Barcode"--"Destination Rack"--"Destination Position"
            "09999998"--"A1"--"1001"--"09999977"--"G1"
            "09999998"--"A1"--"1003"--"09999978"--"G1"
            "09999998"--"C2"--"1004"--"09999977"--"G2"
            "09999999"--"B1"--"1002"--"09999976"--"G1"'''
        self.__continue_setup()
        self._test_and_expect_errors('Unknown delimiter')

    def test_unexpected_content(self):
        self.worklist = 'This is not the file I\n expected; try again.'
        self.__continue_setup()
        self._test_and_expect_errors('Unexpected number of columns')
