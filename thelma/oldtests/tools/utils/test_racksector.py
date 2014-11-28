"""
Tests for rack sector classes.

AAB
"""
from everest.repositories.rdb.testing import check_attributes
from thelma.tools.semiconstants import get_384_rack_shape
from thelma.tools.semiconstants import get_96_rack_shape
from thelma.tools.semiconstants import get_rack_position_from_label
from thelma.tools.utils.racksector import QuadrantIterator
from thelma.tools.utils.racksector import RackSectorTranslator
from thelma.tools.utils.racksector import check_rack_shape_match
from thelma.tools.utils.racksector import get_sector_positions
from thelma.oldtests.tools.tooltestingutils import ToolsAndUtilsTestCase


class RackSectorTranslatorTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.number_sectors = 4
        self.source_sector_index = 2
        self.target_sector_index = 0
        self.behaviour = None

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.number_sectors
        del self.source_sector_index
        del self.target_sector_index
        del self.behaviour

    def __get_data(self):
        return dict(number_sectors=self.number_sectors,
                    source_sector_index=self.source_sector_index,
                    target_sector_index=self.target_sector_index,
                    behaviour=self.behaviour)

    def test_init_4_sectors(self):
        attrs1 = self.__get_data()
        rst1 = RackSectorTranslator(**attrs1)
        self.assert_is_not_none(rst1)
        attrs1['row_count'] = 2
        attrs1['col_count'] = 2
        attrs1['row_modifier'] = 1
        attrs1['col_modifier'] = 0
        check_attributes(rst1, attrs1)
        self.source_sector_index = 0
        self.target_sector_index = 3
        attrs2 = self.__get_data()
        rst2 = RackSectorTranslator(**attrs2)
        self.assert_is_not_none(rst2)
        attrs1['source_sector_index'] = 0
        attrs1['target_sector_index'] = 3
        attrs1['col_modifier'] = 1
        check_attributes(rst2, attrs1)
        self.target_sector_index = 0
        attrs3 = self.__get_data()
        rst3 = RackSectorTranslator(**attrs3)
        self.assert_is_not_none(rst3)
        attrs1['target_sector_index'] = 0
        attrs1['row_modifier'] = (0, 0)
        attrs1['col_modifier'] = (0, 0)
        check_attributes(rst3, attrs1)
        self.source_sector_index = 3
        self.target_sector_index = 1
        attrs4 = self.__get_data()
        rst4 = RackSectorTranslator(**attrs4)
        attrs4['row_count'] = 2
        attrs4['col_count'] = 2
        attrs4['row_modifier'] = (1, 0)
        attrs4['col_modifier'] = (1, 1)
        check_attributes(rst4, attrs4)

    def test_init_1_sector(self):
        self.source_sector_index = 0
        self.number_sectors = 1
        attrs = self.__get_data()
        rst = RackSectorTranslator(**attrs)
        self.assert_is_not_none(rst)
        attrs['row_count'] = 1
        attrs['col_count'] = 1
        attrs['row_modifier'] = 0
        attrs['col_modifier'] = 0
        check_attributes(rst, attrs)

    def test_init_16_sectors(self):
        self.source_sector_index = 7
        self.number_sectors = 16
        attrs = self.__get_data()
        rst = RackSectorTranslator(**attrs)
        self.assert_is_not_none(rst)
        attrs['row_count'] = 4
        attrs['col_count'] = 4
        attrs['row_modifier'] = 1
        attrs['col_modifier'] = 3
        check_attributes(rst, attrs)

    def test_init_with_row_or_column_count(self):
        self.number_sectors = 8
        self.source_sector_index = 5
        attrs = self.__get_data()
        self.assert_raises(ValueError, RackSectorTranslator, **attrs)
        attrs['row_count'] = 4
        rst1 = RackSectorTranslator(**attrs)
        attrs['col_count'] = 2
        attrs['row_modifier'] = 2
        attrs['col_modifier'] = 1
        check_attributes(rst1, attrs)
        attrs = self.__get_data()
        attrs['col_count'] = 2
        rst2 = RackSectorTranslator(**attrs)
        attrs['row_modifier'] = 2
        attrs['col_modifier'] = 1
        attrs['row_count'] = 4
        check_attributes(rst2, attrs)
        attrs = self.__get_data()
        attrs['row_count'] = 3
        self.assert_raises(ValueError, RackSectorTranslator, **attrs)

    def test_many_to_one(self):
        a1_pos = get_rack_position_from_label('A1')
        b1_pos = get_rack_position_from_label('B1')
        b2_pos = get_rack_position_from_label('B2')
        c2_pos = get_rack_position_from_label('C2')
        b4_pos = get_rack_position_from_label('B4')
        d3_pos = get_rack_position_from_label('D3')
        f8_pos = get_rack_position_from_label('F8')
        g4_pos = get_rack_position_from_label('G4')
        # 4 quadrants
        self.source_sector_index = 0
        self.target_sector_index = 2
        attrs_4 = self.__get_data()
        rst_4 = RackSectorTranslator(**attrs_4)
        self.assert_equal(rst_4.translate(a1_pos), b1_pos)
        self.assert_equal(rst_4.translate(b2_pos), d3_pos)
        # 16 quadrants
        self.number_sectors = 16
        self.source_sector_index = 0
        self.target_sector_index = 7
        attrs_16 = self.__get_data()
        rst_16 = RackSectorTranslator(**attrs_16)
        self.assert_equal(rst_16.translate(a1_pos), b4_pos)
        self.assert_equal(rst_16.translate(b2_pos), f8_pos)
        # 8 quadrants
        self.number_sectors = 8
        self.target_sector_index = 5
        attrs_8 = self.__get_data()
        attrs_8['row_count'] = 4
        rst_8 = RackSectorTranslator(**attrs_8)
        self.assert_equal(rst_8.translate(a1_pos), c2_pos)
        self.assert_equal(rst_8.translate(b2_pos), g4_pos)

    def test_many_to_many(self):
        a2_pos = get_rack_position_from_label('A2')
        b2_pos = get_rack_position_from_label('B2')
        c2_pos = get_rack_position_from_label('C2')
        self.source_sector_index = 3
        self.target_sector_index = 1
        attrs = self.__get_data()
        rst = RackSectorTranslator(**attrs)
        self.assert_equal(rst.translate(b2_pos), a2_pos)
        self.assert_raises(ValueError, rst.translate, c2_pos)

    def test_one_to_one(self):
        a2_pos = get_rack_position_from_label('A2')
        # 1 quadrant
        self.number_sectors = 1
        self.target_sector_index = 0
        self.source_sector_index = 0
        attrs_1 = self.__get_data()
        rst_1 = RackSectorTranslator(**attrs_1)
        self.assert_equal(rst_1.translate(a2_pos), a2_pos)

    def test_one_to_many(self):
        a1_pos = get_rack_position_from_label('A1')
        b1_pos = get_rack_position_from_label('B1')
        b2_pos = get_rack_position_from_label('B2')
        c2_pos = get_rack_position_from_label('C2')
        b4_pos = get_rack_position_from_label('B4')
        d3_pos = get_rack_position_from_label('D3')
        f8_pos = get_rack_position_from_label('F8')
        g4_pos = get_rack_position_from_label('G4')
        # 4 quadrants
        attrs_4 = self.__get_data()
        rst_4 = RackSectorTranslator(**attrs_4)
        self.assert_equal(rst_4.translate(b1_pos), a1_pos)
        self.assert_equal(rst_4.translate(d3_pos), b2_pos)
        self.assert_raises(ValueError, rst_4.translate, b2_pos)
        # 16 quadrants
        self.number_sectors = 16
        self.source_sector_index = 7
        attrs_16 = self.__get_data()
        rst_16 = RackSectorTranslator(**attrs_16)
        self.assert_equal(rst_16.translate(b4_pos), a1_pos)
        self.assert_equal(rst_16.translate(f8_pos), b2_pos)
        self.assert_raises(ValueError, rst_16.translate, b2_pos)
        # 8 quadrants
        self.number_sectors = 8
        self.source_sector_index = 5
        attrs_8 = self.__get_data()
        attrs_8['row_count'] = 4
        rst_8 = RackSectorTranslator(**attrs_8)
        self.assert_equal(rst_8.translate(c2_pos), a1_pos)
        self.assert_equal(rst_8.translate(g4_pos), b2_pos)
        self.assert_raises(ValueError, rst_16.translate, b2_pos)

    def test_from_planned_liquid_transfer(self):
        attrs = self.__get_data()
        del attrs['behaviour']
        prt = self._create_planned_rack_sample_transfer(**attrs)
        self.assert_is_not_none(prt)
        rst = RackSectorTranslator.from_planned_rack_sample_transfer(prt)
        attrs['row_count'] = 2
        attrs['col_count'] = 2
        attrs['row_modifier'] = 1
        attrs['col_modifier'] = 0
        check_attributes(rst, attrs)

    def test_get_translation_behaviour(self):
        shape_96 = get_96_rack_shape()
        shape_384 = get_384_rack_shape()
        self.assert_equal(RackSectorTranslator.get_translation_behaviour(
            source_shape=shape_96, target_shape=shape_96, number_sectors=4),
                          RackSectorTranslator.MANY_TO_MANY)
        self.assert_equal(RackSectorTranslator.get_translation_behaviour(
            source_shape=shape_384, target_shape=shape_384, number_sectors=4),
                          RackSectorTranslator.MANY_TO_MANY)
        self.assert_equal(RackSectorTranslator.get_translation_behaviour(
            source_shape=shape_96, target_shape=shape_384, number_sectors=4),
                          RackSectorTranslator.MANY_TO_ONE)
        self.assert_equal(RackSectorTranslator.get_translation_behaviour(
            source_shape=shape_384, target_shape=shape_96, number_sectors=4),
                          RackSectorTranslator.ONE_TO_MANY)
        self.assert_equal(RackSectorTranslator.get_translation_behaviour(
            source_shape=shape_96, target_shape=shape_96, number_sectors=1),
                          RackSectorTranslator.ONE_TO_ONE)
        self.assert_equal(RackSectorTranslator.get_translation_behaviour(
            source_shape=shape_384, target_shape=shape_384, number_sectors=1),
                          RackSectorTranslator.ONE_TO_ONE)
        self.assert_equal(RackSectorTranslator.get_translation_behaviour(
            source_shape=shape_96, target_shape=shape_384, number_sectors=1),
                          RackSectorTranslator.ONE_TO_ONE)
        self.assert_equal(RackSectorTranslator.get_translation_behaviour(
            source_shape=shape_384, target_shape=shape_96, number_sectors=1),
                          RackSectorTranslator.ONE_TO_ONE)

    def test_behaviour(self):
        self.source_sector_index = 0
        self.target_sector_index = 0
        a1_pos = get_rack_position_from_label('A1')
        a2_pos = get_rack_position_from_label('A2')
        a3_pos = get_rack_position_from_label('A3')
        b2_pos = get_rack_position_from_label('B2')
        c3_pos = get_rack_position_from_label('C3')
        # many to one
        attrs = self.__get_data()
        attrs['behaviour'] = RackSectorTranslator.MANY_TO_ONE
        rst = RackSectorTranslator(**attrs)
        self.assert_equal(rst.translate(a1_pos), a1_pos)
        self.assert_equal(rst.translate(b2_pos), c3_pos)
        self.assert_equal(rst.translate(a2_pos), a3_pos)
        # many to many
        attrs['behaviour'] = RackSectorTranslator.MANY_TO_MANY
        rst = RackSectorTranslator(**attrs)
        self.assert_equal(rst.translate(a1_pos), a1_pos)
        self.assert_equal(rst.translate(c3_pos), c3_pos)
        self.assert_raises(ValueError, rst.translate, a2_pos)
        # one to many
        attrs['behaviour'] = RackSectorTranslator.ONE_TO_MANY
        rst = RackSectorTranslator(**attrs)
        self.assert_equal(rst.translate(a1_pos), a1_pos)
        self.assert_equal(rst.translate(c3_pos), b2_pos)
        self.assert_raises(ValueError, rst.translate, a2_pos)
        # default behaviour = many to many
        attrs['behaviour'] = None
        rst = RackSectorTranslator(**attrs)
        self.assert_equal(rst.translate(a1_pos), a1_pos)
        self.assert_equal(rst.translate(c3_pos), c3_pos)
        self.assert_raises(ValueError, rst.translate, a2_pos)

    def test_check_rack_shapes_for_transfer(self):
        shape_96 = get_96_rack_shape()
        shape_384 = get_384_rack_shape()
        # many to many
        bev = RackSectorTranslator.MANY_TO_MANY
        self.__check_rack_shape_match(shape_96, shape_96, 2, 2, bev, True)
        self.__check_rack_shape_match(shape_384, shape_384, 2, 2, bev, True)
        self.__check_rack_shape_match(shape_96, shape_384, 2, 2, bev, False)
        self.__check_rack_shape_match(shape_384, shape_96, 2, 2, bev, False)
        # one to one
        bev = RackSectorTranslator.ONE_TO_ONE
        self.__check_rack_shape_match(shape_96, shape_96, 2, 2, bev, True)
        self.__check_rack_shape_match(shape_384, shape_384, 2, 2, bev, True)
        self.__check_rack_shape_match(shape_96, shape_384, 2, 2, bev, False)
        self.__check_rack_shape_match(shape_384, shape_96, 2, 2, bev, False)
        # many to one
        bev = RackSectorTranslator.MANY_TO_ONE
        self.__check_rack_shape_match(shape_96, shape_96, 2, 2, bev, False)
        self.__check_rack_shape_match(shape_384, shape_384, 2, 2, bev, False)
        self.__check_rack_shape_match(shape_96, shape_384, 2, 2, bev, True)
        self.__check_rack_shape_match(shape_384, shape_96, 2, 2, bev, False)
        self.__check_rack_shape_match(shape_96, shape_384, 1, 1, bev, False)
        # one to many
        bev = RackSectorTranslator.ONE_TO_MANY
        self.__check_rack_shape_match(shape_96, shape_96, 2, 2, bev, False)
        self.__check_rack_shape_match(shape_384, shape_384, 2, 2, bev, False)
        self.__check_rack_shape_match(shape_96, shape_384, 2, 2, bev, False)
        self.__check_rack_shape_match(shape_384, shape_96, 2, 2, bev, True)
        self.__check_rack_shape_match(shape_384, shape_96, 1, 1, bev, False)
        # errors
        attrs = dict(source_shape=shape_96,
                target_shape=shape_96, row_count=2, col_count=2,
                translation_behaviour=None)
        self.assert_raises(ValueError, check_rack_shape_match, **attrs)


    def __check_rack_shape_match(self, source_shape, target_shape,
                    row_count, col_count, behaviour, expected_result):
        matches = check_rack_shape_match(row_count=row_count,
                col_count=col_count, source_shape=source_shape,
                target_shape=target_shape, translation_behaviour=behaviour)
        self.assert_equal(matches, expected_result)


class SectorPositionIteratorTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.rack_shape = get_96_rack_shape()
        self.number_sectors = 4
        self.sector_index = 1

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.rack_shape
        del self.number_sectors
        del self.sector_index

    def __get_data(self):
        return dict(sector_index=self.sector_index,
                    number_sectors=self.number_sectors,
                    rack_shape=self.rack_shape)

    def test_result(self):
        attrs = self.__get_data()
        positions = get_sector_positions(**attrs)
        exp_positions = ['A2', 'A4', 'A6', 'A8', 'A10', 'A12',
                         'C2', 'C4', 'C6', 'C8', 'C10', 'C12',
                         'E2', 'E4', 'E6', 'E8', 'E10', 'E12',
                         'G2', 'G4', 'G6', 'G8', 'G10', 'G12']
        self.assert_equal(len(positions), len(exp_positions))
        for pos in positions:
            self.assert_true(pos.label in exp_positions)

    def test_result_with_row_and_col_count(self):
        attrs = self.__get_data()
        attrs['col_count'] = 12
        attrs['row_count'] = 2
        positions = get_sector_positions(**attrs)
        exp_positions = ['A2', 'C2', 'E2', 'G2']
        self.assert_equal(len(positions), len(exp_positions))
        for pos in positions:
            self.assert_true(pos.label in exp_positions)


class QuadrantIteratorTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.number_sectors = 4

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.number_sectors

    def test_result(self):
        rsqi = QuadrantIterator(number_sectors=self.number_sectors)
        c3_pos = get_rack_position_from_label('C3')
        c4_pos = get_rack_position_from_label('C4')
        d3_pos = get_rack_position_from_label('D3')
        d4_pos = get_rack_position_from_label('D4')
        positions = rsqi.get_quadrant_positions(c3_pos)
        exp_positions = {0: c3_pos, 1 : c4_pos, 2: d3_pos, 3: d4_pos}
        self.assert_equal(len(exp_positions), len(positions))
        self.assert_equal(exp_positions, positions)

    def test_result_with_row_and_col_count(self):
        rsqi = QuadrantIterator(number_sectors=2,
                                row_count=2, col_count=1)
        c3_pos = get_rack_position_from_label('C3')
        d3_pos = get_rack_position_from_label('D3')
        positions = rsqi.get_quadrant_positions(c3_pos)
        exp_positions = {0: c3_pos, 1 : d3_pos}
        self.assert_equal(len(exp_positions), len(positions))
        self.assert_equal(exp_positions, positions)

