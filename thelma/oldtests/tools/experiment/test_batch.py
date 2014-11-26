"""
Test for batch experiment tools.

AAB
"""
from thelma.automation.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.semiconstants import RACK_SPECS_NAMES
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.semiconstants import get_experiment_type_order
from thelma.automation.tools.experiment import get_batch_executor
from thelma.automation.tools.experiment import get_batch_manual_executor
from thelma.automation.tools.experiment import get_batch_writer
from thelma.entities.racklayout import RackLayout
from thelma.entities.utils import get_user
from thelma.oldtests.tools.experiment.utils import EXPERIMENT_TEST_DATA
from thelma.oldtests.tools.experiment.utils import ExperimentTestCase

class _EXPERIMENT_BATCH_TEST_DATA(EXPERIMENT_TEST_DATA):

    @classmethod
    def get_experiment_label2(cls, case_name):
        return '%s_exp2' % (case_name)

    EXPERIMENT_PLATES_2 = {
                '1' : {'08880211' : 'exp2_ds1_c1', '08880212' : 'exp2_ds1_c2'},
                '2' : {'08880221' : 'exp2_ds2_c1', '08880222' : 'exp2_ds1_c2'}}


    FLOATING_MAP2 = {'md_001' : 205209, 'md_002' : 205210,
                     'md_003' : 205212, 'md_004' : 205214}

    ISO_LABEL_2 = 'testiso2'
    ISO_PLATE_BARCODE_2 = '09999990'
    ISO_PLATE_BARCODE_LIBRARY_2 = '07777712'
    ISO_PLATE_LABEL_2 = ISO_LABEL_2 + '_plate'

    @classmethod
    def get_experiment_plate_final_state_data2(cls, case_name):
        if case_name == cls.CASE_SCREEN_MM:
            fd = dict(b3=[205200, 10], b4=[205200, 20],
                      c3=[205201, 10], c4=[205201, 20],
                      d3=[205200, 10], d4=[205200, 20],
                      e3=[205201, 10], e4=[205201, 20],
                      f3=[None, None], f4=[None, None],
                      b5=[205209, 10], b6=[205209, 20],
                      c5=[205210, 10], c6=[205210, 20],
                      d5=[205212, 10], d6=[205212, 20],
                      e5=[205214, 10], e6=[205214, 20])
            return {'1' : fd, '2' : fd}
        elif case_name == cls.CASE_SCREEN_NO:
            fd = dict(b3=[205200, 10], b4=[205200, 20],
                      c3=[205201, 10], c4=[205201, 20],
                      d3=[205200, 10], d4=[205200, 20],
                      e3=[205201, 10], e4=[205201, 20],
                      f3=[None, None], f4=[None, None],
                      b5=[205209, 10], b6=[205209, 20],
                      c5=[205210, 10], c6=[205210, 20],
                      d5=[205212, 10], d6=[205212, 20],
                      e5=[205214, 10], e6=[205214, 20])
            return {'1' : fd, '2' : fd}
        elif case_name == cls.CASE_LIBRARY_MM:
            fd = dict(b2=[205201, 10], i10=[205201, 10],
                      d2=[330001, 10], k10=[330001, 10],
                      f2=[1056000, 10], m10=[1056000, 10],
                      h2=[None, None], o10=[None, None],
                      b3=[1068480, 10], b4=[1068481, 10],
                      c3=[1068482, 10])
            return {'1' : fd, '2' : fd}
        elif case_name == cls.CASE_LIBRARY_NO:
            fd = dict(b2=[205201, 30], i10=[205201, 30],
                      d2=[330001, 30], k10=[330001, 30],
                      f2=[1056000, 30], m10=[1056000, 30],
                      h2=[None, None], o10=[None, None],
                      b3=[1068480, 30], b4=[1068481, 30],
                      c3=[1068482, 30])
            return {'1' : fd, '2' : fd}
        return EXPERIMENT_TEST_DATA.get_experiment_plate_final_state_data(
                                                                    case_name)

    # case name - list with file names
    WORKLIST_FILES = {
            EXPERIMENT_TEST_DATA.CASE_OPTI_MM : [
                            'opti_mm_exp_biomek_optimem.csv',
                            'opti_mm_exp_biomek_reagent.csv',
                            'opti_mm_exp_biomek_transfer.csv',
                            'opti_mm_exp_reagent_instructions.csv',
                            'opti_mm_exp2_biomek_optimem.csv',
                            'opti_mm_exp2_biomek_reagent.csv',
                            'opti_mm_exp2_biomek_transfer.csv',
                            'opti_mm_exp2_reagent_instructions.csv'],
            EXPERIMENT_TEST_DATA.CASE_SCREEN_MM : [
                              'screen_mm_exp_biomek_optimem.csv',
                              'screen_mm_exp_biomek_reagent.csv',
                              'screen_mm_exp_cybio_transfers.txt',
                              'screen_mm_exp_reagent_instructions.csv',
                              'screen_mm_exp2_biomek_optimem.csv',
                              'screen_mm_exp2_biomek_reagent.csv',
                              'screen_mm_exp2_cybio_transfers.txt',
                              'screen_mm_exp2_reagent_instructions.csv'],
            EXPERIMENT_TEST_DATA.CASE_LIBRARY_MM : [
                               'lib_mm_exp_biomek_optimem.csv',
                               'lib_mm_exp_biomek_reagent.csv',
                               'lib_mm_exp_cybio_transfers.txt',
                               'lib_mm_exp_reagent_instructions.csv',
                               'lib_mm_exp2_biomek_optimem.csv',
                               'lib_mm_exp2_biomek_reagent.csv',
                               'lib_mm_exp2_cybio_transfers.txt',
                               'lib_mm_exp2_reagent_instructions.csv']}

    @classmethod
    def get_source_plate_final_plate_data_2(cls, case_name):
        if case_name == cls.CASE_OPTI_MM:
            return EXPERIMENT_TEST_DATA.get_source_plate_final_plate_data(
                                                                    case_name)
        elif case_name == cls.CASE_SCREEN_MM: # ISO volume is always 3.8
            return dict(b3=[205200, 70, 10.4], # ISO conc 560
                        b4=[205200, 140, 10.4], # ISO conc 1120
                        c3=[205201, 70, 10.4], # ISO conc 560
                        c4=[205201, 140, 10.4], # ISO conc 1120
                        d3=[205200, 70, 10.4], # ISO conc 560
                        d4=[205200, 140, 10.4], # ISO conc 1120
                        e3=[205201, 70, 10.4], # ISO conc 560
                        e4=[205201, 140, 10.4], # ISO conc 1120
                        f3=[None, None, 10.4],
                        f4=[None, None, 10.4],
                        b5=[205209, 70, 10.4], # ISO conc 560
                        b6=[205209, 140, 10.4], # ISO conc 1120
                        c5=[205210, 70, 10.4], # ISO conc 560
                        c6=[205210, 140, 10.4], # ISO conc 1120
                        d5=[205212, 70, 10.4], # ISO conc 560
                        d6=[205212, 140, 10.4], # ISO conc 1120
                        e5=[205214, 70, 10.4], # ISO conc 560
                        e6=[205214, 140, 10.4]) # ISO conc 1120
        elif case_name == cls.CASE_LIBRARY_MM:
            # ISO volume is always 4, ISO conc is always 1270 (1269) nM
            return dict(b2=[205201, 69.8, 52.8],
                        d2=[330001, 69.8, 52.8],
                        f2=[1056000, 69.8, 52.8],
                        h2=[None, None, 52.8],
                        i10=[205201, 69.8, 52.8],
                        k10=[330001, 69.8, 52.8],
                        m10=[1056000, 69.8, 52.8],
                        o10=[None, None, 52.8],
                        b3=[1068480, 69.8, 52.8],
                        b4=[1068481, 69.8, 52.8],
                        c3=[1068482, 69.8, 52.8])
        raise NotImplementedError('The values for this case are missing!')

class _ExperimentBatchTestCase(ExperimentTestCase):

    def set_up(self):
        ExperimentTestCase.set_up(self)
        self.case = _EXPERIMENT_BATCH_TEST_DATA.CASE_SCREEN_MM
        self.experiment2 = None
        self.iso_plate2 = None
        self.experiments = []

    def tear_down(self):
        ExperimentTestCase.tear_down(self)
        del self.experiment2
        del self.iso_plate2
        del self.experiments

    def _continue_setup(self, file_name=None):
        ExperimentTestCase._continue_setup(self, file_name=file_name)
        if _EXPERIMENT_BATCH_TEST_DATA.has_source_plate(self.case):
            self.__generate_second_iso_and_plate()
        if _EXPERIMENT_BATCH_TEST_DATA.has_experiments(self.case):
            self.__generate_second_experiment_and_plates()
        self.experiments = [self.experiment, self.experiment2]
        self._create_tool()

    def __generate_second_iso_and_plate(self):
        layout2 = self._generate_iso_layout(
                                    _EXPERIMENT_BATCH_TEST_DATA.FLOATING_MAP2)
        pool_set2 = self._generate_pool_set_from_iso_layout(layout2)
        iso2 = self._create_lab_iso(rack_layout=layout2.create_rack_layout(),
                       label=_EXPERIMENT_BATCH_TEST_DATA.ISO_LABEL_2,
                       molecule_design_pool_set=pool_set2,
                       iso_request=self.experiment_metadata.lab_iso_request)
        if self.library_generator is not None:
            # all plates have been filled an generated before
            lib_plate2 = self.library_generator.library_plates[2]
            self.iso_plate2 = lib_plate2.rack
            lib_plate2.iso = iso2
        else:
            self.iso_plate2 = self._generate_iso_plate(layout2, iso2)
            self.iso_plate2.barcode = \
                        _EXPERIMENT_BATCH_TEST_DATA.ISO_PLATE_BARCODE_2

    def __generate_second_experiment_and_plates(self):
        ps_name = _EXPERIMENT_BATCH_TEST_DATA.EXPERIMENT_PLATE_SPECS[self.case]
        plate_specs = RACK_SPECS_NAMES.from_name(ps_name)
        exp_label2 = _EXPERIMENT_BATCH_TEST_DATA.\
                     get_experiment_label2(self.case)
        self.experiment2 = self._create_experiment(label=exp_label2,
                                                   source_rack=self.iso_plate2,
                experiment_design=self.experiment_metadata.experiment_design)
        self._generate_experiment_plates(plate_specs,
                             _EXPERIMENT_BATCH_TEST_DATA.EXPERIMENT_PLATES_2,
                             self.experiment2)

    def _test_invalid_input_values(self):
        self._load_scenario(_EXPERIMENT_BATCH_TEST_DATA.CASE_OPTI_MM)
        ori_e = self.experiments
        self.experiments = dict()
        self._test_and_expect_errors('The experiment list must be a list ' \
                                     'object (obtained: dict).')
        self.experiments = []
        self._test_and_expect_errors('The experiment list is empty!')
        self.experiments = [1]
        self._test_and_expect_errors('The experiment must be a Experiment ' \
                                     'object (obtained: int).')
        self.experiments = ori_e


class ExperimentBatchManualExecutorTestCase(_ExperimentBatchTestCase):

    def set_up(self):
        _ExperimentBatchTestCase.set_up(self)
        self.executor_user = get_user('tondera')

    def _create_tool(self):
        self.tool = get_batch_manual_executor(experiments=self.experiments,
                                              user=self.executor_user)

    def __check_result(self, case_name):
        self._load_scenario(case_name)
        experiments = self.tool.get_result()
        self.assert_is_not_none(experiments)
        self.assert_equal(len(experiments), 2)
        self._check_no_worklist_executions()
        warnings = ' '.join(self.tool.get_messages())
        warn = 'This experiment is robot-compatible. Would you still like to ' \
               'use the manual update?'
        if EXPERIMENT_TEST_DATA.supports_mastermixes(self.case):
            self.assert_true(warn in warnings)
        else:
            self.assert_false(warn in warnings)
        # experiment 1
        self._check_final_plates_final_state()
        self._check_source_plate_unaltered()
        # experiment 2
        self._check_source_plate_unaltered(self.iso_plate2,
                                _EXPERIMENT_BATCH_TEST_DATA.FLOATING_MAP2)
        self._check_final_plates_final_state(
                    _EXPERIMENT_BATCH_TEST_DATA.\
                    get_experiment_plate_final_state_data2(self.case),
                    self.experiment2.experiment_racks)
        for edr in self.experiment2.experiment_racks:
            self.assert_equal(edr.rack.status.name, ITEM_STATUS_NAMES.MANAGED)
        self._check_iso_aliquot_plate_update(
                        {_EXPERIMENT_BATCH_TEST_DATA.ISO_PLATE_BARCODE_2,
                         _EXPERIMENT_BATCH_TEST_DATA.ISO_PLATE_BARCODE})

    def test_case_order(self):
        self._load_scenario(_EXPERIMENT_BATCH_TEST_DATA.CASE_ORDER)
        self._test_and_expect_errors('The experiment must be a Experiment ' \
                                     'object (obtained: NoneType).')
        ed = self._create_experiment_design(rack_shape=get_96_rack_shape(),
                            experiment_metadata=self.experiment_metadata)
        self.experiment = self._create_experiment(experiment_design=ed)
        self.experiment2 = self._create_experiment(experiment_design=ed)
        self.experiments = [self.experiment, self.experiment2]
        self._test_and_expect_errors('The type of this experiment is not ' \
                                     'supported by this tool')

    def test_case_manual(self):
        self.__check_result(_EXPERIMENT_BATCH_TEST_DATA.CASE_MANUAL)

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

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_invalid_experiment_type(self):
        self._test_invalid_experiment_type()

    def test_update_error(self):
        self._load_scenario(_EXPERIMENT_BATCH_TEST_DATA.CASE_MANUAL)
        self.experiment_metadata.lab_iso_request.rack_layout = RackLayout()
        self._test_and_expect_errors('Error when trying to update experiment')


class ExperimentBatchWorklistWriterTestCase(_ExperimentBatchTestCase):

    def _create_tool(self):
        self.tool = get_batch_writer(experiments=self.experiments)

    def __check_result(self, case_name):
        self._load_scenario(case_name)
        self._check_worklist_files(
                        _EXPERIMENT_BATCH_TEST_DATA.WORKLIST_FILES[self.case])

    def test_case_opti_with_mastermix(self):
        self.__check_result(_EXPERIMENT_BATCH_TEST_DATA.CASE_OPTI_MM)

    def test_case_screen_with_mastermix(self):
        self.__check_result(_EXPERIMENT_BATCH_TEST_DATA.CASE_SCREEN_MM)

    def test_case_library_with_mastermix(self):
        self.__check_result(_EXPERIMENT_BATCH_TEST_DATA.CASE_LIBRARY_MM)

    def test_no_mastermix_support(self):
        self._load_scenario(_EXPERIMENT_BATCH_TEST_DATA.CASE_OPTI_NO)
        self._test_and_expect_errors('This experiment is not ' \
                                     'Biomek-compatible.')
        self._check_error_messages('Error when trying to generate ' \
                                   'worklists for experiment')

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_invalid_experiment_type_and_writer_init_failure(self):
        self._load_scenario(_EXPERIMENT_BATCH_TEST_DATA.CASE_OPTI_MM)
        self.experiment_metadata.experiment_metadata_type = \
                                                get_experiment_type_order()
        self._test_and_expect_errors('This experiment type (ISO without ' \
                'experiment) does not support robot worklists!')

    def test_worklist_generation_failure(self):
        self._load_scenario(_EXPERIMENT_BATCH_TEST_DATA.CASE_OPTI_MM)
        self.experiment_metadata.lab_iso_request.rack_layout = RackLayout()
        self._test_and_expect_errors('Error when trying to generate ' \
                                     'worklists for experiment')


class ExperimentBatchExecutorTestCase(_ExperimentBatchTestCase):

    def set_up(self):
        _ExperimentBatchTestCase.set_up(self)
        self.executor_user = get_user('tondera')

    def _create_tool(self):
        self.tool = get_batch_executor(experiments=self.experiments,
                                       user=self.executor_user)

    def __check_result(self, case_name):
        self._load_scenario(case_name)
        experiments = self.tool.get_result()
        self.assert_is_not_none(experiments)
        self.assert_equal(len(experiments), 2)
         # experiment 1
        self._check_final_plates_final_state()
        self._check_source_plate_final_state()
        # experiment 2
        self._check_final_plates_final_state(
                    _EXPERIMENT_BATCH_TEST_DATA.\
                    get_experiment_plate_final_state_data2(self.case),
                    self.experiment2.experiment_racks)
        self._check_source_plate_final_state(
            _EXPERIMENT_BATCH_TEST_DATA.get_source_plate_final_plate_data_2(
                                                self.case), self.iso_plate2)
        for experiment in experiments:
            for edr in experiment.experiment_racks:
                self.assert_equal(edr.rack.status.name,
                                  ITEM_STATUS_NAMES.MANAGED)
        self._check_iso_aliquot_plate_update(
                        {_EXPERIMENT_BATCH_TEST_DATA.ISO_PLATE_BARCODE_2,
                         _EXPERIMENT_BATCH_TEST_DATA.ISO_PLATE_BARCODE})

    def test_case_opti_with_mastermix(self):
        self.__check_result(_EXPERIMENT_BATCH_TEST_DATA.CASE_OPTI_MM)

    def test_case_screen_with_mastermix(self):
        self.__check_result(_EXPERIMENT_BATCH_TEST_DATA.CASE_SCREEN_MM)

    def test_case_library_with_mastermix(self):
        self.__check_result(_EXPERIMENT_BATCH_TEST_DATA.CASE_LIBRARY_MM)

    def test_no_mastermix_support(self):
        self._load_scenario(_EXPERIMENT_BATCH_TEST_DATA.CASE_OPTI_NO)
        self._test_and_expect_errors('This experiment is not ' \
                                     'Biomek-compatible.')
        self._check_error_messages('Error when trying to update experiment ' \
                                    '"opti_no_exp"')

    def test_invalid_input_values(self):
        self._test_invalid_input_values()
        self.executor_user = None
        self._test_and_expect_errors('The user must be a User object ' \
                                     '(obtained: NoneType).')

    def test_invalid_experiment_type_and_writer_init_failure(self):
        self._load_scenario(_EXPERIMENT_BATCH_TEST_DATA.CASE_OPTI_MM)
        self.experiment_metadata.experiment_metadata_type = \
                                                get_experiment_type_order()
        self._test_and_expect_errors('This experiment type (ISO without ' \
                'experiment) does not support robot worklists!')

    def test_worklist_generation_failure(self):
        self._load_scenario(_EXPERIMENT_BATCH_TEST_DATA.CASE_OPTI_MM)
        self.experiment_metadata.lab_iso_request.rack_layout = RackLayout()
        self._test_and_expect_errors('Error when trying to update experiment')
