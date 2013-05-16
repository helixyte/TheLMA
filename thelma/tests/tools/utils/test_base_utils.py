"""
tool base utils testing

AAB Aug 12, 2011
"""

from everest.entities.utils import get_root_aggregate
from everest.testing import check_attributes
from thelma.automation.tools.semiconstants import get_384_rack_shape
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_positions_for_shape
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.utils.base import EMPTY_POSITION_TYPE
from thelma.automation.tools.utils.base import EmptyPositionManager
from thelma.automation.tools.utils.base import FIXED_POSITION_TYPE
from thelma.automation.tools.utils.base import FLOATING_POSITION_TYPE
from thelma.automation.tools.utils.base import MOCK_POSITION_TYPE
from thelma.automation.tools.utils.base import MoleculeDesignPoolLayout
from thelma.automation.tools.utils.base import MoleculeDesignPoolParameters
from thelma.automation.tools.utils.base import MoleculeDesignPoolPosition
from thelma.automation.tools.utils.base import TransferLayout
from thelma.automation.tools.utils.base import TransferParameters
from thelma.automation.tools.utils.base import TransferPosition
from thelma.automation.tools.utils.base import TransferTarget
from thelma.automation.tools.utils.base import UNTREATED_POSITION_TYPE
from thelma.automation.tools.utils.base import WorkingLayout
from thelma.automation.tools.utils.base import WorkingPosition
from thelma.automation.tools.utils.base import add_list_map_element
from thelma.automation.tools.utils.base import create_in_term_for_db_queries
from thelma.automation.tools.utils.base import get_converted_number
from thelma.automation.tools.utils.base import get_trimmed_string
from thelma.automation.tools.utils.base import is_valid_number
from thelma.automation.tools.utils.base import round_up
from thelma.automation.tools.utils.base import sort_rack_positions
from thelma.automation.tools.utils.iso import IsoPosition
from thelma.automation.tools.worklists.base \
    import CONCENTRATION_CONVERSION_FACTOR
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import IMoleculeType
from thelma.models.moleculetype import MOLECULE_TYPE_IDS
from thelma.models.tagging import Tag
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase


class WorkingPositionTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.rack_pos = get_rack_position_from_label('A1')

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.rack_pos

    def test_working_position_init(self):
        wp1 = WorkingPosition(self.rack_pos)
        self.assert_false(wp1 is None)
        self.assert_equal(wp1.rack_position, self.rack_pos)
        self.assert_raises(ValueError, WorkingPosition, None)


class WorkingLayoutTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.shape = get_96_rack_shape()

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.shape

    def test_working_layout_init(self):
        ToolsAndUtilsTestCase.set_up(self)
        wl1 = WorkingLayout(shape=self.shape)
        self.assert_false(wl1 is None)
        self.assert_equal(wl1.shape, self.shape)
        self.assert_equal(len(wl1), 0)
        tup = (wl1, 'user')
        self.assert_raises(AttributeError, getattr, *tup)


class ToolUtilsFunctionsTestCase(ToolsAndUtilsTestCase):

    def test_rack_position_sorting(self):
        a1_pos = get_rack_position_from_label('A1')
        a2_pos = get_rack_position_from_label('A2')
        a10_pos = get_rack_position_from_label('A10')
        a12_pos = get_rack_position_from_label('A12')
        b1_pos = get_rack_position_from_label('B1')
        test_list = [b1_pos, a10_pos, a2_pos, a12_pos, a1_pos]
        sorted_list = sort_rack_positions(test_list)
        self.assert_equal(len(sorted_list), len(test_list))
        self.assert_equal(sorted_list[0], a1_pos)
        self.assert_equal(sorted_list[1], a2_pos)
        self.assert_equal(sorted_list[2], a10_pos)
        self.assert_equal(sorted_list[3], a12_pos)
        self.assert_equal(sorted_list[4], b1_pos)

    def test_is_valid_number(self):
        self.assert_true(is_valid_number('4'))
        self.assert_true(is_valid_number('4.0'))
        self.assert_true(is_valid_number(4))
        self.assert_true(is_valid_number(4.2))
        self.assert_false(is_valid_number('0'))
        self.assert_false(is_valid_number(-4))
        self.assert_false(is_valid_number('-4'))
        self.assert_true(is_valid_number(-4, positive=False))
        self.assert_true(is_valid_number('-4', positive=False))
        self.assert_true(is_valid_number('0', may_be_zero=True))
        self.assert_true(is_valid_number('4', may_be_zero=True))
        self.assert_true(is_valid_number('-4', may_be_zero=True,
                                         positive=False))
        self.assert_true(is_valid_number('4', is_integer=True))
        self.assert_true(is_valid_number('4.0', is_integer=True))
        self.assert_false(is_valid_number('4.2', is_integer=True))
        self.assert_false(is_valid_number(4.2, is_integer=True))

    def test_get_converted_number(self):
        self.assert_equal(get_converted_number('4'), 4.0)
        self.assert_equal(get_converted_number('4.2'), 4.2)
        self.assert_equal(get_converted_number('4', is_integer=True), 4)
        self.assert_equal(get_converted_number('4.2', is_integer=True), '4.2')
        self.assert_equal(get_converted_number(4), 4)
        self.assert_equal(get_converted_number(4.2), 4.2)
        self.assert_equal(get_converted_number('test'), 'test')

    def test_get_trimmed_string(self):
        self.assert_equal(get_trimmed_string(4), '4')
        self.assert_equal(get_trimmed_string(4.0), '4')
        self.assert_equal(get_trimmed_string('test:value'), 'test:value')

    def test_round_up(self):
        self.assert_equal(round_up(1.344), 1.4)
        self.assert_equal(round_up(1.1), 1.1)
        self.assert_equal(round_up(1.344, decimal_places=2), 1.35)
        self.assert_equal(round_up(84.1, 0), 85)

    def test_create_in_term_for_db_queries(self):
        values = [3, 4]
        self.assert_equal(create_in_term_for_db_queries(values), '(3, 4)')
        self.assert_equal(create_in_term_for_db_queries(values, as_string=True),
                          '(\'3\', \'4\')')

    def test_add_list_map_element(self):
        value_map = dict()
        self.assert_equal(len(value_map), 0)
        add_list_map_element(value_map, 1, 'string1')
        self.assert_equal(len(value_map), 1)
        self.assert_equal(value_map[1], ['string1'])
        add_list_map_element(value_map, 1, 'string2')
        self.assert_equal(len(value_map), 1)
        self.assert_equal(value_map[1], ['string1', 'string2'])


class EmptyPositionManagerTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.rack_shape = get_96_rack_shape()

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.rack_shape

    def test_has_and_get_position(self):
        manager = EmptyPositionManager(rack_shape=self.rack_shape)
        for rack_pos in get_positions_for_shape(self.rack_shape):
            self.assert_true(manager.has_empty_positions())
            manager_pos = manager.get_empty_position()
            self.assert_equal(rack_pos, manager_pos)
        self.assert_false(manager.has_empty_positions())
        self.assert_raises(ValueError, manager.get_empty_position)

    def test_add_position(self):
        manager = EmptyPositionManager(rack_shape=self.rack_shape)
        a1_pos = get_rack_position_from_label('A1')
        first_pos = manager.get_empty_position()
        self.assert_equal(a1_pos, first_pos)
        second_pos = manager.get_empty_position()
        self.assert_not_equal(a1_pos, second_pos)
        self.assert_equal(second_pos.label, 'A2')
        manager.add_empty_position(a1_pos)
        third_pos = manager.get_empty_position()
        self.assert_equal(third_pos, a1_pos)


class MoleculeDesignPoolParametersTestCase(ToolsAndUtilsTestCase):

    def test_get_position_type(self):
        meth = MoleculeDesignPoolParameters.get_position_type
        pool = self._get_entity(IMoleculeDesignPool, '205200')
        self.assert_equal(meth(pool), FIXED_POSITION_TYPE)
        self.assert_equal(meth('md_1'), FLOATING_POSITION_TYPE)
        self.assert_equal(meth('mock'), MOCK_POSITION_TYPE)
        self.assert_equal(meth('untreated'), UNTREATED_POSITION_TYPE)
        self.assert_equals(meth(None), EMPTY_POSITION_TYPE)
        self.assert_raises(ValueError, meth, 1)
        self.assert_raises(ValueError, meth, 'fixed')


class MoleculeDesignPoolParametersDummy(MoleculeDesignPoolParameters):
    """
    This dummy class allows to test the transfer position. It only adds
    the domain map and the required and all lists that would normally be
    provided by the subclass implementation.
    """
    DOMAIN = 'molecule design pool'

    DOMAIN_MAP = {MoleculeDesignPoolParameters.MOLECULE_DESIGN_POOL : DOMAIN,
                  MoleculeDesignPoolParameters.POS_TYPE : DOMAIN}

    ALL = [MoleculeDesignPoolParameters.MOLECULE_DESIGN_POOL,
           MoleculeDesignPoolParameters.POS_TYPE]
    REQUIRED = [MoleculeDesignPoolParameters.MOLECULE_DESIGN_POOL]


class MoleculeDesignPoolPositionDummy(MoleculeDesignPoolPosition):
    """
    This dummy class allows to test the molecule design pool positions. It only
    provides a parameters with domains. It only serves to get around the
    abstract class.
    """
    PARAMETER_SET = MoleculeDesignPoolParametersDummy


class MoleculeDesignPoolWorkingTypeTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.pool = self._get_entity(IMoleculeDesignPool, '205200')
        self.pool_tag = Tag('molecule design pool', 'molecule_design_pool_id',
                            '205200')
        self.floating_md = 'md_1'
        self.floating_tag = Tag('molecule design pool',
                                'molecule_design_pool_id', self.floating_md)
        self.mock_tag = Tag('molecule design pool', 'molecule_design_pool_id',
                            'mock')
        self.a1_pos = get_rack_position_from_label('A1')
        self.b2_pos = get_rack_position_from_label('B1')
        self.c3_pos = get_rack_position_from_label('C3')
        self.d4_pos = get_rack_position_from_label('D4')
        self.e5_pos = get_rack_position_from_label('E5')

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.pool
        del self.pool_tag
        del self.floating_md
        del self.floating_tag
        del self.mock_tag
        del self.a1_pos
        del self.b2_pos
        del self.c3_pos
        del self.d4_pos
        del self.e5_pos

    def _get_fixed_pos_type_tag(self):
        return Tag('molecule design pool', 'position_type', 'fixed')

    def _get_floating_pos_type_tag(self):
        return Tag('molecule design pool', 'position_type', 'floating')

    def _get_mock_pos_type_tag(self):
        return Tag('molecule design pool', 'position_type', 'mock')

    def _get_empty_pos_type_tag(self):
        return Tag('molecule design pool', 'position_type', 'empty')

    def _get_untreated_pos_type_tag(self):
        return Tag('molecule design pool', 'position_type', 'untreated')

    def _get_untreated_pool_tag(self):
        return Tag('molecule design pool', 'molecule_design_pool_id',
                   'untreated')

    def _get_fixed_init_data(self):
        return dict(rack_position=self.a1_pos, molecule_design_pool=self.pool)

    def _get_floating_init_data(self):
        return dict(rack_position=self.b2_pos,
                    molecule_design_pool=self.floating_md)

    def _get_mock_init_data(self):
        return dict(rack_position=self.c3_pos,
                    molecule_design_pool=MOCK_POSITION_TYPE)

    def _get_untreated_init_data(self):
        return dict(rack_position=self.d4_pos,
                    molecule_design_pool=UNTREATED_POSITION_TYPE)

    def _get_empty_init_data(self):
        return dict(rack_position=self.e5_pos, molecule_design_pool=None)

    def _init_working_position(self, attrs):
        return MoleculeDesignPoolPositionDummy(**attrs)


class MoleculeDesignPoolPositionTestCase(MoleculeDesignPoolWorkingTypeTestCase):

    def test_init_molecule_design_pool_base_class(self):
        fixed_attrs = self._get_fixed_init_data()
        self.assert_raises(NotImplementedError, MoleculeDesignPoolPosition,
                           **fixed_attrs)

    def test_fixed(self):
        fixed_attrs = self._get_fixed_init_data()
        mp = self._init_working_position(fixed_attrs)
        self.assert_is_not_none(mp)
        fixed_attrs['position_type'] = FIXED_POSITION_TYPE
        check_attributes(mp, fixed_attrs)
        self.assert_true(mp.is_fixed)
        self.assert_false(mp.is_floating)
        self.assert_false(mp.is_mock)
        self.assert_false(mp.is_untreated)
        self.assert_false(mp.is_empty)
        self.assert_equal(mp.molecule_design_pool_id, self.pool.id)
        tags = [self.pool_tag, self._get_fixed_pos_type_tag()]
        tag_set = mp.get_tag_set()
        self._compare_tag_sets(tags, tag_set)

    def test_floating(self):
        float_attrs = self._get_floating_init_data()
        mp = self._init_working_position(float_attrs)
        self.assert_is_not_none(mp)
        float_attrs['position_type'] = FLOATING_POSITION_TYPE
        check_attributes(mp, float_attrs)
        self.assert_false(mp.is_fixed)
        self.assert_true(mp.is_floating)
        self.assert_false(mp.is_mock)
        self.assert_false(mp.is_untreated)
        self.assert_false(mp.is_empty)
        self.assert_equal(mp.molecule_design_pool_id, self.floating_md)
        tags = [self.floating_tag, self._get_floating_pos_type_tag()]
        tag_set = mp.get_tag_set()
        self._compare_tag_sets(tags, tag_set)

    def test_mock(self):
        mock_attrs = self._get_mock_init_data()
        mp = self._init_working_position(mock_attrs)
        self.assert_is_not_none(mp)
        mock_attrs['position_type'] = MOCK_POSITION_TYPE
        check_attributes(mp, mock_attrs)
        self.assert_false(mp.is_fixed)
        self.assert_false(mp.is_floating)
        self.assert_true(mp.is_mock)
        self.assert_false(mp.is_untreated)
        self.assert_false(mp.is_empty)
        self.assert_equal(mp.molecule_design_pool_id, MOCK_POSITION_TYPE)
        tags = [self._get_mock_pos_type_tag(), self.mock_tag]
        tag_set = mp.get_tag_set()
        self._compare_tag_sets(tags, tag_set)

    def test_untreated(self):
        untreated_attrs = self._get_untreated_init_data()
        mp = self._init_working_position(untreated_attrs)
        self.assert_is_not_none(mp)
        untreated_attrs['position_type'] = UNTREATED_POSITION_TYPE
        check_attributes(mp, untreated_attrs)
        self.assert_false(mp.is_fixed)
        self.assert_false(mp.is_floating)
        self.assert_false(mp.is_mock)
        self.assert_true(mp.is_untreated)
        self.assert_true(mp.is_empty)
        self.assert_equal(mp.molecule_design_pool_id, UNTREATED_POSITION_TYPE)
        tags = [self._get_untreated_pos_type_tag(),
                self._get_untreated_pool_tag()]
        tag_set = mp.get_tag_set()
        self._compare_tag_sets(tags, tag_set)

    def test_empty(self):
        empty_attrs = self._get_empty_init_data()
        mp = self._init_working_position(empty_attrs)
        self.assert_is_not_none(mp)
        empty_attrs['position_type'] = EMPTY_POSITION_TYPE
        check_attributes(mp, empty_attrs)
        self.assert_false(mp.is_fixed)
        self.assert_false(mp.is_floating)
        self.assert_false(mp.is_mock)
        self.assert_false(mp.is_untreated)
        self.assert_true(mp.is_empty)
        self.assert_is_none(mp.molecule_design_pool_id)
        tags = [self._get_empty_pos_type_tag()]
        tag_set = mp.get_tag_set()
        self._compare_tag_sets(tags, tag_set)

    def test_empty_position_factory(self):
        mp = MoleculeDesignPoolPositionDummy.create_empty_position(self.e5_pos)
        empty_pos_data = self._get_empty_init_data()
        check_attributes(mp, empty_pos_data)

    def test_init_failure(self):
        attrs = self._get_fixed_init_data()
        # position type determination will fail
        attrs['molecule_design_pool'] = 205200
        self.assert_raises(ValueError, self._init_working_position, attrs)

    def test_equality(self):
        fixed_attrs = self._get_fixed_init_data()
        mp1 = self._init_working_position(fixed_attrs)
        mp2 = self._init_working_position(fixed_attrs)
        fixed_attrs['rack_position'] = self.b2_pos
        mp3 = self._init_working_position(fixed_attrs)
        fixed_attrs['rack_position'] = self.a1_pos
        fixed_attrs['molecule_design_pool'] = self.floating_md
        mp4 = self._init_working_position(fixed_attrs)
        self.assert_equal(mp1, mp2)
        self.assert_not_equal(mp1, mp3)
        self.assert_not_equal(mp1, mp4)
        self.assert_not_equal(mp1, 1)

    def test_stock_concentration(self):
        fixed_attrs = self._get_fixed_init_data()
        mp = self._init_working_position(fixed_attrs)
        self.assert_equal(mp.stock_concentration, 50000)
        pool3 = self._get_entity(IMoleculeDesignPool, '1056000') # 3 siRNAs
        mp.molecule_design_pool = pool3
        self.assert_equal(mp.stock_concentration, 10000)
        mp.molecule_design_pool = self.floating_md
        self.assert_is_none(mp.stock_concentration)

    def test_molecule_type(self):
        fixed_attrs = self._get_fixed_init_data()
        mt_agg = get_root_aggregate(IMoleculeType) # get_entity returns None
        siRNA = mt_agg.get_by_id(MOLECULE_TYPE_IDS.SIRNA)
        mp = self._init_working_position(fixed_attrs)
        self.assert_equal(mp.molecule_type, siRNA)
        pool3 = self._get_entity(IMoleculeDesignPool, '1056000') # 3 siRNAs
        mp.molecule_design_pool = pool3
        self.assert_equal(mp.molecule_type, siRNA)
        miRNA = mt_agg.get_by_id(MOLECULE_TYPE_IDS.MIRNA_INHI)
        pool_mirna = self._get_entity(IMoleculeDesignPool, '330001')
        mp.molecule_design_pool = pool_mirna
        self.assert_equal(mp.molecule_type, miRNA)
        mp.molecule_design_pool = self.floating_md
        self.assert_is_none(mp.molecule_type)


class MoleculeDesignPoolLayoutDummy(MoleculeDesignPoolLayout):
    """
    This dummy class allows to test the molecule design pool layouts. It only
    serves to get around the abstract class.
    """
    pass


class MoleculeDesignPoolLayoutTestCase(MoleculeDesignPoolWorkingTypeTestCase):

    def __get_fixed_position(self):
        return self._init_working_position(self._get_fixed_init_data())

    def __get_floating_position(self):
        return self._init_working_position(self._get_floating_init_data())

    def __get_mock_position(self):
        return self._init_working_position(self._get_mock_init_data())

    def __get_untreated_position(self):
        return self._init_working_position(self._get_untreated_init_data())

    def __get_empty_position(self):
        return self._init_working_position(self._get_empty_init_data())

    def __init_layout(self, shape=None):
        if shape is None:
            shape = get_96_rack_shape()
        return MoleculeDesignPoolLayoutDummy(shape=shape)

    def __create_test_layout(self):
        ml = self.__init_layout()
        ml.add_position(self.__get_fixed_position())
        ml.add_position(self.__get_floating_position())
        ml.add_position(self.__get_mock_position())
        ml.add_position(self.__get_untreated_position())
        ml.add_position(self.__get_empty_position())
        return ml

    def test_init_molecule_design_pool_base_class(self):
        shape = get_96_rack_shape()
        attrs = dict(shape=shape)
        self.assert_raises(NotImplementedError, MoleculeDesignPoolLayout,
                           **attrs)

    def test_init(self):
        shape = get_384_rack_shape()
        ml = self.__init_layout(shape=shape)
        self.assert_is_not_none(ml)
        self.assert_equal(ml.shape, shape)
        self.assert_equal(len(ml), 0)

    def test_add_working_position(self):
        ml = self.__init_layout()
        self.assert_equal(len(ml), 0)
        a1_mp = self.__get_fixed_position()
        ml.add_position(a1_mp)
        self.assert_equal(len(ml), 1)

    def test_get_working_position(self):
        ml = self.__init_layout()
        a1_mp = self.__get_fixed_position()
        ml.add_position(a1_mp)
        self.assert_equal(ml.get_working_position(self.a1_pos), a1_mp)
        self.assert_is_none(ml.get_working_position(self.c3_pos))

    def test_equality(self):
        ml1 = self.__create_test_layout()
        ml2 = self.__create_test_layout()
        ml3 = self.__create_test_layout()
        ml3.del_position(self.e5_pos)
        self.assert_equal(ml1, ml2)
        self.assert_not_equal(ml1, ml3)
        self.assert_not_equal(ml1, 1)

    def test_get_tags(self):
        ml = self.__create_test_layout()
        tags = [self.pool_tag, self.floating_tag, self.mock_tag,
                self._get_fixed_pos_type_tag(),
                self._get_floating_pos_type_tag(),
                self._get_mock_pos_type_tag(),
                self._get_untreated_pos_type_tag(),
                self._get_empty_pos_type_tag(), self._get_untreated_pool_tag()]
        tag_set = ml.get_tags()
        self._compare_tag_sets(tags, tag_set)

    def test_get_positions(self):
        ml = self.__create_test_layout()
        positions = [self.a1_pos, self.b2_pos, self.c3_pos, self.d4_pos,
                     self.e5_pos]
        pos_set = ml.get_positions()
        self._compare_pos_sets(positions, pos_set)

    def test_get_tags_for_position(self):
        ml = self.__create_test_layout()
        tags = [self.pool_tag, self._get_fixed_pos_type_tag()]
        tag_set = ml.get_tags_for_position(self.a1_pos)
        self._compare_tag_sets(tags, tag_set)

    def test_get_positions_for_tag(self):
        ml = self.__create_test_layout()
        positions = [self.b2_pos]
        pos_set = ml.get_positions_for_tag(self.floating_tag)
        self._compare_pos_sets(positions, pos_set)

    def test_close(self):
        ml = self.__create_test_layout()
        self.assert_equals(len(ml), 5)
        empty_mp = self.__get_empty_position()
        self.assert_equal(ml.get_working_position(self.e5_pos), empty_mp)
        self.assert_false(ml.is_closed)
        ml.close()
        self.assert_true(ml.is_closed)
        self.assert_equal(len(ml), 4)
        self.assert_is_none(ml.get_working_position(self.e5_pos))
        self.assert_raises(AttributeError, ml.add_position, empty_mp)

    def test_create_rack_layout(self):
        ml = self.__create_test_layout()
        self.assert_false(ml.is_closed)
        rl = ml.create_rack_layout()
        self.assert_is_not_none(rl)
        self.assert_equal(len(rl.tagged_rack_position_sets), 4)
        self._compare_tag_sets(ml.get_tags(), rl.get_tags())
        self._compare_pos_sets(ml.get_positions(), rl.get_positions())
        self._compare_tag_sets(ml.get_tags_for_position(self.a1_pos),
                               rl.get_tags_for_position(self.a1_pos))
        self._compare_pos_sets(ml.get_positions_for_tag(self.floating_tag),
                               rl.get_positions_for_tag(self.floating_tag))
        self.assert_true(ml.is_closed)

    def test_floating_molecule_type(self):
        ml = self.__create_test_layout()
        self.assert_is_none(ml.floating_molecule_type)
        mt = get_root_aggregate(IMoleculeType).get_by_id(
                                                        MOLECULE_TYPE_IDS.SIRNA)
        ml.set_floating_molecule_type(mt)
        self.assert_equal(ml.floating_molecule_type, mt)
        self.assert_raises(TypeError, ml.set_floating_molecule_type,
                           MOLECULE_TYPE_IDS.SIRNA)

    def test_floating_stock_concentration(self):
        ml = self.__create_test_layout()
        self.assert_is_none(ml.floating_stock_concentration)
        ml.set_floating_stock_concentration(50000)
        self.assert_equal(ml.floating_stock_concentration, 50000)
        conc_in_M = 50000 / CONCENTRATION_CONVERSION_FACTOR
        ml.set_floating_stock_concentration(conc_in_M)
        self.assert_equal(ml.floating_stock_concentration, 50000)
        self.assert_raises(ValueError, ml.set_floating_stock_concentration, -4)

    def test_has_floatings(self):
        ml = self.__create_test_layout()
        self.assert_true(ml.has_floatings())
        ml.del_position(self.b2_pos)
        self.assert_false(ml.has_floatings())

    def test_get_floating_positions(self):
        ml = self.__create_test_layout()
        exp_floatings = { self.floating_md : [self.__get_floating_position()]}
        self.assert_equal(ml.get_floating_positions(), exp_floatings)
        ml.del_position(self.b2_pos)
        self.assert_equal(ml.get_floating_positions(), {})

    def test_get_molecule_design_pool_count(self):
        ml = self.__create_test_layout()
        self.assert_equal(ml.get_molecule_design_pool_count(), 2)
        mp = ml.get_working_position(self.b2_pos)
        mp.molecule_design_pool = self.pool
        self.assert_equal(ml.get_molecule_design_pool_count(), 1)



class TransferTargetTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.rack_pos = get_rack_position_from_label('A1')
        self.rack_pos_label = self.rack_pos.label
        self.transfer_vol = 5
        self.info = 'A1:5'

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.rack_pos
        del self.rack_pos_label
        del self.transfer_vol
        del self.info

    def test_transfer_target_init(self):
        tt1 = TransferTarget(self.rack_pos, self.transfer_vol)
        self.assert_not_equal(tt1, None)
        self.assert_equal(tt1.position_label, self.rack_pos_label)
        self.assert_equal(tt1.transfer_volume, self.transfer_vol)
        tt2 = TransferTarget(self.rack_pos_label, self.transfer_vol)
        self.assert_not_equal(tt2, None)
        self.assert_equal(tt2.position_label, self.rack_pos_label)
        self.assert_equal(tt2.transfer_volume, self.transfer_vol)
        tt2 = TransferTarget(self.rack_pos, str(self.transfer_vol))
        self.assert_not_equal(tt2, None)
        self.assert_equal(tt2.position_label, self.rack_pos_label)
        self.assert_equal(tt2.transfer_volume, self.transfer_vol)
        no_rack_pos = (None, self.transfer_vol)
        self.assert_raises(TypeError, TransferTarget, *no_rack_pos)
        no_vol = (self.rack_pos, None)
        self.assert_raises(ValueError, TransferTarget, *no_vol)
        invalid_vol = (self.rack_pos, 'default')
        self.assert_raises(ValueError, TransferTarget, *invalid_vol)

    def test_transfer_target_info(self):
        tt = TransferTarget(self.rack_pos, self.transfer_vol)
        info = tt.target_info
        self.assert_equal(info, self.info)

    def test_parse_info(self):
        tt = TransferTarget.parse_info_string(self.info)
        self.assert_not_equal(tt, None)
        self.assert_equal(tt.position_label, self.rack_pos_label)
        self.assert_equal(tt.transfer_volume, self.transfer_vol)
        info2 = self.info.replace(':', '_')
        self.assert_raises(ValueError, TransferTarget.parse_info_string, info2)


class TransferPositionDummy(TransferPosition):
    """
    This dummy class allows to test the transfer position. It only serves
    to come around the abstract class initialization.
    """

    def __init__(self, rack_position, molecule_design_pool=None,
                 transfer_targets=None):
        TransferPosition.__init__(self, rack_position=rack_position,
                                  molecule_design_pool=molecule_design_pool,
                                  transfer_targets=transfer_targets)


class TransferPositionTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.rack_pos = get_rack_position_from_label('A1')
        self.pool = self._get_pool(205200)
        self.pool_tag = Tag('molecule_design_pool', 'molecule_design_pool_id',
                            '205200')
        self.pos_type_tag = Tag('molecule_design_pool', 'position_type',
                                'fixed')
        self.volume1 = 80
        self.volume2 = 60
        self.target_well1 = get_rack_position_from_label('B1')
        self.target_well2 = get_rack_position_from_label('B2')
        self.target_well_labels = [self.target_well1.label,
                                   self.target_well2.label]
        self.tt1 = TransferTarget(self.target_well1, self.volume1)
        self.tt2 = TransferTarget(self.target_well2, self.volume2)
        self.transfer_targets = [self.tt1, self.tt2]
        self.target_tag_value = 'B1:80-B2:60'
        self.target_tag = Tag('sample_transfer', 'target_wells', 'B1:80-B2:60')

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.rack_pos
        del self.pool
        del self.pool_tag
        del self.pos_type_tag
        del self.volume1
        del self.volume2
        del self.target_well1
        del self.target_well2
        del self.target_well_labels
        del self.tt1
        del self.tt2
        del self.transfer_targets
        del self.target_tag_value
        del self.target_tag

    def __get_data(self):
        return dict(rack_position=self.rack_pos,
                    molecule_design_pool=self.pool,
                    transfer_targets=self.transfer_targets)

    def __create_test_position(self, attrs=None):
        if attrs is None:
            attrs = self.__get_data()
        return TransferPositionDummy(**attrs)

    def test_init(self):
        # working initialisation
        attrs = self.__get_data()
        tp1 = self.__create_test_position(attrs)
        self.assert_is_not_none(tp1)
        check_attributes(tp1, attrs)
        self.assert_true(tp1.is_fixed)
        empty_attrs = dict(rack_position=self.rack_pos)
        tp2 = self.__create_test_position(empty_attrs)
        self.assert_is_not_none(tp2)
        check_attributes(tp2, empty_attrs)
        self.assert_is_none(tp2.molecule_design_pool)
        self.assert_equal(len(tp2.transfer_targets), 0)
        self.assert_true(tp2.is_empty)
        # failing initializations
        ori_targets = attrs['transfer_targets']
        attrs['transfer_targets'] = self.tt1
        self.assert_raises(TypeError, TransferPositionDummy, **attrs)
        attrs['transfer_targets'] = ori_targets
        attrs['molecule_design_pool'] = 'default'
        self.assert_raises(ValueError, TransferPositionDummy, **attrs)

    def test_equality(self):
        attrs = self.__get_data()
        tp1 = self.__create_test_position(attrs)
        tp2 = self.__create_test_position(attrs)
        attrs['rack_position'] = get_rack_position_from_label('G4')
        tp3 = self.__create_test_position(attrs)
        attrs['rack_position'] = self.rack_pos
        attrs['molecule_design_pool'] = MOCK_POSITION_TYPE
        tp4 = self.__create_test_position(attrs)
        attrs['molecule_design_pool'] = self.pool
        attrs['transfer_targets'] = [self.tt1]
        tp5 = self.__create_test_position(attrs)
        self.assert_equal(tp1, tp2)
        self.assert_not_equal(tp1, tp3)
        self.assert_not_equal(tp1, tp4)
        self.assert_not_equal(tp4, tp5)
        ip = IsoPosition.create_empty_position(self.rack_pos)
        self.assert_not_equal(tp1, ip)

    def test_add_target(self):
        attrs = self.__get_data()
        attrs['transfer_targets'] = None
        tp = self.__create_test_position(attrs)
        self.assert_equal(len(tp.transfer_targets), 0)
        tp.add_transfer_target(self.tt1)
        self.assert_equal(len(tp.transfer_targets), 1)
        self.assert_true(self.tt1 in tp.transfer_targets)
        tp.add_transfer_target(self.tt2)
        self.assert_equal(len(tp.transfer_targets), 2)
        self.assert_true(self.tt1 in tp.transfer_targets)
        self.assert_true(self.tt2 in tp.transfer_targets)
        self.assert_raises(ValueError, tp.add_transfer_target, self.tt1)
        self.assert_raises(TypeError, tp.add_transfer_target,
                           (self.target_well1, self.volume1))

    def test_get_targets_tag_value(self):
        tp = self.__create_test_position()
        tag_val = tp.get_targets_tag_value()
        self.assert_equal(tag_val, self.target_tag_value)

    def test_parse_tag_value(self):
        tts = TransferPositionDummy.parse_target_tag_value(
                                                        self.target_tag_value)
        self.assert_equal(len(tts), 2)
        tt_labels = []
        tt_vols = []
        for tt in tts:
            tt_labels.append(tt.position_label)
            tt_vols.append(tt.transfer_volume)
        self.assert_equal(tt_labels, self.target_well_labels)
        exp_vols = [self.volume1, self.volume2]
        self.assert_equal(exp_vols, tt_vols)

    def test_get_parameter_values(self):
        tp = self.__create_test_position()
        self.assert_equal(
                tp.get_parameter_value(TransferParameters.TARGET_WELLS),
                self.transfer_targets)
        self.assert_equal(self.pool,
                tp.get_parameter_value(TransferParameters.MOLECULE_DESIGN_POOL))
        self.assert_equal(FIXED_POSITION_TYPE,
                tp.get_parameter_value(TransferParameters.POS_TYPE))

    def test_get_parameter_tag(self):
        tp = self.__create_test_position()
        self.assert_equal(
                tp.get_parameter_tag(TransferParameters.TARGET_WELLS),
                self.target_tag)
        self.assert_equal(self.pool_tag,
                tp.get_parameter_tag(TransferParameters.MOLECULE_DESIGN_POOL))
        self.assert_equal(self.pos_type_tag,
                tp.get_parameter_tag(TransferParameters.POS_TYPE))

    def test_tag_set(self):
        tp1 = self.__create_test_position()
        tags = [self.target_tag, self.pool_tag, self.pos_type_tag]
        tag_set1 = tp1.get_tag_set()
        self.assert_true(len(tag_set1), len(tags))
        for tag in tags: self.assert_true(tag in tag_set1)
        tp2 = TransferPositionDummy.create_empty_position(self.rack_pos)
        tags2 = [Tag('molecule_design_pool', 'position_type', 'empty')]
        tag_set2 = tp2.get_tag_set()
        self._compare_tag_sets(tags2, tag_set2)


class TransferLayoutDummy(TransferLayout):
    """
    This dummy class allows to test the transfer layouts. It only circumvents
    the abstract class initialization.
    """

    def __init__(self, shape):
        TransferLayout.__init__(self, shape=shape)


class TransferLayoutTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.shape = get_96_rack_shape()
        domain = TransferParameters.DOMAIN
        self.volume1 = 80
        self.volume2 = 100
        self.a1_pos = get_rack_position_from_label('A1')
        self.a2_pos = get_rack_position_from_label('A2')
        self.b1_pos = get_rack_position_from_label('B1')
        self.b2_pos = get_rack_position_from_label('B2')
        self.c1_pos = get_rack_position_from_label('C1')
        self.c2_pos = get_rack_position_from_label('C2')
        self.d1_pos = get_rack_position_from_label('D1')
        self.d2_pos = get_rack_position_from_label('D2')
        self.pool = self._get_pool(205200)
        self.pool_tag = Tag(MoleculeDesignPoolParameters.DOMAIN,
                            TransferParameters.MOLECULE_DESIGN_POOL, '205200')
        self.type_tag = Tag(MoleculeDesignPoolParameters.DOMAIN,
                            TransferParameters.POS_TYPE, FIXED_POSITION_TYPE)
        self.a_target_wells = [self.a1_pos, self.a2_pos]
        self.a1_tt = TransferTarget(self.a1_pos, self.volume1)
        self.a2_tt = TransferTarget(self.a2_pos, self.volume2)
        self.tts_a = [self.a1_tt, self.a2_tt]
        self.tp_a = TransferPositionDummy(self.a1_pos, self.pool, self.tts_a)
        self.a_target_tag = Tag(domain, TransferParameters.TARGET_WELLS,
                              'A1:80-A2:100')
        self.b1_tt = TransferTarget(self.b1_pos, self.volume1)
        self.b2_tt = TransferTarget(self.b2_pos, self.volume1)
        self.tts_b = [self.b1_tt, self.b2_tt]
        self.tp_b = TransferPositionDummy(self.b1_pos, self.pool, self.tts_b)
        self.b_target_tag = Tag(domain, TransferParameters.TARGET_WELLS,
                              'B1:80-B2:80')
        self.c1_tt = TransferTarget(self.c1_pos, self.volume2)
        self.c2_tt = TransferTarget(self.c2_pos, self.volume2)
        self.tts_c = [self.c1_tt, self.c2_tt]
        self.tp_c = TransferPositionDummy(self.c1_pos, self.pool, self.tts_c)
        self.c_target_tag = Tag(domain, TransferParameters.TARGET_WELLS,
                              'C1:100-C2:100')
        self.d_dest_wells = [self.d1_pos, self.d2_pos]
        self.d_dest_tag = Tag(domain, TransferParameters.TARGET_WELLS, 'D1-D2')

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.shape
        del self.volume1
        del self.volume2
        del self.a1_pos
        del self.a2_pos
        del self.b1_pos
        del self.b2_pos
        del self.c1_pos
        del self.c2_pos
        del self.d1_pos
        del self.d2_pos
        del self.pool
        del self.pool_tag
        del self.type_tag
        del self.a_target_wells
        del self.a1_tt
        del self.a2_tt
        del self.tts_a
        del self.tp_a
        del self.a_target_tag
        del self.b1_tt
        del self.b2_tt
        del self.tts_b
        del self.tp_b
        del self.b_target_tag
        del self.c1_tt
        del self.c2_tt
        del self.tts_c
        del self.tp_c
        del self.c_target_tag
        del self.d_dest_wells
        del self.d_dest_tag

    def __create_test_layout(self):
        layout = TransferLayoutDummy(self.shape)
        layout.add_position(self.tp_a)
        layout.add_position(self.tp_b)
        layout.add_position(self.tp_c)
        return  layout

    def test_init(self):
        tl = TransferLayoutDummy(self.shape)
        self.assert_false(tl is None)
        self.assert_equal(tl.shape, self.shape)
        self.assert_equal(len(tl), 0)

    def test_add_position(self):
        tl = TransferLayoutDummy(self.shape)
        self.assert_equal(len(tl), 0)
        tl.add_position(self.tp_a)
        self.assert_equal(len(tl), 1)
        self.assert_equal(tl.get_working_position(self.a1_pos), self.tp_a)
        self.assert_raises(ValueError, tl.add_position, self.tp_a)
        iso_pos = IsoPosition(rack_position=self.b2_pos)
        self.assert_raises(TypeError, tl.add_position, iso_pos)

    def test_get_position(self):
        tl = self.__create_test_layout()
        self.assert_equal(tl.get_working_position(self.a1_pos), self.tp_a)
        self.assert_equal(tl.get_working_position(self.a2_pos), None)

    def test_equality(self):
        tl1 = self.__create_test_layout()
        tl2 = self.__create_test_layout()
        tl3 = self.__create_test_layout()
        d1_tp = TransferPositionDummy(self.d1_pos)
        tl3.add_position(d1_tp)
        self.assert_equal(tl1, tl2)
        self.assert_not_equal(tl1, tl3)

    def test_get_tags(self):
        tl = self.__create_test_layout()
        tags = [self.a_target_tag, self.b_target_tag, self.c_target_tag,
                self.pool_tag, self.type_tag]
        tag_set = tl.get_tags()
        self.assert_equal(len(tag_set), len(tags))
        for tag in tags: self.assert_true(tag in tag_set)

    def test_get_positions(self):
        tl = self.__create_test_layout()
        positions = [self.a1_pos, self.b1_pos, self.c1_pos]
        pos_set = tl.get_positions()
        self.assert_equal(len(pos_set), len(positions))
        for pos in positions: self.assert_true(pos in pos_set)

    def test_get_tags_for_positions(self):
        tl = self.__create_test_layout()
        tags_a = [self.a_target_tag, self.pool_tag, self.type_tag]
        tag_set_a = tl.get_tags_for_position(self.a1_pos)
        self.assert_equal(len(tag_set_a), len(tags_a))
        for tag in tags_a: self.assert_true(tag in tag_set_a)
        self.assert_false(self.b_target_tag in tag_set_a)
        tags_no = tl.get_tags_for_position(self.a2_pos)
        self.assert_equal(len(tags_no), 0)

    def test_get_position_for_tag(self):
        tl = self.__create_test_layout()
        pos1 = [self.a1_pos]
        pos_set1 = tl.get_positions_for_tag(self.a_target_tag)
        self.assert_equal(len(pos_set1), len(pos1))
        for pos in pos1: self.assert_true(pos in pos_set1)
        self.assert_false(self.c1_pos in pos_set1)

    def test_create_rack_layout(self):
        tl = self.__create_test_layout()
        rack_layout = tl.create_rack_layout()
        self.assert_false(rack_layout is None)
        self.assert_not_equal(tl, rack_layout)
        self.assert_equal(tl.shape, rack_layout.shape)
        trps_list = rack_layout.tagged_rack_position_sets
        self.assert_equal(len(trps_list), 4)
        self.assert_equal(tl.get_tags(), rack_layout.get_tags())
        self.assert_equal(set(tl.get_positions()), rack_layout.get_positions())
        self.assert_equal(tl.get_positions_for_tag(self.volume1),
                rack_layout.get_positions_for_tag(self.volume1))
        self.assert_equal(tl.get_tags_for_position(self.c1_pos),
                          rack_layout.get_tags_for_position(self.c1_pos))

