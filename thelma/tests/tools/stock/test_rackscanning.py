"""
Test classes that deal with tasks related to rack scanning.

AAB
"""
from StringIO import StringIO
from datetime import datetime
from datetime import timedelta
from everest.entities.utils import get_root_aggregate
from everest.repositories.rdb.testing import RdbContextManager
from thelma.automation.parsers.rackscanning import RackScanningParser
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_item_status_managed
from thelma.automation.tools.semiconstants import get_positions_for_shape
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.stock.rackscanning import RackScanningAdjuster
from thelma.automation.tools.stock.rackscanning import RackScanningReportWriter
from thelma.automation.tools.worklists.tubehandler import TubeTransferData
from thelma.automation.tools.writers import LINEBREAK_CHAR
from thelma.automation.tools.writers import create_zip_archive
from thelma.automation.tools.writers import read_zip_archive
from thelma.interfaces import IPlateSpecs
from thelma.interfaces import IRack
from thelma.interfaces import ITubeRackSpecs
from thelma.interfaces import ITubeSpecs
from thelma.models.container import ContainerLocation
from thelma.models.container import Tube
from thelma.models.rack import TubeRack
from thelma.models.utils import get_user
from thelma.tests.tools.tooltestingutils import FileCreatorTestCase
from thelma.tests.tools.tooltestingutils import TestingLog


class RackScanningReportWriterTestCase(FileCreatorTestCase):

    def set_up(self):
        FileCreatorTestCase.set_up(self)
        self.WL_PATH = 'thelma:tests/tools/stock/rackscanning/'
        self.rack_barcodes = []
        self.tube_transfers = []
        self.log = TestingLog()
        # tube barcode - src rack barcode, src pos, trg rack barcode, trg pos
        self.transfer_data = {'1001' : ('09999991', 'A1', '09999991', 'A2'),
                              '1002' : ('09999991', 'B1', '09999992', 'B1'),
                              '1005' : ('09999991', 'C2', '09999993', 'C1'),
                              '1004' : ('09999993', 'A1', '09999992', 'A2')}

    def tear_down(self):
        FileCreatorTestCase.tear_down(self)
        del self.rack_barcodes
        del self.tube_transfers
        del self.log
        del self.transfer_data

    def _create_tool(self):
        self.tool = RackScanningReportWriter(rack_barcodes=self.rack_barcodes,
                            tube_transfers=self.tube_transfers, log=self.log)

    def __continue_setup(self):
        self.__create_tube_transfer_data()
        self.__create_rack_barcodes()
        self._create_tool()

    def __create_tube_transfer_data(self):
        for tube_barcode, data_tuple in self.transfer_data.iteritems():
            tt = TubeTransferData(tube_barcode=tube_barcode,
                              src_rack_barcode=data_tuple[0],
                              src_pos=get_rack_position_from_label(data_tuple[1]),
                              trg_rack_barcode=data_tuple[2],
                              trg_pos=get_rack_position_from_label(data_tuple[3]))
            self.tube_transfers.append(tt)

    def __create_rack_barcodes(self):
        barcodes = set()
        for tt in self.tube_transfers:
            barcodes.add(tt.src_rack_barcode) #pylint: disable=E1101
            barcodes.add(tt.trg_rack_barcode) #pylint: disable=E1101
        self.rack_barcodes = list(barcodes)

    def test_result(self):
        self.__continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_txt_file_stream(tool_stream, 'rack_scanning_report.txt',
                                      ignore_lines=[0])

    def test_invalid_input_values(self):
        self.__continue_setup()
        self.rack_barcodes = dict()
        self._test_and_expect_errors('The rack barcode list must be a list')
        self.rack_barcodes = [9999993]
        self._test_and_expect_errors('The rack barcode must be a basestring')
        self.__create_rack_barcodes()
        self.tube_transfers = dict()
        self._test_and_expect_errors('The tube transfer list must be a list')
        self.tube_transfers = [123]
        self._test_and_expect_errors('The tube transfer must be a ' \
                                     'TubeTransferData object')


class RackScanningAdjusterTestCase(FileCreatorTestCase):

    def set_up(self):
        FileCreatorTestCase.set_up(self)
        self.rack_scanning_stream = None
        self.adjust_database = False
        self.executor_user = get_user('it')
        self.WL_PATH = 'thelma:tests/tools/stock/rackscanning/'
        self.as_zip = False
        self.number_files = 1
        self.file_age = timedelta(hours=2)
        # transfer data: tube barcode - src rack barcode, src pos,
        #              trg rack barcode, trg pos
        self.transfer_data = {'1003' : ('09999999', 'C1', '09999999', 'C2'),
                              '1005' : ('09999999', 'E1', '09999999', 'E3')}
        # rack setup data: rack barocode - lists of tube barcodes and positions
        self.rack_data = {'09999999' : {'A1' : '1001', 'B1' : '1002',
                         'C1' : '1003', 'D1' : '1004', 'E1' : '1005'}}
        self.file_data = {'09999999' : {'A1' : '1001', 'B1' : '1002',
                         'C2' : '1003', 'D1' : '1004', 'E3' : '1005'}}
        # multi-rack data
        self.transfer_data_mr = {'1003' : ('09999999', 'C1', '09999990', 'C3'),
                          '1005' : ('09999999', 'E1', '09999999', 'E3'),
                          '1006' : ('09999990', 'A1', '09999999', 'F1'),
                          '1008' : ('09999990', 'C1', '09999990', 'C2')}
        # rack setup data: rack barocode - lists of tube barcodes and pos
        self.rack_data_mr = {'09999999' : {'A1' : '1001', 'B1' : '1002',
                          'C1' : '1003', 'D1' : '1004', 'E1' : '1005'},
                          '09999990' : {'A1' : '1006', 'B1' : '1007',
                                        'C1' : '1008'}}
        self.file_data_mr = {'09999999' : {'A1' : '1001', 'B1' : '1002',
                            'D1' : '1004', 'E3' : '1005', 'F1' : '1006'},
                            '09999990' : {'B1' : '1007', 'C3' : '1003',
                                          'C2' : '1008'}}
        self.report_comparison_file = None
        self.rack_agg = get_root_aggregate(IRack)
        self.new_racks = []

    def tear_down(self):
        FileCreatorTestCase.tear_down(self)
        del self.rack_scanning_stream
        del self.adjust_database
        del self.as_zip
        del self.number_files
        del self.file_age
        del self.transfer_data
        del self.rack_data
        del self.file_data
        del self.transfer_data_mr
        del self.rack_data_mr
        del self.file_data_mr
        del self.report_comparison_file
        del self.rack_agg
        del self.new_racks

    def _create_tool(self):
        self.tool = RackScanningAdjuster(user=self.executor_user,
                            rack_scanning_files=self.rack_scanning_stream,
                            adjust_database=self.adjust_database)

    def _test_and_expect_errors(self, msg=None):
        FileCreatorTestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_overview_stream())
        self.assert_is_none(self.tool.get_tube_transfer_worklist())

    def __continue_setup(self, session):
        self.__set_values_for_file_number()
        self.__create_streams()
        self.__create_racks(session)
        self._create_tool()

    def __set_values_for_file_number(self):
        if self.number_files == 1:
            self.report_comparison_file = 'report_one_rack.txt'
        else:
            self.report_comparison_file = 'report_several_racks.txt'
            self.as_zip = True
            self.transfer_data = self.transfer_data_mr
            self.rack_data = self.rack_data_mr
            self.file_data = self.file_data_mr

    def __create_streams(self):
        streams = dict()
        parser = RackScanningParser
        positions96 = get_positions_for_shape(get_96_rack_shape())
        timepoint = datetime.now() - self.file_age
        date_str = timepoint.strftime(parser.TIMESTAMP_FORMAT)
        for rack_barcode, tube_map in self.file_data.iteritems():
            stream = StringIO()
            # time stamp line
            date_line = parser.TIMESTAMP_MARKER + date_str + LINEBREAK_CHAR
            stream.write(date_line)
            # rack line
            rack_line = parser.RACK_BARCODE_MARKER + rack_barcode \
                        + LINEBREAK_CHAR
            stream.write(rack_line)
            # datalines
            for rack_pos in positions96:
                pos_label = rack_pos.label
                if tube_map.has_key(pos_label):
                    barcode = tube_map[pos_label]
                else:
                    barcode = parser.NO_TUBE_PLACEHOLDER
                data_line = pos_label + parser.SEPARATOR + barcode \
                            + LINEBREAK_CHAR
                stream.write(data_line)
            stream.seek(0)
            fn = 'file_%i.txt' % (len(streams) + 1)
            streams[fn] = stream
        if self.as_zip:
            zip_stream = StringIO()
            create_zip_archive(zip_stream, streams)
            self.rack_scanning_stream = zip_stream
        else:
            self.rack_scanning_stream = streams.values()[0]

    def __create_racks(self, session):
        tube_rack_specs = self._get_entity(ITubeRackSpecs)
        tube_specs = self._get_entity(ITubeSpecs)
        status = get_item_status_managed()
        for rack_barcode, tube_map in self.rack_data.iteritems():
            rack = TubeRack(label=rack_barcode, specs=tube_rack_specs,
                            status=status, barcode=rack_barcode)
            for pos_label, tube_barcode in tube_map.iteritems():
                tube = Tube(specs=tube_specs, status=status,
                            barcode=tube_barcode)
                ContainerLocation(container=tube, rack=rack,
                            position=get_rack_position_from_label(pos_label))
                rack.containers.append(tube)
            self.new_racks.append(rack)
            session.add(rack)
        session.commit()

    def __check_result(self):
        with RdbContextManager() as session:
            self.__continue_setup(session)
            res = self.tool.get_result()
            self.assert_is_not_none(res)
            session.commit()
            self.__check_report_file(res[self.tool.STREAM_KEY])
            self.__check_report_file(self.tool.get_overview_stream())
            if not self.adjust_database:
                self.assert_is_none(res[self.tool.WORKLIST_KEY])
                self.assert_is_none(self.tool.get_tube_transfer_worklist())
            else:
                self.__check_tube_transfer_worklist(res[self.tool.WORKLIST_KEY])
                self.__check_tube_transfer_worklist(
                                        self.tool.get_tube_transfer_worklist())

    def __check_report_file(self, tool_stream):
        self.assert_is_not_none(tool_stream)
        self._compare_txt_file_stream(tool_stream, self.report_comparison_file,
                                      ignore_lines=[0])
        tool_stream.seek(0)

    def __check_tube_transfer_worklist(self, ttw):
        self.assert_is_not_none(ttw)
        self.assert_equal(ttw.user, self.executor_user)
        self.assert_is_not_none(ttw.timestamp)
        tts = ttw.tube_transfers
        self.assert_equal(len(tts), len(self.transfer_data))
        racks = dict()
        for tt in tts:
            exp_data = self.transfer_data[tt.tube.barcode]
            src_rack = tt.source_rack
            src_rack_barcode = src_rack.barcode
            trg_rack = tt.target_rack
            trg_rack_barcode = trg_rack.barcode
            if not racks.has_key(src_rack_barcode):
                racks[src_rack_barcode] = src_rack
            self.assert_equal(src_rack_barcode, exp_data[0])
            self.assert_equal(tt.source_position.label, exp_data[1])
            if not racks.has_key(trg_rack_barcode):
                racks[trg_rack_barcode] = trg_rack
            self.assert_equal(trg_rack_barcode, exp_data[2])
            self.assert_equal(tt.target_position.label, exp_data[3])
        for rack_barcode, rack in racks.iteritems():
            tube_map = self.file_data[rack_barcode]
            self.assert_equal(len(rack.containers), len(tube_map))
            for tube in rack.containers:
                expected_barcode = tube_map[tube.location.position.label]
                self.assert_equal(expected_barcode, tube.barcode)

    def test_result_one_rack_no_update(self):
        self.__check_result()

    def test_result_one_rack_with_update(self):
        self.adjust_database = True
        self.__check_result()

    def test_result_one_rack_zip_no_update(self):
        self.as_zip = True
        self.__check_result()

    def test_result_one_rack_zip_with_update(self):
        self.as_zip = True
        self.adjust_database = True
        self.__check_result()

    def test_result_multi_racks_zip_no_update(self):
        self.number_files = 2
        self.__check_result()

    def test_result_multi_racks_zip_with_update(self):
        self.number_files = 2
        self.adjust_database = True
        self.__check_result()

    def test_file_too_old_one_rack(self):
        self.file_age = timedelta(days=4, hours=3, minutes=20)
        self.__check_result()
        self._check_warning_messages('The layout is older than 1 days ' \
                                     '(age: 4 days, 3 hours)')

    def test_file_too_old_several_racks(self):
        self.file_age = timedelta(days=4, hours=3, minutes=20)
        self.number_files = 2
        self.__check_result()
        self._check_warning_messages('is older than 1 days (age: 4 days, ' \
                                     '3 hours)')

    def test_invalid_input_values(self):
        with RdbContextManager() as session:
            self.__continue_setup(session)
            stream = self.rack_scanning_stream
            self.rack_scanning_stream = None
            self._test_and_expect_errors('The rack scanning stream is None!')
            self.rack_scanning_stream = stream
            self.adjust_database = None
            self._test_and_expect_errors('The "adjust DB" flag must be a bool')
            self.adjust_database = True
            self.executor_user = None
            self._test_and_expect_errors('The user must be a User object')

    def test_parser_handler_failure_one_rack(self):
        with RdbContextManager() as session:
            self.__continue_setup(session)
            self.rack_scanning_stream = self._get_expected_worklist_stream(
                                                    self.report_comparison_file)
            self._test_and_expect_errors('Error when trying to parse rack ' \
                                         'scanning file')

    def test_parser_handler_failure_multi_racks(self):
        self.number_files = 2
        with RdbContextManager() as session:
            self.__continue_setup(session)
            old_stream = self.rack_scanning_stream
            file_map = read_zip_archive(self.rack_scanning_stream)
            invalid_stream = self._get_expected_worklist_stream(
                                                    self.report_comparison_file)
            file_map['invalid_file'] = invalid_stream
            old_stream.close()
            self.rack_scanning_stream = StringIO()
            create_zip_archive(self.rack_scanning_stream, file_map)
            self._test_and_expect_errors('Error when trying to parse rack ' \
                                         'scanning file "invalid_file"')

    def test_missing_rack(self):
        self.rack_data = dict()
        with RdbContextManager() as session:
            self.__continue_setup(session)
            self._test_and_expect_errors('Could not find database records ' \
                                         'for the following rack barcodes:')

    def test_wrong_rack_type(self):
        self.rack_data = dict()
        with RdbContextManager() as session:
            self.__continue_setup(session)
            plate_specs = self._get_entity(IPlateSpecs)
            plate = plate_specs.create_rack(label='test_plate',
                                            barcode='09999999',
                                            status=get_item_status_managed())
            session.add(plate)
            self._test_and_expect_errors('The following rack are no tube ' \
                                         'racks: 09999999 (Plate)')

    def test_no_differences(self):
        self.rack_data = self.file_data
        with RdbContextManager() as session:
            self.__continue_setup(session)
            self._test_and_expect_errors('The content of rack scanning ' \
                        'file(s) matches the status of the racks in the ' \
                        'database. There is nothing to update.')

    def test_tube_missing_in_database(self):
        self.rack_data = {'09999999' : {'A1' : '1001', 'B1' : '1002',
                                        'D1' : '1004'}}
        with RdbContextManager() as session:
            self.__continue_setup(session)
            self._test_and_expect_errors('Some tubes from the rack scanning ' \
                    'file(s) have not been found in the database records of ' \
                    'the investigated racks: 1003, 1005. Investigated racks: ' \
                    '09999999.')

    def test_tube_missing_in_file(self):
        self.file_data = {'09999999' : {'A1' : '1001', 'D1' : '1004',
                                        'E3' : '1005'}}
        with RdbContextManager() as session:
            self.__continue_setup(session)
            self._test_and_expect_errors('Some tube expected in the ' \
                    'investigated racks have not been found in the rack ' \
                    'scanning file(s): 1002, 1003. Investigated racks: ' \
                    '09999999.')

    def test_not_feasible(self):
        self.number_files = 2
        self.file_data_mr['09999990'] = {'B1' : '1007', 'C1' : '1003',
                                         'C2' : '1008'}
        with RdbContextManager() as session:
            self.__continue_setup(session)
            self._test_and_expect_errors('Some positions are both source ' \
                'position of one rack and target positions of another rack.')
