"""
Tests for classes involved in layout handling
"""
from everest.entities.utils import get_root_aggregate
from everest.repositories.rdb.testing import check_attributes
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.utils.converters import BaseLayoutConverter
from thelma.automation.utils.converters import LibraryLayoutConverter
from thelma.automation.utils.converters import MoleculeDesignPoolLayoutConverter
from thelma.automation.utils.converters import TransferLayoutConverter
from thelma.automation.utils.layouts import EMPTY_POSITION_TYPE
from thelma.automation.utils.layouts import FIXED_POSITION_TYPE
from thelma.automation.utils.layouts import FLOATING_POSITION_TYPE
from thelma.automation.utils.layouts import LIBRARY_POSITION_TYPE
from thelma.automation.utils.layouts import LibraryLayout
from thelma.automation.utils.layouts import LibraryLayoutParameters
from thelma.automation.utils.layouts import LibraryLayoutPosition
from thelma.automation.utils.layouts import MOCK_POSITION_TYPE
from thelma.automation.utils.layouts import MoleculeDesignPoolLayout
from thelma.automation.utils.layouts import MoleculeDesignPoolParameters
from thelma.automation.utils.layouts import MoleculeDesignPoolPosition
from thelma.automation.utils.layouts import ParameterAliasValidator
from thelma.automation.utils.layouts import ParameterSet
from thelma.automation.utils.layouts import TransferLayout
from thelma.automation.utils.layouts import TransferParameters
from thelma.automation.utils.layouts import TransferPosition
from thelma.automation.utils.layouts import TransferTarget
from thelma.automation.utils.layouts import UNTRANSFECTED_POSITION_TYPE
from thelma.automation.utils.layouts import UNTREATED_POSITION_TYPE
from thelma.automation.utils.layouts import WorkingLayout
from thelma.automation.utils.layouts import WorkingPosition
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import IMoleculeType
from thelma.models.moleculetype import MOLECULE_TYPE_IDS
from thelma.models.rack import RackPosition
from thelma.models.tagging import Tag
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase
from thelma.tests.tools.utils.utils import ConverterTestCase
from thelma.tests.tools.utils.utils import MoleculeDesignPoolBaseTestCase


class _ParameterSetDummy(ParameterSet):

    DOMAIN = 'test'
    MY_PARAM = 'test_param'
    OTHER_PARAM = 'other_param'
    ALL = [MY_PARAM, OTHER_PARAM]
    REQUIRED = [MY_PARAM]
    ALIAS_MAP = {MY_PARAM : ['param_alias1', 'param_alias2'],
                 OTHER_PARAM : {}}
    DOMAIN_MAP = {MY_PARAM : DOMAIN, OTHER_PARAM : DOMAIN}


class ParameterSetTestCase(ToolsAndUtilsTestCase):

    def test_alias_validator(self):
        val = ParameterAliasValidator(_ParameterSetDummy.MY_PARAM)
        self.assert_equal(len(val.aliases), 1)
        alias1 = 'alias_1'
        val.add_alias(alias1)
        self.assert_equal(len(val.aliases), 2)
        self.assert_true(val.has_alias(alias1))
        self.assert_true(val.has_alias(alias1.replace('_', ' ')))
        self.assert_false(val.has_alias('other_alias'))

    def test_is_valid_parameter(self):
        self.assert_true(_ParameterSetDummy.is_valid_parameter(
                                           _ParameterSetDummy.MY_PARAM))
        self.assert_false(_ParameterSetDummy.is_valid_parameter('other'))

    def test_create_validator_from_parameter(self):
        val = _ParameterSetDummy.create_validator_from_parameter(
                                                _ParameterSetDummy.MY_PARAM)
        exp_val = ParameterAliasValidator(_ParameterSetDummy.MY_PARAM)
        exp_val.add_alias('param_alias1')
        exp_val.add_alias('param_alias2')
        self.assert_equal(val, exp_val)
        self.assert_equal(val.aliases, exp_val.aliases)

    def test_create_all_validators(self):
        val1 = ParameterAliasValidator(_ParameterSetDummy.MY_PARAM)
        val1.add_alias('param_alias1')
        val1.add_alias('param_alias2')
        val2 = ParameterAliasValidator(_ParameterSetDummy.OTHER_PARAM)
        exp_vals = {val1.parameter : val1, val2.parameter : val2}
        all_vals = _ParameterSetDummy.create_all_validators()
        self.assert_equal(len(all_vals), len(exp_vals))
        for parameter_name, val in all_vals.iteritems():
            exp_val = exp_vals[parameter_name]
            self.assert_equal(exp_val.aliases, val.aliases)

    def test_get_all_alias(self):
        params = _ParameterSetDummy
        aliases = params.get_all_alias(_ParameterSetDummy.MY_PARAM)
        exp_aliases = [params.MY_PARAM]
        exp_aliases.extend(params.ALIAS_MAP[params.MY_PARAM])
        exp_aliases = set(exp_aliases)
        self.assert_equal(aliases, exp_aliases)
        aliases2 = params.get_all_alias(params.OTHER_PARAM)
        exp_aliases2 = set([params.OTHER_PARAM])
        self.assert_equal(aliases2, exp_aliases2)


class _WorkingPositionDummy(WorkingPosition):
    """
    This class is meant to test the main functions of the
    :class:`WorkingPosition` class. It serves to get around the abstract
    limitation.
    """

    PARAMETER_SET = _ParameterSetDummy
    RECORD_FALSE_VALUES = False

    def __init__(self, rack_position, my_param, other_param):
        WorkingPosition.__init__(self, rack_position=rack_position)
        self.my_param = my_param
        self.other_param = other_param

    def _get_parameter_values_map(self):
        return {self.PARAMETER_SET.MY_PARAM : self.my_param,
                self.PARAMETER_SET.OTHER_PARAM : self.other_param}


class WorkingPositionTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.rack_pos = get_rack_position_from_label('a1')
        self.my_param_tag = Tag('test', 'test_param', '1')
        self.other_param_tag = Tag('test', 'other_param', 'True')

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.rack_pos
        del self.my_param_tag
        del self.other_param_tag

    def __get_kw(self):
        return dict(rack_position=self.rack_pos, my_param=1, other_param=True)

    def __get_position(self):
        return _WorkingPositionDummy(**self.__get_kw())

    def test_init(self):
        self._expect_error(NotImplementedError, WorkingPosition,
                       'Abstract class.', **dict(rack_position=self.rack_pos))
        wp = self.__get_position()
        self.assert_is_not_none(wp)
        check_attributes(wp, self.__get_kw())

    def test_get_parameter_value(self):
        wp = self.__get_position()
        self.assert_equal(wp.get_parameter_value(_ParameterSetDummy.MY_PARAM),
                          1)
        self.assert_equal(wp.get_parameter_value(
                          _ParameterSetDummy.OTHER_PARAM), True)

    def test_get_parameter_tag(self):
        wp = self.__get_position()
        params = _ParameterSetDummy
        self.assert_equal(wp.get_parameter_tag(params.MY_PARAM),
                          self.my_param_tag)
        self.assert_equal(wp.get_parameter_tag(params.OTHER_PARAM),
                          self.other_param_tag)
        wp.other_param = False
        self.assert_is_none(wp.get_parameter_tag(params.OTHER_PARAM))

    def test_get_tag_set(self):
        wp = self.__get_position()
        exp_tags1 = [self.my_param_tag, self.other_param_tag]
        tags1 = wp.get_tag_set()
        self._compare_tag_sets(exp_tags1, tags1)
        wp.other_param = False # false booleans are not recorded
        exp_tags2 = [self.my_param_tag]
        tags2 = wp.get_tag_set()
        self._compare_tag_sets(exp_tags2, tags2)
        wp.other_param = None # not required
        exp_tags3 = [self.my_param_tag]
        tags3 = wp.get_tag_set()
        self._compare_tag_sets(exp_tags3, tags3)
        wp.my_param = None # required
        self.my_param_tag.value = wp.NONE_REPLACER
        exp_tags4 = [self.my_param_tag]
        tags4 = wp.get_tag_set()
        self._compare_tag_sets(exp_tags4, tags4)

    def test_has_tag(self):
        wp = self.__get_position()
        self.assert_true(wp.has_tag(self.my_param_tag))
        wp.my_param += 1
        self.assert_false(wp.has_tag(self.my_param_tag))

    def test_get_value_string(self):
        self.assert_equal(WorkingPosition.get_value_string(1), '1')
        self.assert_equal(WorkingPosition.get_value_string(1.0), '1')
        self.assert_equal(WorkingPosition.get_value_string(1.1), '1.1')
        self.assert_equal(WorkingPosition.get_value_string(1.01), '1')

    def test_parse_boolean_tag_value(self):
        self.assert_equal(WorkingPosition.parse_boolean_tag_value('True'),
                          True)
        self.assert_equal(WorkingPosition.parse_boolean_tag_value('False'),
                          False)
        self._expect_error(ValueError, WorkingPosition.parse_boolean_tag_value,
                           'Invalid string for boolean conversion: None',
                           **dict(boolean_str='None'))


class _WorkingLayoutDummy(WorkingLayout):
    """
    This class is meant to test the main functions of the
    :class:`WorkingLayout` class. It serves to get around the abstract
    limitation.
    """
    POSITION_CLS = _WorkingPositionDummy


class WorkingLayoutTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.shape = get_96_rack_shape()
        self.params = dict(a1=[1, True], b1=[2, False], c1=[1, True])

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.shape
        del self.params

    def __get_positions(self):
        wps = []
        for pos_label, pos_data in self.params.iteritems():
            kw = dict(rack_position=get_rack_position_from_label(pos_label),
                      my_param=pos_data[0], other_param=pos_data[1])
            wp = _WorkingPositionDummy(**kw)
            wps.append(wp)
        return wps

    def __get_tags(self, pos_label):
        if pos_label == 'a1':
            tag1 = Tag(_ParameterSetDummy.DOMAIN, _ParameterSetDummy.MY_PARAM,
                       '1')
            tag2 = Tag(_ParameterSetDummy.DOMAIN, _ParameterSetDummy.OTHER_PARAM,
                       'True')
            return set([tag1, tag2])
        elif pos_label == 'b1':
            tag1 = Tag(_ParameterSetDummy.DOMAIN, _ParameterSetDummy.MY_PARAM,
                       '2')
            return set([tag1])
        else:
            tag1 = Tag(_ParameterSetDummy.DOMAIN, _ParameterSetDummy.MY_PARAM,
                       '1')
            tag2 = Tag(_ParameterSetDummy.DOMAIN, _ParameterSetDummy.OTHER_PARAM,
                       'True')
            return set([tag1, tag2])

    def __get_layout(self, with_positions=True):
        wl = _WorkingLayoutDummy(shape=self.shape)
        if with_positions:
            for wp in self.__get_positions():
                wl.add_position(wp)
        return wl

    def test_init(self):
        self._expect_error(NotImplementedError, WorkingLayout,
                       'Abstract class.', **dict(shape=self.shape))
        wl = self.__get_layout(with_positions=False)
        self.assert_is_not_none(wl)

    def test_add_get_and_del_position(self):
        wl = self.__get_layout(with_positions=False)
        positions = self.__get_positions()
        wp1 = positions[0]
        wp2 = positions[1]
        self.assert_equal(len(wl), 0)
        wl.add_position(wp1)
        self.assert_equal(len(wl), 1)
        self.assert_equal(wl.get_working_position(wp1.rack_position), wp1)
        self.assert_is_none(wl.get_working_position(wp2.rack_position))
        self._expect_error(TypeError, wl.add_position,
                   'A position to be added must be a ' \
                   '_WorkingPositionDummy object (obtained type: int).',
                   **dict(working_position=2))
        wl.del_position(wp1.rack_position)
        self.assert_equal(len(wl), 0)
        self.assert_is_none(wl.get_working_position(wp1.rack_position))
        wl.del_position(wp2.rack_position) # no error
        self.assert_equal(len(wl), 0)
        beyond_pos = get_rack_position_from_label('o24')
        wp1.rack_position = beyond_pos
        self._expect_error(KeyError, wl.add_position,
                           'Position O24 is beyond the layout range (8x12)',
                           **dict(working_position=wp1))

    def test_equality(self):
        wl1 = self.__get_layout()
        wl2 = self.__get_layout()
        wl3 = self.__get_layout()
        wl3.del_position(wl3.get_positions()[0])
        self.assert_equal(wl1, wl2)
        self.assert_not_equal(wl1, wl3)
        self.assert_not_equal(wl1, 1)

    def test_get_tags(self):
        exp_tags = set()
        for pos_label in self.params.keys():
            pos_tags = self.__get_tags(pos_label)
            for tag in pos_tags: exp_tags.add(tag)
        self.assert_equal(len(exp_tags), 3)
        wl = self.__get_layout()
        tags = wl.get_tags()
        self._compare_tag_sets(exp_tags, tags)

    def test_positions(self):
        wl = self.__get_layout()
        self._compare_pos_sets(self.params.keys(), wl.get_positions())

    def test_get_tags_for_position(self):
        wl = self.__get_layout()
        exp_tags = self.__get_tags('a1')
        tags = wl.get_tags_for_position(get_rack_position_from_label('a1'))
        self._compare_tag_sets(exp_tags, tags)

    def test_get_positions_for_tag(self):
        tag = list(self.__get_tags('c1'))[0]
        exp_pos_labels = ['a1', 'c1']
        wl = self.__get_layout()
        positions = wl.get_positions_for_tag(tag)
        self._compare_pos_sets(exp_pos_labels, positions)

    def test_get_sorted_working_positions(self):
        self.params['a2'] = self.params['c1']
        del self.params['c1']
        wl = self.__get_layout()
        sorted_wps = wl.get_sorted_working_positions()
        wp_order = []
        for wp in sorted_wps: wp_order.append(wp.rack_position.label)
        exp_order = ['A1', 'A2', 'B1']
        self.assert_equal(wp_order, exp_order)

    def test_create_tagged_rack_position_sets(self):
        wl = self.__get_layout()
        trp_sets = wl.create_tagged_rack_position_sets()
        self.assert_equal(len(trp_sets), 2)
        for trps in trp_sets:
            self.assert_equal(len(trps.rack_position_set), len(trps.tags))

    def test_create_rack_layout(self):
        wl = self.__get_layout()
        rl = wl.create_rack_layout()
        self.assert_equal(len(rl.tagged_rack_position_sets), 2)
        self._compare_pos_sets(wl.get_positions(), rl.get_positions())
        self._compare_tag_sets(wl.get_tags(), rl.get_tags())
        tag = list(self.__get_tags('c1'))[0]
        self._compare_pos_sets(wl.get_positions_for_tag(tag),
                               rl.get_positions_for_tag(tag))
        rack_pos = wl.get_positions()[0]
        self._compare_tag_sets(wl.get_tags_for_position(rack_pos),
                               rl.get_tags_for_position(rack_pos))


class _BaseLayoutConverterDummy(BaseLayoutConverter):
    """
    Serves to circumvent the abstract class restriction of the class.
    """

    PARAMETER_SET = _ParameterSetDummy
    LAYOUT_CLS = _WorkingLayoutDummy
    POSITION_CLS = _WorkingPositionDummy

    def _get_position_init_values(self, parameter_map, rack_pos):
        my_param = parameter_map[self.PARAMETER_SET.MY_PARAM]
        if my_param is None: return None
        other_param = parameter_map[self.PARAMETER_SET.OTHER_PARAM]
        return dict(my_param=my_param, other_param=other_param)

    def _perform_layout_validity_checks(self, working_layout):
        pass


class BaseLayoutConverterTestCase(ConverterTestCase):

    PARAMETER_SET = _ParameterSetDummy
    POS_CLS = _WorkingPositionDummy
    LAYOUT_CLS = _WorkingLayoutDummy
    CONVERTER_CLS = _BaseLayoutConverterDummy

    def set_up(self):
        ConverterTestCase.set_up(self)
        self.pos_set_data = {1 : ['a1'], 2 : ['b1']}
        params = self.PARAMETER_SET
        self.tag_data = {
                    1 : [Tag(params.DOMAIN, params.MY_PARAM, '1')],
                    2 : [Tag(params.DOMAIN, params.MY_PARAM, '2'),
                         Tag(params.DOMAIN, params.OTHER_PARAM, '3')]}

    def test_result(self):
        self._test_result()

    def _test_position_for_tag(self, layout):
        tag = self.tag_data[1][0]
        exp_positions = self.pos_set_data[1]
        self._compare_pos_sets(exp_positions, layout.get_positions_for_tag(tag))

    def _test_tag_for_position(self, layout):
        rack_pos = get_rack_position_from_label('b1')
        exp_tags = self.tag_data[2]
        tag_set = layout.get_tags_for_position(rack_pos)
        self._compare_tag_sets(exp_tags, tag_set)

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_missing_parameter(self):
        for tag_list in self.tag_data.values():
            tag = tag_list[0]
            tag.predicate = 'changed'
        self._continue_setup()
        self._test_and_expect_errors('There is no test_param specification ' \
                 'for this rack layout. Valid factor names are: ' \
                 'param alias1, param alias2, test param (case-insensitive)')

    def test_multiple_tags(self):
        tag = self.tag_data[2][1]
        tag.predicate = self.PARAMETER_SET.MY_PARAM
        self._continue_setup()
        self._test_and_expect_errors()


class _MoleculeDesignPoolPositionDummy(MoleculeDesignPoolPosition):
    """
    This dummy class allows to test the molecule design pool positions.
    It only serves to get around the abstract class.
    """
    PARAMETER_SET = MoleculeDesignPoolParameters


class _MoleculeDesignPoolLayoutDummy(MoleculeDesignPoolLayout):
    """
    A dummy class that allows testing while circumventing the abstract class
    restriction.
    """
    POSITION_CLS = _MoleculeDesignPoolPositionDummy


class _MoleculeDesignPoolClassesTestCase(MoleculeDesignPoolBaseTestCase):

    LAYOUT_CLS = _MoleculeDesignPoolLayoutDummy
    POS_CLS = _MoleculeDesignPoolPositionDummy


class MoleculeDesignPoolParametersTestCase(_MoleculeDesignPoolClassesTestCase):

    def test_get_position_type(self):
        meth = MoleculeDesignPoolParameters.get_position_type
        pool = self._get_entity(IMoleculeDesignPool, '205200')
        self.assert_equal(meth(pool), FIXED_POSITION_TYPE)
        self.assert_equal(meth('md_1'), FLOATING_POSITION_TYPE)
        self.assert_equal(meth('mock'), MOCK_POSITION_TYPE)
        self.assert_equal(meth('library'), LIBRARY_POSITION_TYPE)
        self.assert_equal(meth('untreated'), UNTREATED_POSITION_TYPE)
        self.assert_equal(meth('untransfected'), UNTRANSFECTED_POSITION_TYPE)
        self.assert_equals(meth(None), EMPTY_POSITION_TYPE)
        self._expect_error(ValueError, meth,
                   'Unable to determine type for molecule design pool: 1.2',
                   **dict(molecule_design_pool=1.2))
        self._expect_error(ValueError, meth,
                   'Unable to determine type for molecule design pool: fixed.',
                   **dict(molecule_design_pool='fixed'))

    def test_is_untreated_type(self):
        self.assert_true(MoleculeDesignPoolParameters.is_untreated_type(
                                                            'untreated'))
        self.assert_true(MoleculeDesignPoolParameters.is_untreated_type(
                                                            'untransfected'))
        self.assert_false(MoleculeDesignPoolParameters.is_untreated_type(
                                                            None))
        self.assert_false(MoleculeDesignPoolParameters.is_untreated_type(
                                                            'fixed'))
        self.assert_false(MoleculeDesignPoolParameters.is_untreated_type(
                                                            'empty'))

    def test_is_valid_untreated_value(self):
        m = { 'untreated' : True, 'UNTREATED' : True, None:  True,
             'untransfected' : True, 'UNTRANSFECTED' : True, 'None' : True,
             'fixed' : False, 'empty' : False, 'mock' : False}
        for val, exp_res in m.iteritems():
            res = MoleculeDesignPoolParameters.is_valid_untreated_value(val)
            self.assert_equal(res, exp_res)


class MoleculeDesignPoolPositionTestCase(_MoleculeDesignPoolClassesTestCase):

    POS_TYPE_IN_INIT = True

    def test_init(self):
        self._test_position_init()
        attrs = self._get_init_data('a1')
        self._expect_error(NotImplementedError, MoleculeDesignPoolPosition,
                           'Abstract class', **attrs)
        pool = attrs['molecule_design_pool']
        attrs['molecule_design_pool'] = pool.id
        self._expect_error(TypeError, self.POS_CLS,
                           'The molecule design pool must be a ' \
                           'MoleculeDesignPool (obtained: int)', **attrs)
        attrs['molecule_design_pool'] = pool
        attrs['position_type'] = MOCK_POSITION_TYPE
        self._expect_error(ValueError, self.POS_CLS,
                'The position type for this pool (fixed) does not match ' \
                'the passed position type (mock)', **attrs)

    def test_type_properties(self):
        self._test_position_type_properties()

    def test_equality(self):
        self._test_position_equality({}, {})

    def test_create_empty_pos(self):
        exp_pos = self._get_position('g1')
        empty_pos = _MoleculeDesignPoolPositionDummy.create_empty_position(
                                                        exp_pos.rack_position)
        self.assert_equal(exp_pos, empty_pos)

    def test_molecule_design_pool_id(self):
        fp = self._get_position('a1') # fixed position
        self.assert_equal(fp.molecule_design_pool_id,
                          fp.molecule_design_pool.id)
        flp = self._get_position('b1') # floating position
        self.assert_equal(flp.molecule_design_pool_id, flp.molecule_design_pool)

    def test_stock_concentration(self):
        fp = self._get_position('a1') # fixed position
        self.assert_equal(fp.stock_concentration, 50000)
        for pos_label, pos_data in self.pos_data.iteritems():
            if pos_data[0] == FIXED_POSITION_TYPE: continue
            pp = self._get_position(pos_label)
            self.assert_is_none(pp.stock_concentration)

    def test_molecule_type(self):
        fp = self._get_position('a1') # fixed position
        self.assert_equal(fp.molecule_type.id, MOLECULE_TYPE_IDS.SIRNA)
        for pos_label, pos_data in self.pos_data.iteritems():
            if pos_data[0] == FIXED_POSITION_TYPE: continue
            pp = self._get_position(pos_label)
            self.assert_is_none(pp.molecule_type)

    def test_get_tag_set(self):
        self._test_position_get_tag_set()


class MoleculeDesignPoolLayoutTestCase(_MoleculeDesignPoolClassesTestCase):

    def test_init(self):
        attrs = dict(shape=get_96_rack_shape)
        self._expect_error(NotImplementedError, MoleculeDesignPoolLayout,
                           'Abstract class', **attrs)
        self._test_layout_init()

    def test_floating_molecule_type(self):
        pl = self._create_test_layout()
        self.assert_is_none(pl.floating_molecule_type)
        mt = get_root_aggregate(IMoleculeType).get_by_id(
                                                        MOLECULE_TYPE_IDS.SIRNA)
        pl.set_floating_molecule_type(mt)
        self.assert_equal(pl.floating_molecule_type, mt)
        self._expect_error(TypeError, pl.set_floating_molecule_type,
                   'The molecule type must be a MoleculeType (obtained: str).',
                   **dict(molecule_type=MOLECULE_TYPE_IDS.MIRNA_INHI))

    def test_floating_stock_concentration(self):
        pl = self._create_test_layout()
        self.assert_is_none(pl.floating_stock_concentration)
        pl.set_floating_stock_concentration(50000)
        self.assert_equal(pl.floating_stock_concentration, 50000)
        conc_in_M = 50000 / CONCENTRATION_CONVERSION_FACTOR
        pl.set_floating_stock_concentration(conc_in_M)
        self.assert_equal(pl.floating_stock_concentration, 50000)
        self._expect_error(ValueError, pl.set_floating_stock_concentration,
                   'The stock concentration must be a positive number ' \
                   '(obtained: -4)', **dict(stock_concentration=-4))

    def test_close(self):
        pl = self._create_test_layout()
        empty_pos = pl.get_working_position(get_rack_position_from_label('g1'))
        self.assert_equal(len(pl), 7)
        self.assert_false(pl.is_closed)
        pl.close()
        self.assert_true(pl.is_closed)
        self.assert_equal(len(pl), 6)
        self.assert_is_none(pl.get_working_position(empty_pos.rack_position))
        self._expect_error(AttributeError, pl.add_position,
                           'The layout is closed!',
                           **dict(working_position=empty_pos))

    def test_create_rack_layout(self):
        pl = self._create_test_layout()
        self.assert_false(pl.is_closed)
        rl = pl.create_rack_layout()
        self.assert_true(pl.is_closed)
        self._compare_pos_sets(rl.get_positions(), pl.get_positions())
        self._compare_tag_sets(rl.get_tags(), pl.get_tags())

    def test_has_floating(self):
        pl = self._create_test_layout()
        self.assert_true(pl.has_floatings())
        pl.del_position(get_rack_position_from_label('b1'))
        self.assert_false(pl.has_floatings())

    def test_get_floating_positions(self):
        self.pos_data['a1'] = ['floating', 'md_1']
        self.pos_data['c1'] = ['floating', 'md_2']
        pl = self._create_test_layout()
        floating_map = pl.get_floating_positions()
        pos_labels = ['a1', 'b1', 'c1']
        pos_map = dict()
        for pos_label in pos_labels:
            pp = pl.get_working_position(get_rack_position_from_label(pos_label))
            pos_map[pos_label] = pp
        exp_map = {
            'md_1' : [pos_map['a1'], pos_map['b1']], 'md_2' : [pos_map['c1']]}
        self.assert_equal(floating_map, exp_map)


class _MoleculeDesignPoolLayoutConverterDummy(MoleculeDesignPoolLayoutConverter):
    """
    A dummy class that allows testing while circumventing the abstract class
    restriction.
    """

    PARAMETER_SET = MoleculeDesignPoolParameters
    LAYOUT_CLS = _MoleculeDesignPoolLayoutDummy
    POSITION_CLS = _MoleculeDesignPoolPositionDummy


class MoleculeDesignPoolConverterTestCase(ConverterTestCase,
                                          MoleculeDesignPoolBaseTestCase):

    PARAMETER_SET = MoleculeDesignPoolParameters
    POS_CLS = _MoleculeDesignPoolPositionDummy
    LAYOUT_CLS = _MoleculeDesignPoolLayoutDummy
    CONVERTER_CLS = _MoleculeDesignPoolLayoutConverterDummy

    def set_up(self):
        ConverterTestCase.set_up(self)
        self.pos_set_data = {1 : ['a1', 'a2'], 2 : ['b1'], 3 : ['c1'],
                             4 : ['d1'], 5 : ['e1'], 6 : ['f1'],
                             7 : ['g1'], 8 : ['a1', 'b1', 'c1']}
        # Do not alter tag attributes but overwrite the index!
        self.tag_data = {
            1 : [self.TYPE_TAGS['fixed'], self.POOL_TAGS['fixed']],
            2 : [self.TYPE_TAGS['floating'], self.POOL_TAGS['floating']],
            3 : [self.TYPE_TAGS['mock'], self.POOL_TAGS['mock']],
            4 : [self.TYPE_TAGS['library'], self.POOL_TAGS['library']],
            5 : [self.TYPE_TAGS['untreated'], self.POOL_TAGS['untreated']],
            6 : [self.TYPE_TAGS['untransfected'],
                 self.POOL_TAGS['untransfected']],
            7 : [self.TYPE_TAGS['empty']],
            8 : [Tag('some', 'other', 'data')]}

    def tear_down(self):
        ConverterTestCase.tear_down(self)

    def __remove_type_tags(self):
        for i in range(7):
            num = i + 1
            del self.tag_data[num][0]
            if len(self.tag_data[num]) < 1:
                del self.tag_data[num]
                del self.pos_set_data[num]

    def _get_all_positions(self):
        positions = []
        for i in range(4):
            positions.extend(self.pos_set_data[i + 1])
        return positions

    def _get_all_tags(self):
        tags = []
        for pos_type in (FIXED_POSITION_TYPE, FLOATING_POSITION_TYPE,
                         MOCK_POSITION_TYPE, LIBRARY_POSITION_TYPE):
            tags.append(self.TYPE_TAGS[pos_type])
            tags.append(self.POOL_TAGS[pos_type])
        return tags

    def _test_tag_for_position(self, layout):
        rack_pos = get_rack_position_from_label('a1')
        exp_tags = [self.TYPE_TAGS['fixed'], self.POOL_TAGS['fixed']]
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

    def test_result_with_pos_type(self):
        self._test_result()

    def test_result_without_pos_type(self):
        self.__remove_type_tags()
        self._test_result()

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_missing_pool(self):
        self.tag_data[1] = [self.TYPE_TAGS['fixed']]
        self._continue_setup()
        self._test_and_expect_errors('Some position have non-empty position ' \
                            'types although there is no pool for them: A1, A2')

    def test_unknown_position_type(self):
        tag = Tag(self.PARAMETER_SET.DOMAIN,
                  self.PARAMETER_SET.MOLECULE_DESIGN_POOL, 'invalid')
        self.tag_data[5] = [tag]
        self._continue_setup()
        self._test_and_expect_errors('Unknown or unsupported position types ' \
             'for the following pool IDs: invalid. Supported position types: ' \
             'empty, fixed, floating, library, mock, untransfected, untreated')

    def test_type_mismatch(self):
        self.tag_data[5] = [self.TYPE_TAGS['untransfected'],
                            self.POOL_TAGS['library']]
        self.tag_data[6] = [self.TYPE_TAGS['library'], self.POOL_TAGS['mock']]
        self.tag_data[7] = [self.TYPE_TAGS['mock'], self.POOL_TAGS['untreated']]
        self._continue_setup()
        self._test_and_expect_errors('The pool IDs and position types for ' \
                 'the following pools do not match: pool library (expected: ' \
                 'library, found: untransfected), pool mock (expected: mock, ' \
                 'found: library), pool untreated (expected: ' \
                 'None/NONE/UNTRANSFECTED/UNTREATED, found: mock)')

    def test_unknown_pool(self):
        self.tag_data[1] = [Tag(self.PARAMETER_SET.DOMAIN,
                                self.PARAMETER_SET.MOLECULE_DESIGN_POOL, '1')]
        self._continue_setup()
        self._test_and_expect_errors()


class TransferTargetTestCase(ToolsAndUtilsTestCase):

    test_cls = TransferTarget

    def _get_init_data(self):
        return dict(rack_position=get_rack_position_from_label('a1'),
                    transfer_volume=5,
                    target_rack_marker='prep1')

    def _get_object(self, attrs):
        return self.test_cls(**attrs)

    def _check_object(self, attrs, tt=None):
        if tt is None: tt = self._get_object(attrs)
        self.assert_is_not_none(tt)
        exp_attrs = {}
        for attr_name, value in attrs.iteritems():
            if attr_name == 'rack_position':
                if isinstance(value, RackPosition):
                    value = value.label
                attr_name = 'position_label'
            elif attr_name == 'transfer_volume':
                value = float(value)
            exp_attrs[attr_name] = value
        check_attributes(tt, exp_attrs)

    def test_init(self):
        attrs = self._get_init_data()
        self._check_object(attrs)
        attrs['rack_position'] = 'A1'
        self._check_object(attrs)
        attrs['transfer_volume'] = str(attrs['transfer_volume'])
        self._check_object(attrs)
        attrs['target_rack_marker'] = None
        self._check_object(attrs)
        ori_pos = attrs['rack_position']
        attrs['rack_position'] = 3
        self._expect_error(TypeError, self.test_cls,
               'The rack position must be a RackPosition or a string ' \
               '(obtained: int).', **attrs)
        attrs['rack_position'] = ori_pos
        ori_vol = attrs['transfer_volume']
        attrs['transfer_volume'] = -2
        self._expect_error(ValueError, self.test_cls,
               'The transfer volume must be a positive number (obtained: -2).',
               **attrs)
        attrs['transfer_volume'] = ori_vol
        attrs['target_rack_marker'] = 3
        self._expect_error(TypeError, self.test_cls,
                   'The target rack marker must be string (obtained: int)!',
                   **attrs)

    def test_hash_value(self):
        attrs = self._get_init_data()
        tt1 = self._get_object(attrs)
        self.assert_equal(tt1.hash_value, 'A1prep1')
        attrs['target_rack_marker'] = None
        tt2 = self._get_object(attrs)
        self.assert_equal(tt2.hash_value, 'A1')

    def test_target_info(self):
        attrs = self._get_init_data()
        tt1 = self._get_object(attrs)
        self.assert_equal(tt1.target_info, 'A1:5:prep1')
        attrs['target_rack_marker'] = None
        tt2 = self._get_object(attrs)
        self.assert_equal(tt2.target_info, 'A1:5')

    def test_parse_info(self):
        info1 = 'A1:5:prep1'
        tt1 = TransferTarget.parse_info_string(info1)
        attrs = self._get_init_data()
        self._check_object(attrs, tt1)
        info2 = 'A1:5'
        tt2 = TransferTarget.parse_info_string(info2)
        attrs['target_rack_marker'] = None
        self._check_object(attrs, tt2)
        info3 = info2.replace(':', '_')
        self._expect_error(ValueError, TransferTarget.parse_info_string,
               'Could not find ":" delimiter in info string (obtained: A1_5!)',
               **dict(info_string=info3))


class _TransferParameterDummy(TransferParameters):
    """
    This dummy class has one mandatory and one optional transfer target group.
    """
    MANDATORY_TARGETS = 'mandatory_targets'
    ALL = TransferParameters.ALL + [MANDATORY_TARGETS]
    REQUIRED = TransferParameters.REQUIRED + [MANDATORY_TARGETS]
    TRANSFER_TARGET_PARAMETERS = TransferParameters.TRANSFER_TARGET_PARAMETERS \
                                 + [MANDATORY_TARGETS]
    MUST_HAVE_TRANSFER_TARGETS = {TransferParameters.TRANSFER_TARGETS : False,
                                  MANDATORY_TARGETS : True}
    ALIAS_MAP = dict(TransferParameters.ALIAS_MAP, **{MANDATORY_TARGETS : []})
    DOMAIN_MAP = dict(TransferParameters.DOMAIN_MAP,
                      **{MANDATORY_TARGETS : 'test'})


class _TransferPositionDummy(TransferPosition):
    """
    This dummy class allows to test the transfer position. It serves
    to come around the abstract class initialisation and tests both mandatory
    and optional transfer transfer targets.
    """

    PARAMETER_SET = _TransferParameterDummy

    def __init__(self, rack_position, mandatory_targets, position_type=None,
                 molecule_design_pool=None, transfer_targets=None):
        TransferPosition.__init__(self, rack_position=rack_position,
                                  molecule_design_pool=molecule_design_pool,
                                  position_type=position_type,
                                  transfer_targets=transfer_targets)
        self._check_transfer_targets(self.PARAMETER_SET.MANDATORY_TARGETS,
                              mandatory_targets, name='mandatory target')
        self.mandatory_targets = mandatory_targets

    def _get_parameter_values_map(self):
        parameters = TransferPosition._get_parameter_values_map(self)
        parameters[self.PARAMETER_SET.MANDATORY_TARGETS] = \
                                                    self.mandatory_targets
        return parameters

    def _get_transfer_target_map(self):
        return {self.PARAMETER_SET.TRANSFER_TARGETS : self.transfer_targets,
                self.PARAMETER_SET.MANDATORY_TARGETS : self.mandatory_targets}


class _TransferLayoutDummy(TransferLayout):
    """
    This dummy class allows to test the transfer layouts. It circumvents the
    abstract class restriction and tests both mandatory and optional
    transfer transfer targets.
    """
    POSITION_CLS = _TransferPositionDummy
    _TRANSFER_TARGET_PARAMETERS = _TransferParameterDummy.\
                                  TRANSFER_TARGET_PARAMETERS
    ALLOW_DUPLICATE_TARGET_WELLS = {
                    POSITION_CLS.PARAMETER_SET.TRANSFER_TARGETS : False,
                    POSITION_CLS.PARAMETER_SET.MANDATORY_TARGETS: True}


class _TransferClassesBaseTestCase(MoleculeDesignPoolBaseTestCase):

    POS_CLS = _TransferPositionDummy
    LAYOUT_CLS = _TransferLayoutDummy

    POOL_TAGS = {
        'fixed' : Tag('molecule_design_pool', 'molecule_design_pool_id',
                   '205200'),
        'floating' : Tag('molecule_design_pool', 'molecule_design_pool_id',
                         'md_1'), }
    TYPE_TAGS = {
            'fixed' : Tag('molecule_design_pool', 'position_type', 'fixed'),
            'floating' : Tag('molecule_design_pool', 'position_type',
                             'floating')}
    POS_TYPES = (FIXED_POSITION_TYPE, FLOATING_POSITION_TYPE)

    _TT_INFOS = {1 : 'A2:1:prep1', 2 : 'B2:1:prep1', 3 : 'C2:1:prep2',
                 4 : 'D2:1:prep2'}

    _TT_TAG_VALUES = dict(a1='C2:1:prep2-D2:1:prep2', b1=None)
    _MT_TAG_VALUES = dict(a1=_TT_INFOS[1], b1=_TT_INFOS[2])

    def set_up(self):
        MoleculeDesignPoolBaseTestCase.set_up(self)
        self.tts = {1 : TransferTarget(rack_position='a2', transfer_volume=1,
                                       target_rack_marker='prep1'),
                    2 : TransferTarget(rack_position='b2', transfer_volume=1,
                                       target_rack_marker='prep1'),
                    3 : TransferTarget(rack_position='c2', transfer_volume=1,
                                       target_rack_marker='prep2'),
                    4 : TransferTarget(rack_position='d2', transfer_volume=1,
                                       target_rack_marker='prep2')}
        #: pos label - pos type, pool, mandatory tts, optinal tt1
        self.pos_data = dict(
                a1=['fixed', get_root_aggregate(IMoleculeDesignPool).get_by_id(
                            205200), [self.tts[1]], [self.tts[3], self.tts[4]]],
                b1=['floating', 'md_1', [self.tts[2]], []])

    def tear_down(self):
        MoleculeDesignPoolBaseTestCase.tear_down(self)
        del self.tts

    def _get_init_data(self, pos_label):
        kw = MoleculeDesignPoolBaseTestCase._get_init_data(self, pos_label)
        pos_data = self.pos_data[pos_label]
        kw['mandatory_targets'] = pos_data[2]
        kw['transfer_targets'] = pos_data[3]
        return kw

    def _get_tt_tag(self, pos_label):
        value = self._TT_TAG_VALUES[pos_label]
        if value is None: return None
        return Tag('sample_transfer', 'transfer_targets', value)

    def _get_mt_tag(self, pos_label):
        value = self._MT_TAG_VALUES[pos_label]
        return Tag('test', 'mandatory_targets', value)

    def _get_tags(self, pos_label):
        tags = MoleculeDesignPoolBaseTestCase._get_tags(self, pos_label)
        tt_tag = self._get_tt_tag(pos_label)
        if not tt_tag is None: tags.add(tt_tag)
        tags.add(self._get_mt_tag(pos_label))
        return tags


class TransferParametersTestCase(_TransferClassesBaseTestCase):

    def test_must_have_transfer_targets(self):
        params = _TransferParameterDummy
        self.assert_true(params.must_have_transfer_targets(
                         params.MANDATORY_TARGETS))
        self.assert_false(params.must_have_transfer_targets(
                          params.TRANSFER_TARGETS))
        self._expect_error(KeyError, params.must_have_transfer_targets, '',
                           **dict(parameter_name='inv'))


class TransferPositionTestCase(_TransferClassesBaseTestCase):

    def test_init(self):
        self._test_position_init()
        attrs = self._get_init_data('a1')
        attrs['transfer_targets'] = None
        tp = self.POS_CLS(**attrs)
        self.assert_is_not_none(tp)
        attrs['transfer_targets'] = []
        check_attributes(tp, attrs)
        attrs['mandatory_targets'] = None
        self._expect_error(ValueError, self.POS_CLS,
               'A _TransferPositionDummy must have at least one mandatory ' \
               'target!', **attrs)
        attrs['mandatory_targets'] = []
        self._expect_error(ValueError, self.POS_CLS,
               'A _TransferPositionDummy must have at least one mandatory ' \
               'target!', **attrs)
        attrs['mandatory_targets'] = self.tts[1]
        self._expect_error(TypeError, self.POS_CLS,
                'The mandatory targets must be passed as list (obtained: ' \
                'TransferTarget).', **attrs)
        attrs['mandatory_targets'] = [1]
        self._expect_error(TypeError, self.POS_CLS,
               'The mandatory target must be TransferTarget objects ' \
               '(obtained: int).', **attrs)
        del attrs['mandatory_targets']
        self._expect_error(NotImplementedError, TransferPosition,
                           'Abstract class', **attrs)

    def test_equality(self):
        irr_values = dict(transfer_targets=[self.tts[1]],
                          mandatory_targets=[self.tts[3]])
        self._test_position_equality({}, irr_values)

    def test_get_transfer_target_list(self):
        tp = self._get_position('a1')
        params = _TransferParameterDummy
        self.assert_equal(tp.get_transfer_target_list(params.TRANSFER_TARGETS),
                          [self.tts[3], self.tts[4]])
        self.assert_equal(tp.get_transfer_target_list(params.MANDATORY_TARGETS),
                          [self.tts[1]])
        tp.transfer_targets = []
        self.assert_equal(tp.get_transfer_target_list(params.TRANSFER_TARGETS),
                          [])

    def test_add_transfer_target(self):
        tp = self._get_position('a1')
        self.assert_equal(tp.mandatory_targets, [self.tts[1]])
        self.assert_equal(tp.transfer_targets, [self.tts[3], self.tts[4]])
        tp.add_transfer_target(self.tts[2],
                               _TransferParameterDummy.MANDATORY_TARGETS)
        self.assert_equal(tp.mandatory_targets, [self.tts[1], self.tts[2]])
        self.assert_equal(tp.transfer_targets, [self.tts[3], self.tts[4]])
        tp.add_transfer_target(self.tts[2])
        self.assert_equal(tp.mandatory_targets, [self.tts[1], self.tts[2]])
        self.assert_equal(tp.transfer_targets, [self.tts[3], self.tts[4],
                                                self.tts[2]])
        self._expect_error(TypeError, tp.add_transfer_target,
                'Transfer targets wells must be TransferTarget objects ' \
                '(obtained: 1, type: int)', **dict(transfer_target=1))
        # test duplicate hash
        self._expect_error(ValueError, tp.add_transfer_target,
                           'Duplicate target position B2prep1', self.tts[2])

    def test_get_targets_tag_value(self):
        tp = self._get_position('a1')
        self.assert_equal(tp.get_targets_tag_value(),
                          self._TT_TAG_VALUES['a1'])
        self.assert_equal(self._MT_TAG_VALUES['a1'], tp.get_targets_tag_value(
                          _TransferParameterDummy.MANDATORY_TARGETS))
        self._expect_error(ValueError, tp.get_targets_tag_value,
                           'Parameter "inv" is no transfer target parameter!',
                           **dict(parameter_name='inv'))

    def test_get_targets_tag(self):
        tp = self._get_position('a1')
        tt_tag = self._get_tt_tag('a1')
        mt_tag = self._get_mt_tag('a1')
        self.assert_equal(tp.get_targets_tag(
                          _TransferParameterDummy.TRANSFER_TARGETS), tt_tag)
        self.assert_equal(tp.get_targets_tag(
                          _TransferParameterDummy.MANDATORY_TARGETS), mt_tag)
        tp.transfer_targets = []
        self.assert_is_none(tp.get_targets_tag(
                            _TransferParameterDummy.TRANSFER_TARGETS))
        self._expect_error(ValueError, tp.get_targets_tag,
               'Parameter "inv" is no transfer target parameter!',
               **dict(parameter_name='inv'))
        tp.mandatory_targets = []
        self._expect_error(AttributeError, tp.get_targets_tag,
                'There are no transfer targets for the mandatory transfer ' \
                'parameter "mandatory_targets"!',
                _TransferParameterDummy.MANDATORY_TARGETS)

    def test_parse_tag_value(self):
        value = 'C2:1:prep2-D2:1:prep2'
        exp_tts = [self.tts[3], self.tts[4]]
        self.assert_equal(exp_tts,
                          TransferPosition.parse_target_tag_value(value))
        value_dup = 'C2:1:prep2-C2:1:prep2'
        self._expect_error(ValueError, TransferPosition.parse_target_tag_value,
                           'Duplicate transfer target: C2prep2',
                           **dict(target_tag_value=value_dup))

    def test_get_parameter_tag(self):
        tp = self._get_position('b1')
        self.assert_equal(tp.get_parameter_tag(
                          _TransferParameterDummy.MOLECULE_DESIGN_POOL),
                          self.POOL_TAGS[tp.position_type])
        self.assert_is_none(tp.get_parameter_tag(
                            _TransferParameterDummy.TRANSFER_TARGETS))
        self.assert_equal(self._get_mt_tag('b1'), tp.get_parameter_tag(
                          _TransferParameterDummy.MANDATORY_TARGETS))

    def test_get_tag_set(self):
        self._test_position_get_tag_set()


class TransferLayoutTestCase(_TransferClassesBaseTestCase):

    def test_init(self):
        self._test_layout_init()

    def test_add_and_del_position(self):
        tl = self._init_layout()
        self.assert_equal(len(tl), 0)
        tp1 = self._get_position('a1')
        tl.add_position(tp1)
        self.assert_equal(len(tl), 1)
        self.pos_data['b1'] = self.pos_data['a1']
        tp2 = self._get_position('b1')
        self._expect_error(ValueError, tl.add_position,
                           'Duplicate target well C2prep2!',
                           **dict(working_position=tp2))
        tl.del_position(tp1.rack_position)
        self.assert_equal(len(tl), 0)
        tl.add_position(tp2)
        self.assert_equal(len(tl), 1)

    def test_duplicate_targets(self):
        tl = self._init_layout()
        tp1 = self._get_position('a1')
        tl.add_position(tp1)
        tp2 = self._get_position('b1')
        tp2.transfer_targets = tp1.transfer_targets
        self._expect_error(ValueError, tl.add_position,
                           'Duplicate target well C2prep2!',
                           **dict(working_position=tp2))
        tp2.transfer_targets = []
        tp2.mandatory_targets = tp1.mandatory_targets
        tl.add_position(tp2)
        self.assert_equal(len(tl), 2)


class _TransferLayoutConverterDummy(TransferLayoutConverter):
    """
    This dummy class allows to test the transfer layout converters. It
    circumvents the abstract class restriction and tests both mandatory and
    optional transfer transfer targets.
    """

    PARAMETER_SET = _TransferParameterDummy
    LAYOUT_CLS = _TransferLayoutDummy
    POSITION_CLS = _TransferPositionDummy

    def _get_position_init_values(self, parameter_map, rack_pos):
        kw = TransferLayoutConverter._get_position_init_values(self,
                                            parameter_map, rack_pos)
        if kw is None: return None

        mt_tag_value = parameter_map[self.PARAMETER_SET.MANDATORY_TARGETS]
        tts = self._parse_target_tag_value(mt_tag_value, rack_pos,
                                           self.PARAMETER_SET.MANDATORY_TARGETS)
        if tts is None: return None # an error has occurred
        kw['mandatory_targets'] = tts
        return kw


class TransferLayoutConverterTestCase(ConverterTestCase,
                                      _TransferClassesBaseTestCase):

    PARAMETER_SET = _TransferParameterDummy
    POS_CLS = _TransferPositionDummy
    LAYOUT_CLS = _TransferLayoutDummy
    CONVERTER_CLS = _TransferLayoutConverterDummy

    def set_up(self):
        ConverterTestCase.set_up(self)
        self.pos_set_data = {1 : ['a1'], 2: ['b1'], 3 : ['a1', 'b1']}
        self.tag_data = {
                1 : [self._get_mt_tag('a1'), self._get_tt_tag('a1')],
                2 : [self._get_mt_tag('b1')],
                3 : [Tag('some', 'more', 'data'), self.POOL_TAGS['fixed'],
                     self.TYPE_TAGS['fixed']]}

    def tear_down(self):
        ConverterTestCase.tear_down(self)

    def test_result(self):
        self._test_result()

    def _get_all_tags(self):
        tags = [self.TYPE_TAGS['fixed'], self.POOL_TAGS['fixed']]
        tags.extend(self.tag_data[1])
        tags.extend(self.tag_data[2])
        return tags

    def _test_tag_for_position(self, layout):
        rack_pos = get_rack_position_from_label('b1')
        exp_tags = [self._get_mt_tag('b1'), self.TYPE_TAGS['fixed'],
                    self.POOL_TAGS['fixed']]
        tag_set = layout.get_tags_for_position(rack_pos)
        self._compare_tag_sets(exp_tags, tag_set)

    def _test_position_for_tag(self, layout):
        tag = self.TYPE_TAGS['fixed']
        exp_positions = ['a1', 'b1']
        pos_set = layout.get_positions_for_tag(tag)
        self._compare_pos_sets(exp_positions, pos_set)
        tag2 = self._get_mt_tag('a1')
        exp_positions2 = ['a1']
        pos_set2 = layout.get_positions_for_tag(tag2)
        self._compare_pos_sets(exp_positions2, pos_set2)

    def test_invalid_tag_string(self):
        mt_tag = self._get_mt_tag('b1')
        mt_tag.value = 'invalid'
        self.tag_data[2] = [mt_tag]
        self._continue_setup()
        self._test_and_expect_errors('The following rack positions have ' \
            'invalid target position descriptions: parameter "mandatory ' \
            'targets": "invalid" (B1)')

    def test_missing_targets(self):
        self.tag_data[1] = [self._get_tt_tag('a1')]
        self._continue_setup()
        self._test_and_expect_errors('Position of this type ' \
             '(_TransferPositionDummy) must have certain transfer targets. ' \
             'The transfer targets are missing for the following positions: ' \
             'parameter "mandatory targets": A1')

    def test_duplicate_targets(self):
        self.tag_data[2] = [self._get_mt_tag('b1'), self._get_tt_tag('a1')]
        self._continue_setup()
        self._test_and_expect_errors('There are duplicate target positions: ' \
                                     'parameter "transfer targets": "prep2-C2"')


class LibraryLayoutPositionTestCase(ToolsAndUtilsTestCase):

    test_cls = LibraryLayoutPosition

    def __get_init_data(self):
        rack_pos = get_rack_position_from_label('a1')
        is_library_pos = True
        return dict(rack_position=rack_pos, is_library_position=is_library_pos)

    def test_init(self):
        attrs = self.__get_init_data()
        lp = self.test_cls(**attrs)
        self.assert_is_not_none(lp)
        check_attributes(lp, attrs)
        del attrs['is_library_position']
        lp2 = self.test_cls(**attrs)
        attrs['is_library_position'] = True
        self.assert_is_not_none(lp2)
        check_attributes(lp2, attrs)
        attrs['is_library_position'] = None
        self._expect_error(TypeError, self.test_cls,
                'The "library position" flag must be a bool (obtained: ' \
                'NoneType).', **attrs)

    def test_equality(self):
        attrs = self.__get_init_data()
        lp1 = self.test_cls(**attrs)
        lp2 = self.test_cls(**attrs)
        lp3 = self.test_cls(**attrs)
        lp3.is_library_position = False
        lp4 = self.test_cls(**attrs)
        lp4.rack_position = get_rack_position_from_label('g8')
        self.assert_equal(lp1, lp2)
        self.assert_not_equal(lp1, lp3)
        self.assert_not_equal(lp1, lp4)
        self.assert_not_equal(lp1, 1)


class LibraryLayoutTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.pos_data = dict(a1=True, a2=False, b1=True)

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.pos_data

    def __create_test_layout(self):
        layout = LibraryLayout(shape=get_96_rack_shape())
        for pos_label, is_lib_pos in self.pos_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            lp = LibraryLayoutPosition(rack_position=rack_pos,
                                       is_library_position=is_lib_pos)
            layout.add_position(lp)
        return layout

    def test_close(self):
        ll = self.__create_test_layout()
        self.assert_equal(len(ll), 3)
        self.assert_false(ll.is_closed)
        a2_pos = get_rack_position_from_label('a2')
        a2_lp = ll.get_working_position(a2_pos)
        self.assert_is_not_none(a2_lp)
        ll.close()
        self.assert_true(ll.is_closed)
        self.assert_equal(len(ll), 2)
        self.assert_is_none(ll.get_working_position(a2_pos))
        self._expect_error(AttributeError, ll.add_position,
                       'The layout is closed!', **dict(working_position=a2_lp))

    def test_create_rack_layout(self):
        ll = self.__create_test_layout()
        self.assert_false(ll.is_closed)
        rl = ll.create_rack_layout()
        self.assert_true(ll.is_closed)
        self._compare_pos_sets(ll.get_positions(), rl.get_positions())
        self._compare_tag_sets(ll.get_tags(), rl.get_tags())
        self.assert_equal(len(rl.tagged_rack_position_sets), 1)


class LibraryLayoutConverterTestCase(ConverterTestCase):

    PARAMETER_SET = LibraryLayoutParameters
    POS_CLS = LibraryLayoutPosition
    LAYOUT_CLS = LibraryLayout
    CONVERTER_CLS = LibraryLayoutConverter

    def set_up(self):
        ConverterTestCase.set_up(self)
        self.pos_set_data = {1 : ['a1', 'a2'],
                             2 : ['b1'],
                             3 : ['c1']}
        params = self.PARAMETER_SET
        self.tag_data = {
                1 : [Tag(params.DOMAIN, params.IS_LIBRARY_POS, 'True'),
                     Tag('some', 'other', 'things')],
                2 : [Tag(params.DOMAIN, params.IS_LIBRARY_POS, 'False')],
                3 : [Tag('some', 'other', 'stuff')]}

    def test_result(self):
        ll = self._test_result()
        self.assert_true(ll.is_closed)

    def _get_all_positions(self):
        return self.pos_set_data[1]

    def _get_all_tags(self):
        return [self.tag_data[1][0]]

    def _test_tag_for_position(self, layout):
        a1_pos = get_rack_position_from_label('a1')
        lp = layout.get_working_position(a1_pos)
        self.assert_true(lp.is_library_position)
        c1_pos = get_rack_position_from_label('c3')
        self.assert_is_none(layout.get_working_position(c1_pos))

    def _test_position_for_tag(self, layout):
        tag1 = self.tag_data[1][0]
        exp_positions = self.pos_set_data[1]
        pos_set = layout.get_positions_for_tag(tag1)
        self._compare_pos_sets(exp_positions, pos_set)
        tag2 = self.tag_data[1][1]
        pos_set2 = layout.get_positions_for_tag(tag2)
        self.assert_equal(len(pos_set2), 0)

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_invalid_library_value(self):
        self.tag_data[2][0].value = 'default'
        self._continue_setup()
        self._test_and_expect_errors('The "library position" flag must be ' \
                 'a boolean. The values for some positions are invalid. ' \
                 'Details: B1 (default)')
