"""
Tests for tools involved in the worklists generation for stock sample creation
ISOs.

AAB
"""
from thelma.automation.semiconstants import get_pipetting_specs_cybio
from thelma.automation.semiconstants import get_positions_for_shape
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.iso.poolcreation import get_worklist_uploader
from thelma.automation.tools.iso.poolcreation import get_worklist_writer
from thelma.automation.tools.iso.poolcreation.writer import StockSampleCreationInstructionsWriter
from thelma.automation.tools.iso.poolcreation.base \
    import StockSampleCreationLayout
from thelma.automation.tools.iso.poolcreation.base \
    import StockSampleCreationPosition
from thelma.automation.tools.iso.poolcreation.writer \
    import StockSampleCreationIsoLayoutWriter
from thelma.automation.tools.iso.poolcreation.writer \
    import StockSampleCreationIsoWorklistWriter
from thelma.automation.tools.iso.poolcreation.writer \
    import _SingleRackTransferWorklistWriter
from thelma.automation.tools.iso.poolcreation.writer \
    import _StockSampleCreationXL20ReportWriter
from thelma.automation.tools.worklists.tubehandler import TubeTransferData
from thelma.automation.tools.worklists.tubehandler import XL20WorklistWriter
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.models.iso import ISO_STATUS
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.racklayout import RackLayout
from thelma.tests.tools.iso.poolcreation.utils \
    import StockSampleCreationTestCase3
from thelma.tests.tools.iso.poolcreation.utils import SSC_TEST_DATA
from thelma.tests.tools.tooltestingutils import FileComparisonUtils
from thelma.tests.tools.tooltestingutils import FileCreatorTestCase


class StockSampleCreationIsoLayoutWriterTestCase(StockSampleCreationTestCase3,
                                                 FileCreatorTestCase):

    def set_up(self):
        StockSampleCreationTestCase3.set_up(self)
        self.WL_PATH = SSC_TEST_DATA.WORKLIST_FILE_PATH
        self.layout = None

    def tear_down(self):
        StockSampleCreationTestCase3.tear_down(self)
        del self.WL_PATH
        del self.layout

    def _create_tool(self):
        self.tool = StockSampleCreationIsoLayoutWriter(self.layout)

    def _continue_setup(self, file_name=None):
        StockSampleCreationTestCase3._continue_setup(self, file_name=file_name)
        self.layout = self.iso_layouts[1]
        self._create_tool()

    def test_result(self):
        self._continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, 'ssgen_test_01_layout.csv')

    def test_invalid_input_values(self):
        self.layout = 1
        self._test_and_expect_errors('The ISO layout must be a ' \
                        'StockSampleCreationLayout object (obtained: int)')


class _StockSampleCreationWriterTestCase(StockSampleCreationTestCase3,
                                         FileCreatorTestCase):

    def set_up(self):
        StockSampleCreationTestCase3.set_up(self)
        self.WL_PATH = SSC_TEST_DATA.WORKLIST_FILE_PATH
        self.target_rack_barcode = SSC_TEST_DATA.POOL_STOCK_RACK_BARCODE

    def tear_down(self):
        StockSampleCreationTestCase3.tear_down(self)
        del self.WL_PATH
        del self.target_rack_barcode

    def _continue_setup(self, file_name=None):
        StockSampleCreationTestCase3._continue_setup(self, file_name=file_name)
        self._create_tool()

    def _test_invalid_input_values(self):
        self._continue_setup()
        self.target_rack_barcode = 123
        self._test_and_expect_errors('The pool stock rack barcode must be a ' \
                                     'basestring object (obtained: int).')
        self.target_rack_barcode = SSC_TEST_DATA.POOL_STOCK_RACK_BARCODE

    def _test_invalid_takeout_volume(self):
        self.take_out_volume = 0
        self._test_and_expect_errors('The stock take out volume must be a ' \
                                     'positive number (obtained: 0).')
        self.take_out_volume = -1
        self._test_and_expect_errors('The stock take out volume must be a ' \
                                     'positive number (obtained: -1).')
        self.take_out_volume = 1 #pylint: disable=W0201


class StockSampleCreationInstructionsWriterTestCase(
                                        _StockSampleCreationWriterTestCase):

    def set_up(self):
        _StockSampleCreationWriterTestCase.set_up(self)
        self.iso_label = SSC_TEST_DATA.ISO_LABELS[1]
        self.take_out_volume = SSC_TEST_DATA.SINGLE_DESIGN_TRANSFER_VOLUME
        self.buffer_volume = SSC_TEST_DATA.BUFFER_VOLUME

    def tear_down(self):
        _StockSampleCreationWriterTestCase.tear_down(self)
        del self.take_out_volume
        del self.buffer_volume

    def _create_tool(self):
        self.tool = StockSampleCreationInstructionsWriter(
                                                self.iso_label,
                                                self.target_rack_barcode,
                                                self.tube_destination_racks,
                                                self.take_out_volume,
                                                self.buffer_volume)

    def test_result_cybio(self):
        self._continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, 'instructions_cybio.txt')

    def test_result_biomek(self):
        self.tube_destination_racks = [self.tube_destination_racks[0]]
        self._continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, 'instructions_biomek.txt')


    def test_invalid_input_values(self):
        self._test_invalid_input_values()
        self.tube_destination_racks = dict()
        self._test_and_expect_errors('The tube destination rack map must be ' \
                                     'a list object (obtained: dict).')
        self.tube_destination_racks = [1]
        self._test_and_expect_errors('The barcode for a tube destination ' \
                         'rack must be a basestring object (obtained: int).')
        self.tube_destination_racks = []
        self._test_and_expect_errors('There are no barcodes in the ' \
                                     'destination rack map!')
        self.tube_destination_racks = SSC_TEST_DATA.TUBE_DESTINATION_RACKS
        self.iso_label = 123
        self._test_and_expect_errors('The ISO label must be a basestring ' \
                                     'object (obtained: int).')
        self.iso_label = SSC_TEST_DATA.ISO_LABELS[1]
        self._test_invalid_takeout_volume()
        self.buffer_volume = 0
        self._test_and_expect_errors('The buffer volume must be a positive ' \
                                     'number (obtained: 0).')
        self.buffer_volume = -1
        self._test_and_expect_errors()
        self._test_and_expect_errors('The buffer volume must be a positive ' \
                                     'number (obtained: -1).')


class SingleRackTransferWorklistWriterTestCase(
                                            _StockSampleCreationWriterTestCase):

    def set_up(self):
        _StockSampleCreationWriterTestCase.set_up(self)
        self.worklist = None
        self.single_design_rack_barcode = self.tube_destination_racks[0]

    def tear_down(self):
        _StockSampleCreationWriterTestCase.tear_down(self)
        del self.worklist
        del self.single_design_rack_barcode

    def _create_tool(self):
        self.tool = _SingleRackTransferWorklistWriter(
                                            self.worklist,
                                            self.single_design_rack_barcode,
                                            self.target_rack_barcode)

    def _continue_setup(self, file_name=None):
        _StockSampleCreationWriterTestCase._continue_setup(self,
                                                           file_name=file_name)
        worklist_series = self._generate_stock_rack_worklist_series(True)
        self.worklist = worklist_series.get_worklist_for_index(0)
        self._create_tool()

    def test_result(self):
        self._continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream,
                                SSC_TEST_DATA.FILE_NAME_STOCK_TRANSFER_BIOMEK)

    def test_input_values(self):
        self._continue_setup()
        self.single_design_rack_barcode = 123
        self._test_and_expect_errors('The single design rack barcode must ' \
                                     'be a basestring object (obtained: int).')
        self.single_design_rack_barcode = self.tube_destination_racks[0]
        self.target_rack_barcode = 123
        self._test_and_expect_errors('The pool rack barcode must be a ' \
                                     'basestring object (obtained: int).')
        self.target_rack_barcode = SSC_TEST_DATA.POOL_STOCK_RACK_BARCODE
        ori_worklist = self.worklist
        self.worklist = self.worklist.transfer_type
        self._test_and_expect_errors('The worklist must be a PlannedWorklist ' \
                                     'object (obtained: str).')
        self.worklist = ori_worklist
        self.worklist.transfer_type = TRANSFER_TYPES.RACK_SAMPLE_TRANSFER
        self._test_and_expect_errors('The worklist has an unexpected ' \
                'transfer type! Expected: SAMPLE_TRANSFER. ' \
                'Found: RACK_SAMPLE_TRANSFER.')
        self.worklist.transfer_type = TRANSFER_TYPES.SAMPLE_TRANSFER
        self.worklist.pipetting_specs = get_pipetting_specs_cybio()
        self._test_and_expect_errors('The worklist has unexpected pipetting ' \
                'specs! Expected: BioMekStock. Found: CyBio.')


class StockSampleCreationXL20ReportWriterTestCase(
                                            _StockSampleCreationWriterTestCase):

    def set_up(self):
        _StockSampleCreationWriterTestCase.set_up(self)
        self.WL_PATH = SSC_TEST_DATA.WORKLIST_FILE_PATH
        self.tube_transfers = []
        self.iso_label = 'ssgen_test_03'
        self.layout_number = 3
        self.take_out_volume = 2.7
        # tube barcode, src rack barcode, src pos label, trg rack barcode
        # trg pos label
        self.tube_transfer_data = [
                ('10001', '01111111', 'a1', '01000001', 'a1'),
                ('10003', '01111112', 'g8', '01000002', 'a1'),
                ('10002', '01111113', 'd3', '01000001', 'b1'),
                ('10004', '01111111', 'c1', '01000002', 'b1')]
        self.source_rack_locations = {'01111111' : 'freezer1, C1',
                                      '01111112' : 'frigde',
                                      '01111113' : None}

    def tear_down(self):
        _StockSampleCreationWriterTestCase.tear_down(self)
        del self.tube_transfers
        del self.iso_label
        del self.layout_number
        del self.take_out_volume
        del self.tube_transfer_data
        del self.source_rack_locations

    def _create_tool(self):
        self.tool = _StockSampleCreationXL20ReportWriter(
                                                self.tube_transfers,
                                                self.iso_label,
                                                self.layout_number,
                                                self.source_rack_locations,
                                                self.take_out_volume)

    def _continue_setup(self): #pylint: disable=W0221
        self.__create_tube_transfers()
        self._create_tool()

    def __create_tube_transfers(self):
        for ttd_data in self.tube_transfer_data:
            ttd = TubeTransferData(tube_barcode=ttd_data[0],
                       src_rack_barcode=ttd_data[1],
                       src_pos=get_rack_position_from_label(ttd_data[2]),
                       trg_rack_barcode=ttd_data[3],
                       trg_pos=get_rack_position_from_label(ttd_data[4]))
            self.tube_transfers.append(ttd)

    def test_result(self):
        self._continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_txt_file_stream(tool_stream, 'xl20_summary.txt', [0])

    def test_invalid_input_values(self):
        self._continue_setup()
        ori_transfers = self.tube_transfers
        self.tube_transfers = dict()
        self._test_and_expect_errors()
        self.tube_transfers = [1]
        self._test_and_expect_errors()
        self.tube_transfers = []
        self._test_and_expect_errors()
        self.tube_transfers = ori_transfers
        self.iso_label = self._create_stock_sample_creation_iso()
        self._test_and_expect_errors('The ISO label must be a basestring ' \
                                'object (obtained: StockSampleCreationIso).')
        self.iso_label = 'label'
        self.layout_number = '3'
        self._test_and_expect_errors('The layout number must be a int ' \
                                'object (obtained: str).')
        self.layout_number = 3.4
        self._test_and_expect_errors('The layout number must be a int ' \
                                'object (obtained: float).')
        self.layout_number = 3
        self._test_invalid_takeout_volume()
        self.source_rack_locations = []
        self._test_and_expect_errors('The rack location map must be a dict ' \
                                     'object (obtained: list).')

    def test_missing_source_rack_barcode(self):
        self._continue_setup()
        del self.source_rack_locations['01111111']
        self._test_and_expect_errors('The source location data for the ' \
                        'following barcodes has not been passed: 01111111.')


class StockSampleCreationWorklistWriterTestCase(
                                    _StockSampleCreationWriterTestCase):

    def set_up(self):
        _StockSampleCreationWriterTestCase.set_up(self)
        self.pick_tubes_for_isos = True
        self.iso = None
        self.use_single_source_rack = False

    def tear_down(self):
        _StockSampleCreationWriterTestCase.tear_down(self)
        del self.iso
        del self.use_single_source_rack

    def _create_tool(self):
        self.tool = StockSampleCreationIsoWorklistWriter(
                        self.iso,
                        self.tube_destination_racks,
                        self.target_rack_barcode,
                        use_single_source_rack=self.use_single_source_rack)

    def _continue_setup(self, file_name=None):
        _StockSampleCreationWriterTestCase._continue_setup(self,
                                                           file_name=file_name)
        self.iso = self.isos[1]
        self._generate_stock_racks()
        self._generate_pool_stock_rack()
        self._create_tool()

    def __check_result(self):
        file_map = self.tool.get_result()
        self.assert_is_not_none(file_map)
        self.__check_files(file_map)
        self.__check_stock_racks()

    def __check_files(self, file_map):
        exp_list = [SSC_TEST_DATA.FILE_NAME_XL20_WORKLIST,
                    SSC_TEST_DATA.FILE_NAME_XL20_SUMMARY,
                    SSC_TEST_DATA.FILE_NAME_INSTRUCTIONS,
                    SSC_TEST_DATA.FILE_NAME_LAYOUT]
        if self.use_single_source_rack:
            exp_list.append(SSC_TEST_DATA.FILE_NAME_STOCK_TRANSFER_BIOMEK)
        self.assert_equal(sorted(file_map.keys()), sorted(exp_list))
        for fn, tool_stream in file_map.iteritems():
            if fn == SSC_TEST_DATA.FILE_NAME_LAYOUT:
                self._compare_csv_file_stream(tool_stream, fn,
                                              ignore_columns=[3])
            elif fn == SSC_TEST_DATA.FILE_NAME_INSTRUCTIONS:
                if self.use_single_source_rack:
                    cmp_fn = 'instructions_biomek.txt'
                else:
                    cmp_fn = 'instructions_cybio.txt'
                self._compare_txt_file_stream(tool_stream, cmp_fn)
            elif fn == SSC_TEST_DATA.FILE_NAME_XL20_SUMMARY:
                self.__check_xl20_summary_file(tool_stream)
            elif fn == SSC_TEST_DATA.FILE_NAME_STOCK_TRANSFER_BIOMEK:
                self._compare_csv_file_stream(tool_stream, fn)
            else:
                self.__check_xl20_worklist(tool_stream)

    def __check_xl20_summary_file(self, tool_stream):
        tool_lines = FileComparisonUtils.convert_stream(tool_stream)
        if len(self.tube_destination_racks) == 1:
            cmp_fn = 'xl20_summary_biomek.txt'
        else:
            cmp_fn = 'xl20_summary_biomek.txt'
        exp_stream = self._get_expected_file_stream(cmp_fn)
        exp_lines = FileComparisonUtils.convert_stream(exp_stream)
        for i in range(len(exp_lines)):
            t_lin = FileComparisonUtils.convert_to_list(tool_lines[i + 1])
            e_lin = FileComparisonUtils.convert_to_list(exp_lines[i])
            self.assert_equal(t_lin, e_lin)

    def __check_xl20_worklist(self, tool_stream):
        lines = tool_stream.readlines()
        self.assert_equal(len(lines),
              1 + SSC_TEST_DATA.NUMBER_POOLS_11 * self.number_designs) #+headers
        trg_pos_index = XL20WorklistWriter.DEST_POSITION_INDEX
        tube_barcode_index = XL20WorklistWriter.TUBE_BARCODE_INDEX
        trg_rack_index = XL20WorklistWriter.DEST_RACK_INDEX
        dest_racks = set()
        barcodes = []
        trg_positions = set()
        for i in range(len(lines)):
            if i == 0: continue
            lin = lines[i].strip()
            ttd_data = lin.split(',')
            dest_racks.add(ttd_data[trg_rack_index])
            barcodes.append(ttd_data[tube_barcode_index])
            trg_positions.add(ttd_data[trg_pos_index].lower())
        exp_barcodes = []
        for iso_pos in self.iso_layouts[1].working_positions():
            exp_barcodes.extend(iso_pos.stock_tube_barcodes)
        self.assert_equal(sorted(exp_barcodes), sorted(barcodes))
        self.assert_equal(sorted(list(dest_racks)), self.tube_destination_racks)
        if self.use_single_source_rack:
            exp_positions = SSC_TEST_DATA.STOCK_POSITIONS_SINGLE_RACK.keys()
        else:
            exp_positions = SSC_TEST_DATA.STOCK_POSITIONS_3_RACKS
        self.assert_equal(sorted(exp_positions), sorted(list(trg_positions)))

    def __check_stock_racks(self):
        stock_racks = self.iso.iso_stock_racks
        self.assert_equal(len(stock_racks),
                          1 + len(self.tube_destination_racks))
        labels = []
        for stock_rack in stock_racks:
            labels.append(stock_rack.label)
            if stock_rack.label == SSC_TEST_DATA.POOL_STOCK_RACK_LABEL:
                self.__check_pool_stock_rack(stock_rack)
            else:
                self.__check_tube_destination_stock_rack(stock_rack)
        self.assert_true(SSC_TEST_DATA.POOL_STOCK_RACK_LABEL in labels)
        if self.use_single_source_rack:
            self.assert_true(SSC_TEST_DATA.SINGLE_STOCK_RACK_LABEL in labels)
        else:
            for label in SSC_TEST_DATA.TUBE_DESTINATION_RACKS.values():
                self.assert_true(label in labels)

    def __check_pool_stock_rack(self, stock_rack):
        rack = stock_rack.rack
        self.assert_equal(rack.barcode, SSC_TEST_DATA.POOL_STOCK_RACK_BARCODE)
        self.assert_equal(len(rack.containers), SSC_TEST_DATA.NUMBER_POOLS_11)
        for tube in rack.containers:
            self.assert_is_none(tube.sample)
        layout = self._get_stock_rack_layout(stock_rack,
                                             is_pool_stock_rack=True)
        iso_layout = self.iso_layouts[1]
        self.assert_equal(len(layout), SSC_TEST_DATA.NUMBER_POOLS_11)
        pos_labels = []
        for rack_pos, sr_pos in layout.iterpositions():
            pos_labels.append(rack_pos.label.lower())
            exp_pool = iso_layout.get_working_position(rack_pos).\
                       molecule_design_pool
            self.assert_equal(exp_pool, sr_pos.molecule_design_pool)
            exp_barcode = SSC_TEST_DATA.get_tube_barcode_for_pool(exp_pool)
            self.assert_equal(exp_barcode, sr_pos.tube_barcode)
            self.assert_equal(len(sr_pos.transfer_targets), 0)
        self.assert_equal(sorted(pos_labels),
                  sorted(SSC_TEST_DATA.STOCK_POSITIONS_3_RACKS)) # target rack
        self._compare_stock_rack_worklist_series(stock_rack.worklist_series,
                                                 self.use_single_source_rack)

    def __check_tube_destination_stock_rack(self, stock_rack):
        if self.use_single_source_rack:
            self.assert_equal(stock_rack.rack.barcode,
                  sorted(SSC_TEST_DATA.TUBE_DESTINATION_RACKS.keys())[0])
            num_tubes = SSC_TEST_DATA.NUMBER_POOLS_11 * self.number_designs
            exp_positions = SSC_TEST_DATA.STOCK_POSITIONS_SINGLE_RACK.keys()
        else:
            self.assert_true(stock_rack.rack.barcode in \
                             SSC_TEST_DATA.TUBE_DESTINATION_RACKS.keys())
            num_tubes = SSC_TEST_DATA.NUMBER_POOLS_11
            exp_positions = SSC_TEST_DATA.STOCK_POSITIONS_3_RACKS
        self.assert_equal(len(stock_rack.rack.containers), 0) # still empty
        layout = self._get_stock_rack_layout(stock_rack,
                                             is_single_stock_rack=True)
        self.assert_equal(len(layout), num_tubes)
        pos_labels = []
        found_mds = set()
        found_barcodes = set()
        iso_layout = self.iso_layouts[1]
        for rack_pos, sr_pos in layout.iterpositions():
            pos_labels.append(rack_pos.label.lower())
            pool = sr_pos.molecule_design_pool
            self.assert_equal(len(pool), 1)
            self.assert_equal(len(sr_pos.transfer_targets), 1)
            tt = sr_pos.transfer_targets[0]
            md = list(pool.molecule_designs)[0]
            if self.use_single_source_rack:
                final_pool_id = SSC_TEST_DATA.SINGLE_DESIGN_LOOKUP[md.id]
                final_pool_pos = SSC_TEST_DATA.POOL_POSITION_LOOKUP[
                                                            final_pool_id]
                self.assert_equal(tt.position_label.lower(), final_pool_pos)
                self.assert_false(md.id in found_mds)
                found_mds.add(md.id)
                self.assert_false(sr_pos.tube_barcode in found_barcodes)
                found_barcodes.add(sr_pos.tube_barcode)
            else:
                self.assert_equal(tt.position_label, rack_pos.label)
                iso_pos = iso_layout.get_working_position(rack_pos)
                self.assert_true(md in iso_pos.molecule_designs)
                self.assert_true(sr_pos.tube_barcode \
                                 in iso_pos.stock_tube_barcodes)
        if self.use_single_source_rack:
            exp_barcodes = []
            for iso_pos in iso_layout.working_positions():
                exp_barcodes.extend(iso_pos.stock_tube_barcodes)
            self.assert_equal(sorted(exp_barcodes),
                              sorted(list(found_barcodes)))
            self.assert_equal(sorted(list(found_mds)),
                    sorted(SSC_TEST_DATA.STOCK_POSITIONS_SINGLE_RACK.values()))
        self.assert_equal(sorted(pos_labels), sorted(exp_positions))
        self._compare_stock_rack_worklist_series(stock_rack.worklist_series,
                                                 self.use_single_source_rack)

    def test_result_cybio(self):
        self._continue_setup()
        self.__check_result()

    def test_result_biomek(self):
        self.tube_destination_racks = [self.tube_destination_racks[0]]
        self.use_single_source_rack = True
        self._continue_setup()
        self.__check_result()

    def test_invalid_input_values(self):
        self._test_invalid_input_values()
        ori_iso = self.iso
        self.iso = self._create_lab_iso()
        self._test_and_expect_errors('The ISO must be a ' \
                            'StockSampleCreationIso object (obtained: LabIso).')
        self.iso = ori_iso
        self.iso.status = ISO_STATUS.DONE
        self._test_and_expect_errors('Unexpected ISO status: "done"')
        self.iso.status = ISO_STATUS.QUEUED
        self.use_single_source_rack = None
        self._test_and_expect_errors('The "use single source rack " flag ' \
                                'must be a bool object (obtained: NoneType)')
        self.use_single_source_rack = False
        self.tube_destination_racks = dict()
        self._test_and_expect_errors('The tube destination rack list must be ' \
                                     'a list object (obtained: dict).')
        self.tube_destination_racks = []
        self._test_and_expect_errors('The tube destination rack list is empty!')
        self.tube_destination_racks = [1]
        self._test_and_expect_errors('The tube destination rack must be ' \
                                     'a basestring object (obtained: int).')

    def test_no_worklist_series(self):
        self._continue_setup()
        self.iso_request.worklist_series = None
        self._test_and_expect_errors('Unable to find worklist series ' \
                                     'for ISO request!')

    def test_unexpected_worklist_series_length(self):
        self._continue_setup()
        pw = self._create_planned_worklist()
        self.iso_request.worklist_series.add_worklist(1, pw)
        self._test_and_expect_errors('The worklist series of the ISO ' \
                        'request has an unexpected length (2, expected: 1).')

    def test_buffer_worklist_not_found(self):
        self._continue_setup()
        buffer_wl = self.iso_request.worklist_series.get_worklist_for_index(0)
        buffer_wl.index = 2
        self._test_and_expect_errors('Error when trying to determine ' \
                        'buffer volume: There is no worklist for index 0!')

    def test_different_buffer_volumes(self):
        self._continue_setup()
        buffer_wl = self.iso_request.worklist_series.get_worklist_for_index(0)
        vol = SSC_TEST_DATA.BUFFER_VOLUME * 2 / VOLUME_CONVERSION_FACTOR
        pst = self._create_planned_sample_transfer(volume=vol)
        buffer_wl.planned_liquid_transfers.append(pst)
        self._test_and_expect_errors('There are different volumes in the ' \
                                     'buffer dilution worklist!')

    def test_volume_calculation_failure(self):
        self._continue_setup()
        self.iso_request.stock_volume = 1 / VOLUME_CONVERSION_FACTOR
        self._test_and_expect_errors('Unable to determine stock transfer ' \
                'volume: The target volume you have requested (1 ul) is too ' \
                'low for the required dilution (1:15) since the CyBio cannot ' \
                'pipet less than 1.0 ul per transfer. The volume that has to ' \
                'be taken from the stock for each single molecule design ' \
                'would be lower that that. Increase the target volume ' \
                'to 15.0 ul or increase the target concentration.')

    def test_unknown_racks(self):
        self._continue_setup()
        self.tube_destination_racks[0] = '09876543'
        self._test_and_expect_errors('The following racks have not been ' \
                                     'found in the DB: 09876543!')

    def test_layout_conversion_error(self):
        self._continue_setup()
        self.iso.rack_layout = RackLayout()
        self._test_and_expect_errors('Error when trying to convert stock ' \
                                     'sample creation layout.')

    def test_multiple_barcodes_for_single_rack(self):
        self.use_single_source_rack = True
        self._continue_setup()
        file_map = self.tool.get_result()
        self.assert_is_not_none(file_map)
        self._check_warning_messages('There is more than one barcode for ' \
                            'tube destination list. Will use the smallest one.')

    def test_more_than_96_pools_for_single_rack(self):
        self.use_single_source_rack = True
        self._continue_setup()
        pools = []
        pool_id = 1056000
        while len(pools) < 40:
            pool_id += 1
            pool = self._get_pool(pool_id)
            if pool is not None: pools.append(pool)
        new_iso_layout = StockSampleCreationLayout()
        positions = get_positions_for_shape(new_iso_layout.shape,
                                            vertical_sorting=True)
        rack = self.rack_generator.barcode_map[self.target_rack_barcode]
        tube_positions = set()
        for tube in rack.containers:
            tube_positions.add(tube.location.position)
        for pool in pools:
            rack_pos = positions.pop(0)
            tube_barcodes = SSC_TEST_DATA.get_stock_tubes_barcodes(pool)
            iso_pos = StockSampleCreationPosition(rack_position=rack_pos,
                        molecule_design_pool=pool,
                        stock_tube_barcodes=tube_barcodes)
            new_iso_layout.add_position(iso_pos)
            if not rack_pos in tube_positions:
                self.tube_generator.create_tube(rack, rack_pos, pool)
            if len(new_iso_layout) == 96: break
        rl = new_iso_layout.create_rack_layout()
        self.iso.rack_layout = rl
        self.iso_layouts[0] = new_iso_layout
        for pool in pools:
            self.iso.molecule_design_pool_set.molecule_design_pools.add(pool)
        self._test_and_expect_errors('One rack is not sufficient to take up ' \
                'all tubes (120 tubes). Try again without requesting a ' \
                'single source rack.')

    def test_not_enough_rack_barcodes(self):
        self._continue_setup()
        del self.tube_destination_racks[0]
        self._test_and_expect_errors('You need to provide 3 empty racks. ' \
                                     'You have provided 2 barcodes.')

    def test_tube_racks_not_empty(self):
        self._continue_setup()
        c = 0
        for barcode, rack in self.rack_generator.barcode_map.iteritems():
            if barcode == self.target_rack_barcode: continue
            rack_pos = get_rack_position_from_label('a1')
            pool = None
            while pool is None:
                pool_id = 1056000 + c
                c += 1
                pool = self._get_pool(pool_id)
            self.tube_generator.create_tube(rack, rack_pos, pool)
        self._test_and_expect_errors('The following tube destination racks ' \
                'you have chosen are not empty: 09999981, 09999982, 09999983.')

    def test_missing_tube_in_pool_stock_rack(self):
        self._continue_setup()
        iso_layout = self.iso_layouts[1]
        # is closed, we cannot add anything;
        # removing tubes is hard in a test case, too
        new_layout = StockSampleCreationLayout(iso_layout.shape)
        for rack_pos, iso_pos in iso_layout.iterpositions():
            iso_pos = StockSampleCreationPosition(rack_position=rack_pos,
                    molecule_design_pool=iso_pos.molecule_design_pool,
                    stock_tube_barcodes=iso_pos.stock_tube_barcodes)
            new_layout.add_position(iso_pos)
        pool = self._get_pool(1056000)
        tube_barcodes = SSC_TEST_DATA.get_stock_tubes_barcodes(pool)
        rack_pos = get_rack_position_from_label('g8')
        iso_pos = StockSampleCreationPosition(rack_position=rack_pos,
                        molecule_design_pool=pool,
                        stock_tube_barcodes=tube_barcodes)
        new_layout.add_position(iso_pos)
        self.isos[1].rack_layout = new_layout.create_rack_layout()
        self._test_and_expect_errors('There are some tubes missing in the ' \
                                     'pool stock rack (09999999): G8.')

    def test_non_empty_tube_in_pool_stock_rack(self):
        self._continue_setup()
        rack = self.rack_generator.barcode_map[self.target_rack_barcode]
        for tube in rack.containers:
            tube.make_sample(1)
            break
        self._test_and_expect_errors('Some tubes in the pool stock rack ' \
                                     '(09999999) which are not empty: A2.')

    def test_additional_tube(self):
        self._continue_setup()
        rack = self.rack_generator.barcode_map[self.target_rack_barcode]
        pool = self._get_pool(1056000)
        rack_pos = get_rack_position_from_label('g8')
        self.tube_generator.create_tube(rack, rack_pos, pool)
        # the pool is only used for the barcode
        file_map = self.tool.get_result()
        self.assert_is_not_none(file_map)
        self._check_warning_messages('There are some tubes in the pool ' \
            'stock rack (09999999) that are located in positions that ' \
            'should be empty: G8. Please remove the tubes before continuing.')

    def test_unknown_tube(self):
        self._continue_setup()
        iso_layout = self.iso_layouts[1]
        for iso_pos in iso_layout.working_positions():
            iso_pos.stock_tube_barcodes[0] = '1001'
            break
        self.isos[1].rack_layout = iso_layout.create_rack_layout()
        self._test_and_expect_errors('Could not find tubes for the ' \
                                     'following tube barcodes: 1001.')


class StockSampleCreationTicketWorklistUploaderTestCase(
                                        _StockSampleCreationWriterTestCase):

    def set_up(self):
        _StockSampleCreationWriterTestCase.set_up(self)
        self.pick_tubes_for_isos = True
        self.create_test_tickets = True
        self.writer = None
        self.iso = None

    def tear_down(self):
        _StockSampleCreationWriterTestCase.tear_down(self)
        del self.writer
        del self.iso

    def _create_tool(self):
        self.tool = get_worklist_uploader(writer=self.writer)

    def _continue_setup(self, file_name=None):
        _StockSampleCreationWriterTestCase._continue_setup(self,
                                                           file_name=file_name)
        self.iso = self.isos[1]
        self._generate_stock_racks()
        self._generate_pool_stock_rack()
        self.__run_writer()
        self._create_tool()

    def __run_writer(self):
        self.writer = get_worklist_writer(iso=self.iso,
                    tube_destination_racks=self.tube_destination_racks,
                    pool_stock_rack_barcode=self.target_rack_barcode,
                    use_single_source_rack=False)
        self.writer.run()
        self.assert_false(self.writer.has_errors())

    def test_result(self):
        self._continue_setup()
        self.tool.run()
        self.assert_true(self.tool.transaction_completed())
        trac_fn = self.tool.return_value
        self.assert_equal(trac_fn, 'ssgen_test_01_robot_worklists.zip')

    def test_invalid_input_values(self):
        self._continue_setup()
        self.writer.add_error('error')
        self._test_and_expect_errors('The writer has errors! ' \
                                     'Abort file generation.')
        self.writer.reset()
        self._test_and_expect_errors('The writer has not run yet!')
