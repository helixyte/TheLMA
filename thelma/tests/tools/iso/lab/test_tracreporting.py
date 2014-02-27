"""
Tests for tools that report to stock transfers involved in lab ISO preparation.

AAB
"""
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.iso.base import StockRackLayout
from thelma.automation.tools.iso.base import StockRackPosition
from thelma.automation.tools.iso.tracreporting import IsoStockTransferReporter
from thelma.automation.tools.iso.lab.tracreporting \
    import LabIsoStockTransferLogFileWriter
from thelma.automation.tools.iso.lab.tracreporting \
    import LabIsoStockTransferReporter
from thelma.automation.utils.layouts import TransferTarget
from thelma.models.iso import ISO_STATUS
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.tests.tools.iso.lab.test_processing \
    import _LabIsoWriterExecutorToolTestCase
from thelma.tests.tools.iso.lab.utils import LAB_ISO_TEST_CASES
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.tooltestingutils import TracToolTestCase


class _LabIsoStockTransferTracReportingTestCase(
                                        _LabIsoWriterExecutorToolTestCase):

    def set_up(self):
        _LabIsoWriterExecutorToolTestCase.set_up(self)
        self.WL_PATH = LAB_ISO_TEST_CASES.TRAC_FILE_PATH
        self.executor = None
        self.executed_worklists = None
        self.stock_rack_data = None

    def tear_down(self):
        _LabIsoWriterExecutorToolTestCase.tear_down(self)
        del self.executor
        del self.executed_worklists
        del self.stock_rack_data

    def _continue_setup(self, file_name=None):
        _LabIsoWriterExecutorToolTestCase._continue_setup(self,
                                                          file_name=file_name)
        if self.inactivated_pool_id is not None:
            self._inactivate_position()
        self._create_executor()
        self.executor.run()
        self.executed_worklists = self.executor.get_executed_stock_worklists()
        self.stock_rack_data = self.executor.get_stock_rack_data()
        self._create_tool()

    def _create_executor(self):
        _LabIsoWriterExecutorToolTestCase._create_tool(self)
        self.executor = self.tool
        self.tool = None

    def _create_tool(self):
        raise NotImplementedError('Abstract method.')

    def _check_tool_stream(self, tool_stream):
        self.assert_is_not_none(tool_stream)
        if self.inactivated_pool_id is None:
            fn = LAB_ISO_TEST_CASES.get_trac_log_file_name(self.case,
                                                           self.FOR_JOB)
        elif self.FOR_JOB:
            fn = 'inactivation_job.csv'
        else:
            fn = 'inactivation_iso.csv'
        self._compare_csv_file_stream(tool_stream, fn)

    def _test_position_inactivation(self):
        self._set_inactivation_data()
        self._continue_setup()
        self._check_result()


class _LabIsoProcessingStockTransferLogFileWriterTestCase(
                                _LabIsoStockTransferTracReportingTestCase):

    def set_up(self):
        _LabIsoStockTransferTracReportingTestCase.set_up(self)
        self.log = TestingLog()

    def _create_tool(self):
        self.tool = LabIsoStockTransferLogFileWriter(log=self.log,
                                    stock_rack_data=self.stock_rack_data,
                                    executed_worklists=self.executed_worklists)

    def _check_result(self):
        tool_stream = self.tool.get_result()
        self._check_tool_stream(tool_stream)

    def _test_and_expect_no_processing(self, case_name):
        self._load_iso_request(case_name)
        self._test_and_expect_errors('The executed worklist list must be a ' \
                                     'list object (obtained: NoneType).')
        self._check_error_messages('The stock rack layout map must be a dict ' \
                                   'object (obtained: NoneType).')


class UnspecificLabIsoProcessingStockTransferLogFileWriterTestCase(
                        _LabIsoProcessingStockTransferLogFileWriterTestCase):

    FOR_JOB = False

    def test_invalid_input_values(self):
        if self.case is None:
            self.case = LAB_ISO_TEST_CASES.CASE_ORDER_ONLY
        self._load_iso_request(self.case)
        ori_srd = self.stock_rack_data
        self.stock_rack_data = []
        self._test_and_expect_errors('The stock rack layout map must be a ' \
                                     'dict object (obtained: list).')
        self.stock_rack_data = {ori_srd.keys()[0] : 1}
        self._test_and_expect_errors('The stock rack layout must be a ' \
                                     'StockRackLayout object (obtained: int).')
        self.stock_rack_data = {1 : ori_srd.values()[0]}
        self._test_and_expect_errors('The stock rack barcode must be a ' \
                                     'basestring object (obtained: int).')
        self.stock_rack_data = dict()
        self._test_and_expect_errors('The stock rack layout map is empty!')
        self.stock_rack_data = ori_srd
        ori_ews = self.executed_worklists
        self.executed_worklists = dict()
        self._test_and_expect_errors('The executed worklist list must be a ' \
                                     'list object (obtained: dict).')
        self.executed_worklists = [1]
        self._test_and_expect_errors('The executed worklist must be a ' \
                                     'ExecutedWorklist object (obtained: int).')
        self.executed_worklists = []
        self._test_and_expect_errors('The executed worklist list is empty!')
        self.executed_worklists = ori_ews

    def test_missing_layout(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        layout = self.stock_rack_data.values()[0]
        layouts_str = ', '.join(sorted(self.stock_rack_data.keys()))
        self.stock_rack_data = {'09876543' : layout}
        self._test_and_expect_errors('Unable to find the layouts for the ' \
                                'following stock racks: %s' % (layouts_str))

    def test_source_wells(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        iso = self.isos[self._USED_ISO_LABEL]
        final_plate = iso.iso_aliquot_plates[0].rack
        wells = []
        for well in final_plate.containers:
            wells.append(well)
            if len(wells) > 1: break
        new_layout = StockRackLayout()
        psts = []
        ests = []
        for well in wells:
            rack_pos = well.location.position
            pst = self._create_planned_sample_transfer(source_position=rack_pos,
                                                       target_position=rack_pos)
            psts.append(pst)
            est = self._create_executed_sample_transfer(source_container=well,
                    target_container=well, planned_sample_transfer=pst)
            ests.append(est)
            pool_id = 205200 + (len(new_layout))
            pool = self._get_pool(pool_id)
            tt = TransferTarget(rack_pos, 1, 'a#5')
            sr_pos = StockRackPosition(rack_position=rack_pos,
                                       molecule_design_pool=pool,
                                       tube_barcode='1002%i' % (pool_id),
                                       transfer_targets=[tt])
            new_layout.add_position(sr_pos)
        new_wl = self._create_planned_worklist(label='invalid_worklist',
                           transfer_type=TRANSFER_TYPES.SAMPLE_TRANSFER,
                           planned_liquid_transfers=psts)
        new_ew = self._create_executed_worklist(planned_worklist=new_wl,
                                                executed_liquid_transfers=ests)
        self.executed_worklists.append(new_ew)
        self.stock_rack_data[final_plate.barcode] = new_layout
        self._test_and_expect_errors('Some source containers in the ' \
                    'worklists are wells: plate 09999210 (positions A1, A2)!')

    def test_unknown_pool(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)
        layout = self.stock_rack_data.values()[0]
        rack_pos = get_rack_position_from_label('b2')
        layout.del_position(rack_pos)
        self._test_and_expect_errors('Could not find molecule design pools ' \
                    'for the following source positions in rack 09999011: B2.')


class LabIsoStockTransferLogFileWriterTestCase(
                        _LabIsoProcessingStockTransferLogFileWriterTestCase):

    FOR_JOB = False

    def test_case_order_only(self):
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)

    def test_case_no_job_direct(self):
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_NO_JOB_DIRECT)

    def test_case_no_job_one_prep(self):
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
        self._test_and_expect_no_processing(
                                LAB_ISO_TEST_CASES.CASE_LIBRARY_SIMPLE)

    def test_case_library_2_aliquots(self):
        self._test_and_expect_no_processing(
                                LAB_ISO_TEST_CASES.CASE_LIBRARY_2_ALIQUOTS)

    def test_position_inactivation(self):
        self._test_position_inactivation()


class IsoJobStockTransferLogFileWriterTestCase(
                        _LabIsoProcessingStockTransferLogFileWriterTestCase):

    FOR_JOB = True

    def test_case_order_only(self):
        self._test_and_expect_no_processing(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)

    def test_case_no_job_direct(self):
        self._test_and_expect_no_processing(
                                LAB_ISO_TEST_CASES.CASE_NO_JOB_DIRECT)

    def test_case_no_job_one_prep(self):
        self._test_and_expect_no_processing(
                                LAB_ISO_TEST_CASES.CASE_NO_JOB_1_PREP)

    def test_case_no_job_complex(self):
        self._test_and_expect_no_processing(
                                LAB_ISO_TEST_CASES.CASE_NO_JOB_COMPLEX)

    def test_case_association_direct(self):
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)

    def test_case_association_96(self):
        self._test_and_expect_no_processing(
                                LAB_ISO_TEST_CASES.CASE_ASSOCIATION_96)

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
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_LIBRARY_SIMPLE)

    def test_case_library_2_aliquots(self):
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_LIBRARY_2_ALIQUOTS)

    def test_position_inactivation(self):
        self._test_position_inactivation()


class _LabIsoProcessingStockTransferReporterTestCase(TracToolTestCase,
                                _LabIsoStockTransferTracReportingTestCase):

    TEST_CLS = LabIsoStockTransferReporter

    def set_up(self):
        _LabIsoStockTransferTracReportingTestCase.set_up(self)
        TracToolTestCase.set_up_as_add_on(self)
        self.comment_pattern = \
            IsoStockTransferReporter.BASE_COMMENT \
            % ('Daniel Tondera', '%s', '%s', '%s', "'''Target plates:''' %s")
        self.exp_attachment_name = None
        self.exp_type = None
        self.exp_target_plates_str = None

    def tear_down(self):
        TracToolTestCase.tear_down_as_add_on(self)
        _LabIsoStockTransferTracReportingTestCase.tear_down(self)
        del self.comment_pattern
        del self.exp_attachment_name
        del self.exp_type
        del self.exp_target_plates_str

    def _create_tool(self):
        self.tool = LabIsoStockTransferReporter(executor=self.executor)

    def _continue_setup(self, file_name=None):
        _LabIsoStockTransferTracReportingTestCase._continue_setup(self,
                                                        file_name=file_name)
        self.__create_and_set_ticket()

    def __create_and_set_ticket(self):
        ticket_number = self._get_ticket()
        self.iso_request.experiment_metadata.ticket_number = ticket_number

    def _check_result(self):
        self.tool.send_request()
        self.assert_true(self.tool.transaction_completed())
        tool_stream, comment = self.tool.return_value # unpack non-sequence pylint: disable=W0633
        self._check_tool_stream(tool_stream)
        self.__check_comment(comment)

    def __check_comment(self, comment):
        exp_comment = self.comment_pattern % (self.exp_attachment_name,
                  self.entity.label, self.exp_type, self.exp_target_plates_str)
        self.assert_equal(exp_comment, comment)

    def _test_and_expect_no_processing(self, case_name):
        self._load_iso_request(case_name)
        self._test_and_expect_errors('The executor has errors! Abort file ' \
                                     'generation.')

    def _test_and_expect_errors(self, msg=None):
        TracToolTestCase._test_and_expect_errors(self, msg=msg)


class UnspecificLabIsoProcessingStockTransferReporterTestCase(
                            _LabIsoProcessingStockTransferReporterTestCase):

    FOR_JOB = False

    def test_invalid_input_values(self):
        self._test_and_expect_errors('The executor must be a ' \
                    '_LabIsoWriterExecutorTool object (obtained: NoneType).')
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)
        self.executor.mode = self.executor.MODE_PRINT_WORKLISTS
        self._test_and_expect_errors('The executor is not in execution mode!')
        self._create_executor()
        self.executor.run()
        self._test_and_expect_errors('The executor has errors! Abort file ' \
                                     'generation.')
        self.entity.status = ISO_STATUS.QUEUED
        self._create_executor()
        self._test_and_expect_errors('The executor has not run yet!')

    def test_log_file_preparation_error(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)
        layout = self.stock_rack_data.values()[0]
        rack_pos = get_rack_position_from_label('b2')
        layout.del_position(rack_pos)
        self._test_and_expect_errors('Error when trying to generate ' \
                                     'transfer log file.')

    def test_trac_error(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)
        self.iso_request.experiment_metadata.ticket_number += 1
        self._test_and_expect_errors('Fault')


class LabIsoProcessingStockTransferReporterTestCase(
                            _LabIsoProcessingStockTransferReporterTestCase):

    FOR_JOB = False

    def set_up(self):
        _LabIsoProcessingStockTransferReporterTestCase.set_up(self)
        self.exp_attachment_name = 'stock_transfer_123_iso_01.csv'

    def test_case_order_only(self):
        self.exp_type = self.TEST_CLS.SAMPLE_TYPE_CONTROLS
        self.exp_target_plates_str = '09999210'
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)

    def test_case_no_job_direct(self):
        self.exp_type = self.TEST_CLS.SAMPLE_TYPE_CONTROLS
        self.exp_target_plates_str = '09999210'
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_NO_JOB_DIRECT)

    def test_case_no_job_one_prep(self):
        self.exp_type = self.TEST_CLS.SAMPLE_TYPE_CONTROLS
        self.exp_target_plates_str = '09999210, 09999911'
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_NO_JOB_1_PREP)

    def test_case_no_job_complex(self):
        self.exp_type = self.TEST_CLS.SAMPLE_TYPE_CONTROLS
        self.exp_target_plates_str = '09999210, 09999911'
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_NO_JOB_COMPLEX)

    def test_case_association_direct(self):
        self.exp_type = self.TEST_CLS.SAMPLE_TYPE_SAMPLES
        self.exp_target_plates_str = '09999210'
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)

    def test_case_association_96(self):
        self.exp_type = self.TEST_CLS.SAMPLE_TYPE_BOTH
        self.exp_target_plates_str = '09999911'
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_96)

    def test_case_association_simple(self):
        self.exp_type = self.TEST_CLS.SAMPLE_TYPE_SAMPLES
        self.exp_target_plates_str = '09999911'
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE)

    def test_case_association_no_cybio(self):
        self.exp_type = self.TEST_CLS.SAMPLE_TYPE_SAMPLES
        self.exp_target_plates_str = '09999911'
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_NO_CYBIO)

    def test_case_association_2_aliquots(self):
        self.exp_type = self.TEST_CLS.SAMPLE_TYPE_SAMPLES
        self.exp_target_plates_str = '09999911'
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_2_ALIQUOTS)

    def test_case_association_job_last(self):
        self.exp_type = self.TEST_CLS.SAMPLE_TYPE_SAMPLES
        self.exp_target_plates_str = '09999911'
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_JOB_LAST)

    def test_case_association_several_conc(self):
        self.exp_type = self.TEST_CLS.SAMPLE_TYPE_SAMPLES
        self.exp_target_plates_str = '09999911'
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SEVERAL_CONC)

    def test_case_library_simple(self):
        self._test_and_expect_no_processing(
                                LAB_ISO_TEST_CASES.CASE_LIBRARY_SIMPLE)

    def test_case_library_2_aliquots(self):
        self._test_and_expect_no_processing(
                                LAB_ISO_TEST_CASES.CASE_LIBRARY_2_ALIQUOTS)

    def test_position_inactivation(self):
        self.exp_type = self.TEST_CLS.SAMPLE_TYPE_SAMPLES
        self.exp_target_plates_str = '09999911'
        self._test_position_inactivation()


class IsoJobProcessingStockTransferReporterTestCase(
                            _LabIsoProcessingStockTransferReporterTestCase):

    FOR_JOB = True

    def set_up(self):
        _LabIsoProcessingStockTransferReporterTestCase.set_up(self)
        self.exp_attachment_name = 'stock_transfer_123_job_01.csv'
        self.exp_type = self.TEST_CLS.SAMPLE_TYPE_CONTROLS

    def test_case_order_only(self):
        self._test_and_expect_no_processing(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)

    def test_case_no_job_direct(self):
        self._test_and_expect_no_processing(
                                LAB_ISO_TEST_CASES.CASE_NO_JOB_DIRECT)

    def test_case_no_job_one_prep(self):
        self._test_and_expect_no_processing(
                                LAB_ISO_TEST_CASES.CASE_NO_JOB_1_PREP)

    def test_case_no_job_complex(self):
        self._test_and_expect_no_processing(
                                LAB_ISO_TEST_CASES.CASE_NO_JOB_COMPLEX)

    def test_case_association_direct(self):
        self.exp_target_plates_str = '09999210, 09999220'
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)

    def test_case_association_96(self):
        self._test_and_expect_no_processing(
                                    LAB_ISO_TEST_CASES.CASE_ASSOCIATION_96)

    def test_case_association_simple(self):
        self.exp_target_plates_str = '09999911, 09999912'
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE)

    def test_case_association_no_cybio(self):
        self.exp_target_plates_str = '09999900'
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_ASSOCIATION_NO_CYBIO)

    def test_case_association_2_aliquots(self):
        self.exp_target_plates_str = '09999911, 09999912'
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_ASSOCIATION_2_ALIQUOTS)

    def test_case_association_job_last(self):
        self.exp_target_plates_str = '09999900'
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_ASSOCIATION_JOB_LAST)

    def test_case_association_several_conc(self):
        self.exp_target_plates_str = '09999900'
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SEVERAL_CONC)

    def test_case_library_simple(self):
        self.exp_target_plates_str = '09999900'
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_LIBRARY_SIMPLE)

    def test_case_library_2_aliquots(self):
        self.exp_target_plates_str = '09999900'
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_LIBRARY_2_ALIQUOTS)

    def test_position_inactivation(self):
        self.exp_target_plates_str = '09999911, 09999912'
        self._test_position_inactivation()
