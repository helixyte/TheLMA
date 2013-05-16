"""
Tests the library member parser and handler.

AAB
"""
from everest.entities.utils import get_root_aggregate
from thelma.automation.handlers.libmembers import LibraryMemberParserHandler
from thelma.automation.parsers.libmembers import LibraryMemberParser
from thelma.interfaces import IMoleculeType
from thelma.models.moleculetype import MOLECULE_TYPE_IDS
from thelma.tests.tools.tooltestingutils import ParsingTestCase


class LibraryMemberTestCase(ParsingTestCase):

    def set_up(self):
        ParsingTestCase.set_up(self)
        self.TEST_FILE_PATH = 'thelma:tests/parsers/libmembers/'
        self.VALID_FILE = 'valid_file.xls'

    def _get_expected_molecule_design_ids(self):
        md_ids = [[10247990, 10331567, 10339513],
                  [10247991, 10331568, 10339514],
                  [10247992, 10331569, 10339515],
                  [10247993, 10331570, 10339516],
                  [10247986, 10331563, 10339509],
                  [10247987, 10331564, 10339510],
                  [10247988, 10331565, 10339511],
                  [10247989, 10331566, 10339512],
                  [10247998, 10331574, 10339520],
                  [10247999, 10331575, 10339521],
                  [10248000, 10331576, 10339522]]
        return md_ids


class LibraryMemberParserTestCase(LibraryMemberTestCase):

    def _create_tool(self):
        self.tool = LibraryMemberParser(stream=self.stream, log=self.log)

    def _test_invalid_file(self, file_name, msg):
        self._continue_setup(file_name)
        self.tool.parse()
        self.assert_true(self.tool.has_errors())
        self._check_error_messages(msg)

    def test_result(self):
        self._continue_setup()
        self.tool.parse()
        self.assert_false(self.tool.has_errors())
        tool_list = self.tool.molecule_design_lists
        exp_list = self._get_expected_molecule_design_ids()
        self.assert_equal(len(tool_list), len(exp_list))
        self.assert_equal(tool_list, exp_list)

    def test_empty_column(self):
        self._test_invalid_file('empty.xls',
                                'There are no molecule designs in the column')

    def test_no_columns(self):
        self._test_invalid_file('no_column.xls', 'Unable to find ' \
                'molecule design column. A valid column must be called ' \
                '"Molecule Design IDs" (case-insensitive)')

    def test_invalid_id(self):
        self._test_invalid_file('invalid_id.xls',
                'Some cells contain invalid molecule design IDs')


class LibraryMemberParserHandlerTestCase(LibraryMemberTestCase):

    def set_up(self):
        LibraryMemberTestCase.set_up(self)
        self.number_designs = 3
        self.molecule_type = get_root_aggregate(IMoleculeType).get_by_id(
                                                MOLECULE_TYPE_IDS.SIRNA)

    def tear_down(self):
        LibraryMemberTestCase.tear_down(self)
        del self.number_designs
        del self.molecule_type

    def _create_tool(self):
        self.tool = LibraryMemberParserHandler(log=self.log,
                                   stream=self.stream,
                                   number_molecule_designs=self.number_designs,
                                   molecule_type=self.molecule_type)

    def test_result(self):
        self._continue_setup()
        pool_set = self.tool.get_result()
        self.assert_is_not_none(pool_set)
        exp_ids = self._get_expected_molecule_design_ids()
        self.assert_equal(len(exp_ids), len(pool_set))
        sorted_exp_ids = []
        for md_list in exp_ids:
            sorted_exp_ids.append(sorted(md_list))
        found_mds = []
        for pool in pool_set:
            md_ids = []
            for md in pool: md_ids.append(md.id)
            md_ids.sort()
            self.assert_true(md_ids in sorted_exp_ids)
            self.assert_false(md_ids in found_mds)
            found_mds.append(md_ids)
        self.assert_equal(pool_set.molecule_type, self.molecule_type)

    def test_invalid_input_values(self):
        self._continue_setup()
        self.number_designs = '3'
        self._test_and_expect_errors('The number molecule designs must be ' \
                                     'a int')
        self.number_designs = 3
        self.molecule_type = MOLECULE_TYPE_IDS.SIRNA
        self._test_and_expect_errors('The molecule type must be a ' \
                                     'MoleculeType object')

    def test_mismatching_number_designs(self):
        self.number_designs = 2
        self._continue_setup()
        self._test_and_expect_errors('Some molecule design pool stated in ' \
                'the file do not have the expected number of molecule designs')

    def test_unknown_molecule_design(self):
        self._continue_setup('unknown_md.xls')
        self._test_and_expect_errors('The following molecule designs have ' \
                                     'not been found in the DB: 2, 99999999')

    def test_invalid_md_type(self):
        self._continue_setup('invalid_md_type.xls')
        self._test_and_expect_errors('The molecule designs in the list have ' \
                        'different molecule types. Expected: SIRNA. Others ' \
                        '(molecule designs): 10405733')
