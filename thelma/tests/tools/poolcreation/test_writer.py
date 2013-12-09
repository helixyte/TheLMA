#"""
#Tests for classes involved in pool stock sample worklist writing
#
#AAB
#"""
#from everest.entities.utils import get_root_aggregate
#from everest.repositories.rdb.testing import RdbContextManager
#from thelma.automation.tools.libcreation.base import LibraryLayout
#from thelma.automation.tools.libcreation.base import LibraryPosition
#from thelma.automation.tools.poolcreation.writer \
#    import PoolCreationCyBioOverviewWriter
#from thelma.automation.tools.poolcreation.writer \
#    import PoolCreationIsoLayoutWriter
#from thelma.automation.tools.poolcreation.writer \
#    import PoolCreationWorklistWriter
#from thelma.automation.tools.poolcreation.writer \
#    import PoolCreationXL20ReportWriter
#from thelma.automation.tools.semiconstants import get_96_rack_shape
#from thelma.automation.tools.semiconstants import get_item_status_managed
#from thelma.automation.tools.semiconstants import get_rack_position_from_label
#from thelma.automation.tools.worklists.tubehandler import TubeTransferData
#from thelma.interfaces import IMoleculeDesignLibrary
#from thelma.interfaces import IMoleculeDesignPool
#from thelma.interfaces import ITubeRack
#from thelma.interfaces import ITubeRackSpecs
#from thelma.interfaces import ITubeSpecs
#from thelma.models.container import Tube
#from thelma.models.iso import ISO_STATUS
#from thelma.models.iso import IsoSampleStockRack
#from thelma.models.library import LibraryCreationIso
#from thelma.models.liquidtransfer import PlannedWorklist
#from thelma.models.liquidtransfer import TRANSFER_TYPES
#from thelma.models.racklayout import RackLayout
#from thelma.models.sample import Sample
#from thelma.tests.tools.poolcreation.utils import PoolCreationTestCase
#from thelma.tests.tools.tooltestingutils import FileCreatorTestCase
#from thelma.tests.tools.tooltestingutils import TestingLog
#
#
#class PoolCreationWriterTestCase(PoolCreationTestCase, FileCreatorTestCase):
#
#    def set_up(self):
#        PoolCreationTestCase.set_up(self)
#        self.TEST_FILE_PATH = 'thelma:tests/tools/poolcreation/writer/'
#        self.WL_PATH = 'thelma:tests/tools/poolcreation/writer/'
#        self.VALID_FILE = 'valid_file.xls'
#        self.layout_file = 'layout_writer.csv'
#        self.cybio_overview_file = 'cybio_overview.txt'
#        self.xl20_report_file = 'xl20report.txt'
#        self.xl20_worklist_file = 'xl20_worklist.csv'
#        self.log = TestingLog()
#        self.pool_creation_iso = None
#        self.iso_request_label = 'testlib'
#        self.stock_conc = 50000 # 50 uM
#        self.iso_request_label = 'writer_test'
#        self.layout_number = 2
#        self.iso_label = '%s-%i' % (self.iso_request_label, self.layout_number)
#        self.target_volume = 30 # 30 ul
#        self.target_concentration = 10000 # 10 uM
#        self.pool_stock_rack_barcode = '09999999'
#        self.rack_map = dict()
#        self.tube_destination_barcodes = ['08000001', '08000002', '08000003']
#        self.pool_iso_layout = None
#        self.iso_request = None
#        # pos label - pool ID, stock tube barcodes
#        self.pos_data = dict(A1=[1061383, ['10101', '10102', '10103']],
#                             B1=[1060579, ['10201', '10202', '10203']],
#                             C1=[1065744, ['10301', '10302', '10303']],
#                             D1=[1061384, ['10401', '10402', '10403']])
#        self.tube_src_positions = {
#                '10101': 'A1', '10102' : 'A2', '10103' : 'A3',
#                '10201': 'B1', '10202' : 'B2', '10203' : 'B3',
#                '10301': 'C1', '10302' : 'C2', '10303' : 'C3',
#                '10401': 'D1', '10402' : 'D2', '10403' : 'D3',
#                '10501': 'E1', '10502' : 'E2', '10503' : 'E3',
#                '10601': 'F1', '10602' : 'F2', '10603' : 'F3'}
#        self.source_rack_barcode = '09777777'
#        self.take_out_volume = 2
#        self.session = None
#
#    def tear_down(self):
#        PoolCreationTestCase.tear_down(self)
#        del self.WL_PATH
#        del self.layout_file
#        del self.cybio_overview_file
#        del self.xl20_report_file
#        del self.xl20_worklist_file
#        del self.log
#        del self.pool_creation_iso
#        del self.stock_conc
#        del self.layout_number
#        del self.iso_label
#        del self.pool_stock_rack_barcode
#        del self.tube_destination_barcodes
#        del self.pool_iso_layout
#        del self.pos_data
#        del self.tube_src_positions
#        del self.source_rack_barcode
#        del self.take_out_volume
#        del self.session
#
#    def _continue_setup(self): #pylint: disable=W0221
#        PoolCreationTestCase._continue_setup(self, file_name=self.VALID_FILE)
#        self._create_library_layout()
#        self._create_pool_iso()
#        if not self.session is None:
#            lib_agg = get_root_aggregate(IMoleculeDesignLibrary)
#            lib_agg.add(self.library)
#            self.__create_tube_racks()
#        self._create_tool()
#
#    def _create_library_layout(self):
#        self.pool_iso_layout = LibraryLayout(shape=get_96_rack_shape())
#        pool_agg = get_root_aggregate(IMoleculeDesignPool)
#        for pos_label, data_tuple in self.pos_data.iteritems():
#            rack_pos = get_rack_position_from_label(pos_label)
#            pool = pool_agg.get_by_id(data_tuple[0])
#            lib_pos = LibraryPosition(rack_position=rack_pos, pool=pool,
#                                      stock_tube_barcodes=data_tuple[1])
#            self.pool_iso_layout.add_position(lib_pos)
#
#    def _create_pool_iso(self):
#        self.pool_creation_iso = LibraryCreationIso(ticket_number=123,
#                        layout_number=self.layout_number, label=self.iso_label,
#                        iso_request=self.library.iso_request,
#                        rack_layout=self.pool_iso_layout.create_rack_layout())
#
#    def __create_tube_racks(self):
#        tube_rack_specs = self._get_entity(ITubeRackSpecs)
#        tube_specs = self._get_entity(ITubeSpecs)
#        status = get_item_status_managed()
#        rack_counter = -1
#        # tube destination racks (tube transfer targets)
#        for barcode in self.tube_destination_barcodes:
#            tube_rack = tube_rack_specs.create_rack(status=status,
#                                                    label=barcode)
#            tube_rack.barcode = barcode
#            tube_rack.id = rack_counter
#            rack_counter -= 1
#            self.session.add(tube_rack)
#            self.rack_map[barcode] = tube_rack
#        # pool stock racks
#        pool_stock_rack_label = 'test_pool_stock_rack'
#        ps_rack = tube_rack_specs.create_rack(label=pool_stock_rack_label,
#                                              status=status)
#        ps_rack.barcode = self.pool_stock_rack_barcode
#        self.rack_map[self.pool_stock_rack_barcode] = ps_rack
#        tube_counter = 0
#        for pos_label in self.pos_data.keys():
#            rack_pos = get_rack_position_from_label(pos_label)
#            tube_barcode = '4%04i' % (tube_counter)
#            tube_counter += 1
#            tube = Tube.create_from_rack_and_position(specs=tube_specs,
#                              status=status, barcode=tube_barcode,
#                              rack=ps_rack, position=rack_pos)
#            self.session.add(tube)
#            ps_rack.containers.append(tube)
#        self.session.add(ps_rack)
#        self.assert_equal(len(ps_rack.containers), len(self.pos_data))
#        # tube transfer source rack
#        source_rack = tube_rack_specs.create_rack(status=status,
#                                                  label='tt source rack')
#        source_rack.barcode = self.source_rack_barcode
#        for tube_barcode, pos_label in self.tube_src_positions.iteritems():
#            rack_pos = get_rack_position_from_label(pos_label)
#            tube = Tube.create_from_rack_and_position(specs=tube_specs,
#                      status=status, barcode=tube_barcode, rack=source_rack,
#                      position=rack_pos)
#            self.session.add(tube)
#            source_rack.containers.append(tube)
#        self.session.add(source_rack)
#        self.session.commit()
#        self.assert_equal(len(self.tube_src_positions),
#                          len(source_rack.containers))
#
#
#class PoolCreationXL20ReportWriterTestCase(PoolCreationWriterTestCase):
#
#    def set_up(self):
#        PoolCreationWriterTestCase.set_up(self)
#        self.tube_transfers = []
#        self.rack_locations = {'09999999' : 'freezer1 (shelf 2)',
#                               '09999998' : None}
#        self.xl20_report_file = 'xl20report_single.txt'
#
#    def tear_down(self):
#        PoolCreationWriterTestCase.tear_down(self)
#        del self.tube_transfers
#        del self.rack_locations
#
#    def _create_tool(self):
#        self.tool = PoolCreationXL20ReportWriter(log=self.log,
#                                 tube_transfers=self.tube_transfers,
#                                 iso_request_name=self.iso_request_label,
#                                 layout_number=self.layout_number,
#                                 source_rack_locations=self.rack_locations,
#                                 take_out_volume=self.take_out_volume)
#
#    def _continue_setup(self):
#        self.__create_tube_transfers()
#        self._create_tool()
#
#    def __create_tube_transfers(self):
#        tt_data = [['1001', '09999999', 'A1', '09000000', 'A1'],
#                   ['1003', '09999999', 'B1', '09000000', 'B2'],
#                   ['1009', '09999998', 'A1', '09000000', 'C3'],
#                   ['1010', '09999998', 'B1', '09000001', 'A1']]
#        for data_list in tt_data:
#            tt = TubeTransferData(tube_barcode=data_list[0],
#                          src_rack_barcode=data_list[1],
#                          src_pos=get_rack_position_from_label(data_list[2]),
#                          trg_rack_barcode=data_list[3],
#                          trg_pos=get_rack_position_from_label(data_list[4]))
#            self.tube_transfers.append(tt)
#
#    def test_result(self):
#        self._continue_setup()
#        tool_stream = self.tool.get_result()
#        self.assert_is_not_none(tool_stream)
#        self._compare_txt_file_stream(tool_stream, self.xl20_report_file,
#                                      ignore_lines=[0])
#
#    def test_invalid_input(self):
#        tt = self.tube_transfers
#        self.tube_transfers = dict()
#        self._test_and_expect_errors('The tube transfer list must be a list ' \
#                                     'object (obtained: dict).')
#        self.tube_transfers = [1]
#        self._test_and_expect_errors('The tube transfer must be a ' \
#                                     'TubeTransferData object (obtained: int).')
#        self.tube_transfers = tt
#        self.iso_request_label = 123
#        self._test_and_expect_errors('The ISO request name must be a ' \
#                                     'basestring object (obtained: int).')
#        self.iso_request_label = 'testlib'
#        self.layout_number = 3.4
#        self._test_and_expect_errors('The layout number must be a int ' \
#                                     'object (obtained: float).')
#        self.layout_number = 2
#        self.take_out_volume = 0
#        self._test_and_expect_errors()
#        self.take_out_volume = 2
#        self.rack_locations = []
#        self._test_and_expect_errors('The rack location map must be a dict ' \
#                                     'object (obtained: list).')
#
#
#class PoolCreationCyBioOverviewWriterTestCase(PoolCreationWriterTestCase):
#
#    def set_up(self):
#        PoolCreationWriterTestCase.set_up(self)
#        self.buffer_volume = 24
#
#    def tear_down(self):
#        PoolCreationWriterTestCase.tear_down(self)
#        del self.buffer_volume
#
#    def _create_tool(self):
#        self.tool = PoolCreationCyBioOverviewWriter(log=self.log,
#                        pool_creation_iso=self.pool_creation_iso,
#                        pool_stock_rack_barcode=self.pool_stock_rack_barcode,
#                        tube_destination_racks=self.tube_destination_barcodes,
#                        take_out_volume=self.take_out_volume,
#                        buffer_volume=self.buffer_volume)
#
#    def test_result(self):
#        self._continue_setup()
#        tool_stream = self.tool.get_result()
#        self.assert_is_not_none(tool_stream)
#        self._compare_txt_file_stream(tool_stream, self.cybio_overview_file,
#                                      ignore_lines=[0])
#
#    def test_invalid_input(self):
#        self._continue_setup()
#        pci = self.pool_creation_iso
#        self.pool_creation_iso = None
#        self._test_and_expect_errors('The pool creation ISO must be a ' \
#                             'LibraryCreationIso object (obtained: NoneType).')
#        self.pool_creation_iso = pci
#        barcode = self.pool_stock_rack_barcode
#        self.pool_stock_rack_barcode = 123
#        self._test_and_expect_errors('The pool stock rack barcode must be a ' \
#                                     'basestring object (obtained: int).')
#        self.pool_stock_rack_barcode = barcode
#        tdb = self.tube_destination_barcodes
#        self.tube_destination_barcodes = dict()
#        self._test_and_expect_errors('The tube destination rack map must be ' \
#                                     'a list object (obtained: dict).')
#        self.tube_destination_barcodes = [123]
#        self._test_and_expect_errors('The barcode for a tube destination ' \
#                        'rack must be a basestring object (obtained: int).')
#        self.tube_destination_barcodes = []
#        self._test_and_expect_errors('There are no barcodes in the ' \
#                                     'destination rack map!')
#        self.tube_destination_barcodes = tdb
#        self.take_out_volume = 0
#        self._test_and_expect_errors('The stock take out volume must be a ' \
#                                     'positive number (obtained: 0).')
#        self.take_out_volume = 2
#        self.buffer_volume = 0
#        self._test_and_expect_errors('The buffer volume must be a positive ' \
#                                     'number (obtained: 0).')
#
#
#class PoolCreationIsoLayoutWriterTestCase(PoolCreationWriterTestCase):
#
#    def set_up(self):
#        PoolCreationWriterTestCase.set_up(self)
#        self.layout = None
#
#    def tear_down(self):
#        PoolCreationWriterTestCase.tear_down(self)
#        del self.layout
#
#    def _create_tool(self):
#        self.tool = PoolCreationIsoLayoutWriter(log=self.log,
#                                    pool_creation_layout=self.pool_iso_layout)
#
#    def _continue_setup(self):
#        self._create_library_layout()
#        self._create_tool()
#
#    def test_result(self):
#        self._continue_setup()
#        tool_stream = self.tool.get_result()
#        self.assert_is_not_none(tool_stream)
#        self._compare_csv_file_stream(tool_stream, self.layout_file)
#
#    def test_invalid_input(self):
#        self._create_tool()
#        self._test_and_expect_errors('The ISO layout must be a LibraryLayout ' \
#                                     'object (obtained: NoneType)')
#
#
#class PoolCreationWorklistWriterTestCase(PoolCreationWriterTestCase):
#
#    def _create_tool(self):
#        self.tool = PoolCreationWorklistWriter(
#                   pool_creation_iso=self.pool_creation_iso,
#                   tube_destination_racks=self.tube_destination_barcodes,
#                   pool_stock_rack_barcode=self.pool_stock_rack_barcode)
#
#    def __check_file_map(self, file_map):
#        self.assert_is_not_none(file_map)
#        self.assert_equal(len(file_map), 4)
#        for fn, stream in file_map.iteritems():
#            if 'layout.csv' in fn:
#                self._compare_csv_file_stream(stream, self.layout_file)
#            elif 'xl20_worklist' in fn:
#                self._compare_csv_file_stream(stream, self.xl20_worklist_file)
#            elif 'xl20_report' in fn:
#                self._compare_txt_file_stream(stream, self.xl20_report_file,
#                                              ignore_lines=[0])
#            elif 'CyBio_instructions' in fn:
#                self._compare_txt_file_stream(stream, self.cybio_overview_file)
#            else:
#                raise ValueError('unknown file: %s' % (fn))
#
#    def __check_iso(self):
#        issrs = self.pool_creation_iso.iso_sample_stock_racks
#        self.assert_equal(len(issrs), 1)
#        issr = issrs[0]
#        worklist = issr.planned_worklist
#        self.assert_is_not_none(worklist)
#        exp_positions = self.pos_data.keys()
#        found_positions = []
#        for barcode in self.tube_destination_barcodes:
#            self.assert_true(barcode in worklist.label)
#        self.assert_equal(len(worklist.planned_transfers), len(exp_positions))
#        for pct in worklist.planned_transfers:
#            self.assert_equal(pct.type, TRANSFER_TYPES.CONTAINER_TRANSFER)
#            self._compare_transfer_volume(pct, self.take_out_volume)
#            found_positions.append(pct.target_position.label)
#        self.assert_equal(sorted(exp_positions), sorted(found_positions))
#
#    def test_result(self):
#        with RdbContextManager() as session:
#            self.session = session
#            self._continue_setup()
#            file_map = self.tool.get_result()
#            self.assert_is_not_none(file_map)
#            self.__check_file_map(file_map)
#            self.__check_iso()
#
#    def test_invalid_input_values(self):
#        self._continue_setup()
#        pci = self.pool_creation_iso
#        self.pool_creation_iso = None
#        self._test_and_expect_errors('The pool creation ISO must be a ' \
#                         'LibraryCreationIso object (obtained: NoneType).')
#        self.pool_creation_iso = pci
#        self.pool_creation_iso.status = ISO_STATUS.DONE
#        self._test_and_expect_errors('Unexpected ISO status: "done"')
#        self.pool_creation_iso.status = ISO_STATUS.QUEUED
#        barcode = self.pool_stock_rack_barcode
#        self.pool_stock_rack_barcode = 123
#        self._test_and_expect_errors('The pool stock rack barcode must be a ' \
#                                     'basestring object (obtained: int).')
#        self.pool_stock_rack_barcode = barcode
#        self.tube_destination_barcodes = dict()
#        self._test_and_expect_errors('The tube destination rack map must be ' \
#                                     'a list object (obtained: dict).')
#        self.tube_destination_barcodes = [123]
#        self._test_and_expect_errors('The barcode for a tube destination ' \
#                        'rack must be a basestring object (obtained: int).')
#        self.tube_destination_barcodes = []
#        self._test_and_expect_errors('There are no barcodes in the ' \
#                                     'destination rack map!')
#
#    def test_missing_worklist_series(self):
#        with RdbContextManager() as session:
#            self.session = session
#            self._continue_setup()
#            self.library.iso_request.worklist_series = None
#            self._test_and_expect_errors('Unable to find worklist series for ' \
#                                         'ISO request!')
#
#    def test_unexpected_worklist_series(self):
#        with RdbContextManager() as session:
#            self.session = session
#            self._continue_setup()
#            ws = self.library.iso_request.worklist_series
#            wl = PlannedWorklist(label='add')
#            ws.add_worklist(index=1, worklist=wl)
#            self._test_and_expect_errors('The worklist series of the ISO ' \
#                         'request has an unexpected length (2, expected: 1).')
#
#    def test_different_buffer_volumes(self):
#        with RdbContextManager() as session:
#            self.session = session
#            self._continue_setup()
#            ws = self.library.iso_request.worklist_series
#            wl = ws.get_worklist_for_index(0)
#            for pct in wl.planned_transfers:
#                pct.volume = (pct.volume * 2)
#                break
#            self._test_and_expect_errors('There are different volumes in the ' \
#                                         'buffer dilution worklist!')
#
#    def test_unknown_rack(self):
#        with RdbContextManager() as session:
#            self.session = session
#            self._continue_setup()
#            self.pool_stock_rack_barcode = '09876543'
#            self._test_and_expect_errors('The following racks have not been ' \
#                                         'found in the DB: 09876543!')
#
#    def test_library_layout_conversion_error(self):
#        with RdbContextManager() as session:
#            self.session = session
#            self._continue_setup()
#            self.pool_creation_iso.rack_layout = RackLayout(
#                                                shape=get_96_rack_shape())
#            self._test_and_expect_errors('Error when trying to convert ' \
#                                         'library layout.')
#
#    def test_invalid_tube_rack_number(self):
#        with RdbContextManager() as session:
#            self.session = session
#            self.tube_destination_barcodes = self.tube_destination_barcodes[:-1]
#            self._continue_setup()
#            self._test_and_expect_errors('You need to provide 3 empty racks. ' \
#                                         'You have provided 2 barcodes.')
#
#    def test_non_empty_tube_destination_rack(self):
#        with RdbContextManager() as session:
#            self.session = session
#            self._continue_setup()
#            self.tube_destination_barcodes[0] = self.source_rack_barcode
#            self._test_and_expect_errors('The following tube destination ' \
#                            'racks you have chosen are not empty: 09777777.')
#
#    def test_invalid_pool_stock_rack_additional(self):
#        with RdbContextManager() as session:
#            self.session = session
#            self._continue_setup()
#            rack_agg = get_root_aggregate(ITubeRack)
#            rack = rack_agg.get_by_slug(self.pool_stock_rack_barcode)
#            self.assert_is_not_none(rack)
#            tube_specs = self._get_entity(ITubeSpecs)
#            Tube.create_from_rack_and_position(specs=tube_specs,
#                       status=get_item_status_managed(),
#                       barcode='1222', rack=rack,
#                       position=get_rack_position_from_label('G8'))
#            file_map = self.tool.get_result()
#            self.__check_file_map(file_map)
#            self._check_warning_messages('There are some tubes in the pool ' \
#                     'stock rack (09999999) that are located in positions ' \
#                     'that should be empty: G8. Please remove the tubes ' \
#                     'before continuing.')
#
#    def test_invalid_pool_stock_rack_not_empty(self):
#        with RdbContextManager() as session:
#            self.session = session
#            self._continue_setup()
#            rack_agg = get_root_aggregate(ITubeRack)
#            rack = rack_agg.get_by_slug(self.pool_stock_rack_barcode)
#            self.assert_is_not_none(rack)
#            tube = rack.containers[0]
#            Sample(volume=5, container=tube)
#            self._test_and_expect_errors('Some tubes in the pool stock rack ' \
#                                         '(09999999) which are not empty')
#
#    def test_invalid_pool_stock_rack_missing(self):
#        with RdbContextManager() as session:
#            self.session = session
#            self._continue_setup()
#            rack_agg = get_root_aggregate(ITubeRack)
#            rack = rack_agg.get_by_slug(self.pool_stock_rack_barcode)
#            self.assert_is_not_none(rack)
#            del rack.containers[0]
#            self._test_and_expect_errors('There are some tubes missing in ' \
#                                         'the pool stock rack (09999999)')
#
#    def test_too_many_sample_stock_racks(self):
#        with RdbContextManager() as session:
#            self.session = session
#            self._continue_setup()
#            wl = PlannedWorklist(label='add')
#            IsoSampleStockRack(iso=self.pool_creation_iso,
#                       rack=self.rack_map[self.tube_destination_barcodes[0]],
#                       sector_index=0, planned_worklist=wl)
#            IsoSampleStockRack(iso=self.pool_creation_iso,
#                       rack=self.rack_map[self.tube_destination_barcodes[1]],
#                       sector_index=1, planned_worklist=wl)
#            self._test_and_expect_errors('There are too many ISO sample ' \
#                      'stock racks for this ISOs.Please check and reduce the ' \
#                      'number to 1 or less.')
#
#    def test_unknown_tube(self):
#        with RdbContextManager() as session:
#            self.session = session
#            self._continue_setup()
#            for lib_pos in self.pool_iso_layout.working_positions():
#                lib_pos.stock_tube_barcodes[0] = '122222'
#                break
#            self.pool_creation_iso.rack_layout = \
#                                    self.pool_iso_layout.create_rack_layout()
#            self._test_and_expect_errors('Could not find tubes for the ' \
#                                         'following tube barcodes: 122222')
