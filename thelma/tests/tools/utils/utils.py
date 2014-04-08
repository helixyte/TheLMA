"""
Base classes for layout testing.

AAB
"""
from everest.entities.utils import get_root_aggregate
from everest.repositories.rdb.testing import check_attributes
from thelma.automation.semiconstants import get_384_rack_shape
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.utils.converters import BaseLayoutConverter
from thelma.automation.utils.layouts import EMPTY_POSITION_TYPE
from thelma.automation.utils.layouts import FIXED_POSITION_TYPE
from thelma.automation.utils.layouts import FLOATING_POSITION_TYPE
from thelma.automation.utils.layouts import LIBRARY_POSITION_TYPE
from thelma.automation.utils.layouts import MOCK_POSITION_TYPE
from thelma.automation.utils.layouts import MoleculeDesignPoolLayout
from thelma.automation.utils.layouts import MoleculeDesignPoolPosition
from thelma.automation.utils.layouts import ParameterSet
from thelma.automation.utils.layouts import UNTRANSFECTED_POSITION_TYPE
from thelma.automation.utils.layouts import UNTREATED_POSITION_TYPE
from thelma.automation.utils.layouts import WorkingLayout
from thelma.automation.utils.layouts import WorkingPosition
from thelma.interfaces import IMoleculeDesignPool
from thelma.models.rack import RACK_TYPES
from thelma.models.rack import RackPositionSet
from thelma.models.racklayout import RackLayout
from thelma.models.tagging import Tag
from thelma.models.tagging import TaggedRackPositionSet
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase


#: lists the position types that might return *True*
TYPE_METHODS = {'is_fixed' : set([FIXED_POSITION_TYPE]),
                'is_floating' : set([FLOATING_POSITION_TYPE]),
                'is_mock' : set([MOCK_POSITION_TYPE]),
                'is_library' : set([LIBRARY_POSITION_TYPE]),
                'is_empty' : set([EMPTY_POSITION_TYPE, UNTREATED_POSITION_TYPE,
                                  UNTRANSFECTED_POSITION_TYPE]),
                'is_untreated_type' : set([UNTREATED_POSITION_TYPE,
                                           UNTRANSFECTED_POSITION_TYPE])}


class MoleculeDesignPoolBaseTestCase(ToolsAndUtilsTestCase):

    POS_CLS = MoleculeDesignPoolPosition
    LAYOUT_CLS = MoleculeDesignPoolLayout
    POS_TYPE_IN_INIT = False

    POOL_TAGS = {
        'fixed' : Tag('molecule_design_pool', 'molecule_design_pool_id',
                      '205200'),
        'floating' : Tag('molecule_design_pool', 'molecule_design_pool_id',
                         'md_1'),
        'mock' : Tag('molecule_design_pool', 'molecule_design_pool_id', 'mock'),
        'library' : Tag('molecule_design_pool', 'molecule_design_pool_id',
                        'library'),
        'untreated' : Tag('molecule_design_pool', 'molecule_design_pool_id',
                          'untreated'),
        'untransfected' : Tag('molecule_design_pool', 'molecule_design_pool_id',
                              'untransfected')}

    TYPE_TAGS = {
            'fixed' : Tag('molecule_design_pool', 'position_type', 'fixed'),
            'floating' : Tag('molecule_design_pool', 'position_type',
                             'floating'),
            'mock' : Tag('molecule_design_pool', 'position_type', 'mock'),
            'library' : Tag('molecule_design_pool', 'position_type', 'library'),
            'untreated' : Tag('molecule_design_pool', 'position_type',
                              'untreated'),
            'untransfected' : Tag('molecule_design_pool', 'position_type',
                                  'untransfected'),
            'empty' : Tag('molecule_design_pool', 'position_type', 'empty')}

    POS_TYPES = (FIXED_POSITION_TYPE, FLOATING_POSITION_TYPE, MOCK_POSITION_TYPE,
             LIBRARY_POSITION_TYPE, UNTREATED_POSITION_TYPE,
             UNTRANSFECTED_POSITION_TYPE, EMPTY_POSITION_TYPE)

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        # pos label - pos type, pool
        self.pos_data = dict(
            a1=['fixed',
                get_root_aggregate(IMoleculeDesignPool).get_by_id(205200)],
            b1=['floating', 'md_1'],
            c1=['mock', 'mock'],
            d1=['library', 'library'],
            e1=['untreated', 'untreated'],
            f1=['untransfected', 'untransfected'],
            g1=['empty', None])

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        self.tear_down_as_add_on()

    def tear_down_as_add_on(self):
        del self.pos_data

    def _get_init_data(self, pos_label):
        pos_data = self.pos_data[pos_label]
        rack_pos = get_rack_position_from_label(pos_label)
        kw = dict(rack_position=rack_pos,
                  molecule_design_pool=pos_data[1])
        if self.POS_TYPE_IN_INIT:
            kw['position_type'] = pos_data[0]
        return kw

    def _get_position(self, pos_label, attrs=None):
        if attrs is None: attrs = self._get_init_data(pos_label)
        return self.POS_CLS(**attrs)

    def _get_tags(self, pos_label):
        tags = set()
        pos_type = self.pos_data[pos_label][0]
        if self.POS_CLS.EXPOSE_POSITION_TYPE: tags.add(self.TYPE_TAGS[pos_type])
        if self.POOL_TAGS.has_key(pos_type): tags.add(self.POOL_TAGS[pos_type])
        return tags

    def _add_optional_tag(self, tags, tag_map, pos_label):
        if tag_map.has_key(pos_label):
            tags.add(tag_map[pos_label])

    def _test_position_init(self):
        for pos_label in self.pos_data.keys():
            attrs = self._get_init_data(pos_label)
            wp = self._get_position(pos_label, attrs)
            self.assert_is_not_none(wp)
            check_attributes(wp, attrs)
            attrs['rack_position'] = 'a1'
            self.assert_raises(TypeError, self.POS_CLS, **attrs)

    def _test_position_type_properties(self, pos_labels=None):
        if pos_labels is None: pos_labels = self.pos_data.keys()
        for pos_label in pos_labels:
            wp = self._get_position(pos_label)
            pos_type = self.pos_data[pos_label][0]
            for meth, allowed_types in TYPE_METHODS.iteritems():
                is_type = getattr(wp, meth)
                if not (pos_type in allowed_types) == is_type:
                    msg = 'Wrong result for position type property test. ' \
                          'Position: %s, type: %s, method: %s' % (wp, pos_type,
                                                                  meth)
                    raise AssertionError(msg)

    def _test_position_equality(self, add_relevant_values, irrelevant_values):
        relevant_values = {
                    'rack_position' : get_rack_position_from_label('g8'),
                    'molecule_design_pool' : 'md_2',
                    'position_type' : FLOATING_POSITION_TYPE}
        relevant_values.update(add_relevant_values)
        all_values = dict(relevant_values, **irrelevant_values)
        pp1 = self._get_position('a1')
        pp2 = self._get_position('a1')
        self.assert_equal(pp1, pp2)
        for attr_name, value in all_values.iteritems():
            setattr(pp1, attr_name, value)
            if relevant_values.has_key(attr_name):
                if pp1 == pp2:
                    msg = 'Two positions should not be equal if their %s ' \
                          'values differ!' % (attr_name)
                    raise AssertionError(msg)
            else:
                if not pp1 == pp2:
                    msg = 'Two positions should be equal even if their %s ' \
                          'values differ!' % (attr_name)
                    raise AssertionError(msg)
            setattr(pp1, attr_name, getattr(pp2, attr_name))

    def _test_position_get_tag_set(self):
        for pos_label in self.pos_data.keys():
            exp_tags = self._get_tags(pos_label)
            pp = self._get_position(pos_label)
            self._compare_tag_sets(exp_tags, pp.get_tag_set())

    def _init_layout(self, shape=None):
        if shape is None: shape = get_96_rack_shape()
        return self.LAYOUT_CLS(shape=shape)

    def _create_test_layout(self):
        ml = self._init_layout()
        for pos_label in self.pos_data.keys():
            ml.add_position(self._get_position(pos_label))
        return ml

    def _test_layout_init(self):
        shape = get_384_rack_shape()
        ml = self._init_layout(shape=shape)
        self.assert_is_not_none(ml)
        self.assert_equal(ml.shape, shape)
        self.assert_equal(len(ml), 0)


class ConverterTestCase(ToolsAndUtilsTestCase):

    PARAMETER_SET = ParameterSet
    POS_CLS = WorkingPosition
    LAYOUT_CLS = WorkingLayout
    CONVERTER_CLS = BaseLayoutConverter

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        # pos_label = init values
        self.rack_layout = None
        self.shape = get_96_rack_shape()
        # positions as labels mapped onto temp ID
        self.pos_set_data = dict()
        # tags mapped onto temp ID
        self.tag_data = dict()
        #: tag map mapped onto pos labels
        self.tag_key_map = dict()

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.rack_layout
        del self.shape
        del self.pos_set_data
        del self.tag_data
        del self.tag_key_map

    def _create_tool(self):
        kw = self._get_kw()
        self.tool = self.CONVERTER_CLS(**kw)

    def _continue_setup(self):
        self.__create_test_layout()
        self._create_tool()

    def __create_test_layout(self):
        trp_sets = []
        for ident, pos_labels in self.pos_set_data.iteritems():
            positions = []
            for pos_label in pos_labels:
                rack_pos = get_rack_position_from_label(pos_label)
                positions.append(rack_pos)
            tag_list = self.tag_data[ident]
            tag_list = filter(None, tag_list) # pylint: disable=W0141
            rps = RackPositionSet.from_positions(positions)
            trps = TaggedRackPositionSet(set(tag_list), rps, self.user)
            trp_sets.append(trps)
        self.rack_layout = RackLayout(shape=self.shape,
                           tagged_rack_position_sets=trp_sets)

    def _insert_tag_data_tag(self, k, pos_label, tag_map, i):
        if tag_map.has_key(pos_label):
            self.tag_data[k].insert(i, tag_map[pos_label])
        else:
            self.tag_data[k].insert(i, None)

    def _get_kw(self):
        return dict(rack_layout=self.rack_layout)

    def _test_result(self, continue_setup=True):
        if continue_setup: self._continue_setup()
        layout = self.tool.get_result()
        self.assert_is_not_none(layout)
        self.assert_true(isinstance(layout, self.LAYOUT_CLS))
        exp_positions = self._get_all_positions()
        self._compare_pos_sets(exp_positions, layout.get_positions())
        exp_tags = self._get_all_tags()
        self._compare_tag_sets(exp_tags, layout.get_tags())
        self._test_position_for_tag(layout)
        self._test_tag_for_position(layout)
        return layout

    def _get_all_positions(self):
        all_labels = []
        for pos_labels in self.pos_set_data.values():
            all_labels.extend(pos_labels)
        return set(all_labels)

    def _get_all_tags(self):
        all_tags = []
        for tag_list in self.tag_data.values():
            all_tags.extend(tag_list)
        return set(all_tags)

    def _test_tag_for_position(self, layout):
        raise NotImplementedError('Abstract method.')

    def _test_position_for_tag(self, layout):
        raise NotImplementedError('Abstract method.')

    def _test_invalid_input_values(self):
        self._continue_setup()
        rl = self.rack_layout
        self.rack_layout = None
        self._test_and_expect_errors('The rack layout must be a RackLayout')
        self.rack_layout = rl

    def _test_invalid_rack_layout(self, msg):
        self._continue_setup()
        self._test_and_expect_errors(msg)


class RackSectorTestCase(ToolsAndUtilsTestCase):

    LAYOUT_CLS = MoleculeDesignPoolLayout

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.layout = None
        self.number_sectors = 4
        self.attribute_name = None
        self.rack_shape = get_384_rack_shape()
        # pos_label - [sector index, pool ID, conc]
        self.position_data = None
        self.cases = (1, 2, 3, 4)
        self.pool_agg = get_root_aggregate(IMoleculeDesignPool)
        self.current_case_num = None

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.layout
        del self.number_sectors
        del self.attribute_name
        del self.rack_shape
        del self.position_data
        del self.cases
        del self.pool_agg
        del self.current_case_num

    def _continue_setup(self):
        if self.position_data is None:
            self.position_data = self._get_case_data(3)
        self._init_layout()
        self._fill_layout()
        self._create_tool()

    def _init_layout(self):
        self.layout = self.LAYOUT_CLS(shape=self.rack_shape)

    def _fill_layout(self):
        raise NotImplementedError('Abstract method.')

    def _get_case_data(self, case_num):
        self.current_case_num = case_num
        if case_num == 1:
            # different pools and concentration, 1 empty
            # will not allow for sector association because
            # concentration combinations are not allowed
            return dict(
                C3=[0, 1, 10], C4=[1, 2, 20],
                    D3=[2, 'mock', None], D4=[3, 'mock', None],
                C5=[0, 3, 10], C6=[1, 4, 20],
                    D5=[2, 'md_001', 30], D6=[3, None, None],
                E3=[0, 6, 10], E4=[1, None, None],
                    F3=[2, 'md_002', 30], F4=[3, 'untreated', None],
                E5=[0, 7, 10], E6=[1, 9, 20],
                    F5=[2, 10, 30], F6=[3, None, None])
        elif case_num == 2:
            # different pools, equal concentrations, 1 empty
            return dict(
                C3=[0, 1, 10], C4=[1, 2, 10],
                    D3=[2, 'mock', None], D4=[3, 'mock', None],
                C5=[0, 3, 10], C6=[1, 4, 10],
                    D5=[2, 'md_001', 10], D6=[3, None, None],
                E3=[0, 6, 10], E4=[1, None, None],
                    F3=[2, 'md_002', 10], F4=[3, 'untreated', None],
                E5=[0, 7, 10], E6=[1, 9, 10],
                    F5=[2, 10, 10], F6=[3, None, None])
        elif case_num == 3:
            # 2 x 2 association, different concentrations
            return dict(
                C3=[0, 1, 10], C4=[1, 'mock', None],
                    D3=[2, 1, 20], D4=[3, 'mock', None],
                C5=[0, 3, 10], C6=[1, 4, 10],
                    D5=[2, 3, 20], D6=[3, 4, 20],
                E3=[0, 'md_001', 10], E4=[1, 'md_002', 10],
                    F3=[2, 'md_001', 20], F4=[3, 'md_002', 20],
                E5=[0, 5, 10], E6=[1, 5, 10],
                    F5=[2, 5, 20], F6=[3, 5, 20],
                E7=[0, 'md_003', 10], E8=[1, 'md_004', 10],
                    F7=[2, 'md_003', 20], F8=[3, 'md_004', 20],)
        elif case_num == 4:
            # 2 x 2 association, all equal concentrations
            return dict(
                C3=[0, 1, 10], C4=[1, 'mock', None],
                    D3=[2, 1, 10], D4=[3, 'mock', None],
                C5=[0, 3, 10], C6=[1, 4, 10],
                    D5=[2, 3, 10], D6=[3, 4, 10],
                E3=[0, 'md_001', 10], E4=[1, 'md_002', 10],
                    F3=[2, 'md_001', 10], F4=[3, 'md_002', 10],
                E5=[0, 5, 10], E6=[1, 5, 10],
                    F5=[2, 5, 10], F6=[3, 5, 10])

    def _get_expected_sector_concentrations(self, include_none_sectors=True):
        if self.current_case_num == 1:
            # different pools and concentration, 1 empty
            if include_none_sectors:
                return {0 : 10, 1 : 20, 2 : 30, 3 : None}
            else:
                return {0 : 10, 1 : 20, 2 : 30}
        elif self.current_case_num == 2:
            # different pools, equal concentrations, 1 empty
            if include_none_sectors:
                return {0 : 10, 1 : 10, 2 : 10, 3 : None}
            else:
                return {0 : 10, 1 : 10, 2 : 10}
        elif self.current_case_num == 3:
            # 2 x 2 association, different concentrations
            return {0 : 10, 1 : 10, 2 : 20, 3 : 20}
        else: # 2 x 2 association, all equal concentrations
            return {0 : 10, 1 : 10, 2 : 10, 3 : 10}

    def _get_expected_associated_sectors(self):
        if self.current_case_num == 1:
            # different pools and concentration, 1 empty
            return None
        elif self.current_case_num == 2:
            # different pools, equal concentrations, 1 empty
            return [[0], [1], [2]]
        elif self.current_case_num == 3:
            # 2 x 2 association, different concentrations
            return [[0, 2], [1, 3]]
        else: # 2 x 2 association, all equal concentrations
            return [[0, 2], [1, 3]]

    def _get_expected_parent_sectors(self):
        if self.current_case_num == 1:
            # different pools and concentration, 1 empty
            return {0 : None, 1 : None, 2 : None}
        elif self.current_case_num == 2:
            # different pools, equal concentrations, 1 empty
            return {0 : None, 1 : None, 2 : None}
        elif self.current_case_num == 3:
            # 2 x 2 association, different concentrations
            return {0 : 2, 1 : 3, 2 : None, 3 : None}
        else: # 2 x 2 association, all equal concentrations
            return {0 : None, 1 : None, 2 : 0, 3 : 1}

    def _get_pool(self, pool_id):
        if not isinstance(pool_id, int): return pool_id
        if self.pool_map.has_key(pool_id):
            return self.pool_map[pool_id]
        pool = self.pool_agg.get_by_id(pool_id + 205600)
        if pool is None:
            raise ValueError('Pool ID %i is not known!' % (pool_id))
        self.pool_map[pool_id] = pool
        return pool

    def _test_invalid_layout(self):
        ori_layout = self.layout
        self.layout = self.layout.create_rack_layout()
        msg = 'layout must be a %s object' % (self.LAYOUT_CLS.__name__)
        self._test_and_expect_errors(msg)
        self.layout = ori_layout

    def _test_invalid_number_sectors(self):
        self.number_sectors = '4'
        self._test_and_expect_errors('The number of sectors must be a int')
        self.number_sectors = 4

    def _test_invalid_attribute_name(self):
        ori_name = self.attribute_name
        self.attribute_name = 3
        self._test_and_expect_errors('The attribute name must be a str ' \
                                     'object (obtained: int)')
        self.attribute_name = ori_name

    def _test_value_determine_unknown_attribute_name(self):
        self._continue_setup()
        self.attribute_name = 'molecule'
        self._test_and_expect_errors('Unknown attribute')

    def _test_value_determiner(self):
        for case_num in self.cases:
            self.position_data = self._get_case_data(case_num)
            self._continue_setup()
            if self.tool is None: self._create_value_determiner()
            exp_map = self._get_expected_sector_concentrations(case_num)
            self._check_value_determiner_run(exp_map)

    def _create_value_determiner(self):
        raise NotImplementedError('Abstract method.')

    def _check_value_determiner_run(self, exp_map):
        sector_map = self.tool.get_result()
        if sector_map is None:
            msg = 'Sector map for case %i is None!' % (self.current_case_num)
            raise AssertionError(msg)
        if not sector_map == exp_map:
            msg = 'The sector map for case %i differs from the expected map!' \
                  '\nExpected:%s\nFound:%s\n' \
                   % (self.current_case_num, exp_map, sector_map)
            raise AssertionError(msg)

    def _test_sector_associator(self):
        for case_num in self.cases:
            self.position_data = self._get_case_data(case_num)
            self._continue_setup()
            if self.tool is None: self._create_sector_associator()
            exp_association = self._get_expected_associated_sectors()
            self._check_sector_associator_run(exp_association)

    def _create_sector_associator(self):
        raise NotImplementedError('Abstract method.')

    def _check_sector_associator_run(self, exp_association):
        if exp_association is None:
            self._test_and_expect_errors('All sector set must have the ' \
                'same combination of concentrations to ensure all samples ' \
                'are treated equally.')
        else:
            association = self.tool.get_result()
            if association is None:
                msg = 'Associations for case %i is None!' \
                       % (self.current_case_num)
                raise AssertionError(msg)
            if not sorted(association) == sorted(exp_association):
                msg = 'The associations for case %i differs from the ' \
                      'expected map!\nExpected:%s\nFound:%s\n' \
                       % (self.current_case_num, exp_association, association)
                raise AssertionError(msg)

    def _test_associator_inconsistent_quadrants(self, exp_msg):
        self.position_data = self._get_case_data(4)
        self.position_data['F6'] = [3, None, None]
        self._continue_setup()
        self._test_and_expect_errors(exp_msg)

    def _test_associator_different_set_lengths(self, exp_msg):
        self.position_data = self._get_case_data(3)
        self.position_data['C6'] = [1, 2, 10]
        self.position_data['E4'] = [1, 2, 10]
        self._continue_setup()
        self._test_and_expect_errors(exp_msg)

    def _test_different_concentration_combinations(self):
        self.position_data = self._get_case_data(3)
        for pos_data in self.position_data.values():
            if pos_data[2] is None: continue
            sector_num = pos_data[0] + 1
            pos_data[2] = sector_num * 10
        self._continue_setup()
        self._test_and_expect_errors('All sector set must have the same ' \
            'combination of concentrations to ensure all samples are ' \
            'treated equally. This rule is not met. Talk to IT, please. ' \
            'Associated sectors: [[0, 2], [1, 3]], concentrations: 0 (10.0) ' \
            '- 1 (20.0) - 2 (30.0) - 3 (40.0).')

    def _test_association_data_384(self):
        for case_num in self.cases:
            self.position_data = self._get_case_data(case_num)
            self._continue_setup()
            self._check_association_data_384()

    def _test_assocation_data_96(self):
        self.rack_shape = get_96_rack_shape()
        for case_num in self.cases:
            self.position_data = self._get_case_data(case_num)
            self._continue_setup()
            self._adjust_96_layout_for_association_data_test()
            self._check_association_data_96()

    def _adjust_96_layout_for_association_data_test(self):
        raise NotImplementedError('Abstract method.')

    def _create_association_data(self):
        raise NotImplementedError('Abstract method.')

    def _check_association_data_384(self):
        exp_associations = self._get_expected_associated_sectors()
        if exp_associations is None:
            self._expect_error(ValueError, self._create_association_data,
                        'Error when trying to find rack sector association.')
            return None
        ad = self._create_association_data()
        self.assert_is_not_none(ad)
        self.assert_equal(ad.number_sectors, 4)
        exp_conc = self._get_expected_sector_concentrations(False)
        if not ad.sector_concentrations == exp_conc:
            msg = 'The sector maps for case %i differ. Expected: %s, ' \
                  'found: %s.' % (self.current_case_num, exp_conc,
                                  ad.sector_concentrations)
            raise AssertionError(msg)
        if not sorted(ad.associated_sectors) == sorted(exp_associations):
            msg = 'The associated sectors for case %i differ: Expected: %s, ' \
                  'found: %s.' % (self.current_case_num, exp_associations,
                                  ad.associated_sectors)
            raise AssertionError(msg)
        exp_parents = self._get_expected_parent_sectors()
        if not exp_parents == ad.parent_sectors:
            msg = 'The parent sectors for case %i differ: Expected: %s, ' \
                  'found: %s.' % (self.current_case_num, exp_parents,
                                  ad.parent_sectors)
            raise AssertionError(msg)
        return ad

    def _check_association_data_96(self):
        if self.current_case_num == 1 or self.current_case_num == 3:
            self._expect_error(ValueError, self._create_association_data,
                'There is more than 1 concentration although there is is ' \
                'only one rack sector!')
            return None
        else:
            ad = self._create_association_data()
            self.assert_equal(ad.number_sectors, 1)
            self.assert_equal({0 : 10}, ad.sector_concentrations)
            self.assert_equal({0 : None}, ad.parent_sectors)
            self.assert_equal([[0]], ad.associated_sectors)
            return ad


class VerifierTestCase(ToolsAndUtilsTestCase):

    LAYOUT_CLS = MoleculeDesignPoolLayout
    POSITION_CLS = MoleculeDesignPoolPosition

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.layout = None
        self.rack = None
        self.position_data = dict() # are added to both layout and rack
        self.add_pos_data = dict() # are only added to the layout
        self.plate_type = None
        self.starting_sample_vol = 10 / VOLUME_CONVERSION_FACTOR
        self.starting_sample_conc = 10000 / CONCENTRATION_CONVERSION_FACTOR
        self.shape = get_96_rack_shape()
        self.rack_specs = None

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.layout
        del self.position_data
        del self.starting_sample_vol
        del self.starting_sample_conc
        del self.add_pos_data
        del self.shape
        del self.rack_specs

    def _continue_setup(self, session=None):
        self.__create_test_rack(session)
        self._init_layout()
        self.__fill_layout()
        self._fill_rack(session)
        self._create_other_objects()
        self._create_tool()

    def __create_test_rack(self, session):
        if self.plate_type == RACK_TYPES.PLATE:
            self.rack = self._create_plate(specs=self.rack_specs)
        else:
            self.rack = self._create_tube_rack(specs=self.rack_specs)
        self.rack.barcode = '09999999'
        if not session is None:
            session.add(type(self.rack), self.rack)

    def _init_layout(self):
        self.layout = self.LAYOUT_CLS(shape=self.shape)

    def __fill_layout(self):
        for pos_label, pos_data in self.position_data.iteritems():
            self._add_position(pos_label, pos_data)
        if len(self.add_pos_data) > 0:
            for pos_label, pos_data in self.add_pos_data.iteritems():
                self._add_position(pos_label, pos_data)

    def _add_position(self, pos_label, pos_data):
        kw = self._get_position_kw(pos_label, pos_data)
        pool_pos = self.POSITION_CLS(**kw)
        self.layout.add_position(pool_pos)

    def _get_position_kw(self, pos_label, pos_data):
        raise NotImplementedError('Abstract method.')

    def _fill_rack(self, session):
        raise NotImplementedError('Abstract method.')

    def _add_sample(self, container, pool_id):
        pool = self._get_pool(pool_id)
        conc = self.starting_sample_conc / pool.number_designs
        sample = container.make_sample(self.starting_sample_vol)
        for md in pool:
            mol = self._create_molecule(molecule_design=md)
            sample.make_sample_molecule(mol, conc)

    def _create_other_objects(self):
        raise NotImplementedError('Abstract method.')

    def _test_and_expect_errors(self, msg=None):
        ToolsAndUtilsTestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_expected_layout())

    def _test_and_expect_compliance(self):
        result = self.tool.get_result()
        self.assert_is_not_none(result)
        self.assert_true(result)
        self.assert_equal(self.tool.get_expected_layout(),
                          self.layout)

    def __test_and_expect_mismatch(self, error_msg_fragment):
        self._create_tool()
        result = self.tool.get_result()
        self.assert_is_not_none(result)
        self.assert_false(result)
        self._check_error_messages(error_msg_fragment)
        self.assert_is_none(self.tool.get_expected_layout())

    def _test_and_expect_missing_sample(self):
        self.__test_and_expect_mismatch('Some expected molecule designs ' \
                                        'are missing in the rack:')

    def _test_and_expect_additional_samples(self):
        self.__test_and_expect_mismatch('molecule designs although they ' \
                                        'should be empty')

    def _test_and_expect_mismatching_samples(self):
        self.__test_and_expect_mismatch('The molecule designs of the ' \
                                        'following positions do not match')

    def _test_and_expect_rack_shape_mismatch(self):
        self.__test_and_expect_mismatch('The rack shapes of the expected ' \
                                        'layout')

    def _test_insufficient_volume(self):
        self.__test_and_expect_mismatch('The volumes for the following ' \
                                        'positions are insufficient:')
