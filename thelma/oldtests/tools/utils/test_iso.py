"""
Tests of classes related to ISO-handling.

AAB
"""
from thelma.tools.semiconstants import get_rack_position_from_label
from thelma.tools.utils.iso import IsoRequestAssociationData
from thelma.tools.utils.iso import IsoRequestLayout
from thelma.tools.utils.iso import IsoRequestLayoutConverter
from thelma.tools.utils.iso import IsoRequestParameters
from thelma.tools.utils.iso import IsoRequestPosition
from thelma.tools.utils.iso import IsoRequestSectorAssociator
from thelma.tools.utils.iso import IsoRequestValueDeterminer
from thelma.tools.utils.layouts import LIBRARY_POSITION_TYPE
from thelma.tools.utils.layouts import UNTREATED_POSITION_TYPE
from thelma.entities.tagging import Tag
from thelma.oldtests.tools.utils.utils import ConverterTestCase
from thelma.oldtests.tools.utils.utils import MoleculeDesignPoolBaseTestCase
from thelma.oldtests.tools.utils.utils import RackSectorTestCase


class IsoRequestClassesBaseTestCase(MoleculeDesignPoolBaseTestCase):

    POS_CLS = IsoRequestPosition
    LAYOUT_CLS = IsoRequestLayout

    _ISO_VOLUME_TAGS = {
            'a1' : Tag('iso_request', 'iso_volume', '5'),
            'b1' : Tag('iso_request', 'iso_volume', '10'),
            'c1' : Tag('iso_request', 'iso_volume', '10'),
            'd1' : Tag('iso_request', 'iso_volume', '10'),
            'e1' : Tag('iso_request', 'iso_volume', 'untreated'),
            'f1' : Tag('iso_request', 'iso_volume', 'None')}
    _ISO_CONCENTRATION_TAGS = {
            'a1' : Tag('iso_request', 'iso_concentration', '30'),
            'b1' : Tag('iso_request', 'iso_concentration', '45'),
            'c1' : Tag('iso_request', 'iso_concentration', 'mock'),
            'd1' : Tag('iso_request', 'iso_concentration', '45'),
            'e1' : Tag('iso_request', 'iso_concentration', 'None'),
            'f1' : Tag('iso_request', 'iso_concentration', 'untransfected')}

    def set_up(self):
        MoleculeDesignPoolBaseTestCase.set_up(self)
        # the pos data is extended byiso conc, iso vol
        self.pos_data['a1'].extend([30, 5])
        self.pos_data['b1'].extend([45, 10])
        self.pos_data['c1'].extend(['mock', 10])
        self.pos_data['d1'].extend([45, 10])
        self.pos_data['e1'].extend(['None', 'untreated'])
        self.pos_data['f1'].extend(['untransfected', 'None'])
        self.pos_data['g1'].extend([None, None])

    def _get_init_data(self, pos_label):
        kw = MoleculeDesignPoolBaseTestCase._get_init_data(self, pos_label)
        pos_data = self.pos_data[pos_label]
        kw['iso_concentration'] = pos_data[2]
        kw['iso_volume'] = pos_data[3]
        return kw

    def _get_tags(self, pos_label):
        tags = MoleculeDesignPoolBaseTestCase._get_tags(self, pos_label)
        self._add_optional_tag(tags, self._ISO_VOLUME_TAGS, pos_label)
        self._add_optional_tag(tags, self._ISO_CONCENTRATION_TAGS, pos_label)
        return tags


class IsoRequestParametersTestCase(IsoRequestClassesBaseTestCase):

    def test_is_valid_mock_value(self):
        # iso concentration
        m = {'mock' : True, 'MOCK' : True, None : True, 'None' : True,
             'fixed' : False, 'empty' : False, 'untreated' : False,
             50 : False}
        parameter = IsoRequestParameters.ISO_CONCENTRATION
        for val, exp_res in m.iteritems():
            res = IsoRequestParameters.is_valid_mock_value(val, parameter)
            self.assert_equal(res, exp_res)
        # iso volume
        m = {'mock' : False, 'MOCK' : False, None : True, 'None' : False,
             'fixed' : False, 'empty' : False, 50 : True}
        parameter = IsoRequestParameters.ISO_VOLUME
        for val, exp_res in m.iteritems():
            res = IsoRequestParameters.is_valid_mock_value(val, parameter)
            self.assert_equal(res, exp_res)


class IsoRequestPositionTestCase(IsoRequestClassesBaseTestCase):

    def test_init(self):
        self._test_position_init()

    def test_empty_init_failures(self):
        kw = self._get_init_data('g1')
        ep = self._get_position('g1', attrs=kw)
        self.assert_is_not_none(ep)
        kw['iso_concentration'] = 'None'
        self._expect_error(ValueError, self.POS_CLS,
                   'The ISO concentration must be None for empty ' \
                   'positions', **kw)
        kw['iso_concentration'] = None
        kw['iso_volume'] = 5
        self._expect_error(ValueError, self.POS_CLS,
                   'The ISO volume must be None for empty positions ' \
                   '(obtained: 5.0)!', **kw)

    def test_untransfected_init_failures(self):
        kw = self._get_init_data('f1')
        ip = self._get_position('f1', attrs=kw)
        self.assert_is_not_none(ip)
        kw['iso_concentration'] = 5
        self._expect_error(ValueError, self.POS_CLS,
                'The value "5.0" is invalid for the ISO concentration of ' \
                'untransfected positions. Allowed values are: (None, ' \
                '\'UNTREATED\', \'NONE\', \'UNTRANSFECTED\')', **kw)
        kw['iso_concentration'] = 'untransfected'
        kw['iso_volume'] = 5
        self._expect_error(ValueError, self.POS_CLS,
                'The value "5.0" is invalid for the ISO volume of ' \
                'untransfected positions. Allowed values are: (None, ' \
                '\'UNTREATED\', \'NONE\', \'UNTRANSFECTED\')', **kw)

    def test_untreated_init_failures(self):
        kw = self._get_init_data('e1')
        ip = self._get_position('e1', attrs=kw)
        self.assert_is_not_none(ip)
        kw['iso_concentration'] = 5
        self._expect_error(ValueError, self.POS_CLS,
                'The value "5.0" is invalid for the ISO concentration of ' \
                'untreated positions. Allowed values are: (None, ' \
                '\'UNTREATED\', \'NONE\', \'UNTRANSFECTED\')', **kw)
        kw['iso_concentration'] = 'untreated'
        kw['iso_volume'] = 5
        self._expect_error(ValueError, self.POS_CLS,
                'The value "5.0" is invalid for the ISO volume of ' \
                'untreated positions. Allowed values are: (None, ' \
                '\'UNTREATED\', \'NONE\', \'UNTRANSFECTED\')', **kw)

    def test_library_init_failure(self):
        kw = self._get_init_data('d1')
        ip = self._get_position('d1', attrs=kw)
        self.assert_is_not_none(ip)
        kw['iso_concentration'] = LIBRARY_POSITION_TYPE
        self._expect_error(ValueError, self.POS_CLS,
                   'The ISO concentration must be a positive number ' \
                   '(obtained: library).', **kw)
        kw['iso_concentration'] = None
        kw['iso_volume'] = LIBRARY_POSITION_TYPE
        self._expect_error(ValueError, self.POS_CLS,
                    'The ISO volume must be a positive number ' \
                    '(obtained: library).', **kw)

    def test_mock_init_failure(self):
        kw = self._get_init_data('c1')
        ip = self._get_position('d1', attrs=kw)
        self.assert_is_not_none(ip)
        kw['iso_concentration'] = 50
        self._expect_error(ValueError, self.POS_CLS,
            'The value "50.0" is invalid for the ISO concentration of ' \
            'mock positions. Allowed values are: (None, \'MOCK\', \'NONE\')',
            **kw)
        kw['iso_concentration'] = 'None'
        kw['iso_volume'] = -2
        self._expect_error(ValueError, self.POS_CLS,
            'The ISO volume must be a positive number (obtained: -2).', **kw)

    def test_floating_init_failure(self):
        kw = self._get_init_data('b1')
        ip = self._get_position('b1', attrs=kw)
        self.assert_is_not_none(ip)
        kw['iso_concentration'] = -4
        self._expect_error(ValueError, self.POS_CLS,
                'The ISO concentration must be a positive number ' \
                '(obtained: -4).', **kw)
        kw['iso_concentration'] = None
        kw['iso_volume'] = -2
        self._expect_error(ValueError, self.POS_CLS,
               'The ISO volume must be a positive number ' \
               '(obtained: -2).', **kw)

    def test_fixed_init_failure(self):
        kw = self._get_init_data('a1')
        ip = self._get_position('a1', attrs=kw)
        self.assert_is_not_none(ip)
        kw['iso_concentration'] = -4
        self._expect_error(ValueError, self.POS_CLS,
                'The ISO concentration must be a positive number ' \
                '(obtained: -4).', **kw)
        kw['iso_concentration'] = None
        kw['iso_volume'] = -4
        self._expect_error(ValueError, self.POS_CLS,
               'The ISO volume must be a positive number ' \
               '(obtained: -4).', **kw)

    def test_equality(self):
        self._test_position_equality(dict(iso_concentration=70, iso_volume=100),
                                     dict())

    def test_position_get_tag_set(self):
        self._test_position_get_tag_set()


class IsoRequestLayoutTestCase(IsoRequestClassesBaseTestCase):

    def test_init(self):
        self._test_layout_init()

    def test_has_consistent_volumes_and_concentrations(self):
        irl = self._create_test_layout()
        self.assert_true(irl.has_consistent_volumes_and_concentrations())
        fixed_irp = irl.get_working_position(get_rack_position_from_label('a1'))
        mock_irp = irl.get_working_position(get_rack_position_from_label('c1'))
        unt_irp = irl.get_working_position(get_rack_position_from_label('e1'))
        # check volume
        fixed_irp.iso_volume = None
        self.assert_false(irl.has_consistent_volumes_and_concentrations())
        fixed_irp.iso_volume = 1
        mock_irp.iso_volume = None
        self.assert_false(irl.has_consistent_volumes_and_concentrations())
        mock_irp.iso_volume = 1
        unt_irp.iso_volume = None
        self.assert_true(irl.has_consistent_volumes_and_concentrations())
        unt_irp.iso_volume = 'untreated'
        # check concentration
        fixed_irp.iso_concentration = None
        self.assert_false(irl.has_consistent_volumes_and_concentrations())
        fixed_irp.iso_concentration = 1
        mock_irp.iso_concentration = None
        self.assert_true(irl.has_consistent_volumes_and_concentrations())
        mock_irp.iso_concentration = 'mock'
        unt_irp.iso_concentration = None
        self.assert_true(irl.has_consistent_volumes_and_concentrations())


class IsoRequestLayoutConverterTestCase(ConverterTestCase,
                                        IsoRequestClassesBaseTestCase):

    PARAMETER_SET = IsoRequestParameters
    POS_CLS = IsoRequestPosition
    LAYOUT_CLS = IsoRequestLayout
    CONVERTER_CLS = IsoRequestLayoutConverter

    def set_up(self):
        ConverterTestCase.set_up(self)
        self.pos_set_data = {1 : ['a1', 'a2'], 2 : ['b1'], 3 : ['c1'],
                             4 : ['d1'], 5 : ['e1'], 6 : ['f1'],
                             7 : ['g1'], 8 : ['a1', 'b1', 'c1']}
        # Do not alter tag attributes but overwrite the index!
        self.tag_data = {
            1 : [self.TYPE_TAGS['fixed'], self.POOL_TAGS['fixed'],
                 self._ISO_VOLUME_TAGS['a1'],
                 self._ISO_CONCENTRATION_TAGS['a1']],
            2 : [self.TYPE_TAGS['floating'], self.POOL_TAGS['floating'],
                 self._ISO_VOLUME_TAGS['b1'],
                 self._ISO_CONCENTRATION_TAGS['b1']],
            3 : [self.TYPE_TAGS['mock'], self.POOL_TAGS['mock'],
                 self._ISO_VOLUME_TAGS['c1'],
                 self._ISO_CONCENTRATION_TAGS['c1']],
            4 : [self.TYPE_TAGS['library'], self.POOL_TAGS['library'],
                 self._ISO_VOLUME_TAGS['d1'],
                 self._ISO_CONCENTRATION_TAGS['d1']],
            5 : [self.TYPE_TAGS['untreated'], self.POOL_TAGS['untreated'],
                 self._ISO_VOLUME_TAGS['e1'],
                 self._ISO_CONCENTRATION_TAGS['e1']],
            6 : [self.TYPE_TAGS['untransfected'],
                 self.POOL_TAGS['untransfected'],
                 self._ISO_VOLUME_TAGS['f1'],
                 self._ISO_CONCENTRATION_TAGS['f1']],
            7 : [self.TYPE_TAGS['empty']],
            8 : [Tag('some', 'other', 'data')]}

    def test_result(self):
        self._test_result()

    def _get_all_positions(self):
        positions = []
        for i in range(4):
            positions.extend(self.pos_set_data[i + 1])
        return positions

    def _get_all_tags(self):
        tags = []
        for i in range(4):
            tags.extend(self.tag_data[i + 1])
        tags = set(tags)
        return list(tags)

    def _test_tag_for_position(self, layout):
        rack_pos = get_rack_position_from_label('a2')
        exp_tags = self.tag_data[1]
        tag_set = layout.get_tags_for_position(rack_pos)
        self._compare_tag_sets(exp_tags, tag_set)
        rack_pos_empty = get_rack_position_from_label('f1')
        tag_set_empty = layout.get_tags_for_position(rack_pos_empty)
        self.assert_equal(len(tag_set_empty), 0)

    def _test_position_for_tag(self, layout):
        positions = self.pos_set_data[1]
        pos_set = layout.get_positions_for_tag(self.TYPE_TAGS['fixed'])
        self._compare_pos_sets(positions, pos_set)
        pos_set_empty = layout.get_positions_for_tag(
                                                    self.TYPE_TAGS['untreated'])
        self.assert_equal(len(pos_set_empty), 0)

    def test_invalid_iso_volume(self):
        inv_tag = Tag(self.PARAMETER_SET.DOMAIN, self.PARAMETER_SET.ISO_VOLUME,
                      '-1')
        self.tag_data[1] = [self.TYPE_TAGS['fixed'], inv_tag,
            self.POOL_TAGS['fixed'], self._ISO_CONCENTRATION_TAGS['a1']]
        self._continue_setup()
        self._test_and_expect_errors('Some position have invalid ISO ' \
            'volumes. The volume must be a positive number. Details: A1, A2')

    def test_missing_iso_volume(self):
        self.tag_data[1] = [self.TYPE_TAGS['fixed'], self.POOL_TAGS['fixed'],
                            self._ISO_CONCENTRATION_TAGS['a1']]
        self._continue_setup()
        self._test_and_expect_errors('Some position do not have an ISO ' \
                                     'volume specifications: A1, A2')

    def test_invalid_iso_concentration(self):
        inv_tag = Tag(self.PARAMETER_SET.DOMAIN,
                      self.PARAMETER_SET.ISO_CONCENTRATION, '-2')
        self.tag_data[1] = [self.TYPE_TAGS['fixed'], inv_tag,
            self.POOL_TAGS['fixed'], self._ISO_VOLUME_TAGS['a1']]
        self._continue_setup()
        self._test_and_expect_errors('Some position have invalid ISO ' \
             'concentrations. The concentration must a positive number. ' \
             'Details: A1, A2')

    def test_missing_iso_concentration(self):
        self.tag_data[1] = [self.TYPE_TAGS['fixed'], self.POOL_TAGS['fixed'],
                            self._ISO_VOLUME_TAGS['a1']]
        self._continue_setup()
        self._test_and_expect_errors('Some positions do not have an ISO ' \
                                     'concentration specification: A1, A2')


class _IsoRequestRackSectorToolTestCase(RackSectorTestCase):

    LAYOUT_CLS = IsoRequestLayout

    def set_up(self):
        RackSectorTestCase.set_up(self)
        self.regard_controls = True
        self.attribute_name = 'iso_concentration'

    def tear_down(self):
        RackSectorTestCase.tear_down(self)
        del self.regard_controls

    def _fill_layout(self):
        for pos_label, pos_data in self.position_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            pool_id = pos_data[1]
            if pool_id is None or pool_id == UNTREATED_POSITION_TYPE:
                ir_pos = IsoRequestPosition.create_empty_position(rack_pos)
                self.layout.add_position(ir_pos)
                continue
            iso_conc = pos_data[2]
            pool = self._get_pool(pool_id)
            ir_pos = IsoRequestPosition(rack_position=rack_pos,
                                         molecule_design_pool=pool,
                                         iso_concentration=iso_conc,
                                         iso_volume=((pos_data[0] + 1) * 2))
            self.layout.add_position(ir_pos)

    def _test_invalid_regard_controls(self):
        self.regard_controls = None
        self._test_and_expect_errors('The "regard controls" flag must be a ' \
                                     'bool')
        self.regard_controls = True

    def _adjust_pos_data_for_regard_control_test(self):
        self.position_data = self._get_case_data(3)
        self.position_data['C6'] = [1, 5, 70]

    def _create_value_determiner(self):
        self.tool = IsoRequestValueDeterminer(self.layout,
                                              self.attribute_name,
                                              self.number_sectors,
                                              self.regard_controls)

    def _create_sector_associator(self):
        self.tool = IsoRequestSectorAssociator(self.layout,
                                               self.regard_controls,
                                               number_sectors=
                                                    self.number_sectors)

    def _create_association_data(self):
        return IsoRequestAssociationData(self.layout,
                                         self.tool,
                                         self.regard_controls)

    def _adjust_96_layout_for_association_data_test(self):
        iso_vol = 10
        for pool_pos in self.layout.working_positions():
            if not pool_pos.is_empty:
                pool_pos.iso_volume = iso_vol

    def _get_expected_sector_volumes(self):
        if self.current_case_num == 1:
            # different pools and concentration, 1 empty
            raise AssertionError('The association for case %i should always ' \
                                 'fail!' % (self.current_case_num))
        elif self.current_case_num == 2:
            # different pools, equal concentrations, 1 empty
            return {0 : 2, 1 : 4, 2 : 6}
        elif self.current_case_num == 3:
            # 2 x 2 association, different concentrations
            return {0 : 2, 1 : 4, 2 : 6, 3 : 8}
        else: # 2 x 2 association, all equal concentrations
            return {0 : 2, 1 : 4, 2 : 6, 3 : 8}


class IsoRequestValueDetermineTestCase(_IsoRequestRackSectorToolTestCase):

    def _create_tool(self):
        self._create_value_determiner()

    def test_result(self):
        self._test_value_determiner()

    def test_regard_controls(self):
        self._adjust_pos_data_for_regard_control_test()
        self._continue_setup()
        self._test_and_expect_errors('There is more than one value for ' \
                 'sector 2! Attribute: iso_concentration. Values: 10, 70')
        self.regard_controls = False
        self._create_tool()
        exp_map = self._get_expected_sector_concentrations(3)
        self._check_value_determiner_run(exp_map)

    def test_invalid_input_values(self):
        self._continue_setup()
        self._test_invalid_layout()
        self._test_invalid_number_sectors()
        self._test_invalid_regard_controls()
        self._test_invalid_attribute_name()

    def test_unknown_attribute_name(self):
        self._test_value_determine_unknown_attribute_name()

    def test_more_than_one_value(self):
        self._adjust_pos_data_for_regard_control_test()
        self._continue_setup()
        self._test_and_expect_errors('There is more than one value for ' \
                 'sector 2! Attribute: iso_concentration. Values: 10, 70')


class IsoRequestRackSectorAssociatorTestCase(_IsoRequestRackSectorToolTestCase):

    def _create_tool(self):
        self._create_sector_associator()

    def test_result(self):
        self._test_sector_associator()

    def test_regard_controls(self):
        self._adjust_pos_data_for_regard_control_test()
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to determine rack ' \
                                     'sector concentrations.')
        self.regard_controls = False
        self._create_tool()
        exp_res = self._get_expected_associated_sectors()
        self._check_sector_associator_run(exp_res)

    def test_invalid_input_values(self):
        self._continue_setup()
        self._test_invalid_layout()
        self._test_invalid_regard_controls()
        self._test_invalid_number_sectors()

    def test_value_determiner_failure(self):
        self._adjust_pos_data_for_regard_control_test()
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to determine rack ' \
                                     'sector concentrations.')

    def test_inconsistent_quadrants(self):
        exp_msg = 'The molecule design pools in the different quadrants are ' \
            'not consistent. Found associated pools: 0.1.2 ([\'E5\', \'E6\', ' \
            '\'F5\']) - 0.2 ([\'C3\', \'D3\'], [\'C5\', \'D5\'], [\'E3\', ' \
            '\'F3\']) - 1.3 ([\'C6\', \'D6\'], [\'E4\', \'F4\']).'
        self._test_associator_inconsistent_quadrants(exp_msg)

    def test_different_set_lengths(self):
        exp_msg = 'The sets of molecule design pools in ' \
            'a quadrant have different lengths: 0.1.2.3 ([\'E5\', \'E6\', ' \
            '\'F5\', \'F6\']) - 0.2 ([\'C3\', \'D3\'], [\'C5\', \'D5\'], ' \
            '[\'E3\', \'F3\'], [\'E7\', \'F7\']) - 1 ([\'C6\'], [\'E4\']) - ' \
            '1.3 ([\'E8\', \'F8\']) - 3 ([\'D6\'], [\'F4\'])'
        self._test_associator_different_set_lengths(exp_msg)

    def test_different_concentration_combinations(self):
        self._test_different_concentration_combinations()


class IsoRequestAssociationDataTestCase(_IsoRequestRackSectorToolTestCase):

    def test_result_384(self):
        self._test_association_data_384()

    def _check_association_data_384(self):
        ad = _IsoRequestRackSectorToolTestCase._check_association_data_384(
                                                                     self)
        if not ad is None:
            exp_volumes = self._get_expected_sector_volumes()
            self.assert_equal(ad.sector_volumes, exp_volumes)

    def test_result_96(self):
        self._test_assocation_data_96()
        for pool_pos in self.layout.working_positions():
            if pool_pos.is_empty: continue
            pool_pos.iso_volume = (2 * pool_pos.iso_volume)
            break
        self._expect_error(ValueError, self._create_association_data,
                           'Error when trying to determine sector volumes.')

    def _check_association_data_96(self):
        ad = _IsoRequestRackSectorToolTestCase._check_association_data_96(self)
        if not ad is None:
            self.assert_equal({0 : 10}, ad.sector_volumes)

    def test_regard_controls(self):
        self._adjust_pos_data_for_regard_control_test()
        self._continue_setup()
        self._expect_error(ValueError, self._create_association_data,
                           'Error when trying to find rack sector association.')
        self.regard_controls = False
        self._check_association_data_384()

    def test_failure(self):
        self._adjust_pos_data_for_regard_control_test()
        self._continue_setup()
        self._expect_error(
                    ValueError, self._create_association_data,
                    'Error when trying to find rack sector association.')

    def test_find(self):
        self._continue_setup()
        ad, regard_controls = IsoRequestAssociationData.find(self.layout,
                                                             self.tool)
        self.assert_is_not_none(ad)
        self.assert_true(regard_controls)
        self._adjust_pos_data_for_regard_control_test()
        self._continue_setup()
        ad, regard_controls = IsoRequestAssociationData.find(self.layout,
                                                             self.tool)
        self.assert_is_not_none(ad)
        self.assert_false(regard_controls)
        rack_pos = get_rack_position_from_label('E3')
        ir_pos = self.layout.get_working_position(rack_pos)
        ir_pos.iso_volume = 1000
        self.assert_equal((None, None), IsoRequestAssociationData.find(
                                                                self.layout,
                                                                self.tool))
