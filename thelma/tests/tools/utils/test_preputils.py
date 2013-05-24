"""
Tests for ISO preparation utils.

AAB, Jan 2012
"""
from everest.testing import check_attributes
from thelma.automation.tools.iso.prep_utils import IsoControlRackLayout
from thelma.automation.tools.iso.prep_utils import IsoControlRackLayoutConverter
from thelma.automation.tools.iso.prep_utils import IsoControlRackParameters
from thelma.automation.tools.iso.prep_utils import IsoControlRackPosition
from thelma.automation.tools.iso.prep_utils import PrepIsoAssociationData
from thelma.automation.tools.iso.prep_utils import PrepIsoLayout
from thelma.automation.tools.iso.prep_utils import PrepIsoLayoutConverter
from thelma.automation.tools.iso.prep_utils import PrepIsoParameters
from thelma.automation.tools.iso.prep_utils import PrepIsoPosition
from thelma.automation.tools.iso.prep_utils import PrepIsoRackSectorAssociator
from thelma.automation.tools.iso.prep_utils import PrepIsoValueDeterminer
from thelma.automation.tools.iso.prep_utils import RequestedStockSample
from thelma.automation.tools.semiconstants import get_384_rack_shape
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.utils.base import FIXED_POSITION_TYPE
from thelma.automation.tools.utils.base import FLOATING_POSITION_TYPE
from thelma.automation.tools.utils.base import MOCK_POSITION_TYPE
from thelma.automation.tools.utils.base import TransferParameters
from thelma.automation.tools.utils.base import TransferTarget
from thelma.automation.tools.utils.base import UNTREATED_POSITION_TYPE
from thelma.automation.tools.utils.iso import IsoParameters
from thelma.automation.tools.utils.iso import IsoPosition
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import IRackShape
from thelma.models.organization import Organization
from thelma.models.racklayout import RackLayout
from thelma.models.tagging import Tag
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase
from thelma.automation.tools.iso.prep_utils import ISO_LABELS


class IsoLabelsTestCase(ToolsAndUtilsTestCase):

    def test_create_iso_label(self):
        ticket_number = 123
        em = self._create_experiment_metadata(ticket_number=ticket_number)
        ir = self._create_iso_request(experiment_metadata=em)
        label1 = ISO_LABELS.create_iso_label(iso_request=ir)
        self.assert_equal(label1, '123_iso1')
        self._create_iso(label=label1, iso_request=ir)
        label2 = ISO_LABELS.create_iso_label(iso_request=ir)
        self.assert_equal(label2, '123_iso2')
        self._create_iso(label=label2, iso_request=ir)
        label3 = ISO_LABELS.create_iso_label(iso_request=ir, create_copy=True)
        self.assert_equal(label3, '123_iso3_copy')

    def test_get_iso_number(self):
        label1 = '456_iso4'
        iso1 = self._create_iso(label=label1)
        self.assert_equal(ISO_LABELS.get_iso_number(iso1), 4)
        label2 = '456_iso19_copy'
        iso2 = self._create_iso(label=label2)
        self.assert_equal(ISO_LABELS.get_iso_number(iso2), 19)

    def test_create_aliquot_plate_label(self):
        em = self._create_experiment_metadata(ticket_number=123)
        ir = self._create_iso_request(plate_set_label='psl', number_aliquots=1,
                                      experiment_metadata=em)
        iso_label = ISO_LABELS.create_iso_label(ir)
        iso = self._create_iso(iso_request=ir, label=iso_label)
        label1 = 'psl#1'
        self.assert_equal(ISO_LABELS.create_aliquot_plate_label(iso), label1)
        ir.number_aliquots = 2
        label2 = 'psl#1_a1'
        self.assert_equal(ISO_LABELS.create_aliquot_plate_label(iso), label2)
        ir.number_aliquots = 1
        label3 = 'psl#1_a2'
        self.assert_equal(label3,
                  ISO_LABELS.create_aliquot_plate_label(iso, aliquot_number=2))


class PrepIsoPositionTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.rack_position = get_rack_position_from_label('A1')
        self.pool = self._get_entity(IMoleculeDesignPool, '205200')
        self.position_type = FIXED_POSITION_TYPE
        self.prep_concentration = 2800
        self.required_volume = 15
        self.stock_tube_barcode = '0123456789'
        self.stock_rack_barcode = '09539'
        tt1 = TransferTarget(rack_position='A2', transfer_volume=5)
        tt2 = TransferTarget(rack_position='A3', transfer_volume=5)
        self.transfer_targets = [tt1, tt2]
        self.parent_well = get_rack_position_from_label('B2')
        self.init_data = dict(rack_position=self.rack_position,
                              molecule_design_pool=self.pool,
                              position_type=self.position_type,
                              prep_concentration=self.prep_concentration,
                              required_volume=self.required_volume,
                              transfer_targets=self.transfer_targets,
                              stock_tube_barcode=self.stock_tube_barcode,
                              stock_rack_barcode=self.stock_rack_barcode,
                              parent_well=self.parent_well)
        self.min_init_data = dict(rack_position=self.rack_position,
                             molecule_design_pool=self.pool,
                             position_type=self.position_type,
                             prep_concentration=self.prep_concentration,
                             required_volume=self.required_volume,
                             transfer_targets=self.transfer_targets)
        self.mdp_tag = Tag('iso_preparation', 'molecule_design_pool_id',
                           '205200')
        self.type_tag = Tag('iso_preparation', 'position_type', 'fixed')
        self.prep_conc_tag = Tag('iso_preparation', 'preparation_concentration',
                                 '2800')
        self.req_vol_tag = Tag('iso_preparation', 'required_volume', '15')
        self.tt_tag = Tag('sample_transfer', 'target_wells',
                          'A2:5-A3:5')
        self.barcode_tag = Tag('iso_preparation', 'stock_tube_barcode',
                               '0123456789')
        self.rack_tag = Tag('iso_preparation', 'stock_rack_barcode', '09539')
        self.parent_well_tag = Tag('iso_preparation', 'parent_well', 'B2')
        self.md_mock_tag = Tag('iso_preparation', 'molecule_design_pool_id',
                               'mock')

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.rack_position
        del self.pool
        del self.position_type
        del self.prep_concentration
        del self.required_volume
        del self.stock_tube_barcode
        del self.stock_rack_barcode
        del self.transfer_targets
        del self.parent_well
        del self.init_data
        del self.min_init_data
        del self.mdp_tag
        del self.type_tag
        del self.prep_conc_tag
        del self.req_vol_tag
        del self.tt_tag
        del self.barcode_tag
        del self.rack_tag
        del self.parent_well_tag
        del self.md_mock_tag

    def test_init(self):
        pp1 = PrepIsoPosition(**self.min_init_data)
        self.min_init_data['stock_tube_barcode'] = None
        self.min_init_data['stock_rack_barcode'] = None
        self.min_init_data['parent_well'] = None
        check_attributes(pp1, self.min_init_data)
        pp2 = PrepIsoPosition(**self.init_data)
        check_attributes(pp2, self.init_data)
        # Test Errors
        self.init_data['rack_position'] = self.rack_position.label
        self.assert_raises(ValueError, PrepIsoPosition, **self.init_data)
        self.init_data['rack_position'] = self.rack_position
        self.init_data['molecule_design_pool'] = 4.3
        self.assert_raises(ValueError, PrepIsoPosition, **self.init_data)
        self.init_data['molecule_design_pool'] = self.pool
        self.init_data['prep_concentration'] = 0
        self.assert_raises(ValueError, PrepIsoPosition, **self.init_data)
        self.init_data['prep_concentration'] = 2.8
        self.init_data['required_volume'] = 0
        self.assert_raises(ValueError, PrepIsoPosition, **self.init_data)
        self.init_data['required_volume'] = 15
        self.init_data['transfer_targets'] = dict()
        self.assert_raises(TypeError, PrepIsoPosition, **self.init_data)
        self.init_data['transfer_targets'] = self.transfer_targets
        self.init_data['stock_tube_barcode'] = 123
        self.assert_raises(TypeError, PrepIsoPosition, **self.init_data)
        self.init_data['stock_tube_barcode'] = '0123456789'
        self.init_data['stock_rack_barcode'] = 9539
        self.assert_raises(TypeError, PrepIsoPosition, **self.init_data)
        self.init_data['stock_rack_barcode'] = '09539'
        self.init_data['parent_well'] = self.parent_well.label
        self.assert_raises(TypeError, PrepIsoPosition, **self.init_data)

    def test_mock_factory(self):
        self.init_data['molecule_design_pool'] = MOCK_POSITION_TYPE
        self.init_data['position_type'] = MOCK_POSITION_TYPE
        self.init_data['prep_concentration'] = None
        self.init_data['stock_tube_barcode'] = None
        self.init_data['stock_rack_barcode'] = None
        self.init_data['parent_well'] = None
        mock_pp = PrepIsoPosition.create_mock_position(
                                    rack_position=self.rack_position,
                                    required_volume=self.required_volume,
                                    transfer_targets=self.transfer_targets)
        check_attributes(mock_pp, self.init_data)
        # test mock ini inconsistency
        pp = PrepIsoPosition(**self.init_data)
        self.assert_is_not_none(pp)
        self.init_data['molecule_design_pool'] = self.pool
        self.assert_raises(ValueError, PrepIsoPosition, **self.init_data)
        self.init_data['molecule_design_pool'] = MOCK_POSITION_TYPE
        self.init_data['position_type'] = FIXED_POSITION_TYPE
        self.assert_raises(ValueError, PrepIsoPosition, **self.init_data)

    def test_equality(self):
        pp1 = PrepIsoPosition(**self.init_data)
        pp2 = PrepIsoPosition(**self.init_data)
        other_rack_pos = get_rack_position_from_label('A2')
        self.init_data['rack_position'] = other_rack_pos
        pp3 = PrepIsoPosition(**self.init_data)
        self.init_data['rack_position'] = self.rack_position
        other_pool = self._get_entity(IMoleculeDesignPool, '330001')
        self.init_data['molecule_design_pool'] = other_pool
        pp4 = PrepIsoPosition(**self.init_data)
        self.init_data['molecule_design_pool'] = self.pool
        self.init_data['prep_concentration'] = (self.prep_concentration * 2)
        pp5 = PrepIsoPosition(**self.init_data)
        self.init_data['prep_concentration'] = self.prep_concentration
        self.init_data['transfer_targets'] = [self.transfer_targets[0]]
        pp6 = PrepIsoPosition(**self.init_data)
        self.init_data['transfer_targets'] = self.transfer_targets
        self.init_data['required_volume'] = (self.required_volume * 2)
        pp7 = PrepIsoPosition(**self.init_data)
        self.init_data['required_volume'] = self.required_volume
        self.init_data['stock_tube_barcode'] = '0987654321'
        pp8 = PrepIsoPosition(**self.init_data)
        self.init_data['stock_tube_barcode'] = self.stock_tube_barcode
        self.init_data['stock_rack_barcode'] = '0150'
        pp9 = PrepIsoPosition(**self.init_data)
        self.init_data['stock_rack_barcode'] = self.stock_rack_barcode
        self.init_data['parent_well'] = other_rack_pos
        pp10 = PrepIsoPosition(**self.init_data)
        self.assert_equal(pp1, pp2)
        self.assert_not_equal(pp1, pp3)
        self.assert_not_equal(pp1, pp4)
        self.assert_not_equal(pp1, pp5)
        self.assert_equal(pp1, pp6)
        self.assert_equal(pp1, pp7)
        self.assert_equal(pp1, pp8)
        self.assert_equal(pp1, pp9)
        self.assert_equal(pp1, pp10)
        self.assert_not_equal(pp1, self.rack_position)

    def test_floating_md(self):
        self.pool = 'md_1'
        self.init_data['molecule_design_pool'] = self.pool
        pp = PrepIsoPosition(**self.init_data)
        self.assert_is_not_none(pp)
        self.init_data['molecule_design_pool'] = 'some'
        self.assert_raises(ValueError, PrepIsoPosition, **self.init_data)

    def test_untreated_failure(self):
        self.init_data['molecule_design_pool'] = UNTREATED_POSITION_TYPE
        self.assert_raises(ValueError, PrepIsoPosition, **self.init_data)

    def test_get_tag_set(self):
        pp1 = PrepIsoPosition(**self.min_init_data)
        tags1 = [self.mdp_tag, self.prep_conc_tag, self.tt_tag,
                 self.req_vol_tag, self.type_tag]
        tag_set1 = pp1.get_tag_set()
        self._compare_tag_sets(tags1, tag_set1)
        pp2 = PrepIsoPosition(**self.init_data)
        tags2 = [self.mdp_tag, self.barcode_tag, self.prep_conc_tag,
                 self.tt_tag, self.req_vol_tag, self.parent_well_tag,
                 self.rack_tag, self.type_tag]
        tag_set2 = pp2.get_tag_set()
        self._compare_tag_sets(tags2, tag_set2)

    def test_mock_tag_set(self):
        pp_mock = PrepIsoPosition.create_mock_position(
                                    rack_position=self.rack_position,
                                    required_volume=self.required_volume,
                                    transfer_targets=self.transfer_targets)
        type_mock_tag = Tag('iso_preparation', 'position_type', 'mock')
        exp_tags = [self.md_mock_tag, self.req_vol_tag, self.tt_tag,
                    type_mock_tag]
        tag_set = pp_mock.get_tag_set()
        self._compare_tag_sets(exp_tags, tag_set)

    def test_get_parameter_values(self):
        pp = PrepIsoPosition(**self.init_data)
        self.assert_equal(self.pool,
                pp.get_parameter_value(PrepIsoParameters.MOLECULE_DESIGN_POOL))
        self.assert_equal(self.position_type,
                pp.get_parameter_value(PrepIsoParameters.POSITION_TYPE))
        self.assert_equal(self.stock_tube_barcode,
                pp.get_parameter_value(PrepIsoParameters.STOCK_TUBE_BARCODE))
        self.assert_equal(self.stock_rack_barcode,
                pp.get_parameter_value(PrepIsoParameters.STOCK_RACK_BARCODE))
        self.assert_equal(self.prep_concentration,
                pp.get_parameter_value(PrepIsoParameters.PREP_CONCENTRATION))
        self.assert_equal(self.transfer_targets,
                pp.get_parameter_value(PrepIsoParameters.TARGET_WELLS))
        self.assert_equal(self.required_volume,
                pp.get_parameter_value(PrepIsoParameters.REQUIRED_VOLUME))
        self.assert_equal(self.parent_well,
                pp.get_parameter_value(PrepIsoParameters.PARENT_WELL))

    def test_get_parameter_tag(self):
        pp = PrepIsoPosition(**self.init_data)
        self.assert_equal(self.mdp_tag,
                pp.get_parameter_tag(PrepIsoParameters.MOLECULE_DESIGN_POOL))
        self.assert_equal(self.type_tag,
                pp.get_parameter_tag(PrepIsoParameters.POSITION_TYPE))
        self.assert_equal(self.barcode_tag,
                pp.get_parameter_tag(PrepIsoParameters.STOCK_TUBE_BARCODE))
        self.assert_equal(self.rack_tag,
                pp.get_parameter_tag(PrepIsoParameters.STOCK_RACK_BARCODE))
        self.assert_equal(self.prep_conc_tag,
                pp.get_parameter_tag(PrepIsoParameters.PREP_CONCENTRATION))
        self.assert_equal(self.tt_tag,
                pp.get_parameter_tag(PrepIsoParameters.TARGET_WELLS))
        self.assert_equal(self.req_vol_tag,
                pp.get_parameter_tag(PrepIsoParameters.REQUIRED_VOLUME))
        self.assert_equal(self.parent_well_tag,
                pp.get_parameter_tag(PrepIsoParameters.PARENT_WELL))

    def test_hash_value(self):
        pp = PrepIsoPosition(**self.init_data)
        hash_value = '2052002800'
        self.assert_equal(pp.hash_value, hash_value)

    def test_is_floating(self):
        pp1 = PrepIsoPosition(**self.init_data)
        self.assert_false(pp1.is_floating)
        placeholder = '%s1' % (IsoParameters.FLOATING_INDICATOR)
        self.init_data['position_type'] = FLOATING_POSITION_TYPE
        pp2 = PrepIsoPosition(**self.init_data)
        self.assert_true(pp2.is_floating)
        self.init_data['molecule_design_pool'] = placeholder
        pp3 = PrepIsoPosition(**self.init_data)
        self.assert_true(pp3.is_floating)

    def test_is_mock(self):
        pp1 = PrepIsoPosition(**self.init_data)
        self.assert_false(pp1.is_mock)
        self.init_data['molecule_design_pool'] = MOCK_POSITION_TYPE
        self.init_data['position_type'] = MOCK_POSITION_TYPE
        pp2 = PrepIsoPosition(**self.init_data)
        self.assert_true(pp2.is_mock)

    def test_get_stock_concentration(self):
        pp = PrepIsoPosition(**self.min_init_data)
        self.assert_equal(pp.stock_concentration, 50000)
        self.init_data['molecule_design_pool'] = MOCK_POSITION_TYPE
        self.init_data['position_type'] = MOCK_POSITION_TYPE
        pp_mock = PrepIsoPosition(**self.init_data)
        self.assert_is_none(pp_mock.stock_concentration)

    def test_get_stock_take_out_volume(self):
        pp = PrepIsoPosition(**self.min_init_data)
        self.assert_equal(pp.get_stock_takeout_volume(), 0.8)
        pp.parent_well = self.parent_well
        self.assert_is_none(pp.get_stock_takeout_volume())
        self.init_data['molecule_design_pool'] = MOCK_POSITION_TYPE
        self.init_data['position_type'] = MOCK_POSITION_TYPE
        pp_mock = PrepIsoPosition(**self.init_data)
        self.assert_equal(pp_mock.get_stock_takeout_volume(), 0)

    def test_get_completed_copy(self):
        pp = PrepIsoPosition(**self.min_init_data)
        pp.parent_well = self.parent_well
        copy1 = pp.get_completed_copy(self.stock_tube_barcode,
                                      self.stock_rack_barcode)
        check_attributes(copy1, self.init_data)
        self.assert_is_none(pp.stock_tube_barcode)
        self.assert_is_none(pp.stock_rack_barcode)
        self.assert_equal(pp.molecule_design_pool_id,
                          copy1.molecule_design_pool_id)
        placeholder = '%s1' % (IsoParameters.FLOATING_INDICATOR)
        pp.molecule_design_pool = placeholder
        copy2 = pp.get_completed_copy(self.stock_tube_barcode,
                        self.stock_rack_barcode, self.pool)
        check_attributes(copy2, self.init_data)
        self.assert_is_none(pp.stock_tube_barcode)
        self.assert_is_none(pp.stock_rack_barcode)
        self.assert_not_equal(pp.molecule_design_pool_id,
                              copy2.molecule_design_pool_id)
        self.init_data['molecule_design_pool'] = MOCK_POSITION_TYPE
        self.init_data['position_type'] = MOCK_POSITION_TYPE
        mock_pp = PrepIsoPosition(**self.init_data)
        self.assert_is_none(mock_pp.get_completed_copy(self.stock_tube_barcode,
                                                       self.stock_rack_barcode))

    def test_supplier(self):
        supplier = Organization(name='test_supplier')
        # fixed positions
        pp = PrepIsoPosition(**self.init_data)
        pp.set_supplier(supplier)
        self.assert_equal(pp.get_supplier(), supplier)
        self.assert_raises(TypeError, pp.set_supplier, 'test_supplier')
        # floating position
        self.init_data['position_type'] = FLOATING_POSITION_TYPE
        pp = PrepIsoPosition(**self.init_data)
        self.assert_true(pp.is_floating)
        self.assert_raises(ValueError, pp.set_supplier, supplier)
        # mock position
        pp = PrepIsoPosition.create_mock_position(
                                rack_position=self.rack_position,
                                required_volume=self.required_volume,
                                transfer_targets=self.transfer_targets)
        self.assert_true(pp.is_mock)
        self.assert_raises(ValueError, pp.set_supplier, supplier)

    def test_inactivation(self):
        pp = PrepIsoPosition(**self.init_data)
        self.assert_is_not_none(pp.stock_tube_barcode)
        self.assert_is_not_none(pp.stock_rack_barcode)
        self.assert_false(pp.is_inactivated)
        pp.inactivate()
        self.assert_is_none(pp.stock_tube_barcode)
        self.assert_is_none(pp.stock_rack_barcode)
        self.assert_true(pp.is_inactivated)
        mock_pp = PrepIsoPosition.create_mock_position(
                                        rack_position=self.rack_position,
                                        required_volume=self.required_volume,
                                        transfer_targets=self.transfer_targets)
        self.assert_false(mock_pp.is_inactivated)


class PrepIsoLayoutTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.shape = get_96_rack_shape()
        self.a1_pos = get_rack_position_from_label('A1')
        self.a2_pos = get_rack_position_from_label('A2')
        self.a3_pos = get_rack_position_from_label('A3')
        self.b1_pos = get_rack_position_from_label('B1')
        self.b2_pos = get_rack_position_from_label('B2')
        self.b3_pos = get_rack_position_from_label('B3')
        self.c3_pos = get_rack_position_from_label('C3')
        self.d1_pos = get_rack_position_from_label('D1')
        parameters = PrepIsoParameters
        self.mdp1 = self._get_entity(IMoleculeDesignPool, '205200')
        self.mdp1_tag = Tag(parameters.DOMAIN, parameters.MOLECULE_DESIGN_POOL,
                           self.mdp1.id)
        self.mdp2 = self._get_entity(IMoleculeDesignPool, '1056000')
        self.mdp2_tag = Tag(parameters.DOMAIN, parameters.MOLECULE_DESIGN_POOL,
                           self.mdp2.id)
        self.fixed_tag = Tag(parameters.DOMAIN, parameters.POS_TYPE,
                             FIXED_POSITION_TYPE)
        self.md_mock = MOCK_POSITION_TYPE
        self.md_mock_tag = Tag(parameters.DOMAIN,
                               parameters.MOLECULE_DESIGN_POOL, self.md_mock)
        self.mock_type_tag = Tag(parameters.DOMAIN, parameters.POS_TYPE,
                                 MOCK_POSITION_TYPE)
        self.barcode1 = '0111'
        self.barcode1_tag = Tag(parameters.DOMAIN,
                                parameters.STOCK_TUBE_BARCODE, self.barcode1)
        self.barcode2 = '0222'
        self.barcode2_tag = Tag(parameters.DOMAIN,
                                parameters.STOCK_TUBE_BARCODE, self.barcode2)
        self.rack_barcode = '09539'
        self.rack_barcode_tag = Tag(parameters.DOMAIN,
                                parameters.STOCK_RACK_BARCODE,
                                self.rack_barcode)
        self.prep_conc1 = 2.8
        self.prep_conc1_tag = Tag(parameters.DOMAIN,
                                 parameters.PREP_CONCENTRATION,
                                 str(self.prep_conc1))
        self.prep_conc2 = 5.6
        self.prep_conc2_tag = Tag(parameters.DOMAIN,
                                 parameters.PREP_CONCENTRATION,
                                 str(self.prep_conc2))
        self.iso_volume = 5
        self.tt_a1_tag = Tag(TransferParameters.DOMAIN,
                             TransferParameters.TARGET_WELLS,
                             'A1:5')
        self.tt_a2_tag = Tag(TransferParameters.DOMAIN,
                             TransferParameters.TARGET_WELLS,
                             'A2:5')
        self.tt_b1_tag = Tag(TransferParameters.DOMAIN,
                             TransferParameters.TARGET_WELLS,
                             'B1:5')
        self.tt_b2_tag = Tag(TransferParameters.DOMAIN,
                             TransferParameters.TARGET_WELLS,
                             'B2:5')
        self.tt_mock_tag = Tag(TransferParameters.DOMAIN,
                               TransferParameters.TARGET_WELLS,
                               'D1:5')
        self.req_vol1 = 15
        self.req_vol1_tag = Tag(parameters.DOMAIN, parameters.REQUIRED_VOLUME,
                                '%.0f' % (self.req_vol1))
        self.req_vol2 = 22.5
        self.req_vol2_tag = Tag(parameters.DOMAIN, parameters.REQUIRED_VOLUME,
                                str(self.req_vol2))
        self.req_vol_mock = 50
        self.req_vol_mock_tag = Tag(parameters.DOMAIN,
                                    parameters.REQUIRED_VOLUME,
                                    '%.0f' % (self.req_vol_mock))
        self.parent_well1 = self.a1_pos
        self.parent_tag1 = Tag(parameters.DOMAIN, parameters.PARENT_WELL,
                               self.parent_well1.label)
        self.parent_well2 = self.a2_pos
        self.parent_tag2 = Tag(parameters.DOMAIN, parameters.PARENT_WELL,
                               self.parent_well2.label)
        self.a1_pp = self.__create_prep_positions(self.a1_pos)
        self.a2_pp = self.__create_prep_positions(self.a2_pos,
                                                  self.parent_well1)
        self.b1_pp = self.__create_prep_positions(self.b1_pos)
        self.b2_pp = self.__create_prep_positions(self.b2_pos,
                                                  self.parent_well2)
        tt_mock = TransferTarget(rack_position=self.d1_pos, transfer_volume=5)
        self.d1_pp = PrepIsoPosition.create_mock_position(
                                     rack_position=self.d1_pos,
                                     required_volume=self.req_vol_mock,
                                     transfer_targets=[tt_mock])

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.shape
        del self.a1_pos
        del self.a2_pos
        del self.a3_pos
        del self.b1_pos
        del self.b2_pos
        del self.b3_pos
        del self.c3_pos
        del self.d1_pos
        del self.mdp1
        del self.mdp1_tag
        del self.mdp2
        del self.mdp2_tag
        del self.md_mock
        del self.md_mock_tag
        del self.barcode1
        del self.barcode1_tag
        del self.barcode2
        del self.barcode2_tag
        del self.rack_barcode
        del self.rack_barcode_tag
        del self.prep_conc1
        del self.prep_conc1_tag
        del self.prep_conc2
        del self.prep_conc2_tag
        del self.iso_volume
        del self.tt_a1_tag
        del self.tt_a2_tag
        del self.tt_b1_tag
        del self.tt_b2_tag
        del self.tt_mock_tag
        del self.req_vol1
        del self.req_vol1_tag
        del self.req_vol2
        del self.req_vol2_tag
        del self.req_vol_mock
        del self.req_vol_mock_tag
        del self.parent_well1
        del self.parent_tag1
        del self.parent_well2
        del self.parent_tag2
        del self.a1_pp
        del self.a2_pp
        del self.b1_pp
        del self.b2_pp
        del self.d1_pp

    def __create_prep_positions(self, rack_pos, parent_well=None):
        if rack_pos.row_index == 0:
            pool = self._get_pool(self.mdp1)
            barcode = self.barcode1
        else:
            pool = self._get_pool(self.mdp2)
            barcode = self.barcode2
        if rack_pos.column_index == 0:
            prep_conc = self.prep_conc2
            req_vol = self.req_vol2
        else:
            prep_conc = self.prep_conc1
            req_vol = self.req_vol1
        tt = TransferTarget(rack_position=rack_pos,
                            transfer_volume=self.iso_volume)
        pp = PrepIsoPosition(rack_position=rack_pos,
                             molecule_design_pool=pool,
                             position_type=FIXED_POSITION_TYPE,
                             stock_tube_barcode=barcode,
                             stock_rack_barcode=self.rack_barcode,
                             prep_concentration=prep_conc,
                             required_volume=req_vol,
                             transfer_targets=[tt],
                             parent_well=parent_well)
        return pp

    def __create_test_layout(self):
        pl = PrepIsoLayout(shape=self.shape)
        pl.add_position(self.a1_pp)
        pl.add_position(self.a2_pp)
        pl.add_position(self.b1_pp)
        pl.add_position(self.b2_pp)
        pl.add_position(self.d1_pp)
        return pl

    def test_init(self):
        pl = PrepIsoLayout(shape=self.shape)
        self.assert_is_not_none(pl)
        self.assert_equal(pl.shape, self.shape)
        self.assert_equal(len(pl), 0)

    def test_add_position(self):
        pl = PrepIsoLayout(shape=self.shape)
        self.assert_equal(len(pl), 0)
        pl.add_position(self.b2_pp)
        self.assert_equal(len(pl), 1)
        iso_pos = IsoPosition(rack_position=self.b1_pos)
        self.assert_raises(TypeError, pl.add_position, iso_pos)
        tt = TransferTarget(rack_position=self.c3_pos, transfer_volume=5)
        c3_pp = PrepIsoPosition(rack_position=self.c3_pos,
                    molecule_design_pool=self.b2_pp.molecule_design_pool,
                    position_type=FIXED_POSITION_TYPE,
                    prep_concentration=self.b2_pp.prep_concentration,
                    required_volume=self.req_vol1,
                    transfer_targets=[tt])
        self.assert_raises(ValueError, pl.add_position, c3_pp)
        shape_384 = self._get_entity(IRackShape, '16x24')
        pl.shape = shape_384
        pl.add_position(c3_pp)
        c3_pp.prep_concentration = (self.b2_pp.prep_concentration * 2)
        c3_pp.add_transfer_target(self.b2_pp.transfer_targets[0])
        self.assert_raises(ValueError, pl.add_position, c3_pp)

    def test_get_working_position(self):
        pl = self.__create_test_layout()
        self.assert_equal(pl.get_working_position(self.a1_pos), self.a1_pp)
        self.assert_is_none(pl.get_working_position(self.c3_pos))

    def test_equality(self):
        pl1 = self.__create_test_layout()
        pl2 = self.__create_test_layout()
        pl3 = PrepIsoLayout(shape=self.shape)
        tt = TransferTarget(rack_position=self.c3_pos, transfer_volume=4)
        c3_pp = PrepIsoPosition(rack_position=self.c3_pos,
                                molecule_design_pool=self.mdp1,
                                position_type=FIXED_POSITION_TYPE,
                                prep_concentration=(self.prep_conc1 * 3),
                                required_volume=self.req_vol1,
                                transfer_targets=[tt])
        pl3.add_position(c3_pp)
        self.assert_equal(pl1, pl2)
        self.assert_not_equal(pl1, pl3)

    def test_get_tags(self):
        pl = self.__create_test_layout()
        tags = [self.mdp1_tag, self.mdp2_tag, self.fixed_tag, self.barcode1_tag,
                self.barcode2_tag, self.prep_conc1_tag, self.tt_a1_tag,
                self.tt_a2_tag, self.tt_b1_tag, self.tt_b2_tag,
                self.prep_conc2_tag, self.req_vol1_tag, self.req_vol2_tag,
                self.parent_tag1, self.parent_tag2, self.rack_barcode_tag,
                self.md_mock_tag, self.tt_mock_tag,
                self.req_vol_mock_tag, self.mock_type_tag]
        tag_set = pl.get_tags()
        self._compare_tag_sets(tags, tag_set)

    def test_get_positions(self):
        pl = self.__create_test_layout()
        positions = [self.a1_pos, self.a2_pos, self.b1_pos, self.b2_pos,
                     self.d1_pos]
        pos_set = pl.get_positions()
        self._compare_pos_sets(positions, pos_set)

    def test_get_tags_for_position(self):
        pl = self.__create_test_layout()
        tags_a1 = [self.mdp1_tag, self.barcode1_tag, self.tt_a1_tag,
                   self.prep_conc2_tag, self.req_vol2_tag,
                   self.rack_barcode_tag, self.fixed_tag]
        tag_set_a1 = pl.get_tags_for_position(self.a1_pos)
        self._compare_tag_sets(tags_a1, tag_set_a1)
        self.assert_false(self.mdp2_tag in tag_set_a1)

    def test_get_positions_for_tags(self):
        pl = self.__create_test_layout()
        pos_mdp1 = [self.a1_pos, self.a2_pos]
        pos_set_mdp1 = pl.get_positions_for_tag(self.mdp1_tag)
        self._compare_pos_sets(pos_mdp1, pos_set_mdp1)
        self.assert_false(self.b1_pos in pos_set_mdp1)

    def test_create_rack_layout(self):
        pl = self.__create_test_layout()
        rack_layout = pl.create_rack_layout()
        self.assert_is_not_none(rack_layout)
        self.assert_not_equal(pl, rack_layout)
        self.assert_equal(pl.shape, rack_layout.shape)
        trps_list = rack_layout.tagged_rack_position_sets
        self.assert_equal(len(trps_list), 10)
        self.assert_equal(set(pl.get_tags()), rack_layout.get_tags())
        self.assert_equal(set(pl.get_positions()), rack_layout.get_positions())
        self.assert_equal(set(pl.get_tags_for_position(self.a1_pos)),
                          rack_layout.get_tags_for_position(self.a1_pos))
        self.assert_equal(set(pl.get_positions_for_tag(self.mdp1_tag)),
                          rack_layout.get_positions_for_tag(self.mdp1_tag))

    def test_starting_well_uniqueness(self):
        pl = self.__create_test_layout()
        self.assert_true(pl.check_starting_well_uniqueness())
        self.b2_pp.parent_well = None
        self.assert_false(pl.check_starting_well_uniqueness())
        shape_384 = self._get_entity(IRackShape, '16x24')
        pl.shape = shape_384
        self.assert_true(pl.check_starting_well_uniqueness())

    def test_get_starting_wells(self):
        pl = self.__create_test_layout()
        exp_wells = {self.a1_pos : self.a1_pp, self.b1_pos : self.b1_pp,
                     self.d1_pos : self.d1_pp}
        starting_wells = pl.get_starting_wells()
        self.assert_equal(len(exp_wells), len(starting_wells))
        for pos, prep_pos in exp_wells.iteritems():
            self.assert_true(starting_wells.has_key(pos))
            self.assert_equal(starting_wells[pos], prep_pos)

    def test_get_hash_map(self):
        pl = self.__create_test_layout()
        exp_map = {self.a1_pp.hash_value : self.a1_pp,
                   self.a2_pp.hash_value : self.a2_pp,
                   self.b1_pp.hash_value : self.b1_pp,
                   self.b2_pp.hash_value : self.b2_pp,
                   self.d1_pp.hash_value : self.d1_pp}
        hash_map = pl.get_hash_map()
        self.assert_equal(len(hash_map), len(exp_map))
        for hash_value, prep_pos in exp_map.iteritems():
            self.assert_true(hash_map.has_key(hash_value))
            self.assert_equal(hash_map[hash_value], prep_pos)
        shape_384 = self._get_entity(IRackShape, '16x24')
        pl.shape = shape_384
        self.assert_is_none(pl.get_hash_map())

    def test_has_unconverted_floatings(self):
        pl1 = self.__create_test_layout()
        self.assert_false(pl1.has_unconverted_floatings())
        self.a1_pp.position_type = FLOATING_POSITION_TYPE
        pl2 = self.__create_test_layout()
        self.assert_false(pl2.has_unconverted_floatings())
        self.a1_pp.stock_tube_barcode = None
        pl3 = self.__create_test_layout()
        self.assert_true(pl3.has_unconverted_floatings())
        self.a1_pp.stock_tube_barcode = self.barcode1
        pl4 = self.__create_test_layout()
        self.assert_false(pl4.has_unconverted_floatings())

    def test_get_md_conc_map(self):
        pl = self.__create_test_layout()
        exp_map = {self.mdp1 : {self.prep_conc1 : self.a2_pp,
                               self.prep_conc2 : self.a1_pp},
                   self.mdp2 : {self.prep_conc1 : self.b2_pp,
                               self.prep_conc2 : self.b1_pp},
                   self.md_mock : {None : self.d1_pp}}
        mdp_conc_map = pl.get_md_pool_concentration_map()
        self.assert_equal(exp_map, mdp_conc_map)

    def test_get_supplier_map(self):
        self.b1_pp.position_type = FLOATING_POSITION_TYPE
        self.b2_pp.position_type = FLOATING_POSITION_TYPE
        pl = self.__create_test_layout()
        exp_map = {self.mdp1.id : IsoPosition.ANY_SUPPLIER_INDICATOR}
        pl_map = pl.get_supplier_map()
        self.assert_equal(exp_map, pl_map)
        self.b1_pp.position_type = FIXED_POSITION_TYPE
        self.b2_pp.position_type = FIXED_POSITION_TYPE
        supplier1 = Organization(name='supplier1', id= -1)
        supplier2 = Organization(name='supplier2', id= -2)
        self.a1_pp.set_supplier(supplier1)
        self.a2_pp.set_supplier(supplier1)
        self.b1_pp.set_supplier(supplier2)
        self.b1_pp.set_supplier(supplier2)
        pl = self.__create_test_layout()
        exp_map = {self.mdp1.id : supplier1.id,
                   self.mdp2.id : supplier2.id}
        pl_map = pl.get_supplier_map()
        self.assert_equal(exp_map, pl_map)

    def test_get_pool(self):
        pl = self.__create_test_layout()
        pm = pl.get_pools()
        self.assert_equal(len(pm), 2)
        for pool_id, md_pool in pm.iteritems():
            self.assert_equal(md_pool.id, pool_id)


class PrepIsoLayoutConverterTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.rack_layout = None
        self.log = TestingLog()
        self.shape = get_96_rack_shape()
        self.a1_pos = get_rack_position_from_label('A1')
        self.a2_pos = get_rack_position_from_label('A2')
        self.a3_pos = get_rack_position_from_label('A3')
        self.b1_pos = get_rack_position_from_label('B1')
        self.b2_pos = get_rack_position_from_label('B2')
        self.b3_pos = get_rack_position_from_label('B3')
        self.d1_pos = get_rack_position_from_label('D1')
        parameters = PrepIsoParameters
        self.transfer_domain = TransferParameters.DOMAIN
        self.mdp1_tag = Tag(parameters.DOMAIN, parameters.MOLECULE_DESIGN_POOL,
                            205200)
        self.mdp2_tag = Tag(parameters.DOMAIN, parameters.MOLECULE_DESIGN_POOL,
                            1056000)
        self.fixed_tag = Tag(parameters.DOMAIN, parameters.POS_TYPE,
                             FIXED_POSITION_TYPE)
        self.md_mock_tag = Tag(parameters.DOMAIN,
                            parameters.MOLECULE_DESIGN_POOL, MOCK_POSITION_TYPE)
        self.mock_type_tag = Tag(parameters.DOMAIN, parameters.POS_TYPE,
                                 MOCK_POSITION_TYPE)
        self.barcode1_tag = Tag(parameters.DOMAIN,
                                parameters.STOCK_TUBE_BARCODE, '10111')
        self.barcode2_tag = Tag(parameters.DOMAIN,
                                parameters.STOCK_TUBE_BARCODE, '10222')
        self.rack_barcode_tag = Tag(parameters.DOMAIN,
                                    parameters.STOCK_RACK_BARCODE, '09539999')
        self.prep_conc1_tag = Tag(parameters.DOMAIN,
                                 parameters.PREP_CONCENTRATION, '2')
        self.prep_conc2_tag = Tag(parameters.DOMAIN,
                                 parameters.PREP_CONCENTRATION, '1')
        self.prep_conc_mock_tag = Tag(parameters.DOMAIN,
                                 parameters.PREP_CONCENTRATION,
                                 PrepIsoPosition.NONE_REPLACER)
        self.req_vol1_tag = Tag(parameters.DOMAIN, parameters.REQUIRED_VOLUME,
                                '60')
        self.req_vol2_tag = Tag(parameters.DOMAIN, parameters.REQUIRED_VOLUME,
                                '40')
        self.req_vol_mock_tag = Tag(parameters.DOMAIN,
                                parameters.REQUIRED_VOLUME, '30')
        self.parent_well_a = self.a1_pos
        self.parent_a_tag = Tag(parameters.DOMAIN, parameters.PARENT_WELL,
                                self.parent_well_a.label)
        self.parent_well_b = self.b1_pos
        self.parent_b_tag = Tag(parameters.DOMAIN, parameters.PARENT_WELL,
                                self.parent_well_b.label)
        self.iso_volume = 10
        self.tt_a1_tag = Tag(self.transfer_domain,
                             TransferParameters.TARGET_WELLS, 'A1:10-A3:10')
        self.tt_a2_tag = Tag(self.transfer_domain,
                             TransferParameters.TARGET_WELLS, 'A2:10')
        self.tt_b1_tag = Tag(self.transfer_domain,
                             TransferParameters.TARGET_WELLS, 'B1:10-B3:10')
        self.tt_b2_tag = Tag(self.transfer_domain,
                             TransferParameters.TARGET_WELLS, 'B2:10')
        self.tt_mock_tag = Tag(self.transfer_domain,
                               TransferParameters.TARGET_WELLS, 'D1:20')
        self.other_tag = Tag('test', 'unimportant', 'stuff')

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.rack_layout
        del self.log
        del self.shape
        del self.a1_pos
        del self.a2_pos
        del self.a3_pos
        del self.b1_pos
        del self.b2_pos
        del self.b3_pos
        del self.d1_pos
        del self.transfer_domain
        del self.mdp1_tag
        del self.mdp2_tag
        del self.md_mock_tag
        del self.barcode1_tag
        del self.barcode2_tag
        del self.rack_barcode_tag
        del self.prep_conc1_tag
        del self.prep_conc2_tag
        del self.prep_conc_mock_tag
        del self.req_vol1_tag
        del self.req_vol2_tag
        del self.req_vol_mock_tag
        del self.parent_well_a
        del self.parent_a_tag
        del self.parent_well_b
        del self.parent_b_tag
        del self.iso_volume
        del self.tt_a1_tag
        del self.tt_a2_tag
        del self.tt_b1_tag
        del self.tt_b2_tag
        del self.tt_mock_tag
        del self.other_tag

    def _create_tool(self):
        self.tool = PrepIsoLayoutConverter(rack_layout=self.rack_layout,
                                           log=self.log)

    def __create_test_layout(self):
        trp_sets = []
        mdp1_tags = [self.mdp1_tag, self.barcode1_tag]
        mdp1_pos = [self.a1_pos, self.a2_pos]
        mdp1_trps = self._create_test_trp_set(mdp1_tags, mdp1_pos)
        trp_sets.append(mdp1_trps)
        mdp2_tags = [self.mdp2_tag, self.barcode2_tag]
        mdp2_pos = [self.b1_pos, self.b2_pos]
        mdp2_trps = self._create_test_trp_set(mdp2_tags, mdp2_pos)
        trp_sets.append(mdp2_trps)
        conc1_tags = [self.prep_conc1_tag, self.req_vol1_tag]
        conc1_pos = [self.a1_pos, self.b1_pos]
        conc1_trps = self._create_test_trp_set(conc1_tags,
                                                            conc1_pos)
        trp_sets.append(conc1_trps)
        conc2_tags = [self.prep_conc2_tag, self.req_vol2_tag]
        conc2_pos = [self.a2_pos, self.b2_pos]
        conc2_trps = self._create_test_trp_set(conc2_tags,
                                                            conc2_pos)
        trp_sets.append(conc2_trps)
        a1_trps = self._create_test_trp_set([self.tt_a1_tag],
                                                         [self.a1_pos])
        trp_sets.append(a1_trps)
        a2_trps = self._create_test_trp_set(
                            [self.tt_a2_tag, self.parent_a_tag], [self.a2_pos])
        trp_sets.append(a2_trps)
        b1_trps = self._create_test_trp_set([self.tt_b1_tag],
                                                         [self.b1_pos])
        trp_sets.append(b1_trps)
        b2_trps = self._create_test_trp_set(
                            [self.tt_b2_tag, self.parent_b_tag], [self.b2_pos])
        trp_sets.append(b2_trps)
        d1_tags = [self.md_mock_tag, self.prep_conc_mock_tag,
                   self.req_vol_mock_tag, self.tt_mock_tag, self.mock_type_tag]
        d1_trps = self._create_test_trp_set(d1_tags, [self.d1_pos])
        trp_sets.append(d1_trps)
        all_tags = [self.other_tag, self.rack_barcode_tag, self.fixed_tag]
        all_pos = [self.a1_pos, self.a2_pos, self.b1_pos, self.b2_pos]
        all_trps = self._create_test_trp_set(all_tags, all_pos)
        trp_sets.append(all_trps)
        self.rack_layout = RackLayout(shape=self.shape,
                                      tagged_rack_position_sets=trp_sets)

    def __test_and_expect_errors(self, msg=None):
        self.__create_test_layout()
        self._test_and_expect_errors(msg)

    def test_result(self):
        self.__create_test_layout()
        self._create_tool()
        prep_layout = self.tool.get_result()
        self.assert_is_not_none(prep_layout)
        self.assert_equal(len(prep_layout), 5)
        tags = [self.mdp1_tag, self.mdp2_tag, self.fixed_tag, self.barcode1_tag,
                self.barcode2_tag, self.prep_conc1_tag, self.prep_conc2_tag,
                self.req_vol1_tag, self.req_vol2_tag, self.parent_a_tag,
                self.parent_b_tag, self.tt_a1_tag, self.tt_a2_tag,
                self.tt_b1_tag, self.tt_b2_tag, self.rack_barcode_tag,
                self.md_mock_tag, self.tt_mock_tag, self.req_vol_mock_tag,
                self.mock_type_tag]
        tag_set = prep_layout.get_tags()
        self._compare_tag_sets(tags, tag_set)
        positions = [self.a1_pos, self.a2_pos, self.b1_pos, self.b2_pos,
                     self.d1_pos]
        pos_set = prep_layout.get_positions()
        self._compare_pos_sets(positions, pos_set)
        a1_tags = [self.mdp1_tag, self.barcode1_tag, self.tt_a1_tag,
                   self.prep_conc1_tag, self.req_vol1_tag, self.fixed_tag,
                   self.rack_barcode_tag]
        a1_tag_set = prep_layout.get_tags_for_position(self.a1_pos)
        self._compare_tag_sets(a1_tags, a1_tag_set)
        prep_conc2_positions = [self.a2_pos, self.b2_pos]
        prep_conc2_pos_set = prep_layout.get_positions_for_tag(
                                                            self.prep_conc2_tag)
        self._compare_pos_sets(prep_conc2_positions, prep_conc2_pos_set)

    def test_invalid_rack_layout(self):
        self._create_tool()
        pl = self.tool.get_result()
        self.assert_is_none(pl)
        self._check_error_messages('rack layout must be a RackLayout')

    def test_double_specification(self):
        self.other_tag.predicate = PrepIsoParameters.PARENT_WELL
        self.other_tag.value = 'C3'
        self.__test_and_expect_errors('specified multiple times')

    def test_invalid_target_info(self):
        self.tt_a2_tag.value = 'A2(10)'
        self.__test_and_expect_errors('invalid target position descriptions')

    def test_duplicate_target(self):
        self.tt_a2_tag.value = 'A1:10-A2:10'
        self.__test_and_expect_errors('duplicate target positions')

    def test_missing_molecule_design(self):
        self.mdp1_tag = Tag('more', 'unimportant', 'data')
        self.__test_and_expect_errors('molecule design pool IDs for the ' \
                                      'following rack positions are missing')

    def test_invalid_molecule_design_pool(self):
        self.mdp1_tag.value = 12.3
        self.__test_and_expect_errors('Some molecule design pool IDs could ' \
                                      'not be found in the DB')
        self.mdp1_tag.value = 9999999
        self.__test_and_expect_errors('Some molecule design pool IDs could ' \
                                      'not be found in the DB')

    def test_missing_type(self):
        self.fixed_tag = self.other_tag
        self.__test_and_expect_errors('The position type for the following ' \
                                      'positions are missing')

    def test_inconsistent_types(self):
        self.mock_type_tag = self.fixed_tag
        self.__test_and_expect_errors('The mock positions both molecule ' \
                    'design pool ID and position type must be "mock". The ' \
                    'types for the following positions are inconsistent')

    def test_missing_prep_conc(self):
        self.prep_conc1_tag = Tag('more', 'unimportant', 'data')
        self.__test_and_expect_errors('not have a preparation concentration')

    def test_invalid_prep_concentration(self):
        self.prep_conc1_tag.value = '4,3'
        self.__test_and_expect_errors('invalid preparation concentrations')

    def test_missing_required_volume(self):
        self.req_vol1_tag = Tag('more', 'unimportant', 'data')
        self.__test_and_expect_errors('not have a required volume')

    def test_invalid_required_volume(self):
        self.req_vol1_tag.value = '4,3'
        self.__test_and_expect_errors('invalid required volume')

    def test_invalid_parent_well(self):
        self.parent_a_tag.value = 'no_well'
        self.__test_and_expect_errors('invalid parent well labels')


class PrepIsoRackSectorToolsTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.log = TestingLog()
        self.prep_layout = None
        self.rack_shape = get_384_rack_shape()
        self.number_sectors = 4
        # value: sector index, md set, conc, req vol
        self.position_data = dict(
         A4=(1, 'md_1', 10, 30), B3=(2, None), B4=(3, 'md_1', 20, 45),
         A6=(1, 'md_3', 10, 30), B5=(2, 'mock', 30, 30), B6=(3, 'md_3', 20, 45),
         C2=(1, 'md_5', 10, 30), D1=(2, 'md_6', 30, 30), D2=(3, 'md_5', 20, 45),
         E2=(1, 'md_9', 10, 30), F1=(2, 'md_9', 30, 30), F2=(3, 'md_9', 20, 45))
        self.one_sector_data = dict(A4=(1, 'md_1', 10, 30), B3=(2, None),
                        B4=(3, 'md_1', 10, 30),
                        A6=(1, 'md_3', 10, 30), B5=(2, 'md_4', 10, 30),
                        B6=(3, 'md_3', 10, 30))

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.log
        del self.prep_layout
        del self.rack_shape
        del self.number_sectors
        del self.position_data
        del self.one_sector_data

    def _continue_setup(self):
        self.__create_prep_layout()
        self._create_tool()

    def __create_prep_layout(self):
        self.prep_layout = PrepIsoLayout(shape=self.rack_shape)
        for pos_label, pos_data in self.position_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            pool = pos_data[1]
            if pool is None: continue
            prep_conc = pos_data[2]
            req_vol = pos_data[3]
            tt = TransferTarget(rack_position=rack_pos, transfer_volume=10)
            pos_type = FIXED_POSITION_TYPE
            if pool == MOCK_POSITION_TYPE: pos_type = pool
            prep_pos = PrepIsoPosition(rack_position=rack_pos,
                                       molecule_design_pool=pool,
                                       position_type=pos_type,
                                       required_volume=req_vol,
                                       transfer_targets=[tt],
                                       prep_concentration=prep_conc)
            self.prep_layout.add_position(prep_pos)

    def _test_invalid_prep_layout(self):
        self._continue_setup()
        self.prep_layout = self.prep_layout.create_rack_layout()
        self._test_and_expect_errors('must be a PrepIsoLayout object')

    def _test_invalid_number_sectors(self):
        self._continue_setup()
        self.number_sectors = '4'
        self._test_and_expect_errors('The number of sectors must be a int')


class PrepIsoValueDeterminerTestCase(PrepIsoRackSectorToolsTestCase):

    def set_up(self):
        PrepIsoRackSectorToolsTestCase.set_up(self)
        self.attribute_name = 'prep_concentration'

    def tear_down(self):
        PrepIsoRackSectorToolsTestCase.tear_down(self)
        del self.attribute_name

    def _create_tool(self):
        self.tool = PrepIsoValueDeterminer(prep_layout=self.prep_layout,
                    attribute_name=self.attribute_name, log=self.log,
                    number_sectors=self.number_sectors)

    def test_result(self):
        self._continue_setup()
        sector_map = self.tool.get_result()
        self.assert_is_not_none(sector_map)
        self.assert_equal(len(sector_map), 4)
        self.assert_equal(sector_map[0], None)
        self.assert_equal(sector_map[1], 10)
        self.assert_equal(sector_map[2], 30)
        self.assert_equal(sector_map[3], 20)

    def test_result_1_conc(self):
        self.position_data = self.one_sector_data
        self._continue_setup()
        sector_map = self.tool.get_result()
        self.assert_equal(len(sector_map), 4)
        self.assert_equal(sector_map[0], None)
        self.assert_equal(sector_map[1], 10)
        self.assert_equal(sector_map[2], 10)
        self.assert_equal(sector_map[3], 10)
        self.number_sectors = 1
        self._create_tool()
        sector_map = self.tool.get_result()
        self.assert_equal(len(sector_map), 1)
        self.assert_equal(sector_map[0], 10)

    def test_invalid_prep_layout(self):
        self._test_invalid_prep_layout()

    def test_invalid_number_sectors(self):
        self._test_invalid_number_sectors()

    def test_invalid_attribute_name(self):
        self._continue_setup()
        self.attribute_name = [self.attribute_name]
        self._test_and_expect_errors('The attribute name must be a str object')

    def test_unknown_attribute_name(self):
        self._continue_setup()
        self.attribute_name = 'molecule_design'
        self._test_and_expect_errors('Unknown attribute')

    def test_more_than_one_value(self):
        self._continue_setup()
        self.attribute_name = 'molecule_design_pool_id'
        self._test_and_expect_errors('There is more than one value for sector')


class PrepIsoAssociatorTestCase(PrepIsoRackSectorToolsTestCase):

    def _create_tool(self):
        self.tool = PrepIsoRackSectorAssociator(prep_layout=self.prep_layout,
                            log=self.log, number_sectors=self.number_sectors)

    def test_result(self):
        self._continue_setup()
        associated_sectors = self.tool.get_result()
        self.assert_is_not_none(associated_sectors)
        exp_result = [[1, 3], [2]]
        self.assert_equal(len(exp_result), len(associated_sectors))
        for association in exp_result:
            self.assert_true(association in associated_sectors)

    def test_invalid_prep_layout(self):
        self._test_invalid_prep_layout()

    def test_invalid_number_sectors(self):
        self._test_invalid_number_sectors()

    def test_inconsistent_rack_sectors(self):
        self.position_data['C2'] = (1, 'md_5', 40, 30)
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to determine rack ' \
                                     'sector concentrations')

    def test_inconsistent_molecule_designs(self):
        self.position_data['C2'] = (1, 'md_7', 10, 30)
        self._continue_setup()
        self._test_and_expect_errors('The molecule design pools in the ' \
                                     'different quadrants are not consistent')


class PrepIsoAssociationDataTestCase(PrepIsoRackSectorToolsTestCase):

    def test_result_4(self):
        self._continue_setup()
        ad = PrepIsoAssociationData(preparation_layout=self.prep_layout,
                                    log=self.log)
        self.assert_equal(ad.number_sectors, 4)
        # check associated sectors
        associated_sectors = ad.associated_sectors
        self.assert_is_not_none(associated_sectors)
        exp_as = [[1, 3], [2]]
        self.assert_equal(len(exp_as), len(associated_sectors))
        for association in exp_as:
            self.assert_true(association in associated_sectors)
        # check sector concentrations
        sector_concentrations = ad.sector_concentrations
        exp_sc = {0 : None, 1 : 10, 2 : 30, 3 : 20}
        self.assert_equal(len(exp_sc), len(sector_concentrations))
        self.assert_equal(exp_sc, sector_concentrations)
        # check parent sectors
        parent_sectors = ad.parent_sectors
        exp_ps = {1 : 3, 2 : None, 3 : None}
        self.assert_equal(len(exp_ps), len(parent_sectors))
        self.assert_equal(exp_ps, parent_sectors)
        # check required volumes
        sector_req_volume = ad.sector_req_volumes
        exp_srv = {0 : None, 1 : 30, 2: 30, 3 : 45}
        self.assert_equal(len(sector_req_volume), len(exp_srv))
        self.assert_equal(sector_req_volume, exp_srv)

    def test_result_1(self):
        self.position_data = self.one_sector_data
        self._continue_setup()
        ad = PrepIsoAssociationData(preparation_layout=self.prep_layout,
                                    log=self.log)
        self.assert_equal(ad.number_sectors, 1)
        # check associated sectors
        associated_sectors = ad.associated_sectors
        self.assert_is_not_none(associated_sectors)
        exp_as = [[0]]
        self.assert_equal(len(exp_as), len(associated_sectors))
        for association in exp_as:
            self.assert_true(association in associated_sectors)
        # check sector concentrations
        sector_concentrations = ad.sector_concentrations
        exp_sc = {0 : 10}
        self.assert_equal(len(exp_sc), len(sector_concentrations))
        self.assert_equal(exp_sc, sector_concentrations)
        # check parent sectors
        parent_sectors = ad.parent_sectors
        exp_ps = {0 : None}
        self.assert_equal(len(exp_ps), len(parent_sectors))
        self.assert_equal(exp_ps, parent_sectors)
        # check required volumes
        sector_req_volume = ad.sector_req_volumes
        exp_srv = {0 : 30}
        self.assert_equal(len(sector_req_volume), len(exp_srv))
        self.assert_equal(sector_req_volume, exp_srv)

    def test_failure(self):
        self.position_data['C2'] = (1, 'md_7', 10, 30)
        self._continue_setup()
        attrs = dict(preparation_layout=self.prep_layout, log=self.log)
        self.assert_raises(ValueError, PrepIsoAssociationData, **attrs)



class IsoControlRackPositionTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.a1_pos = get_rack_position_from_label('A1')
        self.a2_pos = get_rack_position_from_label('A2')
        self.pool = self._get_entity(IMoleculeDesignPool, '205200')
        self.tt1 = TransferTarget(rack_position=self.a1_pos, transfer_volume=1)
        self.tt2 = TransferTarget(rack_position=self.a2_pos, transfer_volume=2)
        self.transfer_targets = [self.tt1, self.tt2]
        self.mdp_tag = Tag('iso_control_rack', 'molecule_design_pool_id',
                           '205200')
        self.tt_tag = Tag('sample_transfer', 'target_wells',
                          'A1:1-A2:2')
        self.init_data = dict(rack_position=self.a1_pos,
                              molecule_design_pool=self.pool,
                              transfer_targets=self.transfer_targets)

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.a1_pos
        del self.a2_pos
        del self.pool
        del self.tt1
        del self.tt2
        del self.transfer_targets
        del self.mdp_tag
        del self.tt_tag
        del self.init_data

    def test_init(self):
        icpp = IsoControlRackPosition(**self.init_data)
        self.assert_is_not_none(icpp)
        check_attributes(icpp, self.init_data)
        # errors
        self.init_data['molecule_design_pool'] = 1.3
        self.assert_raises(ValueError, IsoControlRackPosition, **self.init_data)
        self.init_data['molecule_design_pool'] = 'md_1'
        self.assert_raises(ValueError, IsoControlRackPosition, **self.init_data)
        self.init_data['molecule_design_pool'] = UNTREATED_POSITION_TYPE
        self.assert_raises(ValueError, IsoControlRackPosition, **self.init_data)
        self.init_data['molecule_design_pool'] = self.pool
        self.init_data['transfer_targets'] = None
        self.assert_raises(ValueError, IsoControlRackPosition, **self.init_data)
        self.init_data['transfer_targets'] = dict()
        self.assert_raises(TypeError, IsoControlRackPosition, **self.init_data)
        self.init_data['transfer_targets'] = []
        self.assert_raises(ValueError, IsoControlRackPosition, **self.init_data)
        self.init_data['transfer_targets'] = [3]
        self.assert_raises(TypeError, IsoControlRackPosition, **self.init_data)

    def test_equality(self):
        icpp1 = IsoControlRackPosition(**self.init_data)
        icpp2 = IsoControlRackPosition(**self.init_data)
        self.init_data['rack_position'] = self.a2_pos
        icpp3 = IsoControlRackPosition(**self.init_data)
        self.init_data['rack_position'] = self.a1_pos
        other_pool = self._get_entity(IMoleculeDesignPool, '205202')
        self.init_data['molecule_design_pool'] = other_pool
        icpp4 = IsoControlRackPosition(**self.init_data)
        self.init_data['molecule_design_pool'] = self.pool
        self.init_data['transfer_targets'] = [self.tt1]
        icpp5 = IsoControlRackPosition(**self.init_data)
        self.assert_equal(icpp1, icpp2)
        self.assert_not_equal(icpp1, icpp3)
        self.assert_not_equal(icpp1, icpp4)
        self.assert_not_equal(icpp1, icpp5)
        self.assert_not_equal(icpp1, 1)

    def test_get_parameter_value(self):
        icrp = IsoControlRackPosition(**self.init_data)
        self.assert_equal(self.pool, icrp.get_parameter_value(
                                IsoControlRackParameters.MOLECULE_DESIGN_POOL))
        self.assert_equal(self.transfer_targets,
            icrp.get_parameter_value(IsoControlRackParameters.TARGET_WELLS))

    def test_get_parameter_tag(self):
        icpp = IsoControlRackPosition(**self.init_data)
        self.assert_equal(self.mdp_tag, icpp.get_parameter_tag(
                                IsoControlRackParameters.MOLECULE_DESIGN_POOL))
        self.assert_equal(self.tt_tag,
            icpp.get_parameter_tag(IsoControlRackParameters.TARGET_WELLS))

    def test_tag_set(self):
        icpp = IsoControlRackPosition(**self.init_data)
        exp_tags = [self.mdp_tag, self.tt_tag]
        tag_set = icpp.get_tag_set()
        self._compare_tag_sets(exp_tags, tag_set)


class IsoControlRackLayoutTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.a1_pos = get_rack_position_from_label('A1')
        self.a2_pos = get_rack_position_from_label('A2')
        self.a3_pos = get_rack_position_from_label('A3')
        self.b1_pos = get_rack_position_from_label('B1')
        self.b2_pos = get_rack_position_from_label('B2')
        self.b3_pos = get_rack_position_from_label('B3')
        self.mdp_1 = self._get_entity(IMoleculeDesignPool, '205200')
        self.mdp_2 = self._get_entity(IMoleculeDesignPool, '205201')
        domain = IsoControlRackParameters.DOMAIN
        self.mdp1_tag = Tag(domain,
                IsoControlRackParameters.MOLECULE_DESIGN_POOL, self.mdp_1.id)
        self.mdp2_tag = Tag(domain,
                IsoControlRackParameters.MOLECULE_DESIGN_POOL, self.mdp_2.id)
        self.tt_1_1 = TransferTarget(rack_position=self.a2_pos,
                                  transfer_volume=1)
        self.tt_1_2 = TransferTarget(rack_position=self.a3_pos,
                                  transfer_volume=2)
        self.tts1 = [self.tt_1_1, self.tt_1_2]
        self.tt_2_1 = TransferTarget(rack_position=self.b2_pos,
                                  transfer_volume=1)
        self.tt_2_2 = TransferTarget(rack_position=self.b3_pos,
                                  transfer_volume=2)
        self.tt2 = [self.tt_2_1, self.tt_2_2]
        self.tts1_tag = Tag(TransferParameters.DOMAIN,
                            IsoControlRackParameters.TARGET_WELLS,
                            'A2:1-A3:2')
        self.tts2_tag = Tag(TransferParameters.DOMAIN,
                            IsoControlRackParameters.TARGET_WELLS,
                            'B2:1-B3:2')
        self.a1_icpp = IsoControlRackPosition(rack_position=self.a1_pos,
                molecule_design_pool=self.mdp_1, transfer_targets=self.tts1)
        self.b1_icpp = IsoControlRackPosition(rack_position=self.b1_pos,
                molecule_design_pool=self.mdp_2, transfer_targets=self.tt2)

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.a1_pos
        del self.a2_pos
        del self.a3_pos
        del self.b1_pos
        del self.b2_pos
        del self.b3_pos
        del self.mdp_1
        del self.mdp_2
        del self.mdp1_tag
        del self.mdp2_tag
        del self.tt_1_1
        del self.tt_1_2
        del self.tts1
        del self.tt_2_1
        del self.tt_2_2
        del self.tt2
        del self.tts1_tag
        del self.tts2_tag
        del self.a1_icpp
        del self.b1_icpp

    def __create_test_layout(self):
        layout = IsoControlRackLayout()
        layout.add_position(self.a1_icpp)
        layout.add_position(self.b1_icpp)
        return layout

    def test_init(self):
        icpl = IsoControlRackLayout()
        self.assert_is_not_none(icpl)
        self.assert_equal(icpl.shape, get_96_rack_shape())
        self.assert_equal(len(icpl), 0)

    def test_add_position(self):
        icpl = IsoControlRackLayout()
        self.assert_equal(len(icpl), 0)
        icpl.add_position(self.a1_icpp)
        self.assert_equal(len(icpl), 1)
        iso_pos = IsoPosition.create_empty_position(self.b1_pos)
        self.assert_raises(TypeError, icpl.add_position, iso_pos)
        b1_icpp = IsoControlRackPosition(rack_position=self.b1_pos,
                molecule_design_pool=self.mdp_2, transfer_targets=self.tts1)
        self.assert_raises(ValueError, icpl.add_position, b1_icpp)

    def test_get_working_positions(self):
        icpl = IsoControlRackLayout()
        self.assert_is_none(icpl.get_working_position(self.a1_pos))
        icpl.add_position(self.a1_icpp)
        self.assert_equal(icpl.get_working_position(self.a1_pos), self.a1_icpp)

    def test_equality(self):
        icpl1 = self.__create_test_layout()
        icpl2 = self.__create_test_layout()
        icpl3 = IsoControlRackLayout()
        icpl3.add_position(self.a1_icpp)
        self.assert_equal(icpl1, icpl2)
        self.assert_not_equal(icpl1, icpl3)

    def test_get_tags(self):
        icpl = self.__create_test_layout()
        exp_tags = [self.mdp1_tag, self.mdp2_tag, self.tts1_tag, self.tts2_tag]
        tag_set = icpl.get_tags()
        self._compare_tag_sets(exp_tags, tag_set)

    def test_get_positions(self):
        icpl = self.__create_test_layout()
        positions = [self.a1_pos, self.b1_pos]
        pos_set = icpl.get_positions()
        self._compare_pos_sets(positions, pos_set)

    def test_get_position_for_tag(self):
        icpl = self.__create_test_layout()
        mdp1_positions = [self.a1_pos]
        mdp1_pos_set = icpl.get_positions_for_tag(self.mdp1_tag)
        self._compare_pos_sets(mdp1_positions, mdp1_pos_set)

    def test_get_tags_for_position(self):
        icpl = self.__create_test_layout()
        a1_tags = [self.mdp1_tag, self.tts1_tag]
        a1_tag_set = icpl.get_tags_for_position(self.a1_pos)
        self._compare_tag_sets(a1_tags, a1_tag_set)

    def test_create_rack_layout(self):
        icpl = self.__create_test_layout()
        rl = icpl.create_rack_layout()
        self.assert_equal(rl.shape, icpl.shape)
        self.assert_equal(len(rl.tagged_rack_position_sets), 2)
        self.assert_equal(rl.get_tags(), icpl.get_tags())
        self.assert_equal(rl.get_positions(), set(icpl.get_positions()))
        self.assert_equal(rl.get_tags_for_position(self.a1_pos),
                          set(icpl.get_tags_for_position(self.a1_pos)))
        self.assert_equal(rl.get_positions_for_tag(self.mdp1_tag),
                          set(icpl.get_positions_for_tag(self.mdp1_tag)))

    def test_duplicate_pool(self):
        icpl = self.__create_test_layout()
        dmd = icpl.get_duplicate_molecule_design_pools()
        self.assert_equal(len(dmd), 0)
        self.b1_icpp.molecule_design_pool = self.mdp_1
        dmd = icpl.get_duplicate_molecule_design_pools()
        self.assert_equal(len(dmd), 1)
        self.assert_equal([self.mdp_1], dmd)


class IsoControlRackLayoutConverterTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.shape = get_96_rack_shape()
        self.rack_layout = None
        self.log = TestingLog()
        self.a1_pos = get_rack_position_from_label('A1')
        self.b1_pos = get_rack_position_from_label('B1')
        self.c3_pos = get_rack_position_from_label('C3')
        self.mdp_1 = self._get_entity(IMoleculeDesignPool, '205200')
        self.mdp_2 = self._get_entity(IMoleculeDesignPool, '205201')
        domain = IsoControlRackParameters.DOMAIN
        self.mdp1_tag = Tag(domain,
                IsoControlRackParameters.MOLECULE_DESIGN_POOL, self.mdp_1.id)
        self.mdp2_tag = Tag(domain,
                IsoControlRackParameters.MOLECULE_DESIGN_POOL, self.mdp_2.id)
        self.tts1_tag = Tag(TransferParameters.DOMAIN,
                            IsoControlRackParameters.TARGET_WELLS,
                            'A2:1-A3:2')
        self.tts2_tag = Tag(TransferParameters.DOMAIN,
                            IsoControlRackParameters.TARGET_WELLS,
                            'B2:1-B3:2')
        self.other_tag = Tag('some', 'unimportant', 'tag')

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.shape
        del self.rack_layout
        del self.log
        del self.a1_pos
        del self.b1_pos
        del self.c3_pos
        del self.mdp_1
        del self.mdp_2
        del self.mdp1_tag
        del self.mdp2_tag
        del self.tts1_tag
        del self.tts2_tag
        del self.other_tag

    def _create_tool(self):
        self.tool = IsoControlRackLayoutConverter(rack_layout=self.rack_layout,
                                                  log=self.log)

    def __test_and_expect_errors(self, msg=None):
        self.__create_test_layout()
        self._test_and_expect_errors(msg)

    def __create_test_layout(self):
        trp_sets = []
        mdp1_positions = [self.a1_pos]
        mdp1_tags = [self.mdp1_tag, self.tts1_tag]
        mdp1_trps = self._create_test_trp_set(mdp1_tags, mdp1_positions)
        trp_sets.append(mdp1_trps)
        mdp2_positions = [self.b1_pos]
        mdp2_tags = [self.mdp2_tag, self.tts2_tag]
        mdp2_trps = self._create_test_trp_set(mdp2_tags, mdp2_positions)
        trp_sets.append(mdp2_trps)
        all_positions = [self.a1_pos, self.b1_pos]
        all_tags = [self.other_tag]
        all_trps = self._create_test_trp_set(all_tags, all_positions)
        trp_sets.append(all_trps)
        self.rack_layout = RackLayout(shape=self.shape,
                                      tagged_rack_position_sets=trp_sets)

    def test_result(self):
        self.__create_test_layout()
        self._create_tool()
        icpl = self.tool.get_result()
        self.assert_is_not_none(icpl)
        tags = [self.mdp1_tag, self.mdp2_tag, self.tts1_tag, self.tts2_tag]
        tag_set = icpl.get_tags()
        self._compare_tag_sets(tags, tag_set)
        positions = [self.a1_pos, self.b1_pos]
        pos_set = icpl.get_positions()
        self._compare_pos_sets(positions, pos_set)
        a1_tags = [self.mdp1_tag, self.tts1_tag]
        a1_tag_set = icpl.get_tags_for_position(self.a1_pos)
        self._compare_tag_sets(a1_tags, a1_tag_set)
        mdp1_positions = [self.a1_pos]
        mdp1_pos_set = icpl.get_positions_for_tag(self.mdp1_tag)
        self._compare_pos_sets(mdp1_positions, mdp1_pos_set)
        tt1 = TransferTarget(rack_position=get_rack_position_from_label('A2'),
                             transfer_volume=1)
        tt2 = TransferTarget(rack_position=get_rack_position_from_label('A3'),
                             transfer_volume=2)
        a1_icpp = IsoControlRackPosition(rack_position=self.a1_pos,
                            molecule_design_pool=self.mdp_1,
                            transfer_targets=[tt1, tt2])
        self.assert_equal(icpl.get_working_position(self.a1_pos), a1_icpp)

    def test_invalid_rack_layout(self):
        self._create_tool()
        icpl = self.tool.get_result()
        self.assert_is_none(icpl)
        self._check_error_messages('rack layout must be a RackLayout')

    def test_double_specification(self):
        self.other_tag = Tag(IsoControlRackParameters.DOMAIN,
                             IsoControlRackParameters.MOLECULE_DESIGN_POOL,
                             '40')
        self.__test_and_expect_errors('specified multiple times')

    def test_missing_molecule_design_pool(self):
        self.mdp1_tag = self.other_tag
        self.__test_and_expect_errors('The following positions to not have ' \
                                      'a molecule design pool ID')

    def test_unknown_molecule_design(self):
        self.mdp1_tag.value = 'default'
        self.__test_and_expect_errors('Some molecule design pool IDs could ' \
                                      'not be found in the DB')

    def test_missing_transfer_targets(self):
        self.tts1_tag = self.other_tag
        self.__test_and_expect_errors('The following rack position do not ' \
                                      'have a transfer target')

    def test_duplicate_transfer_targets(self):
        self.tts2_tag = self.tts1_tag
        self.__test_and_expect_errors('There are duplicate target positions')

    def test_invalid_transfer_target(self):
        self.tts1_tag.value = 'A1'
        self.__test_and_expect_errors('invalid target position descriptions')

    def test_molecule_design_uniqueness(self):
        self.mdp2_tag = self.mdp1_tag
        self.__test_and_expect_errors()


class RequestedStockSampleTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.a1_pos = get_rack_position_from_label('A1')
        self.pool = self._get_entity(IMoleculeDesignPool, '205200')
        self.stock_tube_barcode = '01'
        self.stock_rack_barcode = '02'
        self.iso_concentration = 10000
        self.pp = PrepIsoPosition(rack_position=self.a1_pos,
                             molecule_design_pool=self.pool,
                             position_type=FIXED_POSITION_TYPE,
                             required_volume=10,
                             transfer_targets=None,
                             prep_concentration=self.iso_concentration,
                             parent_well=None,
                             stock_tube_barcode=self.stock_tube_barcode,
                             stock_rack_barcode=self.stock_rack_barcode)
        self.attrs = dict(pool=self.pool,
                          stock_tube_barcode=self.stock_tube_barcode,
                          stock_rack_barcode=self.stock_rack_barcode,
                          tube_candidate=None,
                          stock_concentration=50000)

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.a1_pos
        del self.pool
        del self.stock_tube_barcode
        del self.stock_rack_barcode
        del self.iso_concentration
        del self.pp
        del self.attrs

    def test_from_prep_pos(self):
        rss = RequestedStockSample.from_prep_pos(self.pp)
        self.assert_is_not_none(rss)
        self.attrs['target_position'] = self.a1_pos
        self.attrs['take_out_volume'] = 2
        check_attributes(rss, self.attrs)

    def test_from_control_pos(self):
        a2_pos = get_rack_position_from_label('A2')
        take_out_volume = self.pp.get_stock_takeout_volume()
        tt = TransferTarget(rack_position=a2_pos,
                            transfer_volume=take_out_volume)
        control_pos = IsoControlRackPosition(rack_position=a2_pos,
                    molecule_design_pool=self.pool,
                    transfer_targets=[tt])
        rss = RequestedStockSample.from_control_pos(control_pos=control_pos,
                    prep_pos=self.pp, number_isos=2)
        self.assert_is_not_none(rss)
        self.attrs['target_position'] = a2_pos
        self.attrs['take_out_volume'] = take_out_volume * 2
        check_attributes(rss, self.attrs)
