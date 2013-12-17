"""
Tests for base classes, functions and constants for ISO processing
(type-independent).

AAB
"""
from everest.repositories.rdb.testing import RdbContextManager
from everest.repositories.rdb.testing import check_attributes
from thelma.automation.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.semiconstants import get_384_rack_shape
from thelma.automation.semiconstants import get_item_status_managed
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.iso.base import IsoRackContainer
from thelma.automation.tools.iso.base import StockRackLayout
from thelma.automation.tools.iso.base import StockRackLayoutConverter
from thelma.automation.tools.iso.base import StockRackParameters
from thelma.automation.tools.iso.base import StockRackPosition
from thelma.automation.tools.iso.base import StockRackVerifier
from thelma.automation.tools.iso.base import _ISO_LABELS_BASE
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.utils.layouts import FIXED_POSITION_TYPE
from thelma.automation.utils.layouts import MOCK_POSITION_TYPE
from thelma.automation.utils.layouts import MoleculeDesignPoolParameters
from thelma.automation.utils.layouts import TransferTarget
from thelma.interfaces import IPlate
from thelma.interfaces import ITubeRack
from thelma.models.liquidtransfer import PlannedSampleTransfer
from thelma.models.rack import RACK_TYPES
from thelma.models.tagging import Tag
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase
from thelma.tests.tools.utils.utils import ConverterTestCase
from thelma.tests.tools.utils.utils import MoleculeDesignPoolBaseTestCase
from thelma.tests.tools.utils.utils import VerifierTestCase
from thelma.automation.semiconstants import RACK_SPECS_NAMES


class _LABELS_DUMMY(_ISO_LABELS_BASE):
    pass

class IsoLabelTestCase(ToolsAndUtilsTestCase):

    def test_create_rack_marker(self):
        rack_role = 'starter'
        self.assert_equal(_LABELS_DUMMY.create_rack_marker(rack_role),
                          'starter')
        self.assert_equal(_LABELS_DUMMY.create_rack_marker(rack_role, 4),
                          'starter#4')

    def test_parse_rack_marker(self):
        marker1 = 'starter'
        exp_values1 = {'rack_role' : 'starter'}
        self.assert_equal(_LABELS_DUMMY.parse_rack_marker(marker1), exp_values1)
        marker2 = 'starter#4'
        exp_values2 = {'rack_role' : 'starter', 'rack_num' : 4}
        self.assert_equal(_LABELS_DUMMY.parse_rack_marker(marker2), exp_values2)


class IsoRackContainerTestCase(ToolsAndUtilsTestCase):

    def test_init(self):
        label1 = 'iso1_starter#4'
        plate = self._create_plate(label=label1)
        marker = 'final#5'
        exp_attrs = dict(rack=plate, label=label1, role='final',
                         rack_marker=marker)
        irc1 = IsoRackContainer(rack=plate, rack_marker=marker)
        check_attributes(irc1, exp_attrs)
        label2 = 'iso5_starter#1'
        irc2 = IsoRackContainer(rack=plate, rack_marker=marker, label=label2)
        exp_attrs['label'] = label2
        check_attributes(irc2, exp_attrs)
        irc3 = IsoRackContainer(rack=plate, rack_marker=marker, label=label2,
                                role='starter')
        exp_attrs['role'] = 'starter'
        check_attributes(irc3, exp_attrs)

    def test_equality(self):
        rack1 = self._get_entity(IPlate)
        rack2 = self._get_entity(ITubeRack)
        marker = 'starter#4'
        label = 'test_label'
        role = 'final'
        irc1 = IsoRackContainer(rack=rack1, rack_marker=marker, label=label,
                                role=role)
        irc2 = IsoRackContainer(rack=rack1, rack_marker=marker, label=label,
                                role=role)
        irc3 = IsoRackContainer(rack=rack2, rack_marker=marker, label=label,
                                role=role)
        irc4 = IsoRackContainer(rack=rack1, rack_marker='other', label=label,
                                role=role)
        irc5 = IsoRackContainer(rack=rack1, rack_marker=marker, label='other',
                                role=role)
        irc6 = IsoRackContainer(rack=rack1, rack_marker=marker, label=label,
                                role='other')
        self.assert_equal(irc1, irc2)
        self.assert_not_equal(irc1, irc3)
        self.assert_equal(irc1, irc4)
        self.assert_equal(irc1, irc5)
        self.assert_equal(irc1, irc6)
        self.assert_not_equal(irc1, rack1)


class _StockRackClassesBaseTestCase(MoleculeDesignPoolBaseTestCase):

    POS_CLS = StockRackPosition
    LAYOUT_CLS = StockRackLayout

    POOL_TAGS = {
        'a1' : Tag('molecule_design_pool', 'molecule_design_pool_id',
                   '205200'), # siRNA 1
        'b1' : Tag('molecule_design_pool', 'molecule_design_pool_id',
                   '1056000'), # siRNA 3
        'c1' : Tag('molecule_design_pool', 'molecule_design_pool_id',
                   '330001')} # miRNA
    TYPE_TAGS = {
            'fixed' : Tag('molecule_design_pool', 'position_type', 'fixed')}

    POS_TYPES = (FIXED_POSITION_TYPE,)

    _TUBE_BARCODE_TAGS = {'a1' : Tag('stock_rack', 'tube_barcode', '1001'),
                          'b1' : Tag('stock_rack', 'tube_barcode', '1004'),
                          'c1' : Tag('stock_rack', 'tube_barcode', '1009')}

    _TRANSFER_TARGET_TAGS = {
            'a1' : Tag('sample_transfer', 'transfer_targets',
                       'A2:1:final#1-A2:2.5:int'),
            'b1' : Tag('sample_transfer', 'transfer_targets',
                       'B2:1:final#2-B2:2.5:int'),
            'c1' : Tag('sample_transfer', 'transfer_targets',
                       'C2:1:final#1-C2:1:final#2')}

    def set_up(self):
        MoleculeDesignPoolBaseTestCase.set_up(self)
        self.tts = {1 : TransferTarget('a2', 2.5, 'int'),
                    2 : TransferTarget('a2', 1, 'final#1'),
                    3 : TransferTarget('b2', 2.5, 'int'),
                    4 : TransferTarget('b2', 1, 'final#2'),
                    5 : TransferTarget('c2', 1, 'final#1'),
                    6 : TransferTarget('c2', 1, 'final#2')}
        # pos label - pool, tube barcode, transfer targets
        self.pos_data = dict(
            a1=[self._get_pool(205200), '1001', [self.tts[1], self.tts[2]]],
            b1=[self._get_pool(1056000), '1004', [self.tts[3], self.tts[4]]],
            c1=[self._get_pool(330001), '1009', [self.tts[5], self.tts[6]]])

    def _get_init_data(self, pos_label):
        pos_data = self.pos_data[pos_label]
        kw = dict(rack_position=get_rack_position_from_label(pos_label),
                  molecule_design_pool=pos_data[0],
                  tube_barcode=pos_data[1],
                  transfer_targets=pos_data[2])
        return kw

    def _get_tags(self, pos_label):
        tags = set()
        self._add_optional_tag(tags, self.POOL_TAGS, pos_label)
        self._add_optional_tag(tags, self._TUBE_BARCODE_TAGS, pos_label)
        self._add_optional_tag(tags, self._TRANSFER_TARGET_TAGS, pos_label)
        return tags

    def _init_layout(self, shape=None):
        return self.LAYOUT_CLS()

    def _test_layout_init(self):
        srl = self._init_layout(None)
        self.assert_is_not_none(srl)
        self.assert_equal(srl.shape.name, RACK_SHAPE_NAMES.SHAPE_96)
        self.assert_equal(len(srl), 0)


class StockRackPositionTestCase(_StockRackClassesBaseTestCase):

    def test_init(self):
        self._test_position_init()
        a1_data = self._get_init_data('a1')
        ori_pool = a1_data['molecule_design_pool']
        a1_data['molecule_design_pool'] = MOCK_POSITION_TYPE
        self._expect_error(ValueError, self.POS_CLS,
                'The position type "mock" is not allowed for this parameter ' \
                'set (StockRackParameters)!',
                **a1_data)
        a1_data['molecule_design_pool'] = ori_pool
        a1_data['tube_barcode'] = 1001
        self._expect_error(TypeError, self.POS_CLS,
                'The tube barcode must be a string (obtained: int).', **a1_data)
        a1_data['tube_barcode'] = '1001'
        a1_data['transfer_targets'] = None
        self._expect_error(ValueError, self.POS_CLS,
                'A StockRackPosition must have at least one transfer target!',
                **a1_data)

    def test_equality(self):
        tts = [TransferTarget('g8', 1)]
        self._test_position_equality(dict(tube_barcode='1000'),
                                     dict(transfer_targets=tts))

    def test_get_planned_sample_transfers(self):
        sp = self._get_position('a1')
        a1_pos = sp.rack_position
        a2_pos = get_rack_position_from_label('a2')
        exp_transfers1 = [PlannedSampleTransfer.get_entity(
                          volume=(2.5 / VOLUME_CONVERSION_FACTOR),
                          source_position=a1_pos, target_position=a2_pos)]
        self.assert_equal(sorted(exp_transfers1),
                          sorted(sp.get_planned_sample_transfers('int')))
        exp_transfers2 = [PlannedSampleTransfer.get_entity(
                          volume=(1 / VOLUME_CONVERSION_FACTOR),
                          source_position=a1_pos, target_position=a2_pos)]
        self.assert_equal(sorted(exp_transfers2),
                          sorted(sp.get_planned_sample_transfers('final#1')))
        self.assert_equal(sp.get_planned_sample_transfers('final#2'), [])

    def test_get_required_stock_volume(self):
        sr1 = self._get_position('a1')
        self.assert_equal(sr1.get_required_stock_volume(), 8.5)
        sr3 = self._get_position('c1')
        self.assert_equal(sr3.get_required_stock_volume(), 7)

    def test_get_tag_set(self):
        self._test_position_get_tag_set()


class StockRackLayoutTestCase(_StockRackClassesBaseTestCase):

    def test_init(self):
        self._test_layout_init()

    def test_get_duplicate_molecule_design_pools(self):
        srl1 = self._create_test_layout()
        self.assert_equal(srl1.get_duplicate_molecule_design_pools(), [])
        self.pos_data = dict(
            a1=[self.pool_map[205200], '1001', [self.tts[1]]],
            b1=[self.pool_map[1056000], '1004', [self.tts[3]]],
            c1=[self.pool_map[330001], '1009', [self.tts[5]]],
            d1=[self.pool_map[205200], '1002', [self.tts[2]]],
            e1=[self.pool_map[1056000], '1005', [self.tts[4]]])
        srl2 = self._create_test_layout()
        self.assert_equal(sorted(srl2.get_duplicate_molecule_design_pools()),
                          sorted([self.pool_map[205200],
                                  self.pool_map[1056000]]))


class _StockRackLayoutConverterBaseTestCase(ConverterTestCase,
                                            _StockRackClassesBaseTestCase):

    PARAMETER_SET = StockRackParameters
    POS_CLS = StockRackPosition
    LAYOUT_CLS = StockRackLayout
    CONVERTER_CLS = StockRackLayoutConverter

    _POOL_INDEX = 0
    _TUBE_BARCODE_INDEX = 1
    _TRANSFER_TARGET_INDEX = 2

    def set_up(self):
        ConverterTestCase.set_up(self)
        self.pos_set_data = {1 : ['a1'], 2 : ['b1'], 3 : ['c1'],
                             4 : ['a1', 'b1', 'c1']}
        self.tag_key_map = {1 : 'a1', 2 : 'b1', 3 : 'c1'}
        self.tag_data = {4 : [Tag('some', 'more', 'data')]}
        for k, pos_label in self.tag_key_map.iteritems():
            self.tag_data[k] = []
            self._insert_tag_data_tag(k, pos_label, self.POOL_TAGS,
                                      self._POOL_INDEX)
            self._insert_tag_data_tag(k, pos_label, self._TUBE_BARCODE_TAGS,
                                      self._TUBE_BARCODE_INDEX)
            self._insert_tag_data_tag(k, pos_label, self._TRANSFER_TARGET_TAGS,
                                      self._TRANSFER_TARGET_INDEX)

    def tear_down_add_on_attributes(self):
        _StockRackClassesBaseTestCase.tear_down_as_add_on(self)

    def _get_all_tags(self):
        tags = []
        for i in range(3):
            tags.extend(self.tag_data[i + 1])
        return set(tags)

    def _test_tag_for_position(self, layout):
        rack_pos = get_rack_position_from_label('a1')
        exp_tags = self.tag_data[1]
        tag_set = layout.get_tags_for_position(rack_pos)
        self._compare_tag_sets(exp_tags, tag_set)

    def _test_position_for_tag(self, layout):
        tag1 = self.tag_data[1][0]
        exp_positions = self.pos_set_data[1]
        pos_set = layout.get_positions_for_tag(tag1)
        self._compare_pos_sets(exp_positions, pos_set)
        tag2 = self.tag_data[4][0]
        self.assert_equal(layout.get_positions_for_tag(tag2), set())


class StockRackLayoutConverterTestCase(_StockRackLayoutConverterBaseTestCase):

    def test_result(self):
        self._test_result()

    def test_missing_tube_barcode(self):
        self.tag_data[2][1] = Tag(self.PARAMETER_SET.DOMAIN,
                                  self.PARAMETER_SET.TUBE_BARCODE, '1')
        self._continue_setup()
        self._test_and_expect_errors('The following positions to not have ' \
                                     'tube barcode: B1')

    def test_non_fixed_position(self):
        self.tag_data[2][self._POOL_INDEX] = Tag(
                MoleculeDesignPoolParameters.DOMAIN,
                self.PARAMETER_SET.MOLECULE_DESIGN_POOL, MOCK_POSITION_TYPE)
        self._continue_setup()
        self._test_and_expect_errors('Unknown or unsupported position types ' \
                 'for the following pool IDs: mock. Supported position ' \
                 'types: empty, fixed')

    def test_duplicate_pools(self):
        self.tag_data[2][self._POOL_INDEX] = self.tag_data[1][0]
        self._continue_setup()
        self._test_and_expect_errors('There are duplicate molecule design ' \
                'pools in the stock rack layout. This is a programming ' \
                'error, please contact the IT department.')


class StockRackVerifierTestCase(VerifierTestCase):

    LAYOUT_CLS = StockRackLayout
    POSITION_CLS = StockRackPosition

    def set_up(self):
        VerifierTestCase.set_up(self)
        self.stock_rack = None
        self.stock_rack_layout = None
        self.plate_type = RACK_TYPES.TUBE_RACK
        # pos_label - pool ID, tube barcode
        self.position_data = dict(a1=[205200, '1001'],
                                  b1=[1056000, '1002'])
        self.rack_specs = RACK_SPECS_NAMES.from_name(
                                                RACK_SPECS_NAMES.STOCK_RACK)

    def tear_down(self):
        VerifierTestCase.tear_down(self)
        del self.stock_rack
        del self.stock_rack_layout

    def _create_tool(self):
        self.tool = StockRackVerifier(log=self.log,
                                      stock_rack=self.stock_rack,
                                      stock_rack_layout=self.stock_rack_layout)

    def _init_layout(self):
        self.layout = StockRackLayout()

    def _get_position_kw(self, pos_label, pos_data):
        pool = self._get_pool(pos_data[0])
        rack_pos = get_rack_position_from_label(pos_label)
        tt = TransferTarget(pos_label, 5, 'int')
        return dict(rack_position=rack_pos, molecule_design_pool=pool,
                    tube_barcode=pos_data[1], transfer_targets=[tt])

    def _fill_rack(self, session):
        for pos_label, pos_data in self.position_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            tube = self.rack.specs.tube_specs[0].create_tube(
                            item_status=get_item_status_managed(),
                            barcode=pos_data[1])
            self.rack.add_tube(tube, rack_pos)
            session.add(tube)
            self._add_sample(tube, pos_data[0])
        session.commit()

    def _create_other_objects(self):
        self.stock_rack = self._create_iso_stock_rack(
                                rack_layout=self.layout.create_rack_layout(),
                                label='test_stock_rack',
                                rack=self.rack)

    def test_result_with_layout_conversion(self):
        with RdbContextManager() as session:
            self._continue_setup(session)
            self._test_and_expect_compliance()

    def test_result_without_layout_conversion(self):
        with RdbContextManager() as session:
            self._continue_setup(session)
            self.stock_rack_layout = self.layout
            self._test_and_expect_compliance()

    def test_and_expect_rack_shape_mismatch(self):
        with RdbContextManager() as session:
            self._continue_setup(session)
            self.layout.shape = get_384_rack_shape()
            self.stock_rack_layout = self.layout
            self._test_and_expect_rack_shape_mismatch()

    def test_and_expect_missing_sample(self):
        with RdbContextManager() as session:
            self.add_pos_data = dict(c1=[330001, '1003'])
            self._continue_setup(session)
            self._test_and_expect_missing_sample()

    def test_and_expect_mismatch(self):
        with RdbContextManager() as session:
            self._continue_setup(session)
            rack_pos = get_rack_position_from_label('b1')
            sr_pos = self.layout.get_working_position(rack_pos)
            sr_pos.molecule_design_pool = self._get_pool(330001)
            self.stock_rack_layout = self.layout
            self._test_and_expect_mismatching_samples()

    def test_additional_samples(self):
        with RdbContextManager() as session:
            self._continue_setup(session)
            rack_pos = get_rack_position_from_label('b1')
            self.layout.del_position(rack_pos)
            self.stock_rack_layout = self.layout
            self._test_and_expect_additional_samples()

    def test_insufficient_volume(self):
        with RdbContextManager() as session:
            self.starting_sample_vol = 3 / VOLUME_CONVERSION_FACTOR
            self._continue_setup(session)
            self._test_insufficient_volume()
            self._check_error_messages('A1 (expected: 10 ul, found: 3 ul), ' \
                                       'B1 (expected: 10 ul, found: 3 ul)')
