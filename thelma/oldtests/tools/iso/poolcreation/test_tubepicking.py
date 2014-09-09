"""
Deals with tube picking optimisation for pool stock sample creations.

AAB
"""
from everest.repositories.rdb.testing import RdbContextManager
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.iso.poolcreation.tubepicking \
    import StockSampleCreationTubePicker
from thelma.automation.tools.iso.poolcreation.tubepicking import PoolCandidate
from thelma.automation.tools.stock.tubepicking import TubeCandidate
from thelma.automation.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.interfaces import IMoleculeDesign
from thelma.oldtests.tools.tooltestingutils import ToolsAndUtilsTestCase


class PoolCandidateTestCase(ToolsAndUtilsTestCase):

    def __get_molecule_design_ids(self):
        return [10315676, 10319279, 10341998]

    def __get_single_pool_ids(self, md_id):
        d = {10315676 : 287431, 10319279 : 291121, 10341998 : 314179,
             5 : 287431}
        return d[md_id]

    def __get_data(self):
        return dict(pool=self._get_pool(1056000))

    def __init(self, kw):
        return PoolCandidate(**kw)

    def __create_tube_candidate(self, md_id):
        return TubeCandidate(self.__get_single_pool_ids(md_id),
                       rack_barcode='012345678',
                       rack_position=get_rack_position_from_label('a1'),
                       tube_barcode='100%i' % (md_id),
                       concentration=50000 / CONCENTRATION_CONVERSION_FACTOR,
                       volume=10 / VOLUME_CONVERSION_FACTOR)

    def test_init(self):
        pc = self.__init(self.__get_data())
        self.assert_is_not_none(pc)
        self.assert_equal(pc.pool.id, 1056000)
        self.assert_equal(sorted(pc.get_molecule_design_ids()),
                          sorted(self.__get_molecule_design_ids()))

    def test_tube_candidates(self):
        pc = self.__init(self.__get_data())
        self.assert_false(pc.is_completed())
        self.assert_equal(pc.get_tube_barcodes(), [])
        tube_barcodes = []
        for md in pc.pool:
            md_id = md.id
            tc = self.__create_tube_candidate(md_id)
            tube_barcode = tc.tube_barcode
            tube_barcodes.append(tube_barcode)
            self.assert_false(pc.has_tube_candidate(md_id))
            pc.set_tube_candidate(md_id, tc)
            self.assert_true(pc.has_tube_candidate(md_id))
            if len(tube_barcodes) == 3:
                self.assert_true(pc.is_completed())
            else:
                self.assert_false(pc.is_completed())
        self.assert_equal(sorted(tube_barcodes), sorted(pc.get_tube_barcodes()))
        new_tc = self.__create_tube_candidate(5)
        tube_barcodes.remove(tc.tube_barcode)
        tube_barcodes.append(new_tc.tube_barcode)
        self.assert_not_equal(sorted(tube_barcodes),
                              sorted(pc.get_tube_barcodes()))
        self._expect_error(AttributeError, pc.set_tube_candidate,
              'The candidate for molecule design %i has already been set ' \
              '(library pool 1056000)' % (md_id),
               **dict(md_id=md_id, candidate=new_tc))
        pc.replace_candidate(md_id, new_tc)
        self.assert_equal(sorted(tube_barcodes), sorted(pc.get_tube_barcodes()))


class StockSampleCreationTubePickerTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.molecule_design_pools = []
        self.single_design_concentration = 50000 # 50 mM
        self.take_out_volume = 1
        self.excluded_racks = None
        self.requested_tubes = None
        # pool id - single design IDs
        self.pool_data = {1056000 : [10315676, 10319279, 10341998],
                          1056001 : [10315722, 10319325, 10342044]}

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.molecule_design_pools
        del self.single_design_concentration
        del self.take_out_volume
        del self.excluded_racks
        del self.requested_tubes
        del self.pool_data

    def _create_tool(self):
        self.tool = StockSampleCreationTubePicker(
                                        self.molecule_design_pools,
                                        self.single_design_concentration,
                                        self.take_out_volume,
                                        excluded_racks=self.excluded_racks,
                                        requested_tubes=self.requested_tubes)

    def __continue_setup(self):
        self.__create_pools()
        self._create_tool()

    def __create_pools(self):
        conc = 10000 / CONCENTRATION_CONVERSION_FACTOR # 10 mM
        for pool_id, md_ids in self.pool_data.iteritems():
            mds = [self._get_entity(IMoleculeDesign, str(md_id)) \
                   for md_id in md_ids]
            pool = self._create_molecule_design_pool(molecule_designs=mds,
                                 default_stock_concentration=conc)
            pool.id = pool_id
            self.molecule_design_pools.append(pool)

    def __check_result(self):
        pool_cands = self.tool.get_result()
        self.assert_is_not_none(pool_cands)
        self.assert_equal(len(pool_cands), len(self.pool_data))
        pool_ids = []
        for pool_cand in pool_cands:
            self.assert_true(pool_cand.is_completed())
            pool = pool_cand.pool
            for md in pool:
                self.assert_true(pool_cand.has_tube_candidate(md.id))
            pool_ids.append(pool.id)
        self.assert_equal(sorted(pool_ids), sorted(self.pool_data.keys()))

    def test_result(self):
        self.__continue_setup()
        self.__check_result()

    def test_result_exluded_racks(self):
        with RdbContextManager() as session:
            self.excluded_racks = []
            self.__continue_setup()
            missing_pool_id = 287431 # belongs to pool 10315676 (in 1056000)
            query = 'SELECT r.barcode AS rack_barcode ' \
                    'FROM rack r, containment rc, sample s, stock_sample ss ' \
                    'WHERE r.rack_id = rc.holder_id ' \
                    'AND r.rack_type = \'TUBERACK\' ' \
                    'AND rc.held_id = s.container_id ' \
                    'AND ss.sample_id = s.sample_id ' \
                    'AND ss.molecule_design_set_id = %i' % (missing_pool_id)
            result = session.query('rack_barcode').from_statement(query).all()
            for record in result: self.excluded_racks.append(record[0])
            if len(self.excluded_racks) < 1: raise ValueError('no rack found')
            del self.pool_data[1056000]
            self.__check_result()
            self._check_warning_messages('Unable to find valid tubes for ' \
                                         'the following pools: 1056000.')

    def test_invalid_input_values(self):
        self.__continue_setup()
        ori_pools = self.molecule_design_pools
        self.molecule_design_pools = dict()
        self._test_and_expect_errors('The pool list must be a list or ' \
                                     'an InstrumentedSet (obtained: dict).')
        self.molecule_design_pools = [3]
        self._test_and_expect_errors('The molecule design pool must be a ' \
                             'MoleculeDesignPool object (obtained: int).')
        self.molecule_design_pools = []
        self._test_and_expect_errors('The pool list is empty!')
        self.molecule_design_pools = ori_pools
        self.single_design_concentration = -1
        self._test_and_expect_errors('The stock concentration must be a ' \
                                     'positive number (obtained: -1).')
        self.single_design_concentration = 50000
        self.take_out_volume = 0
        self._test_and_expect_errors('The stock take out volume must be a ' \
                                     'positive number (obtained: 0) or None.')
        self.take_out_volume = 1
        self.excluded_racks = {}
        self._test_and_expect_errors('The excluded rack list must be a ' \
                            'list object (obtained: dict)')
        self.excluded_racks = [1]
        self._test_and_expect_errors('The excluded rack must be a ' \
                            'basestring object (obtained: int)')
        self.excluded_racks = None
        self.requested_tubes = {}
        self._test_and_expect_errors('The requested tube list must be a ' \
                            'list object (obtained: dict)')
        self.requested_tubes = [1]
        self._test_and_expect_errors('The requested tube must be a ' \
                            'basestring object (obtained: int)')

    def test_take_out_volume(self):
        self.take_out_volume = 500
        self.__continue_setup()
        self._test_and_expect_errors('Did not find any candidate!')
