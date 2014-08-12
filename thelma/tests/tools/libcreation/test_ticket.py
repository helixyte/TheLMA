#"""
#Tests for library creation ticket tools.
#
#AAB
#"""
#from everest.repositories.rdb.testing import RdbContextManager
#from pkg_resources import resource_filename # pylint: disable=E0611,F0401
#from thelma.automation.tools.libcreation.execution \
#    import LibraryCreationExecutor
#from thelma.automation.tools.libcreation.generation import LibraryGenerator
#from thelma.automation.tools.libcreation.ticket \
#    import LibraryCreationIsoCreator
#from thelma.automation.tools.libcreation.ticket \
#    import LibraryCreationStockLogFileWriter
#from thelma.automation.tools.libcreation.ticket \
#    import LibraryCreationStockTransferReporter
#from thelma.automation.tools.libcreation.ticket \
#    import LibraryCreationTicketGenerator
#from thelma.automation.tools.libcreation.ticket \
#    import LibraryCreationTicketWorklistUploader
#from thelma.automation.tools.libcreation.writer \
#    import LibraryCreationWorklistWriter
#from thelma.interfaces import IOrganization
#from thelma.models.library import LibraryCreationIso
#from thelma.models.racklayout import RackLayout
#from thelma.models.sample import Molecule
#from thelma.models.utils import get_user
#from thelma.tests.tools.iso.test_uploadreport import StockTransferReportTestCase
#from thelma.tests.tools.libcreation.test_execution \
#    import LibraryCreationExecutorBaseTestCase
#from thelma.tests.tools.libcreation.test_writer \
#    import LibraryCreationWorklistWriterBaseTestCase
#from thelma.tests.tools.tooltestingutils import TracToolTestCase
#
#
#class LibraryCreationTicketGeneratorTestCase(TracToolTestCase):
#
#    def set_up(self):
#        TracToolTestCase.set_up(self)
#        self.requester = get_user('sachse')
#        self.iso_label = 'testlib-14'
#        self.layout_number = 14
#
#    def tear_down(self):
#        TracToolTestCase.tear_down(self)
#        del self.requester
#        del self.iso_label
#        del self.layout_number
#
#    def _create_tool(self):
#        self.tool = LibraryCreationTicketGenerator(self.requester,
#                                                   self.iso_label,
#                                                   self.layout_number)
#
#    def test_result(self):
#        self._create_tool()
#        ticket_id = self.tool.get_ticket_id()
#        self.assert_true(self.tool.transaction_completed())
#        self.assert_is_not_none(ticket_id)
#
#    def test_invalid_input(self):
#        req = self.requester
#        self.requester = self.requester.username
#        self._test_and_expect_errors()
#        self.requester = req
#        self.layout_number = '14'
#        self._test_and_expect_errors()
#        self.layout_number = 14
#        self.iso_label = 14
#        self._test_and_expect_errors()
#
#
#class LibraryCreationIsoCreatorTestCase(TracToolTestCase):
#
#    def set_up(self):
#        TracToolTestCase.set_up(self)
#        self.library = None
#        self.library_name = 'testlib'
#        self.stream = None
#        self.requester = get_user('sachse')
#        self.FILE_PATH = 'thelma:tests/tools/libcreation/generation/'
#        self.valid_file = 'valid_file.xls'
#
#    def tear_down(self):
#        TracToolTestCase.tear_down(self)
#        del self.library
#        del self.library_name
#        del self.stream
#        del self.requester
#        del self.FILE_PATH
#        del self.valid_file
#
#    def _create_tool(self):
#        self.tool = LibraryCreationIsoCreator(
#                        molecule_design_library=self.library)
#
#    def __continue_setup(self):
#        self.__read_file(self.valid_file)
#        self.__create_library()
#        self._create_tool()
#
#    def __read_file(self, file_name):
#        fn = self.FILE_PATH + file_name
#        f = resource_filename(*fn.split(':'))
#        stream = open(f, 'rb')
#        self.stream = stream.read()
#
#    def __create_library(self):
#        generator = LibraryGenerator(library_name=self.library_name,
#                                     stream=self.stream,
#                                     requester=self.requester)
#        self.library = generator.get_result()
#        self.assert_equal(len(self.library.iso_request.isos), 0)
#
#    def __check_result(self):
#        lib = self.tool.get_result()
#        self.assert_is_not_none(lib)
#        self.assert_equal(len(self.library.iso_request.isos), 3)
#        layout_numbers = []
#        ticket_numbers = set()
#        for lci in lib.iso_request.isos:
#            layout_numbers.append(lci.layout_number)
#            ti = lci.ticket_number
#            self.assert_is_not_none(ti)
#            self.assert_false(ti in ticket_numbers)
#            ticket_numbers.add(ti)
#        self.assert_equal(sorted(layout_numbers), [1, 2, 3])
#
#    def test_result_all(self):
#        self.__continue_setup()
#        self.__check_result()
#
#    def test_result_existing_iso(self):
#        self.__continue_setup()
#        LibraryCreationIso(ticket_number=99, layout_number=1, label='premade',
#                           iso_request=self.library.iso_request,
#                           rack_layout=RackLayout())
#        self.assert_equal(len(self.library.iso_request.isos), 1)
#        self.__check_result()
#
#    def test_invalid_input_values(self):
#        self._create_tool()
#        lib = self.tool.get_result()
#        self.assert_is_none(lib)
#        self._check_error_messages('The molecule design library must be ' \
#                                   'a MoleculeDesignLibrary object')
#
#    def test_no_isos_left(self):
#        self.__continue_setup()
#        for i in range(3):
#            LibraryCreationIso(ticket_number=99 + i, layout_number=1 + i,
#                               label='premade',
#                               iso_request=self.library.iso_request,
#                               rack_layout=RackLayout())
#        lib = self.tool.get_result()
#        self.assert_is_none(lib)
#        self._check_error_messages('The ISOs have already been created.')
#
#
#class LibraryCreationTicketWorklistUploaderTestCase(
#                            LibraryCreationWorklistWriterBaseTestCase,
#                            TracToolTestCase):
#
#    def set_up(self):
#        TracToolTestCase.set_up(self)
#        LibraryCreationWorklistWriterBaseTestCase.set_up(self)
#        self.file_map = None
#
#    def tear_down(self):
#        LibraryCreationWorklistWriterBaseTestCase.tear_down(self)
#        del self.file_map
#
#    def _create_tool(self):
#        self.tool = LibraryCreationTicketWorklistUploader(
#                    library_creation_iso=self.library_iso,
#                    file_map=self.file_map)
#
#    def _continue_setup(self, session):
#        LibraryCreationWorklistWriterBaseTestCase._continue_setup(self, session)
#        self.__write_files()
#        self._create_tool()
#
#    def _create_isos(self):
#        iso_creator = LibraryCreationIsoCreator(
#                                molecule_design_library=self.library)
#        self.library = iso_creator.get_result()
#        self.assert_is_not_none(self.library)
#
#    def __write_files(self):
#        writer = LibraryCreationWorklistWriter(
#                            library_creation_iso=self.library_iso,
#                            tube_destination_racks=self.tube_destination_racks,
#                            pool_stock_racks=self.pool_stock_rack_barcodes)
#        self.file_map = writer.get_result()
#        self.assert_is_not_none(self.file_map)
#
#    def test_result(self):
#        with RdbContextManager() as session:
#            self._continue_setup(session)
#            self.tool.run()
#            self.assert_true(self.tool.transaction_completed())
#            exp_fn = self.tool.FILE_NAME % (self.libname, 1)
#            self.assert_equal(self.tool.return_value, exp_fn)
#
#    def test_invalid_input_values(self):
#        with RdbContextManager() as session:
#            self._continue_setup(session)
#            lci = self.library_iso
#            self.library_iso = None
#            TracToolTestCase._test_and_expect_errors(self,
#                'The library creation ISO must be a LibraryCreationIso object')
#            self.library_iso = lci
#            self.file_map = None
#            TracToolTestCase._test_and_expect_errors(self,
#                'The file map must be a dict')
#            self.file_map = {2 : 3}
#            TracToolTestCase._test_and_expect_errors(self,
#                'The file name must be a basestring')
#
#    def test_trac_failure(self):
#        with RdbContextManager() as session:
#            self._continue_setup(session)
#            self.library_iso.ticket_number += 100000
#            TracToolTestCase._test_and_expect_errors(self, 'Fault')
#
#
#class LibraryCreationStockTransferReportTestCase(StockTransferReportTestCase,
#                                        LibraryCreationExecutorBaseTestCase):
#
#    def set_up(self):
#        LibraryCreationExecutorBaseTestCase.set_up(self)
#        StockTransferReportTestCase.set_up(self)
#        self.WL_PATH = 'thelma:tests/tools/libcreation/execution/'
#        self.csv_file_name = 'report_log_file.csv'
#        self.sample_stock_racks = dict()
#
#    def tear_down(self):
#        StockTransferReportTestCase.tear_down(self)
#        LibraryCreationExecutorBaseTestCase.tear_down(self)
#        del self.csv_file_name
#        del self.sample_stock_racks
#
#    def _continue_setup(self):
#        LibraryCreationExecutorBaseTestCase._continue_setup(self)
#        self.working_layout = self.library_layout
#        self.__create_sample_stock_racks_map()
#        self.__execute_transfers()
#        self._create_ticket(user=self.executor_user, iso_request=None)
#        self._create_tool()
#
#    def __create_sample_stock_racks_map(self):
#        for issr in self.library_iso.iso_sample_stock_racks:
#            self.sample_stock_racks[issr.sector_index] = issr
#
#    def __execute_transfers(self):
#        self.executor = LibraryCreationExecutor(user=self.executor_user,
#                            library_creation_iso=self.library_iso)
#        updated_iso = self.executor.get_result()
#        if updated_iso is None:
#            raise ValueError('Executor run has failed!')
#        else:
#            self.executed_worklists = \
#                                self.executor.get_executed_stock_worklists()
#
#    def _create_ticket(self, user, iso_request):
#        if self.CREATE_TICKET:
#            ticket_creator = LibraryCreationTicketGenerator(user,
#                                                            self.library_iso.label,
#                                                            self.library_iso.layout_number)
#            self.library_iso.ticket_number = ticket_creator.get_ticket_id()
#
#    def _create_report_uploader(self):
#        self.tool = LibraryCreationStockTransferReporter(
#                                            executor=self.executor)
#
#    def _create_tool_log_file_writer(self):
#        self.tool = LibraryCreationStockLogFileWriter(self.library_layout,
#                                                      self.executed_worklists,
#                                                      self.sample_stock_racks)
#
#
#class LibraryCreationStockTransferLogFileWriterTestCase(
#                                LibraryCreationStockTransferReportTestCase):
#
#    def test_result(self):
#        self._continue_setup()
#        tool_stream = self.tool.get_result()
#        self.assert_is_not_none(tool_stream)
#        self._compare_txt_file_stream(tool_stream, self.csv_file_name)
#
#    def test_invalid_input_values(self):
#        self._continue_setup()
#        ll = self.library_layout
#        self.library_layout = None
#        self._test_and_expect_errors('The library layout must be a ' \
#                                     'LibraryLayout')
#        self.library_layout = ll
#        ew = self.executed_worklists
#        self._test_invalid_executed_worklists_map()
#        self.executed_worklists = ew
#        issr = self.sample_stock_racks.values()[0]
#        self.sample_stock_racks = []
#        self._test_and_expect_errors('The sample stock racks map must be a ' \
#                                     'dict')
#        self.sample_stock_racks = {'3' : issr}
#        self._test_and_expect_errors('The sector index must be a int')
#        self.sample_stock_racks = {1 : 1}
#        self._test_and_expect_errors('The sample stock rack must be a ' \
#                                     'IsoSampleStockRack object')
#
#    def test_more_than_one_source_sample_molecule(self):
#        self._continue_setup()
#        for ew in self.executed_worklists.values():
#            ect = ew.executed_transfers[0]
#            sample = ect.source_container.sample
#            md = sample.sample_molecules[0].molecule.molecule_design
#            mol = Molecule(molecule_design=md,
#                           supplier=self._get_entity(IOrganization))
#            sample.make_sample_molecule(molecule=mol, concentration=1)
#            break
#        self._test_and_expect_errors('Some source container contain more ' \
#                                     'than one molecule design')
#
#
#class LibraryCreationStockTransferReporterTestCase(
#                                LibraryCreationStockTransferReportTestCase):
#
#    CREATE_TICKET = True
#
#    def test_result(self):
#        self._continue_setup()
#        self.tool.run()
#        self.assert_true(self.tool.transaction_completed())
#        tool_stream, comment = self.tool.return_value
#        self.assert_is_not_none(tool_stream)
#        self._compare_csv_file_stream(tool_stream, self.csv_file_name)
#        self.assert_is_not_none(comment)
#        self._compare_txt_file_content(comment, 'report_comment.txt')
#
#    def test_invalid_executor(self):
#        self._continue_setup()
#        self._test_invalid_executor()
#
#    def test_file_generation_failure(self):
#        self._continue_setup()
#        self._test_file_generation_failure('B4')
