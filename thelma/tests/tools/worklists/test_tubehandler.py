"""
Test for tubehandler (XL20) related base classes.
"""
from datetime import datetime
from everest.testing import RdbContextManager
from everest.testing import check_attributes
from pkg_resources import resource_filename # pylint: disable=E0611,F0401
from thelma.automation.tools.semiconstants import get_item_status_managed
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.worklists.tubehandler import TubeTransferData
from thelma.automation.tools.worklists.tubehandler import TubeTransferExecutor
from thelma.automation.tools.worklists.tubehandler import XL20Executor
from thelma.automation.tools.worklists.tubehandler import XL20WorklistWriter
from thelma.interfaces import IPlateSpecs
from thelma.interfaces import ITubeRackSpecs
from thelma.interfaces import ITubeSpecs
from thelma.models.container import Tube
from thelma.models.rack import TubeRack
from thelma.models.tubetransfer import TubeTransfer
from thelma.models.utils import get_user
from thelma.testing import ThelmaModelTestCase
from thelma.tests.tools.tooltestingutils import FileCreatorTestCase
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase
import pytz


class TubeTransferDataTestCase(ThelmaModelTestCase):

    def __get_init_data(self):
        return dict(tube_barcode='0001', src_rack_barcode='09999999',
                    src_pos=get_rack_position_from_label('A1'),
                    trg_rack_barcode='09999998',
                    trg_pos=get_rack_position_from_label('B1'))

    def test_init(self):
        kw = self.__get_init_data()
        tt = TubeTransferData(**kw)
        self.assert_is_not_none(tt)
        check_attributes(tt, kw)

    def test_from_tube_transfer(self):
        tube_transfer = self._create_tube_transfer()
        tt = TubeTransferData.from_tube_transfer(tube_transfer)
        self.assert_equal(tt.tube_barcode, tube_transfer.tube.barcode)
        self.assert_equal(tt.src_rack_barcode,
                          tube_transfer.source_rack.barcode)
        self.assert_equal(tt.src_pos, tube_transfer.source_position)
        self.assert_equal(tt.trg_rack_barcode,
                          tube_transfer.target_rack.barcode)
        self.assert_equal(tt.trg_pos, tube_transfer.target_position)


class XL20WorklistWriterTestCase(FileCreatorTestCase):

    def set_up(self):
        FileCreatorTestCase.set_up(self)
        self.log = TestingLog()
        self.WL_PATH = 'thelma:tests/tools/worklists/test_files/'
        self.tube_transfers = []
        # tube barcode, src rack barcode, src pos label, trg rack barcode,
        # trg pos label
        self.transfer_data = [['1001', '09999998', 'A1', '09999977', 'G1'],
                              ['1002', '09999999', 'B1', '09999976', 'G1'],
                              ['1003', '09999998', 'A1', '09999978', 'G1'],
                              ['1004', '09999998', 'C2', '09999977', 'G2']]

    def tear_down(self):
        FileCreatorTestCase.tear_down(self)
        del self.log
        del self.tube_transfers
        del self.transfer_data

    def _create_tool(self):
        self.tool = XL20WorklistWriter(log=self.log,
                                       tube_transfers=self.tube_transfers)

    def __continue_setup(self, create_tube_transfer_entities=False):
        if create_tube_transfer_entities:
            self.__create_tube_transfer_entities()
        else:
            self.__create_tube_transfer_data()
        self._create_tool()

    def __create_tube_transfer_entities(self):
        for value_list in self.transfer_data:
            tube = self._create_tube(barcode=value_list[0])
            src_rack = self._create_tube_rack(barcode=value_list[1])
            src_pos = get_rack_position_from_label(value_list[2])
            trg_rack = self._create_tube_rack(barcode=value_list[3])
            trg_pos = get_rack_position_from_label(value_list[4])
            tt = TubeTransfer(tube=tube, source_rack=src_rack,
                              source_position=src_pos, target_rack=trg_rack,
                              target_position=trg_pos)
            self.tube_transfers.append(tt)

    def __create_tube_transfer_data(self):
        for value_list in self.transfer_data:
            src_pos = get_rack_position_from_label(value_list[2])
            value_list[2] = src_pos
            trg_pos = get_rack_position_from_label(value_list[4])
            value_list[4] = trg_pos
            tt = TubeTransferData(*tuple(value_list))
            self.tube_transfers.append(tt)

    def __check_result(self):
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream, 'xl20_worklist.csv')

    def test_result_tube_transfer_entities(self):
        self.__continue_setup(create_tube_transfer_entities=True)
        self.__check_result()

    def test_result_tube_transfer_data(self):
        self.__continue_setup()
        self.__check_result()

    def test_invalid_tube_transfers(self):
        self.__continue_setup()
        self.tube_transfers = dict()
        self._test_and_expect_errors('The tube transfer list must be a list')
        self.tube_transfers = [13]
        self._test_and_expect_errors('The tube transfer must be a ' \
                                     'TubeTransfer or a TubeTransferData type')


class TubeTransferExecutorTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.log = TestingLog()
        self.tube_transfers = []
        self.executor_user = get_user('it')
        # tube barcode, src rack barcode, src pos label, trg rack barcode,
        # trg pos label
        self.transfer_data = {'1001' : ['09999998', 'A1', '09999977', 'G1'],
                              '1004' : ['09999998', 'A4', '09999978', 'G1'],
                              '1005' : ['09999999', 'B1', '09999976', 'G1'],
                              '1008' : ['09999999', 'C2', '09999977', 'G2']}
        # rack barcode, value: tube barcode, position
        self.tube_ini_data = {'09999998' : [('1001', 'A1'), ('1002', 'A2'),
                                            ('1003', 'A3'), ('1004', 'A4')],
                              '09999999' : [('1005', 'B1'), ('1006', 'B2'),
                                            ('1007', 'C1'), ('1008', 'C2')],
                              '09999976' : [('1009', 'B1'), ('1010', 'B2')]}
        # additional setup data
        self.rack_map = dict()
        self.tube_map = dict()
        self.tube_specs = self._get_entity(ITubeSpecs)

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.log
        del self.tube_transfers
        del self.transfer_data
        del self.tube_ini_data
        del self.rack_map
        del self.tube_map
        del self.tube_specs

    def _create_tool(self):
        self.tool = TubeTransferExecutor(tube_transfers=self.tube_transfers,
                                         user=self.executor_user, log=self.log)

    def __continue_setup(self, session):
        self.__create_racks(session)
        self.__fill_racks(session)
        self.__create_tube_transfers()
        self._create_tool()

    def __create_racks(self, session):
        barcodes = set()
        for data_list in self.transfer_data.values():
            barcodes.add(data_list[0])
            barcodes.add(data_list[2])
        tube_rack_specs = self._get_entity(ITubeRackSpecs)
        for barcode in barcodes:
            tube_rack = TubeRack(label=barcode, specs=tube_rack_specs,
                                 status=get_item_status_managed())
            tube_rack.barcode = barcode
            self.rack_map[barcode] = tube_rack
            session.add(tube_rack)

    def __fill_racks(self, session):
        managed_status = get_item_status_managed()
        for rack_barcode, tube_tuples in self.tube_ini_data.iteritems():
            rack = self.rack_map[rack_barcode]
            for tube_data in tube_tuples:
                tube = Tube.create_from_rack_and_position(specs=
                            self.tube_specs, status=managed_status,
                            rack=rack, barcode=tube_data[0],
                            position=get_rack_position_from_label(tube_data[1]))
                rack.containers.append(tube)
                self.tube_map[tube.barcode] = tube
                session.add(tube)
        session.commit()

    def __create_tube_transfers(self):
        for tube_barcode, data_list in self.transfer_data.iteritems():
            if not self.tube_map.has_key(tube_barcode):
                tube = Tube(specs=self.tube_specs, barcode=tube_barcode,
                            status=get_item_status_managed(), location=None)
            else:
                tube = self.tube_map[tube_barcode]
            tt = TubeTransfer(tube=tube,
                      source_rack=self.rack_map[data_list[0]],
                      source_position=get_rack_position_from_label(data_list[1]),
                      target_rack=self.rack_map[data_list[2]],
                      target_position=get_rack_position_from_label(data_list[3]))
            self.tube_transfers.append(tt)

    def test_result(self):
        with RdbContextManager() as session:
            self.__continue_setup(session)
            ttw = self.tool.get_result()
            self.assert_is_not_none(ttw)
            session.add(ttw)
            session.commit()
            # worklist attributes
            self.assert_equal(ttw.user, self.executor_user)
            self.assert_is_not_none(ttw.timestamp)
            self.assert_equal(ttw.tube_transfers, self.tube_transfers)
            # racks - collect data
            src_racks = dict()
            trg_racks = dict()
            for tube_barcode, data_list in self.transfer_data.iteritems():
                src_rack_barcode = data_list[0]
                if not src_racks.has_key(src_rack_barcode):
                    src_racks[src_rack_barcode] = []
                src_racks[src_rack_barcode].append(tube_barcode)
                trg_rack_barcode = data_list[2]
                if not trg_racks.has_key(trg_rack_barcode):
                    trg_racks[trg_rack_barcode] = []
                trg_racks[trg_rack_barcode].append(tube_barcode)
            # rack - check data
            for src_rack_barcode, transferred_tubes in src_racks.iteritems():
                src_rack = self.rack_map[src_rack_barcode]
                if self.tube_ini_data.has_key(src_rack_barcode):
                    ini_tubes = len(self.tube_ini_data[src_rack_barcode])
                else:
                    ini_tubes = 0
                exp_num_tubes = ini_tubes - len(transferred_tubes)
                self.assert_equal(len(src_rack.containers), exp_num_tubes)
                for tube in src_rack.containers:
                    self.assert_false(tube.barcode in transferred_tubes)
                    self.assert_is_not_none(tube.location)
            for trg_rack_barcode, transferred_tubes in trg_racks.iteritems():
                trg_rack = self.rack_map[trg_rack_barcode]
                if self.tube_ini_data.has_key(trg_rack_barcode):
                    ini_tubes = len(self.tube_ini_data[trg_rack_barcode])
                else:
                    ini_tubes = 0
                exp_num_tubes = ini_tubes + len(transferred_tubes)
                self.assert_equal(len(trg_rack.containers), exp_num_tubes)
                found_tubes = dict()
                for tube in trg_rack.containers:
                    found_tubes[tube.barcode] = tube.location.position
                    self.assert_is_not_none(tube.location)
                for tube_barcode in transferred_tubes:
                    self.assert_true(tube_barcode in found_tubes)
                    exp_pos = self.transfer_data[tube_barcode][3]
                    found_pos = found_tubes[tube_barcode]
                    self.assert_equal(exp_pos, found_pos.label)

    def test_invalid_input_values(self):
        with RdbContextManager() as session:
            self.__continue_setup(session)
            user = self.executor_user
            self.executor_user = None
            self._test_and_expect_errors('The user must be a User object')
            self.executor_user = user
            self.tube_transfers = dict()
            self._test_and_expect_errors('The tube transfer list must be a ' \
                                         'list')
            self.tube_transfers = ['11']
            self._test_and_expect_errors('The tube transfer must be a ' \
                                         'TubeTransfer object')

    def test_missing_source_tube(self):
        self.tube_ini_data['09999998'] = [('1002', 'A2'), ('1003', 'A3')]
        with RdbContextManager() as session:
            self.__continue_setup(session)
            self._test_and_expect_errors('Some rack positions did not ' \
                    'contain the expected tubes: A1 in rack 09999998 ' \
                    '(expected tube: 1001, no tube found) - A4 in rack ' \
                    '09999998 (expected tube: 1004, no tube found)')

    def test_wrong_source_tube(self):
        self.tube_ini_data['09999998'] = [('1001', 'A2'), ('1002', 'A3'),
                                          ('1003', 'A4'), ('1004', 'A1')]
        with RdbContextManager() as session:
            self.__continue_setup(session)
            self._test_and_expect_errors('Some rack positions did not ' \
                'contain the expected tubes: A1 in rack 09999998 (expected ' \
                'tube: 1001, found: 1004) - A4 in rack 09999998 (expected ' \
                'tube: 1004, found: 1003)')

    def test_target_position_occupied(self):
        self.tube_ini_data['09999977'] = [('1011', 'G2')]
        with RdbContextManager() as session:
            self.__continue_setup(session)
            self._test_and_expect_errors('Some transfer target positions are ' \
                    'not empty: G2 in rack 09999977 (scheduled for: 1008, ' \
                    'tube found: 1011)')

    def test_plate(self):
        plate_specs = self._get_entity(IPlateSpecs)
        plate = plate_specs.create_rack(label='plate',
                                        status=get_item_status_managed())
        plate.barcode = '099999999'
        well1 = plate.containers[0]
        well2 = plate.containers[1]
        tt = TubeTransfer(tube=well1, source_rack=plate,
                          source_position=well1.location.position,
                          target_rack=plate,
                          target_position=well2.location.position)
        self.tube_transfers.append(tt)
        self._test_and_expect_errors('Rack 099999999 is not a tube rack ' \
                                     '(but a Plate)')


class Xl20ExecutorTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.FILE_PATH = 'thelma:tests/tools/worklists/tubehandler/'
        self.valid_file = 'valid_file.txt'
        self.output_file = None
        self.executor_user = get_user('it')
        # tube barcode - src rack barcode, src pos, trg rack barcode, trg pos
        self.transfer_data = {
                '10001' : ['09999998', 'D6', '09999999', 'C4'],
                '10002' : ['09999997', 'D4', '09999999', 'C5']}
        # rack barcode - dict with pos label as key and tueb barcode as values
        self.rack_ini_data = {
                '09999997' : {'A1' : '10003', 'D4' : '10002'},
                '09999998' : {'D4' : '10004', 'D6' : '10001'},
                '09999999' : {'A1' : '10005'}}
        self.rack_res_data = {
                '09999997' : {'A1' : '10003'}, '09999998' : {'D4' : '10004'},
                '09999999' : {'A1' : '10005', 'C4' : '10001', 'C5' : '10002'}}
        # other setup data
        self.racks = dict()

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.FILE_PATH
        del self.valid_file
        del self.output_file
        del self.transfer_data
        del self.rack_ini_data
        del self.rack_res_data
        del self.racks

    def _create_tool(self):
        self.tool = XL20Executor(output_file_stream=self.output_file,
                                 user=self.executor_user)

    def __continue_setup(self, session, file_name=None):
        if file_name is None: file_name = self.valid_file
        self.__read_file(file_name)
        self.__create_racks(session)
        self.__create_tubes(session)
        self._create_tool()

    def __read_file(self, file_name):
        fn = self.FILE_PATH + file_name
        f = resource_filename(*fn.split(':'))
        stream = open(f, 'rb')
        self.output_file = stream

    def __create_racks(self, session):
        rack_barcodes = set()
        for transfer_data in self.transfer_data.values():
            rack_barcodes.add(transfer_data[0])
            rack_barcodes.add(transfer_data[2])
        tube_rack_specs = self._get_entity(ITubeRackSpecs)
        status = get_item_status_managed()
        for barcode in rack_barcodes:
            tube_rack = TubeRack(label=barcode, specs=tube_rack_specs,
                                 status=status, barcode=barcode)
            self.racks[barcode] = tube_rack
            session.add(tube_rack)

    def __create_tubes(self, session):
        tube_specs = self._get_entity(ITubeSpecs)
        status = get_item_status_managed()
        for rack_barcode, tube_map in self.rack_ini_data.iteritems():
            rack = self.racks[rack_barcode]
            for pos_label, tube_barcode in tube_map.iteritems():
                rack_pos = get_rack_position_from_label(pos_label)
                tube = Tube.create_from_rack_and_position(specs=tube_specs,
                                status=status, barcode=tube_barcode,
                                rack=rack, position=rack_pos)
                rack.containers.append(tube)
                session.add(tube)
        session.commit()

    def test_result(self):
        with RdbContextManager() as session:
            self.__continue_setup(session)
            ttw = self.tool.get_result()
            self.assert_is_not_none(ttw)
            session.add(ttw)
            session.commit()
            # check worklist
            expected_timestamp = datetime(2010, 1, 15, 8, 29, 13,
                                          tzinfo=pytz.UTC)
            self.assert_equal(ttw.timestamp, expected_timestamp)
            self.assert_equal(ttw.user, self.executor_user)
            tube_transfers = ttw.tube_transfers
            self.assert_equal(len(tube_transfers), len(self.transfer_data))
            for tt in tube_transfers:
                exp_data = self.transfer_data[tt.tube.barcode]
                self.assert_equal(tt.source_rack.barcode, exp_data[0])
                self.assert_equal(tt.source_position.label, exp_data[1])
                self.assert_equal(tt.target_rack.barcode, exp_data[2])
                self.assert_equal(tt.target_position.label, exp_data[3])
            # check racks
            for rack_barcode, tube_map in self.rack_res_data.iteritems():
                rack = self.racks[rack_barcode]
                self.assert_equal(len(rack.containers), len(tube_map))
                for tube in rack.containers:
                    pos_label = tube.location.position.label
                    self.assert_equal(tube.barcode, tube_map[pos_label])

    def test_one_row(self):
        with RdbContextManager() as session:
            self.__continue_setup(session, 'valid_file_one_row.txt')
            ttw = self.tool.get_result()
            self.assert_is_not_none(ttw)

    def test_invalid_input_values(self):
        with RdbContextManager() as session:
            self.__continue_setup(session)
            user = self.executor_user
            self.executor_user = None
            self._test_and_expect_errors('The user must be a User object')
            self.executor_user = user
            self.output_file = None
            self._test_and_expect_errors('The XL20 output file must be ' \
                                'passed as file, basestring or StringIO object')

    def test_parser_failure(self):
        with RdbContextManager() as session:
            self.__continue_setup(session, 'incomplete_line.txt')
            self._test_and_expect_errors('Error when trying to parser XL20 ' \
                                         'output file.')

    def test_execution_error(self):
        self.rack_ini_data['09999999'] = {'A1' : '10005', 'C4' : '10008'}
        with RdbContextManager() as session:
            self.__continue_setup(session, 'not_feasible.txt')
            self._test_and_expect_errors('Error when trying to update tube ' \
                                         'positions.')

