"""
Tests the classes involved in stock condense worklist generation.

AAB
"""
from everest.testing import RdbContextManager
from everest.testing import check_attributes
from thelma.automation.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.semiconstants import get_positions_for_shape
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.stock.base import get_stock_rack_size
from thelma.automation.tools.stock.condense import CondenseRackQuery
from thelma.automation.tools.stock.condense import RackContainerQuery
from thelma.automation.tools.stock.condense import STOCK_CONDENSE_ROLES
from thelma.automation.tools.stock.condense import StockCondenseRack
from thelma.automation.tools.stock.condense import StockCondenseReportWriter
from thelma.automation.tools.stock.condense import StockCondenser
from thelma.automation.tools.worklists.tubehandler import XL20WorklistWriter
from thelma.models.rack import RACK_TYPES
from thelma.testing import ThelmaModelTestCase
from thelma.tests.tools.tooltestingutils import FileComparisonUtils
from thelma.tests.tools.tooltestingutils import FileCreatorTestCase
from thelma.tests.tools.tooltestingutils import TestingLog


class StockCondenseRackTestCase(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.rack_barcode = '09999999'
        self.tube_count = 4

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.rack_barcode
        del self.tube_count

    def __get_init_data(self):
        return dict(rack_barcode=self.rack_barcode, tube_count=self.tube_count)

    def __create_test_object(self, role=None):
        kw = self.__get_init_data()
        scr = StockCondenseRack(**kw)
        if role is None: return scr
        scr.set_role(role)
        return scr

    def __add_rack_association(self, scr):
        scr.add_rack_association('08888888', 2)
        scr.add_rack_association('08888889', 1)

    def test_init(self):
        kw = self.__get_init_data()
        scr = StockCondenseRack(**kw)
        kw['role'] = None
        kw['associated_racks'] = dict()
        check_attributes(scr, kw)

    def test_set_role(self):
        scr = self.__create_test_object()
        self.assert_is_none(scr.role)
        scr.set_role(STOCK_CONDENSE_ROLES.DONOR)
        self.assert_equal(scr.role, STOCK_CONDENSE_ROLES.DONOR)
        self.assert_raises(AttributeError, scr.set_role,
                           STOCK_CONDENSE_ROLES.RECEIVER)
        set_tuple = (scr, 'role', STOCK_CONDENSE_ROLES.RECEIVER)
        self.assert_raises(AttributeError, setattr, *set_tuple)

    def test_add_rack_association(self):
        scr = self.__create_test_object()
        self.assert_equal(scr.associated_racks, dict())
        ad = dict(rack_barcode='08888888', number_tubes=2)
        self.assert_raises(AttributeError, scr.add_rack_association, **ad)
        scr.set_role(STOCK_CONDENSE_ROLES.DONOR)
        self.assert_equal(scr.associated_racks, dict())
        scr.add_rack_association(**ad)
        self.assert_equal(scr.associated_racks, {'08888888' : 2})
        self.assert_raises(ValueError, scr.add_rack_association, **ad)
        ad2 = dict(rack_barcode='08888889', number_tubes=1)
        scr.add_rack_association(**ad2)
        self.assert_equal(scr.associated_racks,
                          {'08888888' : 2, '08888889' : 1})

    def test_resulting_tube_count(self):
        scr = self.__create_test_object()
        get_tuple = (scr, 'resulting_tube_count')
        self.assert_raises(AttributeError, getattr, *get_tuple)
        # test donor
        scr.set_role(STOCK_CONDENSE_ROLES.DONOR)
        self.assert_equal(scr.resulting_tube_count, self.tube_count)
        self.__add_rack_association(scr)
        self.assert_equal(scr.resulting_tube_count, 1)
        # test receiver
        scr = self.__create_test_object(STOCK_CONDENSE_ROLES.RECEIVER)
        self.assert_equal(scr.resulting_tube_count, self.tube_count)
        self.__add_rack_association(scr)
        self.assert_equal(scr.resulting_tube_count, 7)

    def test_add_tube(self):
        scr = self.__create_test_object()
        self.assert_equal(scr.tubes, dict())
        tube_barcode = '101999'
        rack_pos = get_rack_position_from_label('A1')
        scr.add_tube(rack_pos, tube_barcode)
        self.assert_equal(scr.tubes, {rack_pos : tube_barcode})
        kw = dict(rack_position=rack_pos, tube_barcode=tube_barcode)
        self.assert_raises(ValueError, scr.add_tube, **kw)

    def test_get_positions_without_tube(self):
        scr = self.__create_test_object(role=STOCK_CONDENSE_ROLES.RECEIVER)
        free_positions = scr.get_positions_without_tube()
        stock_rack_size = get_stock_rack_size()
        self.assert_equal(len(free_positions), stock_rack_size)
        positions_96 = get_positions_for_shape(get_96_rack_shape())
        for rack_pos in positions_96:
            self.assert_true(rack_pos in free_positions)
        tube_data = dict(A1='0001', B1='0002', C1='0003', D1='0004')
        for pos_label, tube_barcode in tube_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            scr.add_tube(rack_position=rack_pos, tube_barcode=tube_barcode)
        free_positions = scr.get_positions_without_tube()
        self.assert_equal(len(free_positions), stock_rack_size - len(tube_data))
        for rack_pos in positions_96:
            if tube_data.has_key(rack_pos.label):
                self.assert_false(rack_pos in free_positions)
            else:
                self.assert_true(rack_pos in free_positions)


class CondenseRackQueryTestCase(ThelmaModelTestCase):

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        CondenseRackQuery.shut_down()

    def test_singleton(self):
        query = CondenseRackQuery()
        self.assert_is_not_none(query)
        self.assert_raises(ValueError, CondenseRackQuery)
        CondenseRackQuery.shut_down()
        query = CondenseRackQuery()
        self.assert_is_not_none(query)

    def test_run(self):
        with RdbContextManager() as session:
            query = CondenseRackQuery()
            self.assert_is_none(query.get_query_results())
            query.run(session=session)
            self.assert_not_equal(len(query.get_query_results()), 0)


class RackContainerQueryTestCase(ThelmaModelTestCase):

    def __select_racks(self, session):
        query = 'SELECT DISTINCT r.barcode AS rack_barcode ' \
                'FROM containment rc, rack r ' \
                'WHERE rc.holder_id = r.rack_id ' \
                'AND r.item_status = \'%s\'' \
                'AND r.rack_type = \'%s\' LIMIT 4;' \
                % (ITEM_STATUS_NAMES.MANAGED.upper(), RACK_TYPES.TUBE_RACK)
        result = session.query('rack_barcode').from_statement(query).all()
        rack_barcodes = []
        for record in result: rack_barcodes.append(record[0])
        self.assert_equal(len(rack_barcodes), 4)
        return rack_barcodes

    def __get_donor_racks(self, barcodes):
        # select racks that are not empty
        donor_racks = []
        for rack_barcode in barcodes:
            scr = StockCondenseRack(rack_barcode=rack_barcode, tube_count=2)
            scr.set_role(STOCK_CONDENSE_ROLES.DONOR)
            donor_racks.append(scr)
        self.assert_true(len(donor_racks) > 0)
        return donor_racks

    def __get_receiver_racks(self, barcodes):
        # select racks that are not empty
        receiver_racks = []
        for rack_barcode in barcodes:
            scr = StockCondenseRack(rack_barcode=rack_barcode, tube_count=30)
            scr.set_role(STOCK_CONDENSE_ROLES.RECEIVER)
            receiver_racks.append(scr)
        self.assert_true(len(receiver_racks) > 0)
        return receiver_racks

    def test_run(self):
        with RdbContextManager() as session:
            barcodes = self.__select_racks(session)
            dr = self.__get_donor_racks(barcodes[:2])
            rr = self.__get_receiver_racks(barcodes[2:])
            for scr in dr: self.assert_equal(len(scr.tubes), 0)
            for scr in rr: self.assert_equal(len(scr.tubes), 0)
            query = RackContainerQuery(donor_racks=dr, receiver_racks=rr)
            query.run(session=session)
            for scr in dr: self.assert_not_equal(len(scr.tubes), 0)
            for scr in rr: self.assert_not_equal(len(scr.tubes), 0)


class StockCondenseReportWriterTestCase(FileCreatorTestCase):

    def set_up(self):
        FileCreatorTestCase.set_up(self)
        self.log = TestingLog()
        self.WL_PATH = 'thelma:tests/tools/stock/condense/'
        self.donor_racks = dict()
        self.receiver_racks = dict()
        self.excluded_racks = []
        self.racks_to_empty = None
        # other setup data -
        #: rack barcode, location info
        self.receiver_data = [('09999999', None), ('09999998', 'C28S5'),
                              ('09999997', 'C28S5')]
        self.donor_data = [('09999990', 'C28S7'), ('09999991', 'C28S7')]
        self.association_data = {
            '09999990' : [('09999999', 2), ('09999998', 5), ('09999997', 3)],
            '09999991' : [('09999998', 2)]}

    def tear_down(self):
        FileCreatorTestCase.tear_down(self)
        del self.log
        del self.donor_racks
        del self.excluded_racks
        del self.racks_to_empty

    def _create_tool(self):
        self.tool = StockCondenseReportWriter(log=self.log,
                                        donor_racks=self.donor_racks,
                                        receiver_racks=self.receiver_racks,
                                        excluded_racks=self.excluded_racks,
                                        racks_to_empty=self.racks_to_empty)

    def __continue_setup(self):
        self.__create_receiver_racks()
        self.__create_donor_racks()
        self._create_tool()

    def __create_receiver_racks(self):
        for data_tuple in self.receiver_data:
            rack_barcode = data_tuple[0]
            scr = StockCondenseRack(rack_barcode=rack_barcode, tube_count=80)
            scr.set_role(STOCK_CONDENSE_ROLES.RECEIVER)
            scr.location = data_tuple[1]
            self.receiver_racks[rack_barcode] = scr

    def __create_donor_racks(self):
        for data_tuple in self.donor_data:
            rack_barcode = data_tuple[0]
            ad = self.association_data[rack_barcode]
            tc = 0
            for a_tuple in ad: tc += a_tuple[1]
            scr = StockCondenseRack(rack_barcode=rack_barcode, tube_count=tc)
            scr.set_role(STOCK_CONDENSE_ROLES.DONOR)
            for a_tuple in ad:
                scr.add_rack_association(*a_tuple)
                receiver_barcode = a_tuple[0]
                receiver_rack = self.receiver_racks[receiver_barcode]
                receiver_rack.add_rack_association(rack_barcode, a_tuple[1])
            scr.location = data_tuple[1]
            self.donor_racks[rack_barcode] = scr

    def test_result(self):
        self.__continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_txt_file_stream(tool_stream,
                            'report_no_excl_no_limit.txt', ignore_lines=[0])
        self.excluded_racks = ['09999995', '09999996']
        self.racks_to_empty = 2
        self._create_tool()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_txt_file_stream(tool_stream,
                            'report_with_excl_and_limit.txt', ignore_lines=[0])

    def test_invalid_donation_racks(self):
        self.__continue_setup()
        original_map = self.donor_racks
        self.donor_racks = []
        self._test_and_expect_errors('The donor map must be a dict')
        self.donor_racks = {11 : original_map.values()[0]}
        self._test_and_expect_errors('The donor rack barcode must be a ' \
                                     'basestring')
        self.donor_racks = {original_map.keys()[0] : 11}
        self._test_and_expect_errors('he donor rack must be a ' \
                                     'StockCondenseRack object')

    def test_invalid_receiving_racks(self):
        self.__continue_setup()
        original_map = self.receiver_racks
        self.receiver_racks = []
        self._test_and_expect_errors('The receiver map must be a dict')
        self.receiver_racks = {11 : original_map.values()[0]}
        self._test_and_expect_errors('The receiver rack barcode must be a ' \
                                     'basestring')
        self.receiver_racks = {original_map.keys()[0] : 11}
        self._test_and_expect_errors('he receiver rack must be a ' \
                                     'StockCondenseRack object')

    def test_invalid_excluded_racks(self):
        self.__continue_setup()
        self.excluded_racks = {1 : self.excluded_racks}
        self._test_and_expect_errors('The excluded racks list must be a list')
        self.excluded_racks = [1]
        self._test_and_expect_errors('The excluded rack barcode must be a ' \
                                     'basestring')

    def test_invalid_number_rack_to_empty(self):
        self.__continue_setup()
        self.racks_to_empty = 4.3
        self._test_and_expect_errors('The number of racks to empty must be ' \
                                     'a int')


class StockCondenserTestCase(FileCreatorTestCase):

    def set_up(self):
        FileCreatorTestCase.set_up(self)
        self.racks_to_empty = 5
        self.excluded_racks = None

    def tear_down(self):
        FileCreatorTestCase.tear_down(self)
        CondenseRackQuery.shut_down()
        del self.racks_to_empty
        del self.excluded_racks

    def _create_tool(self):
        self.tool = StockCondenser(racks_to_empty=self.racks_to_empty,
                                   excluded_racks=self.excluded_racks)

    def __check_result(self, check_donor_rack_number=True):
        self._create_tool()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 2)
        wl_content = None
        report_content = None
        for fn in zip_archive.namelist():
            tool_content = zip_archive.read(fn)
            if fn == self.tool.WORKLIST_FILE_NAME:
                wl_content = tool_content
            else:
                report_content = tool_content
        donor_racks, receiver_racks, num_tubes = self.__check_worklist_file(
                                            wl_content, check_donor_rack_number)
        self.__check_report_file(report_content, donor_racks, receiver_racks,
                                 num_tubes)

    def __check_worklist_file(self, file_content, check_donor_rack_number):
        tool_lines = FileComparisonUtils.convert_content(file_content)
        donor_racks = set()
        receiver_racks = set()
        for t_lin in tool_lines:
            line_list = FileComparisonUtils.convert_to_list(t_lin)
            tool = XL20WorklistWriter
            src_rack_barcode = line_list[tool.SOURCE_RACK_INDEX]
            if src_rack_barcode == tool.SOURCE_RACK_HEADER: continue
            donor_racks.add(src_rack_barcode)
            trg_rack_barcode = line_list[tool.DEST_RACK_INDEX]
            receiver_racks.add(trg_rack_barcode)
            if not self.excluded_racks is None:
                self.assert_false(src_rack_barcode in self.excluded_racks)
        if not self.racks_to_empty is None and check_donor_rack_number:
            self.assert_equal(len(donor_racks), self.racks_to_empty)
        return donor_racks, receiver_racks, len(tool_lines) - 1

    def __check_report_file(self, file_content, donor_racks, receiver_racks,
                            num_tubes):
        tool = StockCondenseReportWriter
        rack_to_empty_line = tool.RACK_TO_EMTPTY_LINE % (self.racks_to_empty)
        if self.racks_to_empty is None:
            rack_to_empty_line = tool.RACK_TO_EMTPTY_LINE % (
                                                    tool.NOT_SPECIFIED_MARKER)
        self.assert_true(rack_to_empty_line in file_content)
        exp_num_tubes_line = tool.TUBES_MOVED_LINE % (num_tubes)
        self.assert_true(exp_num_tubes_line in file_content)
        for rack_barcode in donor_racks:
            self.assert_true(rack_barcode in file_content)
        exp_don_count = tool.COUNT_LINE % (len(donor_racks))
        self.assert_true(exp_don_count in file_content)
        for rack_barcode in receiver_racks:
            self.assert_true(rack_barcode in file_content)
        exp_rec_count = tool.COUNT_LINE % (len(receiver_racks))
        self.assert_true(exp_rec_count in file_content)
        if self.excluded_racks is None:
            self.assert_true(tool.NO_EXCLUDED_RACKS_MARKER in file_content)
        else:
            self.assert_false(tool.NO_EXCLUDED_RACKS_MARKER in file_content)
            for rack_barcode in self.excluded_racks:
                self.assert_true(rack_barcode in file_content)

    def test_result_with_limit(self):
        self.__check_result()

    def test_result_without_limit(self):
        self.racks_to_empty = None
        self.__check_result()

    def test_result_excluded_racks(self):
        # get racks for comparison
        self.racks_to_empty = 3
        self._create_tool()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 2)
        wl_content = None
        for fn in zip_archive.namelist():
            tool_content = zip_archive.read(fn)
            if fn == self.tool.WORKLIST_FILE_NAME:
                wl_content = tool_content
        tool_lines = FileComparisonUtils.convert_content(wl_content)
        donor_racks = []
        receiver_racks = []
        for t_lin in tool_lines:
            line_list = FileComparisonUtils.convert_to_list(t_lin)
            tool = XL20WorklistWriter
            src_rack_barcode = line_list[tool.SOURCE_RACK_INDEX]
            if src_rack_barcode == tool.SOURCE_RACK_HEADER: continue
            donor_racks.append(src_rack_barcode)
            trg_rack_barcode = line_list[tool.DEST_RACK_INDEX]
            receiver_racks.append(trg_rack_barcode)
        self.excluded_racks = donor_racks + receiver_racks
        # rerun
        self.racks_to_empty = 10
        self.__check_result()

    def test_not_enough_racks(self):
        self.racks_to_empty = 200
        self.__check_result(check_donor_rack_number=False)
        self._check_warning_messages('Unable to empty the requested number ' \
                'of racks (200) because there are not enough racks available')

    def test_invalid_rack_number(self):
        self.racks_to_empty = 4.5
        self._test_and_expect_errors('The number of racks to empty must be a ' \
                                     'int')
        self.racks_to_empty = 0
        self._test_and_expect_errors('The number of racks to empty must be ' \
                                     'positive')

    def test_invalid_excluded_racks(self):
        self.excluded_racks = dict()
        self._test_and_expect_errors('The excluded racks must be passed as ' \
                                     'list or set')
        self.excluded_racks = [8]
        self._test_and_expect_errors('The excluded rack barcode must be ' \
                                     'a basestring')
