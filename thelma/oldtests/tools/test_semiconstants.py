"""
Tests for semiconstant classes.

AAB
"""
from everest.entities.utils import get_root_aggregate
from everest.repositories.rdb.utils import as_slug_expression
from thelma.automation.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.semiconstants import PIPETTING_SPECS_NAMES
from thelma.automation.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.semiconstants import RACK_SPECS_NAMES
from thelma.automation.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.semiconstants import get_384_rack_shape
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.semiconstants import get_experiment_metadata_type
from thelma.automation.semiconstants import get_experiment_type_isoless
from thelma.automation.semiconstants import get_experiment_type_library
from thelma.automation.semiconstants \
    import get_experiment_type_manual_optimisation
from thelma.automation.semiconstants import get_experiment_type_order
from thelma.automation.semiconstants \
    import get_experiment_type_robot_optimisation
from thelma.automation.semiconstants import get_experiment_type_screening
from thelma.automation.semiconstants import get_item_status
from thelma.automation.semiconstants import get_item_status_future
from thelma.automation.semiconstants import get_item_status_managed
from thelma.automation.semiconstants import get_pipetting_specs
from thelma.automation.semiconstants import get_pipetting_specs_biomek
from thelma.automation.semiconstants import get_pipetting_specs_biomek_stock
from thelma.automation.semiconstants import get_pipetting_specs_cybio
from thelma.automation.semiconstants import get_pipetting_specs_manual
from thelma.automation.semiconstants import get_positions_for_shape
from thelma.automation.semiconstants import get_rack_specs_from_reservoir_specs
from thelma.automation.semiconstants import get_reservoir_spec
from thelma.automation.semiconstants import get_reservoir_specs_deep_96
from thelma.automation.semiconstants import get_reservoir_specs_from_rack_specs
from thelma.automation.semiconstants import get_reservoir_specs_standard_384
from thelma.automation.semiconstants import get_reservoir_specs_standard_96
from thelma.interfaces import IRackSpecs
from thelma.entities.experiment import ExperimentMetadataType
from thelma.entities.liquidtransfer import PipettingSpecs
from thelma.entities.liquidtransfer import ReservoirSpecs
from thelma.entities.rack import RackShape
from thelma.entities.rack import RackSpecs
from thelma.entities.status import ItemStatus
from thelma.oldtests.tools.tooltestingutils import ToolsAndUtilsTestCase


class _SemiConstantCacheTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.entity_cls = None
        self.cache_cls = None
        self.from_name_meth = None
        self.comp_attr_name = 'name'

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.entity_cls
        del self.cache_cls
        del self.from_name_meth
        del self.comp_attr_name

    def _test_from_name(self):
        for entity_slug in self.cache_cls.ALL:
            self.assert_true(self.cache_cls.is_known_entity(entity_slug))
            entity = self.from_name_meth(entity_slug) #pylint: disable=E1102
            self.assert_is_not_none(entity)
            self.assert_true(isinstance(entity, self.entity_cls))
        self.assert_raises(ValueError, self.from_name_meth, 'wrong_name')
        self.assert_false(self.cache_cls.is_known_entity('wrong_name'))

    def _test_shortcut(self, shortcut_meth, exp_name):
        entity = shortcut_meth()
        self.assert_is_not_none(entity)
        self.assert_true(isinstance(entity, self.entity_cls))
        self.assert_equal(getattr(entity, self.comp_attr_name), exp_name)
        return entity


class ReservoirSpecsNamesTestCase(_SemiConstantCacheTestCase):

    def set_up(self):
        _SemiConstantCacheTestCase.set_up(self)
        self.entity_cls = ReservoirSpecs
        self.cache_cls = RESERVOIR_SPECS_NAMES
        self.from_name_meth = get_reservoir_spec

    def test_from_name(self):
        self._test_from_name()

    def test_shortcuts(self):
        self._test_shortcut(get_reservoir_specs_standard_96,
                            RESERVOIR_SPECS_NAMES.STANDARD_96)
        self._test_shortcut(get_reservoir_specs_standard_384,
                            RESERVOIR_SPECS_NAMES.STANDARD_384)
        self._test_shortcut(get_reservoir_specs_deep_96,
                            RESERVOIR_SPECS_NAMES.DEEP_96)

    def test_is_rack(self):
        self.__test_is_rack_result(RESERVOIR_SPECS_NAMES.STANDARD_96, True)
        self.__test_is_rack_result(RESERVOIR_SPECS_NAMES.STANDARD_384, True)
        self.__test_is_rack_result(RESERVOIR_SPECS_NAMES.DEEP_96, True)
        self.__test_is_rack_result(RESERVOIR_SPECS_NAMES.FALCON_MANUAL, False)
        self.__test_is_rack_result(RESERVOIR_SPECS_NAMES.QUARTER_MODULAR,
                                    False)
        self.__test_is_rack_result(RESERVOIR_SPECS_NAMES.TUBE_24, False)
        self.__test_is_rack_result(RESERVOIR_SPECS_NAMES.STOCK_RACK, True)
        self.assert_raises(TypeError, RESERVOIR_SPECS_NAMES.is_rack_spec, 4)
        self.assert_raises(ValueError, RESERVOIR_SPECS_NAMES.is_rack_spec,
                           'invalid')

    def __test_is_rack_result(self, rs_name, is_rack):
        rs = get_reservoir_spec(rs_name)
        if is_rack:
            assert_meth = self.assert_true
        else:
            assert_meth = self.assert_false
        assert_meth(RESERVOIR_SPECS_NAMES.is_rack_spec(rs))
        assert_meth(RESERVOIR_SPECS_NAMES.is_rack_spec(rs.name))


class PipettingsSpecsNamesTestCase(_SemiConstantCacheTestCase):

    def set_up(self):
        _SemiConstantCacheTestCase.set_up(self)
        self.entity_cls = PipettingSpecs
        self.cache_cls = PIPETTING_SPECS_NAMES
        self.from_name_meth = get_pipetting_specs

    def test_from_name(self):
        self._test_from_name()

    def test_shortcuts(self):
        self._test_shortcut(get_pipetting_specs_manual,
                            PIPETTING_SPECS_NAMES.MANUAL)
        self._test_shortcut(get_pipetting_specs_cybio,
                            PIPETTING_SPECS_NAMES.CYBIO)
        self._test_shortcut(get_pipetting_specs_biomek,
                            PIPETTING_SPECS_NAMES.BIOMEK)
        self._test_shortcut(get_pipetting_specs_biomek_stock,
                            PIPETTING_SPECS_NAMES.BIOMEKSTOCK)


class RackSpecsNamesTestCase(_SemiConstantCacheTestCase):

    def set_up(self):
        _SemiConstantCacheTestCase.set_up(self)
        self.entity_cls = RackSpecs
        self.cache_cls = RACK_SPECS_NAMES
        self.from_name_meth = RACK_SPECS_NAMES.from_name

    def test_from_name(self):
        self._test_from_name()

    def test_from_reservoir_specs(self):
        test_names = \
            {RESERVOIR_SPECS_NAMES.STANDARD_96 : RACK_SPECS_NAMES.STANDARD_96,
             RESERVOIR_SPECS_NAMES.STANDARD_384 : RACK_SPECS_NAMES.STANDARD_384,
             RESERVOIR_SPECS_NAMES.DEEP_96 : RACK_SPECS_NAMES.DEEP_96}
        for rs_name, rack_specs_name in test_names.iteritems():
            rs = get_reservoir_spec(rs_name)
            for token in [rs, rs_name]:
                rack_specs = get_rack_specs_from_reservoir_specs(token)
                self.assert_is_not_none(rack_specs)
                self.assert_true(isinstance(rack_specs, RackSpecs))
                self.assert_equal(rack_specs.name, rack_specs_name)
        self.assert_raises(TypeError, get_rack_specs_from_reservoir_specs, 3)
        self.assert_raises(ValueError, get_rack_specs_from_reservoir_specs,
                           RESERVOIR_SPECS_NAMES.STOCK_RACK)
        self.assert_raises(ValueError, get_rack_specs_from_reservoir_specs,
                           'invalid')

    def test_to_reservoir_specs(self):
        test_values = {
            RACK_SPECS_NAMES.STANDARD_96 : RESERVOIR_SPECS_NAMES.STANDARD_96,
            RACK_SPECS_NAMES.DEEP_96 : RESERVOIR_SPECS_NAMES.DEEP_96,
            RACK_SPECS_NAMES.STANDARD_384 : RESERVOIR_SPECS_NAMES.STANDARD_384,
            RACK_SPECS_NAMES.STOCK_RACK : RESERVOIR_SPECS_NAMES.STOCK_RACK}
        for rack_specs_name, rs_name in test_values.iteritems():
            rack_specs = RACK_SPECS_NAMES.from_name(rack_specs_name)
            reservoir_specs = get_reservoir_specs_from_rack_specs(rack_specs)
            self.assert_is_not_none(reservoir_specs)
            self.assert_true(isinstance(reservoir_specs, ReservoirSpecs))
            self.assert_equal(reservoir_specs.name, rs_name)
        ps_agg = get_root_aggregate(IRackSpecs)
        nunc = ps_agg.get_by_slug(as_slug_expression('NUNCV96'))
        self.assert_is_not_none(nunc)
        self.assert_raises(ValueError, get_reservoir_specs_from_rack_specs,
                           nunc)


class RackShapesNamesTestCase(_SemiConstantCacheTestCase):

    def set_up(self):
        _SemiConstantCacheTestCase.set_up(self)
        self.entity_cls = RackShape
        self.cache_cls = RACK_SHAPE_NAMES
        self.from_name_meth = RACK_SHAPE_NAMES.from_name

    def test_from_name(self):
        self._test_from_name()

    def test_shortcuts(self):
        self._test_shortcut(get_96_rack_shape, RACK_SHAPE_NAMES.SHAPE_96,
                            num_rows=8, num_cols=12)
        self._test_shortcut(get_384_rack_shape, RACK_SHAPE_NAMES.SHAPE_384,
                            num_rows=16, num_cols=24)

    #pylint: disable=W0221
    def _test_shortcut(self, shortcut_meth, exp_name, num_rows, num_cols):
        shape = _SemiConstantCacheTestCase._test_shortcut(self, shortcut_meth,
                                                          exp_name)
        self.assert_equal(shape.number_rows, num_rows)
        self.assert_equal(shape.number_columns, num_cols)
    #pylint: enable=W0221


    def test_from_position_count(self):
        shape96 = RACK_SHAPE_NAMES.from_positions_count(96)
        self.assert_true(isinstance(shape96, RackShape))
        self.assert_equal(shape96.name, RACK_SHAPE_NAMES.SHAPE_96)
        shape384 = RACK_SHAPE_NAMES.from_positions_count(384)
        self.assert_true(isinstance(shape384, RackShape))
        self.assert_equal(shape384.name, RACK_SHAPE_NAMES.SHAPE_384)
        self.assert_raises(ValueError,
                    RACK_SHAPE_NAMES.from_positions_count, 12)

    def test_get_positions_for_rack_shape(self):
        attrs = dict(number_rows=2, number_columns=2, name='2x2', label='2x2')
        shape = self._create_rack_shape(**attrs)
        vert_positions = get_positions_for_shape(shape, vertical_sorting=True)
        exp_verts = ['A1', 'B1', 'A2', 'B2']
        self.assert_equal(len(vert_positions), len(exp_verts))
        for i in range(len(vert_positions)):
            pos_label = vert_positions[i].label
            self.assert_equal(pos_label, exp_verts[i])
        hori_positions = get_positions_for_shape(shape, vertical_sorting=False)
        exp_horis = ['A1', 'A2', 'B1', 'B2']
        self.assert_equal(len(hori_positions), len(exp_horis))
        for i in range(len(hori_positions)):
            pos_label = hori_positions[i].label
            self.assert_equal(pos_label, exp_horis[i])


class ItemStatusUtilsTestCase(_SemiConstantCacheTestCase):

    def set_up(self):
        _SemiConstantCacheTestCase.set_up(self)
        self.entity_cls = ItemStatus
        self.cache_cls = ITEM_STATUS_NAMES
        self.from_name_meth = get_item_status

    def test_from_name(self):
        self._test_from_name()

    def test_shortcuts(self):
        self._test_shortcut(get_item_status_managed, ITEM_STATUS_NAMES.MANAGED)
        self._test_shortcut(get_item_status_future, ITEM_STATUS_NAMES.FUTURE)


class ExperimentScenariosTestCase(_SemiConstantCacheTestCase):

    def set_up(self):
        _SemiConstantCacheTestCase.set_up(self)
        self.entity_cls = ExperimentMetadataType
        self.cache_cls = EXPERIMENT_SCENARIOS
        self.from_name_meth = get_experiment_metadata_type
        self.comp_attr_name = 'id'

    def test_from_name(self):
        self._test_from_name()

    def test_shortcuts(self):
        self._test_shortcut(get_experiment_type_robot_optimisation,
                            EXPERIMENT_SCENARIOS.OPTIMISATION)
        self._test_shortcut(get_experiment_type_manual_optimisation,
                            EXPERIMENT_SCENARIOS.MANUAL)
        self._test_shortcut(get_experiment_type_screening,
                            EXPERIMENT_SCENARIOS.SCREENING)
        self._test_shortcut(get_experiment_type_library,
                            EXPERIMENT_SCENARIOS.LIBRARY)
        self._test_shortcut(get_experiment_type_isoless,
                            EXPERIMENT_SCENARIOS.ISO_LESS)
        self._test_shortcut(get_experiment_type_order,
                            EXPERIMENT_SCENARIOS.ORDER_ONLY)
