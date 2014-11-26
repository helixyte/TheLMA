"""
Tests for tools involved the execution of pool stock sample creation worklists.

AAB
"""
from thelma.automation.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.iso.base import StockRackLayout
from thelma.automation.tools.iso.base import StockRackPosition
from thelma.automation.tools.iso.poolcreation import get_executor
from thelma.automation.tools.iso.poolcreation.base \
    import SingleDesignStockRackLayout
from thelma.automation.tools.iso.poolcreation.base import LABELS
from thelma.automation.tools.iso.poolcreation.execution \
    import StockSampleCreationIsoExecutor
from thelma.automation.tools.iso.poolcreation.execution \
    import StockSampleCreationStockTransferReporter
from thelma.automation.tools.iso.poolcreation.execution \
    import _StockSampleCreationStockLogFileWriter
from thelma.automation.tools.iso.tracreporting import IsoStockTransferReporter
from thelma.automation.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.utils.layouts import TransferTarget
from thelma.entities.iso import ISO_STATUS
from thelma.entities.liquidtransfer import TRANSFER_TYPES
from thelma.entities.racklayout import RackLayout
from thelma.entities.utils import get_user
from thelma.oldtests.tools.iso.poolcreation.utils \
    import StockSampleCreationTestCase3
from thelma.oldtests.tools.iso.poolcreation.utils import SSC_TEST_DATA
from thelma.oldtests.tools.tooltestingutils import FileCreatorTestCase


class _StockSampleCreationExecutorBaseTestCase(StockSampleCreationTestCase3):

    def set_up(self):
        StockSampleCreationTestCase3.set_up(self)
        self.iso = None
        self.executor_user = get_user('brehm')
        self.create_single_source_rack = False
        self.pool_stock_rack_layout = None
        self.stock_worklist_series = None
        self.stock_rack_layouts = dict()
        self.starting_vol = 50

    def tear_down(self):
        StockSampleCreationTestCase3.tear_down(self)
        del self.iso
        del self.create_single_source_rack
        del self.pool_stock_rack_layout
        del self.stock_worklist_series
        del self.stock_rack_layouts
        del self.starting_vol

    def _continue_setup(self, file_name=None):
        StockSampleCreationTestCase3._continue_setup(self, file_name=file_name)
        self.iso = self.isos[1]
        self._generate_stock_racks()
        self._generate_pool_stock_rack()
        self.stock_worklist_series = self._generate_stock_rack_worklist_series(
                                                self.create_single_source_rack)
        self.__generate_pool_stock_rack_entity()
        if self.create_single_source_rack:
            self.__generate_single_source_stock_rack_entity()
        else:
            self.__generate_source_stock_rack_entities()
        self.__fill_stock_racks()
        self._create_tool()

    def __generate_pool_stock_rack_entity(self):
        self.pool_stock_rack_layout = self._generate_pool_stock_rack_layout()
        rack = self.rack_generator.barcode_map[
                                        SSC_TEST_DATA.POOL_STOCK_RACK_BARCODE]
        self._create_iso_stock_rack(label=SSC_TEST_DATA.POOL_STOCK_RACK_LABEL,
                iso=self.iso, rack=rack,
                rack_layout=self.pool_stock_rack_layout.create_rack_layout(),
                worklist_series=self.stock_worklist_series)

    def __generate_single_source_stock_rack_entity(self):
        layout = SingleDesignStockRackLayout()
        trg_pool_lookup = dict()
        for pool_id, md_ids in SSC_TEST_DATA.POOL_IDS.iteritems():
            for md_id in md_ids:
                trg_pool_lookup[md_id] = pool_id
        trg_pos_lookup = dict()
        for rack_pos, iso_pos in self.iso_layouts[1].iterpositions():
            trg_pos_lookup[iso_pos.molecule_design_pool.id] = rack_pos
        for pos_label, md_id in \
                        SSC_TEST_DATA.STOCK_POSITIONS_SINGLE_RACK.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            trg_pos = SSC_TEST_DATA.get_target_pos_for_single_rack_source_pos(
                                                                    pos_label)
            pool_id = SSC_TEST_DATA.SINGLE_DESIGN_POOL_IDS[md_id]
            pool = self._get_pool(pool_id)
            barcode = SSC_TEST_DATA.get_tube_barcode_for_pool(pool)
            tt = TransferTarget(trg_pos,
                                SSC_TEST_DATA.SINGLE_DESIGN_TRANSFER_VOLUME,
                                LABELS.ROLE_POOL_STOCK)
            sr_pos = StockRackPosition(rack_position=rack_pos,
                               molecule_design_pool=pool,
                               tube_barcode=barcode, transfer_targets=[tt])
            layout.add_position(sr_pos)
        label = SSC_TEST_DATA.SINGLE_STOCK_RACK_LABEL
        self.stock_rack_layouts[label] = layout
        barcode = self.tube_destination_racks[0]
        rack = self.rack_generator.barcode_map[barcode]
        self._create_iso_stock_rack(label=label, iso=self.iso, rack=rack,
                                    rack_layout=layout.create_rack_layout(),
                                    worklist_series=self.stock_worklist_series)

    def __generate_source_stock_rack_entities(self):
        vol = SSC_TEST_DATA.SINGLE_DESIGN_TRANSFER_VOLUME
        for i in range(len(self.tube_destination_racks)):
            rack_barcode = self.tube_destination_racks[i]
            rack = self.rack_generator.barcode_map[rack_barcode]
            layout = StockRackLayout()
            for pos_label in SSC_TEST_DATA.STOCK_POSITIONS_3_RACKS:
                rack_pos = get_rack_position_from_label(pos_label)
                final_pool_id = SSC_TEST_DATA.ISO_LAYOUT_DATA[pos_label]
                md_ids = SSC_TEST_DATA.POOL_IDS[final_pool_id]
                md_id = md_ids[i]
                pool_id = SSC_TEST_DATA.SINGLE_DESIGN_POOL_IDS[md_id]
                pool = self._get_pool(pool_id)
                tt = TransferTarget(rack_position=rack_pos, transfer_volume=vol,
                                    target_rack_marker=LABELS.ROLE_POOL_STOCK)
                tube_barcode = SSC_TEST_DATA.get_tube_barcode_for_pool(pool)
                sr_pos = StockRackPosition(rack_position=rack_pos,
                        molecule_design_pool=pool, tube_barcode=tube_barcode,
                        transfer_targets=[tt])
                layout.add_position(sr_pos)
            stock_rack_label = SSC_TEST_DATA.TUBE_DESTINATION_RACKS[
                                                                rack_barcode]
            self.stock_rack_layouts[stock_rack_label] = layout
            self._create_iso_stock_rack(label=stock_rack_label, iso=self.iso,
                            rack_layout=layout.create_rack_layout(), rack=rack,
                            worklist_series=self.stock_worklist_series)

    def __fill_stock_racks(self):
        target_conc = 50000
        for stock_rack in self.iso.iso_stock_racks:
            if stock_rack.label == SSC_TEST_DATA.POOL_STOCK_RACK_LABEL:
                continue
            layout = self.stock_rack_layouts[stock_rack.label]
            rack = stock_rack.rack
            for rack_pos, sr_pos in layout.iterpositions():
                pool = sr_pos.molecule_design_pool
                tube = self.tube_generator.create_tube(rack=rack, pool=pool,
                                                       rack_pos=rack_pos)
                self._create_test_sample(container=tube, pool=pool,
                             volume=self.starting_vol, target_conc=target_conc,
                             is_stock_sample=True)

    def _create_executor(self):
        return get_executor(iso=self.iso, user=self.executor_user)


class StockSampleCreationExecutorTestCase(
                                    _StockSampleCreationExecutorBaseTestCase):

    def _create_tool(self):
        self.tool = StockSampleCreationIsoExecutor(iso=self.iso,
                                                user=self.executor_user)

    def _test_and_expect_errors(self, msg=None):
        _StockSampleCreationExecutorBaseTestCase._test_and_expect_errors(self,
                                                                    msg=msg)
        self.assert_is_none(self.tool.get_stock_sample_creation_layout())
        self.assert_is_none(self.tool.get_executed_stock_worklists())

    def __check_result(self):
        iso = self.tool.get_result()
        self.assert_is_not_none(iso)
        self.assert_equal(iso.status, ISO_STATUS.DONE) #pylint: disable=E1103
        self.__check_worklists()
        self.__check_racks()

    def __check_worklists(self):
        for worklist in self.stock_worklist_series:
            self.assert_equal(worklist.index, 0)
            self.assert_equal(worklist.label,
                              SSC_TEST_DATA.STOCK_TRANSFER_WORKLIST_LABEL)
            ews = worklist.executed_worklists
            self.__check_executed_stock_worklists(ews)
        ews = self.tool.get_executed_stock_worklists()
        self.__check_executed_stock_worklists(ews)
        ir_series = self.iso_request.worklist_series
        self.__check_iso_request_worklist(ir_series)

    def __check_executed_stock_worklists(self, executed_worklists):
        if self.create_single_source_rack:
            num_execs = 1
            num_elts = SSC_TEST_DATA.NUMBER_POOLS_11 * self.number_designs
        else:
            num_execs = 3
            num_elts = SSC_TEST_DATA.NUMBER_POOLS_11
        self.assert_equal(len(executed_worklists), num_execs)
        for ew in executed_worklists:
            self.assert_equal(len(ew.executed_liquid_transfers), num_elts)
            src_tubes = []
            trg_tubes = set()
            rack_barcode = None
            for elt in ew:
                rack_barcode = elt.source_container.location.rack.barcode
                self._check_executed_transfer(elt,
                                              TRANSFER_TYPES.SAMPLE_TRANSFER)
                src_tubes.append(str(elt.source_container.barcode))
                trg_tubes.add(str(elt.target_container.barcode))
            exp_trg_tubes = sorted(
                        SSC_TEST_DATA.get_all_pool_stock_rack_tube_barcodes())
            self.assert_equal(sorted(list(trg_tubes)), exp_trg_tubes)
            exp_src_tubes = sorted(SSC_TEST_DATA.get_all_source_tube_barcodes(
                       rack_barcode, self.create_single_source_rack))
            self.assert_equal(sorted(src_tubes), exp_src_tubes)

    def __check_iso_request_worklist(self, worklist_series):
        worklist = worklist_series.get_worklist_for_index(0)
        ews = worklist.executed_worklists
        self.assert_equal(len(ews), 1)
        ew = ews[0]
        self.assert_equal(len(ew.executed_liquid_transfers),
                          SSC_TEST_DATA.NUMBER_POOLS_11)
        target_tubes = []
        for elt in ew:
            self._check_executed_transfer(elt, TRANSFER_TYPES.SAMPLE_DILUTION)
            target_tubes.append(str(elt.target_container.barcode))
            self.assert_equal(elt.reservoir_specs.name,
                              RESERVOIR_SPECS_NAMES.FALCON_MANUAL)
        exp_trg_tubes = SSC_TEST_DATA.get_all_pool_stock_rack_tube_barcodes()
        self.assert_equal(sorted(target_tubes), sorted(exp_trg_tubes))

    def __check_racks(self):
        for isr in self.iso.iso_stock_racks:
            rack = isr.rack
            if rack.barcode == SSC_TEST_DATA.POOL_STOCK_RACK_BARCODE:
                self.__check_pool_stock_rack(rack)
            else:
                self.__check_source_rack(isr)

    def __check_pool_stock_rack(self, rack):
        positions = []
        self.assert_equal(rack.status.name, ITEM_STATUS_NAMES.MANAGED)
        conc = self.iso_request.stock_concentration \
                * CONCENTRATION_CONVERSION_FACTOR / self.number_designs
        exp_vol = self.iso_request.stock_volume * VOLUME_CONVERSION_FACTOR
        for tube in rack.containers:
            pos_label = tube.location.position.label.lower()
            positions.append(pos_label)
            exp_pool_id = SSC_TEST_DATA.ISO_LAYOUT_DATA[pos_label]
            sample = tube.sample
            self.assert_is_not_none(sample)
            sample_info = 'position %s in pool stock rack' % (pos_label)
            self._compare_sample_volume(sample, exp_vol, sample_info)
            self.assert_equal(sample.molecule_design_pool.id, exp_pool_id)
            self._compare_sample_and_pool(sample, sample.molecule_design_pool,
                                          conc, sample_info)
        self.assert_equal(sorted(positions),
                          sorted(SSC_TEST_DATA.ISO_LAYOUT_DATA.keys()))

    def __check_source_rack(self, isr):
        layout = self.stock_rack_layouts[isr.label]
        rack = isr.rack
        self.assert_equal(rack.status.name, ITEM_STATUS_NAMES.MANAGED)
        exp_vol = self.starting_vol \
                   - SSC_TEST_DATA.SINGLE_DESIGN_TRANSFER_VOLUME
        positions = []
        conc = 50000
        for tube in rack.containers:
            rack_pos = tube.location.position
            pos_label = rack_pos.label.lower()
            positions.append(rack_pos)
            sr_pos = layout.get_working_position(rack_pos)
            sample_info = 'position %s in stock rack %s' % (pos_label,
                                                            isr.label)
            if sr_pos is None:
                msg = 'Unexpected tube in position %s' % (sample_info)
                raise AssertionError(msg)
            exp_pool = sr_pos.molecule_design_pool
            sample = tube.sample
            self.assert_is_not_none(sample)
            self._compare_sample_volume(sample, exp_vol, sample_info)
            self.assert_equal(sample.molecule_design_pool, exp_pool)
            self._compare_sample_and_pool(sample, sample.molecule_design_pool,
                                          conc, sample_info)
        self.assert_equal(sorted(positions), sorted(layout.get_positions()))

    def __get_pool_stock_rack(self):
        for isr in self.iso.iso_stock_racks:
            if isr.label == SSC_TEST_DATA.POOL_STOCK_RACK_LABEL:
                return isr

    def test_result_cybio(self):
        self._continue_setup()
        self.__check_result()

    def test_result_biomek(self):
        self.create_single_source_rack = True
        self._continue_setup()
        self.__check_result()

    def test_invalid_input_values(self):
        self._continue_setup()
        ori_iso = self.iso
        self.iso = self._create_lab_iso()
        self._test_and_expect_errors('The entity must be a ' \
                        'StockSampleCreationIso object (obtained: LabIso).')
        self.iso = ori_iso
        self.iso.status = ISO_STATUS.IN_PROGRESS
        self._test_and_expect_errors('Unexpected ISO status: "in_progress"')
        self.iso.status = ISO_STATUS.DONE
        self.executor_user = self.executor_user.username
        self._test_and_expect_errors('The user must be a User object')

    def test_iso_layout_conversion_error(self):
        self._continue_setup()
        self.iso.rack_layout = RackLayout()
        self._test_and_expect_errors('Error when trying to convert stock ' \
                                     'sample creation ISO layout.')

    def test_label_parsing_error(self):
        self._continue_setup()
        for isr in self.iso.iso_stock_racks:
            isr.label = 'invalid'
            break
        self._test_and_expect_errors('Error when trying to parse stock rack ' \
                                     'label "invalid": list index out of range')

    def test_several_pool_stock_racks(self):
        self._continue_setup()
        for isr in self.iso.iso_stock_racks:
            if isr.label == SSC_TEST_DATA.POOL_STOCK_RACK_LABEL: continue
            isr.label = SSC_TEST_DATA.POOL_STOCK_RACK_LABEL
            break
        self._test_and_expect_errors('There are several pool stock racks for ' \
                                     'this ISO!')

    def test_unexpected_number_iso_stock_racks(self):
        self._continue_setup()
        self.iso_request.number_designs = 4
        self._test_and_expect_errors('There is an unexpected number of stock ' \
                    'racks attached to this ISO (4). There should be 5 or 2!')

    def test_no_pool_stock_rack(self):
        self.create_single_source_rack = True
        self._continue_setup()
        isr = self.__get_pool_stock_rack()
        isr.label = SSC_TEST_DATA.TUBE_DESTINATION_RACKS[
                                                self.tube_destination_racks[1]]
        self._test_and_expect_errors('There is no pool stock rack for ' \
                                     'this ISO!')

    def test_unexpected_worklist_series_length(self):
        self._continue_setup()
        wl = self._create_planned_worklist()
        self.stock_worklist_series.add_worklist(1, wl)
        self._test_and_expect_errors('The stock rack worklist series has an ' \
                                     'unexpected length (2 instead of 1)!')

    def test_additional_tube_in_pool_stock_rack(self):
        self._continue_setup()
        pool = self._get_pool(1056000)
        rack_pos = get_rack_position_from_label('g8')
        isr = self.__get_pool_stock_rack()
        self.tube_generator.create_tube(isr.rack, rack_pos, pool)
        self._test_and_expect_errors('There are unexpected tubes in the pool ' \
                'stock rack (09999999): 1001056000 (G8). Please remove ' \
                'them and try again.')

    def test_non_empty_tube_in_pool_stock_rack(self):
        self._continue_setup()
        isr = self.__get_pool_stock_rack()
        for tube in isr.rack.containers:
            tube.make_sample(1)
            break
        self._test_and_expect_errors('The following tubes in the pool stock ' \
                'rack (09999999) are not empty: 1001059776 (A2). Please ' \
                'replace them by empty tubes and try again.')

    def test_missing_tube_in_pool_stock_rack(self):
        self._continue_setup()
        rack_pos = get_rack_position_from_label('a1')
        self.pool_stock_rack_layout.del_position(rack_pos)
        isr = self.__get_pool_stock_rack()
        isr.rack_layout = self.pool_stock_rack_layout.create_rack_layout()
        self._test_and_expect_errors('There are unexpected tubes in the pool ' \
                'stock rack (09999999): 1001063102 (A1). Please remove them ' \
                'and try again.')

    def test_stock_rack_conversion_error_cybio(self):
        self._continue_setup()
        label = None
        barcode = None
        for isr in self.iso.iso_stock_racks:
            if isr.label == SSC_TEST_DATA.POOL_STOCK_RACK_LABEL: continue
            isr.rack_layout = RackLayout()
            label = isr.label
            barcode = isr.rack.barcode
            break
        rack_name = '%s (%s)' % (barcode, label)
        self._test_and_expect_errors('Error when trying to convert stock ' \
                                     'rack layout for rack %s!' % (rack_name))
        self._check_error_messages('Stock Rack Layout Converter')

    def test_stock_rack_conversion_error_biomek(self):
        self.create_single_source_rack = True
        self._continue_setup()
        for isr in self.iso.iso_stock_racks:
            if isr.label == SSC_TEST_DATA.POOL_STOCK_RACK_LABEL: continue
            isr.rack_layout = RackLayout()
            break
        self._test_and_expect_errors('Error when trying to convert stock ' \
                         'rack layout for rack 09999981 (ssgen_test_01_sds)!')
        self._check_error_messages('Single Design Stock Rack Layout Converter')

    def test_verification_failure(self):
        self.starting_vol = 1
        self._continue_setup()
        self._test_and_expect_errors('The following stock racks are not ' \
            'compatible: 09999981 (ssgen_test_01_sds#1), ' \
            '09999982 (ssgen_test_01_sds#2), 09999983 (ssgen_test_01_sds#3)')

    def test_previous_execution(self):
        self._continue_setup()
        wl = self.stock_worklist_series.get_worklist_for_index(0)
        self._create_executed_worklist(planned_worklist=wl)
        self._test_and_expect_errors('The stock transfer has already been ' \
                                     'executed before.')


class StockSampleCreationStockLogFileWriterTestCase(FileCreatorTestCase,
                                _StockSampleCreationExecutorBaseTestCase):

    def set_up(self):
        _StockSampleCreationExecutorBaseTestCase.set_up(self)
        self.WL_PATH = SSC_TEST_DATA.WORKLIST_FILE_PATH
        self.ssc_layout = None
        self.executed_worklists = None

    def tear_down(self):
        _StockSampleCreationExecutorBaseTestCase.tear_down(self)
        del self.ssc_layout
        del self.executed_worklists

    def _create_tool(self):
        self.tool = \
            _StockSampleCreationStockLogFileWriter(self.ssc_layout,
                                                   self.executed_worklists)

    def _continue_setup(self, file_name=None):
        _StockSampleCreationExecutorBaseTestCase._continue_setup(self,
                                                            file_name=file_name)
        executor = self._create_executor()
        executor.run()
        self.assert_false(executor.has_errors())
        self.ssc_layout = executor.get_stock_sample_creation_layout()
        self.executed_worklists = executor.get_executed_stock_worklists()
        self._create_tool()

    def __check_result(self):
        self._continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, SSC_TEST_DATA.FILE_NAME_LOG)

    def test_result_cybio(self):
        self.__check_result()

    def test_result_biomek(self):
        self.create_single_source_rack = True
        self.__check_result()

    def test_invalid_input_values(self):
        self._continue_setup()
        ori_layout = self.ssc_layout
        self.ssc_layout = None
        self._test_and_expect_errors('The stock sample creation layout must ' \
                'be a StockSampleCreationLayout object (obtained: NoneType).')
        self.ssc_layout = ori_layout
        self.executed_worklists = dict()
        self._test_and_expect_errors('The executed_worklist list must be a ' \
                                     'list object (obtained: dict).')
        self.executed_worklists = []
        self._test_and_expect_errors('The executed_worklist list is empty!')
        self.executed_worklists = [1]
        self._test_and_expect_errors('The executed_worklist must be a ' \
                                     'ExecutedWorklist object (obtained: int).')

    def test_more_than_one_source_design(self):
        self._continue_setup()
        for isr in self.iso.iso_stock_racks:
            if isr.label == SSC_TEST_DATA.POOL_STOCK_RACK_LABEL: continue
            for tube in isr.rack.containers:
                self._create_sample_molecule(sample=tube.sample)
                break
        self._test_and_expect_errors('Some source container contain more ' \
                                     'than one molecule design')

    def test_unknown_target_pool(self):
        self._continue_setup()
        rack_pos = get_rack_position_from_label('a1')
        self.ssc_layout.del_position(rack_pos)
        self._test_and_expect_errors('Could not find molecule design pools ' \
                    'for the following target positions: A1 (rack 09999999).')


class StockSampleCreationStockTransferReporterTestCase(FileCreatorTestCase,
                                    _StockSampleCreationExecutorBaseTestCase):

    def set_up(self):
        _StockSampleCreationExecutorBaseTestCase.set_up(self)
        self.WL_PATH = SSC_TEST_DATA.WORKLIST_FILE_PATH
        self.create_test_tickets = True
        self.executor = None

    def tear_down(self):
        _StockSampleCreationExecutorBaseTestCase.tear_down(self)
        del self.executor

    def _continue_setup(self, file_name=None):
        _StockSampleCreationExecutorBaseTestCase._continue_setup(self,
                                                  file_name=file_name)
        self.executor = self._create_executor()
        self.executor.run()
        self.assert_false(self.executor.has_errors())
        self._create_tool()

    def _create_tool(self):
        self.tool = StockSampleCreationStockTransferReporter(
                                                        executor=self.executor)

    def __check_result(self):
        self._continue_setup()
        self.tool.run()
        self.assert_true(self.tool.transaction_completed())
        tool_stream, comment = self.tool.return_value # unpack non-sequence pylint:disable=W0633
        self._compare_csv_file_stream(tool_stream, SSC_TEST_DATA.FILE_NAME_LOG)
        exp_comment = IsoStockTransferReporter.BASE_COMMENT \
                      % ('Michael Brehm', 'stock_transfer_ssgen_test_01.csv',
                         'ssgen_test_01', 'new pooled stock samples',
                         "'''New pool stock rack:''' 09999999")
#        exp_comment = 'A stock transfer has been executed by Michael Brehm ' \
#          '(see file: attachment:stock_transfer_ssgen_test_01.csv).[[br]]' \
#          'Entity: ssgen_test_01 [[br]]'\
#          'Type: new pooled stock samples[[br]]' \
#          'New pool stock rack: 09999999.[[br]]'
        self.assert_equal(comment, exp_comment)

    def test_result_cybio(self):
        self.__check_result()

    def test_result_biomek(self):
        self.create_single_source_rack = True
        self.__check_result()

    def test_invalid_input_values(self):
        self._continue_setup()
        ori_executor = self.executor
        self.executor = None
        self._test_and_expect_errors('The executor must be a ' \
                    'StockSampleCreationIsoExecutor object (obtained: NoneType).')
        self.executor = ori_executor
        self.executor.add_error('test')
        self._test_and_expect_errors('The executor has errors!')
        self.executor.reset()
        self._test_and_expect_errors('The executor has not run yet!')

    def test_ticket_error(self):
        self._continue_setup()
        self.iso.ticket_number += 1
        self._test_and_expect_errors()
