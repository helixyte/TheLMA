"""
Tests for pool stock sample creation ticket tools.

AAB
"""
from everest.testing import RdbContextManager
from thelma.automation.tools.poolcreation.execution import PoolCreationExecutor
from thelma.automation.tools.poolcreation.ticket \
    import PoolCreationStockLogFileWriter
from thelma.automation.tools.poolcreation.ticket \
    import PoolCreationStockTransferReporter
from thelma.automation.tools.poolcreation.ticket \
    import PoolCreationTicketGenerator
from thelma.automation.tools.poolcreation.ticket \
    import PoolCreationTicketWorklistUploader
from thelma.automation.tools.poolcreation.ticket import PoolCreationIsoCreator
from thelma.automation.tools.poolcreation.writer \
    import PoolCreationWorklistWriter
from thelma.models.library import LibraryCreationIso
from thelma.models.racklayout import RackLayout
from thelma.models.sample import Molecule
from thelma.models.utils import get_user
from thelma.tests.tools.iso.test_uploadreport import StockTransferReportTestCase
from thelma.tests.tools.poolcreation.test_execution \
    import PoolCreationExecutorBaseTestCase
from thelma.tests.tools.poolcreation.test_writer \
    import PoolCreationWriterTestCase
from thelma.tests.tools.poolcreation.utils import PoolCreationTestCase
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.tooltestingutils import TracToolTestCase


class PoolCreationTicketGeneratorTestCase(TracToolTestCase):

    def set_up(self):
        TracToolTestCase.set_up(self)
        self.requester = get_user('brehm')
        self.iso_label = 'testorder-4'
        self.layout_number = 4
        self.log = TestingLog()

    def tear_down(self):
        TracToolTestCase.tear_down(self)
        del self.requester
        del self.iso_label
        del self.layout_number
        del self.log

    def _create_tool(self):
        self.tool = PoolCreationTicketGenerator(requester=self.requester,
                            iso_label=self.iso_label,
                            layout_number=self.layout_number, log=self.log)

    def test_result(self):
        self._create_tool()
        ticket_id = self.tool.get_ticket_id()
        self.assert_true(self.tool.transaction_completed())
        self.assert_is_not_none(ticket_id)

    def test_invalid_input(self):
        req = self.requester
        self.requester = self.requester.username
        self._test_and_expect_errors('The requester must be a User object ' \
                                     '(obtained: unicode).')
        self.requester = req
        self.layout_number = '14'
        self._test_and_expect_errors('The layout number must be a int')
        self.layout_number = 14
        self.iso_label = 14
        self._test_and_expect_errors('The ISO label must be a basestring')


class PoolCreationIsoCreatorTestCase(TracToolTestCase, PoolCreationTestCase):

    def set_up(self):
        TracToolTestCase.set_up(self)
        self.TEST_FILE_PATH = 'thelma:tests/tools/poolcreation/ticket/'
        self.VALID_FILE = 'valid_file_120_pools.xls'
        self.iso_request_label = 'testorder'
        self.target_volume = 30
        self.target_concentration = 10000
        self.iso_request = None
        self.requester = get_user('brehm')

    def tear_down(self):
        PoolCreationTestCase.tear_down(self)

    def _create_tool(self):
        self.tool = PoolCreationIsoCreator(iso_request=self.iso_request)

    def __continue_setup(self): # pylint: disable=W0221
        PoolCreationTestCase._continue_setup(self, file_name=self.VALID_FILE)
        self.iso_request = self.library.iso_request
        self._create_tool()

    def _test_and_expect_errors(self, msg=None):
        PoolCreationTestCase._test_and_expect_errors(self, msg)

    def __check_result(self):
        iso_request = self.tool.get_result()
        self.assert_is_not_none(iso_request)
        self.assert_equal(len(iso_request.isos), 2)
        layout_numbers = []
        ticket_numbers = set()
        for lci in iso_request.isos:
            layout_numbers.append(lci.layout_number)
            ti = lci.ticket_number
            self.assert_is_not_none(ti)
            self.assert_false(ti in ticket_numbers)
            ticket_numbers.add(ti)
        self.assert_equal(sorted(layout_numbers), [1, 2])

    def test_result_all(self):
        self.__continue_setup()
        self.__check_result()

    def test_result_existing_iso(self):
        self.__continue_setup()
        LibraryCreationIso(ticket_number=99, layout_number=1,
                           label='premade', iso_request=self.iso_request,
                           rack_layout=RackLayout())
        self.assert_equal(len(self.iso_request.isos), 1)
        self.__check_result()

    def test_invalid_input_values(self):
        self.__continue_setup()
        self.iso_request = None
        self._test_and_expect_errors('The ISO request must be a IsoRequest')

    def test_no_isos_left(self):
        self.__continue_setup()
        for i in range(2):
            LibraryCreationIso(ticket_number=99 + i, layout_number=1 + i,
                               label='premade', iso_request=self.iso_request,
                               rack_layout=RackLayout())
        self._test_and_expect_errors('The ISOs have already been created.')


class PoolCreationTicketWorklistUploaderTestCase(PoolCreationWriterTestCase,
                                                 TracToolTestCase):

    def set_up(self):
        TracToolTestCase.set_up(self)
        PoolCreationWriterTestCase.set_up(self)
        self.file_map = None

    def tear_down(self):
        PoolCreationWriterTestCase.tear_down(self)
        del self.file_map

    def _create_tool(self):
        self.tool = PoolCreationTicketWorklistUploader(file_map=self.file_map,
                       pool_creation_iso=self.pool_creation_iso)

    def _continue_setup(self):
        PoolCreationWriterTestCase._continue_setup(self)
        self.__write_files()
        self._create_tool()

    def _create_pool_iso(self):
        iso_creator = PoolCreationIsoCreator(
                                        iso_request=self.library.iso_request)
        self.iso_request = iso_creator.get_result()
        self.pool_creation_iso = self.iso_request.isos[0]
        self.pool_creation_iso.layout_number = self.layout_number
        self.pool_creation_iso.label = self.iso_label
        self.pool_creation_iso.rack_layout = \
                                    self.pool_iso_layout.create_rack_layout()

    def __write_files(self):
        writer = PoolCreationWorklistWriter(
                        pool_creation_iso=self.pool_creation_iso,
                        tube_destination_racks=self.tube_destination_barcodes,
                        pool_stock_rack_barcode=self.pool_stock_rack_barcode)
        self.file_map = writer.get_result()
        self.assert_is_not_none(self.file_map)

    def test_result(self):
        with RdbContextManager() as session:
            self.session = session
            self._continue_setup()
            self.tool.send_request()
            self.assert_true(self.tool.transaction_completed())
            exp_fn = self.tool.FILE_NAME % (self.iso_request_label,
                                            self.layout_number)
            self.assert_equal(self.tool.return_value, exp_fn)

    def test_invalid_input_values(self):
        with RdbContextManager() as session:
            self.session = session
            self._continue_setup()
            pci = self.pool_creation_iso
            self.pool_creation_iso = None
            TracToolTestCase._test_and_expect_errors(self,
                'The pool creation ISO must be a LibraryCreationIso object')
            self.pool_creation_iso = pci
            self.file_map = None
            TracToolTestCase._test_and_expect_errors(self,
                'The file map must be a dict')
            self.file_map = {2 : 3}
            TracToolTestCase._test_and_expect_errors(self,
                'The file name must be a basestring')

    def test_trac_failure(self):
        with RdbContextManager() as session:
            self.session = session
            self._continue_setup()
            self.pool_creation_iso.ticket_number += 100000
            TracToolTestCase._test_and_expect_errors(self, 'Fault')


class PoolCreationStockTransferReportTestCase(StockTransferReportTestCase,
                                              PoolCreationExecutorBaseTestCase):

    def set_up(self):
        PoolCreationExecutorBaseTestCase.set_up(self)
        StockTransferReportTestCase.set_up(self)
        self.WL_PATH = 'thelma:tests/tools/poolcreation/ticket/'
        self.csv_file_name = 'report_log_file.csv'

    def tear_down(self):
        StockTransferReportTestCase.tear_down(self)
        PoolCreationExecutorBaseTestCase.tear_down(self)
        del self.csv_file_name

    def _continue_setup(self):
        PoolCreationExecutorBaseTestCase._continue_setup(self)
        self.working_layout = self.pool_iso_layout
        self.__execute_transfers()
        self._create_ticket(user=self.executor_user, iso_request=None)
        self._create_tool()

    def __execute_transfers(self):
        self.executor = PoolCreationExecutor(user=self.executor_user,
                                 pool_creation_iso=self.pool_creation_iso)
        updated_iso = self.executor.get_result()
        if updated_iso is None:
            raise ValueError('Executor run has failed!')
        else:
            self.executed_worklists = \
                                    self.executor.get_executed_stock_worklists()


    def _create_ticket(self, user, iso_request):
        if self.CREATE_TICKET:
            ticket_creator = PoolCreationTicketGenerator(requester=user,
                         log=self.log, iso_label=self.pool_creation_iso.label,
                         layout_number=self.layout_number)
            self.pool_creation_iso.ticket_number = \
                                            ticket_creator.get_ticket_id()

    def _create_report_uploader(self):
        self.tool = PoolCreationStockTransferReporter(
                                            executor=self.executor)

    def _create_tool_log_file_writer(self):
        self.tool = PoolCreationStockLogFileWriter(log=self.log,
                                library_layout=self.pool_iso_layout,
                                executed_worklists=self.executed_worklists)


class PoolCreationStockLogFileWriterTestCase(
                                    PoolCreationStockTransferReportTestCase):

    def test_result(self):
        self._continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, self.csv_file_name)

    def test_invalid_input_values(self):
        self._continue_setup()
        pcl = self.pool_iso_layout
        self.pool_iso_layout = None
        self._test_and_expect_errors('The library layout must be a ' \
                                     'LibraryLayout object')
        self.pool_iso_layout = pcl
        self.executed_worklists = None
        self._test_and_expect_errors('The executed worklists map must be a ' \
                                     'dict object')

    def test_more_than_one_source_sample_molecule(self):
        self._continue_setup()
        for ew in self.executed_worklists.values():
            ect = ew.executed_transfers[0]
            sample = ect.source_container.sample
            md = sample.sample_molecules[0].molecule.molecule_design
            mol = Molecule(molecule_design=md, supplier=self.supplier)
            sample.make_sample_molecule(molecule=mol, concentration=1)
            break
        self._test_and_expect_errors('Some source container contain more ' \
                                     'than one molecule design')


class PoolCreationStockTransferReporterTestCase(
                                    PoolCreationStockTransferReportTestCase):

    CREATE_TICKET = True

    def test_result(self):
        self._continue_setup()
        self.tool.send_request()
        self.assert_true(self.tool.transaction_completed())
        tool_stream, comment = self.tool.return_value
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, self.csv_file_name)
        self.assert_is_not_none(comment)
        self._compare_txt_file_content(comment, 'report_comment.txt')

    def test_invalid_executor(self):
        self._continue_setup()
        self._test_invalid_executor()

    def test_file_generation_failure(self):
        self._continue_setup()
        self._test_file_generation_failure('A1')
