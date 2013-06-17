"""
Tests for stock transfer worklists generators (these deal transfer of liquids
from a stock tube to a plate).

AAB
"""
from thelma.automation.tools.iso.prep_utils import IsoControlRackPosition
from thelma.automation.tools.iso.prep_utils import PrepIsoAssociationData
from thelma.automation.tools.iso.prep_utils import RequestedStockSample
from thelma.automation.tools.iso.stockworklist \
    import StockTransferWorklistGenerator384Controls
from thelma.automation.tools.iso.stockworklist \
    import StockTransferWorklistGenerator384Samples
from thelma.automation.tools.iso.stockworklist \
    import StockTransferWorklistGenerator384Single
from thelma.automation.tools.iso.stockworklist \
    import StockTransferWorklistGenerator96
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.utils.base import TransferTarget
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.utils.racksector import QuadrantIterator
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.tests.tools.iso.test_stocktransfer \
    import IsoControlStockRackTestCase
from thelma.tests.tools.iso.test_stocktransfer import StockTaking384TestCase
from thelma.tests.tools.iso.test_stocktransfer import StockTaking96TestCase


class IsoSampleStockRack96WorklistGeneratorTestCase(StockTaking96TestCase):

    def set_up(self):
        StockTaking96TestCase.set_up(self)
        #: rack position, expected volume in ul
        self.result_data = dict(A1=10.2, B1=9, C1=7.2)

    def tear_down(self):
        StockTaking96TestCase.tear_down(self)
        del self.result_data

    def _create_tool(self):
        self.tool = StockTransferWorklistGenerator96(
                            working_layout=self.preparation_layout,
                            label=self.iso_label, log=self.log)

    def _continue_setup(self):
        self._create_prep_layout()
        self._create_tool()

    def __check_result(self):
        worklist = self.tool.get_result()
        self.assert_is_not_none(worklist)
        self.assert_equal(len(worklist.executed_worklists), 0)
        self.assert_equal(len(worklist.planned_transfers),
                          len(self.result_data))
        expected_label = '%s%s' % (self.iso_label, self.tool.WORKLIST_SUFFIX)
        self.assert_true(self.tool.BIOMEK_MARKER in worklist.label)
        self.assert_equal(worklist.label, expected_label)
        for pct in worklist.planned_transfers:
            self.assert_equal(pct.source_position, pct.target_position)
            self.assert_equal(pct.type, TRANSFER_TYPES.CONTAINER_TRANSFER)
            trg_pos = pct.target_position
            expected_volume = self.result_data[trg_pos.label]
            pct_volume = pct.volume * VOLUME_CONVERSION_FACTOR
            self.assert_equal(expected_volume, pct_volume)

    def test_result(self):
        self._continue_setup()
        self.__check_result()

    def test_result_inactivated_position(self):
        self.inactivate_pos = 'A1'
        self._continue_setup()
        del self.result_data['A1']
        self.__check_result()

    def test_invalid_preparation_layout(self):
        self._continue_setup()
        self.preparation_layout = self.preparation_layout.create_rack_layout()
        self._test_and_expect_errors()

    def test_invalid_label(self):
        self._continue_setup()
        self.iso_label = 123
        self._test_and_expect_errors('The label must be a basestring object')


class IsoSampleStockRack384WorklistGeneratorMultiTestCase(
                                                    StockTaking384TestCase):

    def set_up(self):
        StockTaking384TestCase.set_up(self)
        self.sector_stock_samples = dict()
        # target pos, source pos
        self.sector_data = {0 : dict(A3='A2', C1='B1', C3='B2'),
                            1 : dict(A4='A2', C2='B1', C4='B2'),
                            2 : dict(B1='A1', B3='A2', D1='B1'),
                            3 : dict(B2='A1', B4='A2', D2='B1')}
        self.association_data = None

    def tear_down(self):
        StockTaking384TestCase.tear_down(self)
        del self.sector_stock_samples
        del self.association_data

    def _continue_setup(self, single_stock_rack=False):
        self._create_preparation_layout()
        self._create_association_data()
        self._create_req_stock_samples()
        self._create_tool()

    def _create_tool(self):
        self.tool = StockTransferWorklistGenerator384Samples(
                        preparation_layout=self.preparation_layout,
                        iso_label=self.iso_label, log=self.log,
                        sector_stock_samples=self.sector_stock_samples,
                        floating_stock_concentration=self.stock_concentration,
                        association_data=self.association_data)

    def _create_association_data(self):
        self.association_data = PrepIsoAssociationData(
                    preparation_layout=self.preparation_layout, log=self.log)

    def _create_req_stock_samples(self):
        for i in range(4): self.sector_stock_samples[i] = []
        quadrant_iter = QuadrantIterator(number_sectors=4)
        for quadrant_pps in quadrant_iter.get_all_quadrants(
                                working_layout=self.preparation_layout):
            for sector_index, pp in quadrant_pps.iteritems():
                if pp is None: continue
                if pp.is_inactivated or not pp.is_floating: continue
                if not pp.parent_well is None: continue
                rss = RequestedStockSample.from_prep_pos(pp)
                self.sector_stock_samples[sector_index].append(rss)

    def __check_result(self):
        worklist_map = self.tool.get_result()
        self.assert_is_not_none(worklist_map)
        self.assert_equal(len(worklist_map), len(self.sector_data))
        for sector_index, worklist in worklist_map.iteritems():
            expected_label = '%s_Q%i' % (self.iso_label, sector_index + 1)
            self.assert_equal(worklist.label, expected_label)
            self.assert_equal(len(worklist.executed_worklists), 0)
            sector_data = self.sector_data[sector_index]
            self.assert_equal(len(worklist.planned_transfers), len(sector_data))
            for pct in worklist.planned_transfers:
                self.assert_equal(pct.type, TRANSFER_TYPES.CONTAINER_TRANSFER)
                expected_volume = self.take_out_volume
                pct_volume = pct.volume * VOLUME_CONVERSION_FACTOR
                self.assert_equal(expected_volume, pct_volume)
                trg_pos_label = pct.target_position.label
                exp_src_label = sector_data[trg_pos_label]
                self.assert_equal(exp_src_label, pct.source_position.label)

    def test_result(self):
        self.sector_data = {0 : dict(A3='A2', C1='B1'),
                            1 : dict(A4='A2', C2='B1'),
                            2 : dict(B1='A1', B3='A2', D1='B1'),
                            3 : dict(B2='A1', B4='A2', D2='B1')}
        self._continue_setup()
        self.__check_result()

    def test_result_two_sectors(self):
        sector_info_0 = self.sector_data[0]
        del sector_info_0['C3']
        self._continue_setup()
        del self.sector_stock_samples[1]
        del self.sector_stock_samples[3]
        del self.sector_data[1]
        del self.sector_data[3]
        self.__check_result()

    def test_result_several_sectors(self):
        self.position_data = dict(
                # first quadrant
                A1=(205200, 10000, None, 45, 'fixed'),
                A2=(205200, 5000, 'A1', 30, 'fixed'),
                B1=(205203, 10000, None, 45, 'floating'),
                B2=(205203, 5000, 'B1', 30, 'floating'),
                # second quadrant
                A3=(205204, 10000, None, 45, 'floating'),
                A4=(205204, 5000, 'A3', 30, 'floating'),
                B3=(205205, 10000, None, 45, 'floating'),
                B4=(205205, 5000, 'B3', 30, 'floating'),
                # third quadrant
                C1=(205206, 10000, None, 45, 'floating'),
                C2=(205206, 5000, 'C1', 30, 'floating'),
                D1=(205207, 10000, None, 45, 'floating'),
                D2=(205207, 5000, 'D1', 30, 'floating'),
                # fourth quadrant
                C3=(205200, 10000, None, 45, 'fixed'),
                C4=(205200, 5000, 'C3', 30, 'fixed'),
                D3=(205201, 10000, None, 45, 'fixed'),
                D4=(205201, 5000, 'D3', 30, 'fixed'))
        self.sector_data = {0 : dict(A3='A2', C1='B1'),
                            2 : dict(B1='A1', B3='A2', D1='B1')}
        self.take_out_volume = 9
        self._continue_setup()
        self.__check_result()

    def test_result_inactivated_position(self):
        self.sector_data = {0 : dict(A3='A2', C1='B1'),
                            1 : dict(A4='A2', C2='B1'),
                            2 : dict(B3='A2', D1='B1'),
                            3 : dict(B2='A1', B4='A2', D2='B1')}
        self.inactivated_pos = 'B1'
        self._continue_setup()
        self.__check_result()

    def test_invalid_preparation_layout(self):
        self._continue_setup()
        self.preparation_layout = self.preparation_layout.create_rack_layout()
        self._test_and_expect_errors('The preparation plate layout must be a ' \
                                     'PrepIsoLayout object')

    def test_invalid_iso_label(self):
        self._continue_setup()
        self.iso_label = 123
        self._test_and_expect_errors('The ISO label must be a basestring')

    def test_invalid_association_data(self):
        self._continue_setup()
        self.association_data = None
        self._test_and_expect_errors('The association data must be a ' \
                                     'PrepIsoAssociationData object')

    def test_invalid_stock_concentration(self):
        self._continue_setup()
        self.stock_concentration = -2
        self._test_and_expect_errors('The stock concentration must be a ' \
                                     'positive integer')
        self.stock_concentration = 0
        self._test_and_expect_errors('The stock concentration must be a ' \
                                     'positive integer')

    def test_invalid_sector_map(self):
        self._continue_setup()
        req_stock_samples = self.sector_stock_samples[0]
        self.sector_stock_samples = []
        self._test_and_expect_errors('The sector stock samples map must be ' \
                                     'a dict')
        self.sector_stock_samples = dict(A1=req_stock_samples)
        self._test_and_expect_errors('The sector index must be a int object')
        self.sector_stock_samples = {0 : set(req_stock_samples)}
        self._test_and_expect_errors('The requested stock samples list must ' \
                                     'be a list')


class IsoSampleStockRack384WorklistGeneratorSingleTestCase(
                                                        StockTaking384TestCase):

    def set_up(self):
        StockTaking384TestCase.set_up(self)
        self.requested_stock_samples = []
        # pool_id, soource pos label
        self.expected_src_positions = {205203 : 'A1', 205212 : 'B1',
                    205204 : 'C1', 205214 : 'D1', 205209 : 'E1', 205210 : 'F1',
                    205205 : 'G1', 205207 : 'H1', 205206 : 'A2', 205208 : 'B2'}


    def tear_down(self):
        StockTaking384TestCase.tear_down(self)
        del self.requested_stock_samples
        del self.expected_src_positions

    def _create_tool(self):
        self.tool = StockTransferWorklistGenerator384Single(log=self.log,
                        iso_label=self.iso_label,
                        requested_stock_samples=self.requested_stock_samples)

    def _continue_setup(self, single_stock_rack=False):
        self._create_preparation_layout()
        self._create_req_stock_samples()
        self._create_tool()

    def _create_req_stock_samples(self):
        for pp in self.preparation_layout.working_positions():
            if not pp.parent_well is None or pp.is_inactivated: continue
            pool_id = pp.molecule_design_pool_id
            if not pool_id in self.floating_pools: continue
            rss = RequestedStockSample.from_prep_pos(prep_pos=pp)
            self.requested_stock_samples.append(rss)

    def __check_result(self):
        worklist = self.tool.get_result()
        self.assert_is_not_none(worklist)
        expected_label = '%s%s' % (self.iso_label, self.tool.WORKLIST_SUFFIX)
        self.assert_equal(expected_label, worklist.label)
        self.assert_equal(len(worklist.executed_worklists), 0)
        self.assert_equal(len(worklist.planned_transfers),
                          len(self.requested_stock_samples))
        self.assert_equal(len(worklist.planned_transfers),
                          len(self.expected_src_positions))
        for rss in self.requested_stock_samples:
            #pylint: disable=E1101
            pool_id = rss.pool.id
            exp_src_pos = self.expected_src_positions[pool_id]
            self.assert_equal(rss.target_position.label, exp_src_pos)
            #pylint: enable=E1101
        for pct in worklist.planned_transfers:
            self.assert_equal(pct.type, TRANSFER_TYPES.CONTAINER_TRANSFER)
            expected_volume = self.take_out_volume
            pct_volume = pct.volume * VOLUME_CONVERSION_FACTOR
            self.assert_equal(expected_volume, pct_volume)
            target_pos = pct.target_position
            self.assert_not_equal(target_pos.label, self.inactivated_pos)
            prep_pos = self.preparation_layout.get_working_position(target_pos)
            self.assert_is_not_none(prep_pos)
            self.assert_false(prep_pos.is_mock)
            source_pos = pct.source_position
            self.assert_true(source_pos.label in
                             self.expected_src_positions.values())

    def test_result(self):
        self._continue_setup()
        self.__check_result()

    def test_result_inactivated_position(self):
        self.inactivated_pos = 'A4' # md ID = 205206
        self.expected_src_positions[205208] = self.expected_src_positions[205206]
        del self.expected_src_positions[205206]
        self._continue_setup()
        self.__check_result()

    def test_invalid_requested_stock_samples(self):
        self._continue_setup()
        self.requested_stock_samples = dict()
        self._test_and_expect_errors('The requested stock samples list must ' \
                                     'be a list object')
        self.requested_stock_samples = [1]
        self._test_and_expect_errors('The requested stock sample must be a ' \
                                     'RequestedStockSample object')

    def test_invalid_iso_label(self):
        self._continue_setup()
        self.iso_label = 123
        self._test_and_expect_errors('The label must be a basestring object')


class IsoControlStockRackWorklistGeneratorTestCase(
                                                IsoControlStockRackTestCase):

    def _create_tool(self):
        self.tool = StockTransferWorklistGenerator384Controls(
                                control_layout=self.control_layout,
                                job_label=self.job_label, log=self.log)

    def _continue_setup(self):
        self._create_control_layout()
        self._create_tool()

    def _create_control_layout(self):
        for pos_label, pos_data in self.md_map.iteritems():
            tts = []
            for target_label in pos_data[1]:
                transfer_volume = self.volume_map[target_label]
                tt = TransferTarget(rack_position=target_label,
                                    transfer_volume=transfer_volume)
                tts.append(tt)
            rack_pos = get_rack_position_from_label(pos_label)
            pool = self._get_pool(pos_data[0])
            control_pos = IsoControlRackPosition(rack_position=rack_pos,
                                molecule_design_pool=pool,
                                transfer_targets=tts)
            self.control_layout.add_position(control_pos)

    def test_result(self):
        self._continue_setup()
        worklist = self.tool.get_result()
        self.assert_is_not_none(worklist)
        self.assert_equal(len(worklist.executed_worklists), 0)
        expected_label = '%s%s' % (self.job_label,
                    StockTransferWorklistGenerator384Controls.WORKLIST_SUFFIX)
        self.assert_equal(worklist.label, expected_label)
        self.assert_equal(len(worklist.planned_transfers), len(self.volume_map))
        for pct in worklist.planned_transfers:
            self.assert_equal(pct.type, TRANSFER_TYPES.CONTAINER_TRANSFER)
            src_pos = pct.source_position
            source_data = self.md_map[src_pos.label]
            target_label = pct.target_position.label
            self.assert_true(target_label in source_data[1])
            expected_volume = self.volume_map[target_label]
            pct_volume = pct.volume * VOLUME_CONVERSION_FACTOR
            self.assert_equal(expected_volume, pct_volume)

    def test_invalid_control_layout(self):
        self._continue_setup()
        self.control_layout = self.control_layout.create_rack_layout()
        self._test_and_expect_errors('The working layout must be a ' \
                                     'IsoControlRackLayout object')
    def test_invalid_label(self):
        self._continue_setup()
        self.job_label = 123
        self._test_and_expect_errors('The label must be a basestring object')
