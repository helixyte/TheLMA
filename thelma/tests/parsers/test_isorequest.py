"""
tests the ISO excel file parser

AAB July 1a, 2011
"""

from datetime import date
from everest.testing import check_attributes
from thelma.automation.handlers.isorequest import IsoRequestParserHandler
from thelma.automation.parsers.isorequest import IsoRequestParser
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionParameters
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionPosition
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.utils.iso import IsoParameters
from thelma.models.moleculetype import MOLECULE_TYPE_IDS
from thelma.models.rack import RackPositionSet
from thelma.models.tagging import Tag
from thelma.models.utils import get_user
from thelma.tests.tools.tooltestingutils import ParsingTestCase


class IsoRequestParserTest(ParsingTestCase):

    _PARSER_CLS = IsoRequestParser

    def set_up(self):
        ParsingTestCase.set_up(self)
        self.user = get_user('it')
        self.NAMESPACE = 'iso'
        self.VALID_FILE = None
        self.VALID_FILE_OPTI = 'valid_opti.xls'
        self.VALID_FILE_SCREEN = 'valid_screen.xls'
        self.TEST_FILE_PATH = 'thelma:tests/parsers/isos/'
        self.EMPTY_TAG = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                             IsoParameters.EMPTY_TYPE_VALUE)
        self.experiment_type_id = None

    def tear_down(self):
        ParsingTestCase.tear_down(self)
        del self.NAMESPACE
        del self.VALID_FILE_OPTI
        del self.VALID_FILE_SCREEN
        del self.EMPTY_TAG
        del self.experiment_type_id

    def _create_tool(self):
        self.tool = IsoRequestParserHandler.create(stream=self.stream,
                                requester=self.user, log=self.log,
                                experiment_type_id=self.experiment_type_id)

    def _test_and_expect_errors(self, msg=None):
        ParsingTestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_transfection_layout())
        self.assert_is_none(self.tool.get_additional_trps())

    def _test_invalid_user(self):
        self._continue_setup(self.VALID_FILE)
        self.user = None
        self._test_and_expect_errors('The requester must be a User object')

    def _test_unspecific_errors(self):
        self._test_levels_interrupted()
        self._test_value_without_code()
        self._test_no_iso_sheet()
        self._test_invalid_shape()
        self._test_different_shapes()
        self._test_no_level_marker()
        self._test_no_code_marker()
        self._test_no_levels()
        self._test_level_without_code()
        self._test_no_layout()
        self._test_no_pool_tag_definition()
        self._test_unknown_md_pool()
        self._test_no_controls()
        self._test_duplicate_pool_definition()
        self._test_wrong_alignment()
        self._test_missing_metadata()
        self._test_wrong_metadata()
        self._test_wrong_date()
        self._test_duplicate_specification()
        self._test_duplicate_tag()
        self._test_0_concentration()
        self._test_order_stock_conc()
        self._test_missing_level()
        self._test_reagent_dil_factor_0()
        self._test_invalid_reagent_dil_factor()
        self._test_invalid_final_concentration()
        self._test_unicode()
        self._test_plate_set_label_too_long()
        self._test_larger_than_stock_concentration()

    def _test_levels_interrupted(self):
        self._test_invalid_file('lv_interrupted.xls',
                'Tag value (level) code "7" not found for factor ' \
                '"Molecule design pool id".')

    def _test_value_without_code(self):
        self._test_invalid_file('value_without_code.xls',
                'Tag value (level) code "8" not found for factor ' \
                '"Molecule design pool id"')

    def _test_no_iso_sheet(self):
        self._test_invalid_file('no_sheet.xls', '')

    def _test_invalid_shape(self):
        self._test_invalid_file('invalid_shape.xls',
                                'Invalid layout block shape (8x11)')

    def _test_different_shapes(self):
        self._test_invalid_file('different_shapes.xls',
            'There are 2 different layout shapes in the file (16x24 and 8x12)')

    def _test_no_level_marker(self):
        self._test_invalid_file('no_lv_marker.xls',
            'Invalid factor definition! There must be a "Code" marker next ' \
            'to and a "Level" marker below the "Factor" marker!')

    def _test_no_code_marker(self):
        self._test_invalid_file('no_code_marker.xls',
            'Invalid factor definition! There must be a "Code" marker next ' \
            'to and a "Level" marker below the "Factor" marker!')

    def _test_no_levels(self):
        self._continue_setup('no_levels.xls')
        iso_request = self.tool.get_result()
        self.assert_is_not_none(iso_request)

    def _test_level_without_code(self):
        self._test_invalid_file('level_without_code.xls',
            'cell D19: There are levels in definition for factor ' \
            '"sample_type" that do not have a code!')

    def _test_no_layout(self):
        self._test_invalid_file('no_layout.xls',
                                'Could not find a layout definition')

    def _test_no_pool_tag_definition(self):
        self._test_invalid_file('no_pool_tag_definition.xls',
            'Could not find a tag definition for molecule design pool IDs!')

    def _test_unknown_md_pool(self):
        self._test_invalid_file('unknown_md_pool.xls',
            'The following molecule design pools are unknown: 999999999 (B2)')

    def _test_no_controls(self):
        self._test_invalid_file('no_controls.xls',
            'There are no fixed positions in this ISO layout!')

    def _test_duplicate_pool_definition(self):
        self._test_invalid_file('duplicate_pool.xls',
            'There are 2 different molecule design pool tag definitions')

    def _test_wrong_alignment(self):
        self._test_invalid_file('wrong_alignment.xls',
            'Unable to find tags (factors) for layout in row 4! Please ' \
            'check the alignment of your layouts!')

    def _test_missing_metadata(self):
        self._test_invalid_file('missing_metadata.xls',
            'Could not find value for the following ISO meta data ' \
            'specifications: plate_set_label')

    def _test_wrong_metadata(self):
        self._test_invalid_file('wrong_metadata.xls',
                                'Unknown metadata specifier')

    def _test_wrong_date(self):
        self._test_invalid_file('wrong_date.xls',
                                'Cannot read the delivery date')

    def _test_duplicate_tag(self):
        self._continue_setup('duplicate_tag.xls')
        self._test_and_expect_errors('Duplicate tag "sample_type"')

    def _test_duplicate_specification(self):
        self._test_invalid_file('duplicate_specification.xls',
            'You have specified both a default value and a layout for the ' \
            '"iso_concentration" parameter! Please choose one option')

    def _test_0_concentration(self):
        self._test_invalid_file('concentration_0.xls',
                                'invalid ISO concentration')
        self._check_error_messages('Affected positions: B2, B3, B4')

    def _test_order_stock_conc(self):
        self._test_invalid_file('stock_conc_order.xls',
            'Ordering molecule design pools in stock concentration is not ' \
            'allowed for this kind of experiment metadata')

    def _test_missing_level(self):
        self._test_invalid_file('missing_levels.xls',
            'Tag value (level) code "5" not found for factor "sample_type"')

    def _test_reagent_dil_factor_0(self):
        self._test_invalid_file('reagent_vol_0.xls',
            'Invalid or missing reagent dilution factor for rack positions: ' \
            'default value')

    def _test_invalid_reagent_dil_factor(self):
        self._test_invalid_file('invalid_reagent_dil_factor.xls',
            'Invalid or missing reagent dilution factor for rack positions: ' \
            'default value')

    def _test_invalid_final_concentration(self):
        self._test_invalid_file('invalid_final_conc.xls',
                                'Invalid final concentration')

    def _test_unicode(self):
        self._test_invalid_file('unicode.xls', 'Unknown character in cell D39')

    def _test_plate_set_label_too_long(self):
        self._test_invalid_file('plate_set_label_too_long.xls',
                                'maximum length for plate set labels')

    def _test_larger_than_stock_concentration(self):
        self._test_invalid_file('larger_than_stock.xls',
            'Some concentrations you have ordered are larger than the stock ' \
            'concentration for that molecule type')


class IsoRequestOptiParserTestCase(IsoRequestParserTest):

    def set_up(self):
        IsoRequestParserTest.set_up(self)
        self.VALID_FILE = self.VALID_FILE_OPTI
        self.experiment_type_id = EXPERIMENT_SCENARIOS.OPTIMISATION

    def test_if_result(self):
        self.VALID_FILE = self.VALID_FILE_OPTI
        self._test_if_result()

    def test_handler_user(self):
        self._test_invalid_user()

    def test_result(self):
        self._continue_setup(self.VALID_FILE_OPTI)
        iso_request = self.tool.get_result()
        self.assert_is_not_none(iso_request)
        # check metadata
        delivery_date = date(2011, 7, 10)
        attrs = dict(delivery_date=delivery_date, plate_set_label='test_iso',
                     number_aliquots=1, requester=self.user,
                     isos=[], owner='', experiment_metadata=None,
                     comment='some comment')
        check_attributes(iso_request, attrs)
        # check rack layout
        rl = iso_request.iso_layout
        self.assert_equal(len(rl.tagged_rack_position_sets), 16)
        self.assert_equal(len(rl.get_positions()), 18)
        # parameter tags
        fixed_tag = Tag(IsoParameters.DOMAIN,
                        IsoParameters.MOLECULE_DESIGN_POOL, '330001')
        b4_pos = get_rack_position_from_label('B4')
        fixed_positions = [b4_pos]
        fixed_pos_set = rl.get_positions_for_tag(fixed_tag)
        self._compare_pos_sets(fixed_positions, fixed_pos_set)
        fixed_type_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                             IsoParameters.FIXED_TYPE_VALUE)
        b2_pos = get_rack_position_from_label('B2')
        b3_pos = get_rack_position_from_label('B3')
        b5_pos = get_rack_position_from_label('B5')
        fixed_type_positions = [b2_pos, b3_pos, b4_pos, b5_pos]
        fixed_type_pos_set = rl.get_positions_for_tag(fixed_type_tag)
        self._compare_pos_sets(fixed_type_positions, fixed_type_pos_set)
        float_type_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                             IsoParameters.FLOATING_TYPE_VALUE)
        float_positions = rl.get_positions_for_tag(float_type_tag)
        self.assert_equal(len(float_positions), 12)
        float_tag = Tag(IsoParameters.DOMAIN,
                        IsoParameters.MOLECULE_DESIGN_POOL, 'md_002')
        float_positions = [get_rack_position_from_label('D3'),
                           get_rack_position_from_label('E3'),
                           get_rack_position_from_label('F3'),
                           get_rack_position_from_label('G3')]
        float_pos_set = rl.get_positions_for_tag(float_tag)
        self._compare_pos_sets(float_positions, float_pos_set)
        conc_tag = Tag(IsoParameters.DOMAIN, IsoParameters.ISO_CONCENTRATION,
                       '50')
        conc_positions = [b2_pos, b3_pos, b4_pos, b5_pos]
        conc_pos_set = rl.get_positions_for_tag(conc_tag)
        self._compare_pos_sets(conc_positions, conc_pos_set)
        # metadata specification only
        vol_tag = Tag(IsoParameters.DOMAIN, IsoParameters.ISO_VOLUME, '4')
        vol_pos_set = rl.get_positions_for_tag(vol_tag)
        self.assert_equal(len(vol_pos_set), 17)
        d7_pos = get_rack_position_from_label('D7')
        exp_set = rl.get_positions()
        exp_set.remove(d7_pos) # untreated
        self.assert_equal(vol_pos_set, exp_set)
        # layout overwrites metadata
        name_tag = Tag(TransfectionParameters.DOMAIN,
                       TransfectionParameters.REAGENT_NAME, 'RNAi Mix2')
        name_positions = [get_rack_position_from_label('F2'),
                          get_rack_position_from_label('F3'),
                          get_rack_position_from_label('F4'),
                          get_rack_position_from_label('G2'),
                          get_rack_position_from_label('G3'),
                          get_rack_position_from_label('G4')]
        name_pos_set = rl.get_positions_for_tag(name_tag)
        self._compare_pos_sets(name_positions, name_pos_set)
        name1_tag = Tag(TransfectionParameters.DOMAIN,
                        TransfectionParameters.REAGENT_NAME, 'RNAi Mix')
        name1_pos_set = rl.get_positions_for_tag(name1_tag)
        self.assert_equal(len(name1_pos_set), 11)
        # additional tags (are not store in the rack layout)
        add_trps = self.tool.get_additional_trps()
        self.assert_equal(len(add_trps), 5)
        sample_type_tag = Tag('transfection', 'sample_type', 'pos')
        has_tag = False
        for trps in add_trps.values():
            self.assert_equal(len(trps.tags), 1)
            for tag in trps.tags:
                if tag == sample_type_tag:
                    has_tag = True
                    exp_pos_set = [get_rack_position_from_label('B2'),
                                   get_rack_position_from_label('B3')]
                    self._compare_pos_sets(exp_pos_set,
                                           trps.rack_position_set.positions)
        self.assert_true(has_tag)
        # check untreated
        d7_tf = self.tool.get_transfection_layout().get_working_position(d7_pos)
        self.assert_is_not_none(d7_tf)
        self.assert_true(d7_tf.is_untreated)
        self.assert_true(d7_tf.reagent_name, TransfectionPosition.NONE_REPLACER)

    def test_unspecific_errors(self):
        self._test_unspecific_errors()

    def test_missing_parameter(self):
        self._test_invalid_file('missing_parameter.xls',
            'There are no values specified for the parameter "reagent_name"')

    def test_no_supplier(self):
        self._continue_setup('no_supplier.xls')
        iso_request = self.tool.get_result()
        self.assert_is_not_none(iso_request)

    def test_replace_floating_positions(self):
        self._continue_setup('replace_floatings.xls')
        iso_request = self.tool.get_result()
        self.assert_is_not_none(iso_request)
        all_tags = iso_request.iso_layout.get_tags()
        float_tags = []
        for tag in all_tags:
            if tag.predicate == IsoParameters.MOLECULE_DESIGN_POOL and \
                                IsoParameters.FLOATING_INDICATOR in tag.value:
                float_tags.append(tag)
        self.assert_equal(len(float_tags), 12)
        for i in range(12):
            tag = Tag(IsoParameters.DOMAIN, IsoParameters.MOLECULE_DESIGN_POOL,
                      '%s%03i' % (IsoParameters.FLOATING_INDICATOR, (i + 1)))
            self.assert_true(tag in float_tags)
        sl = self.tool.get_transfection_layout()
        counter = 0
        for tf_pos in sl.get_sorted_working_positions():
            if not tf_pos.is_floating: continue
            counter += 1
            exp_placeholder = 'md_%03i' % (counter)
            self.assert_equal(tf_pos.molecule_design_pool, exp_placeholder)


    def test_384_opti_more_than_96_mds(self):
        self._test_invalid_file(self.VALID_FILE_SCREEN,
            '384-well optimisation ISO layouts with more than 96 ' \
            'distinct molecule design pool IDs are not supported')

    def test_stock_concentration(self):
        self._test_invalid_file('opti_stock_conc.xls',
            'Ordering molecule design pools in stock concentration is ' \
            'not allowed for this kind of experiment metadata.')

    def test_missing_iso_volume(self):
        self._test_invalid_file('missing_iso_volume.xls',
            'There are positions in this ISO layout that lack either an ' \
            'ISO volume or an ISO concentration.')

    def test_missing_iso_concentration(self):
        self._test_invalid_file('missing_iso_concentration.xls',
            'There are positions in this ISO layout that lack either an ' \
            'ISO volume or an ISO concentration.')


class IsoRequestScreenParserTestCase(IsoRequestParserTest):

    def set_up(self):
        IsoRequestParserTest.set_up(self)
        self.VALID_FILE = self.VALID_FILE_SCREEN
        self.experiment_type_id = EXPERIMENT_SCENARIOS.SCREENING

    def _test_and_expect_errors(self, msg=None):
        IsoRequestParserTest._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_association_data())
        self.assert_is_none(self.tool.get_molecule_type())
        self.assert_is_none(self.tool.get_iso_volume())

    def test_if_result(self):
        self._test_if_result()

    def test_handler_user(self):
        self._test_invalid_user()

    def test_screening_result(self):
        self._continue_setup(self.VALID_FILE)
        iso_request = self.tool.get_result()
        self.assert_is_not_none(iso_request)
        tf_layout = self.tool.get_transfection_layout()
        self.assert_equal(len(tf_layout), 308)
        all_tags = tf_layout.get_tags()
        self.assert_equal(len(all_tags), 294)
        k23_pos = get_rack_position_from_label('K23')
        k23_tf = tf_layout.get_working_position(k23_pos)
        self.assert_is_not_none(k23_tf)
        self.assert_true(k23_tf.is_untreated)
        reag_name_tag = Tag(TransfectionParameters.DOMAIN,
                            TransfectionParameters.REAGENT_NAME,
                            'RNAiMax')
        reag_df_tag = Tag(TransfectionParameters.DOMAIN,
                          TransfectionParameters.REAGENT_DIL_FACTOR, '600')
        iso_vol_tag = Tag(IsoParameters.DOMAIN, IsoParameters.ISO_VOLUME, '1')
        mock_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                         IsoParameters.MOCK_TYPE_VALUE)
        mock_md_tag = Tag(IsoParameters.DOMAIN,
                          IsoParameters.MOLECULE_DESIGN_POOL,
                          IsoParameters.MOCK_TYPE_VALUE)
        mock_pos = get_rack_position_from_label('C10')
        mock_tags = [mock_tag, mock_md_tag, iso_vol_tag, reag_name_tag,
                     reag_df_tag,
                     Tag(IsoParameters.DOMAIN, IsoParameters.ISO_CONCENTRATION,
                         TransfectionPosition.NONE_REPLACER),
                     Tag(TransfectionParameters.DOMAIN,
                         TransfectionParameters.FINAL_CONCENTRATION,
                         TransfectionPosition.NONE_REPLACER)]
        mock_tag_set = tf_layout.get_tags_for_position(mock_pos)
        self.assert_equal(len(mock_tags), len(mock_tag_set))
        for tag in mock_tags: self.assert_true(tag in mock_tag_set)
        control_pos = get_rack_position_from_label('C4')
        control_tag = Tag(IsoParameters.DOMAIN,
                          IsoParameters.MOLECULE_DESIGN_POOL,
                          '205201')
        iso_conc_tag = Tag(IsoParameters.DOMAIN,
                           IsoParameters.ISO_CONCENTRATION, '5000')
        fixed_tag = Tag(IsoParameters.DOMAIN, IsoParameters.POS_TYPE,
                        IsoParameters.FIXED_TYPE_VALUE)
        final_conc_tag = Tag(TransfectionParameters.DOMAIN,
                             TransfectionParameters.FINAL_CONCENTRATION, '10')
        control_tags = [control_tag, fixed_tag, iso_conc_tag, iso_vol_tag,
                        reag_name_tag, reag_df_tag, final_conc_tag]
        control_tag_set = tf_layout.get_tags_for_position(control_pos)
        self.assert_equal(len(control_tags), len(control_tag_set))
        for tag in control_tags: self.assert_true(tag in control_tag_set)
        md_positions = ['C4', 'F14', 'K8', 'M17']
        md_pos_set = tf_layout.get_positions_for_tag(control_tag)
        self.assert_equal(len(md_positions), len(md_pos_set))
        for pos in md_pos_set: self.assert_true(pos.label in md_positions)
        self.assert_equal(self.tool.get_molecule_type().id,
                          MOLECULE_TYPE_IDS.SIRNA)
        self.assert_equal(self.tool.get_iso_volume(), 1)
        # test rack sector association
        ad = self.tool.get_association_data()
        self.assert_equal(ad.number_sectors, 1)
        exp_concentrations = {0 : 10}
        self.assert_equal(ad.sector_concentrations, exp_concentrations)
        exp_parent_sectors = {0 : None}
        self.assert_equal(ad.parent_sectors, exp_parent_sectors)
        exp_associated_sectors = [[0]]
        ass_sectors = ad.associated_sectors
        self.assert_equal(len(ass_sectors), len(exp_associated_sectors))
        for sectors in exp_associated_sectors:
            self.assert_true(sectors in ass_sectors)

    def test_screening_with_multiple_concentrations(self):
        self._continue_setup('valid_screening_several_conc.xls')
        iso_request = self.tool.get_result()
        self.assert_is_not_none(iso_request)
        tf_layout = self.tool.get_transfection_layout()
        b13_pos = get_rack_position_from_label('B13')
        b14_pos = get_rack_position_from_label('B14')
        b13_tf = tf_layout.get_working_position(b13_pos)
        b14_tf = tf_layout.get_working_position(b14_pos)
        self.assert_equal(b13_tf.molecule_design_pool,
                          b14_tf.molecule_design_pool)
        self.assert_equal(b13_tf.molecule_design_pool, 'md_002')
        c13_pos = get_rack_position_from_label('C13')
        c14_pos = get_rack_position_from_label('C14')
        c13_tf = tf_layout.get_working_position(c13_pos)
        c14_tf = tf_layout.get_working_position(c14_pos)
        self.assert_equal(c13_tf.molecule_design_pool,
                          c14_tf.molecule_design_pool)
        self.assert_equal(c13_tf.molecule_design_pool, 'md_013')
        # test mock
        mock_tag = Tag(IsoParameters.DOMAIN, IsoParameters.MOLECULE_DESIGN_POOL,
                       IsoParameters.MOCK_TYPE_VALUE)
        mock_positions = [get_rack_position_from_label('C9'),
                          get_rack_position_from_label('C10'),
                          get_rack_position_from_label('I21'),
                          get_rack_position_from_label('I22')]
        mock_pos_set = iso_request.iso_layout.get_positions_for_tag(mock_tag)
        self._compare_pos_sets(mock_positions, mock_pos_set)
        self.assert_equal(self.tool.get_molecule_type().id,
                          MOLECULE_TYPE_IDS.SIRNA)
        self.assert_equal(self.tool.get_iso_volume(), 4)
        # test rack sector association
        ad = self.tool.get_association_data()
        self.assert_equal(ad.number_sectors, 4)
        exp_concentrations = {0 : 10, 1: 20, 2 : 10, 3 : 20}
        self.assert_equal(ad.sector_concentrations, exp_concentrations)
        exp_parent_sectors = {0 : 1, 1 : None, 2 : 3, 3 : None}
        self.assert_equal(ad.parent_sectors, exp_parent_sectors)
        exp_associated_sectors = [[0, 1], [2, 3]]
        ass_sectors = ad.associated_sectors
        self.assert_equal(len(ass_sectors), len(exp_associated_sectors))
        for sectors in exp_associated_sectors:
            self.assert_true(sectors in ass_sectors)

    def test_screening_with_multiple_concentrations2(self):
        # other typical case
        self._continue_setup('valid_screening_several_conc2.xls')
        iso_request = self.tool.get_result()
        self.assert_is_not_none(iso_request)
        tf_layout = self.tool.get_transfection_layout()
        c19_pos = get_rack_position_from_label('C19')
        c20_pos = get_rack_position_from_label('C20')
        d19_pos = get_rack_position_from_label('D19')
        c19_tf = tf_layout.get_working_position(c19_pos)
        c20_tf = tf_layout.get_working_position(c20_pos)
        d19_tf = tf_layout.get_working_position(d19_pos)
        self.assert_equal(c19_tf.molecule_design_pool,
                          c20_tf.molecule_design_pool)
        self.assert_equal(c19_tf.molecule_design_pool,
                          d19_tf.molecule_design_pool)
        self.assert_equal(c19_tf.molecule_design_pool, 'md_002')
        self.assert_equal(c19_tf.final_concentration, 50)
        self.assert_equal(c19_tf.iso_concentration, None)
        self.assert_equal(c20_tf.final_concentration, 100)
        self.assert_equal(c20_tf.iso_concentration, None)
        self.assert_equal(d19_tf.final_concentration, 150)
        self.assert_equal(d19_tf.iso_concentration, None)
        self.assert_equal(self.tool.get_iso_volume(), None)
        # test rack sector association
        ad = self.tool.get_association_data()
        self.assert_equal(ad.number_sectors, 4)
        exp_concentrations = {0 : 50, 1: 100, 2 : 150, 3 : None}
        self.assert_equal(ad.sector_concentrations, exp_concentrations)
        exp_parent_sectors = {0 : 1, 1 : 2, 2 : None}
        self.assert_equal(ad.parent_sectors, exp_parent_sectors)
        exp_associated_sectors = [[0, 1, 2]]
        ass_sectors = ad.associated_sectors
        self.assert_equal(len(ass_sectors), len(exp_associated_sectors))
        for sectors in exp_associated_sectors:
            self.assert_true(sectors in ass_sectors)
        # check molecule type
        self.assert_equal(self.tool.get_molecule_type().id,
                          MOLECULE_TYPE_IDS.SIRNA)

    def test_unspecific_errors(self):
        self._test_unspecific_errors()

    def test_missing_parameter(self):
        self._test_invalid_file('missing_parameter.xls', 'Could not find ' \
            'value for the following ISO meta data specifications')

    def test_screening_inconsistent_rack_sectors(self):
        self._test_invalid_file('screen_unequal_conc_blocks.xls',
            'Error when trying to associated rack sectors!')

    def test_different_number_of_concentrations(self):
        self._test_invalid_file('screen_inconsistent_conc_number.xls',
            'The concentrations within the ISO layout are not consistent. ' \
            'Some sample positions have more or different concentrations ' \
            'than others.')

    def test_screening_with_multiple_final_concentrations(self):
        self._test_invalid_file('multiple_final_conc.xls',
            'final concentrations in the screening layout are related to ' \
            'more than one ISO concentration or vice versa')

    def test_screening_with_multiple_iso_concentrations(self):
        self._test_invalid_file('multiple_iso_conc.xls',
            'final concentrations in the screening layout are related to ' \
            'more than one ISO concentration or vice versa')

    def test_screening_with_iso_volume_layout(self):
        self._test_invalid_file('screen_with_iso_volume.xls',
            'Some factors must not be specified as layouts')
        self._check_error_messages('iso volume')

    def test_screening_with_reagent_name_layout(self):
        self._test_invalid_file('screen_with_reagent_name.xls',
            'Some factors must not be specified as layouts')
        self._check_error_messages('reagent name')

    def test_screening_with_reagent_dilution_factor_layout(self):
        self._test_invalid_file('screen_with_reagent_dil_factor.xls',
            'Some factors must not be specified as layouts')
        self._check_error_messages('reagent dilution factor')

    def test_screening_missing_final_conc(self):
        self._test_invalid_file('screen_missing_final_conc.xls',
            'Invalid final concentration for the following rack positions')

    def test_screening_invalid_iso_conc_default(self):
        self._test_invalid_file('invalid_default_iso_conc_screen.xls',
                                'invalid ISO concentration')

    def test_screening_invalid_final_conc_default(self):
        self._test_invalid_file('invalid_default_final_conc_screen.xls',
                                'Invalid final concentration')

    def test_screening_missing_number_of_aliquots(self):
        self._test_invalid_file('screen_missing_aliquot.xls',
                                'number_of_aliquots')

    def test_screening_invalid_number_of_aliquots(self):
        self._test_invalid_file('screen_invalid_aliquot.xls',
            'number of aliquots must be a positive integer')

    def test_different_molecule_types_screening(self):
        self._test_invalid_file('different_molecule_types_screen.xls',
            'There is more than one molecule type in the ISO layout')

    def test_stock_concentration_multi_conc(self):
        self._test_invalid_file('screen_stock_conc_multi_conc.xls',
            'Ordering molecule design pools in stock concentration is not ' \
            'allowed for this kind of experiment metadata.')


class IsoRequestLibraryParserTestCase(IsoRequestParserTest):
    """
    We test only experiment type specific tests here because other wise
    we would need a whole bunch of new test files.
    """
    def set_up(self):
        IsoRequestParserTest.set_up(self)
        self.VALID_FILE = 'valid_library.xls'
        self.experiment_type_id = EXPERIMENT_SCENARIOS.LIBRARY

    def _test_and_expect_errors(self, msg=None):
        IsoRequestParserTest._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_library())
        self.assert_is_none(self.tool.get_final_concentration())
        self.assert_is_none(self.tool.get_reagent_name())
        self.assert_is_none(self.tool.get_reagent_dil_factor())

    def test_if_result(self):
        self._test_if_result()

    def test_handler_user(self):
        self._test_invalid_user()

    def test_result(self):
        self._continue_setup(self.VALID_FILE)
        iso_request = self.tool.get_result()
        self.assert_is_not_none(iso_request)
        # check metadata
        delivery_date = date(2012, 7, 17)
        attrs = dict(delivery_date=delivery_date, plate_set_label='poollib',
                     number_aliquots=1, requester=self.user,
                     isos=[], owner='', experiment_metadata=None,
                     comment='library ISO request test')
        check_attributes(iso_request, attrs)
        # check rack layout
        rl = iso_request.iso_layout
        self.assert_equal(len(rl.tagged_rack_position_sets), 285)
        self.assert_equal(len(rl.get_positions()), 292)
        # parameter tag
        pool_tag = Tag(IsoParameters.DOMAIN, IsoParameters.MOLECULE_DESIGN_POOL,
                       '205200')
        positions_pool = [get_rack_position_from_label('D2'),
                          get_rack_position_from_label('D15'),
                          get_rack_position_from_label('K10'),
                          get_rack_position_from_label('K22')]
        pos_set_pool = rl.get_positions_for_tag(pool_tag)
        self._compare_pos_sets(positions_pool, pos_set_pool)
        # additional tag (are not stored in the rack rack layout yet)
        num_tag = Tag(TransfectionParameters.DOMAIN, 'Number designs', '1')
        has_tag = False
        add_trps = self.tool.get_additional_trps()
        self.assert_equal(len(add_trps), 3)
        for trps in add_trps.values():
            self.assert_equal(len(trps.tags), 1)
            for tag in trps.tags:
                if tag == num_tag:
                    has_tag = True
                    exp_pos_set = [get_rack_position_from_label('D2'),
                                   get_rack_position_from_label('D15'),
                                   get_rack_position_from_label('K10'),
                                   get_rack_position_from_label('K22')]
                    self._compare_pos_sets(exp_pos_set,
                                           trps.rack_position_set.positions)
        self.assert_true(has_tag)
        # additional handler values
        lib = self.tool.get_library()
        self.assert_is_not_none(lib)
        self.assert_equal(lib.label, 'poollib')
        self.assert_equal(self.tool.get_final_concentration(), 30)
        self.assert_equal(self.tool.get_reagent_name(), 'RNAiMax')
        self.assert_equal(self.tool.get_reagent_dil_factor(), 1400)

    def test_invalid_metadata(self):
        self._test_invalid_file('library_invalid_metadata.xls',
                                'Unknown metadata specifiers')

    def test_library_with_iso_concentration(self):
        self._test_invalid_file('library_with_iso_concentration.xls',
                                'Invalid factors found: iso concentration')

    def test_library_with_iso_volume(self):
        self._test_invalid_file('library_with_iso_volume.xls',
                                'Invalid factors found: iso volume')

    def test_library_with_reagent_dilution_factor(self):
        self._test_invalid_file('library_with_reagent_df.xls',
            'Invalid factors found: reagent dilution factor')

    def test_library_with_reagent_name(self):
        self._test_invalid_file('library_with_reagent_name.xls',
                             'Invalid factors found: reagent name')

    def test_library_with_final_concentration(self):
        self._test_invalid_file('library_with_final_conc.xls',
                             'Invalid factors found: final concentration')

    def test_library_invalid_final_concentration(self):
        self._test_invalid_file('library_invalid_final_conc.xls',
                                'Invalid final concentration')

    def test_library_invalid_supplier(self):
        self._test_invalid_file('library_invalid_supplier.xls',
                                'Some suppliers could not be found in the DB')

    def test_library_unknown_library(self):
        self._test_invalid_file('library_unknown_library.xls',
                                'Unknown library "unknown_lib"')

    def test_library_invalid_rack_shape(self):
        self._test_invalid_file('library_invalid_shape.xls',
            'Library "poollib" requires a 16x24 layout. You have provided a ' \
            '8x12 layout')

    def test_library_no_controls(self):
        self._test_invalid_file('library_no_controls.xls',
            'There are no fixed positions in this ISO layout!')

    def test_library_missing_sample_position(self):
        self._test_invalid_file('library_missing_sample_position.xls',
            'The following positions are reserved for library samples: J3. ' \
            'You have assigned a different position type to them')

    def test_library_invalid_sample_position(self):
        self._test_invalid_file('library_invalid_sample_position.xls',
            'The following positions are reserved for library samples: J3. ' \
            'You have assigned a different position type to them')

    def test_library_additional_sample_position(self):
        self._test_invalid_file('library_additional_sample_position.xls',
            'The following positions must not be samples: I3, K3, M3, O3')


class IsoRequestManualParserTestCase(IsoRequestParserTest):
    """
    We test only experiment type specific tests here because other wise
    we would need a whole bunch of new test files.
    """

    def set_up(self):
        IsoRequestParserTest.set_up(self)
        self.VALID_FILE = 'valid_manual.xls'
        self.experiment_type_id = EXPERIMENT_SCENARIOS.MANUAL

    def test_if_result(self):
        self._test_if_result()

    def test_handler_user(self):
        self._test_invalid_user()

    def __test_result(self):
        self._continue_setup(self.VALID_FILE)
        iso_request = self.tool.get_result()
        self.assert_is_not_none(iso_request)
        # check metadata
        delivery_date = date(2012, 8, 7)
        attrs = dict(delivery_date=delivery_date, plate_set_label='test_manual',
                     number_aliquots=1, requester=self.user,
                     isos=[], owner='', experiment_metadata=None,
                     comment='This is test file for manual scenarios.')
        check_attributes(iso_request, attrs)
        # check rack layout
        rl = iso_request.iso_layout
        self.assert_equal(len(rl.tagged_rack_position_sets), 7)
        self.assert_equal(len(rl.get_positions()), 4)
        # check transfection parameters
        b2_pos = get_rack_position_from_label('B2')
        b3_pos = get_rack_position_from_label('B3')
        b4_pos = get_rack_position_from_label('B4')
        b5_pos = get_rack_position_from_label('B5')
        md_tag = Tag(IsoParameters.DOMAIN, IsoParameters.MOLECULE_DESIGN_POOL,
                     '205201')
        md_positions = [b3_pos]
        md_pos_set = rl.get_positions_for_tag(md_tag)
        self._compare_pos_sets(md_positions, md_pos_set)
        # check label coded tags
        vol_tag = Tag(IsoParameters.DOMAIN, IsoParameters.ISO_VOLUME, '4')
        vol_positions = [b2_pos, b3_pos]
        vol_pos_set = rl.get_positions_for_tag(vol_tag)
        self._compare_pos_sets(vol_positions, vol_pos_set)
        # test metadata specification only
        supplier_tag = Tag(IsoParameters.DOMAIN, IsoParameters.SUPPLIER,
                           'Ambion')
        supplier_positions = [b2_pos, b3_pos, b4_pos, b5_pos]
        supplier_pos_set = rl.get_positions_for_tag(supplier_tag)
        self._compare_pos_sets(supplier_positions, supplier_pos_set)
        # additional tags
        sample_type_tag = Tag('transfection', 'sample_type', 'pos')
        add_tags = self.tool.get_additional_trps()
        self.assert_equal(len(add_tags), 3)
        sample_type_positions = [b2_pos]
        exp_pos_set = RackPositionSet.from_positions(sample_type_positions)
        exp_hash_value = exp_pos_set.hash_value
        has_tag = False
        for pos_hash_value, trps in add_tags.iteritems():
            self.assert_equal(len(trps.tags), 1)
            for tag in trps.tags:
                if sample_type_tag == tag:
                    has_tag = True
                    self.assert_equal(pos_hash_value, exp_hash_value)
        self.assert_true(has_tag)

    def test_result_96(self):
        self.__test_result()

    def test_result_384(self):
        self.VALID_FILE = 'valid_manual_384.xls'
        self.__test_result()

    def test_manual_with_invalid_metadata(self):
        self._test_invalid_file('manual_invalid_metadata.xls',
            'Unknown metadata specifiers: final concentration, number of ' \
            'aliquots, reagent dilution factor, reagent name')

    def test_manual_with_mock(self):
        self._test_invalid_file('manual_with_mock.xls',
            'There are some positions in the ISO layout that are not allowed ' \
            'for this type of experiment metadata (manual optimisation): ' \
            'mock (B6).')

    def test_manual_with_untreated(self):
        self._test_invalid_file('manual_with_untreated.xls',
            'There are some positions in the ISO layout that are not allowed ' \
            'for this type of experiment metadata (manual optimisation): ' \
            'untreated (B6).')

    def test_manual_with_floating(self):
        self._test_invalid_file('manual_with_floating.xls',
            'There are some positions in the ISO layout that are not allowed ' \
            'for this type of experiment metadata (manual optimisation): ' \
            'floating (B6, B7).')

#    TODO: review after ISO processing refactoring
#    def test_manual_duplicate_molecule_design_pool(self):
#        self._test_invalid_file('manual_duplicate_md.xls',
#            'If you order a molecule design pool in stock concentration, ' \
#            'this pool may only occur once on the ISO plate. The following ' \
#            'pools violate this rule: 330001.')

    def test_manual_invalid_dilution_volumes(self):
        self._test_invalid_file('manual_invalid_dilution_volumes.xls',
            'The volumes you have requested are not sufficient to prepare ' \
            'the requested dilution of the stock concentration')

    def test_manual_no_pools(self):
        self._test_invalid_file('manual_no_pools.xls',
            'There are no fixed positions in this ISO layout!')

#    TODO: review after ISO processing refactoring
#    def test_manual_too_many_pools(self):
#        self._test_invalid_file('manual_too_many_pools.xls',
#            '384-well manual optimisation ISO layouts with more than 96 ' \
#            'distinct molecule design pools are not supported')


class IsoRequestOrderParserTestCase(IsoRequestParserTest):

    def set_up(self):
        IsoRequestParserTest.set_up(self)
        self.VALID_FILE = 'valid_order.xls'
        self.experiment_type_id = EXPERIMENT_SCENARIOS.ORDER_ONLY


    def test_if_result(self):
        self._test_if_result()

    def test_handler_user(self):
        self._test_invalid_user()

    def test_result(self):
        self._continue_setup()
        iso_request = self.tool.get_result()
        self.assert_is_not_none(iso_request)
        # check metadata
        delivery_date = date(2013, 7, 1)
        attrs = dict(delivery_date=delivery_date,
                     plate_set_label='all_sorts_of_pools',
                     number_aliquots=1, requester=self.user,
                     isos=[], owner='', experiment_metadata=None,
                     comment='ISO request without experiment')
        check_attributes(iso_request, attrs)
        # check rack layout
        rl = iso_request.iso_layout
        pos_b2 = get_rack_position_from_label('B2')
        pos_b4 = get_rack_position_from_label('B4')
        pos_b6 = get_rack_position_from_label('B6')
        pos_b8 = get_rack_position_from_label('B8')
        pos_b10 = get_rack_position_from_label('B10')
        all_positions = [pos_b2, pos_b4, pos_b6, pos_b8, pos_b10]
        self.assert_equal(len(rl.tagged_rack_position_sets), 6)
        pos_set = rl.get_positions()
        self._compare_pos_sets(all_positions, pos_set)
        # check transfection layout
        tf_layout = self.tool.get_transfection_layout()
        self.assert_equal(len(tf_layout), len(all_positions))
        b2_tf = tf_layout.get_working_position(pos_b2)
        self.assert_equal(b2_tf.molecule_design_pool_id, 205201)
        self.assert_equal(b2_tf.iso_volume, 1)
        self.assert_equal(b2_tf.supplier.name, 'Ambion')
        b8_tf = tf_layout.get_working_position(pos_b8)
        self.assert_equal(b8_tf.molecule_design_pool_id, 1056000)
        self.assert_equal(b8_tf.iso_volume, 1)
        self.assert_is_none(b8_tf.supplier)
        # check additional tags
        add_tags = self.tool.get_additional_trps()
        self.assert_equal(len(add_tags), 5)
        pool_tag = Tag('transfection', 'molecule_type', 'siRNA pool')
        pool_positions = [pos_b8]
        exp_pos_set = RackPositionSet.from_positions(pool_positions)
        exp_hash_value = exp_pos_set.hash_value
        has_tag = False
        for pos_hash_value, trps in add_tags.iteritems():
            self.assert_equal(len(trps.tags), 1)
            for tag in trps.tags:
                if pool_tag == tag:
                    has_tag = True
                    self.assert_equal(pos_hash_value, exp_hash_value)
        self.assert_true(has_tag)

    def test_plate_label_too_long(self):
        self._test_invalid_file('order_plate_label_too_long.xls',
                'The maximum length for plate set labels is 24 characters ' \
                '(obtained: "this_label_is_a_little_too_long", 31 characters)')

    def test_with_mock_positions(self):
        self._test_invalid_file('order_with_mock.xls',
            'There are some positions in the ISO layout that are not allowed ' \
            'for this type of experiment metadata (ISO without experiment): ' \
            'mock (B10)')

    def test_with_untreated_positions(self):
        self._test_invalid_file('order_with_untreated.xls',
            'There are some positions in the ISO layout that are not allowed ' \
            'for this type of experiment metadata (ISO without experiment): ' \
            'untreated (B10)')

    def test_with_untreated_floatings(self):
        self._test_invalid_file('order_with_floating.xls',
            'There are some positions in the ISO layout that are not allowed ' \
            'for this type of experiment metadata (ISO without experiment): ' \
            'floating (B10)')

    def test_multiple_occurrence(self):
        self._test_invalid_file('order_multiple_occurrence.xls',
            'In an ISO request without experiment, each molecule design pool ' \
            'may occur only once. The following pools occur several times: ' \
            '180202, 1056000')
