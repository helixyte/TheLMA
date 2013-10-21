"""
Tests for worklist tools base classes and functions.

AAB
"""
from thelma.automation.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.semiconstants import get_positions_for_shape
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.semiconstants import get_reservoir_spec
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.worklists.base import EmptyPositionManager
from thelma.automation.tools.worklists.base import get_dynamic_dead_volume
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase


class WorklistFunctionsTestCase(ToolsAndUtilsTestCase):

    def test_get_dynamic_dead_volume(self):
        quarter_mod_rs = get_reservoir_spec(
                                        RESERVOIR_SPECS_NAMES.QUARTER_MODULAR)
        self.assert_equal(get_dynamic_dead_volume(1, quarter_mod_rs),
                    quarter_mod_rs.min_dead_volume * VOLUME_CONVERSION_FACTOR)
        self.assert_equal(get_dynamic_dead_volume(30, quarter_mod_rs),
                    quarter_mod_rs.min_dead_volume * VOLUME_CONVERSION_FACTOR)
        tube_24_rs = get_reservoir_spec(RESERVOIR_SPECS_NAMES.TUBE_24)
        self.assert_equal(get_dynamic_dead_volume(1, tube_24_rs),
                    tube_24_rs.min_dead_volume * VOLUME_CONVERSION_FACTOR)
        self.assert_equal(get_dynamic_dead_volume(30, tube_24_rs),
                    tube_24_rs.min_dead_volume * VOLUME_CONVERSION_FACTOR)
        falcon_rs = get_reservoir_spec(RESERVOIR_SPECS_NAMES.FALCON_MANUAL)
        self.assert_equal(get_dynamic_dead_volume(1, falcon_rs),
                    falcon_rs.min_dead_volume * VOLUME_CONVERSION_FACTOR)
        self.assert_equal(get_dynamic_dead_volume(30, falcon_rs),
                    falcon_rs.min_dead_volume * VOLUME_CONVERSION_FACTOR)

        plate_rs_names = [RESERVOIR_SPECS_NAMES.STANDARD_96,
                          RESERVOIR_SPECS_NAMES.STANDARD_384,
                          RESERVOIR_SPECS_NAMES.DEEP_96]
        for rs_name in plate_rs_names:
            self.assert_equal(get_dynamic_dead_volume(1, rs_name), 10)
            self.assert_equal(get_dynamic_dead_volume(3, rs_name), 10)
            self.assert_equal(get_dynamic_dead_volume(4, rs_name), 11)
            self.assert_equal(get_dynamic_dead_volume(20, rs_name), 27)
            self.assert_equal(get_dynamic_dead_volume(30, rs_name), 30)


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
