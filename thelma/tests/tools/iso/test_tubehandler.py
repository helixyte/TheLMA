"""
Tests the tube handler tools.
"""
from everest.entities.utils import get_root_aggregate
from everest.testing import RdbContextManager
from everest.testing import check_attributes
from thelma.automation.tools.iso.generation import IsoGenerator
from thelma.automation.tools.iso.prep_utils import PrepIsoLayoutConverter
from thelma.automation.tools.iso.prep_utils import RequestedStockSample
import logging
from thelma.automation.tools.iso.stockworklist \
    import StockTransferWorklistGenerator384Single
from thelma.automation.tools.iso.tubehandler \
    import IsoXL20WorklistGenerator384Controls
from thelma.automation.tools.iso.tubehandler \
    import IsoXL20WorklistGenerator384Samples
from thelma.automation.tools.iso.tubehandler import IsoControlLayoutFinder
from thelma.automation.tools.iso.tubehandler import IsoXL20ReportWriter
from thelma.automation.tools.iso.tubehandler import IsoXL20WorklistGenerator
from thelma.automation.tools.iso.tubehandler import IsoXL20WorklistGenerator96
from thelma.automation.tools.iso.tubehandler import IsoXL20WorklistWriter
from thelma.automation.tools.iso.tubehandler import StockTubePicker
from thelma.automation.tools.iso.tubehandler import TubeCandidate
from thelma.automation.tools.semiconstants \
    import get_experiment_type_robot_optimisation
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.tools.semiconstants import get_384_rack_shape
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_experiment_metadata_type
from thelma.automation.tools.semiconstants import get_item_status_managed
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.utils.base import add_list_map_element
from thelma.automation.tools.utils.iso import IsoParameters
from thelma.interfaces import IJobType
from thelma.interfaces import ITubeRack
from thelma.interfaces import ITubeRackSpecs
from thelma.interfaces import ITubeSpecs
from thelma.models.container import ContainerLocation
from thelma.models.container import Tube
from thelma.models.experiment import ExperimentMetadata
from thelma.models.job import IsoJob
from thelma.models.racklayout import RackLayout
from thelma.tests.tools.tooltestingutils \
    import ExperimentMetadataReadingTestCase
from thelma.tests.tools.tooltestingutils import FileComparisonUtils
from thelma.tests.tools.tooltestingutils import FileCreatorTestCase
from thelma.tests.tools.tooltestingutils import SilentLog
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase


class TubeCandidateTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.rack_barcode = '02488352'
        self.rack_pos = get_rack_position_from_label('A1')
        self.tube_barcode = '1016179640'
        self.stock_volume = 5.7e-5
        self.location_name = 'C74S1'
        self.location_index = '1'
        self.init_data = dict(rack_barcode=self.rack_barcode,
                              rack_position=self.rack_pos,
                              tube_barcode=self.tube_barcode,
                              stock_volume=self.stock_volume)

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.rack_barcode
        del self.rack_pos
        del self.tube_barcode
        del self.stock_volume
        del self.location_name
        del self.location_index
        del self.init_data

    def test_init(self):
        tc = TubeCandidate(**self.init_data) #pylint: disable=W0142
        self.assert_is_not_none(tc)
        check_attributes(tc, self.init_data)

    def test_immutability(self):
        tc = TubeCandidate(**self.init_data) #pylint: disable=W0142
        for attr_name, value in self.init_data.iteritems():
            args = (tc, attr_name, value)
            self.assert_raises(AttributeError, setattr, *args) #pylint: disable=W0142
        tc.prep_rack_pos = self.rack_pos
        self.assert_equal(tc.prep_rack_pos, self.rack_pos)
        tc.location_name = self.location_name
        self.assert_equal(tc.location_name, self.location_name)
        tc.location_index = self.location_index
        self.assert_equal(tc.location_index, self.location_index)

    def test_create_from_confirmation_query(self):
        record = (self.stock_volume, self.rack_barcode, self.rack_pos.row_index,
                  self.rack_pos.column_index)
        tc = TubeCandidate.create_from_confirmation_query(record,
                                                          self.tube_barcode)
        self.assert_is_not_none(tc)
        check_attributes(tc, self.init_data)
        self.assert_is_none(tc.location_name)
        self.assert_is_none(tc.location_index)

    def test_create_from_searching_query(self):
        record = (self.stock_volume, self.rack_barcode, self.rack_pos.row_index,
                  self.rack_pos.column_index, self.tube_barcode)
        tc = TubeCandidate.create_from_searching_query(record)
        self.assert_is_not_none(tc)
        check_attributes(tc, self.init_data)
        self.assert_is_none(tc.location_name)
        self.assert_is_none(tc.location_index)

    def test_set_locations(self):
        tc = TubeCandidate(**self.init_data) #pylint: disable=W0142
        self.assert_is_none(tc.location_name)
        self.assert_is_none(tc.location_index)
        tc.set_location(self.location_name, self.location_index)
        check_attributes(tc, self.init_data)
        self.assert_equal(tc.location_name, self.location_name)
        self.assert_equal(tc.location_index, self.location_index)



class XL20WriterTestCase(FileCreatorTestCase):

    def set_up(self):
        FileCreatorTestCase.set_up(self)
        self.log = TestingLog()
        self.WL_PATH = 'thelma:tests/tools/iso/csv_files/'
        self.WL_FILE_1 = 'xl20_1_sector.csv'
        self.WL_FILE_4 = 'xl20_4_sectors.csv'
        self.destination_rack_map = {
                    0 : '024440', 1 : '024441', 2: '024442', 3 : '024443'}
        self.a1_pos = get_rack_position_from_label('A1')
        self.b1_pos = get_rack_position_from_label('B1')
        self.a2_pos = get_rack_position_from_label('A2')
        self.b2_pos = get_rack_position_from_label('B2')
        # key: tube barcode, value: rack_barcode, rack position, prep rack pos
        #: take out volume,
        self.tc_data = {'10101' : ('022401', self.a1_pos, self.a1_pos, 1),
                        '10102' : ('022401', self.b1_pos, self.b1_pos, 1),
                        '10103' : ('022402', self.a1_pos, self.a2_pos, 2),
                        '10104' : ('022403', self.a1_pos, self.b2_pos, 2)}
        self.sector_data = dict(A1=0, A2=1, B1=2, B2=3)
        self.sector_stock_samples = dict()
        self.tube_candidates = []

    def tear_down(self):
        FileCreatorTestCase.tear_down(self)
        del self.log
        del self.WL_FILE_1
        del self.WL_FILE_4
        del self.destination_rack_map
        del self.a1_pos
        del self.b1_pos
        del self.a2_pos
        del self.b2_pos
        del self.tc_data
        del self.sector_data
        del self.sector_stock_samples
        del self.tube_candidates

    def _continue_setup(self, number_sectors=4):
        self.__create_tube_candidates()
        self.__create_sector_candidates(number_sectors)
        self._create_tool()

    def __create_tube_candidates(self):
        for tube_barcode, data_tuple in self.tc_data.iteritems():
            tc = TubeCandidate(rack_barcode=data_tuple[0],
                               rack_position=data_tuple[1],
                               tube_barcode=tube_barcode,
                               stock_volume=data_tuple[3])
            tc.location_name = 'freezer1'
            tc.location_index = 1
            self.tube_candidates.append(tc)

    def __create_sector_candidates(self, number_sectors):
        for tc in self.tube_candidates:
            pool_id = len(self.pool_map) + 205205
            pool = None
            while pool is None:
                try:
                    pool = self._get_pool(pool_id)
                except ValueError:
                    pool_id += 1
            data_tuple = self.tc_data[tc.tube_barcode]
            rack_pos = data_tuple[2]
            rss = RequestedStockSample(pool=pool,
                    take_out_volume=data_tuple[3], stock_tube_barcode=None,
                    stock_rack_barcode=None, target_position=rack_pos,
                    stock_concentration=50000)
            if number_sectors == 1:
                sector_index = 0
            else:
                sector_index = self.sector_data[rack_pos.label]
            rss.tube_candidate = tc
            add_list_map_element(self.sector_stock_samples, sector_index, rss)

    def _test_invalid_requested_stock_samples(self):
        self._continue_setup(number_sectors=4)
        req_stock_samples = self.sector_stock_samples[0]
        self.sector_stock_samples = req_stock_samples
        self._test_and_expect_errors('The sector stock samples map must be a ' \
                                     'dict object')
        self.sector_stock_samples = dict(A=req_stock_samples)
        self._test_and_expect_errors('The sector index must be a int object')
        self.sector_stock_samples = {0 : req_stock_samples[0]}
        self._test_and_expect_errors('The requested stock sample list must ' \
                                     'be a list object')

    def _test_invalid_barcode_map(self):
        self._continue_setup(number_sectors=1)
        barcode = self.destination_rack_map[0]
        self.destination_rack_map = barcode
        self._test_and_expect_errors('The destination rack barcode map must ' \
                                     'be a dict object')
        self.destination_rack_map = dict(A=barcode)
        self._test_and_expect_errors('The sector index must be a int object')
        self.destination_rack_map = {0 : 4}
        self._test_and_expect_errors('The rack barcode must be a basestring ' \
                                     'object')

    def _test_missing_barcode_sector_index(self):
        self._continue_setup(number_sectors=4)
        self.destination_rack_map = {0 : '024444'}
        self._test_and_expect_errors('The destination map misses sector index')


class IsoXL20WorkListWriterTestCase(XL20WriterTestCase):

    def _create_tool(self):
        self.tool = IsoXL20WorklistWriter(log=self.log,
                    sector_stock_samples=self.sector_stock_samples,
                    destination_rack_barcode_map=self.destination_rack_map)


    def test_result_4_sectors(self):
        self._continue_setup(number_sectors=4)
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, self.WL_FILE_4)

    def test_result_1_sector(self):
        self.destination_rack_map = {0 : '024444'}
        self._continue_setup(number_sectors=1)
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, self.WL_FILE_1)

    def test_invalid_requested_stock_samples(self):
        self._test_invalid_requested_stock_samples()

    def test_invalid_barcode_map(self):
        self._test_invalid_barcode_map()

    def test_missing_barcode_sector_index(self):
        self._test_missing_barcode_sector_index()


class IsoXL20ReportWriterTestCase(XL20WriterTestCase):

    def set_up(self):
        XL20WriterTestCase.set_up(self)
        self.label = 'xl20_report_writer_test'
        self.rack_shape_name = '16x24'
        self.excluded_racks = ['02444100']
        self.requested_tubes = ['10101']
        self.is_job = False
        self.c1_pos = get_rack_position_from_label('C1')
        self.c2_pos = get_rack_position_from_label('C2')
        self.d1_pos = get_rack_position_from_label('D1')
        self.d2_pos = get_rack_position_from_label('D2')
        # key: tube barcode, value: rack_barcode, rack position, prep rack pos
        #: take out volume,
        self.tc_data = {'10101' : ('022401', self.a1_pos, self.a1_pos, 1),
                        '10102' : ('022401', self.b1_pos, self.b1_pos, 1),
                        '10103' : ('022402', self.a1_pos, self.a2_pos, 2),
                        '10104' : ('022403', self.a1_pos, self.b2_pos, 2),
                        '10105' : ('022403', self.a1_pos, self.c1_pos, 2),
                        '10106' : ('022404', self.a1_pos, self.d1_pos, 2),
                        '10107' : ('022402', self.b1_pos, self.c2_pos, 1),
                        '10108' : ('022401', self.c1_pos, self.d2_pos, 1)}
        self.sector_data = dict(A1=0, A2=1, B1=2, B2=3, C1=0, C2=1, D1=2, D2=3)

    def tear_down(self):
        XL20WriterTestCase.tear_down(self)
        del self.label
        del self.rack_shape_name
        del self.excluded_racks
        del self.requested_tubes
        del self.is_job
        del self.c1_pos
        del self.d1_pos
        del self.c2_pos
        del self.d2_pos

    def _create_tool(self):
        self.tool = IsoXL20ReportWriter(label=self.label,
                rack_shape_name=self.rack_shape_name,
                sector_stock_samples=self.sector_stock_samples,
                destination_rack_barcode_map=self.destination_rack_map,
                excluded_racks=self.excluded_racks,
                requested_tubes=self.requested_tubes,
                is_job=self.is_job, log=self.log)

    def __check_result_basics(self):
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        content = tool_stream.read()
        marker = self.tool.ISO_MARKER
        if self.is_job: marker = self.tool.ISO_JOB_MARKER
        self.assert_true('%s: %s' % (marker, self.label) in content)
        self.assert_true(self.tool.PREP_SHAPE_BASE_LINE % \
                         (self.rack_shape_name) in content)
        for sector_index in self.sector_stock_samples.keys():
            lin = self.tool.DESTINATION_RACK_BASE_LINE % ((sector_index + 1),
                            self.destination_rack_map[sector_index])
            self.assert_true(lin in content)
        return content

    def test_result_4(self):
        self._continue_setup(number_sectors=4)
        content = self.__check_result_basics()
        self.assert_true(self.excluded_racks[0] in content)
        self.assert_false(IsoXL20ReportWriter.NO_EXCLUDED_RACKS_MARKER \
                          in content)
        self.assert_true(self.requested_tubes[0] in content)
        self.assert_false(IsoXL20ReportWriter.NO_REQUESTED_TUBES_MARKER \
                          in content)
        self.assert_true(IsoXL20ReportWriter.NO_WARNING_MARKER in content)

    def test_result_1(self):
        self._continue_setup(number_sectors=4)
        content = self.__check_result_basics()
        self.assert_true(self.excluded_racks[0] in content)
        self.assert_false(IsoXL20ReportWriter.NO_EXCLUDED_RACKS_MARKER \
                          in content)
        self.assert_true(self.requested_tubes[0] in content)
        self.assert_false(IsoXL20ReportWriter.NO_REQUESTED_TUBES_MARKER \
                          in content)
        self.assert_true(IsoXL20ReportWriter.NO_WARNING_MARKER in content)

    def test_result_no_racks_and_tubes(self):
        self.excluded_racks = []
        self.requested_tubes = None
        warn = 'test_warning'
        self.log.add_warning(warn)
        self._continue_setup(number_sectors=4)
        content = self.__check_result_basics()
        self.assert_true(IsoXL20ReportWriter.NO_EXCLUDED_RACKS_MARKER in content)
        self.assert_true(IsoXL20ReportWriter.NO_REQUESTED_TUBES_MARKER in content)
        self.assert_false(IsoXL20ReportWriter.NO_WARNING_MARKER in content)
        self.assert_true(warn in content)

    def test_is_iso_job(self):
        self.is_job = True
        self._continue_setup(number_sectors=4)
        content = self.__check_result_basics()
        self.assert_true(self.excluded_racks[0] in content)
        self.assert_false(IsoXL20ReportWriter.NO_EXCLUDED_RACKS_MARKER in content)
        self.assert_true(self.requested_tubes[0] in content)
        self.assert_false(IsoXL20ReportWriter.NO_REQUESTED_TUBES_MARKER in content)
        self.assert_true(IsoXL20ReportWriter.NO_WARNING_MARKER in content)

    def test_invalid_label(self):
        self.label = 123
        self._test_and_expect_errors('The label must be a basestring object')

    def test_invalid_rack_shape_name(self):
        self.rack_shape_name = None
        self._test_and_expect_errors('The rack shape name must be a str object')

    def test_invalid_requested_stock_samples(self):
        self._test_invalid_requested_stock_samples()

    def test_invalid_barcode_map(self):
        self._test_invalid_barcode_map()

    def test_missing_barcode_sector_index(self):
        self._test_missing_barcode_sector_index()

    def test_invalid_excluded_racks(self):
        excl_map = dict()
        for rack in self.excluded_racks: excl_map[rack] = int(rack)
        self.excluded_racks = excl_map
        self._test_and_expect_errors('excluded racks list must be a list')
        self.excluded_racks = excl_map.values()
        self._test_and_expect_errors('excluded rack barcode must be a ' \
                                     'basestring')

    def test_invalid_requested_tubes(self):
        tube_map = dict()
        for tube in self.requested_tubes: tube_map[tube] = int(tube)
        self.requested_tubes = tube_map
        self._test_and_expect_errors('requested tubes list must be a list')
        self.requested_tubes = tube_map.values()
        self._test_and_expect_errors('requested tube barcode must be a ' \
                                     'basestring')


class StockTubePickerTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.log = TestingLog()
        self.requested_stock_samples = []
        self.excluded_racks = None
        self.requested_tubes = None
        self.a1_pos = get_rack_position_from_label('A1')
        self.b1_pos = get_rack_position_from_label('B1')
        self.c1_pos = get_rack_position_from_label('C1')
        self.stock_concentration = 50000
        #: md pool id, value: take out volume, stock rack barcode,
        #: stock tube barcode, rack pos)
        self.rss_data = {
                205200 : [1, '02481991', '1001023622', self.a1_pos],
                205201 : [2, '02477461', '1000334310', self.b1_pos],
                205202 : [4, '02477461', '1000334309', self.c1_pos]}

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.log
        del self.requested_stock_samples
        del self.excluded_racks
        del self.requested_tubes
        del self.a1_pos
        del self.b1_pos
        del self.c1_pos
        del self.rss_data

    def _create_tool(self):
        self.tool = StockTubePicker(log=self.log,
                requested_stock_samples=self.requested_stock_samples,
                excluded_racks=self.excluded_racks,
                requested_tubes=self.requested_tubes)

    def __continue_setup(self):
        self.__create_requested_molecules()
        self._create_tool()

    def __create_requested_molecules(self):
        for pool_id, data_tuple in self.rss_data.iteritems():
            pool = self._get_pool(pool_id)
            rss = RequestedStockSample(pool=pool,
                        take_out_volume=data_tuple[0],
                        stock_tube_barcode=data_tuple[2],
                        stock_rack_barcode=data_tuple[1],
                        target_position=data_tuple[3],
                        stock_concentration=self.stock_concentration)
            self.requested_stock_samples.append(rss)

    def __check_result(self, req_stock_samples=None):
        if req_stock_samples is None:
            self.__continue_setup()
            req_stock_samples = self.tool.get_result()
        self.assert_is_not_none(req_stock_samples)
        self.assert_equal(len(req_stock_samples),
                          len(self.requested_stock_samples))
        for rss in req_stock_samples:
            pool_id = rss.pool.id
            self.assert_true(self.rss_data.has_key(pool_id))
            self.assert_is_not_none(rss.tube_candidate)

    def test_result(self):
        self.__check_result()

    def test_excluded_racks(self):
        self.excluded_racks = ['101']
        self.__continue_setup()
        # run with unimportant rack and get excluded rack
        req_stock_sampless = self.tool.get_result()
        candidate = req_stock_sampless[0].tube_candidate
        excluded_rack = candidate.rack_barcode
        self.assert_equal(len(self.tool.get_messages()), 0)
        # rerun with excluded rack
        self.excluded_racks = [excluded_rack]
        self._create_tool()
        req_stock_sampless = self.tool.get_result()
        for rss in req_stock_sampless:
            self.assert_not_equal(rss.tube_candidate.rack_barcode,
                                  excluded_rack)
        self.__check_result(req_stock_sampless)
        self._check_warning_messages('has been excluded')

    def test_requested_tube(self):
        self.__continue_setup()
        # get excluded rack
        req_stock_sampless = self.tool.get_result()
        candidate = req_stock_sampless[0].tube_candidate
        excluded_rack = candidate.rack_barcode
        self.assert_equal(len(self.tool.get_messages()), 0)
        original_tube_barcodes = []
        for rss in req_stock_sampless:
            original_tube_barcodes.append(rss.tube_candidate.tube_barcode)
        # get requested tube
        self.excluded_racks = [excluded_rack]
        self._create_tool()
        req_stock_sampless = self.tool.get_result()
        replace_tubes = []
        for rss in req_stock_sampless:
            tube_barcode = rss.tube_candidate.tube_barcode
            if not tube_barcode in original_tube_barcodes:
                replace_tubes.append(tube_barcode)
        self.assert_not_equal(len(replace_tubes), 0)
        # rerun with requested tubes
        self.excluded_racks = None
        self.requested_tubes = replace_tubes
        self._create_tool()
        req_stock_sampless = self.tool.get_result()
        self.__check_result(req_stock_sampless)
        tool_tube_barcodes = []
        for rss in req_stock_sampless:
            tool_tube_barcodes.append(rss.tube_candidate.tube_barcode)
        for barcode in replace_tubes:
            self.assert_true(barcode in tool_tube_barcodes)
        self._check_warning_messages('Some requested tubes differ from the ' \
                                     'ones scheduled during ISO generation')

    def test_tube_moved_warning(self):
        self.__continue_setup()
        rss = self.requested_stock_samples[0]
        rss.stock_rack_barcode = '02400078'
        req_stock_samples = self.tool.get_result()
        self.__check_result(req_stock_samples)
        self._check_warning_messages('has been moved since the generation ISO')

    def test_requested_tube_not_found_warning(self):
        self.requested_tubes = ['1001667883']
        self.rss_data[205201] = (30, '02481743', '1001667284', self.b1_pos)
        self.__continue_setup()
        req_mols = self.tool.get_result()
        self.__check_result(req_mols)
        self._check_warning_messages('Could not find suitable tubes for the ' \
                                'following tube barcodes you have requested')

    def test_more_requested_than_md_pools(self):
        self.requested_tubes = ['1001667883', '1001667284', '1002805337',
                                '1001667015']
        self.__check_result()
        self._check_warning_messages('There are more requested tubes (4) ' \
                                     'than molecule design pool IDs (3)!')

    def test_mismatching_requested_tube_md_pool(self):
        self.requested_tubes = []
        for pool_id, data_tuple in self.rss_data.iteritems():
            if not pool_id == 205200: continue
            self.requested_tubes.append(data_tuple[2])
        del self.rss_data[205200]
        self.__check_result()
        self._check_warning_messages('Could not find suitable tubes for ' \
                        'the following tube barcodes you have requested')

    def test_multiple_requested_tubes_for_one_pool(self):
        self.requested_tubes = ['1000336342', '1001023622']
        self.__check_result()
        self._check_warning_messages('You have requested multiple tubes for ' \
                                     'the same molecule design pool ID!')

    def test_invalid_requested_stock_samples(self):
        self.__continue_setup()
        self.requested_stock_samples = set(self.requested_stock_samples)
        self._test_and_expect_errors('The requested stock sample list must ' \
                                     'be a list object')

    def test_invalid_excluded_racks(self):
        self.__continue_setup()
        self.excluded_racks = dict()
        self._test_and_expect_errors('The excluded racks list must be a list')
        self.excluded_racks = [1, 3]
        self._test_and_expect_errors('The excluded rack barcode must be a ' \
                                     'basestring object')

    def test_invalid_requested_tubes(self):
        self.__continue_setup()
        self.requested_tubes = dict()
        self._test_and_expect_errors('The requested tubes list must be a ' \
                                     'list object')
        self.requested_tubes = [1, 3]
        self._test_and_expect_errors('The requested tube barcode must be a ' \
                                     'basestring object')

    def test_no_tube_for_molecule_design_pool(self):
        self.rss_data[205202][0] = 400
        self.__continue_setup()
        req_stock_samples = self.tool.get_result()
        del self.rss_data[205202]
        self.__check_result(req_stock_samples)
        self._check_warning_messages('Could not find a valid tube rack ' \
                                     'for the following molecule design pools')

    def test_less_than_1_tube_found(self):
        self.stock_concentration = 10000
        self.__continue_setup()
        self._test_and_expect_errors('Did not find any tube!')

    def test_requested_tube_not_found(self):
        self.requested_tubes = ['12']
        self.__continue_setup()
        self._test_and_expect_errors('The following requested tubes could ' \
                                     'not be found in the DB')


class IsoXL20WorklistGeneratorTestCase(ExperimentMetadataReadingTestCase,
                                       FileCreatorTestCase):

    def set_up(self):
        ExperimentMetadataReadingTestCase.set_up(self)
        self.TEST_FILE_PATH = 'thelma:tests/tools/iso/tubehandler/'
        self.VALID_FILE_384_SCREEN_SINGLE = 'valid_file_384_screen_single.xls'
        self.silent_log = SilentLog()
        self.destination_rack_map = {
            0 : '09999991', 1 : '09999992', 2: '09999993', 3 : '09999994'}
        self.excluded_racks = None
        self.requested_tubes = None
        self.experiment_type_id = None
        self.number_isos = 1
        self.iso_request = None
        self.generated_isos = None
        self.tube_rack_specs = self._get_entity(ITubeRackSpecs)
        # only name avoid autoflush problems
        self.status_name = ITEM_STATUS_NAMES.FUTURE
        self.iso = None
        self.iso_job = None
        self.pool_id = None
        self.tube_rack_agg = get_root_aggregate(ITubeRack)
        self.racks = dict()
        self.aliquot_plate_labels = ['xl20_test#1']

    def tear_down(self):
        ExperimentMetadataReadingTestCase.tear_down(self)
        del self.VALID_FILE_384_SCREEN_SINGLE
        del self.silent_log
        del self.destination_rack_map
        del self.excluded_racks
        del self.requested_tubes
        del self.experiment_type_id
        del self.number_isos
        del self.iso_request
        del self.generated_isos
        del self.tube_rack_specs
        del self.status_name
        del self.iso
        del self.iso_job
        del self.pool_id
        for rack in self.racks.values(): self.tube_rack_agg.remove(rack)
        del self.racks
        del self.tube_rack_agg
        del self.aliquot_plate_labels

    def _continue_setup(self, file_name=None):
        ExperimentMetadataReadingTestCase._continue_setup(self, file_name)
        self.__generate_isos()
        self.__create_tube_racks()
        self._set_iso_or_iso_job()
        self._create_tool()

    def _set_experiment_metadadata(self):
        em_type = get_experiment_metadata_type(self.experiment_type_id)
        self.experiment_metadata = ExperimentMetadata(
                            label='Tubehandler Test',
                            subproject=self._create_subproject(),
                            number_replicates=2,
                            experiment_metadata_type=em_type,
                            ticket_number=123)

    def __generate_isos(self):
        self.iso_request = self.experiment_metadata.iso_request
        generator = IsoGenerator(iso_request=self.iso_request,
                    number_isos=self.number_isos)
        self.generated_isos = generator.get_result()

    def __create_tube_racks(self):
        for barcode in self.destination_rack_map.values():
            # to avoid authoflush problems
            status = ITEM_STATUS_NAMES.from_name(self.status_name)
            tube_rack = self.tube_rack_specs.create_rack(status=status,
                                                         label=barcode)
            tube_rack.barcode = barcode
            self.tube_rack_agg.add(tube_rack)
            self.racks[barcode] = tube_rack

    def _set_iso_or_iso_job(self):
        raise NotImplementedError('Abstract method')

    def _check_successfull_run(self, zip_stream, expected_tube_number):
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 2)
        report_content = None
        wl_content = None
        for fil in zip_archive.namelist():
            if IsoXL20WorklistGenerator.WORKLIST_FILE_SUFFIX[2:] in fil:
                wl_content = zip_archive.read(fil)
            elif IsoXL20WorklistGenerator.REPORT_FILE_SUFFIX[2:] in fil:
                report_content = zip_archive.read(fil)
        # check worklist
        wl_lines = FileComparisonUtils.convert_content(wl_content)
        line_number = 0
        src_racks = set()
        tubes = []
        for wl_line in wl_lines:
            line_number += 1
            if line_number == 1:
                self.assert_true(IsoXL20WorklistWriter.SOURCE_RACK_HEADER \
                                 in wl_line)
                continue
            line_list = FileComparisonUtils.convert_to_list(wl_line)
            dest_rack_index = IsoXL20WorklistWriter.DEST_RACK_INDEX
            self.assert_true(line_list[dest_rack_index] \
                             in self.destination_rack_map.values())
            src_rack_index = IsoXL20WorklistWriter.SOURCE_RACK_INDEX
            src_racks.add(line_list[src_rack_index])
            tube_barcode_index = IsoXL20WorklistWriter.TUBE_BARCODE_INDEX
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
            self.assert_true(IsoXL20ReportWriter.NO_EXCLUDED_RACKS_MARKER \
                             in report_content)
        else:
            for excl_rack in self.excluded_racks:
                self.assert_true(excl_rack in report_content)
        if self.requested_tubes is None:
            self.assert_true(IsoXL20ReportWriter.NO_REQUESTED_TUBES_MARKER \
                             in report_content)
            self.assert_false('Some requested tubes' in report_content)
        else:
            for req_tube in self.requested_tubes:
                self.assert_true(req_tube in report_content)
        for src_rack in src_racks: self.assert_true(src_rack in report_content)

    def _test_excluded_racks(self, causes_failure=True):
        with RdbContextManager() as session:
            self._set_excluded_racks(session)
            self._continue_setup()
            if causes_failure:
                self._test_and_expect_errors()
                err_msg = ' '.join(self.tool.get_messages(logging.ERROR))
                msg1 = 'For some control molecule design pools there are no ' \
                       'valid stock tubes available'
                msg2 = 'Did not find any tube!'
                has_msg = (msg1 in err_msg) or (msg2 in err_msg)
                self.assert_true(has_msg)
            else:
                zip_stream = self.tool.get_result()
                self.assert_is_not_none(zip_stream)
                self._check_warning_messages('The following molecule design ' \
                                        'pools are put back into the queue')
            self._check_warning_messages('At least one potential candidate ' \
                                         'has been excluded')

    def _test_missing_floating_sample(self):
        with RdbContextManager() as session:
            self._set_excluded_racks(session)
            self._continue_setup()
            # assert that md in set
            set_pool_ids = []
            for md_pool in self.iso.molecule_design_pool_set:
                set_pool_ids.append(md_pool.id)
            self.assert_true(self.pool_id in set_pool_ids)
            # run
            zip_stream = self.tool.get_result()
            self.assert_is_not_none(zip_stream)
            # check molecule is put back into queue
            self._check_warning_messages('The following molecule design '\
                                         'pools are put back into the queue')
            pool_set = self.iso.molecule_design_pool_set
            for md_pool in pool_set:
                self.assert_not_equal(md_pool.id, self.pool_id)
            converter = PrepIsoLayoutConverter(
                                    rack_layout=self.iso.rack_layout,
                                    log=self.silent_log)
            prep_layout = converter.get_result()
            positions = []
            for pp in prep_layout.working_positions():
                if pp.is_inactivated:
                    positions.append(pp.rack_position)
                else:
                    self.assert_not_equal(pp.molecule_design_pool_id,
                                          self.pool_id)
            self.assert_true(len(positions) > 0)
            for issr in self.iso.iso_sample_stock_racks:
                for pct in issr.planned_worklist.planned_transfers:
                    target_pos = pct.target_position
                    self.assert_false(target_pos in positions)

    def _set_excluded_racks(self, session):
        # get racks to be excluded
        query = 'SELECT r.barcode AS rack_barcode ' \
                'FROM rack r, containment rc, sample s, stock_sample ss ' \
                'WHERE r.rack_id = rc.holder_id ' \
                'AND r.rack_type = \'TUBERACK\' ' \
                'AND rc.held_id = s.container_id ' \
                'AND ss.sample_id = s.sample_id ' \
                'AND ss.molecule_design_set_id = %i' % (self.pool_id)
        result = session.query('rack_barcode').from_statement(query).all()
        rack_barcodes = []
        for record in result: rack_barcodes.append(record[0])
        if len(rack_barcodes) < 1: raise ValueError('no rack found')
        self.excluded_racks = rack_barcodes

    def _test_invalid_excluded_racks(self):
        self._continue_setup()
        self.excluded_racks = dict()
        self._test_and_expect_errors('The excluded racks list must be a list')
        self.excluded_racks = [1, 3]
        self._test_and_expect_errors('The excluded rack barcode must be a ' \
                                     'basestring object')

    def _test_requested_tubes(self):
        with RdbContextManager() as session:
            query = 'SELECT cb.barcode AS tube_barcode ' \
                    'FROM container_barcode cb, sample s, stock_sample ss ' \
                    'WHERE cb.container_id = s.container_id ' \
                    'AND ss.sample_id = s.sample_id ' \
                    'AND ss.molecule_design_set_id = %i' % (self.pool_id)
            result = session.query('tube_barcode').from_statement(query).all()
            tube_barcodes = set()
            for record in result: tube_barcodes.add(record[0])
            if len(tube_barcodes) < 2: raise ValueError('no tubes found')
            self.requested_tubes = list(tube_barcodes)
            self._continue_setup()
            zip_stream = self.tool.get_result()
            self.assert_is_not_none(zip_stream)
            self._check_warning_messages('You have requested multiple tubes ' \
                                        'for the same molecule design pool ID!')

    def _test_invalid_requested_tubes(self):
        self._continue_setup()
        self.requested_tubes = dict()
        self._test_and_expect_errors('The requested tubes list must be a ' \
                                     'list object')
        self.requested_tubes = [1, 3]
        self._test_and_expect_errors('The requested tube barcode must be a ' \
                                     'basestring object')

    def _test_no_preparation_layout(self):
        self._continue_setup()
        if not self.iso_job is None: self.iso = self.iso_job.isos[0]
        self.iso.rack_layout = None
        self._test_and_expect_errors('Could not find preparation layout!')

    def _test_invalid_preparation_layout(self, rack_shape):
        self._continue_setup()
        if not self.iso_job is None: self.iso = self.iso_job.isos[0]
        self.iso.rack_layout = RackLayout(shape=rack_shape)
        self._test_and_expect_errors('Error when trying to convert ' \
                                     'preparation layout')

    def _test_unsupported_rack_shape(self, rack_shape):
        self._continue_setup()
        if not self.iso_job is None: self.iso = self.iso_job.isos[0]
        self.iso.rack_layout.shape = rack_shape
        self._test_and_expect_errors('Unsupported rack shape')

    def _test_tube_picker_failure(self):
        self._continue_setup()
        if not self.iso_job is None: self.iso = self.iso_job.isos[0]
        converter = PrepIsoLayoutConverter(rack_layout=self.iso.rack_layout,
                                           log=self.silent_log)
        prep_layout = converter.get_result()
        for prep_pos in prep_layout.working_positions():
            if prep_pos.is_mock: continue
            if not prep_pos.parent_well is None: continue
            prep_pos.prep_concentration = 25000
            prep_pos.required_volume = 500
        self.iso.rack_layout = prep_layout.create_rack_layout()
        self._test_and_expect_errors('Error when trying to pick tubes for ' \
                                     'molecule design pools.')

    def _test_non_empty_rack(self, barcode):
        self._continue_setup()
        stock_rack = self.racks[barcode]
        tube_specs = self._get_entity(ITubeSpecs)
        tube = Tube(specs=tube_specs, status=get_item_status_managed(),
                    barcode='11101')
        ContainerLocation(container=tube, rack=stock_rack,
                          position=get_rack_position_from_label('A1'))
        stock_rack.containers.append(tube)
        self._test_and_expect_errors('The following racks you have chosen ' \
                                     'are not empty')


class IsoXL20WorklistGenerator96TestCase(IsoXL20WorklistGeneratorTestCase):

    def set_up(self):
        IsoXL20WorklistGeneratorTestCase.set_up(self)
        self.VALID_FILE = 'valid_file_96.xls'
        self.VALID_FILE_MANUAL = 'valid_manual.xls'
        self.experiment_type_id = EXPERIMENT_SCENARIOS.OPTIMISATION
        self.destination_rack_barcode = self.destination_rack_map[0]
        self.pool_id = 205230

    def tear_down(self):
        IsoXL20WorklistGeneratorTestCase.tear_down(self)
        del self.destination_rack_barcode
        del self.VALID_FILE_MANUAL

    def _create_tool(self):
        self.tool = IsoXL20WorklistGenerator96(iso=self.iso,
                    destination_rack_barcode=self.destination_rack_barcode,
                    excluded_racks=self.excluded_racks,
                    requested_tubes=self.requested_tubes)

    def _set_iso_or_iso_job(self):
        self.iso = self.generated_isos[0]

    def __check_racks(self, number_transfers=4):
        self.assert_equal(len(self.iso.iso_sample_stock_racks), 1)
        issr = self.iso.iso_sample_stock_racks[0]
        worklist = issr.planned_worklist
        self.assert_equal(len(worklist.planned_transfers), number_transfers)
        self.assert_equal(issr.sector_index, 0)
        self.assert_equal(issr.iso.label, self.iso.label)
        self.assert_is_not_none(self.iso.preparation_plate)
        found_labels = []
        for iap in self.iso.iso_aliquot_plates:
            found_labels.append(iap.plate.label)
        self.assert_equal(sorted(found_labels),
                          sorted(self.aliquot_plate_labels))

    def test_result_opti(self):
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        self._check_successfull_run(zip_stream, expected_tube_number=4)
        self.__check_racks()

    def test_result_manual(self):
        self.VALID_FILE = self.VALID_FILE_MANUAL
        self.experiment_type_id = EXPERIMENT_SCENARIOS.MANUAL
        self.aliquot_plate_labels = []
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        self._check_successfull_run(zip_stream, expected_tube_number=3)
        self.__check_racks(number_transfers=3)

    def test_excluded_racks(self):
        self._test_excluded_racks()

    def test_requested_tubes(self):
        self._test_requested_tubes()
        self.__check_racks()

    def test_missing_floating_design(self):
        self.VALID_FILE = 'valid_file_96_floatings.xls'
        self.pool_id = 205230
        self._test_missing_floating_sample()
        self.__check_racks(number_transfers=3)

    def test_invalid_iso(self):
        self._continue_setup()
        self.iso = self.iso.iso_request
        self._test_and_expect_errors('The entity must be a Iso object')

    def test_invalid_barcode(self):
        self._continue_setup()
        self.destination_rack_barcode = 13
        self._test_and_expect_errors('The rack barcode must be a ' \
                                     'basestring object')

    def test_invalid_excluded_racks(self):
        self._test_invalid_excluded_racks()

    def test_invalid_requested_tubes(self):
        self._test_invalid_requested_tubes()

    def test_no_preparation_layout(self):
        self._test_no_preparation_layout()

    def test_invalid_preparation_layout(self):
        self._test_invalid_preparation_layout(rack_shape=get_96_rack_shape())

    def test_unsupported_rack_shape(self):
        self._test_unsupported_rack_shape(rack_shape=get_384_rack_shape())

    def test_tube_picker_failure(self):
        self._test_tube_picker_failure()

    def test_unknown_rack(self):
        self._continue_setup()
        self.destination_rack_barcode = '02444009'
        self._test_and_expect_errors()

    def test_non_empty_rack(self):
        self._test_non_empty_rack(self.destination_rack_barcode)


class IsoXL20WorklistGenerator384SamplesTestCase(
                                            IsoXL20WorklistGeneratorTestCase):

    def set_up(self):
        IsoXL20WorklistGeneratorTestCase.set_up(self)
        self.VALID_FILE = self.VALID_FILE_384_SCREEN_SINGLE
        self.VALID_FILE_384_SCREEN = 'valid_file_384_screen.xls'
        self.VALID_FILE_384_OPTI = 'valid_file_384_opti.xls'
        self.experiment_type_id = EXPERIMENT_SCENARIOS.SCREENING
        self.enforce_cybio_compatibility = False
        self.aliquot_plate_labels = ['xl20_test#1_a1', 'xl20_test#1_a2']
        self.pool_id = 205235 # floating pool with at lease 2 stock samples

    def tear_down(self):
        IsoXL20WorklistGeneratorTestCase.tear_down(self)
        del self.enforce_cybio_compatibility
        del self.VALID_FILE_384_SCREEN
        del self.VALID_FILE_384_OPTI

    def _create_tool(self):
        self.tool = IsoXL20WorklistGenerator384Samples(iso=self.iso,
                destination_rack_barcode_map=self.destination_rack_map,
                excluded_racks=self.excluded_racks,
                requested_tubes=self.requested_tubes,
                enforce_cybio_compatibility=self.enforce_cybio_compatibility)

    def _set_iso_or_iso_job(self):
        self.iso = self.generated_isos[0]

    def __check_racks(self, number_racks):
        ssr = self.iso.iso_sample_stock_racks
        self.assert_equal(len(ssr), number_racks)
        sector_indices = []
        for issr in ssr:
            worklist = issr.planned_worklist
            self.assert_not_equal(len(worklist.planned_transfers), 0)
            si = issr.sector_index
            sector_indices.append(si)
            if number_racks == 4:
                marker = 'Q%i' % (si + 1)
                self.assert_true(marker in worklist.label)
            else:
                self.assert_equal(si, 0)
                suffix = StockTransferWorklistGenerator384Single.WORKLIST_SUFFIX
                self.assert_true(suffix in worklist.label)
            self.assert_equal(issr.iso.label, self.iso.label)
        for i in range(number_racks):
            self.assert_true(i in sector_indices)
        self.assert_is_not_none(self.iso.preparation_plate)
        found_labels = []
        for iap in self.iso.iso_aliquot_plates:
            found_labels.append(iap.plate.label)
        self.assert_equal(sorted(found_labels),
                          sorted(self.aliquot_plate_labels))

    def test_result_single_rack(self):
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        self._check_warning_messages('The system will only prepare one ' \
                                     'stock rack.')
        self._check_successfull_run(zip_stream, expected_tube_number=67)
        self.__check_racks(number_racks=1)
        # test enforce multiple racks
        self.enforce_cybio_compatibility = True
        self.iso.iso_sample_stock_racks = []
        self._create_tool()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        warnings = ' '.join(self.tool.get_messages())
        self.assert_false('The system will only prepare one stock rack.' \
                          in warnings)
        self._check_successfull_run(zip_stream, expected_tube_number=67)
        self.__check_racks(number_racks=4)

    def test_result_all_quadrants(self):
        self.VALID_FILE = self.VALID_FILE_384_SCREEN
        self.aliquot_plate_labels = ['xl20_test#1_a1',
                                     'xl20_test#1_a2']
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        self._check_successfull_run(zip_stream, expected_tube_number=216)
        self.__check_racks(number_racks=4)

    def test_excluded_racks(self):
        # set a floating pool as stock sample and set to false
        self._test_excluded_racks(causes_failure=False)

    def test_requested_tubes(self):
        self._test_requested_tubes()
        self.__check_racks(number_racks=1)

    def test_result_missing_floating(self):
        self._test_missing_floating_sample()

    def test_result_multiple_sectors(self):
        self.VALID_FILE = 'valid_file_384_screen_multi_sector.xls'
        self.aliquot_plate_labels = ['screen_multi#1_a1',
                                     'screen_multi#1_a2']
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        self._check_warning_messages('The system will only prepare one ' \
                                     'stock rack.')
        self._check_successfull_run(zip_stream, expected_tube_number=46)
        self.__check_racks(number_racks=1)
        # test enforce multiple racks
        self.enforce_cybio_compatibility = True
        self._create_tool()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        warnings = ' '.join(self.tool.get_messages())
        self.assert_false('The system will only prepare one stock rack.' \
                          in warnings)
        self._check_successfull_run(zip_stream, expected_tube_number=46)
        self._check_warning_messages('There is only one source rack because ' \
                'the target wells for the stock transfer are all located ' \
                'in sector 3')
        # we still get only one sample stock rack because there is only
        # one sector for the parent wells
        ssr = self.iso.iso_sample_stock_racks
        self.assert_equal(len(ssr), 1)
        issr = ssr[0]
        self.assert_equal(issr.sector_index, 2)

    def test_result_optimisation(self):
        self.VALID_FILE = self.VALID_FILE_384_OPTI
        self.aliquot_plate_labels = ['test_iso#1']
        self.experiment_type_id = EXPERIMENT_SCENARIOS.OPTIMISATION
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        self._check_successfull_run(zip_stream, expected_tube_number=7)
        self.__check_racks(number_racks=1)

    def test_result_order_only(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.ORDER_ONLY
        self.aliquot_plate_labels = ['all_sorts_of_pools#1']
        self.VALID_FILE = 'valid_order.xls'
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        self._check_successfull_run(zip_stream, expected_tube_number=4)
        self.__check_racks(number_racks=1)
        self._check_warning_messages('There is only 4 molecule design pools ' \
             'in the stock rack. The system will only prepare one stock rack')

    def test_no_requested_molecules(self):
        self._continue_setup()
        converter = PrepIsoLayoutConverter(rack_layout=self.iso.rack_layout,
                                           log=self.silent_log)
        prep_layout = converter.get_result()
        for prep_pos in prep_layout.working_positions():
            if prep_pos.is_floating:
                prep_pos.molecule_design_pool = None
                prep_pos.position_type = None
                prep_pos.stock_rack_barcode = None
                prep_pos.stock_tube_barcode = None
        self.iso.rack_layout = prep_layout.create_rack_layout()
        self._test_and_expect_errors('Did not find any floating positions ' \
                                     'in this layout')

    def test_invalid_iso(self):
        self._continue_setup()
        self.iso = self.iso.iso_request
        self._test_and_expect_errors('The entity must be a Iso object')

    def test_invalid_barcode_map(self):
        self._continue_setup()
        barcodes = self.destination_rack_map.values()
        self.destination_rack_map = []
        self._test_and_expect_errors('The destination rack barcode map must ' \
                                     'be a dict object')
        self.destination_rack_map = dict(A=barcodes[0])
        self._test_and_expect_errors('The sector index must be a int object')
        self.destination_rack_map = {0 : 248}
        self._test_and_expect_errors('The rack barcode must be a basestring')
        self.destination_rack_map = dict()
        self._test_and_expect_errors('There are no barcodes in the ' \
                                     'destination rack map!')

    def test_invalid_excluded_racks(self):
        self._test_invalid_excluded_racks()

    def test_invalid_requested_tubes(self):
        self._test_invalid_requested_tubes()

    def test_no_preparation_layout(self):
        self._test_no_preparation_layout()

    def test_invalid_preparation_layout(self):
        self._test_invalid_preparation_layout(rack_shape=get_384_rack_shape())

    def test_unsupported_rack_shape(self):
        self._test_unsupported_rack_shape(rack_shape=get_96_rack_shape())

    def test_tube_picker_failure(self):
        self._test_tube_picker_failure()

    def test_association_error(self):
        self._continue_setup()
        converter = PrepIsoLayoutConverter(rack_layout=self.iso.rack_layout,
                                           log=self.silent_log)
        prep_layout = converter.get_result()
        for prep_pos in prep_layout.working_positions():
            if prep_pos.is_mock: continue
            prep_pos.prep_concentration = 1000
            prep_pos.required_volume = 3
            break
        self.iso.rack_layout = prep_layout.create_rack_layout()
        self._test_and_expect_errors('Error when trying to determine ' \
                                     'associations')

    def test_unknown_rack(self):
        self._continue_setup()
        self.destination_rack_map[0] = '02444009'
        self._test_and_expect_errors()

    def test_non_empty_rack(self):
        self._test_non_empty_rack(self.destination_rack_map[2])


class IsoJobTubeHandlerTestCase(IsoXL20WorklistGeneratorTestCase):

    def set_up(self):
        IsoXL20WorklistGeneratorTestCase.set_up(self)
        self.VALID_FILE = self.VALID_FILE_384_SCREEN_SINGLE
        self.experiment_type_id = EXPERIMENT_SCENARIOS.SCREENING
        self.destination_rack_barcode = self.destination_rack_map[0]
        self.number_isos = 2
        self.job_type = self._get_entity(IJobType, 'iso-batch')
        # pool IDs must be sorted ASC
        self.position_data = dict(A1=(205200, ['C3', 'F3', 'I3']),
                                  A2=(205201, ['C4', 'F4', 'I4']),
                                  A3=(205202, ['C5', 'F5', 'I5']),
                                  A4=(205204, ['C7', 'F7', 'I7']),
                                  A5=(205206, ['C8', 'F8', 'I8']),
                                  A6=(205207, ['C9', 'F9', 'I9']),
                                  A7=(205230, ['C6', 'F6', 'I6']))
        self.pool_id = 205230

    def tear_down(self):
        IsoXL20WorklistGeneratorTestCase.tear_down(self)
        del self.destination_rack_barcode
        del self.job_type
        del self.position_data

    def _set_iso_or_iso_job(self):
        self.iso_job = IsoJob(label='xl20_test_job',
                              job_type=self.job_type, isos=self.generated_isos)

    def _test_invalid_iso_job(self, iso_job_name):
        self._continue_setup()
        self.iso_job.isos = []
        self._test_and_expect_errors('There are no ISOs in this ISO job!')
        self.iso_job = self.generated_isos
        self._test_and_expect_errors('The %s must be a IsoJob object' \
                                     % iso_job_name)


class IsoXL20WorklistGenerator384ControlsTestCase(IsoJobTubeHandlerTestCase):

    def _create_tool(self):
        self.tool = IsoXL20WorklistGenerator384Controls(iso_job=self.iso_job,
                        destination_rack_barcode=self.destination_rack_barcode,
                        excluded_racks=self.excluded_racks,
                        requested_tubes=self.requested_tubes)

    def __check_racks(self):
        icsr = self.iso_job.iso_control_stock_rack
        self.assert_is_not_none(icsr)
        worklist = icsr.planned_worklist
        self.assert_equal(len(worklist.planned_transfers), 21)
        self.assert_is_not_none(icsr.rack_layout)
        self.assert_equal(len(icsr.rack_layout.tagged_rack_position_sets), 7)
        self.assert_equal(icsr.iso_job.label, self.iso_job.label)
        for iso in self.iso_job:
            self.assert_is_not_none(iso.preparation_plate)
            self.assert_equal(len(iso.iso_aliquot_plates), 0)

    def test_result(self):
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        self._check_successfull_run(zip_stream, expected_tube_number=7)
        self.__check_racks()

    def test_excluded_racks(self):
        self._test_excluded_racks()

    def test_requested_tubes(self):
        self._test_requested_tubes()
        self.__check_racks()

    def test_missing_floating_design(self):
        # we should not get any warning because floating positions are not
        # relevant for control stock racks
        with RdbContextManager() as session:
            self.pool_id = 205205
            self._set_excluded_racks(session)
            self._continue_setup()
            zip_stream = self.tool.get_result()
            self.assert_is_not_none(zip_stream)
            warnings = self.tool.get_messages()
            self.assert_false('The following molecule designs are ' \
                              'put back into the queue' in warnings)

    def test_invalid_iso_job(self):
        self._test_invalid_iso_job('entity')

    def test_invalid_excluded_racks(self):
        self._test_invalid_excluded_racks()

    def test_invalid_requested_tubes(self):
        self._test_invalid_requested_tubes()

    def test_finder_failure(self):
        self._continue_setup()
        for iso in self.iso_job.isos:
            iso.rack_layout = RackLayout(shape=get_384_rack_shape())
            break
        self._test_and_expect_errors('Error when trying to find control rack ' \
                                     'layout and requested molecules.')

    def test_unsupported_rack_shape(self):
        self._test_unsupported_rack_shape(rack_shape=get_96_rack_shape())

    def test_tube_picker_failure(self):
        self.number_isos = 1
        self._test_tube_picker_failure()

    def test_no_controls(self):
        self.number_isos = 1
        self._continue_setup()
        iso = self.iso_job.isos[0]
        converter = PrepIsoLayoutConverter(rack_layout=iso.rack_layout,
                                           log=self.silent_log)
        prep_layout = converter.get_result()
        for pp in prep_layout.working_positions():
            if pp.is_mock: continue
            pp.position_type = IsoParameters.FLOATING_TYPE_VALUE
        iso.rack_layout = prep_layout.create_rack_layout()
        self._test_and_expect_errors('Could not find control positions for ' \
                'this job. The molecule design pools are all covered by the ' \
                'sample stock racks.')

    def test_unknown_rack(self):
        self._continue_setup()
        self.destination_rack_barcode = '02444009'
        self._test_and_expect_errors()

    def test_invalid_type(self):
        self._continue_setup()
        self.experiment_metadata.experiment_metadata_type = \
                                        get_experiment_type_robot_optimisation()
        self._test_and_expect_errors('You cannot create a control stock rack ' \
                'for optimisation with robot-support scenarios! Control ' \
                'stock racks are only available for screening cases!')

    def test_non_empty_rack(self):
        self._test_non_empty_rack(self.destination_rack_barcode)


class IsoControlLayoutFinderTestCase(IsoJobTubeHandlerTestCase):

    def set_up(self):
        IsoJobTubeHandlerTestCase.set_up(self)
        self.log = TestingLog()
        self.transfer_volume = 1.2
        self.takeout_volume = 7.2

    def tear_down(self):
        IsoJobTubeHandlerTestCase.tear_down(self)
        del self.log
        del self.transfer_volume
        del self.takeout_volume

    def _create_tool(self):
        self.tool = IsoControlLayoutFinder(iso_job=self.iso_job, log=self.log)

    def test_result(self):
        self._continue_setup()
        control_layout = self.tool.get_result()
        self.assert_is_not_none(control_layout)
        self.assert_equal(len(control_layout), 7)
        # Check control layout
        for rack_pos, control_pos in control_layout.iterpositions():
            pos_data = self.position_data[rack_pos.label]
            self.assert_equal(pos_data[0], control_pos.molecule_design_pool_id)
            trg_labels = pos_data[1]
            self.assert_equal(len(control_pos.transfer_targets), 3)
            for tt in control_pos.transfer_targets:
                self.assert_true(tt.position_label in trg_labels)
                self.assert_equal(tt.transfer_volume, self.transfer_volume)
        # Check requested stock samples
        req_stock_samples = self.tool.get_requested_stock_samples()
        self.assert_is_not_none(req_stock_samples)
        self.assert_equal(len(req_stock_samples), 7)
        for rss in req_stock_samples:
            trg_label = rss.target_position.label
            expected_md = self.position_data[trg_label][0]
            self.assert_equal(expected_md, rss.pool.id)
            self.assert_equal(round(rss.take_out_volume, 1),
                              self.takeout_volume)

    def test_invalid_iso_job(self):
        self._test_invalid_iso_job('ISO job')

    def test_invalid_preparation_layout(self):
        self._test_invalid_preparation_layout(rack_shape=get_384_rack_shape())

    def test_unsupported_rack_shape(self):
        self._test_unsupported_rack_shape(rack_shape=get_96_rack_shape())

    def test_inconsistent_controls(self):
        self._continue_setup()
        iso = self.iso_job.isos[0]
        converter = PrepIsoLayoutConverter(rack_layout=iso.rack_layout,
                                           log=self.silent_log)
        prep_layout = converter.get_result()
        original_concentration = None
        for prep_pos in prep_layout.working_positions():
            original_concentration = prep_pos.prep_concentration
            prep_pos.prep_concentration = original_concentration + 500
        iso.rack_layout = prep_layout.create_rack_layout()
        self._test_and_expect_errors('The preparation layouts of the ' \
                                     'different ISOs are inconsistent')
        first_pool = None
        replacer_pool = 205210
        for prep_pos in prep_layout.working_positions():
            prep_pos.prep_concentration = original_concentration
            if first_pool is None:
                prep_pos.molecule_design_pool = replacer_pool
        iso.rack_layout = prep_layout.create_rack_layout()
        self._test_and_expect_errors('The preparation layouts of the ' \
                                     'different ISOs are inconsistent')
