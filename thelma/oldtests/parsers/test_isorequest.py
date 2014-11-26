"""
tests the ISO excel file parser

AAB July 1a, 2011
"""

from datetime import date
from everest.repositories.rdb.testing import check_attributes
from thelma.automation.handlers.isorequest import IsoRequestParserHandler
from thelma.automation.parsers.isorequest import IsoRequestParser
from thelma.automation.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.semiconstants import get_384_rack_shape
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.semiconstants import get_positions_for_shape
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.metadata.base import TransfectionLayout
from thelma.automation.tools.metadata.base import TransfectionParameters
from thelma.automation.tools.metadata.base import TransfectionPosition
from thelma.automation.utils.iso import IsoRequestParameters
from thelma.automation.utils.layouts import EMPTY_POSITION_TYPE
from thelma.automation.utils.layouts import FIXED_POSITION_TYPE
from thelma.automation.utils.layouts import FLOATING_POSITION_TYPE
from thelma.automation.utils.layouts import LIBRARY_POSITION_TYPE
from thelma.automation.utils.layouts import MOCK_POSITION_TYPE
from thelma.automation.utils.layouts import UNTRANSFECTED_POSITION_TYPE
from thelma.entities.iso import LabIsoRequest
from thelma.entities.library import MoleculeDesignLibrary
from thelma.entities.utils import get_user
from thelma.oldtests.tools.tooltestingutils import ParsingTestCase


# I (Anna) have summarized several files in one test case to speed things up
# because test setup and tear down take the most time during testing

class _IsoRequestParserTestCase(ParsingTestCase):

    _PARSER_CLS = IsoRequestParser
    _TEST_FILE_SUBDIRECTORY = ''

    def set_up(self):
        ParsingTestCase.set_up(self)
        self.user = get_user('it')
        self.VALID_FILE = 'valid_file.xls'
        self.TEST_FILE_PATH = 'thelma:tests/parsers/isorequest/%s/' \
                               % (self._TEST_FILE_SUBDIRECTORY)
        self.experiment_type_id = None
        # expected result values
        self.expected_ir_attrs = dict()
        self.exp_layout_shape = None
        # pos_label - pool, pos_type, iso vol, iso conc, final conc, reagent
        # name, reagent df
        self.layout_data = dict()
        self.exp_association_data_values = dict()
        self.num_add_control_tags = 2
        self.num_add_other_tags = 8

    def tear_down(self):
        ParsingTestCase.tear_down(self)
        del self.experiment_type_id
        del self.expected_ir_attrs
        del self.layout_data
        del self.exp_association_data_values
        del self.num_add_control_tags
        del self.num_add_other_tags

    def _create_tool(self):
        self.tool = IsoRequestParserHandler.create(self.experiment_type_id,
                                                   self.stream, self.user,
                                                   None)

    def _check_result(self):
        self._continue_setup()
        iso_request = self.tool.get_result()
        self.assert_is_not_none(iso_request)
        self.assert_true(isinstance(iso_request, LabIsoRequest))
        self.assert_true(self.tool.has_iso_sheet())
        self.__check_entity_values(iso_request)
        self.__check_transfection_layout()
        self.__check_association_data()
        self._check_additional_trps()

    def __check_entity_values(self, iso_request):
        check_attributes(iso_request, self.expected_ir_attrs)
        self.assert_equal(len(iso_request.isos), 0)
        self.assert_is_none(iso_request.iso_plate_reservoir_specs)
        self.assert_is_none(iso_request.experiment_metadata)

    def __check_transfection_layout(self):
        exp_layout = self._build_expected_layout()
        attrs = ('molecule_design_pool', 'iso_volume', 'iso_concentration',
                 'final_concentration', 'reagent_name', 'reagent_dil_factor')
        tool_layout = self.tool.get_transfection_layout()
        self.assert_equal(len(tool_layout), len(exp_layout))
        self.assert_equal(tool_layout.shape, exp_layout.shape)
        for rack_pos, exp_pos in exp_layout.iterpositions():
            tool_pos = tool_layout.get_working_position(rack_pos)
            if tool_pos is None:
                msg = 'Position %s is missing!' % (rack_pos.label)
                raise AssertionError(msg)
            self.assert_is_not_none(tool_pos)
            for attr_name in attrs:
                if not getattr(exp_pos, attr_name) == \
                                        getattr(tool_pos, attr_name):
                    msg = 'Different value for attribute %s in position %s.\n' \
                          'Found: %s\nExpected: %s' \
                           % (attr_name, rack_pos.label,
                              getattr(tool_pos, attr_name),
                              getattr(exp_pos, attr_name))
                    raise AssertionError(msg)
            self.assert_is_none(tool_pos.optimem_dil_factor)

    def _build_expected_layout(self):
        exp_layout = TransfectionLayout(shape=self.exp_layout_shape)
        for pos_label, pos_data in self.layout_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            pool_id = pos_data[0]
            if isinstance(pool_id, int):
                pool = self._get_pool(pool_id)
            else:
                pool = pool_id
            tf_pos = TransfectionPosition(rack_position=rack_pos,
                        molecule_design_pool=pool,
                        position_type=pos_data[1],
                        iso_volume=pos_data[2],
                        iso_concentration=pos_data[3],
                        final_concentration=pos_data[4],
                        reagent_name=pos_data[5],
                        reagent_dil_factor=pos_data[6])
            exp_layout.add_position(tf_pos)
        return exp_layout

    def __check_association_data(self):
        ass_data = self.tool.get_association_data()
        if self.exp_association_data_values is None:
            self.assert_is_none(ass_data)
        else:
            for attr_name, exp_value in self.exp_association_data_values.\
                                        iteritems():
                value = getattr(ass_data, attr_name)
                if attr_name == 'associated_sectors': value.sort()
                if not exp_value == value:
                    msg = 'The %s values for the association data differs.' \
                          'Expected:%s\nFound:%s' % (attr_name, exp_value, value)
                    raise AssertionError(msg)

    def _check_additional_trps(self):
        add_trps = self.tool.get_additional_trps()
        self.assert_equal(len(add_trps), 3)
        for trps in add_trps.values():
            self.assert_equal(len(trps.tags), 1)
            rps = trps.rack_position_set
            for tag in trps.tags:
                self.assert_equal(tag.domain, 'transfection')
                self.assert_equal(tag.predicate, 'sample type')
                if len(rps) == self.num_add_control_tags:
                    self.assert_true(tag.value in ('pos_control',
                                                   'neg_control'))
                else:
                    self.assert_equal(tag.value, 'sample')
                    self.assert_equal(len(rps), self.num_add_other_tags)

    def _test_and_expect_errors(self, msg=None):
        ParsingTestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_transfection_layout())
        self.assert_is_none(self.tool.get_additional_trps())
        self.assert_is_none(self.tool.get_association_data())

    def _test_invalid_user(self):
        self._continue_setup(self.VALID_FILE)
        self.user = None
        self._test_and_expect_errors('The requester must be a User object')

#    def _test_invalid_file(self, file_name, msg):
#        self.tool.reset()
#        ParsingTestCase._test_invalid_file(self, file_name, msg)


class _IsoRequestParserHandlerUnspecificErrorsDummy(IsoRequestParserHandler):
    """
    Used to test errors which are not specific for the experiment type.
    """
    SUPPORTED_SCENARIO = 'QPCR' # we need to use a valid one for display names
    ALLOWED_POSITION_TYPES = set([FIXED_POSITION_TYPE, FLOATING_POSITION_TYPE,
                              MOCK_POSITION_TYPE, LIBRARY_POSITION_TYPE,
                              UNTRANSFECTED_POSITION_TYPE, EMPTY_POSITION_TYPE])

    ISO_REQUEST_LAYOUT_PARAMETERS = IsoRequestParameters.ALL
    TRANSFECTION_LAYOUT_PARAMETERS = [
                TransfectionParameters.FINAL_CONCENTRATION,
                TransfectionParameters.REAGENT_DIL_FACTOR]
    REQUIRED_METADATA = [IsoRequestParserHandler.PLATE_SET_LABEL_KEY,
                         IsoRequestParserHandler.DELIVERY_DATE_KEY,
                         IsoRequestParserHandler.COMMENT_KEY]
    OPTIONAL_PARAMETERS = [IsoRequestParameters.ISO_VOLUME,
                           TransfectionParameters.REAGENT_NAME,
                           TransfectionParameters.FINAL_CONCENTRATION]

    def _create_positions(self):
        parameter_map = self.parser.parameter_map
        pool_container = parameter_map[IsoRequestParameters.
                                       MOLECULE_DESIGN_POOL]

        for pos_container in self.parser.shape.position_containers:
            pos_label = pos_container.label

            pool_id = self._get_value_for_rack_pos(pool_container, pos_label)
            pos_type = self._get_position_type(pool_id, pos_label)
            if pos_type is None: continue

            pool = self._get_molecule_design_pool_for_id(pool_id, pos_type,
                                                         pos_label)

            iso_volume = self._get_iso_volume(pos_label, pos_type, True)
            iso_conc = self._get_iso_concentration(pos_label, pos_type, True)
            final_conc = self._get_final_concentration(pos_label, pos_type,
                                                       True)
            reagent_name = self._get_reagent_name(pos_label, pos_type)
            reagent_df = self._get_reagent_dilution_factor(pos_label, pos_type)

            # Create position
            if pos_type == EMPTY_POSITION_TYPE or pool is None: continue
            kw = dict(molecule_design_pool=pool, iso_volume=iso_volume,
                  iso_concentration=iso_conc, reagent_name=reagent_name,
                  reagent_dil_factor=reagent_df, final_concentration=final_conc)
            self._add_position_to_layout(pos_container, kw)


class IsoRequestUnspecificErrorsTestCase(_IsoRequestParserTestCase):

    _TEST_FILE_SUBDIRECTORY = 'unspecific'

    def set_up(self):
        _IsoRequestParserTestCase.set_up(self)
        self.expected_ir_attrs = dict(comment='Fits to all scenarios',
                    requester=self.user,
                    delivery_date=date(2016, 9, 17),
                    process_job_first=True,
                    number_aliquots=1)
        self.exp_layout_shape = get_96_rack_shape()
        # pos_label - pool, pos_type, iso vol, iso conc, final conc, reagent
        # name, reagent df
        self.layout_data = dict(
            b2=[205200, 'fixed', None, 500, 5, 'mix1', 14],
            b3=[205200, 'fixed', None, 500, 10, 'mix1', 14],
            c2=[1056000, 'fixed', None, 500, 5, 'mix1', 14],
            c3=[1056000, 'fixed', None, 500, 10, 'mix1', 14],
            d2=['md_001', 'floating', None, 500, 5, 'mix1', 14],
            d3=['md_002', 'floating', None, 500, 10, 'mix1', 14],
            e2=['mock', 'mock', None, 'None', 'None', 'mix1', 14],
            e3=['mock', 'mock', None, 'None', 'None', 'mix1', 14],
            f2=['library', 'library', None, 500, 5, 'mix1', 14],
            f3=['library', 'library', None, 500, 10, 'mix1', 14],
            g2=['untransfected', 'untransfected', 'None', 'None',
                'untransfected', 'None', 'untransfected'],
            g3=['untransfected', 'untransfected', 'None', 'None',
                'untransfected', 'None', 'untransfected'])
        self.num_add_control_tags = 2
        self.num_add_other_tags = 8

    def _create_tool(self):
        self.tool = _IsoRequestParserHandlerUnspecificErrorsDummy(self.stream,
                                                                  self.user)

    def test_if_result(self):
        self._test_if_result()

    def test_result(self):
        self._check_result()

    def test_result_associations(self):
        # 2x2 sectors horizontal, including controls
        self.VALID_FILE = 'valid_file_asso_384a.xls'
        self.exp_layout_shape = get_384_rack_shape()
        self.num_add_control_tags = 4
        self.num_add_other_tags = 12
        self.exp_association_data_values = dict(
                number_sectors=4,
                associated_sectors=[[0, 1], [2, 3]],
                parent_sectors={0 : 1, 1 : None, 2 : 3, 3 : None},
                sector_concentrations={0 : 5, 1 : 10, 2: 5, 3 : 10},
                iso_concentrations={0 : 50, 1 : 100, 2: 50, 3 : 100},
                sector_volumes={0 : 2, 1 : 2, 2 : 2, 3 : 2})
        # pos_label - pool, pos_type, iso vol, iso conc, final conc, reagent
        # name, reagent df
        self.layout_data = dict(
            b3=[205200, 'fixed', 2, 50, 5, 'mix1', 14],
            b4=[205200, 'fixed', 2, 100, 10, 'mix1', 14],
            b5=[1056000, 'fixed', 2, 50, 5, 'mix1', 14],
            b6=[1056000, 'fixed', 2, 100, 10, 'mix1', 14],
            c3=['md_001', 'floating', 2, 50, 5, 'mix1', 14],
            c4=['md_001', 'floating', 2, 100, 10, 'mix1', 14],
            c5=['md_003', 'floating', 2, 50, 5, 'mix1', 14],
            c6=['md_003', 'floating', 2, 100, 10, 'mix1', 14],
            d3=['md_002', 'floating', 2, 50, 5, 'mix1', 14],
            d4=['md_002', 'floating', 2, 100, 10, 'mix1', 14],
            d5=['md_004', 'floating', 2, 50, 5, 'mix1', 14],
            d6=['md_004', 'floating', 2, 100, 10, 'mix1', 14],
            e3=[205200, 'fixed', 2, 50, 5, 'mix1', 14],
            e4=[205200, 'fixed', 2, 100, 10, 'mix1', 14],
            e5=[1056000, 'fixed', 2, 50, 5, 'mix1', 14],
            e6=[1056000, 'fixed', 2, 100, 10, 'mix1', 14],
            f3=['mock', 'mock', 2, 'mock', 'mock', 'mix1', 14],
            f4=['mock', 'mock', 2, 'mock', 'mock', 'mix1', 14],
            f5=['untransfected', 'untransfected', 'None', 'untransfected',
                'untransfected', 'None', 'None'],
            f6=['untransfected', 'untransfected', 'None', 'untransfected',
                'untransfected', 'None', 'None'])
        self._check_result()
        # 2x2 sectors vertical, without controls
        # pos_label - pool, pos_type, iso vol, iso conc, final conc, reagent
        # name, reagent df
        self.VALID_FILE = 'valid_file_asso_384b.xls'
        self.layout_data = dict(
            c3=[205200, 'fixed', 2, 150, 15, 'mix1', 14],
            c4=[205200, 'fixed', 2, 100, 10, 'mix1', 14],
            d3=[205200, 'fixed', 2, 50, 5, 'mix1', 14],
            d4=['untransfected', 'untransfected', 'None', 'None', 'None',
                'None', 'None'],
            c5=[1056000, 'fixed', 2, 150, 15, 'mix1', 14],
            c6=[1056000, 'fixed', 2, 100, 10, 'mix1', 14],
            d5=[1056000, 'fixed', 2, 50, 5, 'mix1', 14],
            d6=['mock', 'mock', 2, 'None', 'None', 'mix1', 14],
            e3=['md_001', 'floating', 2, 100, 10, 'mix1', 14],
            e4=['md_002', 'floating', 2, 100, 10, 'mix1', 14],
            e5=['md_003', 'floating', 2, 100, 10, 'mix1', 14],
            e6=['md_004', 'floating', 2, 100, 10, 'mix1', 14],
            f3=['md_001', 'floating', 2, 50, 5, 'mix1', 14],
            f4=['md_002', 'floating', 2, 50, 5, 'mix1', 14],
            f5=['md_003', 'floating', 2, 50, 5, 'mix1', 14],
            f6=['md_004', 'floating', 2, 50, 5, 'mix1', 14],
            g3=[205200, 'fixed', 2, 150, 15, 'mix1', 14],
            g4=[205200, 'fixed', 2, 100, 10, 'mix1', 14],
            h3=[205200, 'fixed', 2, 50, 5, 'mix1', 14],
            h4=['untransfected', 'untransfected', 'None', 'None', 'None',
                'None', 'None'],
            g5=[1056000, 'fixed', 2, 150, 15, 'mix1', 14],
            g6=[1056000, 'fixed', 2, 100, 10, 'mix1', 14],
            h5=[1056000, 'fixed', 2, 50, 5, 'mix1', 14],
            h6=['mock', 'mock', 2, 'None', 'None', 'mix1', 14])
        self.expected_ir_attrs['process_job_first'] = False
        self.exp_association_data_values = dict(
                number_sectors=4,
                associated_sectors=[[0, 2], [1, 3]],
                parent_sectors={0 : None, 1 : None, 2 : 0, 3 : 1},
                sector_concentrations={0 : 10, 1 : 10, 2: 5, 3 : 5},
                iso_concentrations={0 : 100, 1 : 100, 2: 50, 3 : 50},
                sector_volumes={0 : 2, 1 : 2, 2 : 2, 3 : 2})
        self.num_add_control_tags = 6
        self._check_result()
        # 4 independent sectors, controls not included
        self.VALID_FILE = 'valid_file_asso_384c.xls'
        self.layout_data['e3'] = ['md_001', 'floating', 2, 100, 10, 'mix1', 14]
        self.layout_data['e4'] = ['md_002', 'floating', 2, 100, 10, 'mix1', 14]
        self.layout_data['e5'] = ['md_003', 'floating', 2, 100, 10, 'mix1', 14]
        self.layout_data['e6'] = ['md_004', 'floating', 2, 100, 10, 'mix1', 14]
        self.layout_data['f3'] = ['md_005', 'floating', 2, 100, 10, 'mix1', 14]
        self.layout_data['f4'] = ['md_006', 'floating', 2, 100, 10, 'mix1', 14]
        self.layout_data['f5'] = ['md_007', 'floating', 2, 100, 10, 'mix1', 14]
        self.layout_data['f6'] = ['md_008', 'floating', 2, 100, 10, 'mix1', 14]
        self.exp_association_data_values = dict(
                number_sectors=4,
                associated_sectors=[[0], [1], [2], [3]],
                parent_sectors={0 : None, 1 : None, 2 : None, 3 : None},
                sector_concentrations={0 : 10, 1 : 10, 2: 10, 3 : 10},
                iso_concentrations={0 : 100, 1 : 100, 2: 100, 3 : 100},
                sector_volumes={0 : 2, 1 : 2, 2 : 2, 3 : 2})
        self._check_result()

    def test_invalid_input_values(self):
        self._test_invalid_user()

    def test_no_sheet(self):
        # no sheet, no error
        self._continue_setup('no_sheet.xls')
        ir = self.tool.get_result()
        self.assert_is_none(ir)
        self.assert_false(self.tool.has_errors())

    def test_general_parser_errors(self):
        self._test_invalid_file('unicode.xls', 'Unknown character in cell D36')
        self._test_invalid_file('no_level_marker.xls',
            'Invalid factor definition! There must be a "Code" marker next ' \
            'to and a "Level" marker below the "Factor" marker!')
        self._test_invalid_file('no_code_marker.xls',
            'Invalid factor definition! There must be a "Code" marker next ' \
            'to and a "Level" marker below the "Factor" marker!')
        self._test_invalid_file('duplicate_tag.xls', 'Duplicate tag "type"')
        self._test_invalid_file('missing_code.xls',
            'On sheet "ISO" cell C37: There are levels in definition for ' \
            'factor "reagent dilution factor" that do not have a code!')
        self._test_invalid_file('code_without_label.xls',
            'cell B51: There is a code without label!')
        self._test_invalid_file('layout_alignment.xls',
            'Unable to find tags (factors) for layout in row 3! Please ' \
            'check the alignment of your layouts!')
        self._test_invalid_file('no_layouts.xls',
            'Could not find a layout definition on this sheet. Please make ' \
            'sure you have indicated them correctly.')
        self._test_invalid_file('invalid_rack_shape.xls',
            'cell F37: Invalid layout block shape (8x11). Make sure you ' \
            'have placed an "end" maker, too.')
        self._test_invalid_file('different_rack_shapes.xls',
            'There are 2 different layout shapes in the file (16x24 and ' \
            '8x12). For this parser, all layout dimensions have to be the ' \
            'same.')
        self._test_invalid_file('duplicate_code.xls',
            'Duplicate code "2" for factor "molecule design pool id".')
        self._test_invalid_file('unknown_code.xls',
            'Tag value (level) code "4" not found for factor "molecule ' \
            'design pool id".')
        self._test_invalid_file('duplicate_pool_definition.xls',
            'There are 2 different molecule design pool tag definitions ' \
            '("molecule design pool id" and "molecule design pool")')
        self._test_invalid_file('levels_interrupted.xls',
            'Tag value (level) code "u" not found for factor "molecule ' \
            'design pool id".')
        self._test_invalid_file('level_without_code.xls',
            'cell C17: There are levels in definition for factor ' \
            '"molecule design pool id" that do not have a code!')

    def test_specific_parser_errors(self):
        self._test_invalid_file('unknown_metadata_key.xls',
            'Unknown metadata specifiers: iso request label. Please use ' \
            'only the following specifiers: comment, delivery_date, ' \
            'final_concentration, iso_concentration, iso_volume, ' \
            'number_of_aliquots, plate_set_label, reagent_dilution_factor, ' \
            'reagent_name')
        self._test_invalid_file('missing_metadata_value.xls',
            'Could not find value for the following ISO meta data ' \
            'specifications: comment')
        self._test_invalid_file('no_pool_definition.xls',
            'Could not find a tag definition for molecule design pool IDs!')
        self._test_invalid_file('missing_parameter.xls',
            'There are no values specified for the parameter ' \
            '"reagent_dilution_factor". Please give a default value at the ' \
            'beginning of the sheet or specify the values as factor and ' \
            'levels. Valid factor names are: reagent_concentration, ' \
            'reagent_dilution_factor.')
        self._test_invalid_file('default_and_layout_value.xls',
            'You have specified both a default value and a layout for the ' \
            '"iso_concentration" parameter! Please choose one option.')

    def test_parameter_values(self):
        self._test_invalid_file('invalid_iso_volume.xls',
            'Some positions in the ISO request layout have invalid ISO ' \
            'volumes. The volume must be a positive number or left blank. ' \
            'Untreated position may have a volume "None", "untreated" or ' \
            '"untransfected". Affected positions: default value.')
        self._test_invalid_file('invalid_iso_volume_untreated.xls',
            'Some positions in the ISO request layout have invalid ISO ' \
            'volumes. The volume must be a positive number or left blank. ' \
            'Untreated position may have a volume "None", "untreated" or ' \
            '"untransfected". Affected positions: ')
        self._test_invalid_file('invalid_iso_concentration.xls',
            'Some positions in the ISO request layout have invalid ISO ' \
            'concentration. The concentration must be a positive number or ' \
            'left blank. Mock and untreated positions may have the values ' \
            '"None", "mock", "untreated" or "untransfected". Affected ' \
            'positions: default value.')
        self._test_invalid_file('invalid_iso_concentration_mock.xls',
             'Some positions in the ISO request layout have invalid ISO ' \
             'concentration. The concentration must be a positive number or ' \
             'left blank. Mock and untreated positions may have the values ' \
             '"None", "mock", "untreated" or "untransfected". Affected ' \
             'positions: E2, E3.')
        self._test_invalid_file('invalid_iso_concentration_untreated.xls',
             'Some positions in the ISO request layout have invalid ISO ' \
             'concentration. The concentration must be a positive number or ' \
             'left blank. Mock and untreated positions may have the values ' \
             '"None", "mock", "untreated" or "untransfected". Affected ' \
             'positions: G2, G3.')
        self._test_invalid_file('invalid_final_concentration.xls',
            'Invalid final concentration for the following rack positions ' \
            'in the ISO request layout: B2, C2, D2, F2. The final ' \
            'concentration must be a positive number! Mock and untreated ' \
            'positions may have the values "None", "mock", "untreated" or ' \
            '"untransfected" or no value.')
        self._test_invalid_file('invalid_final_concentration_mock.xls',
            'Invalid final concentration for the following rack positions ' \
            'in the ISO request layout: E2, E3. The final ' \
            'concentration must be a positive number! Mock and untreated ' \
            'positions may have the values "None", "mock", "untreated" or ' \
            '"untransfected" or no value.')
        self._test_invalid_file('invalid_final_concentration_untreated.xls',
            'Invalid final concentration for the following rack positions ' \
            'in the ISO request layout: G2, G3. The final ' \
            'concentration must be a positive number! Mock and untreated ' \
            'positions may have the values "None", "mock", "untreated" or ' \
            '"untransfected" or no value.')
        self._test_invalid_file('invalid_reagent_dil_factor.xls',
            'Invalid or missing reagent dilution factor for rack positions ' \
            'in the ISO request layout: C2, C3. The dilution factor must be ' \
            '1 or larger! Untreated position may have the values "None", ' \
            '"untreated" or "untransfected".')
        self._test_invalid_file('invalid_reagent_dil_factor_untreated.xls',
            'Invalid or missing reagent dilution factor for rack positions ' \
            'in the ISO request layout: G2, G3. The dilution factor must be ' \
            '1 or larger! Untreated position may have the values "None", ' \
            '"untreated" or "untransfected".')
        self._test_invalid_file('invalid_reagent_name.xls',
            'Invalid or missing reagent name for the following rack ' \
            'positions in the ISO request layout: default value. The ' \
            'reagent name must have a length of at least 2! Untreated ' \
            'position may have the values "None", "untreated" or ' \
            '"untransfected".')
        self._test_invalid_file('forbidden_parameters.xls',
            'Some factors must not be specified as layouts, because there ' \
            'might only be one value for the whole layout (use the metadata ' \
            'specification in this case) or no value at all (current ' \
            'experiment type: qPCR). Invalid factors found: reagent name')

    def test_pools(self):
        self._test_invalid_file('missing_pool.xls',
                'Some position have parameter values although there is no ' \
                'pool for them: B4 (reagent_dilution_factor).')
        self._test_invalid_file('unknown_pool.xls',
            'The following molecule design pools are unknown: ' \
            '1 (B2, B3) - 2 (C2, C3)')

    def test_position_types(self):
        self._test_invalid_file('invalid_position_type.xls',
                'The following position types are not allowed in the ISO ' \
                'request layout for this experiment metadata type')
        # uses qPCR as fake experiment scenario
        self._check_error_messages(': untreated (G2, G3).')
        self._test_invalid_file('unknown_position_type.xls',
                'Unable to determine the position type for the following ' \
                'pool IDs: floatings (D2, D3). Allowed position types for ' \
                'this type of experiment are: empty, fixed, floating, ' \
                'library, mock, untransfected')

    def test_inconsistent_iso_data(self):
        exp_msg = 'There are positions in this ISO request layout that lack ' \
                'either an ISO volume or an ISO concentration. If you set a ' \
                'value for one position, you need to set it for all other ' \
                'positions as well (mock, untreated and untransfected ' \
                'positions are excepted).'
        self._test_invalid_file('inconsistent_iso_volume.xls', exp_msg)
        self._test_invalid_file('inconsistent_iso_concentration.xls', exp_msg)

    def test_layout_validity(self):
        self._test_invalid_file('no_controls.xls',
            'There are no fixed positions in this ISO request layout!')
        self._test_invalid_file('more_than_stock_conc.xls',
            'Some concentrations you have ordered are larger than the ' \
            'stock concentration for that molecule type (50000 nM): B2, B3, ' \
            'C2, C3.')

    def test_association_errors(self):
        self._test_invalid_file('association_no_final_conc.xls',
            'If you use floating positions in an 384-well ISO request layout ' \
            'you have to provide final concentration to enable sorting by ' \
            'sectors. Please regard, that the  different concentrations for ' \
            'a molecule design pool must be located in the same rack sector ' \
            'and that the distribution of concentrations must be the same ' \
            'for all quadrants.')
        self._test_invalid_file('association_failure.xls',
            'Error when trying to associated rack sectors! The floating ' \
            'positions in 384-well ISO request layouts must be arranged in ' \
            'rack sectors to enable the use of the CyBio robot during ISO ' \
            'generation. If floating molecule design pools shall occur ' \
            'several times, all occurrences must be located in the same ' \
            'rack sector and that the distribution of concentrations must ' \
            'be the same for all quadrants.')
        self._test_invalid_file('association_several_final_conc.xls',
            'Some ISO concentrations in the layout that are involved in ' \
            'rack sector formation are related to more than one distinct ' \
            'final concentration: ISO conc: 50 uM (final concentrations: ' \
            '1, 5) - ISO conc: 100 uM (final concentrations: 2, 10).')
        self._test_invalid_file('association_several_iso_conc.xls',
            'Some final concentrations in the layout that are involved in ' \
            'rack sector formation are related to more than one distinct ' \
            'ISO concentration: final conc: 5 uM (ISO concentrations: ' \
            '10, 50) - final conc: 10 uM (ISO concentrations: 20, 100).')

    def test_entity_creation_errors(self):
        self._test_invalid_file('label_too_long.xls',
            'The maximum length for plate set labels is 17 characters ' \
            '(obtained: "this_label_is_a_bit_too_long", 28 characters).')
        self._test_invalid_file('invalid_date.xls',
            'Cannot read the delivery date. Please use the following date ' \
            'format: dd.MM.yyyy')
        self._continue_setup('invalid_date_format.xls')
        res = self.tool.get_result()
        self.assert_is_not_none(res)
        self._check_warning_messages(
            'The delivery date has could not be encoded because Excel has ' \
            'delivered an unexpected format. Make sure the cell is formatted ' \
            'as "text" and reload the file or adjust the delivery date ' \
            'manually after upload, please.')


class IsoRequestParserOptiTestCase(_IsoRequestParserTestCase):

    _TEST_FILE_SUBDIRECTORY = 'opti'

    def set_up(self):
        _IsoRequestParserTestCase.set_up(self)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.OPTIMISATION
        self.expected_ir_attrs = dict(
                    comment='Robot-opti parser test',
                    requester=self.user,
                    delivery_date=date(2016, 9, 17),
                    process_job_first=True,
                    number_aliquots=1,
                    label='robot_opt_test')
        # pos_label - pool, pos_type, iso vol, iso conc, final conc, reagent
        # name, reagent df
        self.layout_data = dict(
            b2=[205200, 'fixed', None, 100, 10, 'mix1', 28],
            b3=[205200, 'fixed', None, 100, 10, 'mix1', 28],
            c2=[1056000, 'fixed', None, 100, 10, 'mix1', 28],
            c3=[1056000, 'fixed', None, 100, 10, 'mix1', 28],
            d2=[330001, 'fixed', None, 10000, 10, 'mix2', 28],
            d3=[330001, 'fixed', None, 10000, 10, 'mix2', 28],
            e2=['mock', 'mock', None, None, 'None', 'mix1', 28],
            e3=['untreated', 'untreated', 'None', None, 'None', None, 'None'],
            b5=['md_001', 'floating', None, 100, 10, 'mix1', 28],
            c5=['md_002', 'floating', None, 100, 10, 'mix1', 28],
            d5=['md_003', 'floating', None, 100, 10, 'mix1', 28])
        self.exp_layout_shape = get_96_rack_shape()
        self.num_add_control_tags = 2
        self.num_add_other_tags = 7

    def test_if_result(self):
        self._test_if_result()

    def test_result(self):
        self._check_result()
        self._check_warning_messages('There are untreated or untransfected ' \
            'positions in your ISO request layout! You do not need to mark ' \
            'them here, because the system considers them to be empty and ' \
            'will not transfer them to the experiment cell plates!')

    def test_result_association(self):
        self.VALID_FILE = 'valid_file_association.xls'
        self.exp_layout_shape = get_384_rack_shape()
        del self.layout_data['e3']
        for pos_data in self.layout_data.values():
            pos_data[3] = None
        self.layout_data['e2'][3] = 'None'
        self.exp_association_data_values = dict(
                number_sectors=4,
                associated_sectors=[[0], [1], [2], [3]],
                parent_sectors={0 : None, 1 : None, 2 : None, 3 : None},
                sector_concentrations={0 : 10, 1: 10, 2 : 10, 3 : 10},
                iso_concentrations={0 : None, 1: None, 2 : None, 3 : None},
                sector_volumes={0 : None, 1: None, 2 : None, 3 : None})
        self.num_add_other_tags -= 1
        self._check_result()
        warnings = ' '.join(self.tool.get_messages())
        self.assert_false('There are untreated or untransfected ' \
            'positions in your ISO request layout!' in warnings)


class IsoRequestParserScreenTestCase(_IsoRequestParserTestCase):

    _TEST_FILE_SUBDIRECTORY = 'screen'

    def set_up(self):
        _IsoRequestParserTestCase.set_up(self)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.SCREENING
        self.exp_layout_shape = get_384_rack_shape()
        self.expected_ir_attrs = dict(
                    comment='Standard screen parser test',
                    requester=self.user,
                    delivery_date=date(2016, 9, 17),
                    process_job_first=True,
                    number_aliquots=2,
                    label='scr_test')
        self.exp_association_data_values = dict(
                    number_sectors=4,
                    associated_sectors=[[0], [1], [2], [3]],
                    parent_sectors={0 : None, 1 : None, 2 : None, 3 : None},
                    sector_concentrations={0: 10, 1 : 10, 2 : 10, 3 : 10},
                    sector_volumes={0 : None, 1 : None, 2 : None, 3 : None},
                    iso_concentrations={0 : None, 1 : None, 2 : None, 3 : None})
        # pos_label - pool, pos_type, iso vol, iso conc, final conc, reagent
        # name, reagent df
        self.layout_data = dict(
            b2=[205200, 'fixed', None, None, 10, 'mix1', 140],
            b3=[1056000, 'fixed', None, None, 10, 'mix1', 140],
            b4=[330001, 'fixed', None, None, 10, 'mix1', 140],
            b5=['mock', 'mock', None, 'None', 'None', 'mix1', 140],
            c2=['md_001', 'floating', None, None, 10, 'mix1', 140],
            c3=['md_002', 'floating', None, None, 10, 'mix1', 140],
            c4=['md_003', 'floating', None, None, 10, 'mix1', 140],
            c5=['md_004', 'floating', None, None, 10, 'mix1', 140],
            d2=['md_005', 'floating', None, None, 10, 'mix1', 140],
            d3=['md_006', 'floating', None, None, 10, 'mix1', 140],
            d4=['md_007', 'floating', None, None, 10, 'mix1', 140],
            d5=['md_008', 'floating', None, None, 10, 'mix1', 140],
            e2=[205200, 'fixed', None, None, 10, 'mix1', 140],
            e3=[1056000, 'fixed', None, None, 10, 'mix1', 140],
            e4=[330001, 'fixed', None, None, 10, 'mix1', 140],
            e5=['untransfected', 'untransfected', 'untransfected', 'None',
                'None', 'untransfected', 'untransfected'])
        self.num_add_control_tags = 2
        self.num_add_other_tags = 12

    def _test_and_expect_errors(self, msg=None):
        _IsoRequestParserTestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_iso_volume())

    def test_if_result(self):
        self._test_if_result()

    def test_result(self):
        self._check_result()
        self.assert_is_none(self.tool.get_iso_volume())
        # 96-well layout
        self.VALID_FILE = 'valid_file_96.xls'
        for pos_label, pos_data in self.layout_data.iteritems():
            if not pos_label == 'e5':
                pos_data[2] = 5
        self.exp_association_data_values = None
        self.exp_layout_shape = get_96_rack_shape()
        self._check_result()
        self.assert_equal(self.tool.get_iso_volume(), 5)

    def test_invalid_number_aliquots(self):
        self._test_invalid_file('invalid_number_aliquots.xls',
            'The number of aliquots must be a positive integer (obtained: 2.3)')
        self._test_invalid_file('missing_number_aliquot.xls',
            'Could not find value for the following ISO meta data ' \
            'specifications: number_of_aliquots')


class IsoRequestParserLibraryTestCase(_IsoRequestParserTestCase):

    _TEST_FILE_SUBDIRECTORY = 'library'

    def set_up(self):
        _IsoRequestParserTestCase.set_up(self)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.LIBRARY
        self.exp_layout_shape = get_384_rack_shape()
        self.expected_ir_attrs = dict(
                comment='library screening parser test case',
                requester=self.user,
                delivery_date=date(2016, 9, 17),
                process_job_first=True,
                number_aliquots=1,
                label='default') # no label placeholder of the parser handler
        self.num_add_control_tags = 2
        self.num_add_other_tags = 280 # 276 library + 4 others
        # pos_label - pool, pos_type, iso vol, iso conc, final conc, reagent
        # name, reagent df
        self.layout_data = dict(
                b2=[205200, 'fixed', None, None, 10, 'mix1', 140],
                b9=[205200, 'fixed', None, None, 10, 'mix1', 140],
                d2=[1056000, 'fixed', None, None, 10, 'mix1', 140],
                d9=[1056000, 'fixed', None, None, 10, 'mix1', 140],
                f2=[330001, 'fixed', None, None, 10, 'mix1', 140],
                f9=[330001, 'fixed', None, None, 10, 'mix1', 140],
                h2=['mock', 'mock', None, None, 'mock', 'mix1', 140],
                h9=['untransfected', 'untransfected', None, None,
                    'untransfected', 'untransfected', 'untransfected'])

    def _test_and_expect_errors(self, msg=None):
        _IsoRequestParserTestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_library())
        self.assert_is_none(self.tool.get_final_concentration())
        self.assert_is_none(self.tool.get_reagent_name())
        self.assert_is_none(self.tool.get_reagent_dil_factor())

    def _build_expected_layout(self):
        exp_layout = _IsoRequestParserTestCase._build_expected_layout(self)
        shape = self.exp_layout_shape
        for rack_pos in get_positions_for_shape(shape):
            if rack_pos.column_index in (0, shape.number_columns - 1):
                continue
            if rack_pos.row_index in (0, shape.number_rows - 1):
                continue
            if rack_pos.label in (
                     'B2', 'D2', 'F2', 'H2', 'B9', 'D9', 'F9', 'H9',
                     'B15', 'D15', 'F15', 'H15', 'B21', 'D21', 'F21', 'H21',
                     'I3', 'K3', 'M3', 'O3', 'I10', 'K10', 'M10', 'O10',
                     'I16', 'K16', 'M16', 'O16', 'I22', 'K22', 'M22', 'O22'):
                continue
            tf_pos = TransfectionPosition(
                            rack_pos,
                            molecule_design_pool=LIBRARY_POSITION_TYPE,
                            reagent_name='mix1', reagent_dil_factor=140,
                            iso_volume=None, iso_concentration=None,
                            final_concentration=10
                            )
            exp_layout.add_position(tf_pos)
        return exp_layout

    def test_if_result(self):
        self._test_if_result()

    def test_result(self):
        self._check_result()
        lib = self.tool.get_library()
        self.assert_is_not_none(lib)
        self.assert_true(isinstance(lib, MoleculeDesignLibrary))
        self.assert_equal(lib.label, 'poollib')
        self.assert_equal(self.tool.get_final_concentration(), 10)
        self.assert_equal(self.tool.get_reagent_name(), 'mix1')
        self.assert_equal(self.tool.get_reagent_dil_factor(), 140)

    def test_unknown_library(self):
        self._test_invalid_file('unknown_library.xls',
                                'Unknown library "otherlib"')

    def test_not_library_compliant(self):
        self._test_invalid_file('different_rack_shape.xls',
            'Library "poollib" requires a 16x24 layout. You have provided ' \
            'a 8x12 layout.')
        self._test_invalid_file('no_fixed_positions.xls',
            'There are no fixed positions in this ISO request layout!')
        self._test_invalid_file('missing_library_positions.xls',
            'The following positions are reserved for library samples: ' \
            'C21, E21, G21, J22, L22, N22. You have assigned a different ' \
            'position type to them.')
        self._test_invalid_file('invalid_library_pos.xls',
            'The following positions must not be samples: I3, K3, M3, O3.')


class IsoRequestParserManualTestCase(_IsoRequestParserTestCase):

    _TEST_FILE_SUBDIRECTORY = 'manual'

    def set_up(self):
        _IsoRequestParserTestCase.set_up(self)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.MANUAL
        self.exp_layout_shape = get_96_rack_shape()
        self.expected_ir_attrs = dict(
                    label='man_opt_test',
                    comment='manual opti parser test case',
                    delivery_date=date(2016, 9, 17),
                    number_aliquots=1,
                    requester=self.user,
                    process_job_first=True)
        # pos_label - pool, pos_type, iso vol, iso conc, final conc, reagent
        # name, reagent df
        self.layout_data = dict(
                b2=[205200, 'fixed', 2, 5000, None, None, None],
                b3=[205200, 'fixed', 2, 5000, None, None, None],
                b4=[205200, 'fixed', 1, 10000, None, None, None],
                c2=[1056000, 'fixed', 2, 5000, None, None, None],
                c3=[1056000, 'fixed', 2, 5000, None, None, None],
                c4=[1056000, 'fixed', 1, 10000, None, None, None],
                d2=[330001, 'fixed', 2, 5000, None, None, None],
                d3=[330001, 'fixed', 2, 5000, None, None, None])
        self.num_add_control_tags = 3
        self.num_add_other_tags = 2

    def test_if_result(self):
        self._test_if_result()

    def test_result(self):
        self._check_result()


class IsoRequestParserOrderTestCase(_IsoRequestParserTestCase):

    _TEST_FILE_SUBDIRECTORY = 'order'

    def set_up(self):
        _IsoRequestParserTestCase.set_up(self)
        self.experiment_type_id = EXPERIMENT_SCENARIOS.ORDER_ONLY
        self.exp_layout_shape = get_96_rack_shape()
        # pos_label - pool, pos_type, iso vol, iso conc, final conc, reagent
        # name, reagent df
        self.layout_data = dict(
            b2=[205200, 'fixed', 2, None, None, None, None],
            c2=[1056000, 'fixed', 2, None, None, None, None],
            d2=[330001, 'fixed', 2, None, None, None, None],
            e2=[1068580, 'fixed', 2, None, None, None, None])
        self.expected_ir_attrs = dict(
                        label='order_test',
                        delivery_date=date(2016, 9, 17),
                        number_aliquots=1,
                        process_job_first=True,
                        requester=self.user,
                        comment='order only parser test case')
        self.num_add_control_tags = 1
        self.num_add_other_tags = 2

    def test_if_result(self):
        self._test_if_result()

    def test_result(self):
        self._check_result()

    def test_more_than_one_occurrence(self):
        self._test_invalid_file('more_than_one.xls',
            'In an ISO request without experiment, each molecule design ' \
            'pool may occur only once. The following pools occur several ' \
            'times: 330001, 1056000')
