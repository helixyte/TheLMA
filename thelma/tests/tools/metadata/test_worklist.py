"""
Tests the experiment liquid transfer plan tools.
AAB Aug 08, 2011
"""

from everest.entities.utils import get_root_aggregate
from pkg_resources import resource_filename # pylint: disable=E0611,F0401
from thelma.automation.tools.semiconstants \
    import get_experiment_type_robot_optimisation
from thelma.automation.tools.semiconstants \
    import get_experiment_type_screening
from thelma.automation.tools.semiconstants \
    import get_experiment_type_manual_optimisation
from thelma.automation.tools.semiconstants \
    import get_experiment_type_order
from thelma.automation.handlers.experimentdesign \
    import ExperimentDesignParserHandler
from thelma.automation.handlers.isorequest import IsoRequestParserHandler
from thelma.automation.tools.metadata.generation \
    import WellAssociatorOptimisation
from thelma.automation.tools.metadata.generation import WellAssociatorManual
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionParameters
from thelma.automation.tools.metadata.worklist \
    import BiomekTransferWorklistGenerator
from thelma.automation.tools.metadata.worklist \
    import CellSuspensionWorklistGenerator
from thelma.automation.tools.metadata.worklist \
    import CybioTransferWorklistGenerator
from thelma.automation.tools.metadata.worklist \
    import EXPERIMENT_WORKLIST_PARAMETERS
from thelma.automation.tools.metadata.worklist \
    import ExperimentWorklistGenerator
from thelma.automation.tools.metadata.worklist import OptimemWorklistGenerator
from thelma.automation.tools.metadata.worklist import ReagentWorklistGenerator
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.worklists.base import VOLUME_CONVERSION_FACTOR
from thelma.interfaces import IMoleculeType
from thelma.interfaces import IUser
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.tests.tools.tooltestingutils import SilentLog
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase


class ExperimentWorklistSeriesTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.TEST_FILE_PATH = 'thelma:tests/tools/metadata/worklist/'
        self.VALID_FILES = {
                        EXPERIMENT_SCENARIOS.OPTIMISATION : 'valid_opti.xls',
                        EXPERIMENT_SCENARIOS.SCREENING : 'valid_screen.xls',
                        EXPERIMENT_SCENARIOS.MANUAL : 'valid_manual.xls',
                        EXPERIMENT_SCENARIOS.LIBRARY : 'valid_library.xls'}
        self.log = TestingLog()
        self.silent_log = SilentLog()
        self.requester = self._get_entity(IUser, 'it')
        self.molecule_type = get_root_aggregate(IMoleculeType).\
                             get_by_id('SIRNA')
        self.experiment_type = get_experiment_type_robot_optimisation()
        self.experiment_metadata_label = 'Worklist Generator Test'
        self.label = None
        self.experiment_design = None
        self.number_replicates = 3
        self.design_rack_label = '1'
        self.transfection_layout = None
        self.default_optimem_df = 4
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
        # result data manual
        self.manual_cell_positions = ['B2', 'B3', 'D2', 'D3', 'F2', 'F3']
        self.manual_biomek_source = dict(B2='B2', B3='B2', D2='C2', D3='C2',
                                         F2='D2', F3='D2')

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.TEST_FILE_PATH
        del self.VALID_FILES
        del self.log
        del self.silent_log
        del self.requester
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

    def _continue_setup(self, file_name=None):
        if file_name is None:
            file_name = self.VALID_FILES[self.experiment_type.id]
        self._read_experiment_file(file_name)
        if self.experiment_type.id == EXPERIMENT_SCENARIOS.OPTIMISATION:
            self.__associate_opti_layouts()
        elif self.experiment_type.id == EXPERIMENT_SCENARIOS.MANUAL:
            self.__associate_manual_layout()
        self._create_tool()

    def _read_experiment_file(self, experiment_data_xml):
        ed_file = self.TEST_FILE_PATH + experiment_data_xml
        file_name = ed_file.split(':')
        f = resource_filename(*file_name) # pylint: disable=W0142
        stream = None
        try:
            stream = open(f, 'rb')
            source = stream.read()
        finally:
            if not stream is None:
                stream.close()
        ed_handler = ExperimentDesignParserHandler(stream=source,
                            requester=self.requester, log=self.silent_log,
                            scenario=self.experiment_type)
        self.experiment_design = ed_handler.get_result()
        iso_handler = IsoRequestParserHandler.create(stream=source,
                    experiment_type_id=self.experiment_type.id,
                    requester=self.requester, log=self.silent_log)
        iso_request = iso_handler.get_result() #pylint: disable=W0612
        self.transfection_layout = iso_handler.get_transfection_layout()
        for tf_pos in self.transfection_layout.working_positions():
            if tf_pos.is_fixed:
                tf_pos.store_optimem_dilution_factor()
            elif tf_pos.is_floating or tf_pos.is_mock:
                tf_pos.set_optimem_dilution_factor(self.default_optimem_df)

    def __associate_opti_layouts(self):
        associator = WellAssociatorOptimisation(
                                experiment_design=self.experiment_design,
                                source_layout=self.transfection_layout,
                                log=self.silent_log)
        self.design_rack_associations = associator.get_result()
        self.transfection_layout = associator.get_completed_source_layout()

    def __associate_manual_layout(self):
        associator = WellAssociatorManual(
                                experiment_design=self.experiment_design,
                                source_layout=self.transfection_layout,
                                log=self.silent_log)
        self.design_rack_associations = associator.get_result()

    def _test_optimem_worklist(self, worklist=None):
        if worklist is None: worklist = self.tool.get_result()
        self.assert_is_not_none(worklist)
        self.assert_true(isinstance(worklist, PlannedWorklist))
        self.assert_equal(len(worklist.executed_worklists), 0)
        label = '%s_optimem' % (self.experiment_metadata_label)
        self.assert_equal(worklist.label, label)
        for pt in worklist.planned_transfers:
            self.assert_equal(pt.type, TRANSFER_TYPES.CONTAINER_DILUTION)
            self.assert_equal(pt.diluent_info,
                              OptimemWorklistGenerator.DILUENT_INFO)
            volume = round(pt.volume * VOLUME_CONVERSION_FACTOR, 2)
            if self.experiment_type.id == EXPERIMENT_SCENARIOS.OPTIMISATION:
                expected_volume = self.optimem_volumes[pt.target_position.label]
            elif self.experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
                expected_volume = self.screen_optimem_volume
            else:
                raise NotImplementedError('Not supported')
            self.assert_equal(volume, expected_volume)

    def _test_reagent_worklist(self, worklist=None):
        if worklist is None: worklist = self.tool.get_result()
        self.assert_is_not_none(worklist)
        self.assert_true(isinstance(worklist, PlannedWorklist))
        self.assert_equal(len(worklist.executed_worklists), 0)
        label = '%s_reagent' % (self.experiment_metadata_label)
        self.assert_equal(worklist.label, label)
        for pt in worklist.planned_transfers:
            self.assert_equal(pt.type, TRANSFER_TYPES.CONTAINER_DILUTION)
            volume = round(pt.volume * VOLUME_CONVERSION_FACTOR, 1)
            if self.experiment_type.id == EXPERIMENT_SCENARIOS.OPTIMISATION:
                expected_volume = self.reagent_volumes[pt.target_position.label]
                self.assert_true(pt.target_position.label in \
                             self.reagent_infos[pt.diluent_info])
            elif self.experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
                expected_volume = self.screen_reagent_volume
                self.assert_equal(pt.diluent_info, self.screen_reagent_info)
            else:
                raise NotImplementedError('Not supported')
            self.assert_equal(volume, expected_volume)

    def _test_biomek_worklist(self, worklist=None, dr_label=None):
        if worklist is None: worklist = self.tool.get_result()
        self.assert_is_not_none(worklist)
        self.assert_true(isinstance(worklist, PlannedWorklist))
        self.assert_equal(len(worklist.executed_worklists), 0)
        if dr_label is None: dr_label = self.design_rack_label
        expected_prefix = self.label
        if self.label is None:
            expected_prefix = '%s-%s' % (self.experiment_metadata_label,
                                         dr_label)
        label = '%s_biomek_transfer' % (expected_prefix)
        self.assert_equal(worklist.label, label)
        source_positions = self.biomek_sources
        if self.experiment_type.id == EXPERIMENT_SCENARIOS.MANUAL:
            source_positions = self.manual_biomek_source
        for pt in worklist.planned_transfers:
            self.assert_equal(pt.type, TRANSFER_TYPES.CONTAINER_TRANSFER)
            volume = pt.volume * VOLUME_CONVERSION_FACTOR
            self.assert_equal(volume, TransfectionParameters.TRANSFER_VOLUME)
            self.assert_equal(pt.source_position.label,
                    source_positions[pt.target_position.label])

    def _test_cybio_worklist(self, worklist=None):
        if worklist is None: worklist = self.tool.get_result()
        self.assert_is_not_none(worklist)
        self.assert_true(isinstance(worklist, PlannedWorklist))
        self.assert_equal(len(worklist.executed_worklists), 0)
        label = '%s_cybio_transfer' % (self.experiment_metadata_label)
        self.assert_equal(worklist.label, label)
        self.assert_equal(len(worklist.planned_transfers), 1)
        pt = worklist.planned_transfers[0]
        self.assert_equal(pt.type, TRANSFER_TYPES.RACK_TRANSFER)
        exp_volume = pt.volume * VOLUME_CONVERSION_FACTOR
        self.assert_equal(exp_volume, TransfectionParameters.TRANSFER_VOLUME)
        self.assert_equal(pt.source_sector_index,
                          CybioTransferWorklistGenerator.SOURCE_SECTOR_INDEX)
        self.assert_equal(pt.target_sector_index,
                          CybioTransferWorklistGenerator.TARGET_SECTOR_INDEX)

    def _test_cell_worklist(self, worklist=None, dr_label=None):
        if worklist is None: worklist = self.tool.get_result()
        self.assert_is_not_none(worklist)
        self.assert_true(isinstance(worklist, PlannedWorklist))
        self.assert_equal(len(worklist.executed_worklists), 0)
        if dr_label is None:
            label = '%s_cellsuspension' % (self.experiment_metadata_label)
        else:
            label = '%s-%s_cellsuspension' % (self.experiment_metadata_label,
                                              dr_label)
        self.assert_equal(worklist.label, label)
        for pt in worklist.planned_transfers:
            self.assert_equal(pt.type, TRANSFER_TYPES.CONTAINER_DILUTION)
            self.assert_equal(pt.diluent_info,
                              CellSuspensionWorklistGenerator.DILUENT_INFO)
            self.assert_equal(pt.volume * VOLUME_CONVERSION_FACTOR, 30)
            if self.experiment_type.id == EXPERIMENT_SCENARIOS.OPTIMISATION:
                cell_positions = self.cell_positions
            elif self.experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
                cell_positions = self.screen_cell_positions
            else:
                cell_positions = self.manual_cell_positions
            self.assert_true(pt.target_position.label in cell_positions)


class OptimemWorklistGeneratorTestCase(ExperimentWorklistSeriesTestCase):

    def _create_tool(self):
        self.tool = OptimemWorklistGenerator(
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

    def test_label(self):
        self._continue_setup()
        self.experiment_metadata_label = 5
        self._test_and_expect_errors('experiment metadata label must be a ' \
                                     'basestring')

    def test_invalid_source_layout(self):
        self._continue_setup()
        self.transfection_layout = self.transfection_layout.create_rack_layout()
        self._test_and_expect_errors('transfection layout must be a ' \
                                     'TransfectionLayout')


class ReagentWorklistGeneratorTestCase(ExperimentWorklistSeriesTestCase):

    def _create_tool(self):
        self.tool = ReagentWorklistGenerator(
                    experiment_metadata_label=self.experiment_metadata_label,
                    transfection_layout=self.transfection_layout, log=self.log)

    def test_result_opti(self):
        self._continue_setup()
        self._test_reagent_worklist()

    def test_result_screen(self):
        self.experiment_type = get_experiment_type_screening()
        self._continue_setup()
        self._test_reagent_worklist()

    def test_label(self):
        self._continue_setup()
        self.experiment_metadata_label = 5
        self._test_and_expect_errors('experiment metadata label must be a ' \
                                     'basestring')

    def test_invalid_transfection_layout(self):
        self._continue_setup()
        self.transfection_layout = self.transfection_layout.create_rack_layout()
        self._test_and_expect_errors('transfection layout must be a ' \
                                     'TransfectionLayout')

    def test_too_small_reagent_dilution_factor_opti(self):
        self._continue_setup(file_name='opti_invalid_reagent_dil_factor.xls')
        self._test_and_expect_errors('Invalid dilution reagent factor')

    def test_too_small_reagent_dilution_factor_screen(self):
        self.experiment_type = get_experiment_type_screening()
        self._continue_setup(file_name='screen_invalid_reagent_dil_factor.xls')
        self._test_and_expect_errors('Invalid dilution reagent factor')


class BiomekTransferWorklistGeneratorTestCase(ExperimentWorklistSeriesTestCase):

    def set_up(self):
        ExperimentWorklistSeriesTestCase.set_up(self)
        self.label = '%s-2' % (self.experiment_metadata_label)

    def _create_tool(self):
        self.tool = BiomekTransferWorklistGenerator(
                    label=self.label,
                    transfection_layout=self.transfection_layout, log=self.log)

    def test_result_opti(self):
        self._continue_setup()
        self._test_biomek_worklist()

    def test_result_manual(self):
        self.experiment_type = get_experiment_type_manual_optimisation()
        self._continue_setup()
        self._test_biomek_worklist()

    def test_label(self):
        self._continue_setup()
        self.label = 5
        self._test_and_expect_errors('The label must be a basestring')

    def test_invalid_transfection_layout(self):
        self._continue_setup()
        self.transfection_layout = self.transfection_layout.create_rack_layout()
        self._test_and_expect_errors('The transfection layout must be a ' \
                                     'TransfectionLayout')


class CybioTransferWorklistGeneratorTestCase(ExperimentWorklistSeriesTestCase):

    def _create_tool(self):
        self.tool = CybioTransferWorklistGenerator(log=self.log,
                experiment_metadata_label=self.experiment_metadata_label)

    def test_result_screen(self):
        self.experiment_type = get_experiment_type_screening()
        self._continue_setup()
        self._test_cybio_worklist()

    def test_label(self):
        self._continue_setup()
        self.experiment_metadata_label = 5
        self._test_and_expect_errors('The experiment metadata label must ' \
                                     'be a basestring')


class CellSuspensionWorklistGeneratorTestCase(ExperimentWorklistSeriesTestCase):

    def set_up(self):
        ExperimentWorklistSeriesTestCase.set_up(self)
        self.label = '%s-%s' % (self.experiment_metadata_label,
                                self.design_rack_label)

    def _create_tool(self):
        self.tool = CellSuspensionWorklistGenerator(
                label=self.label, log=self.log,
                transfection_layout=self.transfection_layout)

    def test_result_opti(self):
        self._continue_setup()
        self._test_cell_worklist(dr_label=self.design_rack_label)

    def test_result_screen(self):
        self.experiment_type = get_experiment_type_screening()
        self._continue_setup()
        self._test_cell_worklist(dr_label=self.design_rack_label)

    def test_result_manual(self):
        self.experiment_type = get_experiment_type_manual_optimisation()
        self._continue_setup()
        self._test_cell_worklist(dr_label=self.design_rack_label)

    def test_label(self):
        self._continue_setup()
        self.label = 5
        self._test_and_expect_errors('The label must be a basestring')

    def test_invalid_transfection_layout(self):
        self._continue_setup()
        self.transfection_layout = self.transfection_layout.create_rack_layout()
        self._test_and_expect_errors('The transfection layout must be a ' \
                                     'TransfectionLayout')


class ExperimentWorklistGeneratorTestCase(ExperimentWorklistSeriesTestCase):

    def set_up(self):
        ExperimentWorklistSeriesTestCase.set_up(self)
        self.supports_mastermix = False

    def tear_down(self):
        ExperimentWorklistSeriesTestCase.tear_down(self)
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
            if self.experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
                self.assert_equal(len(ed_series), 2)
            else:
                self.assert_is_none(ed_series)
        else:
            if self.experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
                self.assert_equal(len(ed_series), 4)
            else:
                self.assert_equal(len(ed_series), 2)
            for worklist in ed_series:
                if worklist.index == self.tool.OPTIMEM_WORKLIST_INDEX:
                    self._test_optimem_worklist(worklist)
                elif worklist.index == self.tool.REAGENT_WORKLIST_INDEX:
                    self._test_reagent_worklist(worklist)
                elif worklist.index == transfer_index \
                            and self.experiment_type.id == \
                            EXPERIMENT_SCENARIOS.SCREENING:
                    self._test_cybio_worklist(worklist)
                else:
                    self._test_cell_worklist(worklist)
        # test design rack series
        for design_rack in ed.design_racks:
            rack_series = design_rack.worklist_series
            if self.experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
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

    def test_result_manual(self):
        self.experiment_type = get_experiment_type_manual_optimisation()
        self._continue_setup()
        self.__check_results()

    def test_manual_with_mastermix(self):
        self.experiment_type = get_experiment_type_manual_optimisation()
        self.supports_mastermix = True
        self._continue_setup()
        self._test_and_expect_errors('Manual optimisation cannot support ' \
                                     'mastermix preparation!')

    def test_invalid_experiment_design(self):
        self._continue_setup()
        self.experiment_design = None
        self._test_and_expect_errors('The experiment design must be a ' \
                                     'ExperimentDesign object')

    def test_invalid_label(self):
        self._continue_setup()
        self.experiment_metadata_label = 13
        self._test_and_expect_errors('The label must be a basestring')

    def test_invalid_source_layout(self):
        self._continue_setup()
        self.transfection_layout = None
        self._test_and_expect_errors('The source layout must be a ' \
                                     'TransfectionLayout object')

    def test_invalid_mastermix_flag(self):
        self._continue_setup()
        self.supports_mastermix = None
        self._test_and_expect_errors('The "support mastermix" flag must be a ' \
                                     'bool')

    def test_unknown_scenario(self):
        self._continue_setup()
        self.experiment_type = get_experiment_type_order()
        self._test_and_expect_errors('Unexpected scenario: "%s"' %
                                     EXPERIMENT_SCENARIOS.ORDER_ONLY)

    def test_invalid_design_rack_associations(self):
        self._continue_setup()
        self.design_rack_associations = []
        self._test_and_expect_errors('The design rack maps must be a dict')
        self.design_rack_associations = {1 : self.transfection_layout}
        self._test_and_expect_errors('The design rack label must be a ' \
                                     'basestring')
        self.design_rack_associations = {'1' : 1 }
        self._test_and_expect_errors('The design rack layout must be a ' \
                                     'TransfectionLayout object')

    def test_reagent_worklist_failure(self):
        self.supports_mastermix = True
        self._continue_setup('opti_invalid_reagent_dil_factor.xls')
        self._test_and_expect_errors('Error when trying to generate ' \
                                     'transfection reagent worklist.')
