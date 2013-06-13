"""
Tests for tools involved in the generation of pool stock sample libraries.

AAB
"""
from thelma.automation.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.tools.semiconstants import get_positions_for_shape
from thelma.automation.tools.poolcreation.generation \
    import PoolCreationLibraryGenerator
from thelma.automation.tools.poolcreation.generation \
    import PoolCreationWorklistGenerator
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.utils import get_user
from thelma.tests.tools.tooltestingutils import FileReadingTestCase
from thelma.tests.tools.tooltestingutils import TestingLog


class PoolCreationLibraryGenerationTestCase(FileReadingTestCase):

    def set_up(self):
        FileReadingTestCase.set_up(self)
        self.target_volume = 30
        self.target_concentration = 10000 # 10 uM
        self.iso_request_label = 'debcontrols'
        self.exp_buffer_volume = 24

    def tear_down(self):
        FileReadingTestCase.tear_down(self)
        del self.target_volume
        del self.target_concentration
        del self.iso_request_label
        del self.exp_buffer_volume

    def _check_worklist_series(self, worklist_series):
        self.assert_is_not_none(worklist_series)
        self.assert_equal(len(worklist_series), 1)
        wl = worklist_series.get_worklist_for_index(
                            PoolCreationWorklistGenerator.BUFFER_WORKLIST_INDEX)
        self.assert_equal(wl.label, 'debcontrols_stock_buffer')
        self.assert_equal(len(wl.executed_worklists), 0)
        self.assert_equal(len(wl.planned_transfers), 96)
        found_positions = []
        for pt in wl.planned_transfers:
            self._compare_transfer_volume(pt, self.exp_buffer_volume)
            self.assert_equal(pt.type, TRANSFER_TYPES.CONTAINER_DILUTION)
            self.assert_equal(pt.diluent_info,
                              PoolCreationWorklistGenerator.DILUENT_INFO)
            found_positions.append(pt.target_position)
        self._compare_pos_sets(found_positions,
                           get_positions_for_shape(RACK_SHAPE_NAMES.SHAPE_96))


class PoolCreationLibraryGeneratorTestCase(
                                        PoolCreationLibraryGenerationTestCase):

    def set_up(self):
        PoolCreationLibraryGenerationTestCase.set_up(self)
        self.TEST_FILE_PATH = 'thelma:tests/tools/poolcreation/generation/'
        self.VALID_FILE = 'valid_file.xls'
        self.exp_pool_ids = [1063102, 1058382, 1064324, 1065599, 1059807,
                    1060579, 1065602, 1063754, 1059776, 1060625, 1065628]
        self.requester = get_user('brehm')

    def tear_down(self):
        PoolCreationLibraryGenerationTestCase.tear_down(self)
        del self.exp_pool_ids
        del self.requester

    def _create_tool(self):
        self.tool = PoolCreationLibraryGenerator(
                         iso_request_label=self.iso_request_label,
                         stream=self.stream, requester=self.requester,
                         target_volume=self.target_volume,
                         target_concentration=self.target_concentration)

    def _continue_setup(self, file_name=None):
        PoolCreationLibraryGenerationTestCase._continue_setup(self, file_name)
        self._create_tool()

    def __check_result(self, number_plates=1):
        self._continue_setup()
        library = self.tool.get_result()
        self.assert_is_not_none(library)
        self.assert_equal(library.label, self.iso_request_label)
        # check ISO request
        iso_request = library.iso_request
        self.assert_equal(iso_request.plate_set_label, self.iso_request_label)
        self.assert_equal(len(iso_request.isos), 0)
        self.assert_equal(iso_request.requester, self.requester)
        self.assert_is_none(iso_request.experiment_metadata)
        self.assert_equal(iso_request.number_plates, number_plates)
        exp_positions = get_positions_for_shape(RACK_SHAPE_NAMES.SHAPE_96)
        rack_layout = iso_request.iso_layout
        self._compare_pos_sets(rack_layout.get_positions(), exp_positions)
        # check worklist series
        self._check_worklist_series(iso_request.worklist_series)
        # check pool set
        pool_set = library.molecule_design_pool_set
        if isinstance(self.exp_pool_ids, list):
            ids = []
            self.assert_equal(len(pool_set), len(self.exp_pool_ids))
            for pool in pool_set: ids.append(pool.id)
            self.assert_equal(sorted(self.exp_pool_ids), sorted(ids))
        else: # compare only pool number
            self.assert_equal(len(pool_set), self.exp_pool_ids)

    def __test_file_and_expect_error(self, file_name, msg):
        self._continue_setup(file_name)
        self._test_and_expect_errors(msg)

    def test_result(self):
        self.__check_result()

    def test_result_several_plates(self):
        self.VALID_FILE = 'valid_file_120_pools.xls'
        self.exp_pool_ids = 120
        self.__check_result(number_plates=2)

    def test_invalid_input_values(self):
        ir_label = self.iso_request_label
        self.iso_request_label = 123
        self._test_and_expect_errors('The ISO request label must be a ' \
                                     'basestring object (obtained: int).')
        self.iso_request_label = ir_label
        req = self.requester
        self.requester = None
        self._test_and_expect_errors('The requester must be a User object ' \
                                     '(obtained: NoneType).')
        self.requester = req
        self.target_volume = 3.5
        self._test_and_expect_errors('The target volume for the pool tubes ' \
                             'must be a positive number (obtained: 3.5).')
        self.target_volume = 30
        self.target_concentration = 0
        self._test_and_expect_errors('The target concentration for the pool ' \
                             'tubes must be a positive number (obtained: 0).')

    def test_pool_set_parser_error(self):
        self.__test_file_and_expect_error('no_pools.xls',
                                          'Unable to parse pool set!')

    def test_worklist_generation_failure(self):
        self.target_volume = 5
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to generate worklist ' \
                                     'series.')


class PoolCreationWorklistGeneratorTestCase(
                                PoolCreationLibraryGenerationTestCase):

    def set_up(self):
        PoolCreationLibraryGenerationTestCase.set_up(self)
        self.log = TestingLog()
        self.stock_concentration = 50000 # 50 uM
        self.number_designs = 3

    def tear_down(self):
        PoolCreationLibraryGenerationTestCase.tear_down(self)
        del self.log
        del self.stock_concentration
        del self.number_designs

    def _create_tool(self):
        self.tool = PoolCreationWorklistGenerator(log=self.log,
                              stock_concentration=self.stock_concentration,
                              number_designs=self.number_designs,
                              target_volume=self.target_volume,
                              target_concentration=self.target_concentration,
                              iso_request_label=self.iso_request_label)

    def test_result(self):
        self._create_tool()
        worklist_series = self.tool.get_result()
        self._check_worklist_series(worklist_series)

    def test_result_number_designs(self):
        self.number_designs = 2
        # the buffer volume is (mathematically) always the same, regardless
        # of the number of designs
        # the transfer volumes change, though
        self._create_tool()
        worklist_series = self.tool.get_result()
        self._check_worklist_series(worklist_series)

    def test_invalid_input(self):
        self.stock_concentration = 'default'
        self._test_and_expect_errors('The stock concentration for the ' \
                     'single source molecules must be a positive number ' \
                     '(obtained: default)')
        self.stock_concentration = 50000
        self.number_designs = 0.5
        self._test_and_expect_errors('The number of designs per pool must be ' \
                                     'a positive number (obtained: 0.5)')
        self.number_designs = 3
        self.target_volume = -2
        self._test_and_expect_errors('The target volume for the pool tubes ' \
                                     'must be a positive number (obtained: -2)')
        self.target_volume = 30
        self.target_concentration = -2
        self._test_and_expect_errors('The target concentration for the pool ' \
                             'tubes must be a positive number (obtained: -2)')
        self.target_concentration = 10000
        self.iso_request_label = 123
        self._test_and_expect_errors('The ISO request label must be a ' \
                                     'basestring object (obtained: int)')

    def test_conc_too_high(self):
        self.target_concentration = (self.stock_concentration \
                                     * (self.number_designs + 1))
        self._test_and_expect_errors('The requested target concentration ' \
             '(200000 nM) cannot be achieved since it would require a ' \
             'concentration of 66666.7 nM for each single design in the ' \
             'pool. However, the stock concentration for this design type is ' \
             'only 50000 nM.')

    def test_conc_too_low_for_volume(self):
        self.target_concentration = (self.target_concentration / 10)
        self._test_and_expect_errors('The target volume you have requested ' \
             '(30 ul) is too low for the required dilution (1:150) since ' \
             'the CyBio cannot pipet less than 1.0 ul per transfer. The ' \
             'volume that has to be taken from the stock for each single ' \
             'molecule design would be lower that that. Increase the target ' \
             'volume to 150.0 ul or increase the target concentration')

    def test_conc_to_large_for_volume(self):
        self.target_concentration = (self.target_concentration * 5)
        self.target_volume = 10
        self._test_and_expect_errors('The target volume you have requested ' \
             '(10 ul) is too low for the concentration you have ordered ' \
             '(50000 uM) since it would require already 3.4 ul per molecule ' \
             'design (10.2 ul in total) to achieve the requested ' \
             'concentration. Increase the volume or lower the concentration, ' \
             'please.')

    def test_buffer_volume_too_low(self):
        self.target_concentration = (self.target_concentration * 4)
        self.target_volume = 5
        self._test_and_expect_errors('The target volume you have requested ' \
             '(5 ul) is too low for the required dilution since the CyBio ' \
             'cannot pipet less than 1.0 ul per transfer (with the current ' \
             'values it would need to pipet 0.8 ul buffer). Please increase ' \
             'the target volume to 20 ul or lower the target concentration.')
