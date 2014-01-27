"""
Tests for base classes and constants involved in pool stock samples creation
tasks.

AAB
"""
from everest.entities.utils import get_root_aggregate
from thelma.automation.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.iso.poolcreation.base \
    import PoolCreationStockRackLayoutConverter
from thelma.automation.tools.iso.poolcreation.base \
    import PoolCreationStockRackPosition
from thelma.automation.tools.iso.poolcreation.base \
    import StockSampleCreationLayout
from thelma.automation.tools.iso.poolcreation.base \
    import StockSampleCreationLayoutConverter
from thelma.automation.tools.iso.poolcreation.base \
    import StockSampleCreationParameters
from thelma.automation.tools.iso.poolcreation.base \
    import StockSampleCreationPosition
from thelma.automation.tools.iso.poolcreation.base import LABELS
from thelma.automation.tools.iso.poolcreation.base import PoolCreationParameters
from thelma.automation.tools.iso.poolcreation.base import VolumeCalculator
from thelma.automation.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.interfaces import IMoleculeDesign
from thelma.interfaces import IMoleculeType
from thelma.models.moleculedesign import MoleculeDesignPoolSet
from thelma.models.moleculetype import MOLECULE_TYPE_IDS
from thelma.models.tagging import Tag
from thelma.tests.tools.iso.test_base \
    import _StockRackLayoutConverterBaseTestCase
from thelma.tests.tools.iso.test_base import _StockRackClassesBaseTestCase
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase
from thelma.tests.tools.utils.utils import ConverterTestCase
from thelma.tests.tools.utils.utils import MoleculeDesignPoolBaseTestCase


class PoolCreationIsoLabelsTestCase(ToolsAndUtilsTestCase):

    def test_create_iso_label(self):
        self.assert_equal(LABELS.create_iso_label('silB', 4), 'silB_04')

    def test_create_job_label(self):
        self.assert_equal(LABELS.create_job_label('silB', 2), 'silB_job_02')

    def test_create_stock_transfer_worklist_label(self):
        self.assert_equal('stock_transfer_silB_04',
                LABELS.create_stock_transfer_worklist_label('silB_04'))

    def test_create_buffer_worklist_label(self):
        self.assert_equal('silB_buffer',
                          LABELS.create_buffer_worklist_label('silB'))

    def test_create_stock_rack_label(self):
        self.assert_equal('silB_04_psr#1',
                          LABELS.create_stock_rack_label('silB_04', 'psr#1'))

    def test_parse_stock_rack_label(self):
        exp_values = dict(rack_role='psr', rack_num=1, iso_label='silB_04',
                          iso_request_label='silB', layout_number=4,
                          rack_marker='psr#1')
        self.assert_equal(LABELS.parse_stock_rack_label('silB_04_psr#1'),
                          exp_values)


class VolumeCalculatorTestCase(ToolsAndUtilsTestCase):

    TEST_CLS = VolumeCalculator

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.target_volume = 30 # 30 ul
        self.target_conc = 10000 # 10 uM
        self.number_designs = 3
        self.stock_conc = 50000 # 50 uM
        self.exp_single_transfer_vol = 2
        self.exp_buffer_vol = 24
        self.adj_target_vol = None

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.target_volume
        del self.target_conc
        del self.number_designs
        del self.stock_conc
        del self.exp_single_transfer_vol
        del self.exp_buffer_vol
        del self.adj_target_vol

    def __create_calculator(self):
        kw = dict(target_volume=self.target_volume,
                    target_concentration=self.target_conc,
                    number_designs=self.number_designs,
                    stock_concentration=self.stock_conc)
        return self.TEST_CLS(**kw)

    def __check_result(self, volume_calculator=None):
        if volume_calculator is None:
            volume_calculator = self.__create_calculator()
        volume_calculator.calculate()
        self.assert_equal(self.exp_single_transfer_vol,
                volume_calculator.get_single_design_stock_transfer_volume())
        self.assert_equal(self.exp_buffer_vol,
                volume_calculator.get_buffer_volume())
        self.assert_equal(self.adj_target_vol,
                volume_calculator.get_adjusted_target_volume())

    def test_result(self):
        self.__check_result()

    def test_result_for_iso_request(self):
        pool = self._get_pool(205200) # siRNA
        pool_set = self._create_molecule_design_pool_set(
                            molecule_design_pools={pool},
                            molecule_type=pool.molecule_type)
        ir = self._create_stock_sample_creation_iso_request(
                 stock_volume=self.target_volume / VOLUME_CONVERSION_FACTOR,
                 stock_concentration=\
                            self.target_conc / CONCENTRATION_CONVERSION_FACTOR,
                 number_designs=3, molecule_design_pool_set=pool_set)
        vc = VolumeCalculator.from_iso_request(ir)
        self.__check_result(vc)

    def test_adjusted_target_volume(self):
        self.target_volume = 20
        self.adj_target_vol = 21
        self.exp_single_transfer_vol = 1.4
        self.exp_buffer_vol = 16.8
        self.__check_result()

    def test_target_single_conc_greater_than_stock_conc(self):
        # stock conc = 50 uM, assumed target single conc 60 uM,
        # * number designs = 180 uM
        self.target_conc = 180000
        self._expect_error(ValueError, self.__check_result,
            'The requested target concentration (180000 nM) cannot be ' \
            'achieved since it would require a concentration of 60000 nM for ' \
            'each single design in the pool. However, the stock ' \
            'concentration for this design type is only 50000 nM.')

    def test_single_design_transfer_vol_below_minimum(self):
        # with df = 15 (current), the minimum volume must be 15
        self.target_volume = 5
        self._expect_error(ValueError, self.__check_result,
            'The target volume you have requested (5 ul) is too low for the ' \
            'required dilution (1:15) since the CyBio cannot pipet less than ' \
            '1.0 ul per transfer. The volume that has to be taken from the ' \
            'stock for each single molecule design would be lower that that. ' \
            'Increase the target volume to 15.0 ul or increase the target ' \
            'concentration')


class _StockSampleCreationClassesBaseTestCase(MoleculeDesignPoolBaseTestCase):

    POS_CLS = StockSampleCreationPosition
    LAYOUT_CLS = StockSampleCreationLayout

    POOL_TAGS = dict(
          a1=Tag('molecule_design_pool', 'molecule_design_pool_id', '1056000'),
          b1=Tag('molecule_design_pool', 'molecule_design_pool_id', '1068580'))

    _MOLECULE_DESIGN_TAGS = dict(
          a1=Tag('stock_sample_generation', 'molecule_designs',
                 '10315676-10319279-10341998'),
          b1=Tag('stock_sample_generation', 'molecule_designs',
                 '10409461-10409467'))

    _TUBE_TAGS = dict(
          a1=Tag('stock_sample_generation', 'stock_tube_barcodes',
                 '1001-1002-1003'),
          b1=Tag('stock_sample_generation', 'stock_tube_barcodes', '2001-2002'))

    def set_up(self):
        MoleculeDesignPoolBaseTestCase.set_up(self)
        self.pos_data = dict(
                    a1=[self._get_pool(1056000), ['1001', '1002', '1003']],
                    b1=[self._get_pool(1068580), ['2001', '2002']])

    def _get_molecule_designs(self, pos_label):
        if pos_label == 'a1':
            md_ids = sorted([10315676, 10319279, 10341998])
        elif pos_label == 'b1':
            md_ids = sorted([10409461, 10409467])
        else:
            raise ValueError('unexpected position label: %s' % (pos_label))
        mds = []
        agg = get_root_aggregate(IMoleculeDesign)
        for md_id in md_ids:
            md = agg.get_by_id(md_id)
            if md is None:
                raise ValueError('Could not find md %s.' % (md_id))
            mds.append(md)
        return mds

    def _get_init_data(self, pos_label):
        pos_data = self.pos_data[pos_label]
        kw = dict(rack_position=get_rack_position_from_label(pos_label),
                  molecule_design_pool=pos_data[0],
                  stock_tube_barcodes=pos_data[1])
        return kw

    def _get_tags(self, pos_label):
        tags = set([self.POOL_TAGS[pos_label]])
        self._add_optional_tag(tags, self._TUBE_TAGS, pos_label)
        self._add_optional_tag(tags, self._MOLECULE_DESIGN_TAGS, pos_label)
        return tags


class StockSampleCreationPositionTestCase(
                                    _StockSampleCreationClassesBaseTestCase):

    def test_init(self):
        self._test_position_init()
        for pos_label in self.pos_data.keys():
            sscp = self._get_position(pos_label)
            self.assert_equal(sscp.molecule_designs,
                              self._get_molecule_designs(pos_label))
        attrs = self._get_init_data('a1')
        attrs['stock_tube_barcodes'] = dict()
        exp_msg = 'The stock tube barcodes must be a list (obtained: dict)'
        self._expect_error(TypeError, self.POS_CLS, exp_msg, **attrs)

    def test_equality(self):
        self._test_position_equality(dict(stock_tube_barcodes=['9999']),
                                     dict(molecule_designs=[3]))

    def test_get_tags(self):
        self._test_position_get_tag_set()

    def test_get_molecule_design_tag_value(self):
        sscp = self._get_position('a1')
        exp_tv = self._MOLECULE_DESIGN_TAGS['a1'].value
        self.assert_equal(sscp.get_molecule_designs_tag_value(), exp_tv)

    def test_validate_molecule_design_tags(self):
        pool = self.pos_data['a1'][0]
        md_tag_value = self._MOLECULE_DESIGN_TAGS['a1'].value
        self.assert_true(self.POS_CLS.validate_molecule_designs(pool,
                                                                md_tag_value))
        alt_tag_value = md_tag_value[:-1]
        self.assert_false(self.POS_CLS.validate_molecule_designs(pool,
                                                                 alt_tag_value))

    def test_get_stock_barcodes_tag_value(self):
        self.pos_data['a1'][1].reverse()
        sscp = self._get_position('a1')
        exp_value = self._TUBE_TAGS['a1'].value
        self.assert_equal(sscp.get_stock_barcodes_tag_value(), exp_value)

    def test_get_tube_barcodes_from_tag_value(self):
        exp_barcodes = self.pos_data['a1'][1]
        self.assert_equal(exp_barcodes,
                          self.POS_CLS.get_tube_barcodes_from_tag_value(
                                                self._TUBE_TAGS['a1'].value))


class StockSampleCreationLayoutTestCase(
                                _StockSampleCreationClassesBaseTestCase):

    def test_init(self):
        self._test_layout_init()
        sscl = self.LAYOUT_CLS(**dict())
        self.assert_equal(sscl.shape.name, RACK_SHAPE_NAMES.SHAPE_96)

    def test_get_pool_set(self):
        self.pos_data['b1'][0] = self._get_pool(1056001)
        exp_pools = []
        for pos_data in self.pos_data.values():
            exp_pools.append(pos_data[0])
        sscl = self._create_test_layout()
        mt = get_root_aggregate(IMoleculeType).get_by_id(
                                                    MOLECULE_TYPE_IDS.SIRNA)
        pool_set = sscl.get_pool_set(mt)
        self.assert_is_not_none(pool_set)
        self.assert_true(isinstance(pool_set, MoleculeDesignPoolSet))
        self.assert_equal(pool_set.molecule_type.id, MOLECULE_TYPE_IDS.SIRNA)
        pools = pool_set.molecule_design_pools
        self.assert_equal(len(pools), len(exp_pools))
        for pool in pools: self.assert_true(pool in exp_pools)


class _StockSampleCreationConverterBaseTestCase(ConverterTestCase,
                                    _StockSampleCreationClassesBaseTestCase):

    PARAMETER_SET = StockSampleCreationParameters
    POS_CLS = StockSampleCreationPosition
    LAYOUT_CLS = StockSampleCreationLayout
    CONVERTER_CLS = StockSampleCreationLayoutConverter

    _POOL_INDEX = 0
    _MOLECULE_DESIGN_INDEX = 1
    _TUBE_BARCODE_INDEX = 2

    def set_up(self):
        ConverterTestCase.set_up(self)
        self.pos_set_data = {1 : ['a1', 'a2'], 2 : ['b1'], 3 : ['a1', 'b1']}
        self.tag_data = {3 : [Tag('some', 'other', 'data')]}
        self.tag_key_map = {1 : 'a1', 2 : 'b1'}
        for k, pos_label in self.tag_key_map.iteritems():
            self.tag_data[k] = []
            self._insert_tag_data_tag(k, pos_label, self.POOL_TAGS,
                                      self._POOL_INDEX)
            self._insert_tag_data_tag(k, pos_label, self._MOLECULE_DESIGN_TAGS,
                                      self._MOLECULE_DESIGN_INDEX)
            self._insert_tag_data_tag(k, pos_label, self._TUBE_TAGS,
                                      self._TUBE_BARCODE_INDEX)

    def _get_all_tags(self):
        tags = self.tag_data[1] + self.tag_data[2]
        return tags

    def _test_tag_for_position(self, layout):
        rack_pos = get_rack_position_from_label('a2')
        tag_set = layout.get_tags_for_position(rack_pos)
        exp_tags = self.tag_data[1]
        self._compare_tag_sets(exp_tags, tag_set)

    def _test_position_for_tag(self, layout):
        tag = self._MOLECULE_DESIGN_TAGS['a1']
        exp_positions = self.pos_set_data[1]
        pos_set = layout.get_positions_for_tag(tag)
        self._compare_pos_sets(exp_positions, pos_set)


class StockSampleCreationLayoutConverterTestCase(
                            _StockSampleCreationConverterBaseTestCase):

    def test_result(self):
        self._test_result()

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_mismatching_molecule_designs(self):
        self.tag_data[2][self._MOLECULE_DESIGN_INDEX] = \
                                            self._MOLECULE_DESIGN_TAGS['a1']
        self._test_invalid_rack_layout('The molecule designs IDs for some ' \
                'pools do not match: B1 (pool 1068580, found: ' \
                '10315676-10319279-10341998, expected: 10409461-10409467).')

    def test_missing_tubes(self):
        self.tag_data[1][self._TUBE_BARCODE_INDEX] = Tag('not', 'the', 'tubes')
        self._test_invalid_rack_layout('The following rack positions do not ' \
                                       'contain stock tube barcodes: A1, A2.')

    def test_tube_mismatch(self):
        self.tag_data[1][self._TUBE_BARCODE_INDEX] = self._TUBE_TAGS['b1']
        self._test_invalid_rack_layout('For some positions the number of ' \
                'tubes does not match the number of molecule designs: ' \
                'A1 (2001-2002, number mds: 3), A2 (2001-2002, number mds: 3).')


class _PoolCreationParametersClassesTestCase(
                                    _StockRackClassesBaseTestCase):

    POS_CLS = PoolCreationStockRackPosition

    _TRANSFER_TARGET_TAGS = dict()

    def set_up(self):
        _StockRackClassesBaseTestCase.set_up(self)
        for pos_data in self.pos_data.values():
            pos_data[-1] = []


class PoolCreationStockRackPositionTestCase(
                                    _PoolCreationParametersClassesTestCase):

    def test_init(self):
        self._test_position_init()
        pcsrp = self._get_position('a1')
        self.assert_equal(len(pcsrp.transfer_targets), 0)
        # would not be allowed in the superclass


class PoolCreationStockRackLayoutConverterTestCase(
                                    _StockRackLayoutConverterBaseTestCase):

    PARAMETER_SET = PoolCreationParameters
    POS_CLS = PoolCreationStockRackPosition
    CONVERTER_CLS = PoolCreationStockRackLayoutConverter

    def set_up(self):
        _StockRackLayoutConverterBaseTestCase.set_up(self)
        for k in self.tag_key_map.keys():
            del self.tag_data[k][self._TRANSFER_TARGET_INDEX]

    def test_result(self):
        layout = self._test_result()
        for pcsrp in layout.working_positions():
            self.assert_equal(len(pcsrp.transfer_targets), 0)
