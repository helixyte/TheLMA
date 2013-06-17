"""
Tests for robot support experiment tools (executor, writer).

AAB
"""
from pkg_resources import resource_filename # pylint: disable=E0611
from thelma.automation.tools.experiment.executor \
    import ExperimentExecutorOptimisation
from thelma.automation.tools.experiment.executor \
    import ExperimentExecutorScreening
from thelma.automation.tools.experiment.writer \
    import ExperimentWorklistWriterOptimisation
from thelma.automation.tools.experiment.writer \
    import ExperimentWorklistWriterScreening
from thelma.automation.tools.experiment.writer \
    import ReagentPreparationWriter
from thelma.automation.tools.metadata.generation \
    import ExperimentMetadataGenerator
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionParameters
from thelma.automation.tools.metadata.worklist import ReagentWorklistGenerator
from thelma.automation.tools.semiconstants \
    import get_experiment_type_robot_optimisation
from thelma.automation.tools.semiconstants \
    import get_experiment_type_screening
from thelma.automation.tools.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.tools.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.tools.semiconstants import get_positions_for_shape
from thelma.automation.tools.semiconstants import get_reservoir_spec
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.worklists.biomek \
    import ContainerDilutionWorklistWriter
from thelma.interfaces import IItemStatus
from thelma.interfaces import IRackShape
from thelma.interfaces import ISubproject
from thelma.interfaces import IUser
from thelma.models.container import Well
from thelma.models.container import WellSpecs
from thelma.models.experiment import ExperimentMetadata
from thelma.models.liquidtransfer import PlannedRackTransfer
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.liquidtransfer import WorklistSeries
from thelma.models.liquidtransfer import WorklistSeriesMember
from thelma.models.rack import PlateSpecs
from thelma.tests.tools.experiment.base import ExperimentToolTestCase
from thelma.tests.tools.tooltestingutils import FileCreatorTestCase
from thelma.tests.tools.tooltestingutils import SilentLog
from thelma.tests.tools.tooltestingutils import TestingLog
import zipfile


class ExperimentOptimisationToolTestCase(ExperimentToolTestCase):

    def _check_execution_results(self, experiment=None):
        if experiment is None:
            self._continue_setup()
            experiment = self.tool.get_result()
        self.assert_is_not_none(experiment)
        self.__check_experiment_design_worklists(experiment)
        self.__check_experiment_design_rack_worklists(experiment)
        self.__check_iso_plate(experiment)
        self.__check_experiment_plates(experiment)

    def __check_experiment_design_worklists(self, experiment):
        series = experiment.experiment_design.worklist_series
        num_et = len(self.result_data_common) + len(self.result_d1) + \
                 len(self.result_d2) - 2 # -2 for mocks
        for worklist in series:
            self.assert_equal(len(worklist.executed_worklists),
                              self.number_experiments)
            ew = worklist.executed_worklists[0]
            self.assert_equal(len(ew.executed_transfers), num_et)
            timestamp = None
            for et in ew.executed_transfers:
                self.assert_equal(et.type, TRANSFER_TYPES.CONTAINER_DILUTION)
                self.assert_equal(et.user, self.executor_user)
                if timestamp is None:
                    timestamp = et.timestamp
                else:
                    self.assert_equal(timestamp, et.timestamp)

    def __check_experiment_design_rack_worklists(self, experiment):
        worklists = dict()
        design_racks = experiment.experiment_design.design_racks
        for design_rack in design_racks:
            series = design_rack.worklist_series
            for worklist in series:
                worklists[worklist] = design_rack.label
        self.assert_equal(len(worklists), len(design_racks) * 2)
        for worklist, drack_label in worklists.iteritems():
            self.assert_equal(len(worklist.executed_worklists),
                              self.number_replicates * self.number_experiments)
            if worklist.index == 0:
                wl_type = TRANSFER_TYPES.CONTAINER_TRANSFER
            else:
                wl_type = TRANSFER_TYPES.CONTAINER_DILUTION
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
        dil_factor = 4 * TransfectionParameters.REAGENT_MM_DILUTION_FACTOR
        dead_volume = self.reservoir_specs.min_dead_volume \
                      * VOLUME_CONVERSION_FACTOR
        for container in experiment.source_rack.containers:
            rack_pos = container.location.position
            iso_pos = self.iso_layout.get_working_position(rack_pos)
            sample = container.sample
            if iso_pos is None or (iso_pos.is_floating and \
                   not self.floating_map.has_key(iso_pos.molecule_design_pool)):
                self.assert_is_none(sample)
                continue
            if iso_pos.is_mock: continue
            sample_volume = sample.volume * VOLUME_CONVERSION_FACTOR
            self.assert_true(sample_volume >= dead_volume)
            if iso_pos.is_fixed:
                pool = iso_pos.molecule_design_pool
            else:
                placeholder = iso_pos.molecule_design_pool
                pool_id = self.floating_map[placeholder]
                pool = self._get_pool(pool_id)
            conc = round(float(iso_pos.iso_concentration) \
                    / (dil_factor * len(pool)), 2)
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
                elif add_results.has_key(pos_label):
                    data_tuple = add_results[pos_label]
                else:
                    self.assert_is_none(sample)
                    continue
                exp_pool_id = data_tuple[0]
                self._compare_sample_volume(sample, exp_vol)
                if exp_pool_id is None:
                    self.assert_equal(len(sample.sample_molecules), 0)
                else:
                    md_pool = self._get_pool(exp_pool_id)
                    conc = float(data_tuple[1]) / len(md_pool)
                    self._compare_sample_and_pool(sample, md_pool, conc)

    def _test_no_mastermix_support(self):
        self.supports_mastermix = False
        self._continue_setup()
        self._test_and_expect_errors('This experiment is not Biomek-compatible')

    def _test_missing_transfer_worklist(self):
        self._continue_setup()
        series = WorklistSeries()
        pw1 = self._create_planned_worklist(label='wl1')
        WorklistSeriesMember(planned_worklist=pw1, worklist_series=series,
                             index=3)
        pw2 = self._create_planned_worklist(label='wl2')
        WorklistSeriesMember(planned_worklist=pw2, worklist_series=series,
                             index=1)
        for design_rack \
                    in self.experiment_metadata.experiment_design.design_racks:
            design_rack.worklist_series = series
            break
        self._test_and_expect_errors('Could not get worklist for plate ' \
                                'transfer to experiment rack for design rack')

    def _test_missing_cell_worklist(self):
        self._continue_setup()
        series = WorklistSeries()
        pw1 = self._create_planned_worklist(label='wl1')
        WorklistSeriesMember(planned_worklist=pw1, worklist_series=series,
                             index=0)
        pw2 = self._create_planned_worklist(label='wl2')
        WorklistSeriesMember(planned_worklist=pw2, worklist_series=series,
                             index=3)
        for design_rack \
                    in self.experiment_metadata.experiment_design.design_racks:
            design_rack.worklist_series = series
            break
        self._test_and_expect_errors('Could not get worklist for addition ' \
                                     'of cell suspension for design rack')


class ExperimentExecutorOptimisationTestCase(
                                            ExperimentOptimisationToolTestCase):

    def _create_tool(self):
        self.tool = ExperimentExecutorOptimisation(experiment=self.experiment,
                                             user=self.executor_user)

    def test_result(self):
        self._check_execution_results()

    def test_result_empty_floatings(self):
        del self.floating_map['md_003']
        self.result_d2 = {}
        self._check_execution_results()

    def test_unsupported_experiment_type(self):
        self.experiment_type = get_experiment_type_screening()
        self._continue_setup()
        self._test_and_expect_errors('The type of this experiment is not ' \
                                     'supported by this tool')

    def test_invalid_experiment(self):
        self._test_invalid_experiment()

    def test_invalid_iso_layout(self):
        self._test_invalid_iso_layout()

    def test_previous_execution(self):
        self._test_previous_execution()

    def test_missing_control_sample(self):
        self._test_missing_control_sample()

    def test_missing_mock_sample(self):
        self._init_missing_mock_sample()
        self._test_and_expect_errors('Some source containers do not contain ' \
                    'enough volume to provide liquid for all target containers')

    def test_biomek_incompatibility(self):
        self._test_no_mastermix_support()

    def test_missing_optimem_worklist(self):
        self._test_missing_optimem_worklist()

    def test_missing_reagent_worklist(self):
        self._test_missing_reagent_worklist()

    def test_missing_transfer_worklist(self):
        self._test_missing_transfer_worklist()

    def test_missing_cell_worklist(self):
        self._test_missing_cell_worklist()

    def test_series_execution_failure(self):
        self.max_vol = (self.max_vol / 10)
        self._continue_setup()
        self._test_and_expect_errors('Error during serial worklist execution.')


class ReagentPreparationWriterTestCase(FileCreatorTestCase):

    def set_up(self):
        FileCreatorTestCase.set_up(self)
        self.TEST_FILE_PATH = 'thelma:tests/tools/experiment/'
        self.VALID_FILE = 'reagent_preparation_test.xls'
        self.WL_PATH = 'thelma:tests/tools/experiment/csv_files/'
        self.log = TestingLog()
        self.silent_log = SilentLog()
        self.requester = self._get_entity(IUser, 'it')
        self.subproject = self._create_subproject()
        self.experiment_metadata = None
        self.experiment = None
        self.reagent_stream_content = None
        self.target_max_volume = 0.0003 # 300 ul
        self.target_dead_volume = 0.000020 # 20 ul
        self.starting_volume = 0
        self.shape = self._get_entity(IRackShape, '8x12')
        self.status = self._get_entity(IItemStatus)
        self.target_well_specs = WellSpecs(label='target well specs',
                                    max_volume=self.target_max_volume,
                                    dead_volume=self.target_dead_volume,
                                    plate_specs=None)
        self.target_plate_specs = PlateSpecs(label='target plate specs',
                                    shape=self.shape,
                                    well_specs=self.target_well_specs)
        self.target_rack = self.target_plate_specs.create_rack(
                            label='target rack',
                            status=self.status)
        self.__create_rack_containers(self.target_rack, self.target_well_specs,
                                      self.starting_volume)
        self.target_rack.barcode = '0150'

    def tear_down(self):
        FileCreatorTestCase.tear_down(self)
        del self.TEST_FILE_PATH
        del self.VALID_FILE
        del self.log
        del self.silent_log
        del self.requester
        del self.subproject
        del self.experiment_metadata
        del self.experiment
        del self.reagent_stream_content
        del self.target_max_volume
        del self.target_dead_volume
        del self.starting_volume
        del self.shape
        del self.status
        del self.target_well_specs
        del self.target_plate_specs
        del self.target_rack

    def _create_tool(self):
        self.tool = ReagentPreparationWriter(log=self.log,
                            reagent_stream_content=self.reagent_stream_content)

    def __continue_setup(self, em_file):
        self.__read_experiment_file(em_file)
        self.__create_worklist_stream()
        self._create_tool()

    def __read_experiment_file(self, em_file):
        ed_file = self.TEST_FILE_PATH + em_file
        file_name = ed_file.split(':')
        f = resource_filename(*file_name) # pylint: disable=W0142
        stream = None
        try:
            stream = open(f, 'rb')
            source = stream.read()
        finally:
            if not stream is None:
                stream.close()
        em = ExperimentMetadata(label='Reagent Writer Test',
                            subproject=self._get_entity(ISubproject),
                            number_replicates=3,
                            experiment_metadata_type=\
                                    get_experiment_type_robot_optimisation(),
                            ticket_number=123)
        generator = ExperimentMetadataGenerator.create(stream=source,
                    experiment_metadata=em, requester=self.requester)
        self.experiment_metadata = generator.get_result()

    def __create_worklist_stream(self):
        worklist_series = self.experiment_metadata.experiment_design.\
                          worklist_series
        for worklist in worklist_series:
            if ReagentWorklistGenerator.WORKLIST_SUFFIX in worklist.label:
                reagent_worklist = worklist
        rs_tube24 = get_reservoir_spec(RESERVOIR_SPECS_NAMES.TUBE_24)
        worklist_writer = ContainerDilutionWorklistWriter(
                                planned_worklist=reagent_worklist,
                                target_rack=self.target_rack,
                                source_rack_barcode='complexes',
                                reservoir_specs=rs_tube24,
                                log=self.silent_log)
        reagent_stream = worklist_writer.get_result()
        self.reagent_stream_content = reagent_stream.read()

    def __create_rack_containers(self, rack, c_specs, starting_volume):
        for pos in get_positions_for_shape(self.shape):
            container = Well.create_from_rack_and_position(specs=c_specs,
                                                           status=self.status,
                                                           rack=rack,
                                                           position=pos)
            container.make_sample(starting_volume)
            rack.containers.append(container)

    def test_result(self):
        self.__continue_setup(self.VALID_FILE)
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_csv_file_stream(tool_stream,
                                              'reagent_preparation.csv')

    def test_invalid_content(self):
        self.__continue_setup(self.VALID_FILE)
        self.reagent_stream_content = self.requester
        self._test_and_expect_errors('The reagent dilution worklist stream ' \
                                     'must be a str object')


class ExperimentWorklistWriterOptimisationTestCase(FileCreatorTestCase,
                                            ExperimentOptimisationToolTestCase):

    def set_up(self):
        FileCreatorTestCase.set_up(self)
        ExperimentOptimisationToolTestCase.set_up(self)
        self.WL_PATH = 'thelma:tests/tools/experiment/csv_files/'

    def tear_down(self):
        ExperimentOptimisationToolTestCase.tear_down(self)

    def _create_tool(self):
        self.tool = ExperimentWorklistWriterOptimisation(experiment=self.experiment)

    def test_result(self):
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = zipfile.ZipFile(zip_stream, 'a',
                                             zipfile.ZIP_DEFLATED, False)
        for fn in zip_archive.namelist():
            tool_content = zip_archive.read(fn)
            if ExperimentWorklistWriterOptimisation.OPTI_FILE_SUFFIX in fn:
                self._compare_csv_file_content(tool_content,
                                                    'optimem_opti.csv')
            if ExperimentWorklistWriterOptimisation.REAGENT_FILE_SUFFIX in fn:
                self._compare_csv_file_content(tool_content,
                                                    'reagent_opti.csv')
            if ExperimentWorklistWriterOptimisation.PREPARATION_FILE_SUFFIX in fn:
                self._compare_csv_file_content(tool_content,
                                                    'reagent_prep_opti.csv')
            if ExperimentWorklistWriterOptimisation.TRANSFER_FILE_SUFFIX in fn:
                self._compare_csv_file_content(tool_content,
                                                    'transfer_opti.csv')

    def test_result_empty_floating(self):
        del self.floating_map['md_003']
        self.result_d2 = {}
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = zipfile.ZipFile(zip_stream, 'a',
                                             zipfile.ZIP_DEFLATED, False)
        for fn in zip_archive.namelist():
            tool_content = zip_archive.read(fn)
            if ExperimentWorklistWriterOptimisation.OPTI_FILE_SUFFIX in fn:
                self._compare_csv_file_content(tool_content,
                                        'optimem_miss_float_opti.csv')
            if ExperimentWorklistWriterOptimisation.REAGENT_FILE_SUFFIX in fn:
                self._compare_csv_file_content(tool_content,
                                        'reagent_miss_float_opti.csv')
            if ExperimentWorklistWriterOptimisation.PREPARATION_FILE_SUFFIX in fn:
                self._compare_csv_file_content(tool_content,
                                        'reagent_prep_miss_float_opti.csv')
            if ExperimentWorklistWriterOptimisation.TRANSFER_FILE_SUFFIX in fn:
                self._compare_csv_file_content(tool_content,
                                        'transfer_miss_float_opti.csv')

    def test_unsupported_type(self):
        self.experiment_type = get_experiment_type_screening()
        self._continue_setup()
        self._test_and_expect_errors('The type of this experiment is not ' \
                                     'supported by this tool')

    def test_invalid_experiment(self):
        self._test_invalid_experiment()

    def test_invalid_iso_layout(self):
        self._test_invalid_iso_layout()

    def test_previous_execution(self):
        self._continue_setup()
        executor = ExperimentExecutorOptimisation(experiment=self.experiment,
                                                  user=self.executor_user)
        self._test_previous_execution(executor=executor)

    def test_missing_control_sample(self):
        self._test_missing_control_sample()

    def test_missing_mock_sample(self):
        self._init_missing_mock_sample()
        self._test_and_expect_errors('Some source containers do not contain ' \
                    'enough volume to provide liquid for all target containers')

    def test_biomek_incompatibility(self):
        self._test_no_mastermix_support()

    def test_missing_optimem_worklist(self):
        self._test_missing_optimem_worklist()

    def test_missing_reagent_worklist(self):
        self._test_missing_reagent_worklist()

    def test_missing_transfer_worklist(self):
        self._test_missing_transfer_worklist()

    def test_missing_cell_worklist(self):
        self._test_missing_cell_worklist()

    def test_failed_execution(self):
        self.max_vol = (self.max_vol / 10)
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to generate ' \
                                     'worklist files')


class ExperimentScreeningToolTestCase(ExperimentToolTestCase):

    def set_up(self):
        ExperimentToolTestCase.set_up(self)
        self.experiment_type = get_experiment_type_screening()

    def _check_execution_results(self, experiment=None):
        if experiment is None:
            self._continue_setup()
            experiment = self.tool.get_result()
        self.assert_is_not_none(experiment)
        self.__check_executed_worklists(experiment)
        self.__check_iso_plate(experiment)
        self.__check_experiment_plates(experiment)

    def __check_executed_worklists(self, experiment):
        worklist_series = experiment.experiment_design.worklist_series
        self.assert_equal(len(worklist_series), 4)
        optimem_worklist = None
        reagent_worklist = None
        transfer_worklist = None
        cell_worklist = None
        for worklist in worklist_series:
            if worklist.index == 0:
                optimem_worklist = worklist
            elif worklist.index == 1:
                reagent_worklist = worklist
            elif worklist.index == 2:
                transfer_worklist = worklist
            else:
                cell_worklist = worklist
        self.assert_equal(len(optimem_worklist.executed_worklists),
                          self.number_experiments)
        self.assert_equal(len(reagent_worklist.executed_worklists),
                          self.number_experiments)
        optimem_ew = optimem_worklist.executed_worklists[0]
        reagent_ew = reagent_worklist.executed_worklists[0]
        self.assert_equal(len(optimem_ew.executed_transfers),
                          len(reagent_ew.executed_transfers))
        expected_length = len(self.result_data_screen)
        self.assert_equal(len(optimem_ew.executed_transfers), expected_length)
        self.assert_equal(len(reagent_ew.executed_transfers), expected_length)
        for et in optimem_ew.executed_transfers:
            self._check_executed_transfer(et, TRANSFER_TYPES.CONTAINER_DILUTION)
            self.assert_is_not_none(et.target_container)
            rack_pos = et.target_container.location.position
            iso_pos = self.iso_layout.get_working_position(rack_pos)
            self.assert_is_not_none(iso_pos)
            self.assert_false(iso_pos.is_empty)
            self.assert_equal(et.reservoir_specs.name,
                              RESERVOIR_SPECS_NAMES.QUARTER_MODULAR)
        for et in reagent_ew.executed_transfers:
            self._check_executed_transfer(et, TRANSFER_TYPES.CONTAINER_DILUTION)
            self.assert_is_not_none(et.target_container)
            rack_pos = et.target_container.location.position
            iso_pos = self.iso_layout.get_working_position(rack_pos)
            self.assert_is_not_none(iso_pos)
            self.assert_false(iso_pos.is_empty)
            self.assert_equal(et.reservoir_specs.name,
                              RESERVOIR_SPECS_NAMES.TUBE_24)
        num_executed_wls = len(experiment.experiment_design.design_racks) \
                            * self.number_replicates
        self.assert_equal(len(transfer_worklist.executed_worklists),
                          num_executed_wls * self.number_experiments)
        self.assert_equal(len(cell_worklist.executed_worklists),
                          num_executed_wls * self.number_experiments)
        for transfer_ew in transfer_worklist.executed_worklists:
            self.assert_equal(len(transfer_ew.executed_transfers), 1)
            et = transfer_ew.executed_transfers[0]
            self._check_executed_transfer(et, TRANSFER_TYPES.RACK_TRANSFER)
            if self.number_experiments == 1:
                self.assert_equal(et.source_rack.barcode,
                                  self.iso_plate_barcode)
                self.assert_true(et.target_rack.barcode \
                             in self.experiment_rack_barcodes)
                continue
            elif not et.source_rack.barcode == self.iso_plate_barcode:
                continue
            self.assert_true(et.target_rack.barcode \
                             in self.experiment_rack_barcodes)
        for cell_ew in cell_worklist.executed_worklists:
            self.assert_equal(len(cell_ew.executed_transfers),
                                  len(self.result_data_screen))
            for et in cell_ew.executed_transfers:
                self._check_executed_transfer(et,
                                              TRANSFER_TYPES.CONTAINER_DILUTION)
                self.assert_equal(et.reservoir_specs.name,
                                  RESERVOIR_SPECS_NAMES.FALCON_MANUAL)
                target_label = et.target_container.location.position
                self.result_data_screen.has_key(target_label)

    def __check_iso_plate(self, experiment):
        dead_volume = self.reservoir_specs.min_dead_volume \
                      * VOLUME_CONVERSION_FACTOR
        for container in experiment.source_rack.containers:
            rack_pos = container.location.position
            iso_pos = self.iso_layout.get_working_position(rack_pos)
            sample = container.sample
            if iso_pos is None or (iso_pos.is_floating and \
                   not self.floating_map.has_key(iso_pos.molecule_design_pool)):
                self.assert_is_none(sample)
                continue
            if iso_pos.is_mock: continue
            sample_volume = sample.volume * VOLUME_CONVERSION_FACTOR
            self.assert_true(sample_volume >= dead_volume)
            if iso_pos.is_fixed:
                pool = iso_pos.molecule_design_pool
            else:
                placeholder = iso_pos.molecule_design_pool
                pool_id = self.floating_map[placeholder]
                pool = self._get_pool(pool_id)
            conc = float(iso_pos.iso_concentration) \
                    / (TransfectionParameters.REAGENT_MM_DILUTION_FACTOR * 4 \
                      * len(pool))
            self._compare_sample_and_pool(sample, pool, conc)

    def __check_experiment_plates(self, experiment):
        exp_vol = TransfectionParameters.TRANSFER_VOLUME \
                  * TransfectionParameters.CELL_DILUTION_FACTOR
        for exp_rack in experiment.experiment_racks:
            plate = exp_rack.rack
            self.assert_equal(plate.status.name, ITEM_STATUS_NAMES.MANAGED)
            for container in plate.containers:
                sample = container.sample
                pos_label = container.location.position.label
                if self.result_data_common.has_key(pos_label):
                    data_tuple = self.result_data_screen[pos_label]
                else:
                    self.assert_is_none(sample)
                    continue
                self._compare_sample_volume(sample, exp_vol)
                exp_pool_id = data_tuple[0]
                if exp_pool_id is None:
                    self.assert_equal(len(sample.sample_molecules), 0)
                else:
                    md_pool = self._get_pool(exp_pool_id)
                    conc = float(data_tuple[1]) / len(md_pool)
                    self._compare_sample_and_pool(sample, md_pool, conc)

    def _test_missing_transfer_worklist(self):
        self._continue_setup()
        for wl in self.experiment_metadata.experiment_design.worklist_series:
            if wl.index == 2: wl.index = 4
        self._test_and_expect_errors('Could not get worklist for transfer ' \
                                     'from ISO to experiment plate.')

    def _test_missing_cell_worklist(self):
        self._continue_setup()
        ws = WorklistSeries()
        wl1 = self._create_planned_worklist(label='optimem')
        WorklistSeriesMember(planned_worklist=wl1, worklist_series=ws, index=0)
        wl2 = self._create_planned_worklist(label='reagent')
        WorklistSeriesMember(planned_worklist=wl2, worklist_series=ws, index=1)
        wl3 = self._create_planned_worklist(label='transfer')
        prt = self._create_planned_rack_transfer()
        wl3.planned_transfers.append(prt)
        WorklistSeriesMember(planned_worklist=wl3, worklist_series=ws, index=2)
        wl4 = self._create_planned_worklist(label='cells')
        WorklistSeriesMember(planned_worklist=wl4, worklist_series=ws, index=4)
        self.experiment_metadata.experiment_design.worklist_series = ws
        self._test_and_expect_errors('Could not get worklist for transfer ' \
                                     'for the addition of cell suspension.')

    def _test_more_than_one_planned_rack_transfer(self):
        self._continue_setup()
        prt = PlannedRackTransfer(volume=5 / VOLUME_CONVERSION_FACTOR,
                                  source_sector_index=1,
                                  target_sector_index=2,
                                  sector_number=4)
        for wl in self.experiment_metadata.experiment_design.worklist_series:
            if wl.index == 2:
                wl.planned_transfers.append(prt)
        self._test_and_expect_errors('There is more than rack transfer in ' \
                                     'the transfer worklist!')


class ExperimentExecutorScreeningTestCase(ExperimentScreeningToolTestCase):

    def _create_tool(self):
        self.tool = ExperimentExecutorScreening(experiment=self.experiment,
                                            user=self.executor_user)

    def test_result(self):
        self._check_execution_results()

    def test_result_empty_floatings(self):
        del self.floating_map_screen['md_001']
        del self.result_data_screen['C17']
        del self.result_data_screen['C18']
        del self.result_data_screen['D17']
        self._check_execution_results()

    def test_no_samples_for_mocks(self):
        self._init_missing_mock_sample()
        experiment = self.tool.get_result()
        self._check_execution_results(experiment)

    def test_invalid_experiment(self):
        self._test_invalid_experiment()

    def test_invalid_iso_layout(self):
        self._test_invalid_iso_layout()

    def test_previous_execution(self):
        self._continue_setup()
        self._test_previous_execution(executor=self.tool)

    def test_missing_control_sample(self):
        self._test_missing_control_sample()

    def test_missing_transfer_worklist(self):
        self._test_missing_transfer_worklist()

    def test_more_than_one_planned_rack_transfer(self):
        self._test_more_than_one_planned_rack_transfer()

    def test_no_mastermix_support(self):
        self._continue_setup()
        ws = WorklistSeries()
        for wl in self.experiment_metadata.experiment_design.worklist_series:
            if not wl.index == 2: continue
            wl.worklist_series = ws
        self.experiment_metadata.experiment_design.worklist_series = ws
        self._test_and_expect_errors()

    def test_serial_execution_failure(self):
        self.max_vol = 30 / VOLUME_CONVERSION_FACTOR
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to execute ' \
                                     'worklist series!')


class ExperimentWorklistWriterScreeningTestCase(ExperimentScreeningToolTestCase,
                                                FileCreatorTestCase):

    def set_up(self):
        ExperimentScreeningToolTestCase.set_up(self)
        self.WL_PATH = 'thelma:tests/tools/experiment/csv_files/'

    def tear_down(self):
        ExperimentScreeningToolTestCase.tear_down(self)

    def _create_tool(self):
        self.tool = ExperimentWorklistWriterScreening(
                                                experiment=self.experiment)

    def test_result(self):
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = zipfile.ZipFile(zip_stream, 'a',
                                             zipfile.ZIP_DEFLATED, False)
        self.assert_equal(len(zip_archive.namelist()), 4)
        for fn in zip_archive.namelist():
            tool_content = zip_archive.read(fn)
            if ExperimentWorklistWriterOptimisation.OPTI_FILE_SUFFIX in fn:
                self._compare_csv_file_content(tool_content,
                                                    'optimem_screen.csv')
            elif ExperimentWorklistWriterOptimisation.REAGENT_FILE_SUFFIX in fn:
                self._compare_csv_file_content(tool_content,
                                                    'reagent_screen.csv')
            elif ExperimentWorklistWriterOptimisation.PREPARATION_FILE_SUFFIX \
                            in fn:
                self._compare_csv_file_content(tool_content,
                                                    'reagent_prep_screen.csv')
            else:
                self._compare_txt_file_content(tool_content,
                                                    'cybio_transfer.txt')

    def test_result_empty_floating(self):
        del self.floating_map_screen['md_001']
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = zipfile.ZipFile(zip_stream, 'a',
                                             zipfile.ZIP_DEFLATED, False)
        self.assert_equal(len(zip_archive.namelist()), 4)
        for fn in zip_archive.namelist():
            tool_content = zip_archive.read(fn)
            if ExperimentWorklistWriterOptimisation.OPTI_FILE_SUFFIX in fn:
                self._compare_csv_file_content(tool_content,
                                        'optimem_miss_float_screen.csv')
            elif ExperimentWorklistWriterOptimisation.REAGENT_FILE_SUFFIX \
                                        in fn:
                self._compare_csv_file_content(tool_content,
                                        'reagent_miss_float_screen.csv')
            elif ExperimentWorklistWriterOptimisation.PREPARATION_FILE_SUFFIX \
                                        in fn:
                self._compare_csv_file_content(tool_content,
                                        'reagent_prep_miss_float_screen.csv')
            else:
                self._compare_txt_file_content(tool_content,
                                        'cybio_transfer.txt')

    def test_no_samples_for_mocks(self):
        self._init_missing_mock_sample()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = zipfile.ZipFile(zip_stream, 'a',
                                             zipfile.ZIP_DEFLATED, False)
        self.assert_equal(len(zip_archive.namelist()), 4)
        for fn in zip_archive.namelist():
            tool_content = zip_archive.read(fn)
            if ExperimentWorklistWriterOptimisation.OPTI_FILE_SUFFIX in fn:
                self._compare_csv_file_content(tool_content,
                                                    'optimem_screen.csv')
            elif ExperimentWorklistWriterOptimisation.REAGENT_FILE_SUFFIX in fn:
                self._compare_csv_file_content(tool_content,
                                                    'reagent_screen.csv')
            elif ExperimentWorklistWriterOptimisation.PREPARATION_FILE_SUFFIX \
                            in fn:
                self._compare_csv_file_content(tool_content,
                                                    'reagent_prep_screen.csv')
            else:
                self._compare_txt_file_content(tool_content,
                                                    'cybio_transfer.txt')

    def test_unsupported_type(self):
        self.experiment_type = get_experiment_type_robot_optimisation()
        self._continue_setup()
        self._test_and_expect_errors('The type of this experiment is not ' \
                                     'supported by this tool')

    def test_invalid_experiment(self):
        self._test_invalid_experiment()

    def test_invalid_iso_layout(self):
        self._test_invalid_iso_layout()

    def test_previous_execution(self):
        self._continue_setup()
        executor = ExperimentExecutorScreening(experiment=self.experiment,
                                               user=self.executor_user)
        self._test_previous_execution(executor=executor)

    def test_missing_control_sample(self):
        self._test_missing_control_sample()

    def test_missing_transfer_worklist(self):
        self._test_missing_transfer_worklist()

    def test_missing_cell_worklist(self):
        self._test_missing_cell_worklist()

    def test_more_than_one_planned_rack_transfer(self):
        self._test_more_than_one_planned_rack_transfer()

    def test_stream_generation_failure(self):
        self.dead_vol = 40 / VOLUME_CONVERSION_FACTOR
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to generate ' \
                                     'Cybio file!')
