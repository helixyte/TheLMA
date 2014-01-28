"""
Tests for the manual experiment executors.

AAB
"""
from thelma.automation.tools.experiment.manual import ExperimentManualExecutor
from thelma.automation.tools.metadata.base import TransfectionLayoutConverter
from thelma.models.racklayout import RackLayout
from thelma.models.utils import get_user
from thelma.tests.tools.experiment.utils import EXPERIMENT_TEST_DATA
from thelma.tests.tools.experiment.utils import ExperimentTestCase
from thelma.tests.tools.tooltestingutils import SilentLog
from thelma.tests.tools.tooltestingutils import TestingLog


class ExperimentManualExecutorTestCase(ExperimentTestCase):

    def set_up(self):
        ExperimentTestCase.set_up(self)
        self.log = TestingLog()
        self.executor_user = get_user('tondera')

    def tear_down(self):
        ExperimentTestCase.tear_down(self)
        del self.log

    def _create_tool(self):
        self.tool = ExperimentManualExecutor(experiment=self.experiment,
                                 user=self.executor_user, log=self.log)

    def __check_result(self, case_name):
        self._load_scenario(case_name)
        exp = self.tool.get_result()
        self.assert_is_not_none(exp)
        self._check_final_plates_final_state()
        self._check_source_plate_unaltered()
        self._check_no_worklist_executions()
        warnings = ' '.join(self.tool.get_messages())
        warn = 'This experiment is robot-compatible. Would you still like to ' \
               'use the manual update?'
        if EXPERIMENT_TEST_DATA.supports_mastermixes(self.case):
            self.assert_true(warn in warnings)
        else:
            self.assert_false(warn in warnings)
        self._check_iso_aliquot_plate_update()

    def test_case_order(self):
        self._test_case_order()

    def test_case_manual(self):
        self.__check_result(EXPERIMENT_TEST_DATA.CASE_MANUAL)

    def test_case_opti_with_mastermix(self):
        self.__check_result(EXPERIMENT_TEST_DATA.CASE_OPTI_MM)

    def test_case_opti_without_mastermix(self):
        self.__check_result(EXPERIMENT_TEST_DATA.CASE_OPTI_NO)

    def test_case_screen_with_mastermix(self):
        self.__check_result(EXPERIMENT_TEST_DATA.CASE_SCREEN_MM)

    def test_case_screen_no_mastermix(self):
        self.__check_result(EXPERIMENT_TEST_DATA.CASE_SCREEN_NO)

    def test_case_library_with_mastermix(self):
        self.__check_result(EXPERIMENT_TEST_DATA.CASE_LIBRARY_MM)

    def test_case_library_no_mastermix(self):
        self.__check_result(EXPERIMENT_TEST_DATA.CASE_LIBRARY_NO)

    def test_case_isoless(self):
        self.__check_result(EXPERIMENT_TEST_DATA.CASE_ISOLESS)

    def test_missing_floating(self):
        self._set_up_missing_floating()
        self.__check_result(self.case)

    def test_invalid_input_values(self):
        self._test_invalid_input_values()
        self.executor_user = None
        self._test_and_expect_errors('The user must be a User object ' \
                                     '(obtained: NoneType).')

    def test_invalid_experiment_type(self):
        self._test_invalid_experiment_type()

    def test_unknown_design_rack(self):
        self._test_unknown_design_rack()

    def test_previous_executor_with_source_plate(self):
        self._test_previous_executor_with_source_plate()

    def test_previous_execution_without_source_plate(self):
        self._test_previous_execution_without_source_plate()

    def test_verification_error(self):
        self._test_verification_error()

    def test_no_verification(self):
        self._test_no_verification()

    def test_design_rack_layout_conversion_error(self):
        self._load_scenario(EXPERIMENT_TEST_DATA.CASE_MANUAL)
        for edr in self.experiment.experiment_racks:
            edr.design_rack.rack_layout = RackLayout()
            break
        self._test_and_expect_errors('Could not get layout for design rack ')

    def test_missing_source_pool(self):
        self._load_scenario(EXPERIMENT_TEST_DATA.CASE_OPTI_NO)
        for edr in self.experiment.experiment_racks:
            dr = edr.design_rack
            if not dr.label == '1': continue
            converter = TransfectionLayoutConverter(rack_layout=dr.rack_layout,
                                log=SilentLog(), is_iso_request_layout=False)
            layout = converter.get_result()
            for tf_pos in layout.working_positions():
                tf_pos.molecule_design_pool = self._get_pool(330001)
                break
            dr.rack_layout = layout.create_rack_layout()
            break
        self._test_and_expect_errors('The following pools from design rack ' \
                         '1 could not be found on the source plate: 330001.')
