"""
Tests the transfection utils.
AAB Aug 03, 2011
"""
from everest.testing import check_attributes
from thelma.automation.tools.utils.base import UNTREATED_POSITION_TYPE
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionAssociationData
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionLayout
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionLayoutConverter
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionParameters
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionPosition
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionRackSectorAssociator
from thelma.automation.tools.semiconstants \
    import get_reservoir_specs_standard_96
from thelma.automation.tools.semiconstants import get_384_rack_shape
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.utils.base import EMPTY_POSITION_TYPE
from thelma.automation.tools.utils.base import FIXED_POSITION_TYPE
from thelma.automation.tools.utils.base import FLOATING_POSITION_TYPE
from thelma.automation.tools.utils.base import MOCK_POSITION_TYPE
from thelma.automation.tools.utils.iso import IsoParameters
from thelma.automation.tools.utils.iso import IsoPosition
from thelma.automation.tools.worklists.base import MIN_BIOMEK_TRANSFER_VOLUME
from thelma.interfaces import IMoleculeDesignPool
from thelma.models.moleculetype import MOLECULE_TYPE_IDS
from thelma.models.racklayout import RackLayout
from thelma.models.tagging import Tag
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase
import logging


class TransfectionParametersTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.a1_pos = get_rack_position_from_label('A1')

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.a1_pos

    def test_calculate_mastermix_volume(self):
        reservoir_specs = get_reservoir_specs_standard_96()
        req_vol1 = TransfectionParameters.calculate_mastermix_volume(
                            number_target_wells=10, number_replicates=3,
                            iso_reservoir_spec=reservoir_specs)
        self.assert_equal(req_vol1, 180)
        req_vol2 = TransfectionParameters.calculate_mastermix_volume(
                            number_target_wells=10, number_replicates=1,
                            iso_reservoir_spec=reservoir_specs)
        self.assert_equal(req_vol2, 67)
        req_vol3 = TransfectionParameters.calculate_mastermix_volume(
                            number_target_wells=10, number_replicates=1,
                            iso_reservoir_spec=reservoir_specs, use_cybio=True)
        self.assert_equal(req_vol3, 60)

    def test_calculate_iso_volume(self):
        reservoir_specs = get_reservoir_specs_standard_96()
        optimem_df_sirna = 4
        iso_vol1 = TransfectionParameters.calculate_iso_volume(
                            number_target_wells=16, number_replicates=3,
                            iso_reservoir_spec=reservoir_specs,
                            optimem_dil_factor=optimem_df_sirna)
        self.assert_equal(iso_vol1, 33.8)
        iso_vol2 = TransfectionParameters.calculate_iso_volume(1, 1,
                                    iso_reservoir_spec=reservoir_specs,
                                    optimem_dil_factor=optimem_df_sirna)
        self.assert_equal(iso_vol2, MIN_BIOMEK_TRANSFER_VOLUME)
        iso_vol3 = TransfectionParameters.calculate_iso_volume(
                            number_target_wells=4, number_replicates=2,
                            iso_reservoir_spec=reservoir_specs,
                            optimem_dil_factor=optimem_df_sirna,
                            use_cybio=True)
        self.assert_equal(iso_vol3, 6.3)
        iso_vol4 = TransfectionParameters.calculate_iso_volume(
                            number_target_wells=1, number_replicates=1,
                            iso_reservoir_spec=reservoir_specs,
                            optimem_dil_factor=optimem_df_sirna,
                            use_cybio=True)
        self.assert_equal(iso_vol4, 1.9)
        optimem_df_mirna = 3
        iso_vol5 = TransfectionParameters.calculate_iso_volume(
                            number_target_wells=4, number_replicates=2,
                            iso_reservoir_spec=reservoir_specs,
                            optimem_dil_factor=optimem_df_mirna,
                            use_cybio=True)
        self.assert_equal(iso_vol5, 8.4)

    def test_calculate_reagent_dilution_volume(self):
        iso_volume = 1
        optimem_df_sirna = 4
        req_vol1 = TransfectionParameters.calculate_reagent_dilution_volume(
                                                iso_volume, optimem_df_sirna)
        self.assert_equal(req_vol1, 4)
        optimem_df_mirna = 3
        req_vol2 = TransfectionParameters.calculate_reagent_dilution_volume(
                                                iso_volume, optimem_df_mirna)
        self.assert_equal(req_vol2, 3)

    def test_calculate_complete_volume(self):
        optimem_df_sirna = 4
        self.assert_equal(80,
                TransfectionParameters.calculate_complete_volume(10,
                                                        optimem_df_sirna))
        optimem_df_mirna = 3
        self.assert_equal(60,
                TransfectionParameters.calculate_complete_volume(10,
                                                        optimem_df_mirna))

    def test_calculate_initial_reagent_dilution(self):
        self.assert_equal(100,
            TransfectionParameters.calculate_initial_reagent_dilution(1400))

    def test_get_optimem_dilution_factor(self):
        mt = MOLECULE_TYPE_IDS.SIRNA
        self.assert_equal(4,
                    TransfectionParameters.get_optimem_dilution_factor(mt))
        mt = MOLECULE_TYPE_IDS.MIRNA_INHI
        self.assert_equal(3,
                    TransfectionParameters.get_optimem_dilution_factor(mt))

    def test_get_total_dilution_factor(self):
        optimem_df_sirna = 4
        self.assert_equal(56, TransfectionParameters.\
                          get_total_dilution_factor(optimem_df_sirna))
        optimem_df_mirna = 3
        self.assert_equal(42, TransfectionParameters.\
                          get_total_dilution_factor(optimem_df_mirna))

    def test_requires_deepwell(self):
        number_target_wells = 15
        number_replicates = 3
        self.assert_true(TransfectionParameters.requires_deepwell(
                                    number_target_wells, number_replicates))
        number_replicates = 1
        self.assert_false(TransfectionParameters.requires_deepwell(
                                    number_target_wells, number_replicates))


    def test_get_layout_optimem_molecule_type(self):
        tf_layout = TransfectionLayout(shape=get_96_rack_shape())
        a1_pos = get_rack_position_from_label('A1')
        b1_pos = get_rack_position_from_label('B1')
        c1_pos = get_rack_position_from_label('C1')
        mi_rna1 = self._get_entity(IMoleculeDesignPool, '330001')
        tf_pos1 = TransfectionPosition(rack_position=a1_pos,
                               molecule_design_pool=mi_rna1)
        tf_pos1.store_optimem_dilution_factor()
        mi_rna2 = self._get_entity(IMoleculeDesignPool, '330002')
        tf_pos2 = TransfectionPosition(rack_position=b1_pos,
                               molecule_design_pool=mi_rna2)
        tf_pos2.store_optimem_dilution_factor()
        tf_pos3 = TransfectionPosition.create_mock_position(c1_pos,
                    iso_volume=1, reagent_name='mix', reagent_dil_factor=1)
        tf_layout.add_position(tf_pos1)
        tf_layout.add_position(tf_pos2)
        tf_layout.add_position(tf_pos3)
        self.assert_equal(3, TransfectionParameters.\
                          get_layout_mock_optimem_molecule_type(tf_layout))
        si_rna = self._get_entity(IMoleculeDesignPool, '205200')
        tf_pos1.molecule_design_pool = si_rna
        tf_pos1.store_optimem_dilution_factor()
        self.assert_equal(4, TransfectionParameters.\
                          get_layout_mock_optimem_molecule_type(tf_layout))


class TransfectionPositionTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.rack_pos = get_rack_position_from_label('A1')
        self.rack_pos2 = get_rack_position_from_label('B2')
        self.empty_type_tag = Tag('iso', 'position_type', 'empty')
        self.fixed_type_tag = Tag('iso', 'position_type', 'fixed')
        self.mdp = self._get_entity(IMoleculeDesignPool, '205200')
        self.mdp_tag = Tag('iso', 'molecule_design_pool_id', '205200')
        self.iso_concentration = 1
        self.iso_volume = 7.5
        self.concentration_tag = Tag('iso', 'iso_concentration', '1')
        self.volume_tag = Tag('iso', 'iso_volume', '7.5')
        self.supplier = self._create_organization(name='iso_test')
        self.supplier_tag = Tag('iso', 'supplier', 'iso_test')
        self.reagent_name = 'Mix1'
        self.reagent_name_tag = Tag('transfection', 'reagent_name', 'Mix1')
        self.reagent_df = 1400
        self.reagent_df_tag = Tag('transfection', 'reagent_dilution_factor',
                                  '1400')
        self.final_concentration = 5
        self.final_conc_tag = Tag('transfection', 'final_concentration', '5')
        self.optimem_df = 3
        self.optimem_df_tag = Tag('transfection', 'optimem_dilution_factor',
                                  '3')
        self.cell_plate_positions = set([self.rack_pos, self.rack_pos2])
        self.init_data = dict(rack_position=self.rack_pos,
                              molecule_design_pool=self.mdp,
                              reagent_name=self.reagent_name,
                              reagent_dil_factor=self.reagent_df,
                              iso_volume=self.iso_volume,
                              iso_concentration=self.iso_concentration,
                              supplier=self.supplier,
                              final_concentration=self.final_concentration)

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.rack_pos
        del self.rack_pos2
        del self.empty_type_tag
        del self.fixed_type_tag
        del self.mdp
        del self.mdp_tag
        del self.iso_concentration
        del self.iso_volume
        del self.concentration_tag
        del self.volume_tag
        del self.supplier
        del self.supplier_tag
        del self.reagent_name
        del self.reagent_name_tag
        del self.reagent_df
        del self.reagent_df_tag
        del self.final_concentration
        del self.final_conc_tag
        del self.optimem_df
        del self.optimem_df_tag
        del self.cell_plate_positions
        del self.init_data

    def test_init_fixed(self):
        tf_pos = TransfectionPosition(**self.init_data)
        check_attributes(tf_pos, self.init_data)
        self.assert_equal(len(tf_pos.cell_plate_positions), 0)
        self.init_data['molecule_design_pool'] = None
        self.assert_raises(ValueError, TransfectionPosition, **self.init_data)
        self.init_data['molecule_design_pool'] = self.mdp
        self.init_data['reagent_dil_factor'] = '4-5'
        self.assert_raises(ValueError, TransfectionPosition, **self.init_data)
        self.init_data['reagent_dil_factor'] = self.reagent_df
        self.init_data['iso_volume'] = '4-5'
        self.assert_raises(ValueError, TransfectionPosition, **self.init_data)
        self.init_data['iso_volume'] = self.iso_volume
        self.init_data['iso_concentration'] = '4-5'
        self.assert_raises(ValueError, TransfectionPosition, **self.init_data)
        self.init_data['iso_concentration'] = self.iso_concentration
        self.init_data['final_concentration'] = '4-5'
        self.assert_raises(ValueError, TransfectionPosition, **self.init_data)
        self.init_data['final_concentration'] = self.final_concentration
        self.init_data['supplier'] = 3
        self.assert_raises(TypeError, TransfectionPosition, **self.init_data)

    def test_init_mock_incl_factory(self):
        mock_attrs = dict(rack_position=self.rack_pos,
                          molecule_design_pool=MOCK_POSITION_TYPE,
                          iso_volume=self.iso_volume,
                          reagent_name=self.reagent_name,
                          reagent_dil_factor=self.reagent_df)
        mock_pos1 = TransfectionPosition(**mock_attrs)
        mock_attrs['final_concentration'] = None
        check_attributes(mock_pos1, mock_attrs)
        mock_pos2 = TransfectionPosition(**mock_attrs)
        check_attributes(mock_pos2, mock_attrs)
        mock_attrs['final_concentration'] = TransfectionPosition.NONE_REPLACER
        mock_pos3 = TransfectionPosition(**mock_attrs)
        check_attributes(mock_pos3, mock_attrs)
        mock_attrs['final_concentration'] = MOCK_POSITION_TYPE
        mock_pos4 = TransfectionPosition(**mock_attrs)
        check_attributes(mock_pos4, mock_attrs)
        mock_attrs['final_concentration'] = 3
        self.assert_raises(ValueError, TransfectionPosition, **mock_attrs)
        mock_attrs['final_concentration'] = None
        del mock_attrs['molecule_design_pool']
        mock_pos5 = TransfectionPosition.create_mock_position(**mock_attrs)
        mock_attrs['position_type'] = MOCK_POSITION_TYPE
        check_attributes(mock_pos5, mock_attrs)
        mock_pos6 = TransfectionPosition.create_mock_position(
                                            rack_position=self.rack_pos,
                                            iso_volume=self.iso_volume)
        mock_attrs['final_concentration'] = TransfectionPosition.NONE_REPLACER
        mock_attrs['reagent_name'] = None
        mock_attrs['reagent_dil_factor'] = None
        check_attributes(mock_pos6, mock_attrs)

    def test_init_untreated_incl_factory(self):
        untreated_attrs = dict(rack_position=self.rack_pos,
                               molecule_design_pool=UNTREATED_POSITION_TYPE,
                               reagent_name=None, reagent_dil_factor=None,
                               final_concentration=None)
        ut_pos1 = TransfectionPosition(**untreated_attrs)
        check_attributes(ut_pos1, untreated_attrs)
        untreated_attrs['reagent_name'] = UNTREATED_POSITION_TYPE
        ut_pos2 = TransfectionPosition(**untreated_attrs)
        check_attributes(ut_pos2, untreated_attrs)
        untreated_attrs['reagent_name'] = TransfectionPosition.NONE_REPLACER
        ut_pos3 = TransfectionPosition(**untreated_attrs)
        check_attributes(ut_pos3, untreated_attrs)
        untreated_attrs['reagent_name'] = 'mix'
        self.assert_raises(ValueError, TransfectionPosition, **untreated_attrs)
        untreated_attrs['reagent_name'] = TransfectionPosition.NONE_REPLACER
        untreated_attrs['reagent_dil_factor'] = UNTREATED_POSITION_TYPE
        ut_pos4 = TransfectionPosition(**untreated_attrs)
        check_attributes(ut_pos4, untreated_attrs)
        untreated_attrs['reagent_dil_factor'] = \
                                    TransfectionPosition.NONE_REPLACER
        ut_pos5 = TransfectionPosition(**untreated_attrs)
        check_attributes(ut_pos5, untreated_attrs)
        untreated_attrs['reagent_dil_factor'] = 1400
        self.assert_raises(ValueError, TransfectionPosition, **untreated_attrs)
        untreated_attrs['reagent_dil_factor'] = UNTREATED_POSITION_TYPE
        untreated_attrs['final_concentration'] = UNTREATED_POSITION_TYPE
        ut_pos6 = TransfectionPosition(**untreated_attrs)
        check_attributes(ut_pos6, untreated_attrs)
        untreated_attrs['final_concentration'] = \
                                    TransfectionPosition.NONE_REPLACER
        ut_pos7 = TransfectionPosition(**untreated_attrs)
        check_attributes(ut_pos7, untreated_attrs)
        untreated_attrs['final_concentration'] = 4
        self.assert_raises(ValueError, TransfectionPosition, **untreated_attrs)
        untreated_attrs['final_concentration'] = UNTREATED_POSITION_TYPE
        del untreated_attrs['molecule_design_pool']
        ut_pos8 = TransfectionPosition.create_untreated_position(
                                                            **untreated_attrs)
        check_attributes(ut_pos8, untreated_attrs)
        untreated_attrs['position_type'] = UNTREATED_POSITION_TYPE
        ut_pos9 = TransfectionPosition.create_untreated_position(
                                                rack_position=self.rack_pos)
        untreated_attrs['reagent_name'] = TransfectionPosition.NONE_REPLACER
        untreated_attrs['reagent_dil_factor'] = \
                                        TransfectionPosition.NONE_REPLACER
        untreated_attrs['final_concentration'] = \
                                        TransfectionPosition.NONE_REPLACER
        check_attributes(ut_pos9, untreated_attrs)

    def test_init_empty_incl_factory(self):
        empty_pos = TransfectionPosition.create_empty_position(self.rack_pos)
        self.init_data['molecule_design_pool'] = None
        self.init_data['reagent_name'] = None
        self.init_data['reagent_dil_factor'] = None
        self.init_data['iso_volume'] = None
        self.init_data['iso_concentration'] = None
        self.init_data['final_concentration'] = None
        self.init_data['supplier'] = None
        check_attributes(empty_pos, self.init_data)
        self.assert_true(empty_pos.is_empty)
        self.init_data['final_concentration'] = self.final_concentration
        self.assert_raises(ValueError, TransfectionPosition, **self.init_data)

    def test_init_number_conversion(self):
        tf_pos = TransfectionPosition(rack_position=self.rack_pos,
                            molecule_design_pool=self.mdp,
                            reagent_name=self.reagent_name,
                            reagent_dil_factor=str(self.reagent_df),
                            iso_volume=str(self.iso_volume),
                            iso_concentration=str(self.iso_concentration),
                            final_concentration=str(self.final_concentration),
                            supplier=self.supplier)
        check_attributes(tf_pos, self.init_data)

    def test_equality(self):
        tf_pos01 = TransfectionPosition(**self.init_data)
        self.init_data['molecule_design_pool'] = self._get_entity(
                                        IMoleculeDesignPool, '205201')
        tf_pos02 = TransfectionPosition(**self.init_data)
        self.init_data['molecule_design_pool'] = self.mdp
        self.init_data['reagent_name'] = 'other'
        tf_pos03 = TransfectionPosition(**self.init_data)
        self.init_data['reagent_name'] = self.reagent_name
        self.init_data['reagent_dil_factor'] = (self.reagent_df * 2)
        tf_pos04 = TransfectionPosition(**self.init_data)
        self.init_data['reagent_dil_factor'] = self.reagent_df
        self.init_data['iso_volume'] = (self.iso_volume * 2)
        tf_pos05 = TransfectionPosition(**self.init_data)
        self.init_data['iso_volume'] = self.iso_volume
        self.init_data['iso_concentration'] = (self.iso_concentration * 2)
        tf_pos06 = TransfectionPosition(**self.init_data)
        self.init_data['iso_concentration'] = self.iso_concentration
        self.init_data['supplier'] = None
        tf_pos07 = TransfectionPosition(**self.init_data)
        self.init_data['supplier'] = self.supplier
        self.init_data['final_concentration'] = (self.final_concentration * 2)
        tf_pos08 = TransfectionPosition(**self.init_data)
        self.init_data['final_concentration'] = self.final_concentration
        tf_pos9 = TransfectionPosition(**self.init_data)
        tf_pos9.add_cell_plate_position(self.rack_pos)
        self.assert_not_equal(tf_pos01, tf_pos02)
        self.assert_not_equal(tf_pos01, tf_pos03)
        self.assert_not_equal(tf_pos01, tf_pos04)
        self.assert_not_equal(tf_pos01, tf_pos05)
        self.assert_not_equal(tf_pos01, tf_pos06)
        self.assert_equal(tf_pos01, tf_pos07)
        self.assert_not_equal(tf_pos01, tf_pos08)
        self.assert_equal(tf_pos01, tf_pos9)
        iso_pos = IsoPosition(rack_position=self.rack_pos)
        self.assert_not_equal(tf_pos01, iso_pos)

    def test_get_tag_set(self):
        tf_pos = TransfectionPosition(**self.init_data)
        tf_pos.add_cell_plate_position(self.rack_pos)
        tf_pos.add_cell_plate_position(self.rack_pos2)
        tags = [self.fixed_type_tag, self.mdp_tag, self.reagent_name_tag,
                self.reagent_df_tag, self.volume_tag, self.concentration_tag,
                self.final_conc_tag, self.supplier_tag]
        tag_set = tf_pos.get_tag_set()
        self._compare_tag_sets(tags, tag_set)
        # add optimem factor
        tf_pos.set_optimem_dilution_factor(self.optimem_df)
        tags.append(self.optimem_df_tag)
        optimem_tag_set = tf_pos.get_tag_set()
        self._compare_tag_sets(tags, optimem_tag_set)
        # empty positions
        empty_pos = TransfectionPosition.create_empty_position(self.rack_pos)
        empty_tags = [self.empty_type_tag]
        empty_tag_set = empty_pos.get_tag_set()
        self._compare_tag_sets(empty_tags, empty_tag_set)

    def test_get_tag_set_untreated(self):
        ut_md_tag = Tag('iso', 'molecule_design_pool_id', 'untreated')
        ut_type_tag = Tag('iso', 'position_type', 'untreated')
        tags1 = [ut_md_tag, ut_type_tag,
                 Tag('transfection', 'reagent_name', 'None'),
                 Tag('transfection', 'reagent_dilution_factor', 'None'),
                 Tag('transfection', 'final_concentration', 'None')]
        attrs = dict(rack_position=self.rack_pos)
        ut_pos1 = TransfectionPosition.create_untreated_position(**attrs)
        tag_set1 = ut_pos1.get_tag_set()
        self._compare_tag_sets(tags1, tag_set1)
        attrs['reagent_name'] = None
        attrs['reagent_dil_factor'] = None
        attrs['final_concentration'] = UNTREATED_POSITION_TYPE
        ut_pos2 = TransfectionPosition.create_untreated_position(**attrs)
        tag_set2 = ut_pos2.get_tag_set()
        tags2 = [ut_md_tag, ut_type_tag,
                 Tag('transfection', 'final_concentration', 'untreated')]
        self._compare_tag_sets(tags2, tag_set2)

    def test_get_parameter_values(self):
        tf_pos = TransfectionPosition(**self.init_data)
        tf_pos.add_cell_plate_position(self.rack_pos)
        tf_pos.add_cell_plate_position(self.rack_pos2)
        self.assert_equal(self.mdp, tf_pos.get_parameter_value(
                                TransfectionParameters.MOLECULE_DESIGN_POOL))
        self.assert_equal(self.reagent_name,
            tf_pos.get_parameter_value(TransfectionParameters.REAGENT_NAME))
        self.assert_equal(self.reagent_df, tf_pos.get_parameter_value(
                                    TransfectionParameters.REAGENT_DIL_FACTOR))
        self.assert_equal(self.iso_volume,
            tf_pos.get_parameter_value(TransfectionParameters.ISO_VOLUME))
        self.assert_equal(self.iso_concentration, tf_pos.get_parameter_value(
                                    TransfectionParameters.ISO_CONCENTRATION))
        self.assert_equal(TransfectionParameters.FIXED_TYPE_VALUE,
            tf_pos.get_parameter_value(TransfectionParameters.POS_TYPE))
        self.assert_equal(self.final_concentration, tf_pos.get_parameter_value(
                                    TransfectionParameters.FINAL_CONCENTRATION))
        self.assert_equal(self.supplier,
            tf_pos.get_parameter_value(TransfectionParameters.SUPPLIER))
        # add optimem factor
        self.assert_is_none(tf_pos.get_parameter_value(
                                    TransfectionParameters.OPTIMEM_DIL_FACTOR))
        tf_pos.set_optimem_dilution_factor(self.optimem_df)
        self.assert_equal(self.optimem_df, tf_pos.get_parameter_value(
                                    TransfectionParameters.OPTIMEM_DIL_FACTOR))

    def test_get_parameter_tags(self):
        tf_pos = TransfectionPosition(**self.init_data)
        tf_pos.add_cell_plate_position(self.rack_pos)
        tf_pos.add_cell_plate_position(self.rack_pos2)
        self.assert_equal(self.mdp_tag, tf_pos.get_parameter_tag(
                                TransfectionParameters.MOLECULE_DESIGN_POOL))
        self.assert_equal(self.reagent_name_tag,
            tf_pos.get_parameter_tag(TransfectionParameters.REAGENT_NAME))
        self.assert_equal(self.reagent_df_tag, tf_pos.get_parameter_tag(
                                    TransfectionParameters.REAGENT_DIL_FACTOR))
        self.assert_equal(self.volume_tag,
            tf_pos.get_parameter_tag(TransfectionParameters.ISO_VOLUME))
        self.assert_equal(self.concentration_tag, tf_pos.get_parameter_tag(
                                    TransfectionParameters.ISO_CONCENTRATION))
        self.assert_equal(self.fixed_type_tag,
            tf_pos.get_parameter_tag(TransfectionParameters.POS_TYPE))
        self.assert_equal(self.final_conc_tag, tf_pos.get_parameter_tag(
                                    TransfectionParameters.FINAL_CONCENTRATION))
        self.assert_equal(self.supplier_tag,
            tf_pos.get_parameter_tag(TransfectionParameters.SUPPLIER))
        # add optimem factor
        tf_pos.set_optimem_dilution_factor(self.optimem_df)
        self.assert_equal(self.optimem_df_tag, tf_pos.get_parameter_tag(
                                    TransfectionParameters.OPTIMEM_DIL_FACTOR))

    def test_position_types(self):
        fixed_pos = TransfectionPosition(**self.init_data)
        self.assert_true(fixed_pos.is_fixed)
        self.assert_false(fixed_pos.is_floating)
        self.assert_false(fixed_pos.is_mock)
        self.assert_false(fixed_pos.is_empty)
        fixed_tag_set = fixed_pos.get_tag_set()
        self.assert_true(self.fixed_type_tag in fixed_tag_set)
        self.assert_true(self.mdp_tag in fixed_tag_set)
        md_float_tag = Tag('iso', 'molecule_design_pool_id', 'md_1')
        self.assert_false(md_float_tag in fixed_tag_set)
        self.init_data['molecule_design_pool'] = 'md_1'
        self.init_data['supplier'] = None
        float_pos = TransfectionPosition(**self.init_data)
        self.assert_false(float_pos.is_fixed)
        self.assert_true(float_pos.is_floating)
        self.assert_false(float_pos.is_mock)
        self.assert_false(float_pos.is_empty)
        float_tag_set = float_pos.get_tag_set()
        float_type_tag = Tag('iso', 'position_type', 'floating')
        self.assert_true(float_type_tag in float_tag_set)
        self.assert_false(self.mdp_tag in float_tag_set)
        self.assert_true(md_float_tag in float_tag_set)
        self.init_data['molecule_design_pool'] = MOCK_POSITION_TYPE
        self.init_data['iso_concentration'] = None
        self.init_data['final_concentration'] = None
        mock_pos = TransfectionPosition(**self.init_data)
        self.assert_false(mock_pos.is_fixed)
        self.assert_false(mock_pos.is_floating)
        self.assert_true(mock_pos.is_mock)
        self.assert_false(mock_pos.is_empty)
        mock_tag_set = mock_pos.get_tag_set()
        mock_type_tag = Tag('iso', 'position_type', 'mock')
        mock_md_tag = Tag('iso', 'molecule_design_pool_id', 'mock')
        self.assert_true(mock_type_tag in mock_tag_set)
        self.assert_false(self.mdp_tag in mock_tag_set)
        self.assert_true(mock_md_tag in mock_tag_set)
        self.assert_false(self.concentration_tag in mock_tag_set)
        empty_pos = TransfectionPosition.create_empty_position(self.rack_pos)
        self.assert_false(empty_pos.is_fixed)
        self.assert_false(empty_pos.is_floating)
        self.assert_false(empty_pos.is_mock)
        self.assert_true(empty_pos.is_empty)
        empty_tag_set = empty_pos.get_tag_set()
        self.assert_true(self.empty_type_tag in empty_tag_set)
        self.assert_false(self.mdp_tag in empty_tag_set)

    def test_has_tag(self):
        tf_pos = TransfectionPosition(**self.init_data)
        self.assert_true(tf_pos.has_tag(self.fixed_type_tag))
        self.assert_false(tf_pos.has_tag(self.empty_type_tag))

    def test_hash_full(self):
        tf_pos = TransfectionPosition(**self.init_data)
        self.assert_equal(tf_pos.hash_full, '205200Mix114005')
        empty_pos = TransfectionPosition.create_empty_position(self.rack_pos)
        empty_hash = 'A1'
        self.assert_equal(empty_pos.hash_full, empty_hash)
        self.init_data['iso_concentration'] = MOCK_POSITION_TYPE
        self.init_data['molecule_design_pool'] = MOCK_POSITION_TYPE
        self.init_data['final_concentration'] = MOCK_POSITION_TYPE
        self.init_data['supplier'] = None
        mock_pos = TransfectionPosition(**self.init_data)
        self.assert_equal(mock_pos.hash_full, 'mockMix11400None')
        ut_pos = TransfectionPosition.create_untreated_position(self.rack_pos)
        self.assert_equal(ut_pos.hash_full, empty_hash)

    def test_hash_partial(self):
        tf_pos = TransfectionPosition(**self.init_data)
        exp_hash = '205200Mix11400'
        self.assert_equal(tf_pos.hash_partial, exp_hash)
        empty_pos = TransfectionPosition.create_empty_position(self.rack_pos)
        empty_hash = 'A1'
        self.assert_equal(empty_pos.hash_partial, empty_hash)
        ut_pos = TransfectionPosition.create_untreated_position(self.rack_pos)
        self.assert_equal(ut_pos.hash_full, empty_hash)

    def test_copy(self):
        tf_pos1 = TransfectionPosition(**self.init_data)
        tf_pos2 = tf_pos1.copy()
        self.assert_equal(tf_pos1, tf_pos2)
        tf_pos2.reagent_name = 'other'
        self.assert_not_equal(tf_pos1, tf_pos2)

    def test_add_cell_plate_position(self):
        tf_pos = TransfectionPosition(**self.init_data)
        self.assert_equal(len(tf_pos.cell_plate_positions), 0)
        tf_pos.add_cell_plate_position(self.rack_pos)
        self.assert_equal(len(tf_pos.cell_plate_positions), 1)
        self.assert_raises(ValueError, tf_pos.add_cell_plate_position,
                           self.rack_pos)
        ut_pos = TransfectionPosition.create_untreated_position(self.rack_pos)
        self.assert_raises(AttributeError, ut_pos.add_cell_plate_position,
                           self.rack_pos)

    def test_calculate_reagent_dilution_volume(self):
        tf_pos = TransfectionPosition(**self.init_data)
        tf_pos.store_optimem_dilution_factor()
        self.assert_equal(tf_pos.calculate_reagent_dilution_volume(), 30)
        ut_pos = TransfectionPosition.create_untreated_position(self.rack_pos)
        self.assert_is_none(ut_pos.calculate_reagent_dilution_volume())

    def test_get_optimem_dilution_factor(self):
        tf_pos = TransfectionPosition(**self.init_data)
        tf_pos.store_optimem_dilution_factor()
        self.assert_equal(tf_pos.optimem_dil_factor, 4)
        self.init_data['molecule_design_pool'] = MOCK_POSITION_TYPE
        self.init_data['supplier'] = None
        self.init_data['final_concentration'] = None
        self.init_data['iso_concentration'] = None
        mock_pos = TransfectionPosition(**self.init_data)
        self.assert_is_none(mock_pos.optimem_dil_factor)
        mock_pos.set_optimem_dilution_factor(4)
        self.assert_equal(mock_pos.optimem_dil_factor, 4)

    def test_get_total_dilution_factor(self):
        tf_pos = TransfectionPosition(**self.init_data)
        tf_pos.store_optimem_dilution_factor()
        self.assert_equal(tf_pos.get_total_dilution_factor(), 56)
        self.init_data['molecule_design_pool'] = MOCK_POSITION_TYPE
        self.init_data['supplier'] = None
        self.init_data['final_concentration'] = None
        self.init_data['iso_concentration'] = None
        mock_pos = TransfectionPosition(**self.init_data)
        self.assert_is_none(mock_pos.get_total_dilution_factor())
        mock_pos.set_optimem_dilution_factor(3)
        self.assert_equal(mock_pos.get_total_dilution_factor(), 42)

    def test_supports_mastermix(self):
        tf_pos = TransfectionPosition(**self.init_data)
        tf_pos.store_optimem_dilution_factor()
        self.assert_false(tf_pos.supports_mastermix_preparation())
        tf_pos.final_concentration = None
        self.assert_is_none(tf_pos.supports_mastermix_preparation())
        tf_pos.final_concentration = self.final_concentration
        tf_pos.iso_concentration = None
        self.assert_is_none(tf_pos.supports_mastermix_preparation())
        tf_pos.final_concentration = 1
        tf_pos.iso_concentration = tf_pos.get_total_dilution_factor()
        self.assert_true(tf_pos.supports_mastermix_preparation())
        mock_pos = TransfectionPosition(rack_position=self.rack_pos,
                    molecule_design_pool=TransfectionParameters.MOCK_TYPE_VALUE)
        self.assert_true(mock_pos.supports_mastermix_preparation())


class TransfectionLayoutTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.shape = get_96_rack_shape()
        self.source_rack = '13'
        self.dest_rack = '78'
        self.a1_pos = get_rack_position_from_label('A1')
        self.a2_pos = get_rack_position_from_label('A2')
        self.a4_pos = get_rack_position_from_label('A4')
        self.b1_pos = get_rack_position_from_label('B1')
        self.b2_pos = get_rack_position_from_label('B2')
        self.pool_id = 205200
        self.molecule_design_pool = self._get_entity(IMoleculeDesignPool,
                                                     str(self.pool_id))
        self.pool_id_tag = Tag('iso', 'molecule_design_pool_id', '205200')
        self.iso_volume = 5
        self.iso_vol_tag = Tag('iso', 'iso_volume', '5')
        self.iso_concentration = 50
        self.iso_conc_tag = Tag('iso', 'iso_concentration', '50')
        self.iso_pos_type_tag = Tag('iso', 'position_type', 'fixed')
        self.supplier = self._create_organization(name='Abgene')
        self.supplier_tag = Tag('iso', 'supplier', 'Abgene')
        self.reagent_name = 'reagent I'
        self.reagent_name_tag = Tag('transfection', 'reagent_name',
                                    self.reagent_name)
        self.reagent_dil_factor = 0.04
        self.reagent_conc_tag = Tag('transfection', 'reagent_dilution_factor',
                                    '0.04')
        self.transfer_volume = 10
        self.transfer_vol_tag = Tag('sample_transfer', 'transfer_volume', '10')
        self.final_concentration = 7
        self.final_conc_tag = Tag('transfection', 'final_concentration', '7')
        self.optimem_df = 4
        self.optimem_df_tag = Tag('transfection', 'optimem_dilution_factor',
                                  '4')
        self.empty_iso_pos = IsoPosition(rack_position=self.a1_pos)
        self.empty_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                             IsoParameters.EMPTY_TYPE_VALUE)
        self.untreated_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                                 IsoParameters.UNTREATED_TYPE_VALUE)
        self.untreated_md_tag = Tag(IsoParameters.DOMAIN,
                                    IsoParameters.MOLECULE_DESIGN_POOL,
                                    IsoParameters.UNTREATED_TYPE_VALUE)
        self.untreated_fc_tag = Tag(TransfectionParameters.DOMAIN,
                                    TransfectionParameters.FINAL_CONCENTRATION,
                                    UNTREATED_POSITION_TYPE)
        self.a1_tp = TransfectionPosition(rack_position=self.a1_pos,
                                molecule_design_pool=self.molecule_design_pool,
                                iso_concentration=self.iso_concentration,
                                iso_volume=self.iso_volume,
                                supplier=self.supplier,
                                reagent_name=self.reagent_name,
                                reagent_dil_factor=self.reagent_dil_factor)
        self.a1_tp.set_optimem_dilution_factor(self.optimem_df)
        self.a2_tp = TransfectionPosition(rack_position=self.a2_pos,
                                molecule_design_pool=self.molecule_design_pool,
                                iso_concentration=self.iso_concentration,
                                iso_volume=self.iso_volume,
                                reagent_name=self.reagent_name,
                                reagent_dil_factor=self.reagent_dil_factor)
        self.b1_tp = TransfectionPosition.create_empty_position(self.b1_pos)
        self.b2_tp = TransfectionPosition.create_untreated_position(self.b2_pos,
                                    final_concentration=UNTREATED_POSITION_TYPE,
                                    reagent_name=None, reagent_dil_factor=None)

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.shape
        del self.source_rack
        del self.dest_rack
        del self.a1_pos
        del self.a2_pos
        del self.a4_pos
        del self.b1_pos
        del self.b2_pos
        del self.molecule_design_pool
        del self.pool_id
        del self.pool_id_tag
        del self.iso_volume
        del self.iso_vol_tag
        del self.iso_concentration
        del self.iso_conc_tag
        del self.iso_pos_type_tag
        del self.supplier
        del self.supplier_tag
        del self.reagent_name
        del self.reagent_name_tag
        del self.reagent_dil_factor
        del self.reagent_conc_tag
        del self.transfer_volume
        del self.transfer_vol_tag
        del self.final_concentration
        del self.final_conc_tag
        del self.optimem_df
        del self.optimem_df_tag
        del self.empty_iso_pos
        del self.empty_tag
        del self.untreated_tag
        del self.untreated_md_tag
        del self.untreated_fc_tag
        del self.a1_tp
        del self.a2_tp
        del self.b1_tp
        del self.b2_tp

    def __create_test_layout(self):
        layout = TransfectionLayout(self.shape)
        layout.add_position(self.a1_tp)
        layout.add_position(self.a2_tp)
        layout.add_position(self.b1_tp)
        layout.add_position(self.b2_tp)
        return  layout

    def test_init(self):
        tl = TransfectionLayout(self.shape)
        self.assert_false(tl is None)
        self.assert_equal(tl.shape, self.shape)
        self.assert_equal(len(tl), 0)

    def test_add_position(self):
        tl = TransfectionLayout(self.shape)
        self.assert_equal(len(tl), 0)
        tl.add_position(self.a1_tp)
        self.assert_equal(len(tl), 1)
        self.assert_equal(tl.get_working_position(self.a1_pos), self.a1_tp)
        empty_iso_pos = IsoPosition(rack_position=self.b1_pos)
        self.assert_raises(TypeError, tl.add_position, empty_iso_pos)

    def test_get_position(self):
        tl = self.__create_test_layout()
        self.assert_equal(tl.get_working_position(self.a1_pos), self.a1_tp)
        self.assert_equal(tl.get_working_position(self.a4_pos), None)

    def test_transfer_layout_equality(self):
        tl1 = self.__create_test_layout()
        tl2 = self.__create_test_layout()
        tl3 = TransfectionLayout(self.shape)
        tl3.add_position(self.a1_tp)
        tl3.add_position(self.a2_tp)
        self.assert_equal(tl1, tl2)
        self.assert_not_equal(tl1, tl3)

    def test_get_tags(self):
        tl = self.__create_test_layout()
        tag_set = tl.get_tags()
        tags = [self.pool_id_tag, self.iso_vol_tag, self.iso_conc_tag,
                self.reagent_name_tag, self.reagent_conc_tag, self.empty_tag,
                self.iso_pos_type_tag, self.supplier_tag, self.optimem_df_tag,
                self.untreated_tag, self.untreated_md_tag,
                self.untreated_fc_tag]
        self._compare_tag_sets(tags, tag_set)

    def test_get_positions(self):
        tl = self.__create_test_layout()
        pos_set = tl.get_positions()
        positions = [self.a1_pos, self.b1_pos, self.a2_pos, self.b2_pos]
        self._compare_pos_sets(positions, pos_set)

    def test_get_tags_for_positions(self):
        tl = self.__create_test_layout()
        tags_a1 = [self.pool_id_tag, self.iso_vol_tag, self.iso_conc_tag,
                self.reagent_name_tag, self.reagent_conc_tag,
                self.iso_pos_type_tag, self.supplier_tag, self.optimem_df_tag]
        tag_set_a1 = tl.get_tags_for_position(self.a1_pos)
        self._compare_tag_sets(tags_a1, tag_set_a1)
        tags_a2 = [self.pool_id_tag, self.iso_vol_tag, self.iso_conc_tag,
                self.reagent_name_tag, self.reagent_conc_tag,
                self.iso_pos_type_tag]
        tag_set_a2 = tl.get_tags_for_position(self.a2_pos)
        self._compare_tag_sets(tags_a2, tag_set_a2)
        self.assert_false(self.empty_tag in tag_set_a1)
        tags_b1 = [self.empty_tag]
        tag_set_b1 = tl.get_tags_for_position(self.b1_pos)
        self._compare_tag_sets(tags_b1, tag_set_b1)
        self.assert_false(self.pool_id_tag in tag_set_b1)

    def test_get_position_for_tag(self):
        tl = self.__create_test_layout()
        pos1 = [self.a1_pos, self.a2_pos]
        pos_set1 = tl.get_positions_for_tag(self.pool_id_tag)
        self._compare_pos_sets(pos1, pos_set1)
        self.assert_false(self.b1_pos in pos_set1)
        pos2 = [self.b1_pos]
        pos_set2 = tl.get_positions_for_tag(self.empty_tag)
        self._compare_pos_sets(pos2, pos_set2)
        self.assert_false(self.a1_pos in pos_set2)
        self.assert_equal(tl.get_positions_for_tag(self.pool_id_tag),
                          tl.get_positions_for_tag(self.reagent_name_tag))
        pos_supplier = [self.a1_pos]
        pos_set_supplier = tl.get_positions_for_tag(self.supplier_tag)
        self._compare_pos_sets(pos_supplier, pos_set_supplier)

    def test_close(self):
        tl = self.__create_test_layout()
        self.assert_equal(len(tl), 4)
        self.assert_false(tl.is_closed)
        tl.close()
        self.assert_equal(len(tl), 3)
        self.assert_true(tl.is_closed)
        self.assert_raises(AttributeError, tl.add_position, self.b1_tp)

    def test_create_rack_layout(self):
        tl = self.__create_test_layout()
        empty_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                        IsoParameters.EMPTY_TYPE_VALUE)
        self.assert_false(tl.is_closed)
        self.assert_true(empty_tag in tl.get_tags())
        rack_layout = tl.create_rack_layout()
        self.assert_true(tl.is_closed)
        self.assert_false(empty_tag in tl.get_tags())
        self.assert_is_not_none(rack_layout)
        self.assert_not_equal(tl, rack_layout)
        self.assert_equal(tl.shape, rack_layout.shape)
        trps_list = rack_layout.tagged_rack_position_sets
        self.assert_equal(len(trps_list), 3)
        self.assert_equal(tl.get_tags(), rack_layout.get_tags())
        self.assert_equal(set(tl.get_positions()), rack_layout.get_positions())
        self.assert_equal(tl.get_positions_for_tag(self.pool_id_tag),
                rack_layout.get_positions_for_tag(self.pool_id_tag))
        self.assert_equal(tl.get_tags_for_position(self.a1_pos),
                          rack_layout.get_tags_for_position(self.a1_pos))

    def test_ambiguous_wells(self):
        tl = TransfectionLayout(self.shape)
        tl.add_position(self.a1_tp)
        self.a2_tp.reagent_name = 'other name'
        tl.add_position(self.a2_tp)
        duplicates = tl.get_ambiguous_wells()
        self.assert_equal(len(duplicates), 0)
        self.a2_tp.reagent_name = self.reagent_name
        tl2 = TransfectionLayout(self.shape)
        tl2.add_position(self.a1_tp)
        tl2.add_position(self.a2_tp)
        duplicates2 = tl2.get_ambiguous_wells()
        self.assert_equal(len(duplicates2), 1)
        duplicate_tup = ('A2', 'A1')
        self.assert_equal(duplicates2[0], duplicate_tup)

    def test_copy(self):
        tl = self.__create_test_layout()
        tl2 = tl.copy()
        self.assert_equal(tl, tl2)
        f7_tp = self.a1_tp.copy()
        f7_pos = get_rack_position_from_label('F7')
        f7_tp.rack_position = f7_pos
        tl2.add_position(f7_tp)
        self.assert_not_equal(tl, tl2)

    def test_has_iso_concentrations(self):
        tl = self.__create_test_layout()
        self.assert_true(tl.has_iso_concentrations())
        self.a1_tp.iso_concentration = None
        self.a2_tp.iso_concentration = None
        tl2 = self.__create_test_layout()
        self.assert_false(tl2.has_iso_concentrations())

    def test_has_iso_volumes(self):
        tl = self.__create_test_layout()
        self.assert_true(tl.has_iso_volumes())
        self.a1_tp.iso_volume = None
        self.a2_tp.iso_volume = None
        tl2 = self.__create_test_layout()
        self.assert_false(tl2.has_iso_volumes())

    def test_has_final_concentrations(self):
        tl = self.__create_test_layout()
        self.assert_false(tl.has_final_concentrations())
        tf_pos = tl.working_positions()[0]
        tf_pos.final_concentration = self.final_concentration
        self.assert_true(tl.has_final_concentrations())


class TransfectionLayoutConverterTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.rack_layout = None
        self.is_iso_layout = True
        self.is_mastermix_template = False
        self.check_well_uniqueness = False
        self.log = TestingLog()
        self.shape = get_96_rack_shape()
        self.a1_pos = get_rack_position_from_label('A1')
        self.b1_pos = get_rack_position_from_label('B1')
        self.c1_pos = get_rack_position_from_label('C1')
        self.d1_pos = get_rack_position_from_label('D1')
        self.e1_pos = get_rack_position_from_label('E1')
        self.empty_type_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                                  IsoParameters.EMPTY_TYPE_VALUE)
        self.fixed_type_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                                  IsoParameters.FIXED_TYPE_VALUE)
        self.mock_type_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                                 IsoParameters.MOCK_TYPE_VALUE)
        self.float_type_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                                  IsoParameters.FLOATING_TYPE_VALUE)
        self.md_tag = Tag(IsoParameters.DOMAIN,
                          IsoParameters.MOLECULE_DESIGN_POOL, '205200')
        self.md_float_tag = Tag(IsoParameters.DOMAIN,
                                IsoParameters.MOLECULE_DESIGN_POOL,
                                '%s1' % (IsoParameters.FLOATING_INDICATOR))
        self.md_mock_tag = Tag(IsoParameters.DOMAIN,
                               IsoParameters.MOLECULE_DESIGN_POOL,
                               IsoParameters.MOCK_TYPE_VALUE)
        self.reagent_name_tag = Tag(TransfectionParameters.DOMAIN,
                                    TransfectionParameters.REAGENT_NAME,
                                    'mix1')
        self.reagent_df1_tag = Tag(TransfectionParameters.DOMAIN,
                                   TransfectionParameters.REAGENT_DIL_FACTOR,
                                   '1400')
        self.reagent_df2_tag = Tag(TransfectionParameters.DOMAIN,
                                   TransfectionParameters.REAGENT_DIL_FACTOR,
                                   '2800')
        self.volume1_tag = Tag(IsoParameters.DOMAIN, IsoParameters.ISO_VOLUME,
                              '2')
        self.volume2_tag = Tag(IsoParameters.DOMAIN, IsoParameters.ISO_VOLUME,
                              '4')
        self.supplier_tag = Tag(IsoParameters.DOMAIN, IsoParameters.SUPPLIER,
                               'Nunc')
        self.iso_conc_tag = Tag(IsoParameters.DOMAIN,
                                IsoParameters.ISO_CONCENTRATION, '50')
        self.final_conc_tag = Tag(TransfectionParameters.DOMAIN,
                                  TransfectionParameters.FINAL_CONCENTRATION,
                                  '10')
        self.optimem_df_tag = Tag('transfection', 'optimem_dilution_factor',
                                  '4')
        self.other_tag = Tag('test', 'something', 'unimportant')

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.rack_layout
        del self.is_iso_layout
        del self.is_mastermix_template
        del self.check_well_uniqueness
        del self.log
        del self.shape
        del self.a1_pos
        del self.b1_pos
        del self.c1_pos
        del self.d1_pos
        del self.e1_pos
        del self.empty_type_tag
        del self.fixed_type_tag
        del self.mock_type_tag
        del self.float_type_tag
        del self.md_tag
        del self.md_float_tag
        del self.md_mock_tag
        del self.reagent_name_tag
        del self.reagent_df1_tag
        del self.reagent_df2_tag
        del self.volume1_tag
        del self.volume2_tag
        del self.supplier_tag
        del self.iso_conc_tag
        del self.final_conc_tag
        del self.optimem_df_tag
        del self.other_tag

    def _create_tool(self):
        self.tool = TransfectionLayoutConverter(rack_layout=self.rack_layout,
                            is_iso_layout=self.is_iso_layout,
                            is_mastermix_template=self.is_mastermix_template,
                            check_well_uniqueness=self.check_well_uniqueness,
                            log=self.log)

    def _test_and_expect_errors(self, msg=None, add_pos_tags=None): #pylint:disable=W0221
        self.__create_test_layout()
        if not add_pos_tags is None:
            self.__add_additional_position(add_pos_tags)
        ToolsAndUtilsTestCase._test_and_expect_errors(self, msg=msg)

    def __create_test_layout(self):
        trps_sets = []
        a_tags = [self.md_tag, self.supplier_tag, self.fixed_type_tag]
        a_positions = [self.a1_pos]
        a_trps = self._create_test_trp_set(a_tags, a_positions)
        trps_sets.append(a_trps)
        b_tags = [self.md_float_tag, self.float_type_tag]
        b_positions = [self.b1_pos]
        b_trps = self._create_test_trp_set(b_tags, b_positions)
        trps_sets.append(b_trps)
        c_tags = [self.md_mock_tag, self.mock_type_tag]
        c_positions = [self.c1_pos]
        c_trps = self._create_test_trp_set(c_tags, c_positions)
        trps_sets.append(c_trps)
        d_tags = [self.empty_type_tag]
        d_positions = [self.d1_pos]
        d_trps = self._create_test_trp_set(d_tags, d_positions)
        trps_sets.append(d_trps)
        ab_tags = [self.iso_conc_tag, self.final_conc_tag]
        ab_positions = [self.a1_pos, self.b1_pos]
        ab_trps = self._create_test_trp_set(ab_tags, ab_positions)
        trps_sets.append(ab_trps)
        abc_tags = [self.volume1_tag, self.other_tag, self.optimem_df_tag,
                    self.reagent_name_tag, self.reagent_df1_tag]
        abc_positions = [self.a1_pos, self.b1_pos, self.c1_pos]
        abc_trps = self._create_test_trp_set(abc_tags, abc_positions)
        trps_sets.append(abc_trps)
        self.rack_layout = RackLayout(shape=self.shape,
                           tagged_rack_position_sets=trps_sets)

    def __add_additional_position(self, tags):
        e_trps = self._create_test_trp_set(tags, [self.e1_pos])
        self.rack_layout.tagged_rack_position_sets.append(e_trps)

    def test_result(self):
        self.__create_test_layout()
        self._create_tool()
        tl = self.tool.get_result()
        self.assert_is_not_none(tl)
        tags = [self.fixed_type_tag, self.md_tag, self.float_type_tag,
                self.md_float_tag, self.mock_type_tag, self.md_mock_tag,
                self.volume1_tag, self.iso_conc_tag, self.reagent_name_tag,
                self.reagent_df1_tag, self.supplier_tag, self.final_conc_tag,
                self.optimem_df_tag]
        tag_set = tl.get_tags()
        self._compare_tag_sets(tags, tag_set)
        self.assert_false(self.empty_type_tag in tag_set)
        positions = [self.a1_pos, self.b1_pos, self.c1_pos]
        pos_set = tl.get_positions()
        self._compare_pos_sets(positions, pos_set)
        b1_tags = [self.float_type_tag, self.md_float_tag, self.volume1_tag,
                   self.iso_conc_tag, self.reagent_df1_tag,
                   self.reagent_name_tag, self.final_conc_tag,
                   self.optimem_df_tag]
        b1_tag_set = tl.get_tags_for_position(self.b1_pos)
        self._compare_tag_sets(b1_tags, b1_tag_set)
        mock_tags = [self.md_mock_tag, self.mock_type_tag, self.volume1_tag,
                     self.reagent_name_tag, self.reagent_df1_tag,
                     self.optimem_df_tag]
        mock_tag_set = tl.get_tags_for_position(self.c1_pos)
        self._compare_tag_sets(mock_tags, mock_tag_set)
        mock_pos = [self.c1_pos]
        mock_pos_set = tl.get_positions_for_tag(self.md_mock_tag)
        self._compare_pos_sets(mock_pos, mock_pos_set)

    def test_result_is_iso_layout(self):
        self.volume1_tag = Tag('test', 'no', 'iso_volume')
        self.iso_conc_tag = Tag('test', 'no', 'iso_concentration')
        self.is_iso_layout = False
        self.__create_test_layout()
        self._create_tool()
        tl = self.tool.get_result()
        self.assert_is_not_none(tl)
        tags = [self.fixed_type_tag, self.md_tag, self.float_type_tag,
                self.md_float_tag, self.mock_type_tag, self.md_mock_tag,
                self.final_conc_tag, self.reagent_name_tag,
                self.reagent_df1_tag, self.supplier_tag]
        tag_set = tl.get_tags()
        self._compare_tag_sets(tags, tag_set)
        self.assert_equal(len(tl), 3)
        b1_tags = [self.float_type_tag, self.md_float_tag, self.final_conc_tag,
                   self.reagent_df1_tag, self.reagent_name_tag]
        b1_tag_set = tl.get_tags_for_position(self.b1_pos)
        self._compare_tag_sets(b1_tags, b1_tag_set)
        mock_pos = [self.c1_pos]
        mock_pos_set = tl.get_positions_for_tag(self.md_mock_tag)
        self._compare_pos_sets(mock_pos, mock_pos_set)
        self.is_iso_layout = True
        self._test_and_expect_errors()

    def test_result_is_mastermix_template(self):
        self.reagent_name_tag = Tag('test', 'no', 'reagent_name')
        self.__create_test_layout()
        self._create_tool()
        tl = self.tool.get_result()
        self.assert_is_not_none(tl)
        self.is_iso_layout = False
        self.is_mastermix_template = True
        self._test_and_expect_errors('no reagent_name specification')

    def test_result_no_position_types(self):
        self.is_iso_layout = False
        self.fixed_type_tag = Tag('no', 'fixed', 'pos_type')
        self.float_type_tag = Tag('no', 'float', 'pos_type')
        self.mock_type_tag = Tag('no', 'mock', 'pos_type')
        self.empty_type_tag = Tag('no', 'empty', 'pos_type')
        self.__create_test_layout()
        self._create_tool()
        tl = self.tool.get_result()
        self.assert_is_not_none(tl)
        self.empty_type_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                                  EMPTY_POSITION_TYPE)
        self.fixed_type_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                                  FIXED_POSITION_TYPE)
        self.mock_type_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                                 MOCK_POSITION_TYPE)
        self.float_type_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                                  FLOATING_POSITION_TYPE)
        tags = [self.fixed_type_tag, self.md_tag, self.float_type_tag,
                self.md_float_tag, self.mock_type_tag, self.md_mock_tag,
                self.final_conc_tag, self.reagent_name_tag,
                self.reagent_df1_tag, self.supplier_tag]
        tag_set = tl.get_tags()
        self._compare_tag_sets(tags, tag_set)
        self.assert_equal(len(tl), 3)
        b1_tags = [self.float_type_tag, self.md_float_tag,
                   self.final_conc_tag, self.reagent_df1_tag,
                   self.reagent_name_tag]
        b1_tag_set = tl.get_tags_for_position(self.b1_pos)
        self._compare_tag_sets(b1_tags, b1_tag_set)
        mock_pos = [self.c1_pos]
        mock_pos_set = tl.get_positions_for_tag(self.md_mock_tag)
        self._compare_pos_sets(mock_pos, mock_pos_set)

    def test_result_mock_and_none_values_for_mocks(self):
        self.__create_test_layout()
        conc_mk_tag = Tag(IsoParameters.DOMAIN, IsoParameters.ISO_CONCENTRATION,
                         'mock')
        fc_mk_tag = Tag(TransfectionParameters.DOMAIN,
                       TransfectionParameters.FINAL_CONCENTRATION, 'mock')
        tags_mk = [self.md_mock_tag, conc_mk_tag, fc_mk_tag, self.volume1_tag,
                   self.reagent_name_tag, self.reagent_df2_tag,
                   self.optimem_df_tag]
        g1_pos = get_rack_position_from_label('G1')
        trps_mk = self._create_test_trp_set(tags_mk, [g1_pos])
        self.rack_layout.tagged_rack_position_sets.append(trps_mk)
        self._create_tool()
        tl = self.tool.get_result()
        tags = [self.md_mock_tag, self.mock_type_tag, self.reagent_name_tag,
                self.reagent_df2_tag, self.volume1_tag, self.optimem_df_tag,
                conc_mk_tag, fc_mk_tag]
        tag_set_mk = tl.get_tags_for_position(g1_pos)
        self._compare_tag_sets(tags, tag_set_mk)
        self.__create_test_layout()
        tags_none = [self.md_mock_tag, self.reagent_name_tag,
                     self.reagent_df2_tag, self.volume1_tag]
        trps_none = self._create_test_trp_set(tags_none, [g1_pos])
        self.rack_layout.tagged_rack_position_sets.append(trps_none)
        tl2 = self.tool.get_result()
        tag_set_none = tl2.get_tags_for_position(g1_pos)
        self._compare_tag_sets(tags, tag_set_none)

    def test_double_specifications(self):
        self.other_tag = Tag(TransfectionParameters.DOMAIN,
                             TransfectionParameters.REAGENT_NAME, 'add_name')
        self._test_and_expect_errors('specified multiple times')

    def test_missing_molecule_design(self):
        md_tags = [self.md_tag, self.md_mock_tag, self.md_float_tag]
        for tag in md_tags:
            tag.predicate = 'md'
        self._test_and_expect_errors('no molecule_design_pool_id specification')

    def test_unknown_molecule_design_pool_id(self):
        self.md_tag.value = '99'
        self._test_and_expect_errors('molecule design pool IDs could not be ' \
                                     'found in the DB')

    def test_unknown_position_type(self):
        self.md_tag.value = 'default'
        self.fixed_type_tag.predicate = 'other'
        self._test_and_expect_errors('Unable to determine position types for ' \
                                     'the following pool IDs')

    def test_missing_iso_volume(self):
        no_vol_tags = [self.md_tag, self.fixed_type_tag, self.iso_conc_tag,
                       self.reagent_name_tag, self.reagent_df2_tag,
                       self.optimem_df_tag]
        self._test_and_expect_errors('do not have an ISO volume',
                                     add_pos_tags=no_vol_tags)

    def test_invalid_volume(self):
        self.volume1_tag.value = '4-5'
        self._test_and_expect_errors('invalid ISO volumes')

    def test_missing_iso_concentration(self):
        no_conc_tags = [self.md_tag, self.fixed_type_tag, self.volume2_tag,
                       self.reagent_name_tag, self.reagent_df2_tag,
                       self.optimem_df_tag]
        self._test_and_expect_errors('do not have an ISO concentration',
                                     add_pos_tags=no_conc_tags)

    def test_invalid_concentration(self):
        self.iso_conc_tag.value = '4-5'
        self._test_and_expect_errors('invalid ISO concentrations')

    def test_unknown_supplier(self):
        self.supplier_tag = Tag(IsoParameters.DOMAIN, IsoParameters.SUPPLIER,
                                'test_supplier')
        self._test_and_expect_errors('suppliers could not be found in the DB')

    def test_invalid_supplier(self):
        invalid_supplier_tags = [self.mock_type_tag, self.supplier_tag,
                                 self.volume1_tag, self.iso_conc_tag,
                                 self.reagent_df2_tag, self.reagent_name_tag,
                                 self.md_mock_tag, self.optimem_df_tag]
        self._test_and_expect_errors(add_pos_tags=invalid_supplier_tags,
                msg='supplier specified for the following non-fixed position')

    def test_empty_and_values(self):
        empty_and_value_tags = [self.empty_type_tag, self.volume1_tag]
        self._test_and_expect_errors(add_pos_tags=empty_and_value_tags,
                        msg='specifications for some empty positions')

    def test_untreated_and_values(self):
        untreated_tags = [Tag(IsoParameters.DOMAIN,
                              IsoParameters.MOLECULE_DESIGN_POOL,
                              UNTREATED_POSITION_TYPE),
                          Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                              UNTREATED_POSITION_TYPE),
                          self.volume1_tag]
        self._test_and_expect_errors(add_pos_tags=untreated_tags,
                 msg='There are invalid parameter specifications for some ' \
                     'untreated positions')

    def test_invalid_reagent_name(self):
        self.reagent_name_tag.value = '2'
        self._test_and_expect_errors('invalid reagent names')

    def test_invalid_dil_factor(self):
        self.reagent_df1_tag.value = '4-5'
        self._test_and_expect_errors('invalid reagent dilution factors')

    def test_invalid_final_concentration(self):
        self.is_iso_layout = False
        self.final_conc_tag.value = '4-5'
        self._test_and_expect_errors('invalid final concentration')

    def test_invalid_optimem_dilution_factor(self):
        self.optimem_df_tag.value = 'default'
        self._test_and_expect_errors(msg='invalid OptiMem dilution factors')

    def test_missing_reagent_name(self):
        self.is_iso_layout = False
        self.is_mastermix_template = True
        no_name_tags = [self.md_tag, self.reagent_df2_tag,
                        self.final_conc_tag]
        self._test_and_expect_errors(add_pos_tags=no_name_tags,
                                     msg='not have a reagent name')

    def test_missing_reagent_dilution_factor(self):
        self.is_iso_layout = False
        self.is_mastermix_template = True
        no_dil_factor_tags = [self.md_tag, self.reagent_name_tag,
                              self.final_conc_tag]
        self._test_and_expect_errors(add_pos_tags=no_dil_factor_tags,
                                msg='do not have a reagent dilution factor')

    def test_missing_final_conc(self):
        self.is_iso_layout = False
        self.is_mastermix_template = True
        no_final_conc_tags = [self.md_tag, self.reagent_name_tag,
                              self.reagent_df2_tag]
        self._test_and_expect_errors(add_pos_tags=no_final_conc_tags,
                              msg='not have a final concentration')

    def test_missing_optimem_dilution_factor(self):
        no_optimem_df_tags = [self.md_tag, self.reagent_name_tag,
                              self.reagent_df2_tag, self.final_conc_tag,
                              self.volume1_tag, self.iso_conc_tag]
        self._test_and_expect_errors(add_pos_tags=no_optimem_df_tags,
                                msg='not have an OptiMem dilution factor')

    def test_check_duplicate_quartets(self):
        self.md_float_tag = self.md_tag
        self.float_type_tag = self.other_tag
        self.__create_test_layout()
        self._create_tool()
        tl = self.tool.get_result()
        self.assert_is_not_none(tl)
        self.check_well_uniqueness = True
        self._test_and_expect_errors('cannot be identified uniquely')

    def test_iso_and_mastermix(self):
        self.is_mastermix_template = True
        self._test_and_expect_errors('cannot be a mastermix layout and an ISO')

    def test_uniqueness_check_unspecified(self):
        self.check_well_uniqueness = None
        self._test_and_expect_errors('In case of ISO layouts you need to ' \
                    'specify whether you want to check the well uniqueness!')


class TransfectionRackSectorTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.log = TestingLog()
        self.transfection_layout = None
        self.number_sectors = 4
        self.rack_shape = get_384_rack_shape()
        # pos label - pool id, final conc, iso conc
        self.position_data = dict(
                A4=['md_1', 1, 50], B3=['md_2', 2, 100], B4=['md_1', 3, 150],
                A6=[205203, 1, 50], B5=[205203, 2, 100], B6=[205203, 3, 150],
                C2=['md_5', 1, 50], D1=['md_6', 2, 100], D2=['md_5', 3, 150],
                C4=[None], D3=[None], D4=[None],
                E2=['md_9', 1, 50], F1=['md_9', 2, 100], F2=['md_9', 3, 150])
        self.one_sector_data = dict(
                A4=['md_1', 1, 50], B3=['md_1', 1, 50], B4=['md_1', 1, 50],
                A6=[205203, 1, 50], B5=[205204, 1, 50], B6=[205205, 1, 50],
                C2=['md_3', 1, 50], D1=['md_3', 1, 50], D2=['md_3', 1, 50],
                C4=[None], D5=[None], D6=[None])

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.log
        del self.transfection_layout
        del self.number_sectors
        del self.rack_shape
        del self.position_data
        del self.one_sector_data

    def _continue_setup(self):
        self.__create_transfection_layout()
        self._create_tool()

    def __create_transfection_layout(self):
        self.transfection_layout = TransfectionLayout(shape=self.rack_shape)
        for pos_label, pos_data in self.position_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            pool_id = pos_data[0]
            if pool_id is None:
                tf_pos = TransfectionPosition.create_empty_position(rack_pos)
                self.transfection_layout.add_position(tf_pos)
                continue
            pool = self._get_pool(pool_id)
            final_conc = pos_data[1]
            iso_conc = pos_data[2]
            tf_pos = TransfectionPosition(rack_position=rack_pos,
                                          molecule_design_pool=pool,
                                          iso_concentration=iso_conc,
                                          final_concentration=final_conc)
            self.transfection_layout.add_position(tf_pos)

class TransfectionRackSectorAssociatorTestCase(TransfectionRackSectorTestCase):

    def _create_tool(self):
        self.tool = TransfectionRackSectorAssociator(log=self.log,
                            number_sectors=self.number_sectors,
                            transfection_layout=self.transfection_layout)

    def test_result(self):
        self._continue_setup()
        associated_sectors = self.tool.get_result()
        self.assert_is_not_none(associated_sectors)
        exp_result = [[1, 2, 3]]
        self.assert_equal(associated_sectors, exp_result)
        final_concentrations = self.tool.get_sector_concentrations()
        exp_fc = {0: None, 1 : 1, 2 : 2, 3 : 3}
        self.assert_equal(final_concentrations, exp_fc)

    def test_invalid_transfection_layout(self):
        self._continue_setup()
        self.transfection_layout = None
        self._test_and_expect_errors('The working layout must be a ' \
                                     'TransfectionLayout object')

    def test_invalid_number_sectors(self):
        self._continue_setup()
        self.number_sectors = 3.4
        self._test_and_expect_errors('The number of sectors must be a int')

    def test_inconsistent_rack_sectors(self):
        self.position_data['D1'][1] = 4
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to determine rack ' \
                                     'sector concentrations.')

    def test_inconsistent_molecule_designs(self):
        del self.position_data['B3']
        self._continue_setup()
        self._test_and_expect_errors('The molecule design pools in the ' \
                                     'different quadrants are not consistent')

class TransfectionAssociationDataTestCase(TransfectionRackSectorTestCase):

    def _get_association_data(self):
        return TransfectionAssociationData(log=self.log,
                                transfection_layout=self.transfection_layout)

    def test_result_4(self):
        self._continue_setup()
        ad = self._get_association_data()
        self.assert_is_not_none(ad)
        associated_sectors = ad.associated_sectors
        exp_as = [[1, 2, 3]]
        self.assert_equal(associated_sectors, exp_as)
        sector_concentrations = ad.sector_concentrations
        exp_sc = {0 : None, 1 : 1, 2 : 2, 3 : 3}
        self.assert_equal(sector_concentrations, exp_sc)
        parent_sectors = ad.parent_sectors
        exp_ps = {1 : 2, 2 : 3, 3 : None}
        self.assert_equal(parent_sectors, exp_ps)
        self.assert_equal(parent_sectors, exp_ps)
        iso_concentrations = ad.iso_concentrations
        exp_ic = {0 : None, 1 : 50, 2 : 100, 3 : 150}
        self.assert_equal(iso_concentrations, exp_ic)

    def test_result_1(self):
        self.position_data = self.one_sector_data
        self._continue_setup()
        ad = self._get_association_data()
        self.assert_is_not_none(ad)
        associated_sectors = ad.associated_sectors
        exp_as = [[0]]
        self.assert_equal(associated_sectors, exp_as)
        sector_concentrations = ad.sector_concentrations
        exp_sc = {0 : 1}
        self.assert_equal(sector_concentrations, exp_sc)
        parent_sectors = ad.parent_sectors
        exp_ps = {0 : None}
        self.assert_equal(parent_sectors, exp_ps)
        self.assert_equal(parent_sectors, exp_ps)
        iso_concentrations = ad.iso_concentrations
        exp_ic = {0 : 50}
        self.assert_equal(iso_concentrations, exp_ic)

    def test_failure(self):
        # inconsistent final conc
        self.position_data['B3'][1] = 4
        self._continue_setup()
        attrs = dict(transfection_layout=self.transfection_layout, log=self.log)
        self.assert_raises(ValueError, TransfectionAssociationData, **attrs)
        errors_msg = ' '.join(self.log.get_messages(logging.ERROR))
        self.assert_true('Error when trying to determine rack sector ' \
                         'concentrations' in errors_msg)
        # inconsistent iso conc
        self.log.reset()
        self.position_data['B3'][1] = 2
        self.position_data['B3'][2] = 200
        self._continue_setup()
        attrs = dict(transfection_layout=self.transfection_layout, log=self.log)
        self.assert_raises(ValueError, TransfectionAssociationData, **attrs)
        errors_msg = ' '.join(self.log.get_messages(logging.ERROR))
        self.assert_true('There is more than one value for sector 3! ' \
                         'Attribute: iso_concentration' in errors_msg)
        # inconsistent md pools
        self.log.reset()
        del self.position_data['B3']
        self._continue_setup()
        attrs = dict(transfection_layout=self.transfection_layout, log=self.log)
        self.assert_raises(ValueError, TransfectionAssociationData, **attrs)
        errors_msg = ' '.join(self.log.get_messages(logging.ERROR))
        self.assert_true('The molecule design pools in the different ' \
                         'quadrants are not consistent' in errors_msg)
