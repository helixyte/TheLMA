"""
tests the ISO excel file parser

AAB July 1a, 2011
"""

from thelma.tests.tools.tooltestingutils import ParsingTestCase
from thelma.automation.handlers.experimentpoolset \
    import ExperimentPoolSetParserHandler
from thelma.automation.parsers.experimentpoolset import ExperimentPoolSetParser


class ExperimentPoolSetExcelParserTest(ParsingTestCase):

    _PARSER_CLS = ExperimentPoolSetParser

    def set_up(self):
        ParsingTestCase.set_up(self)
        self.VALID_FILE = 'valid_list.xls'
        self.TEST_FILE_PATH = 'thelma:tests/parsers/experimentpoolset/'

    def _create_tool(self):
        self.tool = ExperimentPoolSetParserHandler(self.stream)

    def _test_and_expect_errors(self, msg=None):
        ParsingTestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_stock_concentration())

    def test_if_result(self):
        self._test_if_result()

    def test_correct_molecule_designs(self):
        self._continue_setup(self.VALID_FILE)
        pool_set = self.tool.get_result()
        expected_pools = [205200, 205201, 205202, 205203, 205204, 205205,
                          205206, 205207, 205208]
        self.assert_equal(len(pool_set.molecule_design_pools),
                          len(expected_pools))
        for md_pool in pool_set.molecule_design_pools:
            self.assert_true(md_pool.id in expected_pools)
        self.assert_equal(self.tool.get_stock_concentration(), 50000)

    def test_unknown_design(self):
        self._continue_setup('unknown_id.xls')
        self._test_and_expect_errors('The following molecule design pool IDs ' \
                                     'have not be found in the DB')

    def test_duplicate_id(self):
        self._continue_setup('duplicate_id.xls')
        pool_set = self.tool.get_result()
        expected_pools = [205200, 205201, 205202, 205203, 205204,
                          205206, 205207, 205208]
        self.assert_equal(len(pool_set.molecule_design_pools),
                          len(expected_pools))
        for md_pool in pool_set.molecule_design_pools:
            self.assert_true(md_pool.id in expected_pools)
        self._check_warning_messages('Duplicate molecule design pool')
        self.assert_equal(self.tool.get_stock_concentration(), 50000)

    def test_with_interrupt(self):
        self._continue_setup('with_interrupt.xls')
        pool_set = self.tool.get_result()
        expected_pools = [205200, 205201, 205202, 205203, 205204, 205205]
        self.assert_equal(len(pool_set.molecule_design_pools),
                          len(expected_pools))
        for md_pool in pool_set.molecule_design_pools:
            self.assert_true(md_pool.id in expected_pools)
        self._check_warning_messages('Empty Cell in Row')
        self.assert_equal(self.tool.get_stock_concentration(), 50000)

    def test_non_digit_chars(self):
        self._test_invalid_file('non_digit_chars.xls',
                                'There is a non-number character')

    def test_empty_list(self):
        self._test_invalid_file('empty_list.xls',
                'Could not find a column for the molecule design pool IDs')

    def test_wrong_sheet_name(self):
        self._test_invalid_file('wrong_sheet_name.xls', '')
        self.assert_false(self.tool.parsing_completed())
        self.assert_false(self.tool.has_errors())

    def test_wrong_column_name(self):
        self._test_invalid_file('column_missing.xls',
                'Could not find a column for the molecule design pool IDs!')

    def test_no_pool(self):
        self._test_invalid_file('no_mds.xls', '')
        self.assert_false(self.tool.parsing_completed())
        self.assert_false(self.tool.has_errors())

    def test_unicode(self):
        self._test_invalid_file('unicode.xls', 'Unknown character in cell B8')

    def test_different_molecule_types(self):
        self._test_invalid_file('different_molecule_types.xls',
                    'There is more than one molecule type in the the ' \
                    'molecule design set')

    def test_different_stock_concentrations(self):
        self._test_invalid_file('different_stock_conc.xls',
                'The pools in the set have different stock concentrations')
