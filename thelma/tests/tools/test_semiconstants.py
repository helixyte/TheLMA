"""
Tests for semiconstant classes.

AAB
"""
from everest.entities.utils import get_root_aggregate
from everest.repositories.rdb.utils import as_slug_expression
from thelma.automation.tools.semiconstants \
    import get_experiment_type_manual_optimisation
from thelma.automation.tools.semiconstants \
    import get_experiment_type_robot_optimisation
from thelma.automation.tools.semiconstants \
    import get_plate_specs_from_reservoir_specs
from thelma.automation.tools.semiconstants \
    import get_reservoir_specs_from_plate_specs
from thelma.automation.tools.semiconstants \
    import get_reservoir_specs_standard_384
from thelma.automation.tools.semiconstants \
    import get_reservoir_specs_standard_96
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.tools.semiconstants import PLATE_SPECS_NAMES
from thelma.automation.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.tools.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.tools.semiconstants import get_384_rack_shape
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_experiment_type_isoless
from thelma.automation.tools.semiconstants import get_experiment_type_library
from thelma.automation.tools.semiconstants import get_experiment_type_order
from thelma.automation.tools.semiconstants import get_experiment_type_screening
from thelma.automation.tools.semiconstants import get_item_status_future
from thelma.automation.tools.semiconstants import get_item_status_managed
from thelma.automation.tools.semiconstants import get_positions_for_shape
from thelma.automation.tools.semiconstants import get_reservoir_spec
from thelma.automation.tools.semiconstants import get_reservoir_specs_deep_96
from thelma.interfaces import IPlateSpecs
from thelma.models.experiment import ExperimentMetadataType
from thelma.models.liquidtransfer import ReservoirSpecs
from thelma.models.rack import PlateSpecs
from thelma.models.rack import RackShape
from thelma.models.status import ItemStatus
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase


class ReservoirSpecsNamesTestCase(ToolsAndUtilsTestCase):

    def test_from_name(self):
        for rs_name in RESERVOIR_SPECS_NAMES.ALL:
            self.assert_true(RESERVOIR_SPECS_NAMES.is_known_entity(rs_name))
            rs = get_reservoir_spec(rs_name)
            self.assert_is_not_none(rs)
            self.assert_true(isinstance(rs, ReservoirSpecs))
        self.assert_raises(ValueError, get_reservoir_spec, 'wrong_name')
        self.assert_false(RESERVOIR_SPECS_NAMES.is_known_entity('wrong_name'))

    def test_shortcuts(self):
        rs_std_96 = get_reservoir_specs_standard_96()
        self.assert_is_not_none(rs_std_96)
        self.assert_true(isinstance(rs_std_96, ReservoirSpecs))
        self.assert_equal(rs_std_96.name, RESERVOIR_SPECS_NAMES.STANDARD_96)
        rs_std_384 = get_reservoir_specs_standard_384()
        self.assert_is_not_none(rs_std_384)
        self.assert_true(isinstance(rs_std_384, ReservoirSpecs))
        self.assert_equal(rs_std_384.name, RESERVOIR_SPECS_NAMES.STANDARD_384)
        rs_deep_96 = get_reservoir_specs_deep_96()
        self.assert_is_not_none(rs_deep_96)
        self.assert_true(isinstance(rs_deep_96, ReservoirSpecs))
        self.assert_equal(rs_deep_96.name, RESERVOIR_SPECS_NAMES.DEEP_96)

    def test_is_plate(self):
        rs_std_96 = get_reservoir_specs_standard_96()
        self.assert_true(RESERVOIR_SPECS_NAMES.is_plate_spec(rs_std_96))
        self.assert_true(RESERVOIR_SPECS_NAMES.is_plate_spec(rs_std_96.name))
        rs_std_384 = get_reservoir_specs_standard_384()
        self.assert_true(RESERVOIR_SPECS_NAMES.is_plate_spec(rs_std_384))
        self.assert_true(RESERVOIR_SPECS_NAMES.is_plate_spec(rs_std_384.name))
        rs_dp_96 = get_reservoir_specs_deep_96()
        self.assert_true(RESERVOIR_SPECS_NAMES.is_plate_spec(rs_dp_96))
        self.assert_true(RESERVOIR_SPECS_NAMES.is_plate_spec(rs_dp_96.name))
        falcon_rs = get_reservoir_spec(RESERVOIR_SPECS_NAMES.FALCON_MANUAL)
        self.assert_false(RESERVOIR_SPECS_NAMES.is_plate_spec(falcon_rs))
        self.assert_false(RESERVOIR_SPECS_NAMES.is_plate_spec(falcon_rs))
        self.assert_raises(TypeError, RESERVOIR_SPECS_NAMES.is_plate_spec, 4)
        self.assert_raises(ValueError, RESERVOIR_SPECS_NAMES.is_plate_spec,
                           'invalid')


class PlateSpecsNamesTestCase(ToolsAndUtilsTestCase):

    def test_from_name(self):
        for ps_name in PLATE_SPECS_NAMES.ALL:
            self.assert_true(PLATE_SPECS_NAMES.is_known_entity(ps_name))
            ps = PLATE_SPECS_NAMES.from_name(ps_name)
            self.assert_is_not_none(ps)
            self.assert_true(isinstance(ps, PlateSpecs))
        self.assert_raises(ValueError, PLATE_SPECS_NAMES.from_name, 'invalid')
        self.assert_false(PLATE_SPECS_NAMES.is_known_entity('invalid'))

    def test_from_reservoir_specs(self):
        test_names = \
            {RESERVOIR_SPECS_NAMES.STANDARD_96 : PLATE_SPECS_NAMES.STANDARD_96,
             RESERVOIR_SPECS_NAMES.STANDARD_384 : PLATE_SPECS_NAMES.STANDARD_384,
             RESERVOIR_SPECS_NAMES.DEEP_96 : PLATE_SPECS_NAMES.DEEP_96}
        for rs_name, plate_specs_name in test_names.iteritems():
            rs = get_reservoir_spec(rs_name)
            for token in [rs, rs_name]:
                plate_specs = get_plate_specs_from_reservoir_specs(token)
                self.assert_is_not_none(plate_specs)
                self.assert_true(isinstance(plate_specs, PlateSpecs))
                self.assert_equal(plate_specs.name, plate_specs_name)
        self.assert_raises(TypeError, get_plate_specs_from_reservoir_specs, 3)
        self.assert_raises(ValueError, get_plate_specs_from_reservoir_specs,
                           'invalid')

    def test_to_reservoir_specs(self):
        std_96 = PLATE_SPECS_NAMES.from_name(PLATE_SPECS_NAMES.STANDARD_96)
        rs_96 = get_reservoir_specs_from_plate_specs(std_96)
        self.assert_equal(rs_96.name, RESERVOIR_SPECS_NAMES.STANDARD_96)
        ps_agg = get_root_aggregate(IPlateSpecs)
        nunc = ps_agg.get_by_slug(as_slug_expression('NUNCV96'))
        self.assert_is_not_none(nunc)
        self.assert_raises(ValueError, get_reservoir_specs_from_plate_specs,
                           nunc)


class RackShapesNamesTestCase(ToolsAndUtilsTestCase):

    def test_from_name(self):
        name96 = RACK_SHAPE_NAMES.SHAPE_96
        self.assert_true(RACK_SHAPE_NAMES.is_known_entity(name96))
        shape96 = RACK_SHAPE_NAMES.from_name(name96)
        self.assert_true(isinstance(shape96, RackShape))
        self.assert_equal(shape96.number_rows, 8)
        self.assert_equal(shape96.number_columns, 12)
        name384 = RACK_SHAPE_NAMES.SHAPE_384
        self.assert_true(RACK_SHAPE_NAMES.is_known_entity(name384))
        shape384 = RACK_SHAPE_NAMES.from_name(RACK_SHAPE_NAMES.SHAPE_384)
        self.assert_true(isinstance(shape384, RackShape))
        self.assert_equal(shape384.number_rows, 16)
        self.assert_equal(shape384.number_columns, 24)
        self.assert_false(RACK_SHAPE_NAMES.is_known_entity('inv'))
        self.assert_raises(ValueError, RACK_SHAPE_NAMES.from_name, 'inv')

    def test_from_position_count(self):
        shape96 = RACK_SHAPE_NAMES.from_positions_count(96)
        self.assert_true(isinstance(shape96, RackShape))
        self.assert_equal(shape96.number_rows, 8)
        self.assert_equal(shape96.number_columns, 12)
        shape384 = RACK_SHAPE_NAMES.from_positions_count(384)
        self.assert_true(isinstance(shape384, RackShape))
        self.assert_equal(shape384.number_rows, 16)
        self.assert_equal(shape384.number_columns, 24)
        self.assert_raises(ValueError,
                    RACK_SHAPE_NAMES.from_positions_count, 12)

    def test_shortcuts(self):
        shape96 = RACK_SHAPE_NAMES.from_name(RACK_SHAPE_NAMES.SHAPE_96)
        self.assert_equal(shape96, get_96_rack_shape())
        shape384 = RACK_SHAPE_NAMES.from_name(RACK_SHAPE_NAMES.SHAPE_384)
        self.assert_equal(shape384, get_384_rack_shape())

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


class ItemStatusUtilsTestCase(ToolsAndUtilsTestCase):

    def test_from_name(self):
        for status_name in ITEM_STATUS_NAMES.ALL:
            self.assert_true(ITEM_STATUS_NAMES.is_known_entity(status_name))
            entity = ITEM_STATUS_NAMES.from_name(status_name)
            self.assert_is_not_none(entity)
            self.assert_true(isinstance(entity, ItemStatus))
        self.assert_false(ITEM_STATUS_NAMES.is_known_entity('invalid'))
        self.assert_raises(ValueError, ITEM_STATUS_NAMES.from_name,
                           'invalid')

    def test_shortcuts(self):
        status_managed = get_item_status_managed()
        self.assert_is_not_none(status_managed)
        self.assert_true(isinstance(status_managed, ItemStatus))
        self.assert_equal(status_managed.name, ITEM_STATUS_NAMES.MANAGED)
        status_future = get_item_status_future()
        self.assert_is_not_none(status_future)
        self.assert_true(isinstance(status_future, ItemStatus))
        self.assert_equal(status_future.name, ITEM_STATUS_NAMES.FUTURE)


class ExperimentScenariosTestCase(ToolsAndUtilsTestCase):

    def test_from_name(self):
        for em_type_id in EXPERIMENT_SCENARIOS.ALL:
            self.assert_true(EXPERIMENT_SCENARIOS.is_known_entity(em_type_id))
            entity = EXPERIMENT_SCENARIOS.from_name(em_type_id)
            self.assert_is_not_none(entity)
            self.assert_true(isinstance(entity, ExperimentMetadataType))
        self.assert_false(EXPERIMENT_SCENARIOS.is_known_entity('invalid'))
        self.assert_raises(ValueError, EXPERIMENT_SCENARIOS.from_name,
                           'invalid')

    def test_shortcuts(self):
        type_opti = get_experiment_type_robot_optimisation()
        self.__test_shortcut(type_opti, EXPERIMENT_SCENARIOS.OPTIMISATION)
        type_screen = get_experiment_type_screening()
        self.__test_shortcut(type_screen, EXPERIMENT_SCENARIOS.SCREENING)
        type_manual = get_experiment_type_manual_optimisation()
        self.__test_shortcut(type_manual, EXPERIMENT_SCENARIOS.MANUAL)
        type_library = get_experiment_type_library()
        self.__test_shortcut(type_library, EXPERIMENT_SCENARIOS.LIBRARY)
        type_isoless = get_experiment_type_isoless()
        self.__test_shortcut(type_isoless, EXPERIMENT_SCENARIOS.ISO_LESS)
        type_order = get_experiment_type_order()
        self.__test_shortcut(type_order, EXPERIMENT_SCENARIOS.ORDER_ONLY)

    def __test_shortcut(self, em_type, exp_id):
        self.assert_is_not_none(em_type)
        self.assert_true(isinstance(em_type, ExperimentMetadataType))
        self.assert_equal(em_type.id, exp_id)

