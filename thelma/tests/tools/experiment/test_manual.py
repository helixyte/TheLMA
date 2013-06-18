"""
Test case for manual experiment updating (experiment rack filler classes)
"""
from everest.testing import check_attributes
from thelma.automation.tools.experiment.manual \
    import ExperimentRackFillerIsoLess
from thelma.automation.tools.experiment.manual \
    import ExperimentRackFillerOptimisation
from thelma.automation.tools.experiment.manual import ExperimentRackFiller
from thelma.automation.tools.experiment.manual import ExperimentRackFillerManual
from thelma.automation.tools.experiment.manual import ExperimentRackFillerScreen
from thelma.automation.tools.experiment.manual import SampleInfoItem
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionParameters
from thelma.automation.tools.semiconstants \
    import get_experiment_type_manual_optimisation
from thelma.automation.tools.semiconstants \
    import get_experiment_type_robot_optimisation
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.tools.semiconstants import get_experiment_type_isoless
from thelma.automation.tools.semiconstants import get_experiment_type_order
from thelma.automation.tools.semiconstants import get_experiment_type_screening
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.interfaces import IMolecule
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.liquidtransfer import WorklistSeries
from thelma.models.racklayout import RackLayout
from thelma.tests.tools.experiment.base import ExperimentToolTestCase
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase


class SampleInfoItemTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.rack_pos = get_rack_position_from_label('A1')
        self.molecule = self._create_molecule()
        self.concentration = 50
        self.init_data = dict(rack_position=self.rack_pos,
                              molecule=self.molecule,
                              concentration=self.concentration)

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.rack_pos
        del self.molecule
        del self.concentration
        del self.init_data

    def test_init(self):
        sii = SampleInfoItem(self.rack_pos, self.molecule, self.concentration)
        self.assert_not_equal(sii, None)
        check_attributes(sii, self.init_data)

    def test_equality(self):
        sii1 = SampleInfoItem(**self.init_data)
        sii2 = SampleInfoItem(**self.init_data)
        other_pos = get_rack_position_from_label('B2')
        sii3 = SampleInfoItem(other_pos, self.molecule, self.concentration)
        other_mol = self._get_entity(IMolecule)
        sii4 = SampleInfoItem(self.rack_pos, other_mol, self.concentration)
        sii5 = SampleInfoItem(self.rack_pos, self.molecule, 100)
        self.assert_equal(sii1, sii2)
        self.assert_not_equal(sii1, sii3)
        self.assert_not_equal(sii1, sii4)
        self.assert_not_equal(sii1, sii5)
        self.assert_not_equal(sii1, self.molecule)


class RackFillerTestCase(ExperimentToolTestCase):
    """
    Used by the single and the batch test case.
    """

    def set_up(self):
        ExperimentToolTestCase.set_up(self)
        self.rack_filler_cls = None

    def tear_down(self):
        ExperimentToolTestCase.tear_down(self)
        del self.rack_filler_cls

    def _create_tool(self):
        self.tool = ExperimentRackFiller.create(log=self.log,
                    experiment=self.experiment, user=self.executor_user)

    def _create_tool_without_factory(self):
        #pylint: disable=E1102
        self.tool = self.rack_filler_cls(log=self.log,
                    experiment=self.experiment, user=self.executor_user)
        #pylint: enable=E1102

    def _check_result(self, experiment=None):
        if experiment is None: experiment = self.tool.get_result()
        self.assert_is_not_none(experiment)
        self.__check_experiment_design_worklists(experiment)
        self._check_design_racks()
        if not self.experiment_type.id == EXPERIMENT_SCENARIOS.ISO_LESS:
            self.__check_iso_plate(experiment)
        self.__check_experiment_plates(experiment)

    def __check_experiment_design_worklists(self, experiment):
        worklist_series = experiment.experiment_design.worklist_series
        if self.experiment_type.id == EXPERIMENT_SCENARIOS.MANUAL or \
                self.experiment_type.id == EXPERIMENT_SCENARIOS.ISO_LESS:
            self.assert_is_none(worklist_series)
        elif self.experiment_type.id == EXPERIMENT_SCENARIOS.OPTIMISATION and \
                        not self.supports_mastermix:
            self.assert_is_none(worklist_series)
        else:
            optimem_worklist = None
            reagent_worklist = None
            for worklist in worklist_series:
                if worklist.index == 0:
                    optimem_worklist = worklist
                elif worklist.index == 1:
                    reagent_worklist = worklist
            if not self.supports_mastermix:
                self.assert_is_none(optimem_worklist)
                self.assert_is_none(reagent_worklist)
            else:
                self.assert_equal(len(optimem_worklist.executed_worklists), 0)
                self.assert_equal(len(reagent_worklist.executed_worklists), 0)
            if self.experiment_type.id == EXPERIMENT_SCENARIOS.OPTIMISATION:
                self.assert_equal(len(worklist_series), 2) # supports mm
            elif self.supports_mastermix:
                self.assert_equal(len(worklist_series), 4)
            else:
                self.assert_equal(len(worklist_series), 2)

    def _check_design_racks(self):
        worklists = dict()
        design_racks = self.experiment_metadata.experiment_design.design_racks
        for design_rack in design_racks:
            series = design_rack.worklist_series
            for worklist in series:
                if worklist.index == 0:
                    worklists[design_rack.label] = worklist
        self.assert_equal(len(worklists), len(design_racks))
        for drack_label, worklist in worklists.iteritems():
            self.assert_equal(len(worklist.executed_worklists),
                              self.number_replicates * self.number_experiments)
            wl_type = TRANSFER_TYPES.CONTAINER_TRANSFER
            for ew in worklist.executed_worklists:
                timestamp = None
                if drack_label == '1':
                    num_et = len(self.result_data_common) + len(self.result_d1)
                else:
                    num_et = len(self.result_data_common) + len(self.result_d2)
                self.assert_equal(len(ew.executed_transfers), num_et)
                for et in ew.executed_transfers:
                    self.assert_equal(et.type, wl_type)
                    self.assert_equal(et.user.username,
                                      self.executor_user.username)
                    if timestamp is None:
                        timestamp = et.timestamp
                    else:
                        self.assert_equal(timestamp, et.timestamp)

    def __check_iso_plate(self, experiment):
        for container in experiment.source_rack.containers:
            rack_pos = container.location.position
            iso_pos = self.iso_layout.get_working_position(rack_pos)
            sample = container.sample
            if iso_pos is None or (iso_pos.is_floating and \
                   not self.floating_map.has_key(iso_pos.molecule_design_pool)):
                self.assert_is_none(sample)
                continue
            if iso_pos.is_mock: continue
            self._compare_sample_volume(sample, iso_pos.iso_volume)
            if iso_pos.is_mock:
                continue
            elif iso_pos.is_fixed:
                pool = iso_pos.molecule_design_pool
            else:
                placeholder = iso_pos.molecule_design_pool
                pool_id = self.floating_map[placeholder]
                pool = self._get_pool(pool_id)
            conc = iso_pos.iso_concentration / len(pool)
            self._compare_sample_and_pool(sample, pool, conc)

    def __check_experiment_plates(self, experiment):
        exp_vol = TransfectionParameters.TRANSFER_VOLUME \
                  * TransfectionParameters.CELL_DILUTION_FACTOR
        for exp_rack in experiment.experiment_racks:
            plate = exp_rack.rack
            self.assert_equal(plate.status.name, ITEM_STATUS_NAMES.MANAGED)
            if exp_rack.design_rack.label == '1':
                add_results = self.result_d1
            else:
                add_results = self.result_d2
            for container in plate.containers:
                sample = container.sample
                pos_label = container.location.position.label
                if self.result_data_common.has_key(pos_label):
                    data_tuple = self.result_data_common[pos_label]
                elif self.experiment_type.id \
                                        == EXPERIMENT_SCENARIOS.OPTIMISATION \
                                        and add_results.has_key(pos_label):
                    data_tuple = add_results[pos_label]
                else:
                    if not sample is None:
                        raise ValueError(pos_label)
                    self.assert_is_none(sample)
                    continue
                exp_pool_id = data_tuple[0]
                self._compare_sample_volume(sample, exp_vol)
                if exp_pool_id is None: # mock
                    self.assert_equal(len(sample.sample_molecules), 0)
                else:
                    md_pool = self._get_pool(exp_pool_id)
                    conc = float(data_tuple[1]) / len(md_pool)
                    self._compare_sample_and_pool(sample, md_pool, conc)

    def _test_no_design_rack_worklist_series(self):
        self._continue_setup()
        drack = self.experiment_metadata.experiment_design.design_racks[0]
        drack.worklist_series = WorklistSeries()
        self._test_and_expect_errors('Could not find transfer worklist ' \
                                     'for design rack')

    def _test_missing_molecule_in_iso_rack(self):
        self._continue_setup()
        for container in self.iso_rack.containers:
            container.make_sample(10 / VOLUME_CONVERSION_FACTOR)
        self._test_and_expect_errors('Could not find molecules for the ' \
                                     'following ISO positions')

    def _test_invalid_experiment(self):
        kw = dict(experiment=self.experiment, user=self.executor_user,
                  log=self.log)
        # pylint: disable=W0142
        self.assert_raises(ValueError, ExperimentRackFiller.create, **kw)
        # pylint: enable=W0142
        self._create_tool_without_factory()
        result = self.tool.get_result()
        self.assert_is_none(result)
        self._check_error_messages('')

    def _test_invalid_experiment_type(self):
        self._continue_setup()
        self.experiment_metadata.experiment_metadata_type = \
                                                get_experiment_type_order()
        kw = dict(experiment=self.experiment, user=self.executor_user,
                  log=self.log)
        # pylint: disable=W0142
        self.assert_raises(KeyError, ExperimentRackFiller.create, **kw)
        # pylint: enable=W0142
        self._create_tool_without_factory()
        result = self.tool.get_result()
        self.assert_is_none(result)
        self._check_error_messages('The type of this experiment is not ' \
                       'supported by this tool (given: ISO without experiment')

    def _test_invalid_design_rack_layout(self):
        self._continue_setup()
        drack = self.experiment_metadata.experiment_design.design_racks[0]
        drack.layout = RackLayout()
        self._test_and_expect_errors('Could not get design layout')


class ExperimentRackFillerOptimisationTestCase(RackFillerTestCase):

    def set_up(self):
        RackFillerTestCase.set_up(self)
        self.experiment_type = get_experiment_type_robot_optimisation()
        self.rack_filler_cls = ExperimentRackFillerOptimisation

    def test_result_with_mastermix(self):
        self._continue_setup()
        self._check_result()
        self._check_warning_messages('This experiment is robot-compatible.')

    def test_result_without_mastermix(self):
        self.supports_mastermix = False
        self._continue_setup()
        self._check_result()

    def test_result_empty_floatings(self):
        del self.floating_map['md_003']
        self.result_d2 = {}
        self._continue_setup()
        self._check_result()
        self._check_warning_messages('This experiment is robot-compatible.')

    def test_result_no_mastermix_empty_floatings(self):
        self.supports_mastermix = False
        del self.floating_map['md_003']
        self.result_d2 = {}
        self._continue_setup()
        self._check_result()

    def test_no_sample_for_mocks(self):
        self.supports_mastermix = False
        self._init_missing_mock_sample()
        self._check_result()

    def test_invalid_experiment(self):
        self._test_invalid_experiment()

    def test_invalid_experiment_type(self):
        self._test_invalid_experiment_type()

    def test_previous_execution(self):
        self._test_previous_execution()

    def test_no_design_rack_worklist_series(self):
        self._test_no_design_rack_worklist_series()

    def test_missing_molecule_in_iso_rack(self):
        self._test_missing_molecule_in_iso_rack()

    def test_invalid_iso_layout(self):
        self._test_invalid_iso_layout()

    def test_invalid_design_rack_layout(self):
        self._test_invalid_design_rack_layout()

    def test_missing_control_sample(self):
        self._test_missing_control_sample()


class ExperimentRackFillerScreenTestCase(RackFillerTestCase):

    def set_up(self):
        RackFillerTestCase.set_up(self)
        self.experiment_type = get_experiment_type_screening()
        self.rack_filler_cls = ExperimentRackFillerScreen

    def _check_design_racks(self):
        for drack in self.experiment_metadata.experiment_design.design_racks:
            self.assert_is_none(drack.worklist_series)

    def test_result_with_mastermix(self):
        self._continue_setup()
        self._check_result()
        self._check_warning_messages('This experiment is robot-compatible.')

    def test_result_no_mastermix(self):
        self.supports_mastermix = False
        self._continue_setup()
        self._check_result()

    def test_result_empty_floating(self):
        del self.floating_map_screen['md_001']
        del self.result_data_screen['C17']
        del self.result_data_screen['C18']
        del self.result_data_screen['D17']
        self._continue_setup()
        self._check_result()

    def test_result_no_sample_for_mock(self):
        self.supports_mastermix = False
        self._init_missing_mock_sample()
        self._check_result()

    def test_invalid_experiment(self):
        self._test_invalid_experiment()

    def test_invalid_experiment_type(self):
        self._test_invalid_experiment_type()

    def test_previous_execution(self):
        self._test_previous_execution()

    def test_missing_molecule_in_iso_rack(self):
        self._test_missing_molecule_in_iso_rack()

    def test_invalid_iso_layout(self):
        self._test_invalid_iso_layout()

    def test_missing_control_sample(self):
        self._test_missing_control_sample()


class ExperimentRackFillerManualTestCase(RackFillerTestCase):

    def set_up(self):
        RackFillerTestCase.set_up(self)
        self.experiment_type = get_experiment_type_manual_optimisation()
        self.rack_filler_cls = ExperimentRackFillerManual

    def test_result(self):
        self._continue_setup()
        self._check_result()

    def test_no_sample_for_mocks(self):
        self.supports_mastermix = False
        self._init_missing_mock_sample()
        self._check_result()

    def test_invalid_experiment(self):
        self._test_invalid_experiment()

    def test_invalid_experiment_type(self):
        self._test_invalid_experiment_type()

    def test_previous_execution(self):
        self._test_previous_execution()

    def test_no_design_rack_worklist_series(self):
        self._test_no_design_rack_worklist_series()

    def test_missing_molecule_in_iso_rack(self):
        self._test_missing_molecule_in_iso_rack()

    def test_invalid_iso_layout(self):
        self._test_invalid_iso_layout()

    def test_invalid_design_rack_layout(self):
        self._test_invalid_design_rack_layout()

    def test_missing_control_sample(self):
        self._test_missing_control_sample(msg='Could not find samples for ' \
                      'the following positions in the ISO rack: B2, C2, D2.')


class ExperimentRackFillerIsolessTestCase(RackFillerTestCase):

    def set_up(self):
        RackFillerTestCase.set_up(self)
        self.experiment_type = get_experiment_type_isoless()
        self.rack_filler_cls = ExperimentRackFillerIsoLess

    def _check_design_racks(self):
        design_racks = self.experiment_metadata.experiment_design.design_racks
        for design_rack in design_racks:
            self.assert_is_none(design_rack.worklist_series)

    def test_result(self):
        self._continue_setup()
        self._check_result()

    def test_invalid_experiment(self):
        self._test_invalid_experiment()

    def test_invalid_experiment_type(self):
        self._test_invalid_experiment_type()

    def test_previous_execution(self):
        self._test_previous_execution(msg='The database update for ' \
                'experiment "test_Experiment" has already been made before!')
