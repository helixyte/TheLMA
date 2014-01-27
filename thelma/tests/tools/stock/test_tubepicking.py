"""
Tests for tube picking (base) classes.

AAB
"""
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase
from thelma.automation.tools.stock.tubepicking import StockSampleQuery
from everest.testing import RdbContextManager
from thelma.automation.tools.stock.tubepicking import TubePoolQuery
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.stock.tubepicking import TubeCandidate
from everest.testing import check_attributes
from thelma.automation.tools.stock.tubepicking import SinglePoolQuery
from thelma.automation.tools.stock.tubepicking import MultiPoolQuery
from thelma.automation.tools.stock.tubepicking import OptimizingQuery
from thelma.tests.tools.tooltestingutils import TestingLog

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
        self.log = TestingLog()
        self.pools = [self._get_pool(1056000), self._get_pool(330001)]
