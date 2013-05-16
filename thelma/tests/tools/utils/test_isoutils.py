"""
Testing ISO utility classes.

AAB
"""
from everest.testing import check_attributes
from thelma.automation.tools.semiconstants import get_384_rack_shape
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.utils.base import EMPTY_POSITION_TYPE
from thelma.automation.tools.utils.base import FIXED_POSITION_TYPE
from thelma.automation.tools.utils.base import FLOATING_POSITION_TYPE
from thelma.automation.tools.utils.base import MOCK_POSITION_TYPE
from thelma.automation.tools.utils.base import UNTREATED_POSITION_TYPE
from thelma.automation.tools.utils.base import get_trimmed_string
from thelma.automation.tools.utils.iso import IsoAssociationData
from thelma.automation.tools.utils.iso import IsoLayout
from thelma.automation.tools.utils.iso import IsoLayoutConverter
from thelma.automation.tools.utils.iso import IsoParameters
from thelma.automation.tools.utils.iso import IsoPosition
from thelma.automation.tools.utils.iso import IsoRackSectorAssociator
from thelma.automation.tools.utils.iso import IsoValueDeterminer
from thelma.interfaces import IMoleculeDesignPool
from thelma.models.racklayout import RackLayout
from thelma.models.tagging import Tag
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase


class IsoParametersTestCase(ToolsAndUtilsTestCase):

    def test_get_position_type(self):
        self.assert_equal(IsoParameters.get_position_type(None),
                          EMPTY_POSITION_TYPE)
        self.assert_equal(IsoParameters.get_position_type('untreated'),
                          UNTREATED_POSITION_TYPE)
        self.assert_equal(IsoParameters.get_position_type('mock'),
                          MOCK_POSITION_TYPE)
        self.assert_equal(IsoParameters.get_position_type('MOCK'),
                          IsoParameters.MOCK_TYPE_VALUE)
        self.assert_equal(IsoParameters.get_position_type('md_1'),
                          FLOATING_POSITION_TYPE)
        pool = self._get_entity(IMoleculeDesignPool, '205200')
        self.assert_equal(IsoParameters.get_position_type(pool),
                          FIXED_POSITION_TYPE)
        self.assert_raises(ValueError, IsoParameters.get_position_type, 1)


class IsoPositionTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.rack_pos = get_rack_position_from_label('A1')
        self.empty_type_tag = Tag('iso', 'position_type', 'empty')
        self.fixed_type_tag = Tag('iso', 'position_type', 'fixed')
        self.mdp = self._get_entity(IMoleculeDesignPool, '205200')
        self.md_float = 'md_1'
        self.mock_md = 'mock'
        self.iso_concentration = 1
        self.iso_volume = 7.5
        self.concentration_tag = Tag('iso', 'iso_concentration', '1')
        self.volume_tag = Tag('iso', 'iso_volume', '7.5')
        self.supplier = self._create_organization(name='iso_test')
        self.supplier_tag = Tag('iso', 'supplier', 'iso_test')
        self.mdp_tag = Tag('iso', 'molecule_design_pool_id', '205200')
        self.empty_init_data = dict(rack_position=self.rack_pos,
                            molecule_design_pool=None,
                            iso_concentration=None,
                            iso_volume=None,
                            supplier=None)
        self.mock_init_data = dict(rack_position=self.rack_pos,
                            molecule_design_pool=IsoParameters.MOCK_TYPE_VALUE,
                            iso_concentration=None,
                            iso_volume=self.iso_volume,
                            supplier=None)
        self.floating_init_data = dict(rack_position=self.rack_pos,
                            molecule_design_pool=self.md_float,
                            iso_concentration=self.iso_concentration,
                            iso_volume=self.iso_volume,
                            supplier=None)
        self.fixed_init_data = dict(rack_position=self.rack_pos,
                            molecule_design_pool=self.mdp,
                            supplier=self.supplier,
                            iso_concentration=self.iso_concentration,
                            iso_volume=self.iso_volume)

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.rack_pos
        del self.empty_type_tag
        del self.fixed_type_tag
        del self.mdp
        del self.md_float
        del self.mock_md
        del self.iso_concentration
        del self.iso_volume
        del self.concentration_tag
        del self.volume_tag
        del self.supplier
        del self.supplier_tag
        del self.mdp_tag
        del self.empty_init_data
        del self.mock_init_data
        del self.floating_init_data
        del self.fixed_init_data

    def test_empty_pos_init(self):
        iso_pos = IsoPosition(**self.empty_init_data)
        check_attributes(iso_pos, self.empty_init_data)
        self.empty_init_data['iso_concentration'] = self.iso_concentration
        self.assert_raises(ValueError, IsoPosition, **self.empty_init_data)
        self.empty_init_data['iso_concentration'] = None
        self.empty_init_data['iso_volume'] = self.iso_volume
        self.assert_raises(ValueError, IsoPosition, **self.empty_init_data)
        self.empty_init_data['iso_volume'] = None
        self.empty_init_data['supplier'] = self.supplier
        self.assert_raises(ValueError, IsoPosition, **self.empty_init_data)

    def test_untreated_pos_init(self):
        self.empty_init_data['molecule_design_pool'] = UNTREATED_POSITION_TYPE
        iso_pos1 = IsoPosition(**self.empty_init_data)
        check_attributes(iso_pos1, self.empty_init_data)
        self.empty_init_data['iso_concentration'] = self.iso_concentration
        self.assert_raises(ValueError, IsoPosition, **self.empty_init_data)
        self.empty_init_data['iso_concentration'] = UNTREATED_POSITION_TYPE
        iso_pos2 = IsoPosition(**self.empty_init_data)
        check_attributes(iso_pos2, self.empty_init_data)
        self.empty_init_data['iso_concentration'] = IsoPosition.NONE_REPLACER
        iso_pos3 = IsoPosition(**self.empty_init_data)
        check_attributes(iso_pos3, self.empty_init_data)
        self.empty_init_data['iso_volume'] = self.iso_volume
        self.assert_raises(ValueError, IsoPosition, **self.empty_init_data)
        self.empty_init_data['iso_volume'] = UNTREATED_POSITION_TYPE
        iso_pos4 = IsoPosition(**self.empty_init_data)
        check_attributes(iso_pos4, self.empty_init_data)
        self.empty_init_data['iso_volume'] = IsoPosition.NONE_REPLACER
        iso_pos5 = IsoPosition(**self.empty_init_data)
        check_attributes(iso_pos5, self.empty_init_data)
        self.empty_init_data['iso_volume'] = None
        self.empty_init_data['supplier'] = self.supplier
        self.assert_raises(ValueError, IsoPosition, **self.empty_init_data)

    def test_mock_pos_init(self):
        iso_pos1 = IsoPosition(**self.mock_init_data)
        check_attributes(iso_pos1, self.mock_init_data)
        self.mock_init_data['iso_concentration'] = self.iso_concentration
        self.mock_init_data['iso_volume'] = None
        self.assert_raises(ValueError, IsoPosition, **self.mock_init_data)
        self.mock_init_data['iso_concentration'] = MOCK_POSITION_TYPE
        iso_pos2 = IsoPosition(**self.mock_init_data)
        check_attributes(iso_pos2, self.mock_init_data)
        self.mock_init_data['iso_concentration'] = IsoPosition.NONE_REPLACER
        iso_pos3 = IsoPosition(**self.mock_init_data)
        check_attributes(iso_pos3, self.mock_init_data)
        self.mock_init_data['iso_volume'] = 0
        self.assert_raises(ValueError, IsoPosition, **self.mock_init_data)
        self.mock_init_data['iso_volume'] = self.iso_volume
        self.mock_init_data['supplier'] = self.supplier
        self.assert_raises(ValueError, IsoPosition, **self.mock_init_data)

    def test_floating_pos_init(self):
        iso_pos1 = IsoPosition(**self.floating_init_data)
        check_attributes(iso_pos1, self.floating_init_data)
        self.floating_init_data['iso_concentration'] = None
        self.floating_init_data['iso_volume'] = None
        iso_pos2 = IsoPosition(**self.floating_init_data)
        check_attributes(iso_pos2, self.floating_init_data)
        self.floating_init_data['iso_volume'] = self.iso_volume
        self.floating_init_data['iso_concentration'] = 0
        self.assert_raises(ValueError, IsoPosition, **self.floating_init_data)
        self.floating_init_data['iso_concentration'] = self.iso_concentration
        self.floating_init_data['iso_volume'] = 0
        self.assert_raises(ValueError, IsoPosition, **self.floating_init_data)
        self.floating_init_data['iso_volume'] = self.iso_volume
        self.floating_init_data['supplier'] = self.supplier
        self.assert_raises(ValueError, IsoPosition, **self.floating_init_data)

    def test_fixed_pos_init(self):
        iso_pos1 = IsoPosition(**self.fixed_init_data)
        check_attributes(iso_pos1, self.fixed_init_data)
        self.fixed_init_data['molecule_design_pool'] = self.mdp.id
        self.assert_raises(ValueError, IsoPosition, **self.fixed_init_data)
        self.fixed_init_data['molecule_design_pool'] = self.mdp
        self.fixed_init_data['iso_concentration'] = None
        self.fixed_init_data['iso_volume'] = None
        iso_pos2 = IsoPosition(**self.fixed_init_data)
        check_attributes(iso_pos2, self.fixed_init_data)
        self.fixed_init_data['supplier'] = None
        iso_pos3 = IsoPosition(**self.fixed_init_data)
        check_attributes(iso_pos3, self.fixed_init_data)
        self.fixed_init_data['iso_volume'] = self.iso_volume
        self.fixed_init_data['iso_concentration'] = 0
        self.assert_raises(ValueError, IsoPosition, **self.fixed_init_data)
        self.fixed_init_data['iso_concentration'] = self.iso_concentration
        self.fixed_init_data['iso_volume'] = 0
        self.assert_raises(ValueError, IsoPosition, **self.fixed_init_data)
        self.fixed_init_data['iso_volume'] = self.iso_volume
        self.fixed_init_data['supplier'] = self.supplier.name
        self.assert_raises(TypeError, IsoPosition, **self.fixed_init_data)

    def test_number_conversion(self):
        fixed1 = IsoPosition(**self.fixed_init_data)
        self.fixed_init_data['iso_concentration'] = str(self.iso_concentration)
        self.fixed_init_data['iso_volume'] = str(self.iso_volume)
        fixed2 = IsoPosition(**self.fixed_init_data)
        self.assert_equal(fixed1, fixed2)

    def test_empty_pos_equality(self):
        b2_pos = get_rack_position_from_label('B2')
        empty_pos1 = IsoPosition(**self.empty_init_data)
        empty_pos2 = IsoPosition(**self.empty_init_data)
        self.empty_init_data['rack_position'] = b2_pos
        empty_pos3 = IsoPosition(**self.empty_init_data)
        self.assert_equal(empty_pos1, empty_pos2)
        self.assert_not_equal(empty_pos1, empty_pos3)
        self.assert_not_equal(empty_pos1, self.rack_pos)

    def test_non_empty_pos_equality(self):
        b2_pos = get_rack_position_from_label('B2')
        mock_pos = IsoPosition(**self.mock_init_data)
        float_pos = IsoPosition(**self.floating_init_data)
        fixed_pos1 = IsoPosition(**self.fixed_init_data)
        self.fixed_init_data['molecule_design_pool'] = self.mdp
        fixed_pos2 = IsoPosition(**self.fixed_init_data)
        self.fixed_init_data['rack_position'] = b2_pos
        fixed_pos3 = IsoPosition(**self.fixed_init_data)
        self.fixed_init_data['rack_position'] = self.rack_pos
        self.fixed_init_data['iso_concentration'] = (self.iso_concentration * 2)
        fixed_pos4 = IsoPosition(**self.fixed_init_data)
        self.fixed_init_data['iso_concentration'] = self.iso_concentration
        self.fixed_init_data['iso_volume'] = (self.iso_volume * 2)
        fixed_pos5 = IsoPosition(**self.fixed_init_data)
        self.fixed_init_data['iso_volume'] = self.iso_volume
        self.fixed_init_data['supplier'] = None
        fixed_pos6 = IsoPosition(**self.fixed_init_data)
        self.fixed_init_data['supplier'] = self.supplier
        self.assert_not_equal(mock_pos, float_pos)
        self.assert_not_equal(mock_pos, fixed_pos1)
        self.assert_not_equal(float_pos, fixed_pos1)
        self.assert_equal(fixed_pos1, fixed_pos2)
        self.assert_not_equal(fixed_pos1, fixed_pos3)
        self.assert_not_equal(fixed_pos1, fixed_pos4)
        self.assert_not_equal(fixed_pos1, fixed_pos5)
        self.assert_equal(fixed_pos1, fixed_pos6)
        self.assert_not_equal(fixed_pos1, self.rack_pos)

    def test_is_empty(self):
        empty_pos = IsoPosition(**self.empty_init_data)
        self.assert_true(empty_pos.is_empty)
        mock_pos = IsoPosition(**self.mock_init_data)
        self.assert_false(mock_pos.is_empty)
        float_pos = IsoPosition(**self.floating_init_data)
        self.assert_false(float_pos.is_empty)
        fixed_pos = IsoPosition(**self.fixed_init_data)
        self.assert_false(fixed_pos.is_empty)
        self.empty_init_data['molecule_design_pool'] = \
                                        IsoParameters.UNTREATED_TYPE_VALUE
        untreated_pos = IsoPosition(**self.empty_init_data)
        self.assert_true(untreated_pos.is_empty)

    def test_is_untreated(self):
        empty_pos = IsoPosition(**self.empty_init_data)
        self.assert_false(empty_pos.is_untreated)
        mock_pos = IsoPosition(**self.mock_init_data)
        self.assert_false(mock_pos.is_untreated)
        float_pos = IsoPosition(**self.floating_init_data)
        self.assert_false(float_pos.is_untreated)
        fixed_pos = IsoPosition(**self.fixed_init_data)
        self.assert_false(fixed_pos.is_untreated)
        self.empty_init_data['molecule_design_pool'] = \
                                        IsoParameters.UNTREATED_TYPE_VALUE
        untreated_pos = IsoPosition(**self.empty_init_data)
        self.assert_true(untreated_pos.is_empty)

    def test_is_mock(self):
        empty_pos = IsoPosition(**self.empty_init_data)
        self.assert_false(empty_pos.is_mock)
        mock_pos = IsoPosition(**self.mock_init_data)
        self.assert_true(mock_pos.is_mock)
        float_pos = IsoPosition(**self.floating_init_data)
        self.assert_false(float_pos.is_mock)
        fixed_pos = IsoPosition(**self.fixed_init_data)
        self.assert_false(fixed_pos.is_mock)

    def test_is_floating(self):
        empty_pos = IsoPosition(**self.empty_init_data)
        self.assert_false(empty_pos.is_floating)
        mock_pos = IsoPosition(**self.mock_init_data)
        self.assert_false(mock_pos.is_floating)
        float_pos = IsoPosition(**self.floating_init_data)
        self.assert_true(float_pos.is_floating)
        fixed_pos = IsoPosition(**self.fixed_init_data)
        self.assert_false(fixed_pos.is_floating)

    def test_is_fixed(self):
        empty_pos = IsoPosition(**self.empty_init_data)
        self.assert_false(empty_pos.is_fixed)
        mock_pos = IsoPosition(**self.mock_init_data)
        self.assert_false(mock_pos.is_fixed)
        float_pos = IsoPosition(**self.floating_init_data)
        self.assert_false(float_pos.is_fixed)
        fixed_pos = IsoPosition(**self.fixed_init_data)
        self.assert_true(fixed_pos.is_fixed)

    def test_molecule_design_pool_id_property(self):
        fixed_pos = IsoPosition(**self.fixed_init_data)
        self.assert_equal(fixed_pos.molecule_design_pool_id, self.mdp.id)
        float_pos = IsoPosition(**self.floating_init_data)
        self.assert_equal(float_pos.molecule_design_pool_id, self.md_float)
        mock_pos = IsoPosition(**self.mock_init_data)
        self.assert_equal(mock_pos.molecule_design_pool_id, MOCK_POSITION_TYPE)
        empty_pos = IsoPosition(**self.empty_init_data)
        self.assert_equal(empty_pos.molecule_design_pool_id, None)

    def test_empty_tag_set(self):
        exp_tags = [self.empty_type_tag]
        empty_pos = IsoPosition(**self.empty_init_data)
        tag_set = empty_pos.get_tag_set()
        self._compare_tag_sets(exp_tags, tag_set)

    def test_untreated_tag_set(self):
        exp_tags1 = [Tag('iso', 'position_type', 'untreated'),
                    Tag('iso', 'molecule_design_pool_id', 'untreated')]
        self.empty_init_data['molecule_design_pool'] = UNTREATED_POSITION_TYPE
        untreated_pos1 = IsoPosition(**self.empty_init_data)
        tag_set1 = untreated_pos1.get_tag_set()
        self._compare_tag_sets(exp_tags1, tag_set1)
        self.empty_init_data['iso_volume'] = IsoPosition.NONE_REPLACER
        self.empty_init_data['iso_concentration'] = UNTREATED_POSITION_TYPE
        exp_tags2 = exp_tags1 + [Tag('iso', 'iso_volume', 'None'),
                                 Tag('iso', 'iso_concentration', 'untreated')]
        untreated_pos2 = IsoPosition(**self.empty_init_data)
        tag_set2 = untreated_pos2.get_tag_set()
        self._compare_tag_sets(exp_tags2, tag_set2)

    def test_mock_tag_set(self):
        mock_type_tag = Tag('iso', 'position_type', 'mock')
        md_mock_tag = Tag('iso', 'molecule_design_pool_id', 'mock')
        mock_conc_tag = Tag('iso', 'iso_concentration', 'None')
        self.mock_init_data['iso_concentration'] = IsoPosition.NONE_REPLACER
        exp_mock_tags1 = [mock_type_tag, self.volume_tag, md_mock_tag,
                          mock_conc_tag]
        mock_pos1 = IsoPosition(**self.mock_init_data)
        mock_tag_set1 = mock_pos1.get_tag_set()
        self._compare_tag_sets(exp_mock_tags1, mock_tag_set1)
        exp_mock_tags2 = [mock_type_tag, md_mock_tag]
        self.mock_init_data['iso_concentration'] = None
        self.mock_init_data['iso_volume'] = None
        mock_pos2 = IsoPosition(**self.mock_init_data)
        mock_tag_set2 = mock_pos2.get_tag_set()
        self._compare_tag_sets(exp_mock_tags2, mock_tag_set2)

    def test_floating_tag_set(self):
        float_type_tag = Tag('iso', 'position_type', 'floating')
        md_float_tag = Tag('iso', 'molecule_design_pool_id', 'md_1')
        exp_float_tags1 = [float_type_tag, self.concentration_tag,
                         self.volume_tag, md_float_tag]
        float_pos1 = IsoPosition(**self.floating_init_data)
        float_tag_set1 = float_pos1.get_tag_set()
        self._compare_tag_sets(exp_float_tags1, float_tag_set1)
        exp_float_tags2 = [float_type_tag, md_float_tag]
        self.floating_init_data['iso_concentration'] = None
        self.floating_init_data['iso_volume'] = None
        float_pos2 = IsoPosition(**self.floating_init_data)
        float_tag_set2 = float_pos2.get_tag_set()
        self._compare_tag_sets(exp_float_tags2, float_tag_set2)

    def test_fixed_tag_set(self):
        exp_fixed_tags1 = [self.fixed_type_tag, self.concentration_tag,
                           self.volume_tag, self.mdp_tag, self.supplier_tag]
        fixed_pos1 = IsoPosition(**self.fixed_init_data)
        fixed_tag_set1 = fixed_pos1.get_tag_set()
        self._compare_tag_sets(exp_fixed_tags1, fixed_tag_set1)
        exp_fixed_tags2 = [self.fixed_type_tag, self.mdp_tag]
        self.fixed_init_data['iso_concentration'] = None
        self.fixed_init_data['iso_volume'] = None
        self.fixed_init_data['supplier'] = None
        fixed_pos2 = IsoPosition(**self.fixed_init_data)
        fixed_tag_set2 = fixed_pos2.get_tag_set()
        self._compare_tag_sets(exp_fixed_tags2, fixed_tag_set2)

    def test_get_parameter_value(self):
        empty_pos = IsoPosition(**self.empty_init_data)
        self.assert_equal(None,
            empty_pos.get_parameter_value(IsoParameters.MOLECULE_DESIGN_POOL))
        self.assert_equal(None,
            empty_pos.get_parameter_value(IsoParameters.ISO_VOLUME))
        self.assert_equal(None,
            empty_pos.get_parameter_value(IsoParameters.ISO_CONCENTRATION))
        self.assert_equal(None,
            empty_pos.get_parameter_value(IsoParameters.SUPPLIER))
        self.assert_equal(IsoParameters.EMPTY_TYPE_VALUE,
            empty_pos.get_parameter_value(IsoParameters.POS_TYPE))
        fixed_pos = IsoPosition(**self.fixed_init_data)
        self.assert_equal(self.mdp,
            fixed_pos.get_parameter_value(IsoParameters.MOLECULE_DESIGN_POOL))
        self.assert_equal(self.iso_volume,
            fixed_pos.get_parameter_value(IsoParameters.ISO_VOLUME))
        self.assert_equal(self.iso_concentration,
            fixed_pos.get_parameter_value(IsoParameters.ISO_CONCENTRATION))
        self.assert_equal(self.supplier,
            fixed_pos.get_parameter_value(IsoParameters.SUPPLIER))
        self.assert_equal(IsoParameters.FIXED_TYPE_VALUE,
            fixed_pos.get_parameter_value(IsoParameters.POS_TYPE))

    def test_get_parameter_tag(self):
        empty_pos = IsoPosition(**self.empty_init_data)
        self.assert_equal(Tag('iso', 'molecule_design_pool_id', 'None'),
                empty_pos.get_parameter_tag(IsoParameters.MOLECULE_DESIGN_POOL))
        self.assert_equal(Tag('iso', 'iso_volume', 'None'),
                empty_pos.get_parameter_tag(IsoParameters.ISO_VOLUME))
        self.assert_equal(Tag('iso', 'iso_concentration', 'None'),
                empty_pos.get_parameter_tag(IsoParameters.ISO_CONCENTRATION))
        self.assert_equal(Tag('iso', 'supplier', 'None'),
                empty_pos.get_parameter_tag(IsoParameters.SUPPLIER))
        self.assert_equal(self.empty_type_tag,
                empty_pos.get_parameter_tag(IsoParameters.POS_TYPE))
        fixed_pos = IsoPosition(**self.fixed_init_data)
        self.assert_equal(self.mdp_tag,
                fixed_pos.get_parameter_tag(IsoParameters.MOLECULE_DESIGN_POOL))
        self.assert_equal(self.volume_tag,
                fixed_pos.get_parameter_tag(IsoParameters.ISO_VOLUME))
        self.assert_equal(self.concentration_tag,
                fixed_pos.get_parameter_tag(IsoParameters.ISO_CONCENTRATION))
        self.assert_equal(self.supplier_tag,
                fixed_pos.get_parameter_tag(IsoParameters.SUPPLIER))
        self.assert_equal(self.fixed_type_tag,
                fixed_pos.get_parameter_tag(IsoParameters.POS_TYPE))

    def test_has_tag(self):
        fixed_pos = IsoPosition(**self.fixed_init_data)
        self.assert_true(fixed_pos.has_tag(self.mdp_tag))
        self.assert_false(fixed_pos.has_tag(self.empty_type_tag))

    def test_create_empty_pos_factory(self):
        empty_pos = IsoPosition.create_empty_position(self.rack_pos)
        check_attributes(empty_pos, self.empty_init_data)

    def test_create_mock_pos_factory(self):
        mock_pos = IsoPosition.create_mock_position(rack_position=self.rack_pos,
                                    iso_volume=self.iso_volume)
        check_attributes(mock_pos, self.mock_init_data)

    def test_create_untreated_pos_factory(self):
        untreated_pos = IsoPosition.create_untreated_position(
                                                    rack_position=self.rack_pos)
        self.empty_init_data['molecule_design_pool'] = UNTREATED_POSITION_TYPE
        self.empty_init_data['position_type'] = UNTREATED_POSITION_TYPE
        check_attributes(untreated_pos, self.empty_init_data)


class IsoLayoutTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.shape = get_96_rack_shape()
        self.a1_pos = get_rack_position_from_label('A1')
        self.a2_pos = get_rack_position_from_label('A2')
        self.b1_pos = get_rack_position_from_label('B1')
        self.b2_pos = get_rack_position_from_label('B2')
        self.c1_pos = get_rack_position_from_label('C1')
        self.DOMAIN = IsoParameters.DOMAIN
        self.empty_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                             EMPTY_POSITION_TYPE)
        self.fixed_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                             FIXED_POSITION_TYPE)
        self.iso_volume = 2
        self.volume_tag = Tag(IsoParameters.DOMAIN, IsoParameters.ISO_VOLUME,
                              get_trimmed_string(self.iso_volume))
        self.iso_concentration = 0.5
        self.concentration_tag = Tag(IsoParameters.DOMAIN,
                                     IsoParameters.ISO_CONCENTRATION,
                                     get_trimmed_string(self.iso_concentration))
        self.mdp1 = self._get_entity(IMoleculeDesignPool, '205200')
        self.mdp1_tag = Tag(IsoParameters.DOMAIN,
                           IsoParameters.MOLECULE_DESIGN_POOL,
                           get_trimmed_string(self.mdp1.id))
        self.mdp2 = self._get_entity(IMoleculeDesignPool, '205201')
        self.mdp2_tag = Tag(IsoParameters.DOMAIN,
                            IsoParameters.MOLECULE_DESIGN_POOL,
                            get_trimmed_string(self.mdp2.id))
        self.float_replacer = '%s%s' % (IsoParameters.FLOATING_INDICATOR,
                                        self.mdp1.id)
        self.float_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                             FLOATING_POSITION_TYPE)
        self.float_md_tag = Tag(self.DOMAIN, IsoParameters.MOLECULE_DESIGN_POOL,
                                self.float_replacer)
        self.untreated_tag = Tag(self.DOMAIN, IsoParameters.POS_TYPE,
                                 UNTREATED_POSITION_TYPE)
        self.untreated_md_tag = Tag(self.DOMAIN,
                                    IsoParameters.MOLECULE_DESIGN_POOL,
                                    UNTREATED_POSITION_TYPE)
        self.supplier = self._create_organization(name='iso_layout_test')
        self.supplier_tag = Tag(IsoParameters.DOMAIN, IsoParameters.SUPPLIER,
                                self.supplier.name)
        self.a1_ip = IsoPosition(rack_position=self.a1_pos,
                                 molecule_design_pool=self.mdp1,
                                 iso_volume=self.iso_volume,
                                 iso_concentration=self.iso_concentration,
                                 supplier=self.supplier)
        self.a2_ip = IsoPosition(rack_position=self.a2_pos,
                                 molecule_design_pool=self.mdp2,
                                 iso_volume=self.iso_volume,
                                 iso_concentration=self.iso_concentration,
                                 supplier=self.supplier)
        self.b1_ip = IsoPosition(rack_position=self.b1_pos)
        self.c1_ip = IsoPosition(rack_position=get_rack_position_from_label('C1'),
                      molecule_design_pool=UNTREATED_POSITION_TYPE)

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.shape
        del self.a1_pos
        del self.a2_pos
        del self.b1_pos
        del self.b2_pos
        del self.c1_pos
        del self.DOMAIN
        del self.empty_tag
        del self.fixed_tag
        del self.untreated_tag
        del self.untreated_md_tag
        del self.iso_volume
        del self.volume_tag
        del self.iso_concentration
        del self.concentration_tag
        del self.mdp1
        del self.mdp1_tag
        del self.mdp2
        del self.mdp2_tag
        del self.float_replacer
        del self.float_tag
        del self.float_md_tag
        del self.supplier
        del self.supplier_tag
        del self.a1_ip
        del self.a2_ip
        del self.b1_ip
        del self.c1_ip

    def __create_test_layout(self):
        il = IsoLayout(shape=self.shape)
        il.add_position(self.a1_ip)
        il.add_position(self.a2_ip)
        il.add_position(self.b1_ip)
        il.add_position(self.c1_ip)
        return il

    def test_iso_layout_init(self):
        il = IsoLayout(shape=self.shape)
        self.assert_is_not_none(il)
        self.assert_equal(il.shape, self.shape)
        self.assert_equal(len(il), 0)

    def test_add_position(self):
        il = IsoLayout(shape=self.shape)
        self.assert_equal(len(il), 0)
        il.add_position(self.b1_ip)
        self.assert_equal(len(il), 1)
        self.assert_raises(TypeError, il.add_position, self.b2_pos)

    def test_get_working_position(self):
        il = self.__create_test_layout()
        self.assert_equal(il.get_working_position(self.a1_pos), self.a1_ip)
        self.assert_is_none(il.get_working_position(self.b2_pos))

    def test_iso_layout_equality(self):
        il1 = self.__create_test_layout()
        il2 = self.__create_test_layout()
        il3 = self.__create_test_layout()
        il3.del_position(self.a1_pos)
        self.assert_equal(il1, il2)
        self.assert_not_equal(il1, il3)
        self.assert_not_equal(il1, self.a1_pos)

    def test_get_tags(self):
        il = self.__create_test_layout()
        tags = [self.mdp1_tag, self.mdp2_tag, self.empty_tag, self.fixed_tag,
                self.volume_tag, self.concentration_tag, self.supplier_tag,
                self.untreated_tag, self.untreated_md_tag]
        tag_set = il.get_tags()
        self._compare_tag_sets(tags, tag_set)

    def test_get_positions(self):
        il = self.__create_test_layout()
        exp_positions = [self.a1_pos, self.a2_pos, self.b1_pos, self.c1_pos]
        pos_set = il.get_positions()
        self._compare_pos_sets(exp_positions, pos_set)

    def test_get_tags_for_position(self):
        il = self.__create_test_layout()
        a1_tags = [self.mdp1_tag, self.volume_tag, self.concentration_tag,
                   self.fixed_tag, self.supplier_tag]
        a1_tag_set = il.get_tags_for_position(self.a1_pos)
        self._compare_tag_sets(a1_tags, a1_tag_set)
        b1_tags = [self.empty_tag]
        b1_tag_set = il.get_tags_for_position(self.b1_pos)
        self._compare_tag_sets(b1_tags, b1_tag_set)
        c1_tags = [self.untreated_tag, self.untreated_md_tag]
        c1_tag_set = il.get_tags_for_position(self.c1_pos)
        self._compare_tag_sets(c1_tags, c1_tag_set)

    def test_get_positions_for_tag(self):
        il = self.__create_test_layout()
        fixed_positions = [self.a1_pos, self.a2_pos]
        fixed_pos_set = il.get_positions_for_tag(self.fixed_tag)
        self._compare_pos_sets(fixed_positions, fixed_pos_set)

    def test_close(self):
        il = self.__create_test_layout()
        self.assert_false(il.is_closed)
        self.assert_equal(len(il), 4)
        il.close()
        self.assert_equal(len(il), 3)
        self.assert_true(il.is_closed)
        self.assert_raises(AttributeError, il.add_position, self.b1_ip)

    def test_create_rack_layout(self):
        il = self.__create_test_layout()
        rl = il.create_rack_layout()
        self.assert_is_not_none(rl)
        self.assert_equal(len(rl.tagged_rack_position_sets), 4)
        tags = [self.fixed_tag, self.mdp1_tag, self.mdp2_tag, self.volume_tag,
                self.concentration_tag, self.supplier_tag, self.untreated_tag,
                self.untreated_md_tag]
        tag_set = rl.get_tags()
        self._compare_tag_sets(tags, tag_set)
        self.assert_false(self.empty_tag in tag_set)
        positions = [self.a1_pos, self.a2_pos, self.c1_pos]
        pos_set = rl.get_positions()
        self._compare_pos_sets(positions, pos_set)
        self.assert_equal(il.get_tags_for_position(self.a1_pos),
                          rl.get_tags_for_position(self.a1_pos))
        self.assert_equal(il.get_positions_for_tag(self.fixed_tag),
                          rl.get_positions_for_tag(self.fixed_tag))
        empty_set = rl.get_positions_for_tag(self.empty_tag)
        self.assert_equal(len(empty_set), 0)

    def test_volume_and_concentration_consistency(self):
        il = self.__create_test_layout()
        self.assert_true(il.has_consistent_volumes_and_concentrations())
        b2_ip = IsoPosition(rack_position=self.b2_pos,
                            molecule_design_pool=self.mdp1)
        il.add_position(b2_ip)
        self.assert_false(il.has_consistent_volumes_and_concentrations())
        b2_ip.iso_concentration = 5
        self.assert_false(il.has_consistent_volumes_and_concentrations())
        b2_ip.iso_concentration = None
        b2_ip.iso_volume = 5
        self.assert_false(il.has_consistent_volumes_and_concentrations())
        b2_ip.iso_concentration = 5
        self.assert_true(il.has_consistent_volumes_and_concentrations())

    def test_get_floating_positions(self):
        il = IsoLayout(shape=self.shape)
        placeholder1 = '%s1' % (IsoParameters.FLOATING_INDICATOR)
        placeholder2 = '%s2' % (IsoParameters.FLOATING_INDICATOR)
        a1_ip = IsoPosition(rack_position=self.a1_pos,
                            molecule_design_pool=placeholder1)
        il.add_position(a1_ip)
        a2_ip = IsoPosition(rack_position=self.a2_pos,
                            molecule_design_pool=placeholder2)
        il.add_position(a2_ip)
        b2_ip = IsoPosition(rack_position=self.b2_pos,
                            molecule_design_pool=placeholder2)
        il.add_position(b2_ip)
        exp_dict = { placeholder1 : [a1_ip],
                     placeholder2 : [a2_ip, b2_ip]}
        float_dict = il.get_floating_positions()
        self.assert_equal(exp_dict, float_dict)

    def test_get_supplier_map(self):
        il = self.__create_test_layout()
        exp_map = {self.mdp1.id : self.supplier,
                   self.mdp2.id : self.supplier}
        il_map = il.get_supplier_map()
        self.assert_equal(exp_map, il_map)
        self.a2_ip.position_type = IsoParameters.FLOATING_TYPE_VALUE
        exp_map = {self.mdp1.id : self.supplier}
        il_map = il.get_supplier_map()
        self.assert_equal(exp_map, il_map)


class IsoLayoutConverterTest(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.log = TestingLog()
        self.rack_layout = None
        self.shape = get_96_rack_shape()
        self.a1_pos = get_rack_position_from_label('A1')
        self.a2_pos = get_rack_position_from_label('A2')
        self.b1_pos = get_rack_position_from_label('B1')
        self.c1_pos = get_rack_position_from_label('C1')
        self.d1_pos = get_rack_position_from_label('D1')
        self.empty_type_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                                  IsoParameters.EMPTY_TYPE_VALUE)
        self.fixed_type_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                                  IsoParameters.FIXED_TYPE_VALUE)
        self.mock_type_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                                 IsoParameters.MOCK_TYPE_VALUE)
        self.float_type_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                                  IsoParameters.FLOATING_TYPE_VALUE)
        self.untreated_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                                 IsoParameters.UNTREATED_TYPE_VALUE)
        self.untreated_md_tag = Tag(IsoParameters.DOMAIN,
                                    IsoParameters.MOLECULE_DESIGN_POOL,
                                    UNTREATED_POSITION_TYPE)
        self.untreated_conc_tag = Tag(IsoParameters.DOMAIN,
                                      IsoParameters.ISO_CONCENTRATION,
                                      UNTREATED_POSITION_TYPE)
        self.concentration_tag = Tag(IsoParameters.DOMAIN,
                        IsoParameters.ISO_CONCENTRATION, '50')
        self.volume1_tag = Tag(IsoParameters.DOMAIN, IsoParameters.ISO_VOLUME,
                              '2')
        self.volume2_tag = Tag(IsoParameters.DOMAIN, IsoParameters.ISO_VOLUME,
                              '4')
        self.supplier_tag = Tag(IsoParameters.DOMAIN, IsoParameters.SUPPLIER,
                               'Nunc')
        self.mdp_tag = Tag(IsoParameters.DOMAIN,
                          IsoParameters.MOLECULE_DESIGN_POOL, '205200')
        self.floating_tag1 = Tag(IsoParameters.DOMAIN,
                                 IsoParameters.MOLECULE_DESIGN_POOL,
                                 '%s1' % (IsoParameters.FLOATING_INDICATOR))
        self.floating_tag2 = Tag(IsoParameters.DOMAIN,
                                 IsoParameters.MOLECULE_DESIGN_POOL,
                                 '%s2' % (IsoParameters.FLOATING_INDICATOR))
        self.mock_md_tag = Tag(IsoParameters.DOMAIN,
                               IsoParameters.MOLECULE_DESIGN_POOL,
                               IsoParameters.MOCK_TYPE_VALUE)
        self.other_tag = Tag('test', 'something', 'unimportant')

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.log
        del self.rack_layout
        del self.shape
        del self.a1_pos
        del self.a2_pos
        del self.b1_pos
        del self.c1_pos
        del self.d1_pos
        del self.empty_type_tag
        del self.fixed_type_tag
        del self.mock_type_tag
        del self.float_type_tag
        del self.concentration_tag
        del self.volume1_tag
        del self.volume2_tag
        del self.supplier_tag
        del self.mdp_tag
        del self.floating_tag1
        del self.floating_tag2
        del self.mock_md_tag
        del self.untreated_tag
        del self.untreated_md_tag
        del self.untreated_conc_tag
        del self.other_tag

    def _create_tool(self):
        self.tool = IsoLayoutConverter(rack_layout=self.rack_layout,
                                       log=self.log)
    def _test_and_expect_errors(self, msg=None):
        self.__create_test_layout()
        ToolsAndUtilsTestCase._test_and_expect_errors(self, msg=msg)

    def __create_test_layout(self):
        trp_sets = []
        a_tags = [self.float_type_tag, self.concentration_tag]
        a_positions = [self.a1_pos, self.a2_pos]
        a_trps = self._create_test_trp_set(a_tags, a_positions)
        trp_sets.append(a_trps)
        b_tags = [self.fixed_type_tag, self.supplier_tag, self.mdp_tag,
                  self.concentration_tag]
        b_positions = [self.b1_pos]
        b_trps = self._create_test_trp_set(b_tags, b_positions)
        trp_sets.append(b_trps)
        c_tags = [self.mock_md_tag, self.mock_type_tag]
        c_positions = [self.c1_pos]
        c_trps = self._create_test_trp_set(c_tags, c_positions)
        trp_sets.append(c_trps)
        d_tags = [self.untreated_tag, self.untreated_md_tag,
                  self.untreated_conc_tag]
        d_positions = [self.d1_pos]
        d_trps = self._create_test_trp_set(d_tags, d_positions)
        trp_sets.append(d_trps)
        float1_tag = [self.floating_tag1]
        float1_positions = [self.a1_pos]
        float1_trps = self._create_test_trp_set(float1_tag, float1_positions)
        trp_sets.append(float1_trps)
        vol1_tags = [self.volume1_tag]
        vol1_positions = [self.a1_pos, self.b1_pos, self.c1_pos]
        vol1_trps = self._create_test_trp_set(vol1_tags, vol1_positions)
        trp_sets.append(vol1_trps)
        a2_tags = [self.volume2_tag, self.floating_tag2]
        a2_positions = [self.a2_pos]
        a2_trps = self._create_test_trp_set(a2_tags, a2_positions)
        trp_sets.append(a2_trps)
        all_tags = [self.other_tag]
        all_positions = [self.a1_pos, self.a2_pos, self.b1_pos, self.c1_pos]
        all_trps = self._create_test_trp_set(all_tags, all_positions)
        trp_sets.append(all_trps)
        self.rack_layout = RackLayout(shape=self.shape,
                           tagged_rack_position_sets=trp_sets)

    def test_result(self):
        self.__create_test_layout()
        self._create_tool()
        il = self.tool.get_result()
        self.assert_is_not_none(il)
        tags = [self.mdp_tag, self.floating_tag1, self.floating_tag2,
                self.mock_md_tag, self.fixed_type_tag, self.mock_type_tag,
                self.float_type_tag, self.volume1_tag, self.volume2_tag,
                self.concentration_tag, self.supplier_tag]
        tag_set = il.get_tags()
        self._compare_tag_sets(tags, tag_set)
        self.assert_equal(len(il.get_positions()), 4)
        a2_tags = [self.floating_tag2, self.float_type_tag, self.volume2_tag,
                   self.concentration_tag]
        a2_tag_set = il.get_tags_for_position(self.a2_pos)
        self._compare_tag_sets(a2_tags, a2_tag_set)
        mock_positions = [self.c1_pos]
        mock_pos_set = il.get_positions_for_tag(self.mock_type_tag)
        self._compare_pos_sets(mock_positions, mock_pos_set)
        self.assert_equal(len(il.get_positions_for_tag(self.empty_type_tag)), 0)

    def test_double_specification(self):
        self.other_tag = Tag(IsoParameters.DOMAIN, IsoParameters.ISO_VOLUME,
                             '6')
        self._test_and_expect_errors('specified multiple times')

    def test_missing_molecule_design_set(self):
        mdp_tags = [self.mdp_tag, self.mock_md_tag, self.floating_tag1,
                    self.floating_tag2, self.untreated_md_tag]
        for tag in mdp_tags:
            tag.predicate = 'md'
        self._test_and_expect_errors('no molecule_design_pool_id specification')

    def test_unknown_molecule_design_set_id(self):
        self.mdp_tag = Tag(IsoParameters.DOMAIN,
                           IsoParameters.MOLECULE_DESIGN_POOL, 'default99')
        self._test_and_expect_errors('molecule design pool IDs could not be ' \
                                     'found in the DB')

    def test_missing_volume(self):
        self.volume1_tag = Tag('test', 'no', 'iso_volume')
        self._test_and_expect_errors('do not have an ISO volume')

    def test_missing_concentration(self):
        self.concentration_tag = Tag('test', 'no', 'iso_concentration')
        self._test_and_expect_errors('not have an ISO concentration')

    def test_invalid_volume(self):
        self.volume1_tag = Tag(IsoParameters.DOMAIN, IsoParameters.ISO_VOLUME,
                               '4-5')
        self._test_and_expect_errors('invalid ISO volumes')

    def test_invalid_concentration(self):
        self.concentration_tag = Tag(IsoParameters.DOMAIN,
                                     IsoParameters.ISO_CONCENTRATION, '4-5')
        self._test_and_expect_errors('invalid ISO concentrations')

    def test_unknown_supplier(self):
        self.supplier_tag = Tag(IsoParameters.DOMAIN, IsoParameters.SUPPLIER,
                                'test_supplier')
        self._test_and_expect_errors('suppliers could not be found in the DB')

    def test_empty_and_volume(self):
        self.__create_test_layout()
        d4_tags = [self.empty_type_tag, self.volume1_tag]
        d4_positions = [get_rack_position_from_label('D4')]
        trps = self._create_test_trp_set(d4_tags, d4_positions)
        self.rack_layout.tagged_rack_position_sets.append(trps)
        self._create_tool()
        result = self.tool.get_result()
        self.assert_is_none(result)
        self._check_error_messages('ISO volume specifications although they ' \
                                   'are empty')

    def test_empty_and_concentration(self):
        self.__create_test_layout()
        d4_tags = [self.empty_type_tag, self.concentration_tag]
        d4_positions = [get_rack_position_from_label('D4')]
        trps = self._create_test_trp_set(d4_tags, d4_positions)
        self.rack_layout.tagged_rack_position_sets.append(trps)
        self._create_tool()
        result = self.tool.get_result()
        self.assert_is_none(result)
        self._check_error_messages('ISO concentration specifications ' \
                                   'although they are empty')

    def test_non_fixed_and_supplier(self):
        self.__create_test_layout()
        d4_tags = [self.mock_md_tag, self.concentration_tag, self.volume1_tag,
                   self.mock_md_tag, self.supplier_tag]
        d4_positions = [get_rack_position_from_label('D4')]
        trps = self._create_test_trp_set(d4_tags, d4_positions)
        self.rack_layout.tagged_rack_position_sets.append(trps)
        self._create_tool()
        result = self.tool.get_result()
        self.assert_is_none(result)
        self._check_error_messages('supplier specified for the following ' \
                                   'non-fixed position')


class IsoRackSectorToolTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.log = TestingLog()
        self.iso_layout = None
        self.number_sectors = 4
        self.ignore_mocks = True
        self.attribute_name = 'iso_concentration'
        self.rack_shape = get_384_rack_shape()
        # value: sector index, md pool, conc
        self.position_data = dict(
                A4=(1, 'md_1', 10), B3=(2, None, None), B4=(3, 'md_1', 30),
                A6=(1, 'md_3', 10), B5=(2, 'md_4', 20), B6=(3, 'md_3', 30),
                C2=(1, 'md_5', 10), D1=(2, 'md_6', 20), D2=(3, 'md_5', 30),
                C4=(1, 'untreated', None), D3=(2, None, None),
                                                        D4=(3, None, None),
                E2=(1, 'md_9', 10), F1=(2, 'md_9', 20), F2=(3, 'md_9', 30))
        self.one_sector_data = dict(
                A4=(1, 'md_1', 10), B3=(2, 'md_1', 10), B4=(3, 'md_1', 10),
                A6=(1, 'md_2', 10), B5=(2, 'md_2', 10), B6=(3, 'md_2', 10),
                C2=(1, 'md_3', 10), D1=(2, 'md_3', 10), D2=(3, 'md_3', 10),
                C4=(1, None, None), D5=(2, None, None), D6=(3, None, None))

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.log
        del self.iso_layout
        del self.number_sectors
        del self.ignore_mocks
        del self.attribute_name
        del self.rack_shape
        del self.position_data
        del self.one_sector_data

    def _continue_setup(self):
        self.__create_iso_layout()
        self._create_tool()

    def __create_iso_layout(self):
        self.iso_layout = IsoLayout(shape=self.rack_shape)
        for pos_label, pos_data in self.position_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            pool = pos_data[1]
            if pool is None or pool == IsoParameters.UNTREATED_TYPE_VALUE:
                iso_pos = IsoPosition.create_empty_position(rack_pos)
                self.iso_layout.add_position(iso_pos)
                continue
            iso_conc = pos_data[2]
            iso_pos = IsoPosition(rack_position=rack_pos,
                                  molecule_design_pool=pool,
                                  iso_concentration=iso_conc,
                                  iso_volume=10)
            self.iso_layout.add_position(iso_pos)

    def _test_invalid_iso_layout(self):
        self._continue_setup()
        self.iso_layout = self.iso_layout.create_rack_layout()
        self._test_and_expect_errors('layout must be a IsoLayout object')

    def _test_invalid_number_sectors(self):
        self._continue_setup()
        self.number_sectors = '4'
        self._test_and_expect_errors('The number of sectors must be a int')

    def _test_invalid_ignore_mocks(self):
        self._continue_setup()
        self.ignore_mocks = 1
        self._test_and_expect_errors('The "ignore mock" flag must be a bool ' \
                                     'object')


class IsoValueDeterminerTestCase(IsoRackSectorToolTestCase):

    def _create_tool(self):
        self.tool = IsoValueDeterminer(iso_layout=self.iso_layout,
                        attribute_name=self.attribute_name, log=self.log,
                        number_sectors=self.number_sectors,
                        ignore_mock=self.ignore_mocks)

    def test_result(self):
        self._continue_setup()
        sector_map = self.tool.get_result()
        self.assert_is_not_none(sector_map)
        self.assert_equal(len(sector_map), 4)
        self.assert_equal(sector_map[0], None)
        self.assert_equal(sector_map[1], 10)
        self.assert_equal(sector_map[2], 20)
        self.assert_equal(sector_map[3], 30)

    def test_result_1_conc(self):
        self.position_data = self.one_sector_data
        self._continue_setup()
        sector_map = self.tool.get_result()
        self.assert_is_not_none(sector_map)
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

    def test_invalid_iso_layout(self):
        self._test_invalid_iso_layout()

    def test_invalid_number_sectors(self):
        self._test_invalid_number_sectors()

    def test_invalid_ignore_mocks(self):
        self._test_invalid_ignore_mocks()

    def test_invalid_attribute_name(self):
        self._continue_setup()
        self.attribute_name = [self.attribute_name]
        self._test_and_expect_errors('The attribute name must be a str object')

    def test_unknown_attribute_name(self):
        self._continue_setup()
        self.attribute_name = 'molecule'
        self._test_and_expect_errors('Unknown attribute')

    def test_more_than_one_value(self):
        self._continue_setup()
        self.attribute_name = 'molecule_design_pool'
        self._test_and_expect_errors('There is more than one value for sector')


class IsoRackSectorAssociatorTestCase(IsoRackSectorToolTestCase):

    def set_up(self):
        IsoRackSectorToolTestCase.set_up(self)
        self.has_distinct_floatings = True

    def tear_down(self):
        IsoRackSectorToolTestCase.tear_down(self)
        del self.has_distinct_floatings

    def _create_tool(self):
        self.tool = IsoRackSectorAssociator(iso_layout=self.iso_layout,
                        log=self.log, number_sectors=self.number_sectors,
                        has_distinct_floatings=self.has_distinct_floatings,
                        ignore_mock=self.ignore_mocks)

    def test_result(self):
        self._continue_setup()
        associated_sectors = self.tool.get_result()
        self.assert_is_not_none(associated_sectors)
        exp_result = [[1, 3], [2]]
        self.assert_equal(len(exp_result), len(associated_sectors))
        for association in exp_result:
            self.assert_true(association in associated_sectors)

    def test_result_distinct_floatings(self):
        self._continue_setup()
        self.has_distinct_floatings = False
        self._test_and_expect_errors('The molecule design pools in the ' \
                                     'different quadrants are not consistent')
        self.position_data['B3'] = (2, 'md_2', 20)
        self._continue_setup()
        associated_sectors = self.tool.get_result()
        self.assert_is_not_none(associated_sectors)
        exp_result = [[1, 2, 3]]
        self.assert_equal(len(exp_result), len(associated_sectors))
        for association in exp_result:
            self.assert_true(association in associated_sectors)

    def test_invalid_iso_layout(self):
        self._test_invalid_iso_layout()

    def test_invalid_number_sectors(self):
        self._test_invalid_number_sectors()

    def test_invalid_ignore_mocks(self):
        self._test_invalid_ignore_mocks()

    def test_inconsistent_rack_sectors(self):
        self.position_data['C2'] = (1, 'md_5', 40)
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to determine rack ' \
                                     'sector concentrations')

    def test_inconsistent_molecule_design_pools(self):
        self.position_data['C2'] = (1, 'md_7', 10)
        self._continue_setup()
        self._test_and_expect_errors('The molecule design pools in the ' \
                                     'different quadrants are not consistent')


class IsoAssociationTestCase(IsoRackSectorToolTestCase):

    def test_result_4(self):
        self._continue_setup()
        ad = IsoAssociationData(iso_layout=self.iso_layout, log=self.log)
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
        exp_sc = {0 : None, 1 : 10, 2 : 20, 3 : 30}
        self.assert_equal(len(exp_sc), len(sector_concentrations))
        self.assert_equal(exp_sc, sector_concentrations)
        # check parent sectors
        parent_sectors = ad.parent_sectors
        exp_ps = {1 : 3, 2 : None, 3 : None}
        self.assert_equal(len(exp_ps), len(parent_sectors))
        self.assert_equal(exp_ps, parent_sectors)

    def test_result_1(self):
        self.position_data = self.one_sector_data
        self._continue_setup()
        ad = IsoAssociationData(iso_layout=self.iso_layout, log=self.log)
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

    def test_failure(self):
        self.position_data['C2'] = (1, 'md_7', 10)
        self._continue_setup()
        attrs = dict(iso_layout=self.iso_layout, log=self.log)
        self.assert_raises(ValueError, IsoAssociationData, **attrs)
