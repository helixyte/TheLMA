"""
Tests the pool creation ISO request member parser and handler.

AAB
"""

from thelma.tests.tools.tooltestingutils import ParsingTestCase
from thelma.automation.parsers.poolcreationset import PoolCreationSetParser
from thelma.automation.handlers.poolcreationset \
    import PoolCreationSetParserHandler
from everest.entities.utils import get_root_aggregate
from thelma.interfaces import IMoleculeType
from thelma.models.moleculetype import MOLECULE_TYPE_IDS

class PoolCreationSetParsingTestCase(ParsingTestCase):

    _PARSER_CLS = PoolCreationSetParser

    def set_up(self):
        ParsingTestCase.set_up(self)
        self.TEST_FILE_PATH = 'thelma:tests/parsers/poolcreationset/'
        self.VALID_FILE = 'valid_file.xls'

    def _get_expected_molecule_design_ids(self):
        md_ids = {1 : [10247990, 10331567, 10339513],
                  2 : [10247991, 10331568, 10339514],
                  3 : [10247992, 10331569, 10339515],
                  4 : [10247993, 10331570, 10339516],
                  5 : [10247986, 10331563, 10339509],
                  6 : [10247987, 10331564, 10339510],
                  7 : [10247988, 10331565, 10339511],
                  8 : [10247989, 10331566, 10339512],
                  9 : [10247998, 10331574, 10339520],
                  10 : [10247999, 10331575, 10339521],
                  11 : [10248000, 10331576, 10339522]}
        return md_ids

    def _get_exptected_pool_ids(self):
        pool_ids = {1 : 1063102, 2 : 1058382, 3 : 1064324, 4 : 1065599,
                    5 : 1059807, 6 : 1060579, 7 : 1065602, 8 : 1063754,
                    9 : 1059776, 10 : 1060625, 11 : 1065628}
        return pool_ids

    def _continue_setup(self, file_name=None):
        ParsingTestCase._continue_setup(self, file_name)
        self._create_tool()


class PoolCreationSetParserTestCase(PoolCreationSetParsingTestCase):

    def _create_tool(self):
        self.tool = PoolCreationSetParser(stream=self.stream, log=self.log)

    def __check_result(self, file_name=None, exp_md_lists=None, exp_pools=None):
        self._continue_setup(file_name)
        self.tool.parse()
        self.assert_false(self.tool.has_errors())
        md_lists = self.tool.molecule_design_lists
        if exp_md_lists is None:
            exp_md_lists = self._get_expected_molecule_design_ids()
        self.assert_equal(len(md_lists), len(exp_md_lists))
        self.assert_equal(md_lists, exp_md_lists)
        pool_list = self.tool.pool_ids
        if exp_pools is None:
            exp_pools = self._get_exptected_pool_ids()
        self.assert_equal(len(pool_list), len(exp_pools))
        self.assert_equal(pool_list, exp_pools)

    def __test_and_expect_errors(self, file_name, msg):
        self._continue_setup(file_name)
        self.tool.parse()
        self.assert_true(self.tool.has_errors())
        self._check_error_messages(msg)

    def test_result_pools_and_mds(self):
        self.__check_result()

    def test_result_pools_only(self):
        self.__check_result('valid_file_pool_only.xls', exp_md_lists=dict())

    def test_result_single_mds_only(self):
        self.__check_result('valid_file_md_only.xls', exp_pools=dict())

    def test_result_mixed(self):
        exp_md_lists = self._get_expected_molecule_design_ids()
        del exp_md_lists[2]
        exp_pools = self._get_exptected_pool_ids()
        del exp_pools[3]
        self.__check_result('valid_file_mixed.xls', exp_md_lists, exp_pools)

    def test_no_valid_column(self):
        self.__test_and_expect_errors('no_column.xls',
                  'Unable to find a molecule design data column. A valid ' \
                  'column must be called "Molecule Design IDs" for single ' \
                  'molecule design ID lists or "Molecule Design Pool IDs" or ' \
                  '"Pool IDs" for final pool IDs (all case-insensitive).')

    def test_invalid_pool(self):
        self.__test_and_expect_errors('invalid_pool.xls', 'Some rows contain ' \
                        'invalid pool IDs: row 5 (1065599x), row 6 (1059807x).')

    def test_invalid_single_md(self):
        self.__test_and_expect_errors('invalid_md.xls',
              'Some rows contain invalid molecule design IDs: row 6 ' \
              '(10247986-inactive-10339509), row 10 (10247998-10331574-none).')

    def test_no_pools(self):
        self.__test_and_expect_errors('no_pools.xls',
                                      'There is no design data in the columns!')


class PoolCreationSetParserHandlerTestCase(PoolCreationSetParsingTestCase):

    def _create_tool(self):
        self.tool = PoolCreationSetParserHandler(log=self.log,
                                                 stream=self.stream)

    def __get_expected_number_designs(self):
        return 3

    def __get_expected_molecule_type(self):
        mt = get_root_aggregate(IMoleculeType).get_by_id(
                                                     MOLECULE_TYPE_IDS.SIRNA)
        self.assert_is_not_none(mt)
        return mt

    def __check_result(self, file_name=None, exp_md_lists=None, exp_pools=None):
        self._continue_setup(file_name)
        pool_set = self.tool.get_result()
        self.assert_is_not_none(pool_set)
        self.assert_equal(self.tool.get_number_designs(),
                          self.__get_expected_number_designs())
        self.assert_equal(self.tool.get_molecule_type(),
                          self.__get_expected_molecule_type())
        if exp_pools is None: exp_pools = self._get_exptected_pool_ids()
        self.assert_equal(len(exp_pools), len(pool_set))
        found_pool_ids = []
        found_md_lists = []
        for pool in pool_set:
            found_pool_ids.append(pool.id)
            md_ids = []
            for md in pool: md_ids.append(md.id)
            found_md_lists.append(sorted(md_ids))
        self.assert_equal(sorted(found_pool_ids), sorted(exp_pools.values()))
        if exp_md_lists is None:
            exp_md_lists = self._get_expected_molecule_design_ids()
        for i in range(len(exp_md_lists)):
            exp_md_lists[i + 1] = sorted(exp_md_lists[i + 1])
        self.assert_equal(sorted(found_md_lists), sorted(exp_md_lists.values()))


    def _test_and_expect_errors(self, msg=None):
        PoolCreationSetParsingTestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_number_designs())
        self.assert_is_none(self.tool.get_molecule_type())

    def __test_file_and_expect_error(self, msg, file_name=None):
        self._continue_setup(file_name)
        self._test_and_expect_errors(msg)

    def test_if_result(self):
        self._test_if_result()

    def test_result(self):
        self.__check_result()

    def test_result_pools_only(self):
        self.__check_result('valid_file_pool_only.xls')

    def test_result_single_mds_only(self):
        self.__check_result('valid_file_md_only.xls')

    def test_result_mixed(self):
        self.__check_result('valid_file_mixed.xls')

    def test_result_new_pool(self):
        exp_md_lists = self._get_expected_molecule_design_ids()
        exp_md_lists[1][2] = 12
        exp_pools = self._get_exptected_pool_ids()
        exp_pools[1] = None
        self.__check_result('valid_file_new_pool.xls', exp_md_lists, exp_pools)

    def test_unknown_pool(self):
        self.__test_file_and_expect_error(file_name='unknown_pool.xls',
            msg='Unable to find pools for the following IDs in the DB: ' \
                '9999999999')

    def test_unknown_md(self):
        self.__test_file_and_expect_error(file_name='unknown_md.xls',
            msg='Unable to find molecule designs for the following IDs in ' \
                'the DB: 1, 2')

    def test_inconsistent_data(self):
        self.__test_file_and_expect_error(file_name='inconsistent_data.xls',
            msg='In some rows the pools and the molecule designs you have ' \
                'ordered to not match: 1065599 (expected: ' \
                '10247993-10331570-10339516, found in file: ' \
                '10247993-10331570-10339515)')

    def test_invalid_number_designs(self):
        self.__test_file_and_expect_error(
            file_name='invalid_number_designs.xls',
            msg='The number of molecule designs must be the same for all ' \
                'pools. The number of designs for the first pool is 3. The ' \
                'pools in the following rows have different numbers: 5, 6.')

    def test_invalid_molecule_type(self):
        self.__test_file_and_expect_error(file_name='invalid_molecule_type.xls',
            msg='The molecule type must be the same for all pools. The ' \
                'molecule type for the first pools is SIRNA. The pools in ' \
                'the following rows have different molecule types: 5, 6.')
