"""
Tests for classes that deal with the final tube picking for lab ISOs.

AAB
"""
from everest.repositories.rdb.testing import RdbContextManager
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.iso.lab.base import FinalLabIsoPosition
from thelma.automation.tools.iso.lab.stockrack.base import StockTubeContainer
from thelma.automation.tools.iso.lab.stockrack.tubepicking \
    import LabIsoXL20TubePicker
from thelma.automation.tools.stock.base import STOCK_DEAD_VOLUME
from thelma.automation.tools.stock.tubepicking import MultiPoolQuery
from thelma.automation.tools.stock.tubepicking import SinglePoolQuery
from thelma.automation.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.utils.layouts import FIXED_POSITION_TYPE
from thelma.interfaces import ITube
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase

class LabIsoXL20TubePickerTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.log = TestingLog()
        self.session = None
        self.stock_tube_containers = dict()
        self.excluded_racks = []
        self.requested_tubes = []
        # pool ID - pos label, transfer volume, expected tube barcode,
        # expected rack barcode, tube pos, actual tube barcode, actual rack
        # barcode
        self.stock_tube_data = {
            205201 : ['a1', 5, '10001', '09999999', None, None, None],
            330001 : ['b1', 1, '10002', '09999999', None, None, None]}
        self.confirm_tubes = True
        self.tube_map = dict()
        self.rack_map = dict()

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.session
        del self.stock_tube_containers
        del self.excluded_racks
        del self.requested_tubes
        del self.stock_tube_data
        del self.confirm_tubes
        del self.tube_map
        del self.rack_map

    def _create_tool(self):
        self.tool = LabIsoXL20TubePicker(log=self.log,
                            stock_tube_containers=self.stock_tube_containers,
                            excluded_racks=self.excluded_racks,
                            requested_tubes=self.requested_tubes)

    def _continue_setup(self):
        self.__create_stock_tube_containers()
        self._create_tool()

    def __create_stock_tube_containers(self):
        for pool_id, pos_data in self.stock_tube_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_data[0])
            pool = self._get_pool(pool_id)
            conc = pool.default_stock_concentration \
                   * CONCENTRATION_CONVERSION_FACTOR
            self.__get_stock_tube_and_rack_data(pool_id, conc, pos_data[1])
            fp = FinalLabIsoPosition(rack_position=rack_pos,
                             molecule_design_pool=pool,
                             position_type=FIXED_POSITION_TYPE,
                             concentration=conc, volume=pos_data[1],
                             stock_tube_barcode=pos_data[2],
                             stock_rack_barcode=pos_data[3],
                             stock_rack_marker='s#1')
            stc = StockTubeContainer.from_plate_position(fp,
                                                final_position_copy_number=1)
            self.stock_tube_containers[pool] = stc

    def __get_stock_tube_and_rack_data(self, pool_id, conc, vol):
        pos_data = self.stock_tube_data[pool_id]
        if not self.confirm_tubes:
            return pos_data[2], pos_data[3]
        required_vol = STOCK_DEAD_VOLUME + vol
        query = SinglePoolQuery(pool_id, conc, minimum_volume=required_vol)
        query.run(self.session)
        candidates = query.get_query_results()
        if len(candidates) < 1:
            raise ValueError('No candidates for pool %i!' % (pool_id))
        cand = candidates[0]
        tube_barcode = cand.tube_barcode
        rack_barcode = cand.rack_barcode
        pos_data[2] = tube_barcode
        pos_data[3] = rack_barcode
        pos_data[4] = cand.rack_position
        pos_data[5] = tube_barcode
        pos_data[6] = rack_barcode

    def _test_and_expect_errors(self, msg=None):
        ToolsAndUtilsTestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_tube_map())
        self.assert_is_none(self.tool.get_missing_pools())

    def __check_result(self):
        for stc in self.stock_tube_containers.values():
            self.assert_is_none(stc.tube_candidate)
        updated_containers = self.tool.get_result()
        self.assert_is_not_none(updated_containers)
        self.assert_equal(len(updated_containers), len(self.stock_tube_data))
        for pool_id, pos_data in self.stock_tube_data.iteritems():
            pool = self._get_pool(pool_id)
            container = updated_containers[pool]
            candidate = container.tube_candidate
            self.assert_is_not_none(candidate)
            self.assert_true(candidate.volume >= pos_data[1])
            if not self.confirm_tubes:
                self.assert_is_not_none(candidate.tube_barcode)
                self.assert_is_not_none(candidate.rack_barcode)
            else:
                self.assert_equal(candidate.tube_barcode, pos_data[2])
                self.assert_equal(candidate.rack_barcode, pos_data[3])
            self.assert_equal(candidate.get_pool().id, pool_id)

    def test_result_confirm_tubes(self):
        with RdbContextManager() as session:
            self.session = session
            self._continue_setup()
            self.__check_result()

    def test_result_find_new_tubes(self):
        self.confirm_tubes = False
        with RdbContextManager() as session:
            self.session = session
            self._continue_setup()
            self.__check_result()
            self._check_warning_messages('The following scheduled tubes have ' \
                    'not been found in the DB: 10001, 10002')

    def test_result_excluded_racks(self):
        with RdbContextManager() as session:
            self.session = session
            self._continue_setup()
            missing_pool_id = sorted(self.stock_tube_data.keys())[0]
            # get racks to be excluded
            query = 'SELECT r.barcode AS rack_barcode ' \
                    'FROM rack r, containment rc, sample s, stock_sample ss ' \
                    'WHERE r.rack_id = rc.holder_id ' \
                    'AND r.rack_type = \'TUBERACK\' ' \
                    'AND rc.held_id = s.container_id ' \
                    'AND ss.sample_id = s.sample_id ' \
                    'AND ss.molecule_design_set_id = %i' % (missing_pool_id)
            result = self.session.query('rack_barcode').from_statement(query).all()
            for record in result: self.excluded_racks.append(record[0])
            if len(self.excluded_racks) < 1: raise ValueError('no rack found')
            containers = self.tool.get_result()
            self.assert_is_not_none(containers)
            for pool, stc in containers.iteritems():
                pool_id = pool.id
                if pool_id == missing_pool_id:
                    self.assert_is_none(stc.tube_candidate)
                else:
                    self.assert_is_not_none(stc.tube_candidate)
            self._check_warning_messages('Some scheduled tubes had to be ' \
                'replaced or removed because their current racks have been ' \
                'excluded: 205201 (replaced by: could not be replaced, ' \
                'excluded tubes:')
            missing_pools = self.tool.get_missing_pools()
            self.assert_equal(len(missing_pools), 1)
            self.assert_equal(missing_pools[0].id, missing_pool_id)

    def test_requested_tubes(self):
        self.confirm_tubes = False
        with RdbContextManager() as session:
            self.session = session
            self._continue_setup()
            pool_id = sorted(self.stock_tube_data.keys())[0]
            pool = self._get_pool(pool_id)
            conc = pool.default_stock_concentration \
                   * CONCENTRATION_CONVERSION_FACTOR
            vol = self.stock_tube_data[pool_id][1] + STOCK_DEAD_VOLUME
            query = SinglePoolQuery(pool_id=pool_id, concentration=conc,
                                    minimum_volume=vol)
            query.run(session)
            candidates = query.get_query_results()
            candidate = candidates[0]
            self.requested_tubes.append(candidate.tube_barcode)
            containers = self.tool.get_result()
            self.assert_is_not_none(containers)
            for pool, stc in containers.iteritems():
                if pool.id == pool_id:
                    self.assert_equal(stc.tube_candidate.tube_barcode,
                                      self.requested_tubes[0])
            self._check_warning_messages('Some requested tubes differ from ' \
                'the ones scheduled during ISO generation (1 molecule design ' \
                'pool(s)). The scheduled tubes are replaced by the ' \
                'requested ones. Details: MD pool: 205201, requested: ')

    def test_more_requested_tubes_than_pools(self):
        self.requested_tubes = ['10001', '10002', '10003', '10004']
        self.confirm_tubes = False
        with RdbContextManager() as session:
            self.session = session
            self._continue_setup()
            containers = self.tool.get_result()
            self.assert_is_not_none(containers)
            self._check_warning_messages('The following requested tubes ' \
                'have not been found in the DB: 10001, 10002, 10003, 10004.')
            self._check_warning_messages('There are more requested tubes (4) ' \
                                         'than molecule design pool IDs (2)!')

    def test_unexpected_pools(self):
        with RdbContextManager() as session:
            self.session = session
            self._continue_setup()
            pool_ids = (205205, 205206)
            query = MultiPoolQuery(pool_ids, concentration=50000,
                                   minimum_volume=6)
            query.run(session)
            candidates = query.get_query_results()
            for candidate_list in candidates.values():
                for candidate in candidate_list:
                    self.requested_tubes.append(candidate.tube_barcode)
            containers = self.tool.get_result()
            self.assert_is_not_none(containers)
            self._check_warning_messages('The following tube you have ' \
                'requested have samples for pool that are not processed ' \
                'in this step')

    def test_insufficent_volume(self):
        with RdbContextManager() as session:
            self.session = session
            self._continue_setup()
            container = self.stock_tube_containers.values()[0]
            fp = container.get_all_target_positions()[0]
            fp.volume = 500
            containers = self.tool.get_result()
            self.assert_is_not_none(containers)
            self._check_warning_messages('Some scheduled tubes had to be ' \
                    'replaced because their volume was not sufficient anymore')

    def test_concentration_mismatch(self):
        with RdbContextManager() as session:
            self.session = session
            self._continue_setup()
            pool_id = sorted(self.stock_tube_data.keys())[0]
            pool = self._get_pool(pool_id)
            conc = pool.default_stock_concentration \
                   * CONCENTRATION_CONVERSION_FACTOR
            vol = self.stock_tube_data[pool_id][1] + STOCK_DEAD_VOLUME
            query = SinglePoolQuery(pool_id=pool_id, concentration=conc,
                                    minimum_volume=vol)
            query.run(session)
            candidates = query.get_query_results()
            candidate = candidates[0]
            tube_barcode = candidate.tube_barcode
            self.requested_tubes.append(tube_barcode)
            tube = self._get_entity(ITube, tube_barcode)
            self.assert_is_not_none(tube)
            tube.sample.concentration = (2 * tube.sample.concentration)
            containers = self.tool.get_result()
            self.assert_is_not_none(containers)
            self._check_warning_messages('The following scheduled tubes have ' \
                    'been ignored because they concentration does not match ' \
                    'the expected stock concentration')

    def test_invalid_input_values(self):
        with RdbContextManager() as session:
            self.session = session
            self._continue_setup()
            ori_containers = self.stock_tube_containers
            self.stock_tube_containers = []
            self._test_and_expect_errors('The stock tube container map must ' \
                                'be a dict object (obtained: list)')
            self.stock_tube_containers = {1 : ori_containers.values()[0]}
            self._test_and_expect_errors('The pool must be a ' \
                                'MoleculeDesignPool object (obtained: int)')
            self.stock_tube_containers = {ori_containers.keys()[0] : 1}
            self._test_and_expect_errors('The stock tube container must be a ' \
                                'StockTubeContainer object (obtained: int)')
            self.stock_tube_containers = ori_containers
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
