"""
tests the generic sample transfer excel file parser

AAB
"""
from everest.entities.utils import get_root_aggregate
from thelma.automation.handlers.sampletransfer \
    import GenericSampleTransferPlanParserHandler
from thelma.automation.parsers.sampletransfer \
    import GenericSampleTransferPlanParser
from thelma.automation.semiconstants \
    import get_rack_specs_from_reservoir_specs
from thelma.automation.semiconstants import RACK_SPECS_NAMES
from thelma.automation.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.semiconstants import get_item_status_future
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.interfaces import IRack
from thelma.models.liquidtransfer import PlannedSampleDilution
from thelma.models.liquidtransfer import PlannedSampleTransfer
from thelma.tests.tools.tooltestingutils import ParsingTestCase


class GenericSampleTransferParserTestCase(ParsingTestCase):

    _PARSER_CLS = GenericSampleTransferPlanParser

    def set_up(self):
        ParsingTestCase.set_up(self)
        self.VALID_FILE = 'valid_file.xls'
        self.TEST_FILE_PATH = 'thelma:tests/parsers/sampletransfer/'
        self.allow_rack_creation = True
        self.barcodes = {'09999999' : 'stock rack',
                         '09999998' : 'plate 384 std',
                         '09999990' : 'plate 96 deep'}
        self.label = 'alpha'
        transfers1 = [('B2', 'B2', 3.5), ('B2', 'B3', 3.5),
                      ('B3', 'B4', 3.5), ('B3', 'B5', 3.5),
                      ('D2', 'D2', 6), ('F2', 'F2', 6),
                      ('B5', 'B7', 2), ('C5', 'B7', 2), ('D5', 'B7', 2)]
        transfers23 = [('B2', 5), ('B3', 5), ('B4', 5),
                      ('B5', 5), ('B7', 5), ('D2', 5),
                      ('D3', 5), ('F2', 5), ('F3', 5)]
        self.diluents = {2 : 'buffer', 3 : 'medium'}
        transfers4 = [('B2', 'B2', 2), ('B3', 'B3', 2),
                      ('B2', 'B11', 2), ('B3', 'B12', 2),
                      ('B2', 'J2', 2), ('B3', 'J3', 2),
                      ('B2', 'J11', 2), ('B3', 'J12', 2),
                      ('B4', 'C2', 2), ('B5', 'C3', 2),
                      ('B4', 'C11', 2), ('B5', 'C12', 2),
                      ('B4', 'K2', 2), ('B5', 'K3', 2),
                      ('B4', 'K11', 2), ('B5', 'K12', 2),
                      ('D2', 'D2', 2), ('D3', 'D3', 2),
                      ('D2', 'D11', 2), ('D3', 'D12', 2),
                      ('F2', 'L2', 2), ('F3', 'L3', 2),
                      ('F2', 'L11', 2), ('F3', 'L12', 2),
                      ('B7', 'B5', 2), ('B7', 'B14', 2),
                      ('B7', 'J5', 2), ('B7', 'J14', 2)]
        self.transfers = {1 : transfers1, 2 : transfers23,
                          3 : transfers23, 4 : transfers4}
        # rack identifier - is rack, barcode, specs name, src wls, trg wls
        self.rack_data = {
                'S1' : [True, '09999999', 'stock rack', [1], []],
                'R1' : [False, 'buffer_mod', 'quarter mod', [2], []],
                'R2' : [False, 'R2', 'falcon tube', [3], []],
                'Int' : [True, '09999990', 'plate 96 deep', [4], [1, 2, 3]],
                'T1' : [True, None, 'plate 384 std', [], [4]],
                'T2' : [True, '09999998', 'plate 384 std', [], [4]]}

    def tear_down(self):
        ParsingTestCase.tear_down(self)
        del self.allow_rack_creation
        del self.barcodes
        del self.label
        del self.diluents
        del self.transfers
        del self.rack_data

    def _create_tool(self):
        self.tool = \
            GenericSampleTransferPlanParserHandler(self.stream,
                                                   allow_rack_creation=
                                                    self.allow_rack_creation)

    def _continue_setup(self, file_name=None):
        ParsingTestCase._continue_setup(self, file_name=file_name)
        self.__create_racks()

    def __create_racks(self):
        rack_agg = get_root_aggregate(IRack)
        for barcode, reservoir_spec in self.barcodes.iteritems():
            if reservoir_spec == RESERVOIR_SPECS_NAMES.STOCK_RACK:
                rack_spec = RACK_SPECS_NAMES.from_name(
                                                RACK_SPECS_NAMES.STOCK_RACK)
            else:
                rack_spec = get_rack_specs_from_reservoir_specs(reservoir_spec)
            rack = rack_spec.create_rack(label=barcode, barcode=barcode,
                                         status=get_item_status_future())
            rack_agg.add(rack)

    def _test_and_expect_errors(self, msg=None):
        ParsingTestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_racks_and_reservoir_items())

    def test_if_result(self):
        self._test_if_result()

    def test_result(self):
        self._continue_setup()
        ws = self.tool.get_result()
        self.assert_is_not_none(ws)
        self.assert_equal(len(ws), 4)
        # check planned transfers
        for worklist in ws:
            self.assert_true(worklist.label.startswith(self.label))
            step_number = self.__get_wl_numbers([worklist])[0]
            is_dilution = self.diluents.has_key(step_number)
            pts = []
            for pt in worklist.planned_liquid_transfers:
                volume = pt.volume * VOLUME_CONVERSION_FACTOR
                if is_dilution:
                    self.assert_equal(pt.__class__, PlannedSampleDilution)
                    pt_data = (pt.target_position.label, volume)
                else:
                    self.assert_equal(pt.__class__, PlannedSampleTransfer)
                    pt_data = (pt.source_position.label,
                               pt.target_position.label, volume)
                pts.append(pt_data)
            transfer_data = self.transfers[step_number]
            self.assert_equal(len(transfer_data), len(pts))
            for transfer_item in transfer_data:
                self.assert_true(transfer_item in pts)
        rors = self.tool.get_racks_and_reservoir_items()
        self.assert_equal(len(rors), len(self.rack_data))
        for ror in rors:
            # rack identifier - is rack, barcode, specs name, src wls, trg wls
            item_data = self.rack_data[ror.identifier]
            self.assert_equal(ror.is_rack, item_data[0])
            if not ror.is_rack:
                self.assert_is_none(ror.rack)
            else:
                self.assert_is_not_none(ror.rack)
            self.assert_equal(ror.barcode, item_data[1])
            self.assert_equal(ror.reservoir_specs.name, item_data[2])
            src_wls = self.__get_wl_numbers(ror.get_worklists_for_source())
            self.assert_equal(src_wls, item_data[3])
            trg_wls = self.__get_wl_numbers(ror.get_worklists_for_target())
            self.assert_equal(trg_wls, item_data[4])

    def __get_wl_numbers(self, worklists):
        numbers = []
        for worklist in worklists:
            number = int(worklist.label.split('_')[1])
            numbers.append(number)
        return sorted(numbers)

    def test_no_rack_barcode(self):
        self.allow_rack_creation = False
        self._continue_setup()
        self._test_and_expect_errors('When printing or executing worklists ' \
            'directly all used racks must already be stored in the DB ' \
            'and be specified by barcode. Rack "T1" does not have a barcode.')

    def test_no_sheet(self):
        self._test_invalid_file('no_sheet.xls',
                                'There is no sheet called "Sample Transfer"')

    def test_no_worklist_label_marker(self):
        self._test_invalid_file('no_wl_marker.xls',
                'Unable to find label section! The section is marked with ' \
                'the keyword "label" in column A!')

    def test_invalid_worklist_label(self):
        self._test_invalid_file('invalid_wl_label.xls',
                'The worklist prefix must be at least 2 characters long!')

    def test_no_racks_and_reservoirs_marker(self):
        self._test_invalid_file('no_ror_marker.xls',
                'Unable to find rack and reservoir section. The section is ' \
                'marked by the keyword "racks_and_reservoirs" in column A!')

    def test_duplicate_rack_definition_column(self):
        self._test_invalid_file('duplicate_rack_def_column.xls',
                'cell C4: Duplicate barcode definition in the racks and ' \
                'reservoir section!')

    def test_missing_rack_definition_column(self):
        self._test_invalid_file('missing_rack_def_column.xls',
                'Unable to find the following definitions in the racks and ' \
                'reservoir section: specs.')

    def test_duplicate_rack_identifier(self):
        self._test_invalid_file('duplicate_rack_identifier.xls',
                                'Duplicate rack or reservoir identifier "T"')

    def test_no_racks_and_reservoirs(self):
        self._test_invalid_file('no_racks.xls',
                                'There are no racks and reservoirs defined!')

    def test_invalid_step_marker(self):
        self._test_invalid_file('invalid_step_marker.xls',
                'cell A26: Invalid step marker "step_2_(dilution)"')

    def test_duplicate_step_number(self):
        self._test_invalid_file('duplicate_step_number.xls',
                                'Duplicate step number 1!')

    def test_missing_tag_definition(self):
        self._test_invalid_file('missing_tag_definition.xls',
                'There should be a factor definition in row 27 (step 2)')

    def test_no_codes(self):
        self._test_invalid_file('no_codes.xls',
                                'cell B28: There are no codes for step 2')

    def test_invalid_tag_definition(self):
        self._test_invalid_file('invalid_tag_definition.xls',
                                'cell A28: Invalid factor definition!')

    def test_invalid_default_volume(self):
        self._test_invalid_file('invalid_default_volume.xls',
                'cell B29: Invalid default transfer volume for step 2: "-6.0"')

    def test_default_and_individual_volume(self):
        self._test_invalid_file('default_and_ind_volume.xls',
                'There is a default volume and individual volumes for step 2.')

    def test_missing_volume(self):
        self._test_invalid_file('missing_volume.xls',
                                'There are no volumes for step 3!')

    def test_invalid_tag_volume(self):
        self._test_invalid_file('invalid_tag_volume.xls',
                'The transfer volume must be a positive number. The ' \
                'following transfers have invalid numbers: a (step 4, code 1b)')

    def test_duplicate_code(self):
        self._test_invalid_file('duplicate_code.xls',
                                'Duplicate code "1a" for step 4')

    def test_invalid_rack_shape(self):
        self._test_invalid_file('invalid_shape.xls',
                                'cell H27: Invalid layout block shape (1x3)')

    def test_missing_layout_specifier(self):
        self._test_invalid_file('missing_layout_specifier.xls',
                                'cell V26: There is a rack specifier missing!')

    def test_invalid_rack_specifier_type(self):
        self._test_invalid_file('invalid_rack_specifier_type.xls',
                                'cell V26: Invalid rack specifier "Target Int"')

    def test_invalid_rack_specifier_role(self):
        self._test_invalid_file('invalid_rack_specifier_role.xls',
                                'cell V26: Invalid rack specifier "Target Int"')

    def test_invalid_rack_specifier_number(self):
        self._test_invalid_file('invalid_rack_specifier_number.xls',
                                'cell V26: Invalid rack specifier "3"')

    def test_unknown_role(self):
        self._test_invalid_file('unknown_role.xls',
                'cell V26: Unable to determine role for this layout! ' \
                'You have used "Destination"')

    def test_duplicate_role(self):
        self._test_invalid_file('duplicate_role.xls',
                                'There are several source layouts for step 2!')

    def test_unknown_rack_identifier(self):
        self._test_invalid_file('unknown_rack_identifier.xls',
                        'cell V26: Unknown rack identifier "Intermediate"')

    def test_no_rack_identifiers(self):
        self._test_invalid_file('no_rack_identifiers.xls',
                'There are no rack tokens in this layout specifier!')

    def test_wrong_alignment(self):
        self._test_invalid_file('wrong_alignment.xls',
                                'Please check the alignment of your layouts!')

    def test_unknown_code(self):
        self._test_invalid_file('unknown_code.xls',
                'Tag value (level) code "b" not found for factor "Diluent_3"')

    def test_no_layouts(self):
        self._test_invalid_file('no_layouts.xls',
                        'Could not find a layout definition on this sheet')

    def test_multiple_positions(self):
        self._test_invalid_file('multiple_positions.xls',
                        'You must not have multiple source AND target ' \
                        'positions for a code')
        self._check_error_messages('violate this rule: b (step 2).')

    def test_missing_positions(self):
        self._test_invalid_file('missing_positions.xls',
                    'There are no source positions for transfer b in step 2!')

    def test_unknown_specs(self):
        self._test_invalid_file('unknown_specs.xls',
                    'Error when trying to fetch reservoir specs for rack ' \
                    '"R2": Unknown entity identifier "falcon".')

    def test_unknown_rack(self):
        self._test_invalid_file('unknown_rack.xls',
                                'Could not find rack "09999996" in the DB!')

    def test_unknown_rack_specs(self):
        self._test_invalid_file('unknown_rack_specs.xls',
                'Error when trying to determine reservoir specs for rack ' \
                '"02499118" (rack specs "ABI_RTPCR"): Unsupported rack ' \
                'spec "ABI_RTPCR".')

    def test_mismatching_rack_specs(self):
        self._continue_setup('mismatching_rack_specs.xls')
        result = self.tool.get_result()
        self.assert_is_not_none(result)
        self._check_warning_messages('You specified a wrong reservoir spec ' \
                    'for rack "09999998" ("plate 96 std" instead of "plate ' \
                    '384 std"). Will use spec "plate 384 std"')

    def test_mismatching_shape(self):
        self._test_invalid_file('mismatching_shape.xls',
                'The rack shape for layout at V53 (8x12) does not match the ' \
                'rack shape for rack "T2" (16x24)')

    def test_target_reservoir(self):
        self._test_invalid_file('target_reservoir.xls',
                'The target for step 2 is a reservoirs. Reservoirs may only ' \
                'serve as sources!')

    def test_missing_diluent(self):
        self._test_invalid_file('missing_diluent.xls',
                'A diluent must be at least 2 characters long! Change ' \
                'the diluent for step 2 code b, please')

    def test_too_long_rack_label(self):
        self._continue_setup('too_long_rack_label.xls')
        ws = self.tool.get_result()
        self.assert_is_not_none(ws)
        self._check_warning_messages('The label that has been generated for ' \
            'the new plate "this_rack_label_is_much_tool_long_and_invalid" ' \
            '("alpha_this_rack_label_is_much_tool_long_and_invalid") is ' \
            'longer than 20 characters (51 characters)')
