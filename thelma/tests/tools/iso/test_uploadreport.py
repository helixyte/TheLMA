"""
Tests the ISO trac uploads.

AAB
"""
from thelma.automation.tools.iso.isoprocessing import IsoProcessingExecutor
from thelma.automation.tools.iso.stocktransfer \
    import IsoControlStockRackExecutor
from thelma.automation.tools.iso.stocktransfer import IsoSampleStockRackExecutor
from thelma.automation.tools.iso.uploadreport import StockTransferLogFileWriter
from thelma.automation.tools.iso.uploadreport import StockTransferReportUploader
from thelma.automation.tools.metadata.ticket import IsoRequestTicketCreator
from thelma.automation.tools.semiconstants \
    import get_experiment_type_manual_optimisation
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import get_384_rack_shape
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.utils.iso import IsoLayout
from thelma.interfaces import ITractor
from thelma.models.utils import get_user
from thelma.tests.tools.iso.test_isoprocessing \
    import IsoProcessing384TestCase
from thelma.tests.tools.iso.test_stocktransfer \
    import IsoControlStockRackTestCase
from thelma.tests.tools.iso.test_stocktransfer import StockTaking384TestCase
from thelma.tests.tools.iso.test_stocktransfer import StockTaking96TestCase
from thelma.tests.tools.tooltestingutils import FileCreatorTestCase
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.tooltestingutils import TracToolTestCase



class StockTransferReportTestCase(FileCreatorTestCase):
    """
    Add-on test case (not be used as solo super class).
    """

    CREATE_TICKET = False

    def set_up(self):
        if self.CREATE_TICKET:
            tractor_api = self.config.get_registered_utility(ITractor)
            TracToolTestCase.check_tractor_api(tractor_api)
        self.WL_PATH = 'thelma:tests/tools/iso/csv_files/'
        self.executed_worklists = None
        self.working_layout = None
        self.log = TestingLog()
        self.executor_user = get_user('brehm')
        self.executor = None

    def tear_down(self):
        del self.executed_worklists
        del self.working_layout
        del self.executor
        del self.WL_PATH

    def _create_tool(self):
        if self.CREATE_TICKET:
            self._create_report_uploader()
        else:
            self._create_tool_log_file_writer()

    def _create_tool_log_file_writer(self):
        self.tool = StockTransferLogFileWriter(log=self.log,
                                working_layout=self.working_layout,
                                executed_worklists=self.executed_worklists)

    def _create_report_uploader(self):
        self.tool = StockTransferReportUploader(executor=self.executor)

    def _test_and_expect_errors(self, msg=None):
        if self.CREATE_TICKET:
            self._create_report_uploader()
            self.tool.send_request()
            self.assert_false(self.tool.transaction_completed())
            self.assert_is_none(self.tool.return_value)
        else:
            FileCreatorTestCase._test_and_expect_errors(self, msg)

    def _create_ticket(self, user, iso_request):
        if self.CREATE_TICKET:
            ticket_creator = IsoRequestTicketCreator(requester=user,
                        experiment_metadata=iso_request.experiment_metadata)
            iso_request.experiment_metadata.ticket_number = \
                                            ticket_creator.get_ticket_id()

    def _test_invalid_working_layout(self):
        self.working_layout = None
        self._test_and_expect_errors('The working layout must be a ' \
                                     'WorkingLayout object')

    def _test_invalid_executed_worklists_map(self):
        ews = self.executed_worklists
        self.executed_worklists = []
        self._test_and_expect_errors('The executed worklists map must be a ' \
                                     'dict object')
        self.executed_worklists = {'1' : ews.values()[0]}
        self._test_and_expect_errors('The worklist index must be a int')
        self.executed_worklists = {1 : 2}
        self._test_and_expect_errors('The executed worklist must be a ' \
                                     'ExecutedWorklist object')

    def _test_wells_instead_of_tubes(self, well):
        ew = self.executed_worklists[0]
        for et in ew.executed_transfers:
            et.source_container = well
            break
        self._test_and_expect_errors('Some source containers in the ' \
                                     'worklists are wells')

    def _test_no_molecule_design_pool_id(self, pos_label):
        rack_pos = get_rack_position_from_label(pos_label)
        self.working_layout.del_position(rack_pos)
        self._test_and_expect_errors('Could not find molecule design pools ' \
                                     'for the following target positions')

    def _test_invalid_executor(self):
        self.executor.return_value = None
        self._test_and_expect_errors('The executor has not run yet!')
        self.executor.add_error('Error')
        self._test_and_expect_errors('The executor has errors!')
        self.executor = None
        self._test_and_expect_errors('The executor must be a ' \
                                     'StockTransferExecutor object')

    def _test_file_generation_failure(self, pos_label):
        rack_pos = get_rack_position_from_label(pos_label)
        working_layout = self.executor.get_working_layout()
        working_layout.del_position(rack_pos)
        self._test_and_expect_errors('Error when trying to generate ' \
                                     'transfer log file.')


class StockTransferReport96TestCase(StockTaking96TestCase,
                                    StockTransferReportTestCase):

    def set_up(self):
        StockTaking96TestCase.set_up(self)
        StockTransferReportTestCase.set_up(self)
        self.csv_file_name = 'report_log_file_96.csv'

    def tear_down(self):
        StockTransferReportTestCase.tear_down(self)
        StockTaking96TestCase.tear_down(self)
        del self.csv_file_name

    def _continue_setup(self):
        StockTaking96TestCase._continue_setup(self)
        self.working_layout = self.preparation_layout
        self.__execute_transfers()
        self._create_ticket(self.user, self.iso.iso_request)
        self._create_tool()

    def __execute_transfers(self):
        self.executor = IsoSampleStockRackExecutor(iso=self.iso,
                            user=self.executor_user)
        updated_iso = self.executor.get_result()
        if updated_iso is None:
            raise ValueError('Executor run has failed!')
        else:
            self.executed_worklists = \
                                    self.executor.get_executed_stock_worklists()


class StockTransferLogFileWriter96TestCase(StockTransferReport96TestCase):

    def test_result(self):
        self._continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, self.csv_file_name)

    def test_invalid_working_layout(self):
        self._continue_setup()
        self._test_invalid_working_layout()

    def test_invalid_executed_worklists_map(self):
        self._continue_setup()
        self._test_invalid_executed_worklists_map()

    def test_wells_instead_of_tubes(self):
        self._continue_setup()
        well = self.iso.preparation_plate.containers[0]
        self._test_wells_instead_of_tubes(well)

    def test_no_molecule_design_pool_id(self):
        self._continue_setup()
        self._test_no_molecule_design_pool_id('A1')


class StockTransferReportUploader96TestCase(StockTransferReport96TestCase):

    CREATE_TICKET = True

    def test_result(self):
        self._continue_setup()
        self.tool.send_request()
        self.assert_true(self.tool.transaction_completed())
        tool_stream, comment = self.tool.return_value
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, self.csv_file_name)
        self.assert_is_not_none(comment)
        self._compare_txt_file_content(comment, 'report_comment_96.txt')

    def test_result_manual(self):
        self._continue_setup()
        self.iso.iso_request.experiment_metadata.experiment_metadata_type = \
                                    get_experiment_type_manual_optimisation()
        self.tool.send_request()
        self.assert_true(self.tool.transaction_completed())
        tool_stream, comment = self.tool.return_value
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, self.csv_file_name)
        self.assert_is_not_none(comment)
        self._compare_txt_file_content(comment, 'report_comment_96_manual.txt')

    def test_invalid_executor(self):
        self._continue_setup()
        self._test_invalid_executor()

    def test_file_generation_failure(self):
        self._continue_setup()
        self._test_file_generation_failure('A1')


class StockTransferReport384TestCase(StockTaking384TestCase,
                                     StockTransferReportTestCase):

    def set_up(self):
        StockTaking384TestCase.set_up(self)
        StockTransferReportTestCase.set_up(self)
        self.csv_file_name = 'report_log_file_384.csv'

    def tear_down(self):
        StockTransferReportTestCase.tear_down(self)
        StockTaking384TestCase.tear_down(self)
        del self.csv_file_name

    def _continue_setup(self, single_stock_rack=False):
        StockTaking384TestCase._continue_setup(self, single_stock_rack)
        if self.experiment_type_id == EXPERIMENT_SCENARIOS.OPTIMISATION:
            self.csv_file_name = 'report_log_file_384_opti.csv'
        elif self.experiment_type_id == EXPERIMENT_SCENARIOS.ORDER_ONLY:
            self.csv_file_name = 'report_log_file_384_order.csv'
        self.working_layout = self.preparation_layout
        self.__execute_transfers()
        self._create_ticket(self.user, self.iso.iso_request)
        self._create_tool()

    def __execute_transfers(self):
        self.executor = IsoSampleStockRackExecutor(iso=self.iso,
                            user=self.executor_user)
        updated_iso = self.executor.get_result()
        if updated_iso is None:
            raise ValueError('Executor run has failed!')
        else:
            self.executed_worklists = \
                                self.executor.get_executed_stock_worklists()


class StockTransferLogFileWriter384TestCase(StockTransferReport384TestCase):

    def __check_result(self):
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, self.csv_file_name)

    def test_result_single(self):
        self._continue_setup(single_stock_rack=True)
        self.__check_result()

    def test_result_4_racks(self):
        self._continue_setup(single_stock_rack=False)
        self.__check_result()

    def test_result_opti(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.OPTIMISATION
        self._continue_setup()
        self.__check_result()

    def test_result_order(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.ORDER_ONLY
        self._continue_setup()
        self.__check_result()

    def test_invalid_working_layout(self):
        self._continue_setup()
        self._test_invalid_working_layout()

    def test_invalid_executed_worklists_map(self):
        self._continue_setup()
        self._test_invalid_executed_worklists_map()

    def test_wells_instead_of_tubes(self):
        self._continue_setup()
        well = self.iso.preparation_plate.containers[0]
        self._test_wells_instead_of_tubes(well)

    def test_no_molecule_design_pool_id(self):
        self._continue_setup()
        self._test_no_molecule_design_pool_id('B1')


class StockTransferReportUploader384TestCase(StockTransferReport384TestCase):

    CREATE_TICKET = True

    def __check_result(self, comment_file_name):
        self.tool.send_request()
        self.assert_true(self.tool.transaction_completed())
        tool_stream, comment = self.tool.return_value
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, self.csv_file_name)
        self.assert_is_not_none(comment)
        self._compare_txt_file_content(comment, comment_file_name)

    def test_result_single(self):
        self._continue_setup(single_stock_rack=True)
        self.__check_result('report_comment_384_screen.txt')

    def test_result_4_racks(self):
        self._continue_setup(single_stock_rack=False)
        self.__check_result('report_comment_384_screen.txt')

    def test_result_opti(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.OPTIMISATION
        self._continue_setup()
        self.__check_result('report_comment_384_opti.txt')

    def test_result_order(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.ORDER_ONLY
        self._continue_setup()
        self.__check_result('report_comment_384_opti.txt') # same as opti

    def test_invalid_executor(self):
        self._continue_setup()
        self._test_invalid_executor()

    def test_file_generation_failure(self):
        self._continue_setup()
        self._test_file_generation_failure('B1')


class StockTransferReportIsoJobTestCase(IsoControlStockRackTestCase,
                                        StockTransferReportTestCase):

    def set_up(self):
        IsoControlStockRackTestCase.set_up(self)
        StockTransferReportTestCase.set_up(self)
        self.csv_file_name = 'report_log_file_iso_job.csv'

    def tear_down(self):
        del self.csv_file_name
        StockTransferReportTestCase.tear_down(self)
        IsoControlStockRackTestCase.tear_down(self)

    def _continue_setup(self):
        IsoControlStockRackTestCase._continue_setup(self)
        self.working_layout = self.control_layout
        self.__execute_transfers()
        self._create_ticket(self.user, self.iso_job.iso_request)
        self._create_tool()

    def __execute_transfers(self):
        self.executor = IsoControlStockRackExecutor(iso_job=self.iso_job,
                                                    user=self.executor_user)
        updated_iso = self.executor.get_result()
        if updated_iso is None:
            raise ValueError('Executor run has failed!')
        else:
            self.executed_worklists = \
                            self.executor.get_executed_stock_worklists()


class StockTransferLogFileWriterIsoJobTestCase(
                                        StockTransferReportIsoJobTestCase):

    def test_result(self):
        self._continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, self.csv_file_name)

    def test_invalid_working_layout(self):
        self._continue_setup()
        self._test_invalid_working_layout()

    def test_invalid_executed_worklists_map(self):
        self._continue_setup()
        self._test_invalid_executed_worklists_map()

    def test_wells_instead_of_tubes(self):
        self._continue_setup()
        well = self.iso_job.isos[0].preparation_plate.containers[0]
        self._test_wells_instead_of_tubes(well)

    def test_no_molecule_design_pool_id(self):
        self._continue_setup()
        self._test_no_molecule_design_pool_id('B1')

    def test_unsupported_layout_type(self):
        # test does not need to be repeated for other types
        self._continue_setup()
        self.working_layout = IsoLayout(shape=get_384_rack_shape())
        self._test_and_expect_errors('Unsupported layout type: IsoLayout.')


class StockTransferReportUploaderIsoJobTestCase(
                                        StockTransferReportIsoJobTestCase):

    CREATE_TICKET = True

    def test_result(self):
        self._continue_setup()
        self.tool.send_request()
        self.assert_true(self.tool.transaction_completed())
        tool_stream, comment = self.tool.return_value
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, self.csv_file_name)
        self.assert_is_not_none(comment)
        self._compare_txt_file_content(comment, 'report_comment_iso_job.txt')

    def test_invalid_executor(self):
        self._continue_setup()
        self._test_invalid_executor()

    def test_file_generation_failure(self):
        self._continue_setup()
        self._test_file_generation_failure('B1')


class StockTransferReportProcessingTestCase(IsoProcessing384TestCase,
                                            StockTransferReportTestCase):

    def set_up(self):
        IsoProcessing384TestCase.set_up(self)
        StockTransferReportTestCase.set_up(self)
        self.csv_file_name = 'report_log_file_processing.csv'
        self.setup_includes_stock_transfer = False

    def tear_down(self):
        del self.csv_file_name
        StockTransferReportTestCase.tear_down(self)
        IsoProcessing384TestCase.tear_down(self)

    def _continue_setup(self):
        IsoProcessing384TestCase._continue_setup(self)
        self.working_layout = self.preparation_layout
        self.__execute_transfers()
        self._create_ticket(self.user, self.iso.iso_request)
        self._create_tool()

    def __execute_transfers(self):
        self.executor = IsoProcessingExecutor(iso=self.iso,
                                              user=self.executor_user)
        updated_iso = self.executor.get_result()
        if updated_iso is None:
            raise ValueError('Executor run has failed!')
        else:
            self.executed_worklists = \
                                    self.executor.get_executed_stock_worklists()


class StockTransferLogFileWriterProcessingTestCase(
                                    StockTransferReportProcessingTestCase):

    def test_result(self):
        self._continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, self.csv_file_name)

    def test_invalid_working_layout(self):
        self._continue_setup()
        self._test_invalid_working_layout()

    def test_invalid_executed_worklists_map(self):
        self._continue_setup()
        self._test_invalid_executed_worklists_map()

    def test_wells_instead_of_tubes(self):
        self._continue_setup()
        well = self.iso.preparation_plate.containers[0]
        self._test_wells_instead_of_tubes(well)

    def test_no_molecule_design_id(self):
        self._continue_setup()
        self._test_no_molecule_design_pool_id('B1')


class StockTransferReportUploaderProcessingTestCase(
                                        StockTransferReportProcessingTestCase):

    CREATE_TICKET = True

    def test_result_with_stock(self):
        self._continue_setup()
        self.tool.send_request()
        self.assert_true(self.tool.transaction_completed())
        self.assert_false(self.tool.quit_run)
        tool_stream, comment = self.tool.return_value
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, self.csv_file_name)
        self.assert_is_not_none(comment)
        self._compare_txt_file_content(comment, 'report_comment_processing.txt')

    def test_result_without_stock(self):
        self.setup_includes_stock_transfer = True
        self._continue_setup()
        self.tool.send_request()
        self.assert_true(self.tool.transaction_completed())
        self.assert_false(self.tool.has_errors())
        self.assert_true(self.tool.quit_run)
        self.assert_is_none(self.tool.return_value)

    def test_invalid_executor(self):
        self._continue_setup()
        self._test_invalid_executor()

    def test_file_generation_failure(self):
        self._continue_setup()
        self._test_file_generation_failure('B1')
