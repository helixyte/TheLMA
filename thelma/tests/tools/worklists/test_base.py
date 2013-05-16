"""
Tests for worklist tools base classes and functions.

AAB
"""
from thelma.automation.tools.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.tools.semiconstants import get_reservoir_spec
from thelma.automation.tools.worklists.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.worklists.base import get_biomek_dead_volume
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase


class WorklistFunctionsTestCase(ToolsAndUtilsTestCase):

    def test_get_biomek_dead_volume(self):
        quarter_mod_rs = get_reservoir_spec(
                                        RESERVOIR_SPECS_NAMES.QUARTER_MODULAR)
        self.assert_equal(get_biomek_dead_volume(1, quarter_mod_rs),
                    quarter_mod_rs.min_dead_volume * VOLUME_CONVERSION_FACTOR)
        self.assert_equal(get_biomek_dead_volume(30, quarter_mod_rs),
                    quarter_mod_rs.min_dead_volume * VOLUME_CONVERSION_FACTOR)
        tube_24_rs = get_reservoir_spec(RESERVOIR_SPECS_NAMES.TUBE_24)
        self.assert_equal(get_biomek_dead_volume(1, tube_24_rs),
                    tube_24_rs.min_dead_volume * VOLUME_CONVERSION_FACTOR)
        self.assert_equal(get_biomek_dead_volume(30, tube_24_rs),
                    tube_24_rs.min_dead_volume * VOLUME_CONVERSION_FACTOR)
        falcon_rs = get_reservoir_spec(RESERVOIR_SPECS_NAMES.FALCON_MANUAL)
        self.assert_equal(get_biomek_dead_volume(1, falcon_rs),
                    falcon_rs.min_dead_volume * VOLUME_CONVERSION_FACTOR)
        self.assert_equal(get_biomek_dead_volume(30, falcon_rs),
                    falcon_rs.min_dead_volume * VOLUME_CONVERSION_FACTOR)

        plate_rs_names = [RESERVOIR_SPECS_NAMES.STANDARD_96,
                          RESERVOIR_SPECS_NAMES.STANDARD_384,
                          RESERVOIR_SPECS_NAMES.DEEP_96]
        for rs_name in plate_rs_names:
            self.assert_equal(get_biomek_dead_volume(1, rs_name), 10)
            self.assert_equal(get_biomek_dead_volume(3, rs_name), 10)
            self.assert_equal(get_biomek_dead_volume(4, rs_name), 11)
            self.assert_equal(get_biomek_dead_volume(20, rs_name), 27)
            self.assert_equal(get_biomek_dead_volume(30, rs_name), 30)

