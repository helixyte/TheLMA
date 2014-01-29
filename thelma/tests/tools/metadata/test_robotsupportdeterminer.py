"""
Tests for robot support determiners. These tools evaluate wether the system
can generate mastermix worklists for an experiment metadata and, if so,
add the missing values to the source layout.

AAB
"""
from everest.entities.utils import get_root_aggregate
from thelma.automation.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.semiconstants import get_384_rack_shape
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.metadata.base import TransfectionAssociationData
from thelma.automation.tools.metadata.base import TransfectionLayout
from thelma.automation.tools.metadata.base import TransfectionPosition
from thelma.automation.tools.metadata.generation \
    import RobotSupportDeterminatorLibrary
from thelma.automation.tools.metadata.generation \
    import RobotSupportDeterminatorOpti
from thelma.automation.tools.metadata.generation \
    import RobotSupportDeterminatorScreen
from thelma.automation.utils.layouts import UNTREATED_POSITION_TYPE
from thelma.interfaces import IMoleculeDesignLibrary
from thelma.interfaces import IMoleculeType
from thelma.models.moleculetype import MOLECULE_TYPE_IDS
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase


class _RobotSupportDeterminerTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.log = TestingLog()
        self.source_layout = None
        self.layout_shape = None
        self.number_replicates = 2
        self.number_design_racks = 2
        # pos label - md pool id, final conc, iso conc (ini), iso conc (final),
        # iso vol (ini), iso vol (final), target wells (d1), target wells (d2)
        self.position_data = None
        self.odf_map = dict()
        self.set_dilution_factors = True
        self.layout_optimem_df = 4
        self.floating_mt = get_root_aggregate(IMoleculeType).\
                                      get_by_id(MOLECULE_TYPE_IDS.SIRNA)

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.log
        del self.source_layout
        del self.layout_shape
        del self.number_replicates
        del self.number_design_racks
        del self.position_data
        del self.set_dilution_factors
        del self.layout_optimem_df
        del self.floating_mt

    def _continue_setup(self):
        self._create_source_layout()

    def _continue_setup_deepwell(self):
        pass

    def _create_source_layout(self):
        self.source_layout = TransfectionLayout(shape=self.layout_shape)
        for pos_label, pos_data in self.position_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            pool_id = pos_data[0]
            if pool_id is None:
                tf_pos = TransfectionPosition.create_empty_position(rack_pos)
                self.source_layout.add_position(tf_pos)
                continue
            pool = self._get_pool(pool_id)
            final_conc = pos_data[1]
            iso_conc = pos_data[2]
            iso_vol = pos_data[4]
            reagent_name = 'mix1'
            reagent_df = 140
            if pool_id == UNTREATED_POSITION_TYPE:
                reagent_name, reagent_df = None, None
            tf_pos = TransfectionPosition(rack_position=rack_pos,
                        molecule_design_pool=pool, reagent_name=reagent_name,
                        reagent_dil_factor=reagent_df, iso_volume=iso_vol,
                        iso_concentration=iso_conc,
                        final_concentration=final_conc)
            self.source_layout.add_position(tf_pos)
            if self.set_dilution_factors:
                if tf_pos.is_untreated_type:
                    pass
                elif tf_pos.is_fixed:
                    tf_pos.store_optimem_dilution_factor()
                else:
                    tf_pos.set_optimem_dilution_factor(self.layout_optimem_df)
        self.source_layout.set_floating_molecule_type(self.floating_mt)

    def _check_result(self):
        final_layout = self.tool.get_result()
        self.assert_is_not_none(final_layout)
        self.assert_equal(len(final_layout), len(self.position_data))
        for rack_pos, tf_pos in final_layout.iterpositions():
            result_data = self.position_data[rack_pos.label]
            pool_id = tf_pos.molecule_design_pool_id
            self.assert_equal(pool_id, result_data[0])
            if not tf_pos.final_concentration == result_data[1]:
                msg = 'Different final concentration for position %s. ' \
                      'Expected: %s. Found: %s.' % (rack_pos.label,
                       result_data[1], tf_pos.final_concentration)
                raise AssertionError(msg)
            if not tf_pos.iso_concentration == result_data[3]:
                msg = 'Different ISO concentration for position %s. ' \
                      'Expected: %s. Found: %s.' % (rack_pos.label,
                       result_data[3], tf_pos.iso_concentration)
                raise AssertionError(msg)
            if not tf_pos.iso_volume == result_data[5]:
                msg = 'Different ISO volume for position %s. ' \
                      'Expected: %s. Found: %s.' % (rack_pos.label,
                       result_data[5], tf_pos.iso_volume)
                raise AssertionError(msg)

    def _test_result_calculate(self):
        self._continue_setup()
        self._check_result()
        self.assert_true(self.tool.supports_mastermix)
        self.assert_false(self.tool.use_deep_well)

    def _test_result_compare(self):
        for pos_data in self.position_data.values():
            pos_data[2] = pos_data[3]
            pos_data[4] = pos_data[5]
        self._continue_setup()
        self._check_result()
        self.assert_true(self.tool.supports_mastermix)
        self.assert_false(self.tool.use_deep_well)

    def _test_result_deep_well(self):
        self._continue_setup_deepwell()
        self._check_result()
        self.assert_true(self.tool.supports_mastermix)
        self.assert_true(self.tool.use_deep_well)
        self._check_warning_messages('Use deep well plates for the ISO plate.')

    def _test_result_deep_well_384(self):
        self.layout_shape = get_384_rack_shape()
        self._continue_setup_deepwell()
        self._check_result()
        self.assert_true(self.tool.supports_mastermix)
        self.assert_false(self.tool.use_deep_well)

    def _test_result_larger_volume(self):
        for pos_data in self.position_data.values():
            pos_data[2] = pos_data[3]
            iso_vol = pos_data[5] + 1
            pos_data[4] = iso_vol
            pos_data[5] = iso_vol
        self._continue_setup()
        self._check_result()
        self.assert_true(self.tool.supports_mastermix)
        self.assert_false(self.tool.use_deep_well)

    def _test_result_no_support_volume(self, msg):
        for pos_data in self.position_data.values():
            pos_data[2] = pos_data[3]
            pos_data[4] = 3
            pos_data[5] = 3
        self._continue_setup()
        self._check_result()
        self.assert_false(self.tool.supports_mastermix)
        self.assert_false(self.tool.use_deep_well)
        self._check_warning_messages(msg)

    def _test_result_no_support_concentration(self):
        for pos_data in self.position_data.values():
            if not pos_data[1] is None:
                iso_conc = pos_data[1] * 10
                pos_data[2] = iso_conc
                pos_data[3] = iso_conc
            pos_data[4] = pos_data[5]
        self._continue_setup()
        self._check_result()
        self.assert_false(self.tool.supports_mastermix)
        self.assert_false(self.tool.use_deep_well)
        self._check_warning_messages('The concentrations you have ordered ' \
                        'to not allow robot-supported mastermix preparation. ' \
                        'Worklist support is disabled now.')

    def _test_result_no_support_deepwell(self):
        for pos_data in self.position_data.values():
            if not pos_data[1] is None:
                iso_conc = pos_data[1] * 10
                pos_data[2] = iso_conc
                pos_data[3] = iso_conc
            iso_vol = 300
            pos_data[4] = iso_vol
            pos_data[5] = iso_vol
        self._continue_setup()
        self._check_result()
        self.assert_false(self.tool.supports_mastermix)
        self.assert_true(self.tool.use_deep_well)
        self._check_warning_messages('Use deep well plates for the ISO ' \
                            'plate. The ordered ISO volumes exceed 250 ul.')
        self._check_warning_messages('The concentrations you have ordered to ' \
                        'not allow robot-supported mastermix preparation. ' \
                        'Worklist support is disabled now.')

    def _test_invalid_source_layout(self):
        ori_layout = self.source_layout
        self.source_layout = None
        self._test_and_expect_errors('The source layout must be a ' \
                                     'TransfectionLayout object')
        self.source_layout = ori_layout

    def _test_invalid_number_replicates(self):
        num_rep = self.number_replicates
        self.number_replicates = float(self.number_replicates)
        self._test_and_expect_errors('The number of replicates must be a int')
        self.number_replicates = num_rep

    def _test_missing_iso_concentration(self):
        i = 0
        for pos_data in self.position_data.values():
            if not i == 0: pos_data[2] = pos_data[3]
            i += 1
        self._continue_setup()
        self._test_and_expect_errors('Some layout positions have a final ' \
                                     'concentration but no ISO concentration.')

    def _test_incompatible_but_missing_volumes(self):
        for pos_data in self.position_data.values():
            if not pos_data[1] is None:
                iso_conc = pos_data[1] * 10
                pos_data[2] = iso_conc
                pos_data[3] = iso_conc
        self._continue_setup()
        self._test_and_expect_errors('The concentrations in your metadata ' \
                'file do not allow for robot support. In such a case, ' \
                'you have to provide ISO volumes. Please add ISO volumes ' \
                'or adjust your ISO concentrations and re-upload your file.')

    def _test_incompatible_but_missing_concentrations(self):
        for pos_data in self.position_data.values():
            pos_data[4] = 3
            pos_data[5] = 3
        self._continue_setup()
        self._test_and_expect_errors('The volumes in your metadata file do ' \
                'not allow for robot support. In such a case, you have to ' \
                'provide ISO concentrations. Please add ISO concentration or ' \
                'adjust your ISO volumes and re-upload your file.')

    def _test_volume_below_minimum(self, msg):
        for pos_data in self.position_data.values():
            pos_data[4] = 0.5
        self._continue_setup()
        self._test_and_expect_errors(msg)

class RobotSupportDeterminerOptiTestCase(_RobotSupportDeterminerTestCase):

    def set_up(self):
        _RobotSupportDeterminerTestCase.set_up(self)
        self.design_rack_associations = []
        self.layout_shape = get_96_rack_shape()
        # pos label - md pool id, final conc, iso conc (ini), iso conc (final),
        # iso vol (ini), iso vol (final), target wells (d1), target wells (d2)
        self.position_data = dict(
                A1=[205201, 10, None, 560, None, 9.9, ('A1', 'A2', 'A3', 'A4'),
                                                      ('A1', 'A2')],
                B1=[205202, 10, None, 560, None, 6.9, ('B1', 'B2'),
                    ('B1', 'B2')],
                C1=[205203, 20, None, 1120, None, 6.9, ('C1', 'C2'),
                    ('C1', 'C2')],
                D1=[330001, 10, None, 420, None, 9.2, ('D1', 'D2'),
                     ('D1', 'D2')],
                E1=['mock', None, None, None, None, 6.9, ('E1', 'E2'),
                                                         ('E1', 'E2')])
        self.mt_map = {1 : MOLECULE_TYPE_IDS.SIRNA, 2 : MOLECULE_TYPE_IDS.SIRNA,
                       3 : MOLECULE_TYPE_IDS.SIRNA,
                       4 : MOLECULE_TYPE_IDS.MIRNA_INHI,
                       'mock' : MOLECULE_TYPE_IDS.SIRNA}

    def tear_down(self):
        _RobotSupportDeterminerTestCase.tear_down(self)
        del self.design_rack_associations

    def _create_tool(self):
        self.tool = RobotSupportDeterminatorOpti(log=self.log,
                        source_layout=self.source_layout,
                        number_replicates=self.number_replicates,
                        design_rack_associations=self.design_rack_associations)

    def _continue_setup(self):
        _RobotSupportDeterminerTestCase._continue_setup(self)
        self.__create_design_layouts()
        self._create_tool()

    def _continue_setup_deepwell(self):
        self.number_replicates = 8
        self.position_data = dict(
                A1=[205201, 10, None, 560, None, 33.8, ('A1', 'A2', 'A3', 'A4'),
                                                       ('A1', 'A2')],
                B1=[205202, 10, None, 560, None, 23.8,
                    ('B1', 'B2'), ('B1', 'B2')],
                C1=[205203, 20, None, 1120, None, 23.8,
                    ('C1', 'C2'), ('C1', 'C2')],
                D1=[330001, 10, None, 420, None, 31.7,
                    ('D1', 'D2'), ('D1', 'D2')],
                E1=['mock', None, None, None, None, 23.8, ('E1', 'E2'),
                                                          ('E1', 'E2')])
        self._continue_setup()

    def __create_design_layouts(self):
        for i in range(self.number_design_racks):
            tf_layout = self.source_layout.copy()
            for pos_label, pos_data in self.position_data.iteritems():
                rack_pos = get_rack_position_from_label(pos_label)
                tf_pos = tf_layout.get_working_position(rack_pos)
                target_labels = pos_data[i + 6]
                for trg_label in target_labels:
                    trg_pos = get_rack_position_from_label(trg_label)
                    tf_pos.cell_plate_positions.add(trg_pos)
            self.design_rack_associations.append(tf_layout)

    def test_result_calculate(self):
        self._test_result_calculate()

    def test_result_compare(self):
        self._test_result_compare()

    def test_result_deep_well(self):
        self._test_result_deep_well()

    def test_result_deep_well_384(self):
        self._test_result_deep_well_384()

    def test_result_larger_volume(self):
        self._test_result_larger_volume()

    def test_result_no_support_volume(self):
        self._test_result_no_support_volume('If you want to prepare a ' \
                'standard mastermix (incl. robot support) you need to order ' \
                'a certain volume of molecule design pool.')

    def test_result_no_support_concentration(self):
        self._test_result_no_support_concentration()

    def test_result_no_support_deepwell(self):
        self._test_result_no_support_deepwell()

    def test_invalid_input_values(self):
        self._continue_setup()
        self._test_invalid_source_layout()
        self._test_invalid_number_replicates()
        self.design_rack_associations = dict()
        self._test_and_expect_errors('The design rack association list must ' \
                                     'be a list')
        self.design_rack_associations = [1]
        self._test_and_expect_errors('The design rack layout must be a ' \
                                     'TransfectionLayout object')

    def test_missing_iso_concentration(self):
        self._test_missing_iso_concentration()

    def test_incompatible_but_missing_volumes(self):
        self._test_incompatible_but_missing_volumes()

    def test_incompatible_but_missing_concentrations(self):
        self._test_incompatible_but_missing_concentrations()

    def test_volume_below_minimum(self):
        self._test_volume_below_minimum('The minimum ISO volume you can ' \
                'order for optimisations is 2 ul. If you want to order less ' \
                'volume, switch the experiment type to "manual ' \
                'optimisation", please. Positions with invalid volume: ' \
                'A1, B1, C1, D1, E1')


class RobotSupportDeterminerScreenTestCase(_RobotSupportDeterminerTestCase):

    def set_up(self):
        _RobotSupportDeterminerTestCase.set_up(self)
        self.handler_iso_volume = None
        self.association_data = None
        self.regard_controls = True
        self.layout_shape = get_384_rack_shape()
        self.__set_position_data()

    def __set_position_data(self):
        # pos label - md pool id, final conc, iso conc (ini), iso conc (final),
        # iso vol (ini), iso vol (final)
        if self.regard_controls:
            self.position_data = dict(
                A1=[205201, 10, None, 560, None, 3.8],
                A2=[205201, 20, None, 1120, None, 3.8],
                C1=[205202, 10, None, 560, None, 3.8],
                C2=[205202, 20, None, 1120, None, 3.8],
                E1=['mock', None, None, None, None, 3.8],
                E2=['mock', None, None, None, None, 3.8])
        else:
            self.position_data = dict(
                A1=[205201, 10, None, 560, None, 3.8],
                A2=[205201, 20, None, 1120, None, 3.8],
                A3=['md_001', 10, None, 560, None, 3.8],
                A4=['md_001', 20, None, 1120, None, 3.8],
                C1=[330001, 10, None, 560, None, 3.8],
                C2=[330001, 20, None, 1120, None, 3.8],
                C3=['md_002', 10, None, 560, None, 3.8],
                C4=['md_002', 20, None, 1120, None, 3.8],
                E1=['mock', None, None, None, None, 3.8],
                E2=['mock', None, None, None, None, 3.8])

    def tear_down(self):
        _RobotSupportDeterminerTestCase.tear_down(self)
        del self.handler_iso_volume
        del self.association_data
        del self.regard_controls

    def _create_tool(self):
        self.tool = RobotSupportDeterminatorScreen(log=self.log,
                    source_layout=self.source_layout,
                    number_replicates=self.number_replicates,
                    number_design_racks=self.number_design_racks,
                    handler_iso_volume=self.handler_iso_volume,
                    association_data=self.association_data)

    def _continue_setup(self):
        _RobotSupportDeterminerTestCase._continue_setup(self)
        self.__set_layout_optimem_df()
        self.handler_iso_volume = self.position_data.values()[0][4]
        self.__create_association_data()
        self._create_tool()

    def __set_layout_optimem_df(self):
        for tf_pos in self.source_layout.working_positions():
            if tf_pos.is_fixed:
                tf_pos.set_optimem_dilution_factor(self.layout_optimem_df)

    def __create_association_data(self):
        if self.layout_shape.name == RACK_SHAPE_NAMES.SHAPE_384:
            self.association_data = TransfectionAssociationData(log=self.log,
                                      layout=self.source_layout,
                                      regard_controls=self.regard_controls)

    def _continue_setup_deepwell(self):
        self.number_replicates = 10
        self.number_design_racks = 5
        self.position_data = dict(
                A1=[205201, 10, None, 560, None, 32.5],
                A2=[205201, 20, None, 1120, None, 32.5],
                C1=[205202, 10, None, 560, None, 32.5],
                C2=[205202, 20, None, 1120, None, 32.5],
                E1=['mock', None, None, None, None, 32.5],
                E2=['mock', None, None, None, None, 32.5])
        self._continue_setup()

    def test_result_calculate_384(self):
        self._test_result_calculate()
        self.regard_controls = False
        self.__set_position_data()
        self._test_result_calculate()

    def test_result_calculate_96(self):
        self.layout_shape = get_96_rack_shape()
        self._test_result_calculate()
        self.regard_controls = False
        self._test_result_calculate()

    def test_result_compare_384(self):
        self.__set_position_data()
        self._test_result_compare()
        self.regard_controls = False
        self.__set_position_data()
        self._test_result_calculate()

    def test_result_compare_96(self):
        self.__set_position_data()
        self.layout_shape = get_96_rack_shape()
        self._test_result_compare()
        self.regard_controls = False
        self.__set_position_data()
        self._test_result_calculate()

    def test_result_deep_well_384(self):
        self._test_result_deep_well_384()

    def test_result_deep_well_96(self):
        self.layout_shape = get_96_rack_shape()
        self._test_result_deep_well()

    def test_result_molecule_type(self):
        self.layout_optimem_df = 3
        self.floating_mt = get_root_aggregate(IMoleculeType).\
                           get_by_id(MOLECULE_TYPE_IDS.MIRNA_INHI)
        self.position_data = dict(
                A1=[330001, 10, None, 420, None, 5],
                A2=[330001, 20, None, 840, None, 5],
                C1=[330002, 10, None, 420, None, 5],
                C2=[330002, 20, None, 840, None, 5],
                E1=['mock', None, None, None, None, 5],
                E2=['mock', None, None, None, None, 5])
        self._continue_setup()
        self._check_result()
        self.assert_true(self.tool.supports_mastermix)
        self.assert_false(self.tool.use_deep_well)

    def test_result_larger_volume(self):
        self._test_result_larger_volume()

    def test_result_no_support_volume(self):
        self._test_result_no_support_volume('If you want to prepare a ' \
                'standard mastermix (incl. robot support) you need to order ' \
                'at least 3.8 ul (you ordered: 3 ul). Robot support is ' \
                'disabled now. If you want robot support for your ' \
                'experiment, increase the ISO volume and re-upload the file')

    def test_result_no_support_concentration(self):
        self._test_result_no_support_concentration()

    def test_result_no_support_deepwell(self):
        self.layout_shape = get_96_rack_shape()
        self._test_result_no_support_deepwell()

    def test_invalid_input_values(self):
        self._continue_setup()
        self._test_invalid_source_layout()
        self._test_invalid_number_replicates()
        num_racks = self.number_design_racks
        self.number_design_racks = float(self.number_design_racks)
        self._test_and_expect_errors('The number of design racks must be a int')
        self.number_design_racks = num_racks
        vol = self.handler_iso_volume
        self.handler_iso_volume = 0
        self._test_and_expect_errors('The handler ISO volume must be a ' \
                                     'positive number (obtained: 0)')
        self.handler_iso_volume = 'as'
        self._test_and_expect_errors('The handler ISO volume must be a ' \
                                     'positive number (obtained: as)')
        self.handler_iso_volume = vol
        self.association_data = 3
        self._test_and_expect_errors('The association data must be a ' \
                                     'TransfectionAssociationData object')
        self.association_data = None
        self._create_tool()
        self._check_result()
        self.assert_true(self.tool.supports_mastermix)
        self.assert_false(self.tool.use_deep_well)

    def test_different_optimem_dilution_factors(self):
        self._continue_setup()
        for tf_pos in self.source_layout.working_positions():
            if tf_pos.is_fixed:
                tf_pos.set_optimem_dilution_factor(7)
                break
        self._test_and_expect_errors('There are more than one different ' \
                                 'OptiMem dilution factors in the layout: 4, 7')

    def test_missing_iso_concentration_96(self):
        self.layout_shape = get_96_rack_shape()
        self._test_missing_iso_concentration()

    def test_incompatible_but_missing_volumes(self):
        self._test_incompatible_but_missing_volumes()

    def test_incompatible_but_missing_concentrations_384(self):
        self._test_incompatible_but_missing_concentrations()

    def test_incompatible_but_missing_concentrations_96(self):
        self.layout_shape = get_96_rack_shape()
        self._test_incompatible_but_missing_concentrations()

    def test_volume_below_minimum(self):
        for pos_data in self.position_data.values():
            pos_data[4] = 0.5
        self._continue_setup()
        self._test_and_expect_errors('The minimum ISO volume you can order ' \
                                     'is 1 ul. You ordered 0.5 ul.')

class RobotSupportDeterminerLibraryTestCase(_RobotSupportDeterminerTestCase):

    def set_up(self):
        _RobotSupportDeterminerTestCase.set_up(self)
        self.library = self._get_entity(IMoleculeDesignLibrary, 'poollib')
        self.final_conc = None
        self.layout_shape = get_384_rack_shape()
        # pos label - md pool id, final conc, iso conc (ini), iso conc (final),
        # iso vol (ini), iso vol (final)
        self.position_data = dict(
                B2=[205201, 10, None, 1270, None, 4],
                C2=['md_001', 10, None, 1270, None, 4],
                D2=['mock', None, None, None, None, 4],
                E2=['md_002', 10, None, 1270, None, 4],
                F2=['untreated', None, None, None, None, None],
                G2=['md_003', 10, None, 1270, None, 4])
        #pylint: disable=E1103
        self.set_dilution_factors = False

    def tear_down(self):
        _RobotSupportDeterminerTestCase.tear_down(self)
        del self.library
        del self.final_conc

    def _create_tool(self):
        self.tool = RobotSupportDeterminatorLibrary(log=self.log,
                                source_layout=self.source_layout,
                                number_replicates=self.number_replicates,
                                number_design_racks=self.number_design_racks,
                                library=self.library,
                                handler_final_concentration=self.final_conc)

    def _continue_setup(self):
        _RobotSupportDeterminerTestCase._continue_setup(self)
        for pos_data in self.position_data.values():
            if pos_data[1] is not None:
                self.final_conc = pos_data[1]
                break
        self._create_tool()

    def _test_and_expect_errors(self, msg=None):
        _RobotSupportDeterminerTestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_optimem_dil_factor())

    def __check_optimem_dil_factor(self, optimem_df):
        for tf_pos in self.tool.return_value.working_positions():
            if tf_pos.molecule_design_pool == UNTREATED_POSITION_TYPE:
                self.assert_is_none(tf_pos.optimem_dil_factor)
            else:
                self.assert_equal(tf_pos.optimem_dil_factor, optimem_df)
        self.assert_equal(self.tool.get_optimem_dil_factor(), optimem_df)

    def test_result_with_support(self):
        self._continue_setup()
        self._check_result()
        self.assert_true(self.tool.supports_mastermix)
        self.assert_false(self.tool.use_deep_well)
        self.__check_optimem_dil_factor(9.1)

    def test_result_no_support(self):
        for pos_data in self.position_data.values():
            if not pos_data[0] in ('mock', 'untreated'):
                pos_data[1] = 1
        self._continue_setup()
        self._check_result()
        self._check_warning_messages('Robot support for mastermix ' \
                                     'preparation is disabled')
        self.__check_optimem_dil_factor(90.7)
        self.assert_false(self.tool.supports_mastermix)
        self.assert_false(self.tool.use_deep_well)

    def test_invalid_input_values(self):
        self._continue_setup()
        self._test_invalid_source_layout()
        self._test_invalid_number_replicates()
        num_racks = self.number_design_racks
        self.number_design_racks = float(self.number_design_racks)
        self._test_and_expect_errors('The number of design racks must be a int')
        self.number_design_racks = num_racks
        self.library = None
        self._test_and_expect_errors('The molecule design library must be a ' \
                                     'MoleculeDesignLibrary object')

    def test_invalid_handler_final_concentration(self):
        self._continue_setup()
        self.final_conc = -2
        self._test_and_expect_errors('The final concentration must be a ' \
                                     'positive number')

    def test_optimem_dilution_factor_too_small(self):
        for pos_data in self.position_data.values():
            if not pos_data[0] in ('mock', 'untreated'):
                pos_data[1] = 100
        self._continue_setup()
        self._test_and_expect_errors('The final concentration you have ' \
                                     'ordered is too large')

    def test_insufficient_iso_volume(self):
        self.number_design_racks = 10
        self._continue_setup()
        tl = self.tool.get_result()
        self.assert_is_not_none(tl)
        self._check_warning_messages('Currently, the mastermix in the ' \
                'source plate would not provide enough volume for all ' \
                'experiment cell plates (required volume: 100 ul, ' \
                'available (excl. dead volume): 62.8 ul). Robot support ' \
                'is disabled now. To activate it reduce the number of ' \
                'replicates, the number of design racks or the final ' \
                'concentration, please.')
