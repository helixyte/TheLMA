"""
Well associator test cases - well associator are used by the experiment
metadata generator to find the source wells for each transfected well
in an experiment cell plate well.

AAB
"""
from pkg_resources import resource_filename # pylint: disable=E0611,F0401
from thelma.automation.handlers.experimentdesign \
    import ExperimentDesignParserHandler
from thelma.automation.handlers.isorequest import IsoRequestParserHandler
from thelma.automation.tools.metadata.generation \
    import WellAssociatorOptimisation
from thelma.automation.tools.metadata.generation import WellAssociatorManual
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionLayoutConverter
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import get_384_rack_shape
from thelma.automation.tools.semiconstants import get_experiment_metadata_type
from thelma.models.racklayout import RackLayout
from thelma.models.utils import get_user
from thelma.tests.tools.tooltestingutils import SilentLog
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase

class WellAssociatorTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.log = TestingLog()
        self.silent_log = SilentLog()
        self.FILE_PATH = 'thelma:tests/tools/metadata/associator/'
        self.VALID_FILE = None
        # ini values
        self.experiment_design = None
        self.source_layout = None
        self.design_rack_layouts = None
        # result_data: src label; value: target labels
        self.result_data_1 = None
        self.result_data_2 = None
        self.final_concentration1 = 100
        self.final_concentration2 = 200
        self.mock_labels = []
        # other values
        self.source = None
        self.experiment_type_id = None
        self.pass_design_rack_layouts = False
        self.user = get_user('it')

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.log
        del self.silent_log
        del self.FILE_PATH
        del self.VALID_FILE
        del self.experiment_design
        del self.source_layout
        del self.design_rack_layouts
        del self.result_data_1
        del self.result_data_2
        del self.final_concentration1
        del self.final_concentration2
        del self.mock_labels
        del self.source
        del self.experiment_type_id
        del self.pass_design_rack_layouts

    def _continue_setup(self, file_name=None):
        if file_name is None: file_name = self.VALID_FILE
        self.__read_file(file_name)
        self.__parse_experiment_design()
        self.__parse_iso_request()
        if self.pass_design_rack_layouts: self.__generate_design_rack_layouts()
        self._create_tool()

    def __read_file(self, file_name):
        test_file = self.FILE_PATH + file_name
        fn = test_file.split(':')
        f = resource_filename(*fn)
        try:
            stream = open(f, 'rb')
            self.source = stream.read()
        finally:
            stream.close()

    def __parse_experiment_design(self):
        em_type = get_experiment_metadata_type(self.experiment_type_id)
        ed_handler = ExperimentDesignParserHandler(stream=self.source,
                            requester=self.user, scenario=em_type,
                            log=self.silent_log)
        self.experiment_design = ed_handler.get_result()

    def __parse_iso_request(self):
        iso_handler = IsoRequestParserHandler.create(stream=self.source,
                            experiment_type_id=self.experiment_type_id,
                            requester=self.user, log=self.silent_log)
        iso_request = iso_handler.get_result() #pylint: disable=W0612
        self.source_layout = iso_handler.get_transfection_layout()

    def __generate_design_rack_layouts(self):
        self.design_rack_layouts = dict()
        for design_rack in self.experiment_design.design_racks:
            converter = TransfectionLayoutConverter(log=self.silent_log,
                                    rack_layout=design_rack.layout,
                                    is_iso_layout=False)
            tf_layout = converter.get_result()
            self.design_rack_layouts[design_rack.label] = tf_layout

    def _check_result(self):
        layouts = self.tool.get_result()
        self.assert_is_not_none(layouts)
        self.assert_equal(len(layouts), 2)
        final_concentrations = self.tool.get_final_concentrations()
        self.assert_is_not_none(final_concentrations)
        self.assert_equal(len(final_concentrations), 2)
        for label, tf_layout in layouts.iteritems():
            layout_positions = []
            if label == '1':
                result_data = self.result_data_1
                final_conc = self.final_concentration1
            else:
                result_data = self.result_data_2
                final_conc = self.final_concentration2
            for rack_pos, tf_pos in tf_layout.iterpositions():
                pos_label = rack_pos.label
                self.assert_true(result_data.has_key(pos_label))
                tf_targets = []
                for trg_pos in tf_pos.cell_plate_positions:
                    tf_targets.append(trg_pos.label)
                    layout_positions.append(trg_pos)
                tf_targets.sort()
                expected_targets = result_data[pos_label]
                self.assert_equal(tf_targets, expected_targets)
            concentration_map = final_concentrations[label]
            self.assert_equal(len(concentration_map), len(layout_positions))
            for rack_pos in layout_positions:
                conc = concentration_map[rack_pos]
                if rack_pos.label in self.mock_labels:
                    self.assert_is_none(conc)
                else:
                    self.assert_equal(conc, final_conc)

    def _test_and_expect_errors(self, msg=None):
        ToolsAndUtilsTestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_final_concentrations())

    def _test_invalid_experiment_design(self):
        self._continue_setup()
        self.experiment_design = None
        self._test_and_expect_errors('The experiment design must be a ' \
                                     'ExperimentDesign object')

    def _test_invalid_source_layout(self):
        self._continue_setup()
        self.source_layout = None
        self._test_and_expect_errors('The source layout must be a ' \
                                     'TransfectionLayout object')

    def _test_layout_conversion_error(self):
        self._continue_setup()
        for design_rack in self.experiment_design.design_racks:
            design_rack.layout = RackLayout(shape=get_384_rack_shape())
            break
        self._test_and_expect_errors('Error when trying to convert layout ' \
                                     'for design rack')


class WellAssociatorTestCaseManual(WellAssociatorTestCase):

    def set_up(self):
        WellAssociatorTestCase.set_up(self)
        self.VALID_FILE = 'valid_manual.xls'
        self.experiment_type_id = EXPERIMENT_SCENARIOS.MANUAL
        # src label; value: target labels
        self.result_data_1 = dict(
                    B2=['B2', 'B3', 'B4', 'F2', 'F3', 'F4'],
                    C2=['C2', 'C3', 'C4', 'G2', 'G3', 'G4'],
                    D2=[])
        self.result_data_2 = dict(
                    B2=['B2', 'B3', 'B4', 'F2', 'F3', 'F4'],
                    C2=[],
                    D2=['C2', 'C3', 'C4', 'G2', 'G3', 'G4'])

    def _create_tool(self):
        self.tool = WellAssociatorManual(log=self.log,
                                source_layout=self.source_layout,
                                experiment_design=self.experiment_design,
                                design_rack_layouts=self.design_rack_layouts)

    def test_result(self):
        self._continue_setup()
        self._check_result()

    def test_invalid_experiment_design(self):
        self._test_invalid_experiment_design()

    def test_invalid_source_layout(self):
        self._test_invalid_source_layout()

    def test_layout_conversion_error(self):
        self._test_layout_conversion_error()

    def test_missing_source_position(self):
        self._continue_setup('manual_missing_source.xls')
        self._test_and_expect_errors('Could not find source positions for ' \
                                     'the following positions in design rack')


class WellAssociatorTestCaseOpti(WellAssociatorTestCase):

    def set_up(self):
        WellAssociatorTestCase.set_up(self)
        self.VALID_FILE = 'valid_opti.xls'
        self.experiment_type_id = EXPERIMENT_SCENARIOS.OPTIMISATION
        # src label; value: target labels
        self.result_data_1 = dict(
                    B2=['B2', 'B3', 'C2', 'C3'],
                    B3=['E2', 'E3', 'F2', 'F3'],
                    C2=[], C3=[],
                    E2=['B5', 'B6', 'C5', 'C6'],
                    E3=['E5', 'E6', 'F5', 'F6'],
                    C5=[], C6=[],
                    E5=['B8', 'B9'], E6=['C8', 'C9'])
        self.result_data_2 = dict(
                    B2=[], B3=[],
                    C2=['B2', 'B3', 'C2', 'C3'],
                    C3=['E2', 'E3', 'F2', 'F3'],
                    E2=[], E3=[],
                    C5=['B5', 'B6', 'C5', 'C6'],
                    C6=['E5', 'E6', 'F5', 'F6'],
                    E5=['B8', 'B9'], E6=['C8', 'C9'])
        self.mock_labels = ['B8', 'B9', 'C8', 'C9']

    def _create_tool(self):
        self.tool = WellAssociatorOptimisation(log=self.log,
                                source_layout=self.source_layout,
                                experiment_design=self.experiment_design,
                                design_rack_layouts=self.design_rack_layouts)

    def _check_result(self):
        WellAssociatorTestCase._check_result(self)
        completed_src_layout = self.tool.get_completed_source_layout()
        self.assert_is_not_none(completed_src_layout)
        expected_length = len(set(self.result_data_1.keys() \
                              + self.result_data_2.keys()))
        self.assert_equal(len(completed_src_layout), expected_length)
        for tf_pos in completed_src_layout.working_positions():
            if tf_pos.is_mock: continue
            self.assert_is_not_none(tf_pos.final_concentration)

    def _test_and_expect_errors(self, msg=None):
        WellAssociatorTestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_completed_source_layout())

    def test_result(self):
        self._continue_setup()
        self._check_result()

    def test_result_with_design_layouts(self):
        self.pass_design_rack_layouts = True
        self._continue_setup()
        self._check_result()

    def test_result_without_final_concentrations(self):
        self._continue_setup('valid_opti_no_fc.xls')
        layouts = self.tool.get_result()
        self.assert_is_not_none(layouts)
        self.assert_is_not_none(self.tool.get_final_concentrations())
        src_positions = []
        trg_combinations = []
        for tf_layout in layouts.values():
            for rack_pos, tf_pos in tf_layout.iterpositions():
                src_positions.append(rack_pos.label)
                trg_positions = []
                for trg_pos in tf_pos.cell_plate_positions:
                    trg_positions.append(trg_pos.label)
                trg_positions.sort()
                trg_combinations.append(trg_positions)
        expected_src_positions = self.result_data_1.keys() \
                                 + self.result_data_2.keys()
        expected_trg_combinations = self.result_data_1.values() \
                                 + self.result_data_2.values()
        src_positions.sort()
        expected_src_positions.sort()
        self.assert_equal(src_positions, expected_src_positions)
        trg_combinations.sort()
        expected_trg_combinations.sort()
        self.assert_equal(trg_combinations, expected_trg_combinations)

    def test_invalid_experiment_design(self):
        self._test_invalid_experiment_design()

    def test_invalid_source_layout(self):
        self._test_invalid_source_layout()

    def test_layout_conversion_error(self):
        self._test_layout_conversion_error()

    def test_other_reagent_names(self):
        self._continue_setup('opti_other_reagent_names.xls')
        self._test_and_expect_errors('contains other reagent reagent names ' \
                                     'than the ISO plate layout')

    def test_other_reagent_dilution_factor(self):
        self._continue_setup('opti_other_reagent_dil_factor.xls')
        self._test_and_expect_errors('contains other reagent dilution ' \
                                     'factors than the ISO plate layout')

    def test_missing_source(self):
        self._continue_setup('opti_missing_source.xls')
        self._test_and_expect_errors('Could not find source position for ' \
                                     'the following positions in design rack')

    def test_missing_source_no_final_concentration(self):
        self._continue_setup('opti_no_fc_missing_source.xls')
        self._test_and_expect_errors('Could not find source position for the ' \
                                     'following positions')
