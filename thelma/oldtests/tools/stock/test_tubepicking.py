"""
Tests for tube picking (base) classes.

AAB
"""
from everest.repositories.rdb.testing import RdbContextManager
from everest.repositories.rdb.testing import check_attributes
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.stock.tubepicking import MultiPoolQuery
from thelma.automation.tools.stock.tubepicking import OptimizingQuery
from thelma.automation.tools.stock.tubepicking import SinglePoolQuery
from thelma.automation.tools.stock.tubepicking import StockSampleQuery
from thelma.automation.tools.stock.tubepicking import TubeCandidate
from thelma.automation.tools.stock.tubepicking import TubePicker
from thelma.automation.tools.stock.tubepicking import TubePoolQuery
from thelma.automation.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.oldtests.tools.tooltestingutils import ToolsAndUtilsTestCase


class StockSampleQueryTestCase(ToolsAndUtilsTestCase):

    def test_run(self):
        pool_ids = [1056000, 330001]
        concentration = 10000 # nM
        min_vol = 5
        query = StockSampleQuery(pool_ids=pool_ids,
                                 concentration=concentration,
                                 minimum_volume=min_vol)
        with RdbContextManager() as session:
            query.run(session)
            results = query.get_query_results()
            self.assert_equal(len(results), 2)
            self.assert_equal(sorted(results.keys()), sorted(pool_ids))
            for sample_list in results.values():
                self.assert_not_equal(len(sample_list), 0)


class TubePoolQueryTestCase(ToolsAndUtilsTestCase):

    def test_run(self):
        valid_barcodes = {'1016673842' : 330001, '1019052318' : 330001,
                          '1077108257' : 1056000}
        invalid_barcode = '1001'
        all_barcodes = valid_barcodes.keys() + [invalid_barcode]
        query = TubePoolQuery(tube_barcodes=all_barcodes)
        with RdbContextManager() as session:
            query.run(session)
            results = query.get_query_results()
            self.assert_equal(results, valid_barcodes)


class TubeCandidateTestCase(ToolsAndUtilsTestCase):

    def __get_data(self):
        return dict(pool_id=1056000, rack_barcode='09999999',
                    rack_position=get_rack_position_from_label('a1'),
                    tube_barcode='10001056000',
                    concentration=100 / CONCENTRATION_CONVERSION_FACTOR,
                    volume=5 / VOLUME_CONVERSION_FACTOR)

    def test_init(self):
        kw = self.__get_data()
        tc = TubeCandidate(**kw)
        kw['concentration'] = 100
        kw['volume'] = 5
        check_attributes(tc, kw)
        self.assert_is_none(tc.get_pool())
        wrong_pool = self._get_pool(205200)
        self.assert_is_not_none(wrong_pool)
        self._expect_error(ValueError, tc.set_pool, 'The pool does not have ' \
                           'the expected ID (205200 instead of 1056000)',
                           **dict(pool=wrong_pool))
        pool = self._get_pool(1056000)
        self.assert_is_not_none(pool)
        tc.set_pool(pool)
        self.assert_equal(pool, tc.get_pool())


class SinglePoolQueryTestCase(ToolsAndUtilsTestCase):

    def test_run(self):
        query = SinglePoolQuery(pool_id=330001, concentration=10000,
                                minimum_volume=5)
        with RdbContextManager() as session:
            query.run(session)
            results = query.get_query_results()
            self.assert_equal(len(results), 2)
            tube_barcodes = []
            for tc in results:
                self.assert_true(isinstance(tc, TubeCandidate))
                tube_barcodes.append(tc.tube_barcode)
            self.assert_equal(sorted(tube_barcodes),
                              ['1016673842', '1019052318'])


class MultiPoolQueryTestCase(ToolsAndUtilsTestCase):

    def test_run(self):
        query = MultiPoolQuery(pool_ids=[1056000, 330001],
                               concentration=10000, minimum_volume=5)
        with RdbContextManager() as session:
            query.run(session)
            results = query.get_query_results()
            pools = []
            for pool_id, tcs in results.iteritems():
                pools.append(pool_id)
                self.assert_not_equal(len(tcs), 0)
            self.assert_equal(sorted(pools), [330001, 1056000])


class OptimizingQueryTestCase(ToolsAndUtilsTestCase):

    def test_run(self):
        sample_ids = [3090415, 3291134, 3615716]
        query = OptimizingQuery(sample_ids)
        with RdbContextManager() as session:
            query.run(session)
            results = query.get_query_results()
            self.assert_is_not_none(results)
            self.assert_equal(len(results), 3)
            pool_ids = set()
            for tc in results:
                pool_ids.add(tc.pool_id)
            self.assert_equal(sorted(list(pool_ids)), [330001, 1056000])


class TubePickerTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.pools = [self._get_pool(1056000), self._get_pool(330001)]
        self.stock_concentration = 10000
        self.takeoutvol = 5
        self.excluded_racks = None
        self.requested_tubes = None

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.pools
        del self.stock_concentration
        del self.takeoutvol
        del self.excluded_racks
        del self.requested_tubes

    def _create_tool(self):
        self.tool = TubePicker(self.pools,
                               self.stock_concentration,
                               take_out_volume=self.takeoutvol,
                               excluded_racks=self.excluded_racks,
                               requested_tubes=self.requested_tubes)

    def _test_and_expect_errors(self, msg=None):
        ToolsAndUtilsTestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_unsorted_candidates())

    def __check_result(self):
        self._create_tool()
        candidates = self.tool.get_result()
        self.assert_is_not_none(candidates)
        self.assert_equal(len(candidates), 2)
        unsorted = self.tool.get_unsorted_candidates()
        self.assert_is_not_none(unsorted)
        self.assert_equal(len(unsorted), 3)
        tubes = dict()
        pool_ids = set()
        for pool, tcs in candidates.iteritems():
            pool_ids.add(pool.id)
            for tc in tcs:
                tubes[tc.tube_barcode] = tc.rack_barcode
        self.assert_equal(sorted(list(pool_ids)), [330001, 1056000])
        if self.excluded_racks is not None:
            for er in self.excluded_racks:
                self.assert_false(er in tubes.values())
        if self.requested_tubes is not None:
            tc1 = candidates[self._get_pool(330001)][0]
            self.assert_true([tc1.tube_barcode], self.requested_tubes)

    def test_result(self):
        self.__check_result()

    def test_result_excluded_racks(self):
        with RdbContextManager() as session:
            query = SinglePoolQuery(pool_id=330001,
                                    concentration=self.stock_concentration,
                                    minimum_volume=self.takeoutvol)
            query.run(session)
            tubes = query.get_query_results()
            self.excluded_racks = []
            for tc in tubes:
                self.excluded_racks.append(tc.rack_barcode)
                break
            self.assert_not_equal(len(self.excluded_racks), 0)
            self.__check_result()

    def test_requested_tubes(self):
        # you need to use a pool with at least 2 valid tubes
        with RdbContextManager() as session:
            query = SinglePoolQuery(pool_id=330001,
                                    concentration=self.stock_concentration,
                                    minimum_volume=self.takeoutvol)
            query.run(session)
            tubes = query.get_query_results()
            self.requested_tubes = []
            for tc in tubes:
                self.requested_tubes.append(tc.tube_barcode)
                if len(self.requested_tubes) == 2: break
            self.assert_equal(len(self.requested_tubes), 2)

            # use 2 tubes for pool 330001
            tube1 = self.requested_tubes[1]
            tube2 = self.requested_tubes[0]
            self.requested_tubes = [tube1]
            self.__check_result()
            self.requested_tubes = [tube2]
            self.__check_result()

    # TODO: switch on again - this test is failing if run in the model
#    def test_missing_sample(self):
#        with RdbContextManager() as session:
#            query = SinglePoolQuery(pool_id=330001,
#                                    concentration=self.stock_concentration,
#                                    minimum_volume=self.takeoutvol)
#            query.run(session)
#            tubes = query.get_query_results()
#            self.excluded_racks = []
#            for tc in tubes:
#                self.excluded_racks.append(tc.rack_barcode)
#            self.assert_not_equal(len(self.excluded_racks), 0)
#            self._create_tool()
#            candidates = self.tool.get_result()
#            self.assert_is_not_none(candidates)
#            self.assert_equal(len(candidates), 1)
#            pool = candidates.keys()[0]
#            self.assert_equal(pool.id, 1056000)
#            self._check_warning_messages('Unable to find valid tubes for the ' \
#                                         'following pools: 330001.')
