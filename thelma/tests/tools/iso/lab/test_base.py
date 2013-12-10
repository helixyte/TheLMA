"""
Base classes, functions and constants involved in lab ISO processing tasks.

AAB
"""
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.iso.base import IsoRackContainer
from thelma.automation.tools.iso.lab.base import FinalLabIsoLayout
from thelma.automation.tools.iso.lab.base import FinalLabIsoLayoutConverter
from thelma.automation.tools.iso.lab.base import FinalLabIsoParameters
from thelma.automation.tools.iso.lab.base import FinalLabIsoPosition
from thelma.automation.tools.iso.lab.base import LABELS
from thelma.automation.tools.iso.lab.base import LabIsoLayout
from thelma.automation.tools.iso.lab.base import LabIsoLayoutConverter
from thelma.automation.tools.iso.lab.base import LabIsoParameters
from thelma.automation.tools.iso.lab.base import LabIsoPosition
from thelma.automation.tools.iso.lab.base import LabIsoPrepLayout
from thelma.automation.tools.iso.lab.base import LabIsoPrepLayoutConverter
from thelma.automation.tools.iso.lab.base import LabIsoPrepParameters
from thelma.automation.tools.iso.lab.base import LabIsoPrepPosition
from thelma.automation.tools.iso.lab.base import create_instructions_writer
from thelma.automation.tools.iso.lab.base import get_stock_takeout_volume
from thelma.automation.tools.stock.tubepicking import TubeCandidate
from thelma.automation.utils.layouts import EMPTY_POSITION_TYPE
from thelma.automation.utils.layouts import FIXED_POSITION_TYPE
from thelma.automation.utils.layouts import LIBRARY_POSITION_TYPE
from thelma.automation.utils.layouts import MOCK_POSITION_TYPE
from thelma.automation.utils.layouts import MoleculeDesignPoolParameters
from thelma.automation.utils.layouts import TransferTarget
from thelma.models.tagging import Tag
from thelma.tests.tools.iso.lab.utils import LAB_ISO_TEST_CASES
from thelma.tests.tools.iso.lab.utils import LabIsoTestCase2
from thelma.tests.tools.tooltestingutils import FileCreatorTestCase
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase
from thelma.tests.tools.utils.utils import ConverterTestCase
from thelma.tests.tools.utils.utils import MoleculeDesignPoolBaseTestCase


class LabIsoFunctionsTestCase(ToolsAndUtilsTestCase):

    def test_get_stock_takeout_volume(self):
        stock_conc = 50000
        final_conc = 10000
        final_vol = 10
        self.assert_equal(2,
                get_stock_takeout_volume(stock_conc, final_vol, final_conc))


class LabIsoLabelsTestCase(ToolsAndUtilsTestCase):

    def test_create_iso_label(self):
        self.assert_equal(LABELS.create_iso_label(1234, 2), '1234_iso_02')
        self.assert_equal(LABELS.create_iso_label(1234, 2, True),
                          '1234_iso_02_copy')

    def test_parse_iso_label(self):
        exp_values = {'ticket_number' : 1234, 'entity_num' : 2}
        self.assert_equal(LABELS.parse_iso_label('1234_iso_02'), exp_values)
        self.assert_equal(LABELS.parse_iso_label('1234_iso_02_copy'),
                          exp_values)

    def test_get_new_iso_number(self):
        lir = self._create_lab_iso_request()
        self.assert_equal(len(lir.isos), 0)
        self.assert_equal(LABELS.get_new_iso_number(lir), 1)
        self._create_lab_iso(iso_request=lir, label='1234_iso_02')
        self.assert_equal(len(lir.isos), 1)
        self.assert_equal(LABELS.get_new_iso_number(lir), 3)

    def test_create_job_label(self):
        self.assert_equal(LABELS.create_job_label(1234, 2), '1234_job_02')

    def test_get_new_job_label(self):
        lir = self._create_lab_iso_request()
        self.assert_equal(len(lir.iso_jobs), 0)
        self.assert_equal(LABELS.get_new_job_number(lir), 1)
        iso = self._create_lab_iso(iso_request=lir, label='1234_iso_02')
        self._create_iso_job(isos=[iso], label='1234_job_02')
        self.assert_equal(len(lir.iso_jobs), 1)
        self.assert_equal(LABELS.get_new_job_number(lir), 3)

    def test_create_rack_label(self):
        job_label = '1234_job_02'
        rack_marker = 'jp#2'
        self.assert_equal(LABELS.create_rack_label(rack_marker, job_label),
                          '1234_job_02_jp#2')

    def test_parse_rack_label(self):
        exp_values = dict(rack_role='jp', rack_num=2, rack_marker='jp#2',
                          ticket_number=1234, entity_num=2)
        self.assert_equal(LABELS.parse_rack_label('1234_job_02_jp#2'),
                          exp_values)

    def test_create_worklist_label(self):
        ticket_number = 1234
        worklist_num = 4
        target_rack_marker = 'a#2'
        source_rack_marker = 'jp#1'
        self.assert_equal(LABELS.create_worklist_label(ticket_number,
                   worklist_num, target_rack_marker, source_rack_marker),
                  '1234_4_jp#1_to_a#2')
        self.assert_equal(LABELS.create_worklist_label(ticket_number,
                   worklist_num, target_rack_marker), '1234_4_a#2_buffer')

    def test_parse_worklist_label(self):
        exp_values = dict(ticket_number=1234, worklist_number=4,
                          target_rack_marker='a#2')
        self.assert_equal(LABELS.parse_worklist_label('1234_4_a#2_buffer'),
                          exp_values)
        exp_values['source_rack_marker'] = 'jp#1'
        self.assert_equal(LABELS.parse_worklist_label('1234_4_jp#1_to_a#2'),
                          exp_values)

    def test_create_final_plate_label(self):
        lir = self._create_lab_iso_request(label='test_lir')
        iso = self._create_lab_iso(iso_request=lir, label='1234_iso_04')
        self.assert_equal(LABELS.create_final_plate_label(iso), 'test_lir_4')
        self.assert_equal(LABELS.create_final_plate_label(iso, 2),
                          'test_lir_4_2')


class _LabIsoClassesBaseTestCase(MoleculeDesignPoolBaseTestCase):

    POS_CLS = LabIsoPosition
    LAYOUT_CLS = LabIsoLayout

    POOL_TAGS = {
        'a1' : Tag('molecule_design_pool', 'molecule_design_pool_id', '205200'),
        'a2' : Tag('molecule_design_pool', 'molecule_design_pool_id', '205200'),
        'b1' : Tag('molecule_design_pool', 'molecule_design_pool_id',
                   '1056000'),
        'c1' : Tag('molecule_design_pool', 'molecule_design_pool_id', 'mock'),
        'd1' : Tag('molecule_design_pool', 'molecule_design_pool_id',
                   'library')}

    TYPE_TAGS = {
            'a1' : Tag('molecule_design_pool', 'position_type', 'fixed'),
            'a2' : Tag('molecule_design_pool', 'position_type', 'fixed'),
            'b1' : Tag('molecule_design_pool', 'position_type',
                             'floating'),
            'c1' : Tag('molecule_design_pool', 'position_type', 'mock'),
            'd1' : Tag('molecule_design_pool', 'position_type', 'library'),
            'e1' : Tag('molecule_design_pool', 'position_type', 'empty')}

    _TRANSFER_TARGET_TAGS = {'a1' : Tag('sample_transfer', 'transfer_targets',
                                        'A2:1')}
    _CONC_TAGS = {'a1' : Tag('iso_plate', 'concentration', '50'),
                  'a2' : Tag('iso_plate', 'concentration', '25'),
                  'b1' : Tag('iso_plate', 'concentration', '50'),
                  'd1' : Tag('iso_plate', 'concentration', '50')}
    _VOL_TAGS = {'a1' : Tag('iso_plate', 'volume', '5'),
                 'a2' : Tag('iso_plate', 'volume', '2'),
                 'b1' : Tag('iso_plate', 'volume', '5'),
                 'c1' : Tag('iso_plate', 'volume', '2'),
                 'd1' : Tag('iso_plate', 'volume', '5')}
    _STOCK_TUBE_TAGS = {'a1' : Tag('iso_plate', 'stock_tube_barcode', '1001'),
                        'b1' : Tag('iso_plate', 'stock_tube_barcode', '1002')}
    _RACK_BARCODE_TAGS = {
                'a1' : Tag('iso_plate', 'stock_rack_barcode', '09999999'),
                'b1' : Tag('iso_plate', 'stock_rack_barcode', '09999999')}
    _RACK_MARKER_TAGS = {
                'a1' : Tag('iso_plate', 'stock_rack_marker', 's#2'),
                'b1' : Tag('iso_plate', 'stock_rack_marker', 's#2')}
    _SECTOR_INDEX_TAGS = {'a2' : Tag('iso_plate', 'sector_index', '2')}

    def set_up(self):
        MoleculeDesignPoolBaseTestCase.set_up(self)
        # pos_label - pool, pos_type, conc, vol, transfer targets, stock tube
        # barcode, stock rack barcode, sector index, stock rack marker
        self.tts = {1 : TransferTarget('a2', 1)}
        self.pos_data = dict(
            a1=[self._get_pool(205200), 'fixed', 50, 5, [self.tts[1]],
                '1001', '09999999', None, 's#2'],
            a2=[self._get_pool(205200), 'fixed', 25, 2, [], None, None, 2,
                None],
            b1=[self._get_pool(1056000), 'floating', 50, 5, [], '1002',
                '09999999', None, 's#2'],
            c1=['mock', 'mock', None, 2, [], None, None, None, None],
            d1=['library', 'library', 50, 5, [], None, None, None, None],
            e1=[None, 'empty', None, None, [], None, None, None, None, None])

    def tear_down(self):
        MoleculeDesignPoolBaseTestCase.tear_down(self)
        del self.tts

    def _get_init_data(self, pos_label):
        pos_data = self.pos_data[pos_label]
        kw = dict(rack_position=get_rack_position_from_label(pos_label),
              molecule_design_pool=pos_data[0], position_type=pos_data[1],
              concentration=pos_data[2], volume=pos_data[3],
              transfer_targets=pos_data[4], stock_tube_barcode=pos_data[5],
              stock_rack_barcode=pos_data[6], sector_index=pos_data[7],
              stock_rack_marker=pos_data[8])
        return kw

    def _get_tags(self, pos_label):
        tags = set([self.TYPE_TAGS[pos_label]])
        self._add_optional_tag(tags, self.POOL_TAGS, pos_label)
        self._add_optional_tag(tags, self._CONC_TAGS, pos_label)
        self._add_optional_tag(tags, self._VOL_TAGS, pos_label)
        self._add_optional_tag(tags, self._TRANSFER_TARGET_TAGS, pos_label)
        self._add_optional_tag(tags, self._STOCK_TUBE_TAGS, pos_label)
        self._add_optional_tag(tags, self._RACK_BARCODE_TAGS, pos_label)
        self._add_optional_tag(tags, self._RACK_MARKER_TAGS, pos_label)
        self._add_optional_tag(tags, self._SECTOR_INDEX_TAGS, pos_label)
        return tags

    def _test_create_missing_floating_copy(self, add_equal_attrs=None):
        lip = self._get_position('b1')
        lip.sector_index = 3
        lip.transfer_targets = self.tts[1]
        copy1 = lip.create_missing_floating_copy()
        self.assert_is_not_none(copy1)
        self.assert_equal(copy1.molecule_design_pool,
                          self.POS_CLS.MISSING_FLOATING)
        self.assert_true(copy1.is_missing_floating)
        equal_attrs = ['volume', 'concentration', 'sector_index',
                       'rack_position', 'stock_rack_marker']
        if not add_equal_attrs is None:
            equal_attrs += add_equal_attrs
        for attr_name in equal_attrs:
            self.assert_equal(getattr(lip, attr_name),
                              getattr(copy1, attr_name))
        self.assert_equal(len(copy1.transfer_targets), 0)

    def _test_create_completed_copy(self, add_equal_attrs=None):
        tc = TubeCandidate(pool_id=330001, rack_barcode='0999997',
                           rack_position=get_rack_position_from_label('g8'),
                           tube_barcode='1009', concentration=50000, volume=20)
        tc.set_pool(self._get_pool(330001))
        equal_attrs = ['volume', 'concentration', 'sector_index',
                       'rack_position', 'transfer_targets']
        if add_equal_attrs is not None:
            equal_attrs += add_equal_attrs
        # floating positions
        lip1 = self._get_position('b1')
        lip1.molecule_design_pool = self._get_pool(205200)
        lip1.stock_rack_marker = None
        lip1.stock_tube_barcode = self.POS_CLS.TEMP_STOCK_DATA
        lip1.stock_rack_barcode = self.POS_CLS.TEMP_STOCK_DATA
        self._expect_error(AttributeError, lip1.create_completed_copy,
                'The pool for this floating position is already set (205200)!',
                **dict(tube_candidate=tc))
        lip1.molecule_design_pool = 'md_1'
        self.assert_is_none(lip1.stock_rack_marker)
        copy1 = lip1.create_completed_copy(tc)
        self.assert_is_not_none(copy1)
        self.assert_true(copy1.is_floating)
        self.assert_equal(copy1.stock_tube_barcode, tc.tube_barcode)
        self.assert_equal(copy1.stock_rack_barcode, tc.rack_barcode)
        self.assert_is_none(copy1.stock_rack_marker)
        self.assert_equal(copy1.molecule_design_pool.id, # pylint: disable=E1103
                          330001)
        for attr_name in equal_attrs:
            self.assert_equal(getattr(lip1, attr_name),
                              getattr(copy1, attr_name))
        copy2 = lip1.create_completed_copy(None)
        self.assert_is_not_none(copy2)
        self.assert_true(copy2.is_floating)
        self.assert_true(copy2.is_missing_floating)
        lip1.stock_rack_barcode = None
        lip1.stock_rack_marker = None
        copy3 = lip1.create_completed_copy(None)
        self.assert_is_not_none(copy3)
        self.assert_equal(copy1.molecule_design_pool.id, # pylint: disable=E1103
                          330001)
        # fixed positions
        lip2 = self._get_position('a1')
        lip2.stock_tube_barcode = self.POS_CLS.TEMP_STOCK_DATA
        lip2.stock_rack_barcode = self.POS_CLS.TEMP_STOCK_DATA
        lip2.stock_rack_marker = None
        self._expect_error(ValueError, lip2.create_completed_copy,
                'The pools of the position (205200) and the tube candidate ' \
                '(330001) do not match!', **dict(tube_candidate=tc))
        lip2.molecule_design_pool = self._get_pool(tc.pool_id)
        copy4 = lip2.create_completed_copy(tc)
        self.assert_is_not_none(copy4)
        self.assert_equal(copy4.stock_tube_barcode, tc.tube_barcode)
        self.assert_equal(copy4.stock_rack_barcode, tc.rack_barcode)
        self.assert_is_none(copy4.stock_rack_marker)
        for attr_name in equal_attrs:
            self.assert_equal(getattr(lip2, attr_name),
                              getattr(copy4, attr_name))
        self._expect_error(ValueError, lip2.create_completed_copy,
                   'The tube candidate for a fixed position must not be None!',
                   **dict(tube_candidate=None))
        lip2.stock_tube_barcode = None
        lip2.stock_rack_barcode = None
        self._expect_error(AttributeError, copy4.create_completed_copy,
                   'There is already a stock tube barcode set for this ' \
                   'position (1009)!', **dict(tube_candidate=tc))
        copy5 = lip2.create_completed_copy(tc)
        self.assert_is_not_none(copy5)
        self.assert_is_none(copy5.stock_tube_barcode)
        self.assert_is_none(copy5.stock_rack_barcode)
        # other position types
        for pos_label in ('c1', 'd1', 'e1'):
            if not self.pos_data.has_key(pos_label): continue
            lip = self._get_position(pos_label)
            self._expect_error(ValueError, lip.create_completed_copy,
                    'Completed copies can only be created for fixed and ' \
                    'floating positions', **dict(tube_candidate=tc))


class LabIsoPositionTestCase(_LabIsoClassesBaseTestCase):

    def test_init(self):
        self._test_position_init()
        attrs = self._get_init_data('b1')
        ori_pos_type = attrs['position_type']
        attrs['position_type'] = None
        self._expect_error(ValueError, self.POS_CLS,
                'The position type for a LabIsoPosition position must not ' \
                'be None!', **attrs)
        attrs['position_type'] = ori_pos_type
        attrs['molecule_design_pool'] = self._get_pool(205200)
        lip1 = self.POS_CLS(**attrs) # would cause error in superclass
        self.assert_is_not_none(lip1)
        attrs['molecule_design_pool'] = self.POS_CLS.MISSING_FLOATING
        lip2 = self.POS_CLS(**attrs) # would cause error in superclass
        self.assert_is_not_none(lip2)

    def test_fixed_and_floating_init_failures(self):
        attr_sets = [self._get_init_data('a1'), self._get_init_data('b1')]
        for attrs in attr_sets:
            ori_pool = attrs['molecule_design_pool']
            attrs['molecule_design_pool'] = 'mock'
            self._expect_error(ValueError, self.POS_CLS,
                    'The position type for this pool (mock) does not match ' \
                    'the passed position type', **attrs)
            attrs['molecule_design_pool'] = ori_pool
            attrs['concentration'] = -1
            self._expect_error(ValueError, self.POS_CLS,
                    'The concentration must be a positive number ' \
                    '(obtained: -1).', **attrs)
            attrs['concentration'] = None
            self._expect_error(ValueError, self.POS_CLS,
                    'The concentration for %s lab ISO positions must not be ' \
                    'None!' % (attrs['position_type']), **attrs)
            attrs['concentration'] = 50
            attrs['volume'] = -1
            self._expect_error(ValueError, self.POS_CLS,
                    'The volume must a positive number (obtained: -1)', **attrs)
            attrs['volume'] = None
            self._expect_error(ValueError, self.POS_CLS,
                    'The volume for %s lab ISO positions must not be None!' \
                    % (attrs['position_type']), **attrs)
            attrs['volume'] = 1
            attrs['stock_tube_barcode'] = 1001
            self._expect_error(TypeError, self.POS_CLS,
                    'The stock tube barcode must be a string of at least 2 ' \
                    'characters length (obtained: 1001)', **attrs)
            attrs['stock_tube_barcode'] = 'a'
            self._expect_error(TypeError, self.POS_CLS,
                    'The stock tube barcode must be a string of at least 2 ' \
                    'characters length (obtained: a)', **attrs)
            attrs['stock_tube_barcode'] = '1001'
            attrs['stock_rack_barcode'] = 9999999
            self._expect_error(TypeError, self.POS_CLS,
                    'The stock rack barcode must be a string of at least 2 ' \
                    'characters length (obtained: 9999999)', **attrs)
            attrs['stock_rack_barcode'] = '1'
            self._expect_error(TypeError, self.POS_CLS,
                    'The stock rack barcode must be a string of at least 2 ' \
                    'characters length (obtained: 1)', **attrs)
            attrs['stock_rack_barcode'] = '09999999'
            attrs['stock_rack_marker'] = 123
            self._expect_error(TypeError, self.POS_CLS,
                    'The stock rack marker must be a string (obtained: 123)',
                    **attrs)
            attrs['stock_rack_marker'] = 's'
            attrs['sector_index'] = 1.5
            self._expect_error(ValueError, self.POS_CLS,
                    'The sector index must be a non-negative integer ' \
                    '(obtained: 1.5)', **attrs)
            attrs['sector_index'] = -1
            self._expect_error(ValueError, self.POS_CLS,
                    'The sector index must be a non-negative integer ' \
                    '(obtained: -1)', **attrs)

    def test_mock_init_failures(self):
        attrs = self._get_init_data('c1')
        attrs['molecule_design_pool'] = 'md_1'
        self._expect_error(ValueError, self.POS_CLS,
                'The position type for this pool (floating) does not match ' \
                'the passed position type (mock)!', **attrs)
        attrs['molecule_design_pool'] = MOCK_POSITION_TYPE
        attrs['concentration'] = 1
        self._expect_error(ValueError, self.POS_CLS,
                'The concentration for mock lab ISO positions must be None!',
                **attrs)
        attrs['concentration'] = None
        attrs['volume'] = -1
        self._expect_error(ValueError, self.POS_CLS,
                'The volume must a positive number (obtained: -1)', **attrs)
        attrs['volume'] = None
        self._expect_error(ValueError, self.POS_CLS,
                'The volume for mock lab ISO positions must not be None!',
                **attrs)
        attrs['volume'] = 1
        attrs['stock_tube_barcode'] = '1001'
        self._expect_error(ValueError, self.POS_CLS,
                'The stock tube barcode for mock lab ISO positions must be ' \
                'None!', **attrs)
        attrs['stock_tube_barcode'] = None
        attrs['stock_rack_barcode'] = '09999999'
        self._expect_error(ValueError, self.POS_CLS,
                'The stock rack barcode for mock lab ISO positions must be ' \
                'None!', **attrs)
        attrs['stock_rack_barcode'] = None
        attrs['stock_rack_marker'] = 's#2'
        self._expect_error(ValueError, self.POS_CLS,
                'The stock rack marker for mock lab ISO positions must be ' \
                'None!', **attrs)
        attrs['stock_rack_marker'] = None
        attrs['sector_index'] = 1.5
        self._expect_error(ValueError, self.POS_CLS,
                'The sector index must be a non-negative integer ' \
                '(obtained: 1.5)', **attrs)
        attrs['sector_index'] = -1
        self._expect_error(ValueError, self.POS_CLS,
                'The sector index must be a non-negative integer ' \
                '(obtained: -1)', **attrs)

    def test_library_init_failures(self):
        attrs = self._get_init_data('d1')
        ori_pool = attrs['molecule_design_pool']
        attrs['molecule_design_pool'] = 'mock'
        self._expect_error(ValueError, self.POS_CLS,
                'The position type for this pool (mock) does not match the ' \
                'passed position type (library)', **attrs)
        attrs['molecule_design_pool'] = ori_pool
        attrs['concentration'] = -1
        self._expect_error(ValueError, self.POS_CLS,
                'The concentration must be a positive number (obtained: -1)',
                **attrs)
        attrs['concentration'] = None
        self._expect_error(ValueError, self.POS_CLS,
                'The concentration for library lab ISO positions must not ' \
                'be None!', **attrs)
        attrs['concentration'] = 50
        attrs['volume'] = -1
        self._expect_error(ValueError, self.POS_CLS,
                'The volume must a positive number (obtained: -1)', **attrs)
        attrs['volume'] = None
        self._expect_error(ValueError, self.POS_CLS,
                'The volume for library lab ISO positions must not be None!',
                **attrs)
        attrs['volume'] = 1
        attrs['stock_tube_barcode'] = '1001'
        self._expect_error(ValueError, self.POS_CLS,
                'The stock tube barcode for library lab ISO positions must ' \
                'be None!', **attrs)
        attrs['stock_tube_barcode'] = None
        attrs['stock_rack_barcode'] = '09999999'
        self._expect_error(ValueError, self.POS_CLS,
                'The stock rack barcode for library lab ISO positions must ' \
                'be None!', **attrs)
        attrs['stock_rack_barcode'] = None
        attrs['stock_rack_marker'] = 's#2'
        self._expect_error(ValueError, self.POS_CLS,
                'The stock rack marker for library lab ISO positions must ' \
                'be None!', **attrs)
        attrs['stock_rack_marker'] = None
        attrs['sector_index'] = 1.5
        self._expect_error(ValueError, self.POS_CLS,
                'The sector index must be a non-negative integer ' \
                '(obtained: 1.5)', **attrs)
        attrs['sector_index'] = -1
        self._expect_error(ValueError, self.POS_CLS,
                'The sector index must be a non-negative integer ' \
                '(obtained: -1)', **attrs)

    def test_empty_init_failure(self):
        attrs = self._get_init_data('e1')
        attrs['molecule_design_pool'] = 'md_1'
        self._expect_error(ValueError, self.POS_CLS,
                'The position type for this pool (floating) does not match ' \
                'the passed position type (empty)', **attrs)
        attrs['molecule_design_pool'] = None
        attrs['concentration'] = 1
        self._expect_error(ValueError, self.POS_CLS,
                'The concentration for empty lab ISO positions must be None!',
                **attrs)
        attrs['concentration'] = None
        attrs['volume'] = 1
        self._expect_error(ValueError, self.POS_CLS,
                'The volume for empty lab ISO positions must be None!', **attrs)
        attrs['volume'] = None
        attrs['stock_tube_barcode'] = '1001'
        self._expect_error(ValueError, self.POS_CLS,
                'The stock tube barcode for empty lab ISO positions must be ' \
                'None!', **attrs)
        attrs['stock_tube_barcode'] = None
        attrs['stock_rack_barcode'] = '09999999'
        self._expect_error(ValueError, self.POS_CLS,
                'The stock rack barcode for empty lab ISO positions must be ' \
                'None!', **attrs)
        attrs['stock_rack_barcode'] = None
        attrs['stock_rack_marker'] = 's#2'
        self._expect_error(ValueError, self.POS_CLS,
                'The stock rack marker for empty lab ISO positions must be ' \
                'None!', **attrs)
        attrs['stock_rack_marker'] = None
        attrs['sector_index'] = 1
        self._expect_error(ValueError, self.POS_CLS,
                'The sector index for empty lab ISO positions must be None!',
                **attrs)

    def test_equality(self):
        self._test_position_equality(
                 dict(concentration=7, volume=7),
                 dict(stock_tube_barcode='1003', stock_rack_barcode='09999998',
                      stock_rack_marker='s#4', sector_index=3,
                      transfer_targets=[TransferTarget('g8', 1)]))

    def test_get_tags(self):
        self._test_position_get_tag_set()

    def test_mock_position_factory(self):
        attrs = self._get_init_data('c1')
        lip = self.POS_CLS(**attrs)
        fac_pos = self.POS_CLS.create_mock_position(
                rack_position=attrs['rack_position'], volume=attrs['volume'])
        self.assert_equal(lip, fac_pos)

    def test_is_missing_floating(self):
        lip1 = self._get_position('b1')
        self.assert_false(lip1.is_missing_floating)
        lip1.molecule_design_pool = self.POS_CLS.MISSING_FLOATING
        self.assert_true(lip1.is_missing_floating)
        lip2 = self._get_position('a1')
        self.assert_false(lip2.is_missing_floating)
        lip2.molecule_design_pool = self.POS_CLS.MISSING_FLOATING
        self.assert_false(lip2.is_missing_floating)

    def test_inactivation(self):
        lip1 = self._get_position('b1')
        self.assert_false(lip1.is_inactivated)
        self.assert_is_not_none(lip1.stock_tube_barcode)
        self.assert_is_not_none(lip1.stock_rack_barcode)
        self.assert_is_not_none(lip1.stock_rack_marker)
        lip1.inactivate()
        self.assert_true(lip1.is_inactivated)
        self.assert_is_none(lip1.stock_tube_barcode)
        self.assert_is_none(lip1.stock_rack_barcode)
        self.assert_is_not_none(lip1.stock_rack_marker)
        lip2 = self._get_position('a1')
        self.assert_false(lip2.is_inactivated)
        self._expect_error(AttributeError, lip2.inactivate,
                           'fixed positions must not be inactivated!')

    def test_is_starting_well(self):
        exp_values = dict(a1=True, a2=False, b1=True, c1=False, d1=False)
        for pos_label, exp_value in exp_values.iteritems():
            lip = self._get_position(pos_label)
            self.assert_equal(lip.is_starting_well, exp_value)
            if exp_value:
                lip.stock_rack_marker = None
                self.assert_false(lip.is_starting_well)

    def test_get_stock_takeout_volume(self):
        lip = self._get_position('a1')
        lip.concentration = 10000
        lip.volume = 10
        self.assert_equal(lip.get_stock_takeout_volume(), 2)
        lip.stock_rack_marker = None
        self.assert_is_none(lip.get_stock_takeout_volume())

    def test_create_missing_floating_copy(self):
        self._test_create_missing_floating_copy()

    def test_create_completed_copy(self):
        self._test_create_completed_copy()

    def test_as_transfer_target(self):
        lip = self._get_position('a1')
        lip.concentration = 10000
        lip.volume = 10
        self.assert_equal(lip.get_stock_takeout_volume(), 2)
        rack_marker = 'a#2'
        exp_tt = TransferTarget('a1', 2, rack_marker)
        tt = lip.as_transfer_target(rack_marker)
        self.assert_equal(tt, exp_tt)
        self.assert_equal(tt.target_rack_marker, exp_tt.target_rack_marker)
        self.assert_equal(tt.transfer_volume, exp_tt.transfer_volume)


class LabIsoLayoutTestCase(_LabIsoClassesBaseTestCase):

    def _get_layout_pos(self, pos_label, layout):
        rack_pos = get_rack_position_from_label(pos_label)
        return layout.get_working_position(rack_pos)

    def test_init(self):
        self._test_layout_init()

    def test_sorted_floating_positions(self):
        self.pos_data['a1'][0] = 'md_2'
        self.pos_data['a1'][1] = 'floating'
        self.pos_data['a2'][0] = 'md_2'
        self.pos_data['a2'][1] = 'floating'
        layout = self._create_test_layout()
        lip_a1 = self._get_layout_pos('a1', layout)
        lip_a2 = self._get_layout_pos('a2', layout)
        lip_b1 = self._get_layout_pos('b1', layout)
        exp_positions = [lip_b1, lip_a1, lip_a2]
        self.assert_equal(exp_positions, layout.get_sorted_floating_positions())

    def test_get_starting_wells(self):
        layout = self._create_test_layout()
        rack_pos_a1 = get_rack_position_from_label('a1')
        rack_pos_b1 = get_rack_position_from_label('b1')
        exp_positions = {rack_pos_a1 : layout.get_working_position(rack_pos_a1),
                         rack_pos_b1 : layout.get_working_position(rack_pos_b1)}
        self.assert_equal(exp_positions, layout.get_starting_wells())

    def test_get_sector_map(self):
        self.pos_data['a1'][7] = 1
        self.pos_data['b1'][7] = 1
        layout = self._create_test_layout()
        lip_a1 = self._get_layout_pos('a1', layout)
        lip_a2 = self._get_layout_pos('a2', layout)
        lip_b1 = self._get_layout_pos('b1', layout)
        exp_map = {1 : [lip_a1, lip_b1], 2 : [lip_a2]}
        sector_map = layout.get_sector_map()
        self.assert_equal(len(sector_map), len(exp_map))
        for sector_index, exp_pos in exp_map.iteritems():
            positions = sector_map[sector_index]
            self.assert_equal(sorted(exp_pos), sorted(positions))
        lip_b1.sector_index = None
        exp_map = {1 : [lip_a1], 2 : [lip_a2],
                   self.LAYOUT_CLS.NO_SECTOR_MARKER : [lip_b1]}
        self.assert_equal(exp_map, layout.get_sector_map())

    def test_create_rack_layout(self):
        layout = self._create_test_layout()
        rl = layout.create_rack_layout()
        self.assert_is_not_none(rl)
        lip1 = self._get_layout_pos('a2', layout)
        lip1.stock_tube_barcode = self.POS_CLS.TEMP_STOCK_DATA
        rl = layout.create_rack_layout()
        # lip1 is not a starting well
        self.assert_is_not_none(rl)
        lip2 = self._get_layout_pos('a1', layout)
        lip2.stock_tube_barcode = self.POS_CLS.TEMP_STOCK_DATA
        self._expect_error(AttributeError, layout.create_rack_layout,
                'There are still starting wells without stock data in the ' \
                'layout!')


class _LabIsoLayoutBaseConverterTestCase(ConverterTestCase,
                                         _LabIsoClassesBaseTestCase):

    PARAMETER_SET = LabIsoParameters
    POS_CLS = LabIsoPosition
    LAYOUT_CLS = LabIsoLayout
    CONVERTER_CLS = LabIsoLayoutConverter

    _POS_TYPE_INDEX = 0
    _POOL_INDEX = 1
    _VOL_INDEX = 2
    _CONC_INDEX = 3
    _TRANSFER_TARGET_INDEX = 4
    _STOCK_TUBE_INDEX = 5
    _RACK_BARCODE_INDEX = 6
    _RACK_MARKER_INDEX = 7
    _SECTOR_INDEX_INDEX = 8

    def set_up(self):
        ConverterTestCase.set_up(self)
        self.pos_set_data = {1 : ['a1'], 2 : ['a2', 'a3'], 3 : ['b1'],
                         4 : ['c1'], 5 : ['d1'], 6 : ['e1'], 7 : ['a1', 'b1']}
        self.tag_key_map = {1 : 'a1', 2 : 'a2', 3 : 'b1', 4 : 'c1', 5 : 'd1',
                            6 : 'e1'}
        self.tag_data = {7 : [Tag('some', 'other', 'tag')]}
        for k in self.tag_key_map.keys(): self.tag_data[k] = []
        for k, pos_label in self.tag_key_map.iteritems():
            self._insert_tag_data_tag(k, pos_label, self.TYPE_TAGS,
                                      self._POS_TYPE_INDEX)
            self._insert_tag_data_tag(k, pos_label, self.POOL_TAGS,
                                      self._POOL_INDEX)
            self._insert_tag_data_tag(k, pos_label, self._VOL_TAGS,
                                      self._VOL_INDEX)
            self._insert_tag_data_tag(k, pos_label, self._CONC_TAGS,
                                      self._CONC_INDEX)
            self._insert_tag_data_tag(k, pos_label, self._TRANSFER_TARGET_TAGS,
                                      self._TRANSFER_TARGET_INDEX)
            self._insert_tag_data_tag(k, pos_label, self._STOCK_TUBE_TAGS,
                                      self._STOCK_TUBE_INDEX)
            self._insert_tag_data_tag(k, pos_label, self._RACK_BARCODE_TAGS,
                                      self._RACK_BARCODE_INDEX)
            self._insert_tag_data_tag(k, pos_label, self._RACK_MARKER_TAGS,
                                      self._RACK_MARKER_INDEX)
            self._insert_tag_data_tag(k, pos_label, self._SECTOR_INDEX_TAGS,
                                      self._SECTOR_INDEX_INDEX)
        del self.tag_key_map[k] # empty positions are not converted

    def _get_all_positions(self):
        positions = []
        for k in self.tag_key_map.keys():
            positions.extend(self.pos_set_data[k])
        return set(positions)

    def _get_all_tags(self):
        tags = set()
        for k in self.tag_key_map.keys():
            exp_tags = self.tag_data[k]
            for tag in exp_tags: tags.add(tag)
        tags = filter(None, tags) # pylint: disable=W0141
        return tags

    def _test_position_for_tag(self, layout):
        tag = self._CONC_TAGS['a2']
        exp_positions = ['a2', 'a3']
        pos_set = layout.get_positions_for_tag(tag)
        self._compare_pos_sets(exp_positions, pos_set)

    def _test_tag_for_position(self, layout):
        rack_pos = get_rack_position_from_label('a2')
        exp_tags = self.tag_data[2]
        exp_tags = filter(None, exp_tags) # pylint: disable=W0141
        tag_set = layout.get_tags_for_position(rack_pos)
        self._compare_tag_sets(exp_tags, tag_set)


class LabIsoLayoutConverterTestCase(_LabIsoLayoutBaseConverterTestCase):

    def test_result(self):
        self._test_result()

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_invalid_concentration(self):
        self.tag_data[2][self._CONC_INDEX] = Tag('not', 'the', 'concentration')
        self._test_invalid_rack_layout('The concentration must be a positive ' \
            'number (or *None* for mock positions). The following positions ' \
            'in the layout have invalid concentrations: A2 (None), A3 (None).')

    def test_invalid_concentration_mock(self):
        self.tag_data[4].insert(self._CONC_INDEX, Tag(self.PARAMETER_SET.DOMAIN,
                                    self.PARAMETER_SET.CONCENTRATION, 4))
        self._test_invalid_rack_layout('The concentration must be a positive ' \
            'number (or *None* for mock positions). The following positions ' \
            'in the layout have invalid concentrations: C1 (4).')

    def test_invalid_volume(self):
        self.tag_data[2][self._VOL_INDEX] = Tag('not', 'the', 'volume')
        self._test_invalid_rack_layout('The volume must be a positive ' \
            'number. The following rack positions have invalid volumes: ' \
            'A2 (None), A3 (None).')

    def test_invalid_sector_index(self):
        self.tag_data[2].insert(self._SECTOR_INDEX_INDEX, Tag(
            self.PARAMETER_SET.DOMAIN, self.PARAMETER_SET.SECTOR_INDEX, '2.1'))
        self._test_invalid_rack_layout('The sector index must be a ' \
            'non-negative integer or None. The following positions in the ' \
            'layout have invalid sector indices: A2 (2.1), A3 (2.1).')

    def test_invalid_tube_barcode(self):
        self.tag_data[2].insert(self._STOCK_TUBE_INDEX, Tag(
            self.PARAMETER_SET.DOMAIN, self.PARAMETER_SET.STOCK_TUBE_BARCODE,
            '1'))
        self._test_invalid_rack_layout('The stock tube barcode must be at ' \
            'least 2 characters long if it is specified. The following ' \
            'positions ins the layout have invalid stock tube barcodes: ' \
            'A2 (1), A3 (1).')

    def test_invalid_rack_barcode(self):
        self.tag_data[2].insert(self._RACK_BARCODE_INDEX, Tag(
            self.PARAMETER_SET.DOMAIN, self.PARAMETER_SET.STOCK_RACK_BARCODE,
            '2'))
        self._test_invalid_rack_layout('The stock rack barcode must be at ' \
           'least 2 characters long if it is specified. The following ' \
           'positions ins the layout have invalid stock rack barcodes: ' \
           'A2 (2), A3 (2).')

    def test_transfer_data_not_allowed(self):
        self.tag_data[5].insert(self._TRANSFER_TARGET_INDEX, \
                            self.tag_data[1][self._TRANSFER_TARGET_INDEX])
        del self.tag_data[1][self._TRANSFER_TARGET_INDEX]
        self._test_invalid_rack_layout('Library lab ISO position must not ' \
            'have transfer targets. The following library positions violate ' \
            'this rule: D1.')

    def test_invalid_floating(self):
        self.tag_data[3][self._POOL_INDEX] = Tag(
            MoleculeDesignPoolParameters.DOMAIN,
            self.PARAMETER_SET.MOLECULE_DESIGN_POOL, 'md_1')
        self._test_invalid_rack_layout('Pools for floating positions for lab ' \
            'ISO plate must either be a missing placeholder ' \
            '("missing_floating") or a pool ID. The following floating ' \
            'position pools are invalid: md_1.')

    def test_mock_and_tube_data(self):
        self.tag_data[4].insert(self._STOCK_TUBE_INDEX,
                                self._STOCK_TUBE_TAGS['a1'])
        self._test_invalid_rack_layout('Mock and library ISO plate positions ' \
            'must not have stock tube or rack data. The following positions ' \
            'violate this rule: C1.')

    def test_library_and_tube_data(self):
        self.tag_data[5].insert(self._RACK_MARKER_INDEX,
                                self._RACK_MARKER_TAGS['a1'])
        self._test_invalid_rack_layout('Mock and library ISO plate positions ' \
            'must not have stock tube or rack data. The following positions ' \
            'violate this rule: D1.')


class _FinalLabIsoClassesBaseTestCase(_LabIsoClassesBaseTestCase):

    POS_CLS = FinalLabIsoPosition
    LAYOUT_CLS = FinalLabIsoLayout

    _FROM_JOB_TAGS = {'a1' : Tag('final_iso_plate', 'from_job', 'True'),
                      'a2' : Tag('final_iso_plate', 'from_job', 'True')}

    def set_up(self):
        _LabIsoClassesBaseTestCase.set_up(self)
        for pos_label, pos_data in self.pos_data.iteritems():
            from_job = False
            if pos_label in ('a1', 'a2'): from_job = True
            pos_data.append(from_job)

    def _get_init_data(self, pos_label):
        kw = _LabIsoClassesBaseTestCase._get_init_data(self, pos_label)
        kw['from_job'] = self.pos_data[pos_label][-1]
        return kw

    def _get_tags(self, pos_label):
        tags = _LabIsoClassesBaseTestCase._get_tags(self, pos_label)
        self._add_optional_tag(tags, self._FROM_JOB_TAGS, pos_label)
        return tags


class FinalLabIsoPositionTestCase(_FinalLabIsoClassesBaseTestCase):

    def test_init(self):
        self._test_position_init()
        for pos_label in self.pos_data.keys():
            attrs = self._get_init_data(pos_label)
            if attrs['position_type'] == FIXED_POSITION_TYPE: continue
            attrs['from_job'] = True
            self._expect_error(ValueError, self.POS_CLS,
                    'Only fixed final lab ISO positions can be provided from ' \
                    'a job. This one is a %s type.' % (attrs['position_type']),
                    **attrs)

    def test_equality(self):
        self._test_position_equality(
                 dict(concentration=7, volume=7),
                 dict(stock_tube_barcode='1003', stock_rack_barcode='09999998',
                      stock_rack_marker='s#4', sector_index=3,
                      transfer_targets=[TransferTarget('g8', 1)],
                      from_job=False))

    def test_get_tag_set(self):
        self._test_position_get_tag_set()

    def test_from_iso_plate_position(self):
        for pos_label in self.pos_data.keys():
            attrs = self._get_init_data(pos_label)
            flip = self._get_position(pos_label, attrs)
            from_job = attrs['from_job']
            del attrs['from_job']
            lip = LabIsoPosition(**attrs)
            fac_pos = self.POS_CLS.from_iso_plate_position(from_job, lip)
            self.assert_equal(flip, fac_pos)
            attr_names = ('from_job', 'transfer_targets', 'stock_tube_barcode',
                          'stock_rack_barcode', 'stock_rack_marker')
            # attributes not covered by position equality check
            for attr_name in attr_names:
                self.assert_equal(getattr(fac_pos, attr_name),
                                  getattr(flip, attr_name))

    def test_create_library_position(self):
        exp_pos = self._get_position('d1')
        fac_pos = self.POS_CLS.create_library_position(
                        rack_position=exp_pos.rack_position,
                        concentration=exp_pos.concentration,
                        volume=exp_pos.volume)
        self.assert_equal(exp_pos, fac_pos)

    def test_create_missing_floating_copy(self):
        self._test_create_missing_floating_copy(['from_job'])

    def test_create_completed_copy(self):
        self._test_create_completed_copy(['from_job'])


class FinalLabIsoLayoutTestCase(_FinalLabIsoClassesBaseTestCase):

    def test_init(self):
        self._test_layout_init()


class FinalLabIsoLayoutConverterTestCase(_LabIsoLayoutBaseConverterTestCase,
                                         _FinalLabIsoClassesBaseTestCase):

    PARAMETER_SET = FinalLabIsoParameters
    POS_CLS = FinalLabIsoPosition
    LAYOUT_CLS = FinalLabIsoLayout
    CONVERTER_CLS = FinalLabIsoLayoutConverter

    __FROM_JOB_INDEX = 9

    def set_up(self):
        _LabIsoLayoutBaseConverterTestCase.set_up(self)
        for k, pos_label in self.tag_key_map.iteritems():
            self._insert_tag_data_tag(k, pos_label, self._FROM_JOB_TAGS,
                                      self.__FROM_JOB_INDEX)

    def test_result(self):
        self._test_result()

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_invalid_from_job(self):
        self.tag_data[2][self.__FROM_JOB_INDEX] = Tag(
                self.PARAMETER_SET.DOMAIN, self.PARAMETER_SET.FROM_JOB, '1')
        self._test_invalid_rack_layout('The "from job" flag must be a ' \
            'boolean. The values for some positions are invalid. Details: ' \
            'A2 (1), A3 (1)')

    def test_invalid_position_type_for_from_job(self):
        self.tag_data[4].insert(self.__FROM_JOB_INDEX,
                                self._FROM_JOB_TAGS['a1'])
        self._test_invalid_rack_layout('Only fixed position might originate ' \
            'from a job. The following non-fixed positions violate this ' \
            'rule: C1.')


class _LabIsoPrepClassesBaseTestCase(_LabIsoClassesBaseTestCase):

    POS_CLS = LabIsoPrepPosition
    LAYOUT_CLS = LabIsoPrepLayout

    _EXTERNAL_TARGET_TAGS = {
            'a1' : Tag('iso_prep_plate', 'external_targets',
                       'A2:1-A5:1:a-A6:1:a'), # one is also normal target
            'a2' : Tag('iso_prep_plate', 'external_targets', 'A7:1:int'),
            'b1' : Tag('iso_prep_plate', 'external_targets', 'B5:2:a')}

    def set_up(self):
        _LabIsoClassesBaseTestCase.set_up(self)
        del self.pos_data['c1'] # mock
        del self.pos_data['d1'] # library
        self.ext_tts = {1 : TransferTarget('a5', 1, 'a'),
                        2 : TransferTarget('a6', 1, 'a'),
                        3 : TransferTarget('a7', 1, 'int'),
                        4 : TransferTarget('b5', 2, 'a')}
        self.pos_data['a1'].append([self.ext_tts[1], self.ext_tts[2],
                                    self.tts[1]])
        self.pos_data['a2'].append([self.ext_tts[3]]) # fixed
        self.pos_data['b1'].append([self.ext_tts[4]]) # floating
        self.pos_data['e1'].append([]) # empty

    def tear_down(self):
        _LabIsoClassesBaseTestCase.tear_down(self)
        del self.ext_tts

    def _get_init_data(self, pos_label):
        kw = _LabIsoClassesBaseTestCase._get_init_data(self, pos_label)
        kw['external_targets'] = self.pos_data[pos_label][-1]
        return kw

    def _get_tags(self, pos_label):
        tags = _LabIsoClassesBaseTestCase._get_tags(self, pos_label)
        self._add_optional_tag(tags, self._EXTERNAL_TARGET_TAGS, pos_label)
        return tags


class LabIsoPrepPositionTestCase(_LabIsoPrepClassesBaseTestCase):

    def test_init(self):
        self._test_position_init()
        for pos_label in self.pos_data.keys():
            attrs = self._get_init_data(pos_label)
            if attrs['position_type'] == EMPTY_POSITION_TYPE:
                attrs['external_targets'] = [self.ext_tts[1]]
                self._expect_error(ValueError, self.POS_CLS,
                    'Empty positions must not have external plate targets!',
                    **attrs)
            else:
                attrs['transfer_targets'] = None
                attrs['external_targets'] = None
                self._expect_error(ValueError, self.POS_CLS,
                    'A LabIsoPrepPosition must have at least on transfer ' \
                    'target or external target!', **attrs)
        attrs = self._get_init_data('a2')
        attrs['molecule_design_pool'] = LIBRARY_POSITION_TYPE
        attrs['position_type'] = LIBRARY_POSITION_TYPE
        self._expect_error(ValueError, self.POS_CLS,
                'The position type "library" is not allowed for this ' \
                'parameter set (LabIsoPrepParameters)!', **attrs)
        attrs['molecule_design_pool'] = MOCK_POSITION_TYPE
        attrs['position_type'] = MOCK_POSITION_TYPE
        attrs['concentration'] = None
        self._expect_error(ValueError, self.POS_CLS,
                'The position type "mock" is not allowed for this parameter ' \
                'set (LabIsoPrepParameters)!', **attrs)

    def test_equality(self):
        self._test_position_equality(
                 dict(concentration=7, volume=7),
                 dict(stock_tube_barcode='1003', stock_rack_barcode='09999998',
                      stock_rack_marker='s#4', sector_index=3,
                      transfer_targets=[TransferTarget('g8', 1)],
                      external_targets=[TransferTarget('g8', 1)]))

    def test_get_tag_set(self):
        self._test_position_get_tag_set()

    def test_create_missing_floating_copy(self):
        self._test_create_missing_floating_copy(['external_targets'])

    def test_create_completed_copy(self):
        self._test_create_completed_copy(['external_targets'])


class LabIsoPrepLayoutTestCase(_LabIsoPrepClassesBaseTestCase):

    def test_init(self):
        self._test_layout_init()


class LabIsoPrepLayoutConverterTestCase(_LabIsoLayoutBaseConverterTestCase,
                                        _LabIsoPrepClassesBaseTestCase):


    PARAMETER_SET = LabIsoPrepParameters
    POS_CLS = LabIsoPrepPosition
    LAYOUT_CLS = LabIsoPrepLayout
    CONVERTER_CLS = LabIsoPrepLayoutConverter

    __EXTERNAL_TARGETS_INDEX = 9

    def set_up(self):
        _LabIsoLayoutBaseConverterTestCase.set_up(self)
        del self.tag_key_map[4] # mock
        del self.tag_key_map[5] # library
        self.pos_set_data[2] = self.pos_set_data[2][:1]
        del self.pos_set_data[4] # mock
        del self.pos_set_data[5] # library
        for k, pos_label in self.tag_key_map.iteritems():
            self._insert_tag_data_tag(k, pos_label, self._EXTERNAL_TARGET_TAGS,
                                      self.__EXTERNAL_TARGETS_INDEX)

    def test_result(self):
        self._test_result()

    def _test_position_for_tag(self, layout):
        tag = self._CONC_TAGS['a2']
        exp_positions = ['a2']
        pos_set = layout.get_positions_for_tag(tag)
        self._compare_pos_sets(exp_positions, pos_set)

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_duplicate_external_targets(self):
        self.pos_set_data[2].append('f7')
        self._test_invalid_rack_layout('There are duplicate target ' \
                        'positions: parameter "external targets": "int-A7"!')

class _InstructionWriterTestCase(LabIsoTestCase2, FileCreatorTestCase):

    def set_up(self):
        LabIsoTestCase2.set_up(self)
        self.log = TestingLog()
        self.rack_containers = []
        self.WL_PATH = LAB_ISO_TEST_CASES.INSTRUCTIONS_FILE_PATH

    def tear_down(self):
        LabIsoTestCase2.tear_down(self)
        del self.rack_containers

    def _create_tool(self):
        self.tool = create_instructions_writer(log=self.log, entity=self.entity,
                        iso_request=self.iso_request,
                        rack_containers=self.rack_containers)

    def _continue_setup(self, file_name=None):
        LabIsoTestCase2._continue_setup(self, file_name=file_name)
        self._generate_stock_racks(self.entity)
        self.__create_rack_containers()
        self._create_tool()

    def __create_rack_containers(self):
        for label, rack in self.rack_generator.label_map.iteritems():
            value_parts = LABELS.parse_rack_label(label)
            role = value_parts[LABELS.MARKER_RACK_ROLE]
            if not self.FOR_JOB and not self.entity.label in label:
                continue
            elif role == LABELS.ROLE_PREPARATION_JOB and not self.FOR_JOB:
                continue
            rack_marker = value_parts[LABELS.MARKER_RACK_MARKER]
            rack_container = IsoRackContainer(rack=rack, role=role,
                                rack_marker=rack_marker, label=label)
            self.rack_containers.append(rack_container)
        for iso_label, iso in self.isos.iteritems():
            plate_labels = LAB_ISO_TEST_CASES.get_final_plate_labels(self.case)\
                                                                    [iso_label]
            is_single_plate = (len(plate_labels) == 1)
            for lib_plate in iso.library_plates:
                rack = lib_plate.rack
                if is_single_plate:
                    rack_marker = LABELS.ROLE_FINAL
                else:
                    ind = plate_labels.index(rack.label)
                    rack_marker = LABELS.create_rack_marker(LABELS.ROLE_FINAL,
                                                        rack_number=(ind + 1))
                rack_container = IsoRackContainer(rack=rack,
                                rack_marker=rack_marker, label=rack.label,
                                role=LABELS.ROLE_FINAL)
                self.rack_containers.append(rack_container)

    def _test_and_expect_success(self, case_name):
        self._load_iso_request(case_name)

    def __check_result(self):
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        fn = LAB_ISO_TEST_CASES.get_instruction_file(self.case, self.FOR_JOB)
        self._compare_txt_file_stream(tool_stream, fn)

    def _test_invalid_input_values(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)
        if self.FOR_JOB:
            alt_entity = self.isos[self._USED_ISO_LABEL]
            exp_msg = 'The entity must be a IsoJob object (obtained: LabIso)'
        else:
            alt_entity = self.iso_job
            exp_msg = 'The entity must be a LabIso object (obtained: IsoJob)'
        self._create_tool()
        self.tool.entity = alt_entity
        res = self.tool.get_result()
        self.assert_is_none(res)
        self._check_error_messages(exp_msg)
        ori_ir = self.iso_request
        self.iso_request = self.iso_request.label
        self._test_and_expect_errors('The ISO request must be a ' \
                                     'LabIsoRequest object (obtained: str)')
        self.iso_request = ori_ir
        ori_containers = self.rack_containers
        self.rack_containers = dict()
        self._test_and_expect_errors('The rack container list must be a ' \
                                     'list object (obtained: dict)')
        self.rack_containers = [1, ori_containers[0]]
        self._test_and_expect_errors('The rack container must be a ' \
                                     'IsoRackContainer object (obtained: int)')


class LabIsoInstructionsWriterTestCase(_InstructionWriterTestCase):

    FOR_JOB = False

    def test_case_order_only(self):
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)

    def test_case_no_job_direct(self):
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_NO_JOB_DIRECT)

    def test_case_no_job_1_prep(self):
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

    def test_case_assocation_job_last(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_JOB_LAST)

    def test_case_association_several_conc(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SEVERAL_CONC)

    def test_case_library_simple(self):
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_LIBRARY_SIMPLE)

    def test_case_library_2_aliquots(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_LIBRARY_2_ALIQUOTS)

    def test_invalid_input_values(self):
        self._test_invalid_input_values()


class LabIsoJobInstructionsWriterTestCase(_InstructionWriterTestCase):

    FOR_JOB = True

    def test_case_order_only(self):
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)

    def test_case_no_job_direct(self):
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_NO_JOB_DIRECT)

    def test_case_no_job_1_prep(self):
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

    def test_case_assocation_job_last(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_JOB_LAST)

    def test_case_association_several_conc(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SEVERAL_CONC)

    def test_case_library_simple(self):
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_LIBRARY_SIMPLE)

    def test_case_library_2_aliquots(self):
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_LIBRARY_2_ALIQUOTS)

    def test_invalid_input_values(self):
        self._test_invalid_input_values()
