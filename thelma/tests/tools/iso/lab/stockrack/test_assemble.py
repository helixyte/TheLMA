"""
Tests for tools that assemble new stock racks for entities (using the XL20)
involved in ISO processing.

AAB
"""
from everest.repositories.rdb.testing import RdbContextManager
from thelma.automation.semiconstants import clear_semiconstant_caches
from thelma.automation.semiconstants import get_384_rack_shape
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.semiconstants import get_item_status_managed
from thelma.automation.semiconstants import get_positions_for_shape
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.semiconstants import initialize_semiconstant_caches
from thelma.automation.tools.iso.lab.base import FinalLabIsoPosition
from thelma.automation.tools.iso.lab.base import LABELS
from thelma.automation.tools.iso.lab.stockrack.assemble \
    import LabIsoStockRackOptimizer
from thelma.automation.tools.iso.lab.stockrack.assemble \
    import LabIsoXL20SummaryWriter
from thelma.automation.tools.iso.lab.stockrack.assemble \
    import LabIsoXL20WorklistWriter
from thelma.automation.tools.iso.lab.stockrack.assemble \
    import StockRackAssemblerIsoJob
from thelma.automation.tools.iso.lab.stockrack.assemble \
    import StockRackAssemblerLabIso
from thelma.automation.tools.iso.lab.stockrack.base import StockTubeContainer
from thelma.automation.tools.stock.base import STOCK_DEAD_VOLUME
from thelma.automation.tools.stock.base import STOCK_RACK_SHAPE_NAME
from thelma.automation.tools.stock.tubepicking import SinglePoolQuery
from thelma.automation.tools.stock.tubepicking import TubeCandidate
from thelma.automation.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.utils.base import add_list_map_element
from thelma.automation.utils.base import is_smaller_than
from thelma.automation.utils.layouts import FIXED_POSITION_TYPE
from thelma.automation.utils.layouts import MOCK_POSITION_TYPE
from thelma.automation.utils.layouts import TransferTarget
from thelma.interfaces import IUser
from thelma.models.container import Tube
from thelma.tests.tools.iso.lab.stockrack.utils import LabIsoStockRackTestCase
from thelma.tests.tools.iso.lab.utils import LAB_ISO_TEST_CASES
from thelma.tests.tools.iso.lab.utils import TestTubeGenerator
from thelma.tests.tools.tooltestingutils import FileComparisonUtils
from thelma.tests.tools.tooltestingutils import FileCreatorTestCase
from thelma.tests.tools.tooltestingutils import TestingLog


class _AssemblerTestCaseWithStockTubeContainers(LabIsoStockRackTestCase):

    _USE_ISO_LABEL = '123_iso_01'

    def set_up(self):
        LabIsoStockRackTestCase.set_up(self)
        self.WL_PATH += 'assemble/'
        self.stock_tube_containers = dict()
        self.for_job = False

    def tear_down(self):
        LabIsoStockRackTestCase.tear_down(self)
        del self.stock_tube_containers
        del self.for_job

    def _generate_stock_tube_containers(self):
        if self.for_job:
            plate_label = self.job_layouts.keys()[0]
            prep_layout = self.job_layouts[plate_label]
            num_copies = 2
        else:
            plate_label = self.prep_layouts.keys()[0]
            prep_layout = self.prep_layouts[plate_label]
            num_copies = 1
        for pp in prep_layout.working_positions():
            rack_marker = pp.stock_rack_marker
            if rack_marker is None: continue
            pool = self._get_pool(pp.molecule_design_pool)
            if self.stock_tube_containers.has_key(pool):
                container = self.stock_tube_containers[pool]
                container.add_preparation_position(plate_label, pp)
            else:
                container = StockTubeContainer.from_plate_position(pp,
                        final_position_copy_number=1, plate_label=plate_label)
                self.stock_tube_containers[pool] = container
        iso_layout = self.iso_layouts[self._USE_ISO_LABEL]
        for fp in iso_layout.working_positions():
            rack_marker = fp.stock_rack_marker
            if rack_marker is None: continue
            if not fp.from_job == self.for_job: continue
            pool = self._get_pool(fp.molecule_design_pool)
            if self.stock_tube_containers.has_key(pool):
                container = self.stock_tube_containers[pool]
                container.add_final_position(fp)
            else:
                container = StockTubeContainer.from_plate_position(fp,
                                         final_position_copy_number=num_copies)
                self.stock_tube_containers[pool] = container
        for stc in self.stock_tube_containers.values():
            pool = stc.pool
            tc = TestTubeGenerator.create_tube_candidate(pool)
            stc.tube_candidate = tc
            loc = TestTubeGenerator.RACK_LOCATIONS[tc.rack_barcode]
            stc.location = loc


class LabIsoXL20WorklistWriterTestCase(LabIsoStockRackTestCase,
                                       FileCreatorTestCase):

    def set_up(self):
        LabIsoStockRackTestCase.set_up(self)
        self.log = TestingLog()
        self.case = LAB_ISO_TEST_CASES.CASE_ORDER_ONLY
        self.rack_barcode = '09876543'
        self.stock_rack_layout = None
        self.stock_tube_containers = dict()
        self.WL_PATH += 'assemble/'
        self.VALID_FILE = 'xl20_worklist.csv'

    def tear_down(self):
        LabIsoStockRackTestCase.tear_down(self)
        del self.rack_barcode
        del self.stock_rack_layout
        del self.stock_tube_containers

    def _create_tool(self):
        self.tool = LabIsoXL20WorklistWriter(log=self.log,
                        rack_barcode=self.rack_barcode,
                        stock_rack_layout=self.stock_rack_layout,
                        stock_tube_containers=self.stock_tube_containers)

    def _continue_setup(self, file_name=None):
        self.stock_rack_layout = self._generate_stock_rack_layout(
                                                            '123_iso_01_s#1')
        self.__generate_stock_tube_containers()
        self._create_tool()

    def __generate_stock_tube_containers(self):
        layout_data = LAB_ISO_TEST_CASES.get_final_plate_layout_data(
                                                    self.case).values()[0]
        pool_ids = []
        for pos_data in layout_data.values():
            pool_ids.append(pos_data[0])
        for pool_id in pool_ids:
            pool = self._get_pool(pool_id)
            tc = TestTubeGenerator.create_tube_candidate(pool)
            stc = StockTubeContainer(pool=pool,
                    position_type=FIXED_POSITION_TYPE,
                    requested_tube_barcode='some',
                    expected_rack_barcode='some', final_position_copy_number=1)
            stc.tube_candidate = tc
            self.stock_tube_containers[pool] = stc

    def test_result(self):
        self._continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, self.VALID_FILE)

    def test_invalid_input_values(self):
        self._continue_setup()
        ori_barcode = self.rack_barcode
        self.rack_barcode = 123
        self._test_and_expect_errors('The destination rack barcode must be ' \
                                     'a basestring object (obtained: int)')
        self.rack_barcode = ori_barcode
        ori_layout = self.stock_rack_layout
        self.stock_rack_layout = self.stock_rack_layout.get_positions()
        self._test_and_expect_errors('The stock rack layout must be a ' \
                                     'StockRackLayout object (obtained: list)')
        self.stock_rack_layout = ori_layout
        ori_containers = self.stock_tube_containers
        self.stock_tube_containers = []
        self._test_and_expect_errors('The stock tube container map must be ' \
                                     'a dict object (obtained: list)')
        self.stock_tube_containers = {ori_containers.keys()[0] : 3}
        self._test_and_expect_errors('The stock tube container must be a ' \
                                'StockTubeContainer object (obtained: int)')
        self.stock_tube_containers = {3 : ori_containers.values()[0]}
        self._test_and_expect_errors('The pool must be a MoleculeDesignPool ' \
                                     'object (obtained: int)')


class LabIsoXL20SummaryWriterTestCase(_AssemblerTestCaseWithStockTubeContainers,
                                      FileCreatorTestCase):


    def set_up(self):
        _AssemblerTestCaseWithStockTubeContainers.set_up(self)
        self.case = LAB_ISO_TEST_CASES.CASE_ASSOCIATION_JOB_LAST
        self.log = TestingLog()
        self.entity = None
        self.stock_rack_layouts = dict()
        self.excluded_racks = ['033333333', '03333334']
        self.requested_tubes = ['100005203', '100005204']
        self.rack_markers = None

    def tear_down(self):
        _AssemblerTestCaseWithStockTubeContainers.tear_down(self)
        del self.stock_rack_layouts
        del self.excluded_racks
        del self.requested_tubes
        del self.rack_markers

    def _continue_setup(self, file_name=None):
        _AssemblerTestCaseWithStockTubeContainers._continue_setup(self,
                                                    file_name=file_name)
        if self.for_job:
            self.entity = self.iso_job
        else:
            self.entity = self.isos[self._USE_ISO_LABEL]
        self.__create_stock_layouts()
        self._generate_stock_tube_containers()
        self._generate_stock_racks(self.entity)
        if self.for_job:
            self.VALID_FILE = 'xl20_summary_job.txt'
        else:
            self.VALID_FILE = 'xl20_summary_iso.txt'
        self._create_tool()

    def _create_tool(self):
        self.tool = LabIsoXL20SummaryWriter(log=self.log,
                entity=self.entity,
                stock_tube_containers=self.stock_tube_containers,
                stock_rack_layouts=self.stock_rack_layouts,
                excluded_racks=self.excluded_racks,
                requested_tubes=self.requested_tubes)

    def __create_stock_layouts(self):
        stock_rack_labels = LAB_ISO_TEST_CASES.get_stock_rack_labels(self.case)
        if self.for_job:
            self.rack_markers = ['s#1']
        else:
            self.rack_markers = ['s#2', 's#3', 's#4', 's#5']
        for rack_marker in self.rack_markers:
            rack_label = stock_rack_labels[rack_marker][0]
            layout = self._generate_stock_rack_layout(rack_label)
            self.stock_rack_layouts[rack_marker] = layout

    def test_result_iso(self):
        self.excluded_racks = []
        self._continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_txt_file_stream(tool_stream, self.VALID_FILE,
                                      ignore_lines=[0])

    def test_result_job(self):
        self.for_job = True
        self._continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_txt_file_stream(tool_stream, self.VALID_FILE,
                                      ignore_lines=[0])

    def test_invalid_input_values(self):
        self._continue_setup()
        ori_entity = self.entity
        self.entity = 3
        self._test_and_expect_errors('The entity must either be a LabIso or ' \
                                     'an IsoJob object (obtained: int)')
        self.entity = ori_entity
        ori_containers = self.stock_tube_containers
        self.stock_tube_containers = []
        self._test_and_expect_errors('The stock tube container map must be ' \
                                     'a dict object (obtained: list)')
        self.stock_tube_containers = {ori_containers.keys()[0] : 3}
        self._test_and_expect_errors('The stock tube container must be a ' \
                                'StockTubeContainer object (obtained: int)')
        self.stock_tube_containers = {3 : ori_containers.values()[0]}
        self._test_and_expect_errors('The pool must be a MoleculeDesignPool ' \
                                     'object (obtained: int)')
        self.stock_tube_containers = ori_containers
        ori_sr_map = self.stock_rack_layouts
        self.stock_rack_layouts = []
        self._test_and_expect_errors('The stock rack layout map must be a ' \
                                     'dict object (obtained: list)')
        self.stock_rack_layouts = {ori_sr_map.keys()[0] : 3}
        self._test_and_expect_errors('The stock rack layout must be a ' \
                                     'StockRackLayout object (obtained: int)')
        self.stock_rack_layouts = {3 : ori_sr_map.values()[0]}
        self._test_and_expect_errors('The stock rack marker must be a str ' \
                                     'object (obtained: int)')
        self.stock_rack_layouts = ori_sr_map
        self.excluded_racks = {}
        self._test_and_expect_errors('The excluded rack list must be a list ' \
                                     'object (obtained: dict)')
        self.excluded_racks = [1]
        self._test_and_expect_errors('The excluded rack must be a basestring ' \
                                     'object (obtained: int)')
        self.excluded_racks = None
        self.requested_tubes = {}
        self._test_and_expect_errors('The requested tube list must be a list ' \
                                     'object (obtained: dict)')
        self.requested_tubes = [1]
        self._test_and_expect_errors('The requested tube must be a ' \
                                     'basestring object (obtained: int)')


class LabIsoStockRackOptimizerTestCase(
                                _AssemblerTestCaseWithStockTubeContainers):

    def set_up(self):
        _AssemblerTestCaseWithStockTubeContainers.set_up(self)
        self.case = LAB_ISO_TEST_CASES.CASE_NO_JOB_COMPLEX
        self.log = TestingLog()
        self.target_rack_shape = get_96_rack_shape()
        self.rack_marker_map = dict()
        # pos_label - pool, tube barcode, transfer_targets
        self.exp_layout_data = None
        self.WL_PATH += 'assemble/'

    def tear_down(self):
        _AssemblerTestCaseWithStockTubeContainers.tear_down(self)
        del self.target_rack_shape
        del self.rack_marker_map
        del self.exp_layout_data

    def _create_tool(self):
        self.tool = LabIsoStockRackOptimizer(log=self.log,
                            stock_tube_containers=self.stock_tube_containers,
                            target_rack_shape=self.target_rack_shape,
                            rack_marker_map=self.rack_marker_map)

    def _continue_setup(self, file_name=None):
        _AssemblerTestCaseWithStockTubeContainers._continue_setup(self,
                                                   file_name=file_name)
        self._generate_stock_tube_containers()
        self.__generate_rack_marker_map()
        self._create_tool()

    def __generate_rack_marker_map(self):
        iso = self.isos[self._USE_ISO_LABEL]
        all_plates = []
        for aliquot_plate in iso.iso_aliquot_plates:
            all_plates.append(aliquot_plate.rack.label)
        for prep_plate in iso.iso_preparation_plates:
            all_plates.append(prep_plate.rack.label)
        for plate_label in all_plates:
            value_parts = LABELS.parse_rack_label(plate_label)
            rack_marker = value_parts[LABELS.MARKER_RACK_MARKER]
            self.rack_marker_map[plate_label] = rack_marker

    def __check_result(self, stock_rack_label=None):
        self._continue_setup()
        sr_layout = self.tool.get_result()
        self.assert_is_not_none(sr_layout)
        if stock_rack_label is not None:
            layout_data = LAB_ISO_TEST_CASES.get_stock_rack_layout_data(
                                                self.case)[stock_rack_label]
        else:
            layout_data = self.exp_layout_data
        self.assert_equal(sr_layout.shape.name, STOCK_RACK_SHAPE_NAME)
        self.assert_equal(len(sr_layout), len(layout_data))
        tested_labels = []
        layout_name = 'stock rack layout'
        for rack_pos, sr_pos in sr_layout.iterpositions():
            pos_label = rack_pos.label.lower()
            tested_labels.append(pos_label)
            pos_data = layout_data[pos_label]
            self._compare_layout_value(pos_data[0], 'molecule_design_pool',
                                       sr_pos, layout_name)
            self._compare_layout_value(pos_data[1], 'tube_barcode', sr_pos,
                                       layout_name)
            self._compare_layout_value(pos_data[2], 'transfer_targets', sr_pos,
                                       layout_name)
        self.assert_equal(sorted(tested_labels), sorted(layout_data.keys()))

    def test_result_2_target_plates_and_transfer_targets_96_well_target(self):
        self.__check_result('123_iso_01_s#1')

    def test_result_association_no_cybio_384_well_target(self):
        self.case = LAB_ISO_TEST_CASES.CASE_ASSOCIATION_JOB_LAST
        self.target_rack_shape = get_384_rack_shape()
        self.exp_layout_data = dict(
                a1=[205202, '1000205202', [TransferTarget('c2', 1 , 'p')]],
                b1=[205205, '1000205205', [TransferTarget('d2', 1 , 'p')]],
                c1=[205203, '1000205203', [TransferTarget('c3', 1 , 'p')]],
                d1=[205206, '1000205206', [TransferTarget('d3', 1 , 'p')]],
                e1=[205204, '1000205204', [TransferTarget('c4', 1 , 'p')]],
                f1=[205207, '1000205207', [TransferTarget('d4', 1 , 'p')]])
        self.__check_result()

    def test_result_2_target_plates_with_equal_target_number(self):
        self.case = LAB_ISO_TEST_CASES.CASE_NO_JOB_1_PREP
        self.__check_result('123_iso_01_s#1')

    def test_result_one_to_one(self):
        # 96-well target plate
        self.case = LAB_ISO_TEST_CASES.CASE_ASSOCIATION_JOB_LAST
        self.exp_layout_data = dict(
                c2=[205202, '1000205202', [TransferTarget('c2', 1 , 'p')]],
                d2=[205205, '1000205205', [TransferTarget('d2', 1 , 'p')]],
                c3=[205203, '1000205203', [TransferTarget('c3', 1 , 'p')]],
                d3=[205206, '1000205206', [TransferTarget('d3', 1 , 'p')]],
                c4=[205204, '1000205204', [TransferTarget('c4', 1 , 'p')]],
                d4=[205207, '1000205207', [TransferTarget('d4', 1 , 'p')]])
        self.__check_result()

    def test_invalid_input_values(self):
        self._continue_setup()
        ori_containers = self.stock_tube_containers
        self.stock_tube_containers = []
        self._test_and_expect_errors('The stock tube container map must be ' \
                                     'a dict object (obtained: list)')
        self.stock_tube_containers = {ori_containers.keys()[0] : 3}
        self._test_and_expect_errors('The stock tube container must be a ' \
                                'StockTubeContainer object (obtained: int)')
        self.stock_tube_containers = {3 : ori_containers.values()[0]}
        self._test_and_expect_errors('The pool must be a MoleculeDesignPool ' \
                                     'object (obtained: int)')
        self.stock_tube_containers = ori_containers
        ori_shape = self.target_rack_shape
        self.target_rack_shape = self.target_rack_shape.name
        self._test_and_expect_errors('The target rack shape must be a ' \
                                     'RackShape object (obtained: unicode)')
        self.target_rack_shape = ori_shape
        ori_rack_map = self.rack_marker_map
        self.rack_marker_map = []
        self._test_and_expect_errors('The rack marker map must be a dict ' \
                                     'object (obtained: list).')
        self.rack_marker_map = {ori_rack_map.keys()[0] : 1}
        self._test_and_expect_errors('The rack marker must be a basestring ' \
                                     'object (obtained: int).')
        self.rack_marker_map = {1 : ori_rack_map.values()[0]}
        self._test_and_expect_errors('The plate label must be a basestring ' \
                                     'object (obtained: int)')

    def test_no_stock_tube_candidates(self):
        self._continue_setup()
        for pool in sorted(self.stock_tube_containers.keys()):
            container = self.stock_tube_containers[pool]
            container.tube_candidate = None
            break
        self._test_and_expect_errors('There are no stock tube candidates for ' \
                                     'the following pools: 180005!')

    def test_too_many_candidates(self):
        self._continue_setup()
        pool_id = 1056000
        for rack_pos in get_positions_for_shape(self.target_rack_shape):
            pool = self._get_pool(pool_id)
            fp = FinalLabIsoPosition(rack_position=rack_pos,
                        molecule_design_pool=pool, position_type='fixed',
                        volume=1, concentration=10000, # stock conc,
                        stock_tube_barcode='1001',
                        stock_rack_barcode='09999999',
                        stock_rack_marker='s#1')
            container = StockTubeContainer.from_plate_position(fp,
                                     final_position_copy_number=1)
            tc = TubeCandidate(pool_id=pool_id, rack_barcode='09999999',
                               rack_position=rack_pos, tube_barcode='1001',
                               concentration=0.00001, volume=0.00005)
            container.tube_candidate = tc
            self.stock_tube_containers[pool] = container
            pool_id += 1
        self._test_and_expect_errors('The number of source positions (100) ' \
                'exceeds the number of available positions in a stock rack ' \
                '(96). This is a programming error. Talk to the IT ' \
                'department, please.')


class _StockRackAssemblerTestCase(LabIsoStockRackTestCase, FileCreatorTestCase):

    def set_up(self):
        LabIsoStockRackTestCase.set_up(self)
        self.compare_stock_tube_barcode = False
        self.ori_tube_candidates = dict()
        self.session = None
        self.tube_barcodes = []
        self.source_tube_racks = set()
        self.WL_PATH += 'assemble/'
        self.excluded_racks = None
        self.requested_tubes = None
        self.include_dummy_output = False

    def tear_down(self):
        LabIsoStockRackTestCase.tear_down(self)
        del self.ori_tube_candidates
        del self.session
        del self.tube_barcodes
        del self.source_tube_racks
        del self.excluded_racks
        del self.requested_tubes
        del self.include_dummy_output

    def _continue_setup(self, file_name=None):
        LabIsoStockRackTestCase._continue_setup(self, file_name=file_name)
        self._create_tool()

    def _get_original_stock_data(self, pool_id, stock_rack_marker):
        return self.__find_tube(pool_id, stock_rack_marker)

    def __find_tube(self, pool_id, stock_rack_marker):
        if pool_id == MOCK_POSITION_TYPE or stock_rack_marker is None:
            return None, None
        elif self.ori_tube_candidates.has_key(pool_id):
            tc = self.ori_tube_candidates[pool_id]
            return tc.tube_barcode, tc.rack_barcode
        pool = self._get_pool(pool_id)
        conc = pool.default_stock_concentration \
               * CONCENTRATION_CONVERSION_FACTOR
        takeout_vol = LAB_ISO_TEST_CASES.get_stock_takeout_volumes(
                                                            self.case)[pool_id]
        required_volume = STOCK_DEAD_VOLUME + takeout_vol
        query = SinglePoolQuery(pool_id, conc, minimum_volume=required_volume)
        query.run(self.session)
        candidates = query.get_query_results()
        if len(candidates) < 1:
            msg = 'No candidate for pool %i! Please increase the volume ' \
                  'of the stock samples in the test DB!' % (pool_id)
            raise AssertionError(msg)
        vol_map = dict()
        for tc in candidates:
            add_list_map_element(vol_map, tc.volume, tc)
        volume = max(vol_map.keys())
        if is_smaller_than((volume * VOLUME_CONVERSION_FACTOR), required_volume):
            raise ValueError('There is no suitable stock tube for pool %i!' \
                             % (pool_id))
        tc = vol_map[volume].pop(0)
        self.ori_tube_candidates[pool_id] = tc
        self.tube_barcodes.append(tc.tube_barcode)
        self.source_tube_racks.add(tc.rack_barcode)
        return tc.tube_barcode, tc.rack_barcode

    def _set_session(self, session):
        self.session = session
        clear_semiconstant_caches()
        initialize_semiconstant_caches()
        self.user = self._get_entity(IUser, 'it')
        self.em_requester = self.user
        self.rack_generator.reset_session()

    def _test_and_expect_success(self, case_name):
        with RdbContextManager() as session:
            self._set_session(session)
            self._load_iso_request(case_name)
            self._check_result()

    def _check_result(self):
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        self.__check_files(zip_stream)
        self._check_entity()

    def __check_files(self, zip_stream):
        archive = self._get_zip_archive(zip_stream)
        exp_num = 3
        if self.include_dummy_output: exp_num += 1
        self.assert_equal(len(archive.namelist()), exp_num)
        wl_content = None
        report_content = None
        for fn in archive.namelist():
            tool_content = archive.read(fn)
            if self.tool.FILE_NAME_INSTRUCTIONS[2:] in fn:
                self.__compare_instructions_file(tool_content)
            elif self.tool.FILE_NAME_XL20_WORKLIST[2:] in fn:
                wl_content = tool_content
            elif self.tool.FILE_NAME_XL20_SUMMARY[2:] in fn:
                report_content = tool_content
        self.__compare_xl20_contents(wl_content, report_content)

    def __compare_instructions_file(self, tool_content):
        ori_path = self.WL_PATH
        self.WL_PATH = LAB_ISO_TEST_CASES.INSTRUCTIONS_FILE_PATH
        fn = LAB_ISO_TEST_CASES.get_instruction_file(self.case, self.FOR_JOB)
        self._compare_txt_file_content(tool_content, fn)
        self.WL_PATH = ori_path

    def __compare_xl20_contents(self, wl_content, report_content):
        wl_lines = FileComparisonUtils.convert_content(wl_content)
        line_number = 0
        src_racks = set()
        tubes = []
        expected_tube_number = LAB_ISO_TEST_CASES.get_stock_tube_number(
                                                    self.case, self.FOR_JOB)
        WORKLIST_WRITER = LabIsoXL20WorklistWriter
        REPORT_WRITER = LabIsoXL20SummaryWriter
        for wl_line in wl_lines:
            line_number += 1
            if line_number == 1:
                self.assert_true(WORKLIST_WRITER.SOURCE_RACK_HEADER \
                                 in wl_line)
                continue
            line_list = FileComparisonUtils.convert_to_list(wl_line)
            dest_rack_index = WORKLIST_WRITER.DEST_RACK_INDEX
            self.assert_true(line_list[dest_rack_index] in self.rack_barcodes)
            src_rack_index = WORKLIST_WRITER.SOURCE_RACK_INDEX
            src_racks.add(line_list[src_rack_index])
            tube_barcode_index = WORKLIST_WRITER.TUBE_BARCODE_INDEX
            tubes.append(line_list[tube_barcode_index])
        tube_set = set(tubes)
        self.assert_equal(len(tube_set), expected_tube_number)
        self.assert_true('Total number of tubes: %i' % (len(tube_set)) \
                                                        in report_content)
        if not self.excluded_racks is None:
            for excl_rack in self.excluded_racks:
                self.assert_false(excl_rack in src_racks)
        # check report
        if self.excluded_racks is None:
            self.assert_true(REPORT_WRITER.NO_EXCLUDED_RACKS_MARKER \
                             in report_content)
        else:
            for excl_rack in self.excluded_racks:
                self.assert_true(excl_rack in report_content)
        if self.requested_tubes is None:
            self.assert_true(REPORT_WRITER.NO_REQUESTED_TUBES_MARKER \
                             in report_content)
            self.assert_false('Some requested tubes' in report_content)
        else:
            for req_tube in self.requested_tubes:
                self.assert_true(req_tube in report_content)
        for src_rack in src_racks: self.assert_true(src_rack in report_content)

    def _check_entity(self):
        raise NotImplementedError('Abstract method.')

    def _test_invalid_input_values(self):
        with RdbContextManager() as session:
            self._set_session(session)
            self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
            self._test_invalid_input_value_entity()
            self._test_invalid_input_value_rack_barcodes()
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

    def _test_non_empty_destination_racks(self):
        with RdbContextManager() as session:
            self._set_session(session)
            self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
            for barcode in self.rack_barcodes:
                rack = self.rack_generator.barcode_map[barcode]
                tube_specs = rack.specs.tube_specs[0]
                tube = Tube(specs=tube_specs,
                            status=get_item_status_managed(),
                            barcode='123', location=None)
                rack.add_tube(tube, get_rack_position_from_label('a1'))
                break
            self.session.commit()
            self._test_and_expect_errors('The following racks you have ' \
                                         'chosen are not empty:')

    def _test_excluded_racks(self, case_name):
        with RdbContextManager() as session:
            self._set_session(session)
            self._load_iso_request(case_name)
            # get racks to be excluded
            missing_pool_id = 205201
            query = 'SELECT r.barcode AS rack_barcode ' \
                    'FROM rack r, containment rc, sample s, stock_sample ss ' \
                    'WHERE r.rack_id = rc.holder_id ' \
                    'AND r.rack_type = \'TUBERACK\' ' \
                    'AND rc.held_id = s.container_id ' \
                    'AND ss.sample_id = s.sample_id ' \
                    'AND ss.molecule_design_set_id = %i' % (missing_pool_id)
            result = self.session.query('rack_barcode').from_statement(query).all()
            self.excluded_racks = []
            for record in result: self.excluded_racks.append(record[0])
            if len(self.excluded_racks) < 1: raise ValueError('no rack found')
            if self.FOR_JOB:
                self._test_and_expect_errors('For some control molecule ' \
                        'design pools there are no valid stock tubes ' \
                        'available: 205201')
            else:
                self._test_and_expect_errors('Unable to find stock tubes ' \
                        'for the following fixed (control) positions: 205201.')


class StockRackAssemblerLabIsoTestCase(_StockRackAssemblerTestCase):

    FOR_JOB = False

    def _create_tool(self):
        self.tool = StockRackAssemblerLabIso(lab_iso=self.entity,
                            rack_barcodes=self.rack_barcodes,
                            excluded_racks=self.excluded_racks,
                            requested_tubes=self.requested_tubes,
                            include_dummy_output=self.include_dummy_output)

    def _check_entity(self):
        self.assert_is_not_none(self.tool.entity)
        iso = self.tool.entity
        exp_num_sr = LAB_ISO_TEST_CASES.get_number_iso_stock_racks(self.case)\
                                                        [self._USED_ISO_LABEL]
        iso_sr = iso.iso_stock_racks
        sector_sr = iso.iso_sector_stock_racks
        all_sr = sector_sr + iso_sr
        self.assert_equal(len(all_sr), exp_num_sr)
        # check sectors
        sector_racks = dict()
        for sr in sector_sr:
            sector_racks[sr.sector_index] = sr
        sector_data = LAB_ISO_TEST_CASES.get_sectors_for_iso_stock_racks(
                                                                    self.case)
        num_sector_racks = 0
        for rack_marker, sector_index in sector_data.iteritems():
            if sector_index is None: continue
            num_sector_racks += 1
            sr = sector_racks[sector_index]
            value_parts = LABELS.parse_rack_label(sr.label)
            self.assert_equal(rack_marker,
                              value_parts[LABELS.MARKER_RACK_MARKER])
        self.assert_equal(num_sector_racks, len(sector_sr))
        # check layouts and worklist series
        for sr in all_sr:
            label = sr.label
            layout_data = LAB_ISO_TEST_CASES.get_stock_rack_layout_data(
                                                        self.case)[label]
            self._compare_stock_rack_layout(layout_data, sr.rack_layout, label)
            self._compare_stock_rack_worklist_series(sr)

    def test_case_order_only(self):
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)

    def test_case_no_job_direct(self):
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_NO_JOB_DIRECT)

    def test_case_no_job_1_prep(self):
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_NO_JOB_1_PREP)

    def test_case_no_job_complex(self):
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_NO_JOB_COMPLEX)

    def test_case_association_direct(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)

    def test_case_association_96(self):
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_96)

    def test_case_association_simple(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE)

    def test_case_association_no_cybio(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_NO_CYBIO)

    def test_case_association_2_aliquots(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_2_ALIQUOTS)

    def test_case_association_job_last(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_JOB_LAST)

    def test_case_association_several_conc(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SEVERAL_CONC)

    def test_case_library_simple(self):
        with RdbContextManager() as session:
            self.filter_destination_racks = False
            self._set_session(session)
            self._load_iso_request(LAB_ISO_TEST_CASES.CASE_LIBRARY_SIMPLE)
            self._test_and_expect_errors('The lab ISO does not need to be ' \
                'processed. Please proceed with the lab ISO job processing.')

    def test_case_library_2_aliquots(self):
        with RdbContextManager() as session:
            self.filter_destination_racks = False
            self._set_session(session)
            self._load_iso_request(LAB_ISO_TEST_CASES.CASE_LIBRARY_2_ALIQUOTS)
            self._test_and_expect_errors('The lab ISO does not need to be ' \
                'processed. Please proceed with the lab ISO job processing.')

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_unknown_rack_barcodes(self):
        with RdbContextManager() as session:
            self._set_session(session)
            self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)
            self._test_unknown_rack_barcodes()

    def test_non_empty_destination_racks(self):
        self._test_non_empty_destination_racks()

    def test_not_enough_rack_barcodes_iso(self):
        with RdbContextManager() as session:
            self._set_session(session)
            self._test_not_enough_rack_barcodes_iso()

    def test_final_layout_conversion_error(self):
        with RdbContextManager() as session:
            self._set_session(session)
            self._test_final_layout_conversion_error()

    def test_iso_preparation_layout_conversion_error(self):
        with RdbContextManager() as session:
            self._set_session(session)
            self._test_iso_preparation_layout_conversion_error()

    def test_missing_fixed_position(self):
        with RdbContextManager() as session:
            self._set_session(session)
            self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)
            layout = self._get_layout_from_iso()
            for fp in layout.working_positions():
                fp.volume = 1000
            self.entity.rack_layout = layout.create_rack_layout()
            self._test_and_expect_errors('Unable to find stock tubes for the ' \
                    'following fixed (control) positions: 180005, 205201, ' \
                    '330001, 333803, 1056000.')

    def test_missing_floating_position(self):
        with RdbContextManager() as session:
            self._set_session(session)
            self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
            layout = self._get_layout_from_iso()
            pool_set = self.entity.molecule_design_pool_set
            pool = None
            for fp in layout.working_positions():
                if fp.is_floating:
                    fp.volume = 1000
                    pool = fp.molecule_design_pool
                    break
            self.entity.rack_layout = layout.create_rack_layout()
            self.assert_true(pool_set.contains(pool))
            zip_stream = self.tool.get_result()
            self.assert_is_not_none(zip_stream)
            self._check_warning_messages('Unable to find stock tubes for the ' \
                    'following floating positions: %i. The positions are put ' \
                    'back into the queue.' % (pool.id))
            self.assert_false(pool_set.contains(pool))
            layout = self._get_layout_from_iso()
            for fp in layout.working_positions():
                if not fp.molecule_design_pool == pool:
                    self.assert_false(fp.is_inactivated)
                else:
                    self.assert_true(fp.is_inactivated)

    def test_inconsistent_sectors_for_stock_rack(self):
        with RdbContextManager() as session:
            self._set_session(session)
            self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
            layout = self._get_layout_from_iso()
            rack_pos = get_rack_position_from_label('c2')
            fp = layout.get_working_position(rack_pos)
            fp.sector_index = None
            self.entity.rack_layout = layout.create_rack_layout()
            self._test_and_expect_errors('The planned sector indices for ' \
                         'the following stock racks are inconsistent: s#3!')

    def test_inconsistent_sectors_for_pool(self):
        with RdbContextManager() as session:
            self._set_session(session)
            self._load_iso_request(LAB_ISO_TEST_CASES.CASE_NO_JOB_COMPLEX)
            layout = self._get_layout_from_iso()
            rack_pos = get_rack_position_from_label('f3')
            fp = layout.get_working_position(rack_pos)
            fp.concentration = 50000 # stock conc
            fp.sector_index = 1
            fp.stock_rack_marker = 's#1'
            fp.stock_tube_barcode = '1001'
            fp.stock_rack_barcode = '09999999'
            self.entity.rack_layout = layout.create_rack_layout()
            self._test_and_expect_errors('The planned sector indices for the ' \
                                'following stock racks are inconsistent: s#1!')

    def test_excluded_racks(self):
        self._test_excluded_racks(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)


class StockRackAssemblerIsoJobTestCase(_StockRackAssemblerTestCase):

    FOR_JOB = True

    def _create_tool(self):
        self.tool = StockRackAssemblerIsoJob(iso_job=self.entity,
                        rack_barcodes=self.rack_barcodes,
                        excluded_racks=self.excluded_racks,
                        requested_tubes=self.requested_tubes,
                        include_dummy_output=self.include_dummy_output)

    def _check_entity(self):
        self.assert_is_not_none(self.iso_job)
        exp_num_sr = LAB_ISO_TEST_CASES.get_number_job_stock_racks(self.case)
        stock_racks = self.iso_job.iso_job_stock_racks
        self.assert_equal(len(stock_racks), exp_num_sr)
        for stock_rack in stock_racks:
            label = stock_rack.label
            exp_barcode = self.rack_generator.STOCK_RACK_BARCODES[label]
            self.assert_equal(stock_rack.rack.barcode, exp_barcode)
            layout_data = LAB_ISO_TEST_CASES.get_stock_rack_layout_data(
                                                            self.case)[label]
            self._compare_stock_rack_layout(layout_data, stock_rack.rack_layout,
                                            label)
            self._compare_stock_rack_worklist_series(stock_rack)

    def test_case_order_only(self):
        with RdbContextManager() as session:
            self.filter_destination_racks = False
            self._set_session(session)
            self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)
            self._test_and_expect_errors('The lab ISO job does not need ' \
                'to be processed. Please proceed with the lab ISO processing.')

    def test_case_no_job_direct(self):
        with RdbContextManager() as session:
            self.filter_destination_racks = False
            self._set_session(session)
            self._load_iso_request(LAB_ISO_TEST_CASES.CASE_NO_JOB_DIRECT)
            self._test_and_expect_errors('The lab ISO job does not need ' \
                'to be processed. Please proceed with the lab ISO processing.')

    def test_case_no_job_1_prep(self):
        with RdbContextManager() as session:
            self.filter_destination_racks = False
            self._set_session(session)
            self._load_iso_request(LAB_ISO_TEST_CASES.CASE_NO_JOB_1_PREP)
            self._test_and_expect_errors('The lab ISO job does not need ' \
                'to be processed. Please proceed with the lab ISO processing.')

    def test_case_no_job_complex(self):
        with RdbContextManager() as session:
            self.filter_destination_racks = False
            self._set_session(session)
            self._load_iso_request(LAB_ISO_TEST_CASES.CASE_NO_JOB_COMPLEX)
            self._test_and_expect_errors('The lab ISO job does not need ' \
                'to be processed. Please proceed with the lab ISO processing.')

    def test_case_association_direct(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)

    def test_case_association_96(self):
        with RdbContextManager() as session:
            self.filter_destination_racks = False
            self._set_session(session)
            self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_96)
            self._test_and_expect_errors('The lab ISO job does not need ' \
                'to be processed. Please proceed with the lab ISO processing.')

    def test_case_association_simple(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE)

    def test_case_association_no_cybio(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_NO_CYBIO)

    def test_case_association_2_aliquots(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_2_ALIQUOTS)

    def test_case_association_job_last(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_JOB_LAST)

    def test_case_association_several_conc(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SEVERAL_CONC)

    def test_case_library_simple(self):
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_LIBRARY_SIMPLE)

    def test_case_library_2_aliquots(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_LIBRARY_2_ALIQUOTS)

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_unknown_rack_barcodes(self):
        with RdbContextManager() as session:
            self._set_session(session)
            self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
            self._test_unknown_rack_barcodes()

    def test_non_empty_destination_racks(self):
        self._test_non_empty_destination_racks()

    def test_final_layout_conversion_error(self):
        with RdbContextManager() as session:
            self._set_session(session)
            self._test_final_layout_conversion_error()

    def test_iso_preparation_layout_conversion_error(self):
        with RdbContextManager() as session:
            self._set_session(session)
            self._test_iso_preparation_layout_conversion_error()

    def test_job_preparation_layout_conversion_error(self):
        with RdbContextManager() as session:
            self._set_session(session)
            self._test_job_preparation_layout_conversion_error()

    def test_job_different_final_layouts(self):
        with RdbContextManager() as session:
            self._set_session(session)
            self._test_job_different_final_layouts()

    def test_job_different_iso_preparation_positions(self):
        with RdbContextManager() as session:
            self._set_session(session)
            self._test_job_different_iso_preparation_positions()

    def test_job_no_starting_wells(self):
        with RdbContextManager() as session:
            self.filter_destination_racks = False
            self._set_session(session)
            self._test_job_no_starting_wells()

    def test_missing_fixed_position(self):
        with RdbContextManager() as session:
            self._set_session(session)
            self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
            for iso in self.isos.values():
                layout = self._get_layout_from_iso(iso)
                for fp in layout.working_positions():
                    fp.volume = 1000
                iso.rack_layout = layout.create_rack_layout()
            self._test_and_expect_errors('For some control molecule design ' \
                'pools there are no valid stock tubes available: 180005, ' \
                '205201, 205202.')

    def test_excluded_racks(self):
        self._test_excluded_racks(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
