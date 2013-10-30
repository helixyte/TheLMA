"""
Tests the experiment liquid transfer plan tools.
AAB Aug 08, 2011
"""

from everest.entities.utils import get_root_aggregate
from thelma.automation.handlers.experimentdesign \
    import ExperimentDesignParserHandler
from thelma.automation.handlers.isorequest import IsoRequestParserHandler
from thelma.automation.semiconstants \
    import get_experiment_type_robot_optimisation
from thelma.automation.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.semiconstants import PIPETTING_SPECS_NAMES
from thelma.automation.semiconstants import get_experiment_type_library
from thelma.automation.semiconstants import get_experiment_type_screening
from thelma.automation.tools.metadata.base import TransfectionParameters
from thelma.automation.tools.metadata.generation \
    import WellAssociatorOptimisation
from thelma.automation.tools.metadata.worklist \
    import EXPERIMENT_WORKLIST_PARAMETERS
from thelma.automation.tools.metadata.worklist \
    import ExperimentWorklistGenerator
from thelma.automation.tools.metadata.worklist \
    import _BiomekTransferWorklistGenerator
from thelma.automation.tools.metadata.worklist \
    import _CellSuspensionWorklistGenerator
from thelma.automation.tools.metadata.worklist \
    import _CybioTransferWorklistGenerator
from thelma.automation.tools.metadata.worklist import _OptimemWorklistGenerator
from thelma.automation.tools.metadata.worklist import _ReagentWorklistGenerator
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.interfaces import IMoleculeType
from thelma.interfaces import IUser
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.tests.tools.tooltestingutils import FileReadingTestCase
from thelma.tests.tools.tooltestingutils import SilentLog
from thelma.tests.tools.tooltestingutils import TestingLog


class _ExperimentWorklistSeriesTestCase(FileReadingTestCase):

    def set_up(self):
        FileReadingTestCase.set_up(self)
        self.TEST_FILE_PATH = 'thelma:tests/tools/metadata/worklist/'
        self.VALID_FILES = {
                        EXPERIMENT_SCENARIOS.OPTIMISATION : 'valid_opti.xls',
                        EXPERIMENT_SCENARIOS.SCREENING : 'valid_screen.xls',
                        EXPERIMENT_SCENARIOS.MANUAL : 'valid_manual.xls',
                        EXPERIMENT_SCENARIOS.LIBRARY : 'valid_library.xls'}
        self.log = TestingLog()
        self.silent_log = SilentLog()
        self.user = self._get_entity(IUser, 'it')
        self.molecule_type = get_root_aggregate(IMoleculeType).\
                             get_by_id('SIRNA')
        self.experiment_type = get_experiment_type_robot_optimisation()
        self.experiment_metadata_label = 'Worklist Generator Test'
        self.label = None
        self.experiment_design = None
        self.number_replicates = 3
        self.design_rack_label = '1'
        self.transfection_layout = None
        self.default_optimem_df = 4 # and 5 for library cases
        self.design_rack_associations = None
        # result data optimisation (ISO volume and conc are set)
        self.optimem_volumes = dict(B2=56.4, B4=56.4, B6=37.6,
                                    D2=101.4, D3=101.4, D4=101.4,
                                    G2=56.4, G4=56.4, G6=37.6,
                                    B8=29.7, G8=29.7)
        self.reagent_infos = {
                        'RNAi Mix (1400)' : set(['B2', 'B4', 'B6', 'B8',
                                                 'D2', 'D3', 'D4']),
                        'RNAi Mix (2800)' : set(['G2', 'G4', 'G6', 'G8'])}
        self.reagent_volumes = dict(B2=75.2, B4=75.2, B6=56.4,
                                    D2=135.2, D3=135.2, D4=135.2,
                                    G2=75.2, G4=75.2, G6=56.4,
                                    B8=39.6, G8=39.6)
        self.biomek_sources = dict(B2='B2', B3='B2', B4='B4', B5='B4',
                                   B6='B6', B7='B6', B9='B8',
                                   D2='D2', D3='D2', E2='D2', E3='D2',
                                   D4='D3', D5='D3', E4='D3', E5='D3',
                                   D6='D4', D7='D4', E6='D4', E7='D4',
                                   G2='G2', G3='G2', G4='G4', G5='G4',
                                   G6='G6', G7='G6', G9='G8')
        self.cell_positions = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B9',
                               'D2', 'D3', 'D4', 'D5', 'D6', 'D7',
                               'E2', 'E3', 'E4', 'E5', 'E6', 'E7',
                               'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G9']
        # result data screen
        self.screen_optimem_volume = 3
        self.screen_reagent_volume = 4
        self.screen_reagent_info = 'Mix1 (600)'
        self.screen_cell_positions = ['B2', 'B3', 'C2', 'C3',
                                      'D2', 'D3', 'E2', 'E3']
        # result data library - we set the ODF to 5 in the course of the setup
        self.library_optimem_volume = 16
        self.library_reagent_volume = 20
        self.library_reagent_info = 'RNAiMax (1400)'
        self.library_num_transfers = 288

    def tear_down(self):
        FileReadingTestCase.tear_down(self)
        del self.VALID_FILES
        del self.log
        del self.silent_log
        del self.molecule_type
        del self.experiment_type
        del self.experiment_metadata_label
        del self.label
        del self.experiment_design
        del self.number_replicates
        del self.design_rack_label
        del self.transfection_layout
        del self.default_optimem_df
        del self.design_rack_associations
        del self.optimem_volumes
        del self.reagent_infos
        del self.reagent_volumes
        del self.biomek_sources
        del self.screen_optimem_volume
        del self.screen_reagent_volume
        del self.screen_cell_positions
        del self.screen_reagent_info
        del self.library_optimem_volume
        del self.library_reagent_volume
        del self.library_reagent_info
        del self.library_num_transfers

    def _continue_setup(self, file_name=None):
        if file_name is None:
            file_name = self.VALID_FILES[self.experiment_type.id]
        FileReadingTestCase._continue_setup(self, file_name)
        self.__read_experiment_design()
        self.__read_iso_request()
        if self.experiment_type.id == EXPERIMENT_SCENARIOS.OPTIMISATION:
            self.__associate_opti_layouts()
        self._create_tool()

    def __read_experiment_design(self):
        handler = ExperimentDesignParserHandler(stream=self.stream,
                    log=self.silent_log, requester=self.user,
                    scenario=self.experiment_type)
        self.experiment_design = handler.get_result()

    def __read_iso_request(self):
        handler = IsoRequestParserHandler.create(stream=self.stream,
                    requester=self.user, log=self.silent_log,
                    experiment_type_id=self.experiment_type.id)
        handler.get_result()
        self.transfection_layout = handler.get_transfection_layout()
        is_library_scenario = (self.experiment_type.id == \
                               EXPERIMENT_SCENARIOS.LIBRARY)
        if self.experiment_type.id == EXPERIMENT_SCENARIOS.LIBRARY:
            self.default_optimem_df = 5
        for tf_pos in self.transfection_layout.working_positions():
            if tf_pos.is_untreated_type: continue
            if tf_pos.is_fixed:
                if is_library_scenario:
                    tf_pos.set_optimem_dilution_factor(self.default_optimem_df)
                else:
                    tf_pos.store_optimem_dilution_factor()
            elif tf_pos.is_floating or tf_pos.is_mock or tf_pos.is_library:
                tf_pos.set_optimem_dilution_factor(self.default_optimem_df)
            if is_library_scenario:
                tf_pos.iso_volume = 4
                if tf_pos.is_mock: continue
                tf_pos.iso_concentration = 1270

    def __associate_opti_layouts(self):
        associator = WellAssociatorOptimisation(
                                experiment_design=self.experiment_design,
                                source_layout=self.transfection_layout,
                                log=self.silent_log)
        self.design_rack_associations = associator.get_result()
        self.transfection_layout = associator.get_completed_source_layout()

    def _test_optimem_worklist(self, worklist=None):
        if worklist is None: worklist = self.tool.get_result()
        exp_transfer_type = TRANSFER_TYPES.SAMPLE_DILUTION
        self.assert_is_not_none(worklist)
        self.assert_true(isinstance(worklist, PlannedWorklist))
        self.assert_equal(len(worklist.executed_worklists), 0)
        label = '%s_optimem' % (self.experiment_metadata_label)
        self.assert_equal(worklist.label, label)
        self.assert_equal(worklist.transfer_type, exp_transfer_type)
        self.assert_equal(worklist.pipetting_specs.name,
                          PIPETTING_SPECS_NAMES.BIOMEK)
        plts = worklist.planned_liquid_transfers
        if self.experiment_type.id == EXPERIMENT_SCENARIOS.OPTIMISATION:
            exp_num_transfers = len(self.optimem_volumes)
        elif self.experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
            exp_num_transfers = len(self.screen_cell_positions)
        else:
            exp_num_transfers = self.library_num_transfers
        self.assert_equal(len(plts), exp_num_transfers)
        for plt in plts:
            self.assert_equal(plt.transfer_type, exp_transfer_type)
            self.assert_equal(plt.diluent_info,
                              _OptimemWorklistGenerator.DILUENT_INFO)
            volume = round(plt.volume * VOLUME_CONVERSION_FACTOR, 2)
            if self.experiment_type.id == EXPERIMENT_SCENARIOS.OPTIMISATION:
                expected_volume = self.optimem_volumes[plt.target_position.label]
            elif self.experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
                expected_volume = self.screen_optimem_volume
            elif self.experiment_type.id == EXPERIMENT_SCENARIOS.LIBRARY:
                expected_volume = self.library_optimem_volume
            else:
                raise NotImplementedError('Not supported')
            self.assert_equal(volume, expected_volume)

    def _test_reagent_worklist(self, worklist=None):
        if worklist is None: worklist = self.tool.get_result()
        exp_transfer_type = TRANSFER_TYPES.SAMPLE_DILUTION
        self.assert_is_not_none(worklist)
        self.assert_true(isinstance(worklist, PlannedWorklist))
        self.assert_equal(len(worklist.executed_worklists), 0)
        label = '%s_reagent' % (self.experiment_metadata_label)
        self.assert_equal(worklist.label, label)
        self.assert_equal(worklist.transfer_type, exp_transfer_type)
        self.assert_equal(worklist.pipetting_specs.name,
                          PIPETTING_SPECS_NAMES.BIOMEK)
        plts = worklist.planned_liquid_transfers
        if self.experiment_type.id == EXPERIMENT_SCENARIOS.OPTIMISATION:
            exp_num_transfers = len(self.reagent_volumes)
        elif self.experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
            exp_num_transfers = len(self.screen_cell_positions)
        else:
            exp_num_transfers = self.library_num_transfers
        self.assert_equal(len(plts), exp_num_transfers)
        for plt in worklist.planned_liquid_transfers:
            self.assert_equal(plt.transfer_type, exp_transfer_type)
            volume = round(plt.volume * VOLUME_CONVERSION_FACTOR, 1)
            if self.experiment_type.id == EXPERIMENT_SCENARIOS.OPTIMISATION:
                expected_volume = self.reagent_volumes[plt.target_position.label]
                self.assert_true(plt.target_position.label in \
                             self.reagent_infos[plt.diluent_info])
            elif self.experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
                expected_volume = self.screen_reagent_volume
                self.assert_equal(plt.diluent_info, self.screen_reagent_info)
            elif self.experiment_type.id == EXPERIMENT_SCENARIOS.LIBRARY:
                expected_volume = self.library_reagent_volume
                self.assert_equal(plt.diluent_info, self.library_reagent_info)
            else:
                raise NotImplementedError('Not supported')
            self.assert_equal(volume, expected_volume)

    def _test_biomek_worklist(self, worklist=None, dr_label=None):
        if worklist is None: worklist = self.tool.get_result()
        exp_transfer_type = TRANSFER_TYPES.SAMPLE_TRANSFER
        self.assert_is_not_none(worklist)
        self.assert_true(isinstance(worklist, PlannedWorklist))
        self.assert_equal(worklist.transfer_type, exp_transfer_type)
        self.assert_equal(worklist.pipetting_specs.name,
                          PIPETTING_SPECS_NAMES.BIOMEK)
        self.assert_equal(len(worklist.executed_worklists), 0)
        if dr_label is None: dr_label = self.design_rack_label
        expected_prefix = self.label
        if self.label is None:
            expected_prefix = '%s-%s' % (self.experiment_metadata_label,
                                         dr_label)
        label = '%s_biomek_transfer' % (expected_prefix)
        self.assert_equal(worklist.label, label)
        source_positions = self.biomek_sources
        plts = worklist.planned_liquid_transfers
        self.assert_equal(len(plts), len(source_positions))
        for plt in worklist.planned_liquid_transfers:
            self.assert_equal(plt.transfer_type, exp_transfer_type)
            volume = plt.volume * VOLUME_CONVERSION_FACTOR
            self.assert_equal(volume, TransfectionParameters.TRANSFER_VOLUME)
            self.assert_equal(plt.source_position.label,
                    source_positions[plt.target_position.label])

    def _test_cybio_worklist(self, worklist=None):
        if worklist is None: worklist = self.tool.get_result()
        exp_transfer_type = TRANSFER_TYPES.RACK_SAMPLE_TRANSFER
        self.assert_is_not_none(worklist)
        self.assert_true(isinstance(worklist, PlannedWorklist))
        self.assert_equal(len(worklist.executed_worklists), 0)
        self.assert_equal(worklist.transfer_type, exp_transfer_type)
        self.assert_equal(worklist.pipetting_specs.name,
                          PIPETTING_SPECS_NAMES.CYBIO)
        label = '%s_cybio_transfer' % (self.experiment_metadata_label)
        self.assert_equal(worklist.label, label)
        self.assert_equal(len(worklist.planned_liquid_transfers), 1)
        plt = worklist.planned_liquid_transfers[0]
        self.assert_equal(plt.transfer_type, exp_transfer_type)
        exp_volume = plt.volume * VOLUME_CONVERSION_FACTOR
        self.assert_equal(exp_volume, TransfectionParameters.TRANSFER_VOLUME)
        self.assert_equal(plt.source_sector_index,
                          _CybioTransferWorklistGenerator.SOURCE_SECTOR_INDEX)
        self.assert_equal(plt.target_sector_index,
                          _CybioTransferWorklistGenerator.TARGET_SECTOR_INDEX)

    def _test_cell_worklist(self, worklist=None, dr_label=None):
        if worklist is None: worklist = self.tool.get_result()
        exp_transfer_type = TRANSFER_TYPES.SAMPLE_DILUTION
        self.assert_is_not_none(worklist)
        self.assert_true(isinstance(worklist, PlannedWorklist))
        self.assert_equal(len(worklist.executed_worklists), 0)
        self.assert_equal(worklist.transfer_type, exp_transfer_type)
        self.assert_equal(worklist.pipetting_specs.name,
                          PIPETTING_SPECS_NAMES.BIOMEK)
        if dr_label is None:
            label = '%s_cellsuspension' % (self.experiment_metadata_label)
        else:
            label = '%s-%s_cellsuspension' % (self.experiment_metadata_label,
                                              dr_label)
        self.assert_equal(worklist.label, label)
        plts = worklist.planned_liquid_transfers
        if self.experiment_type.id == EXPERIMENT_SCENARIOS.OPTIMISATION:
            exp_num_transfers = len(self.cell_positions)
        elif self.experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
            exp_num_transfers = len(self.screen_cell_positions)
        else:
            exp_num_transfers = self.library_num_transfers
        self.assert_equal(len(plts), exp_num_transfers)
        for plt in plts:
            self.assert_equal(plt.transfer_type, exp_transfer_type)
            self.assert_equal(plt.diluent_info,
                              _CellSuspensionWorklistGenerator.DILUENT_INFO)
            self.assert_equal(plt.volume * VOLUME_CONVERSION_FACTOR, 30)
            if self.experiment_type.id == EXPERIMENT_SCENARIOS.OPTIMISATION:
                cell_positions = self.cell_positions
            elif self.experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
                cell_positions = self.screen_cell_positions
            else:
                # we do not check library positions in details because we
                # expected 288 positions
                tp = plt.target_position
                self.assert_false(tp.column_index in (0, 23))
                self.assert_false(tp.row_index in (0, 15))
                continue
            self.assert_true(plt.target_position.label in cell_positions)

    def _test_invalid_experiment_metadata_label(self):
        ori_label = self.experiment_metadata_label
        self.experiment_metadata_label = 5
        self._test_and_expect_errors('experiment metadata label must be a ' \
                                     'basestring')
        self.experiment_metadata_label = ori_label

    def _test_invalid_label(self):
        ori_label = self.label
        self.label = 5
        self._test_and_expect_errors('The label must be a basestring')
        self.label = ori_label

    def _test_invalid_transfection_layout(self):
        ori_layout = self.transfection_layout
        self.transfection_layout = self.transfection_layout.create_rack_layout()
        self._test_and_expect_errors('transfection layout must be a ' \
                                     'TransfectionLayout')
        self.transfection_layout = ori_layout


class OptimemWorklistGeneratorTestCase(_ExperimentWorklistSeriesTestCase):

    def _create_tool(self):
        self.tool = _OptimemWorklistGenerator(
                    experiment_metadata_label=self.experiment_metadata_label,
                    transfection_layout=self.transfection_layout,
                    log=self.log)

    def test_result_opti(self):
        self._continue_setup()
        self._test_optimem_worklist()

    def test_result_screen(self):
        self.experiment_type = get_experiment_type_screening()
        self._continue_setup()
        self._test_optimem_worklist()

    def test_result_library(self):
        self.experiment_type = get_experiment_type_library()
        self._continue_setup()
        self._test_optimem_worklist()

    def test_invalid_input_value(self):
        self._continue_setup()
        self._test_invalid_experiment_metadata_label()
        self._test_invalid_transfection_layout()


class ReagentWorklistGeneratorTestCase(_ExperimentWorklistSeriesTestCase):

    def _create_tool(self):
        self.tool = _ReagentWorklistGenerator(
                    experiment_metadata_label=self.experiment_metadata_label,
                    transfection_layout=self.transfection_layout, log=self.log)

    def test_result_opti(self):
        self._continue_setup()
        self._test_reagent_worklist()

    def test_result_screen(self):
        self.experiment_type = get_experiment_type_screening()
        self._continue_setup()
        self._test_reagent_worklist()

    def test_result_library(self):
        self.experiment_type = get_experiment_type_library()
        self._continue_setup()
        self._test_reagent_worklist()

    def test_invalid_input_values(self):
        self._continue_setup()
        self._test_invalid_experiment_metadata_label()
        self._test_invalid_transfection_layout()

    def test_too_small_reagent_dilution_factor(self):
        self._continue_setup(file_name='opti_invalid_reagent_dil_factor.xls')
        self._test_and_expect_errors('Invalid dilution reagent factor for ' \
            'rack positions: 14 (B2, B4, B6, B8, D2, D3, D4). The factor ' \
            'would result in an initial dilution factor of less then 1!')
        self.experiment_type = get_experiment_type_screening()
        self._continue_setup(file_name='screen_invalid_reagent_dil_factor.xls')
        self._test_and_expect_errors('Invalid dilution reagent factor for ' \
            'rack positions: 6 (B2, B3, C2, C3, D2, D3, E2, E3). The factor ' \
            'would result in an initial dilution factor of less then 1!')


class BiomekTransferWorklistGeneratorTestCase(_ExperimentWorklistSeriesTestCase):

    def set_up(self):
        _ExperimentWorklistSeriesTestCase.set_up(self)
        self.label = '%s-2' % (self.experiment_metadata_label)

    def _create_tool(self):
        self.tool = _BiomekTransferWorklistGenerator(
                    label=self.label,
                    transfection_layout=self.transfection_layout, log=self.log)

    def test_result_opti(self):
        self._continue_setup()
        self.transfection_layout = self.design_rack_associations['2']
        self._create_tool()
        self._test_biomek_worklist()

    def test_invalid_input_values(self):
        self._continue_setup()
        self._test_invalid_transfection_layout()
        self._test_invalid_label()


class CybioTransferWorklistGeneratorTestCase(_ExperimentWorklistSeriesTestCase):

    def _create_tool(self):
        self.tool = _CybioTransferWorklistGenerator(log=self.log,
                experiment_metadata_label=self.experiment_metadata_label)

    def test_result_screen(self):
        self.experiment_type = get_experiment_type_screening()
        self._continue_setup()
        self._test_cybio_worklist()

    def test_result_library(self):
        self.experiment_type = get_experiment_type_library()
        self._continue_setup()
        self._test_cybio_worklist()

    def test_invalid_input_values(self):
        self._continue_setup()
        self._test_invalid_experiment_metadata_label()


class CellSuspensionWorklistGeneratorTestCase(_ExperimentWorklistSeriesTestCase):

    def set_up(self):
        _ExperimentWorklistSeriesTestCase.set_up(self)
        self.label = '%s-%s' % (self.experiment_metadata_label,
                                self.design_rack_label)

    def _create_tool(self):
        self.tool = _CellSuspensionWorklistGenerator(
                label=self.label, log=self.log,
                transfection_layout=self.transfection_layout)

    def test_result_opti(self):
        self._continue_setup()
        self.transfection_layout = self.design_rack_associations[
                                                    self.design_rack_label]
        self._create_tool()
        self._test_cell_worklist(dr_label=self.design_rack_label)

    def test_result_screen(self):
        self.experiment_type = get_experiment_type_screening()
        self._continue_setup()
        for rack_pos, tf_pos in self.transfection_layout.iterpositions():
            tf_pos.cell_plate_positions.add(rack_pos)
        self._test_cell_worklist(dr_label=self.design_rack_label)

    def test_result_library(self):
        self.experiment_type = get_experiment_type_library()
        self._continue_setup()
        for rack_pos, tf_pos in self.transfection_layout.iterpositions():
            tf_pos.cell_plate_positions.add(rack_pos)
        self._test_cell_worklist(dr_label=self.design_rack_label)

    def test_invalid_input_values(self):
        self._continue_setup()
        self._test_invalid_transfection_layout()
        self._test_invalid_label()


class ExperimentWorklistGeneratorTestCase(_ExperimentWorklistSeriesTestCase):

    def set_up(self):
        _ExperimentWorklistSeriesTestCase.set_up(self)
        self.supports_mastermix = False

    def tear_down(self):
        _ExperimentWorklistSeriesTestCase.tear_down(self)
        del self.supports_mastermix

    def _create_tool(self):
        self.tool = ExperimentWorklistGenerator(log=self.log,
                        label=self.experiment_metadata_label,
                        experiment_design=self.experiment_design,
                        source_layout=self.transfection_layout,
                        scenario=self.experiment_type,
                        supports_mastermix=self.supports_mastermix,
                        design_rack_associations=self.design_rack_associations)

    def __check_results(self):
        ed = self.tool.get_result()
        self.assert_is_not_none(ed)
        storage_location = EXPERIMENT_WORKLIST_PARAMETERS.\
                           STORAGE_LOCATIONS[self.experiment_type.id]
        transfer_index = EXPERIMENT_WORKLIST_PARAMETERS.\
                         TRANSFER_WORKLIST_INDICES[storage_location]
        # test experiment design series
        ed_series = ed.worklist_series
        if not self.supports_mastermix:
            if self.experiment_type.id in (EXPERIMENT_SCENARIOS.SCREENING,
                                           EXPERIMENT_SCENARIOS.LIBRARY):
                self.assert_equal(len(ed_series), 2)
            else:
                self.assert_is_none(ed_series)
        else:
            if self.experiment_type.id in (EXPERIMENT_SCENARIOS.SCREENING,
                                           EXPERIMENT_SCENARIOS.LIBRARY):
                self.assert_equal(len(ed_series), 4)
            else:
                self.assert_equal(len(ed_series), 2)
            for worklist in ed_series:
                if worklist.index == self.tool.OPTIMEM_WORKLIST_INDEX:
                    self._test_optimem_worklist(worklist)
                elif worklist.index == self.tool.REAGENT_WORKLIST_INDEX:
                    self._test_reagent_worklist(worklist)
                elif worklist.index == transfer_index \
                            and self.experiment_type.id in (
                                           EXPERIMENT_SCENARIOS.SCREENING,
                                           EXPERIMENT_SCENARIOS.LIBRARY):
                    self._test_cybio_worklist(worklist)
                else:
                    self._test_cell_worklist(worklist)
        # test design rack series
        for design_rack in ed.experiment_design_racks:
            rack_series = design_rack.worklist_series
            if self.experiment_type.id in (EXPERIMENT_SCENARIOS.SCREENING,
                                           EXPERIMENT_SCENARIOS.LIBRARY):
                self.assert_is_none(rack_series)
                continue
            self.assert_equal(len(rack_series), 2)
            for worklist in rack_series:
                if worklist.index == transfer_index:
                    self._test_biomek_worklist(worklist, design_rack.label)
                else:
                    self._test_cell_worklist(worklist, design_rack.label)

    def test_result_opti_no_mastermix(self):
        self._continue_setup()
        self.__check_results()

    def test_result_opti_with_mastermix(self):
        self.supports_mastermix = True
        self._continue_setup()
        self.__check_results()

    def test_result_screen_no_mastermix(self):
        self.experiment_type = get_experiment_type_screening()
        self._continue_setup()
        self.__check_results()

    def test_result_screen_with_mastermix(self):
        self.experiment_type = get_experiment_type_screening()
        self.supports_mastermix = True
        self._continue_setup()
        self.__check_results()

    def test_result_library_no_mastermix(self):
        self.experiment_type = get_experiment_type_library()
        self._continue_setup()
        self.__check_results()

    def test_result_library_with_mastermix(self):
        self.experiment_type = get_experiment_type_library()
        self.supports_mastermix = True
        self._continue_setup()
        self.__check_results()

    def test_invalid_scenarios(self):
        self._continue_setup()
        for scenario in (EXPERIMENT_SCENARIOS.MANUAL,
                         EXPERIMENT_SCENARIOS.ORDER_ONLY,
                         EXPERIMENT_SCENARIOS.ISO_LESS):
            self.experiment_type = EXPERIMENT_SCENARIOS.from_name(scenario)
            self._test_and_expect_errors('Unexpected scenario')

    def xtest_invalid_input_values(self):
        self._continue_setup()
        ed = self.experiment_design
        self.experiment_design = None
        self._test_and_expect_errors('The experiment design must be a ' \
                                     'ExperimentDesign object')
        self.experiment_design = ed
        ori_label = self.experiment_metadata_label
        self.experiment_metadata_label = 5
        self._test_and_expect_errors('The label must be a basestring object ' \
                                     '(obtained: int)')
        self.experiment_metadata_label = ori_label
        tfl = self.transfection_layout
        self.transfection_layout = self.transfection_layout.create_rack_layout()
        self._test_and_expect_errors('The source layout must be a ' \
                            'TransfectionLayout object (obtained: RackLayout).')
        self.transfection_layout = tfl
        emt = self.experiment_type
        self.experiment_type = EXPERIMENT_SCENARIOS.LIBRARY
        self._test_and_expect_errors('The experiment scenario must be a ' \
                            'ExperimentMetadataType object (obtained: str)')
        self.experiment_type = emt
        self.supports_mastermix = None
        self._test_and_expect_errors('The "support mastermix" flag must be a ' \
                                     'bool')
        self.supports_mastermix = False
        self.design_rack_associations = []
        self._test_and_expect_errors('The design rack maps must be a dict')
        self.design_rack_associations = {1 : self.transfection_layout}
        self._test_and_expect_errors('The design rack label must be a ' \
                                     'basestring')
        self.design_rack_associations = {'1' : 1 }
        self._test_and_expect_errors('The design rack layout must be a ' \
                                     'TransfectionLayout object')
        self.design_rack_associations = None

    def test_reagent_worklist_failure(self):
        self.supports_mastermix = True
        self._continue_setup('opti_invalid_reagent_dil_factor.xls')
        self._test_and_expect_errors('Error when trying to generate ' \
                                     'transfection reagent worklist.')
