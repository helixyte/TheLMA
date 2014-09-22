"""
Test classes for experiment tools that provide mastermix support.

AAB
"""
from thelma.automation.tools.experiment import get_executor
from thelma.automation.tools.experiment import get_writer
from thelma.automation.tools.experiment.base import ExperimentTool
from thelma.automation.tools.experiment.mastermix \
    import ExperimentOptimisationWriterExecutor
from thelma.automation.tools.experiment.mastermix \
    import ExperimentScreeningWriterExecutor
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.utils import get_user
from thelma.oldtests.tools.experiment.utils import EXPERIMENT_TEST_DATA
from thelma.oldtests.tools.experiment.utils import ExperimentTestCase


class _ExperimentWriterExecutorTestCase(ExperimentTestCase):

    TEST_CLS = ExperimentTool

    def set_up(self):
        ExperimentTestCase.set_up(self)
        self.mode = self.TEST_CLS.MODE_PRINT_WORKLISTS
        self.executor_user = get_user('tondera')
        self.use_factory = True

    def tear_down(self):
        ExperimentTestCase.tear_down(self)
        del self.mode
        del self.use_factory

    def _create_tool(self):
        if not self.use_factory:
            kw = dict(experiment=self.experiment, user=self.executor_user,
                      mode=self.mode)
            self.tool = self.TEST_CLS(**kw)
        elif self.mode == self.TEST_CLS.MODE_PRINT_WORKLISTS:
            self.tool = get_writer(experiment=self.experiment)
        else:
            self.tool = get_executor(experiment=self.experiment,
                                     user=self.executor_user)

    def _test_and_expect_errors(self, msg=None):
        self.use_factory = False
        ExperimentTestCase._test_and_expect_errors(self, msg=msg)

    def _check_result(self, case_name=None):
        if case_name is None: case_name = self.case
        self._load_scenario(case_name)
        self.assert_equal(self.tool.__class__, self.TEST_CLS)
        if self.mode == self.TEST_CLS.MODE_PRINT_WORKLISTS:
            self.__check_writer_result()
        else:
            self.__check_executor_result()

    def __check_writer_result(self):
        self._check_worklist_files()
        # we cannot check worklist executions and the plate states because
        # this might have been altered due to worklist generation
        # (we did not abort the transaction)

    def __check_executor_result(self):
        ews = self.tool.get_result()
        self.assert_is_not_none(ews)
        self.__check_executed_worklists(ews)
        self._check_final_plates_final_state()
        self._check_source_plate_final_state()
        self._check_iso_aliquot_plate_update()

    def __check_executed_worklists(self, ews):
        self.assert_equal(len(ews),
                  EXPERIMENT_TEST_DATA.get_number_executed_worklists(self.case))
        wl_data = EXPERIMENT_TEST_DATA.get_worklist_details(self.case)
        exp_plate_barcodes = []
        for barcode_lookup in EXPERIMENT_TEST_DATA.EXPERIMENT_PLATES.values():
            exp_plate_barcodes.extend(barcode_lookup.keys())
        for ew in ews:
            pw = ew.planned_worklist
            exp_data = wl_data[pw.label]
            self.assert_equal(pw.pipetting_specs.name, exp_data[0])
            self.assert_equal(pw.transfer_type, exp_data[1])
            self.assert_equal(len(pw.planned_liquid_transfers), exp_data[2])
            elts = ew.executed_liquid_transfers
            num_elts = exp_data[3]
            if self.missing_floating_placeholder is not None and \
                    not pw.transfer_type == TRANSFER_TYPES.RACK_SAMPLE_TRANSFER:
                num_elts -= 2 # 2 target positions are missing
            self.assert_equal(len(elts), num_elts)
            self.__check_executed_liquid_transfers(pw.label, elts,
                                                   exp_plate_barcodes)

    def __check_executed_liquid_transfers(self, worklist_label, elts,
                                          experiment_plate_barcodes):
        source_plate_barcode = EXPERIMENT_TEST_DATA.ISO_PLATE_BARCODE
        if EXPERIMENT_TEST_DATA.is_library_testcase(self.case):
            source_plate_barcode = \
                                EXPERIMENT_TEST_DATA.ISO_PLATE_BARCODE_LIBRARY
        if EXPERIMENT_TEST_DATA.WORKLIST_MARKER_OPTIMEM in worklist_label:
            for elt in elts:
                self._check_executed_transfer(elt,
                                              TRANSFER_TYPES.SAMPLE_DILUTION)
                self.assert_equal(elt.target_container.location.rack.barcode,
                                  source_plate_barcode)
        elif EXPERIMENT_TEST_DATA.WORKLIST_MARKER_REAGENT in worklist_label:
            for elt in elts:
                self._check_executed_transfer(elt,
                                              TRANSFER_TYPES.SAMPLE_DILUTION)
                self.assert_equal(elt.target_container.location.rack.barcode,
                                  source_plate_barcode)
        elif EXPERIMENT_TEST_DATA.WORKLIST_MARKER_CELLS in worklist_label:
            trg_barcode = None
            for elt in elts:
                self._check_executed_transfer(elt,
                                              TRANSFER_TYPES.SAMPLE_DILUTION)
                trg_rack = elt.target_container.location.rack.barcode
                if trg_barcode is None:
                    trg_barcode = trg_rack
                else:
                    self.assert_equal(trg_barcode, trg_rack)
            self.assert_true(trg_barcode in experiment_plate_barcodes)
        elif EXPERIMENT_TEST_DATA.WORKLIST_MARKER_TRANSFER in worklist_label \
                and elts[0].transfer_type == TRANSFER_TYPES.SAMPLE_TRANSFER:
            trg_barcode = None
            for elt in elts:
                self._check_executed_transfer(elt,
                                              TRANSFER_TYPES.SAMPLE_TRANSFER)
                self.assert_equal(elt.source_container.location.rack.barcode,
                                  source_plate_barcode)
                trg_rack = elt.target_container.location.rack.barcode
                if trg_barcode is None:
                    trg_barcode = trg_rack
                else:
                    self.assert_equal(trg_barcode, trg_rack)
            self.assert_true(trg_barcode in experiment_plate_barcodes)
        elif EXPERIMENT_TEST_DATA.WORKLIST_MARKER_TRANSFER in worklist_label:
            trg_barcodes = []
            self.assert_equal(len(elts), 4)
            for elt in elts:
                self._check_executed_transfer(elt,
                                        TRANSFER_TYPES.RACK_SAMPLE_TRANSFER)
                self.assert_equal(elt.source_rack.barcode, source_plate_barcode)
                trg_barcodes.append(elt.target_rack.barcode)
            self.assert_equal(sorted(trg_barcodes),
                              sorted(experiment_plate_barcodes))
        else:
            raise AssertionError('Unexpected worklist "%s"' % (worklist_label))

    def _test_no_optimem_worklist(self):
        self._load_scenario(self.case)
        ed = self.experiment_metadata.experiment_design
        for worklist in ed.worklist_series:
            if EXPERIMENT_TEST_DATA.WORKLIST_MARKER_OPTIMEM in worklist.label:
                worklist.index = 10
                break
        self._test_and_expect_errors('Could not get worklist for ' \
                                     'Optimem dilution.')

    def _test_no_reagent_worklist(self):
        self._load_scenario(self.case)
        ed = self.experiment_metadata.experiment_design
        for worklist in ed.worklist_series:
            if EXPERIMENT_TEST_DATA.WORKLIST_MARKER_REAGENT in worklist.label:
                worklist.index = 10
                break
        self._test_and_expect_errors('Could not get worklist for ' \
                                     'addition of transfection reagent.')

    def _test_unsupported_type_factories(self):
        kw = dict(case_name=EXPERIMENT_TEST_DATA.CASE_MANUAL)
        self._expect_error(TypeError, self._load_scenario,
                'This experiment type (manual optimisation) does not ' \
                'support robot worklists!', **kw)
        self.mode = self.TEST_CLS.MODE_EXECUTE
        self._expect_error(TypeError, self._create_tool,
                'This experiment type (manual optimisation) does not ' \
                'support robot worklists!')


class ExperimentOptimisationWriterExecutorTestCase(
                                            _ExperimentWriterExecutorTestCase):

    TEST_CLS = ExperimentOptimisationWriterExecutor

    def set_up(self):
        _ExperimentWriterExecutorTestCase.set_up(self)
        self.case = EXPERIMENT_TEST_DATA.CASE_OPTI_MM

    def test_writing_case_optimisation_with_mastermix(self):
        self._check_result()

    def test_execution_case_optimisation_without_mastermix(self):
        self.mode = self.TEST_CLS.MODE_EXECUTE
        self._check_result()

    def test_not_mastermix_compatible(self):
        self._load_scenario(EXPERIMENT_TEST_DATA.CASE_OPTI_NO)
        self._test_and_expect_errors('This experiment is not ' \
                'Biomek-compatible. The system cannot provide Biomek ' \
                'worklists for it. If you have attempted to update the DB, ' \
                'use the "manual" option instead, please.')

    def test_invalid_input_values(self):
        self._test_invalid_input_values()
        self.mode = self.TEST_CLS.MODE_EXECUTE
        self.executor_user = None
        self._test_and_expect_errors('The user must be a User object ' \
                                     '(obtained: NoneType).')

    def test_invalid_experiment_type(self):
        self._test_invalid_experiment_type()

    def test_unknown_design_rack(self):
        self._test_unknown_design_rack()

    def test_previous_executor_with_source_plate(self):
        self._test_previous_executor_with_source_plate()

    def test_verification_error(self):
        self._test_verification_error()

    def test_no_verification(self):
        self._test_no_verification()

    def test_no_optimem_worklist(self):
        self._test_no_optimem_worklist()

    def test_no_reagent_worklist(self):
        self._test_no_reagent_worklist()

    def test_no_transfer_worklist(self):
        self._load_scenario(self.case)
        for dr in self.experiment_metadata.experiment_design.\
                                                    experiment_design_racks:
            if not dr.label == '1': continue
            for wl in dr.worklist_series:
                if EXPERIMENT_TEST_DATA.WORKLIST_MARKER_TRANSFER in wl.label:
                    wl.index = 10
                    break
        self._test_and_expect_errors('Could not get worklist for plate ' \
                        'transfer to experiment rack for design rack "1".')

    def test_no_cell_worklist(self):
        self._load_scenario(self.case)
        for dr in self.experiment_metadata.experiment_design.\
                                                    experiment_design_racks:
            if not dr.label == '1': continue
            for wl in dr.worklist_series:
                if EXPERIMENT_TEST_DATA.WORKLIST_MARKER_CELLS in wl.label:
                    wl.index = 10
                    break
        self._test_and_expect_errors('Could not get worklist for addition ' \
                                     'of cell suspension for design rack "1".')

    def test_unsupported_type_factories(self):
        self._test_unsupported_type_factories()


class ExperimentScreeningWriterExecutorTestCase(
                                            _ExperimentWriterExecutorTestCase):

    TEST_CLS = ExperimentScreeningWriterExecutor

    def set_up(self):
        _ExperimentWriterExecutorTestCase.set_up(self)
        self.case = EXPERIMENT_TEST_DATA.CASE_SCREEN_MM

    def test_writing_case_screen_with_mastermix(self):
        self._check_result()

    def test_execution_case_screen_with_mastermix(self):
        self.mode = self.TEST_CLS.MODE_EXECUTE
        self._check_result()

    def test_writing_case_library_with_mastermix(self):
        self._check_result(EXPERIMENT_TEST_DATA.CASE_LIBRARY_MM)

    def test_execution_case_library_with_mastermix(self):
        self.mode = self.TEST_CLS.MODE_EXECUTE
        self._check_result(EXPERIMENT_TEST_DATA.CASE_LIBRARY_MM)

    def test_writing_missing_floating(self):
        self._set_up_missing_floating()
        self._load_scenario(self.case)
        exp_file_names = {
            'screen_mm_exp_biomek_optimem.csv' : \
                                        'miss_float_biomek_optimem.csv',
            'screen_mm_exp_biomek_reagent.csv' : \
                                        'miss_float_biomek_reagent.csv',
            'screen_mm_exp_reagent_instructions.csv' : \
                                        'miss_float_reagent_instructions.csv',
            'screen_mm_exp_cybio_transfers.txt' : \
                                        'screen_mm_exp_cybio_transfers.txt'}
        zip_stream = self.tool.get_result()
        archive = self._get_zip_archive(zip_stream)
        namelist = archive.namelist()
        self.assert_equal(sorted(namelist), sorted(exp_file_names.keys()))
        for tool_fn, cmp_fn in exp_file_names.iteritems():
            tool_content = archive.read(tool_fn)
            if tool_fn.endswith('.csv'):
                self._compare_csv_file_content(tool_content, cmp_fn)
            else:
                self._compare_txt_file_content(tool_content, cmp_fn)

    def test_execution_missing_floating(self):
        self.mode = self.TEST_CLS.MODE_EXECUTE
        self._set_up_missing_floating()
        self._check_result(self.case)

    def test_not_mastermix_compatible_screen(self):
        self._load_scenario(EXPERIMENT_TEST_DATA.CASE_SCREEN_NO)
        self._test_and_expect_errors('The system cannot provide Biomek ' \
                'worklists for the mastermix preparation of this experiment. ' \
                'If you have attempted to update the DB, use the "manual" ' \
                'option instead, please.')

    def test_not_mastermix_compatible_library(self):
        self._load_scenario(EXPERIMENT_TEST_DATA.CASE_LIBRARY_NO)
        self._test_and_expect_errors('The system cannot provide Biomek ' \
                'worklists for the mastermix preparation of this experiment. ' \
                'If you have attempted to update the DB, use the "manual" ' \
                'option instead, please.')

    def test_invalid_input_values(self):
        self._test_invalid_input_values()
        self.mode = self.TEST_CLS.MODE_EXECUTE
        self.executor_user = None
        self._test_and_expect_errors('The user must be a User object ' \
                                     '(obtained: NoneType).')

    def test_invalid_experiment_type(self):
        self._test_invalid_experiment_type()

    def test_unknown_design_rack(self):
        self._test_unknown_design_rack()

    def test_previous_executor_with_source_plate(self):
        self._test_previous_executor_with_source_plate()

    def test_verification_error(self):
        self._test_verification_error()

    def test_no_verification(self):
        self._test_no_verification()

    def test_no_optimem_worklist(self):
        self._test_no_optimem_worklist()

    def test_no_reagent_worklist(self):
        self._test_no_reagent_worklist()

    def test_no_transfer_worklist(self):
        self._load_scenario(self.case)
        for wl in self.experiment_metadata.experiment_design.worklist_series:
            if EXPERIMENT_TEST_DATA.WORKLIST_MARKER_TRANSFER in wl.label:
                wl.index = 10
                break
        self._test_and_expect_errors('Could not get worklist for transfer ' \
                                     'from ISO to experiment plate.')

    def test_no_cell_worklist(self):
        self._load_scenario(self.case)
        for wl in self.experiment_metadata.experiment_design.worklist_series:
            if EXPERIMENT_TEST_DATA.WORKLIST_MARKER_CELLS in wl.label:
                wl.index = 10
                break
        self._test_and_expect_errors('Could not get worklist for transfer ' \
                                     'for the addition of cell suspension.')

    def test_more_than_one_rack_transfer(self):
        self._load_scenario(self.case)
        for wl in self.experiment_metadata.experiment_design.worklist_series:
            if EXPERIMENT_TEST_DATA.WORKLIST_MARKER_TRANSFER in wl.label:
                prst = self._create_planned_rack_sample_transfer()
                wl.planned_liquid_transfers.append(prst)
                break
        self._test_and_expect_errors('There is more than rack transfer in ' \
                                     'the transfer worklist!')

    def test_unsupported_type_factories(self):
        self._test_unsupported_type_factories()
