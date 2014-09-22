"""
tests the experiment meta data excel file parser

AAB May 12, 2011
"""

from thelma.automation.handlers.experimentdesign \
    import ExperimentDesignParserHandler
from thelma.automation.parsers.experimentdesign import ExperimentDesignParser
from thelma.automation.semiconstants \
    import get_experiment_type_manual_optimisation
from thelma.automation.semiconstants \
    import get_experiment_type_robot_optimisation
from thelma.automation.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.semiconstants import get_experiment_type_isoless
from thelma.automation.semiconstants import get_experiment_type_library
from thelma.automation.semiconstants import get_experiment_type_order
from thelma.automation.semiconstants import get_experiment_type_screening
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.metadata.base import TransfectionParameters
from thelma.automation.utils.layouts import UNTREATED_POSITION_TYPE
from thelma.models.tagging import Tag
from thelma.models.utils import get_user
from thelma.oldtests.tools.tooltestingutils import ParsingTestCase


class ExperimentDesignParserHandlerTestCase(ParsingTestCase):

    _PARSER_CLS = ExperimentDesignParser

    def set_up(self):
        ParsingTestCase.set_up(self)
        self.TEST_FILE_PATH = 'thelma:tests/parsers/experimentdesign/'
        self.user = get_user('it')
        self.scenario = None

    def tear_down(self):
        ParsingTestCase.tear_down(self)
        del self.scenario

    def _create_tool(self):
        self.tool = ExperimentDesignParserHandler(self.stream,
                                                  self.user, self.scenario)

    def _continue_setup(self, file_name=None):
        if self.scenario is None: self._set_opti_values()
        ParsingTestCase._continue_setup(self, file_name=file_name)

    def _set_opti_values(self):
        self.scenario = get_experiment_type_robot_optimisation()
        self.VALID_FILE = 'valid_opti.xls'

    def _set_screening_values(self):
        self.scenario = get_experiment_type_screening()
        self.VALID_FILE = 'valid_screen.xls'

    def _set_library_values(self):
        self.scenario = get_experiment_type_library()
        self.VALID_FILE = 'valid_library.xls'

    def _set_manual_values(self):
        self.scenario = get_experiment_type_manual_optimisation()
        self.VALID_FILE = 'valid_manual.xls'

    def _set_isoless_values(self):
        self.scenario = get_experiment_type_isoless()
        self.VALID_FILE = 'valid_isoless.xls'

    def __check_unspecific_properties(self, ed):
        self.assert_is_not_none(ed)
        self.__check_experiment_design_attributes(ed)
        d1_layout = None
        b12_layout = None
        for design_rack in ed.experiment_design_racks:
            if design_rack.label == '1':
                d1_layout = design_rack.rack_layout
                continue
            elif design_rack.label == 'b12':
                b12_layout = design_rack.rack_layout
                continue
        self.__check_shared_tagged_rack_positions_sets(d1_layout)
        self.__check_color_coded_tag(d1_layout, b12_layout)
        return d1_layout, b12_layout

    def __check_experiment_design_attributes(self, ed):
        self.assert_equal(ed.rack_shape.name, RACK_SHAPE_NAMES.SHAPE_384)
        self.assert_is_none(ed.experiment_metadata)
        self.assert_is_none(ed.worklist_series)
        self.assert_equal(len(ed.experiments), 0)
        self.assert_equal(len(ed.experiment_design_racks), 6)

    def __check_color_coded_tag(self, d1_layout, b12_layout):
        a1_pos = get_rack_position_from_label('A1')
        a2_pos = get_rack_position_from_label('A2')
        b1_pos = get_rack_position_from_label('B1')
        b2_pos = get_rack_position_from_label('B2')
        cell_positions = [a1_pos, a2_pos, b1_pos, b2_pos]
        mcf7_tag = Tag(self.tool.TAG_DOMAIN, 'cell line', 'MCF7')
        smck33_tag = Tag(self.tool.TAG_DOMAIN, 'cell line', 'SKMC-33')
        pos_set_mcf7_1 = d1_layout.get_positions_for_tag(mcf7_tag)
        self.assert_equal(len(pos_set_mcf7_1), 0)
        pos_set_smck_1 = d1_layout.get_positions_for_tag(smck33_tag)
        self._compare_pos_sets(cell_positions, pos_set_smck_1)
        pos_set_mcf7_b12 = b12_layout.get_positions_for_tag(mcf7_tag)
        self._compare_pos_sets(cell_positions, pos_set_mcf7_b12)
        pos_set_smck_b12 = b12_layout.get_positions_for_tag(smck33_tag)
        self.assert_equal(len(pos_set_smck_b12), 0)

    def __check_molecule_design_set_tags(self, d1_layout, b12_layout):
        # label code
        a1_pos = get_rack_position_from_label('A1')
        a2_pos = get_rack_position_from_label('A2')
        a3_pos = get_rack_position_from_label('A3')
        a4_pos = get_rack_position_from_label('A4')
        md1_tag = Tag(self.tool.TAG_DOMAIN,
                      TransfectionParameters.MOLECULE_DESIGN_POOL, '11')
        md13_tag = Tag(self.tool.TAG_DOMAIN,
                       TransfectionParameters.MOLECULE_DESIGN_POOL, '23')

        positions1 = [a1_pos, a2_pos]
        pos_set_1_1 = d1_layout.get_positions_for_tag(md1_tag)
        self._compare_pos_sets(positions1, pos_set_1_1)
        pos_set_1_b12 = b12_layout.get_positions_for_tag(md1_tag)
        self._compare_pos_sets(positions1, pos_set_1_b12)
        pos_set_13_1 = d1_layout.get_positions_for_tag(md13_tag)
        self.assert_equal(len(pos_set_13_1), 0)
        positions_13 = [a3_pos, a4_pos]
        pos_set_13_b12 = b12_layout.get_positions_for_tag(md13_tag)
        self._compare_pos_sets(positions_13, pos_set_13_b12)

    def __check_untreated_tags(self, layout, pos_label, exp_num_tags):
        rack_pos = get_rack_position_from_label(pos_label)
        tags = [Tag(self.tool.TAG_DOMAIN,
                    TransfectionParameters.MOLECULE_DESIGN_POOL,
                    UNTREATED_POSITION_TYPE),
                Tag(self.tool.TAG_DOMAIN,
                    TransfectionParameters.FINAL_CONCENTRATION.replace('_', ' '),
                    UNTREATED_POSITION_TYPE)]
        tag_set = layout.get_tags_for_position(rack_pos)
        self.assert_equal(len(tag_set), exp_num_tags)
        for tag in tags: self.assert_true(tag in tag_set)

    def __check_shared_tagged_rack_positions_sets(self, d1_layout):
        tnf_tag = Tag(self.tool.TAG_DOMAIN, 'compound', 'TNFa')
        dye_tag = Tag(self.tool.TAG_DOMAIN, 'dye', 'DAPI')
        tnf_is_present = False
        for trps in d1_layout.tagged_rack_position_sets:
            if tnf_tag in trps.tags:
                tnf_is_present = True
                self.assert_true(dye_tag in trps.tags)
        self.assert_true(tnf_is_present)

    def __get_all_predicates(self, ed):
        predicates = set()
        for design_rack in ed.experiment_design_racks:
            tags = design_rack.rack_layout.get_tags()
            for tag in tags: predicates.add(tag.predicate)
        return predicates

    def __get_all_validators(self):
        parameters = [TransfectionParameters.MOLECULE_DESIGN_POOL,
                      TransfectionParameters.REAGENT_NAME,
                      TransfectionParameters.REAGENT_DIL_FACTOR,
                      TransfectionParameters.FINAL_CONCENTRATION]
        validators = dict()
        for parameter in parameters:
            validator = TransfectionParameters.create_validator_from_parameter(
                                                                     parameter)
            validators[parameter] = validator
        return validators

    def test_if_result(self):
        self._test_if_result()

    def test_result_opti(self):
        self._continue_setup()
        ed = self.tool.get_result()
        d1_layout, b12_layout = self.__check_unspecific_properties(ed)
        # check label coded tag
        # make sure to use the parameter tag name for md pools
        self.__check_molecule_design_set_tags(d1_layout, b12_layout)
        # no molecule design tags
        p1_pos = get_rack_position_from_label('P1')
        tags_1 = d1_layout.get_tags_for_position(p1_pos)
        self.assert_equal(len(tags_1), 0)
        tags_b12 = b12_layout.get_tags_for_position(p1_pos)
        self.assert_equal(len(tags_b12), 1)
        # check tag predicates
        predicates = self.__get_all_predicates(ed)
        validators = self.__get_all_validators()
        for predicate in predicates:
            for parameter, validator in validators.iteritems():
                if not (
                    parameter == TransfectionParameters.MOLECULE_DESIGN_POOL or \
                    parameter == TransfectionParameters.FINAL_CONCENTRATION):
                    self.assert_false(validator.has_alias(predicate))
        # replaced floatings
        floatings_mds = []
        md_validator = validators[TransfectionParameters.MOLECULE_DESIGN_POOL]
        b1_pos = get_rack_position_from_label('B1')
        b1_tags = d1_layout.get_tags_for_position(b1_pos)
        for tag in b1_tags:
            if md_validator.has_alias(tag.predicate):
                floatings_mds.append(tag.value)
        b2_pos = get_rack_position_from_label('B2')
        b2_tags = d1_layout.get_tags_for_position(b2_pos)
        for tag in b2_tags:
            if md_validator.has_alias(tag.predicate):
                floatings_mds.append(tag.value)
        exptected_mds = ['md_001', 'md_002']
        floatings_mds.sort()
        self.assert_equal(floatings_mds, exptected_mds)
        # untreated
        self.__check_untreated_tags(d1_layout, 'A6', 4)

    def test_result_screen(self):
        self._set_screening_values()
        self._continue_setup()
        ed = self.tool.get_result()
        self.assert_is_not_none(ed)
        self.__check_experiment_design_attributes(ed)
        d1_layout, b12_layout = self.__check_unspecific_properties(ed)
        # check label coded tag
        dye_tag = Tag(self.tool.TAG_DOMAIN, 'dye', 'DAPI')
        positions = [get_rack_position_from_label('A1'),
                     get_rack_position_from_label('A2'),
                     get_rack_position_from_label('B1'),
                     get_rack_position_from_label('B2')]
        pos_set_1 = d1_layout.get_positions_for_tag(dye_tag)
        self._compare_pos_sets(positions, pos_set_1)
        pos_set_b12 = b12_layout.get_positions_for_tag(dye_tag)
        self.assert_equal(len(pos_set_b12), 0)
        # check tag predicates
        predicates = self.__get_all_predicates(ed)
        validators = self.__get_all_validators()
        for predicate in predicates:
            for validator in validators.values():
                self.assert_false(validator.has_alias(predicate))

    def test_result_library(self):
        # this is all the same as in screening scenarios
        self._set_library_values()
        self._continue_setup()
        ed = self.tool.get_result()
        self.assert_is_not_none(ed)
        d1_layout, b12_layout = self.__check_unspecific_properties(ed)
        # check label coded tag
        dye_tag = Tag(self.tool.TAG_DOMAIN, 'dye', 'DAPI')
        positions = [get_rack_position_from_label('A1'),
                     get_rack_position_from_label('A2'),
                     get_rack_position_from_label('B1'),
                     get_rack_position_from_label('B2')]
        pos_set_1 = d1_layout.get_positions_for_tag(dye_tag)
        self._compare_pos_sets(positions, pos_set_1)
        pos_set_b12 = b12_layout.get_positions_for_tag(dye_tag)
        self.assert_equal(len(pos_set_b12), 0)
        # check tag predicates
        predicates = self.__get_all_predicates(ed)
        validators = self.__get_all_validators()
        for predicate in predicates:
            for validator in validators.values():
                self.assert_false(validator.has_alias(predicate))

    def test_result_manual(self):
        # including untreated
        self._set_manual_values()
        self._continue_setup()
        ed = self.tool.get_result()
        d1_layout, b12_layout = self.__check_unspecific_properties(ed)
        # check label coded tag
        # make sure to use the parameter tag name for md pools
        self.__check_molecule_design_set_tags(d1_layout, b12_layout)
        # no molecule design tags
        p1_pos = get_rack_position_from_label('P1')
        tags_1 = d1_layout.get_tags_for_position(p1_pos)
        self.assert_equal(len(tags_1), 0)
        tags_b12 = b12_layout.get_tags_for_position(p1_pos)
        self.assert_equal(len(tags_b12), 1)
        # check tag predicates
        predicates = self.__get_all_predicates(ed)
        validators = self.__get_all_validators()
        has_md = False
        has_reagent_name = False
        has_reagent_df = False
        has_final_conc = False
        for predicate in predicates:
            for parameter, validator in validators.iteritems():
                if not validator.has_alias(predicate): continue
                if parameter == TransfectionParameters.MOLECULE_DESIGN_POOL:
                    has_md = True
                elif parameter == TransfectionParameters.REAGENT_NAME:
                    has_reagent_name = True
                elif parameter == TransfectionParameters.REAGENT_DIL_FACTOR:
                    has_reagent_df = True
                elif parameter == TransfectionParameters.FINAL_CONCENTRATION:
                    has_final_conc = True
        self.assert_true(has_md)
        self.assert_true(has_reagent_name)
        self.assert_true(has_reagent_df)
        self.assert_true(has_final_conc)
        self.__check_untreated_tags(d1_layout, 'A5', 4)

    def test_valid_isoless(self):
        self._set_isoless_values()
        self._continue_setup()
        ed = self.tool.get_result()
        self.assert_equal(len(ed.experiment_design_racks), 3)
        cp_yes = Tag(self.tool.TAG_DOMAIN, 'Compound', 'yes')
        cp_no = Tag(self.tool.TAG_DOMAIN, 'Compound', 'no')
        cell_values = {'1' : ('line A', 'star'), '2' : ('line B', 'sun'),
                       '3' : ('both', 'sky')}
        b2_pos = get_rack_position_from_label('B2')
        d2_pos = get_rack_position_from_label('D2')
        for drack in ed.experiment_design_racks:
            layout = drack.rack_layout
            trp_sets = layout.tagged_rack_position_sets
            self.assert_equal(len(trp_sets), 3)
            data = cell_values[drack.label]
            cell_tag = Tag(self.tool.TAG_DOMAIN, 'cell line', data[0])
            nick_tag = Tag(self.tool.TAG_DOMAIN, 'nick', data[1])
            for trps in trp_sets:
                tags = trps.tags
                for tag in tags:
                    rps = trps.rack_position_set
                    if tag == cp_yes:
                        self.assert_equal(len(rps), 4)
                        self.assert_true(b2_pos in rps)
                        self.assert_false(d2_pos in rps)
                    elif tag == cp_no:
                        self.assert_equal(len(rps), 4)
                        self.assert_true(d2_pos in rps)
                        self.assert_false(b2_pos in rps)
                    elif tag == cell_tag or tag == nick_tag:
                        self.assert_equal(len(rps), 8)
                        self.assert_true(b2_pos in rps)
                        self.assert_true(d2_pos in rps)
                    else:
                        raise ValueError('Unknown tag: %s' % (tag))

    def test_invalid_requester(self):
        self._continue_setup()
        self.user = self.user.username
        self._test_and_expect_errors('The requester must be a User object')

    def test_scenario(self):
        self._continue_setup()
        self.scenario = 123
        self._test_and_expect_errors('The experiment metadata type must be a ' \
                                     'ExperimentMetadataType object')
        self.scenario = get_experiment_type_order()
        self._test_and_expect_errors('Unknown scenario: "ISO without ' \
                'experiment". Allowed scenarios: screening, ' \
                'optimisation with robot-support, manual optimisation, ' \
                'seeding (without ISO), library screening')

    def test_no_levels(self):
        self._continue_setup('no_levels.xls')
        ed = self.tool.get_result()
        self.__check_unspecific_properties(ed)

    def test_code_without_label(self):
        self._test_invalid_file('code_without_label.xls',
                                'On sheet "seeding" cell B6: There is a ' \
                                'code without label!')

    def test_level_interrupted(self):
        self._test_invalid_file('level_interrupted.xls',
                                'On sheet "seeding": Tag value (level) ' \
                                'code "4" not found for factor "cell line"')

    def test_code_without_definition(self):
        self._test_invalid_file('code_without_definition.xls',
                                'On sheet "seeding": Tag value (level) ' \
                                'code "4" not found for factor "cell line"')

    def test_invalid_shape(self):
        self._test_invalid_file('invalid_rack_shape.xls',
                                'Invalid layout block shape')

    def test_different_shapes(self):
        self._test_invalid_file('different_rack_shapes.xls',
                    'On sheet "seeding": There are 2 different layout shapes ' \
                    'in the file (8x12 and 16x24).')

    def test_no_level_marker(self):
        self._test_invalid_file('no_level_marker.xls',
                    'On sheet "seeding" cell A3: Invalid factor definition! ' \
                    'There must be a "Code" marker next to and a "Level" ' \
                    'marker below the "Factor" marker!')

    def test_no_code_marker(self):
        self._test_invalid_file('no_code_marker.xls',
                    'On sheet "seeding" cell B1: Invalid ' \
                    'factor definition! There must be a "Code" marker next ' \
                    'to and a "Level" marker below the "Factor" marker!')

    def test_no_layout(self):
        self._test_invalid_file('no_layout.xls',
                    'Could not find a layout definition on this sheet.')

    def test_invalid_rack_specifier(self):
        self._test_invalid_file('invalid_rack_specifier.xls',
                                'Invalid rack specifier')

    def test_invalid_barcode_range(self):
        self._test_invalid_file('invalid_barcode_range.xls',
                    'Invalid range "b1-b3" in racks specifier "Plates b1-b3"')

    def test_invalid_rack_range(self):
        self._test_invalid_file('invalid_rack_range.xls',
                                'Unable to parse rack range')

    def test_wrong_alignment(self):
        self._test_invalid_file('wrong_alignment.xls',
                'On sheet "assay": Unable to find tags (factors) for ' \
                'layout in row 4! Please check the alignment of your layouts!')

    def test_missing_rel_tag_value(self):
        self._test_invalid_file('missing_rel_tag_value.xls',
                                'On sheet "seeding": Tag value (level) ' \
                                'code "3" not found for factor "rel_tag"')

    def test_level_without_code(self):
        self._test_invalid_file('level_without_code.xls',
                'On sheet "seeding" cell C6: There are levels in ' \
                'definition for factor "cell line" that do not have a code!')

    def test_unknown_character(self):
        self._test_invalid_file('unknown_character.xls', 'Unknown character')

    def test_duplicate_predicate(self):
        self._test_invalid_file('duplicate_predicate.xls',
                                'Duplicate factor name')

    def test_invalid_final_concentration(self):
        self._test_invalid_file('invalid_final_concentration.xls',
                'The levels of some factors must be positive numbers. The ' \
                'following positions in design rack 1 have invalid values: ' \
                'final concentration:')

    def test_invalid_final_concentration_mock(self):
        self._test_invalid_file('invalid_final_concentration_mock.xls',
                'The levels of some factors for mock positions allow only ' \
                'for the values')
        self._check_error_messages('final concentration: A4')

    def test_invalid_final_concentration_untreated(self):
        self._test_invalid_file('invalid_final_concentration_untreated.xls',
                                'The levels of some factors for untreated ' \
                                'positions allow only for the values')
        self._check_error_messages('final concentration: A4')

    def test_invalid_reagent_dilution_factor(self):
        self._test_invalid_file('invalid_reagent_df.xls',
                'The levels of some factors must be positive numbers. The ' \
                'following positions in design rack 1 have invalid values: ' \
                'reagent dilution factor')

    def test_invalid_reagent_dilution_factor_untreated(self):
        self._test_invalid_file('invalid_reagent_df_untreated.xls',
                'The levels of some factors for untreated positions allow ' \
                'only for the values "None" and "untreated"')
        self._check_error_messages('reagent dilution factor: A4')

    def test_invalid_reagent_name(self):
        self._test_invalid_file('invalid_reagent_name.xls',
                'The reagent name must be at least 2 characters long')
        self._check_error_messages('A1, A2, B1, B2')

    def test_invalid_reagent_name_untreated(self):
        self._test_invalid_file('invalid_reagent_name_untreated.xls',
                'Untreated position must only have the reagent names "None", ' \
                '"untreated" or no reagent name at all')
        self._check_error_messages('A6')

    def test_inconsistent_value(self):
        self._test_invalid_file('inconsistent_optional_value.xls',
                'If you specify a factor, you have to specify it for each ' \
                'non-empty well in all design racks. The following wells in ' \
                'design rack b12 lack a specification')

    def test_value_for_empty_position(self):
        self._test_invalid_file('value_for_empty.xls',
                'Some rack positions in design rack 1 contain values ' \
                'although there are no molecule designs for them')

    def test_missing_final_conc_opti(self):
        self._set_opti_values()
        self._test_invalid_file('opti_missing_final_conc.xls',
            'There are mandatory values missing for some rack positions in ' \
            'design rack b12: final concentration')

    def test_missing_md_pool_opti(self):
        self._set_opti_values()
        self._test_invalid_file('opti_missing_md_pool.xls',
                'There are no molecule design pools in the layout')

    def test_forbidden_md_pool_screen(self):
        self._set_screening_values()
        self._test_invalid_file('screen_forbidden_md_pool.xls',
            'There are molecule design pools in the layout for design ' \
            'rack 1. This is not allowed for the current scenario (screening)')

    def test_forbidden_md_pool_library(self):
        self._set_library_values()
        # we re-use the file since it is exactly the same like in screenings
        self._test_invalid_file('screen_forbidden_md_pool.xls',
            'There are molecule design pools in the layout for design ' \
            'rack 1. This is not allowed for the current scenario ' \
            '(library screening)')

    def test_forbidden_reagent_name_screen(self):
        self._set_screening_values()
        self._test_invalid_file('screen_forbidden_reagent_name.xls',
            'Some factors must not be specified in screening scenarios. The ' \
            'following position in design rack 1 contain specifications for ' \
            'forbidden factors: reagent name')

    def test_forbidden_reagent_name_library(self):
        self._set_library_values()
        # we re-use the file since it is exactly the same like in screenings
        self._test_invalid_file('screen_forbidden_reagent_name.xls',
            'Some factors must not be specified in library screening ' \
            'scenarios. The following position in design rack 1 contain ' \
            'specifications for forbidden factors: reagent name')

    def test_forbidden_reagent_dil_factor_screen(self):
        self._set_screening_values()
        self._test_invalid_file('screen_forbidden_reagent_df.xls',
            'Some factors must not be specified in screening scenarios. The ' \
            'following position in design rack 1 contain specifications for ' \
            'forbidden factors: reagent dilution')

    def test_forbidden_reagent_dil_factor_library(self):
        self._set_library_values()
        # we re-use the file since it is exactly the same like in screenings
        self._test_invalid_file('screen_forbidden_reagent_df.xls',
            'Some factors must not be specified in library screening ' \
            'scenarios. The following position in design rack 1 contain ' \
            'specifications for forbidden factors: reagent dilution')

    def test_forbidden_final_concentration_screen(self):
        self._set_screening_values()
        self._test_invalid_file('screen_forbidden_final_conc.xls',
            'Some factors must not be specified in screening scenarios. The ' \
            'following position in design rack 1 contain specifications for ' \
            'forbidden factors: final concentration')

    def test_forbidden_final_concentration_library(self):
        self._set_library_values()
        # we re-use the file since it is exactly the same like in screenings
        self._test_invalid_file('screen_forbidden_final_conc.xls',
            'Some factors must not be specified in library screening ' \
            'scenarios. The following position in design rack 1 contain ' \
            'specifications for forbidden factors: final concentration')

    def test_forbidden_md_pool_isoless(self):
        self._set_isoless_values()
        self._test_invalid_file('isoless_forbidden_md_pool.xls',
            'There are molecule design pools in the layout for design ' \
            'rack 1. This is not allowed for the current scenario ' \
            '(seeding (without ISO))')

    def test_forbidden_reagent_name_isoless(self):
        self._set_isoless_values()
        self._test_invalid_file('isoless_forbidden_reagent_name.xls',
            'Some factors must not be specified in seeding (without ISO) ' \
            'scenarios. The following position in design rack 1 contain ' \
            'specifications for forbidden factors: reagent name')

    def test_forbidden_reagent_dil_factor_isoless(self):
        self._set_isoless_values()
        self._test_invalid_file('isoless_forbidden_reagent_df.xls',
            'Some factors must not be specified in seeding (without ISO) ' \
            'scenarios. The following position in design rack 1 contain ' \
            'specifications for forbidden factors: reagent dilution')

    def test_forbidden_final_concentration_isoless(self):
        self._set_isoless_values()
        self._test_invalid_file('isoless_forbidden_final_conc.xls',
            'Some factors must not be specified in seeding (without ISO) ' \
            'scenarios. The following position in design rack 1 contain ' \
            'specifications for forbidden factors: final concentration')

    def test_missing_md_pool_manual(self):
        self._set_manual_values()
        self._test_invalid_file('manual_missing_md_pool.xls',
            'There are no molecule design pools in the layout')

    def test_missing_final_concentration_manual(self):
        self._set_manual_values()
        self._test_invalid_file('manual_missing_final_conc.xls',
            'There are mandatory values missing for some rack positions in ' \
            'design rack 1: final concentration: A4. Assumed scenario: ' \
            'manual optimisation')

    def test_missing_reagent_name_manual(self):
        self._set_manual_values()
        self._test_invalid_file('manual_missing_reagent_name.xls',
            'There are mandatory values missing for some rack positions in ' \
            'design rack 1: reagent name: A4. Assumed scenario: ' \
            'manual optimisation.')

    def test_missing_reagent_dilution_factor_manual(self):
        self._set_manual_values()
        self._test_invalid_file('manual_missing_reagent_df.xls',
            'There are mandatory values missing for some rack positions in ' \
            'design rack 1: reagent dilution factor: A4. Assumed scenario: ' \
            'manual optimisation.')
