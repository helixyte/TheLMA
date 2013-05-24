"""
Base classes for experiment tests.

AAB
"""
from pkg_resources import resource_filename # pylint: disable=E0611
from thelma.automation.tools.metadata.generation \
    import ExperimentMetadataGenerator
from thelma.automation.tools.semiconstants \
    import get_experiment_type_robot_optimisation
from thelma.automation.tools.semiconstants \
    import get_reservoir_specs_standard_96
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.tools.semiconstants import get_384_rack_shape
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_item_status_future
from thelma.automation.tools.semiconstants import get_item_status_managed
from thelma.automation.tools.utils.iso import IsoLayoutConverter
from thelma.automation.tools.worklists.base \
    import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.worklists.base import VOLUME_CONVERSION_FACTOR
from thelma.interfaces import ISubproject
from thelma.interfaces import IUser
from thelma.models.container import WellSpecs
from thelma.models.experiment import Experiment
from thelma.models.experiment import ExperimentMetadata
from thelma.models.experiment import ExperimentRack
from thelma.models.rack import PlateSpecs
from thelma.models.racklayout import RackLayout
from thelma.models.sample import Molecule
from thelma.models.sample import Sample
from thelma.models.user import User
from thelma.tests.tools.tooltestingutils import SilentLog
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase


class ExperimentToolTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.TEST_FILE_PATH = 'thelma:tests/tools/experiment/'
        self.valid_file = None
        self.supports_mastermix = True
        self.VALID_FILES = {
                    EXPERIMENT_SCENARIOS.OPTIMISATION : 'valid_opti.xls',
                    EXPERIMENT_SCENARIOS.SCREENING : 'valid_screen.xls',
                    EXPERIMENT_SCENARIOS.MANUAL : 'valid_manual.xls',
                    EXPERIMENT_SCENARIOS.ISO_LESS : 'valid_isoless.xls'}
        self.VALID_FILES_NO_MM = {
            EXPERIMENT_SCENARIOS.OPTIMISATION : 'valid_opti_no_mastermix.xls',
            EXPERIMENT_SCENARIOS.SCREENING : 'valid_screen_no_mastermix.xls',
            EXPERIMENT_SCENARIOS.MANUAL : 'valid_manual.xls',
            EXPERIMENT_SCENARIOS.ISO_LESS : 'valid_isoless.xls'}
        self.log = TestingLog()
        self.silent_log = SilentLog()
        self.experiment = None
        self.experiment_type = get_experiment_type_robot_optimisation()
        self.user = self._get_entity(IUser, 'it')
        self.exp_rack_specs = None
        self.status = get_item_status_managed()
        self.number_replicates = 2
        self.number_experiments = 1
        self.experiment_metadata = None
        self.experiment_racks = []
        self.iso_rack = None
        self.iso_layout = None
        self.pool_ids = [205200, 1056000]
        self.pool_ids_screen = [205200, 205201, 205202]
        self.experiment_rack_barcodes = ['09999991', '09999992', '09999993',
                                         '09999994']
        self.mol_map = {}
        self.floating_map = dict(md_001=205203, md_002=205204, md_003=205205)
        self.floating_map_screen = dict(md_001=205203, md_002=205204,
                    md_003=205205, md_004=205206, md_005=205207, md_006=205208)
        self.executor_user = User(username='experiment_executor',
                                  directory_user_id=None,
                                  user_preferenceses=None)
        # md, concentration (final)
        self.result_data_common = dict(B2=(205200, 10), B3=(205200, 10),
                                       C2=(205200, 20), C3=(205200, 20),
                                       E2=(1056000, 10), E3=(1056000, 10),
                                       F2=(1056000, 20), F3=(1056000, 20),
                                       H5=(205204, 10), H6=(205204, 10),
                                       I5=(205204, 20), I6=(205204, 20),
                                       K2=(None, 0), K3=(None, 0),
                                       L2=(None, 0), L3=(None, 0))
        self.result_d1 = dict(H2=(205203, 10), H3=(205203, 10),
                              I2=(205203, 20), I3=(205203, 20))
        self.result_d2 = dict(H2=(205205, 10), H3=(205205, 10),
                              I2=(205205, 20), I3=(205205, 20))
        self.result_data_screen = dict(
               C3=(205200, 50), C4=(205200, 100), D3=(205200, 150),
               I9=(205200, 50), I10=(205200, 100), J9=(205200, 150),
               C5=(205201, 50), C6=(205201, 100), D5=(205201, 150),
               I11=(205201, 50), I12=(205201, 100), J11=(205201, 150),
               C7=(205202, 50), C8=(205202, 100), D7=(205202, 150),
               I13=(205202, 50), I14=(205202, 100), J13=(205202, 150),
               C17=(205203, 50), C18=(205203, 100), D17=(205203, 150),
               C19=(205204, 50), C20=(205204, 100), D19=(205204, 150),
               C21=(205205, 50), C22=(205205, 100), D21=(205205, 150),
               I3=(205206, 50), I4=(205206, 100), J3=(205206, 150),
               I5=(205207, 50), I6=(205207, 100), J5=(205207, 150),
               I7=(205208, 50), I8=(205208, 100), J7=(205208, 150),
               # mocks
               D4=(None, 0), J10=(None, 0), D6=(None, 0), J12=(None, 0),
               D8=(None, 0), J14=(None, 0), D18=(None, 0), D20=(None, 0),
               D22=(None, 0), J4=(None, 0), J6=(None, 0), J8=(None, 0))
        self.result_data_manual = dict(B2=(205200, 10), B3=(205200, 20),
                                       D2=(205201, 10), D3=(205201, 20),
                                       F2=(1056000, 10), F3=(1056000, 20))
        self.result_data_isoless = dict(B2=(None, 0), B3=(None, 0),
                        C2=(None, 0), C3=(None, 0), D2=(None, 0), D3=(None, 0))
        # other setup data
        self.iso_plate_barcode = '09999990'
        self.reservoir_specs = get_reservoir_specs_standard_96()
        self.dead_vol = self.reservoir_specs.min_dead_volume
        self.max_vol = self.reservoir_specs.max_volume
        self.well_specs = None
        self.plate_specs_96 = None
        self.plate_specs_384 = None

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.TEST_FILE_PATH
        del self.supports_mastermix
        del self.valid_file
        del self.VALID_FILES
        del self.VALID_FILES_NO_MM
        del self.log
        del self.silent_log
        del self.experiment
        del self.experiment_type
        del self.exp_rack_specs
        del self.status
        del self.number_replicates
        del self.number_experiments
        del self.experiment_metadata
        del self.experiment_racks
        del self.iso_rack
        del self.iso_layout
        del self.pool_ids
        del self.pool_ids_screen
        del self.experiment_rack_barcodes
        del self.mol_map
        del self.floating_map
        del self.floating_map_screen
        del self.result_data_common
        del self.result_d1
        del self.result_d2
        del self.result_data_screen
        del self.result_data_manual
        del self.result_data_isoless
        del self.iso_plate_barcode
        del self.reservoir_specs
        del self.dead_vol
        del self.max_vol
        del self.well_specs
        del self.plate_specs_96
        del self.plate_specs_384

    def _continue_setup(self):
        if self.valid_file is None:
            file_map = self.VALID_FILES_NO_MM
            if self.supports_mastermix: file_map = self.VALID_FILES
            self.valid_file = file_map[self.experiment_type.id]
        self.__set_data_for_experiment_type()
        self._create_test_plate_specs()
        self._create_test_molecules()
        self._create_test_experiment_metadata()
        if not self.experiment_type.id == EXPERIMENT_SCENARIOS.ISO_LESS:
            self._create_test_iso_layout()
            self._create_test_iso_rack()
        self._create_test_experiment()
        self._create_test_experiment_racks()
        self._create_tool()

    def _create_test_plate_specs(self):
        self.well_specs = WellSpecs(label='experiment_test_well_specs',
                               dead_volume=self.dead_vol,
                               max_volume=self.max_vol,
                               plate_specs=None)
        self.plate_specs_96 = PlateSpecs(label='experiment_96_plate_specs',
                                      shape=get_96_rack_shape(),
                                      well_specs=self.well_specs)
        self.plate_specs_384 = PlateSpecs(label='experiment_384_plate_specs',
                                      shape=get_384_rack_shape(),
                                      well_specs=self.well_specs)

    def __set_data_for_experiment_type(self):
        if self.experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
            self.__set_data_for_screen()
        elif self.experiment_type.id == EXPERIMENT_SCENARIOS.MANUAL:
            self.__set_data_for_manual()
        elif self.experiment_type.id == EXPERIMENT_SCENARIOS.ISO_LESS:
            self.__set_data_for_isoless()

    def __set_data_for_screen(self):
        self.pool_ids = self.pool_ids_screen
        self.floating_map = self.floating_map_screen
        self.result_data_common = self.result_data_screen

    def __set_data_for_manual(self):
        self.pool_ids = [205200, 205201, 1056000]
        self.result_data_common = self.result_data_manual
        self.result_d1 = dict()
        self.result_d2 = dict()

    def __set_data_for_isoless(self):
        self.pool_ids = []
        self.result_data_common = self.result_data_isoless
        self.result_d1 = dict()
        self.result_d2 = dict()

    def _create_test_molecules(self):
        supplier = self._create_organization(name='test_supplier')
        all_pools = self.pool_ids + self.floating_map.values()
        for pool_id in all_pools:
            md_pool = self._get_pool(pool_id)
            self.assert_is_not_none(md_pool)
            for md in md_pool:
                mol = Molecule(molecule_design=md, supplier=supplier)
                self.mol_map[md.id] = mol

    def _create_test_experiment_metadata(self):
        ed_file = self.TEST_FILE_PATH + self.valid_file
        file_name = ed_file.split(':')
        f = resource_filename(*file_name) # pylint: disable=W0142
        stream = None
        try:
            stream = open(f, 'rb')
            source = stream.read()
        finally:
            if not stream is None:
                stream.close()
        em = ExperimentMetadata(label='ExperimentTest',
                                subproject=self._get_entity(ISubproject),
                                number_replicates=self.number_replicates,
                                experiment_metadata_type=self.experiment_type,
                                ticket_number=123)
        generator = ExperimentMetadataGenerator.create(stream=source,
                        experiment_metadata=em, requester=self.user)
        self.experiment_metadata = generator.get_result()
        if self.experiment_metadata is None:
            raise ValueError('Error when trying to generate experiment ' \
                             'metadata!')

    def _create_test_iso_layout(self):
        converter = IsoLayoutConverter(log=self.silent_log,
                rack_layout=self.experiment_metadata.iso_request.iso_layout)
        self.iso_layout = converter.get_result()
        self.iso_layout.close()

    def _create_test_iso_rack(self):
        shape = self.experiment_metadata.iso_request.iso_layout.shape
        plate_specs = self.plate_specs_96
        if shape.name == RACK_SHAPE_NAMES.SHAPE_384:
            plate_specs = self.plate_specs_384
        self.iso_rack = plate_specs.create_rack(label='test_iso_rack',
                                                status=self.status)
        self.iso_rack.barcode = self.iso_plate_barcode
        for container in self.iso_rack.containers:
            rack_pos = container.location.position
            iso_pos = self.iso_layout.get_working_position(rack_pos)
            if iso_pos is None: continue
            if iso_pos.is_floating:
                placeholder = iso_pos.molecule_design_pool
                if not self.floating_map.has_key(placeholder): continue
                pool_id = self.floating_map[placeholder]
                md_pool = self._get_pool(pool_id)
            elif iso_pos.is_fixed:
                md_pool = iso_pos.molecule_design_pool
            iso_volume = iso_pos.iso_volume / VOLUME_CONVERSION_FACTOR
            sample = Sample(iso_volume, container)
            if iso_pos.is_mock: continue
            conc = iso_pos.iso_concentration / (len(md_pool) \
                                        * CONCENTRATION_CONVERSION_FACTOR)
            for md in md_pool:
                mol = self.mol_map[md.id]
                sample.make_sample_molecule(mol, conc)

    def _create_test_experiment(self):
        self.experiment = Experiment(label='test_Experiment',
                destination_rack_specs=self.plate_specs_384,
                source_rack=self.iso_rack,
                experiment_design=self.experiment_metadata.experiment_design)

    def _create_test_experiment_racks(self):
        counter = 0
        for design_rack in \
                    self.experiment_metadata.experiment_design.design_racks:
            i = 0
            while i < self.number_replicates:
                barcode = self.experiment_rack_barcodes[counter]
                plate = self.plate_specs_384.create_rack(label=barcode,
                                        status=get_item_status_future())
                plate.barcode = barcode
                ExperimentRack(design_rack=design_rack,
                               rack=plate,
                               experiment=self.experiment)
                self.experiment_racks.append(plate)
                i += 1
                counter += 1

    def _test_invalid_experiment(self):
        self._test_and_expect_errors('experiment must be a Experiment')

    def _test_invalid_iso_layout(self):
        self._continue_setup()
        self.experiment_metadata.iso_request.iso_layout = RackLayout()
        self._test_and_expect_errors('Could not convert ISO transfection ' \
                                     'layout!')

    def _test_previous_execution(self, executor=None, msg=None):
        if executor is None:
            self._continue_setup()
            updated_experiment = self.tool.get_result()
        else:
            updated_experiment = executor.get_result()
        self.assert_is_not_none(updated_experiment)
        if msg is None:
            msg = 'The database update for source plate 09999990 has ' \
                  'already been made before'
        self._test_and_expect_errors(msg)

    def _test_missing_control_sample(self, msg=None):
        self._continue_setup()
        for container in self.iso_rack.containers:
            container.sample = None
        if msg is None:
            msg = 'Some wells of the ISO rack which should contain ' \
                  'controls are empty'
        self._test_and_expect_errors(msg)

    def _init_missing_mock_sample(self):
        self._continue_setup()
        for container in self.iso_rack.containers:
            rack_pos = container.location.position
            iso_pos = self.iso_layout.get_working_position(rack_pos)
            if iso_pos is None: continue
            if iso_pos.is_mock: container.sample = None

    def _test_missing_optimem_worklist(self):
        self._continue_setup()
        series = self.experiment.experiment_design.worklist_series
        for worklist in series:
            if worklist.index == 0: worklist.index = 3
        self._test_and_expect_errors('Could not get worklist for Optimem ' \
                                     'dilution')

    def _test_missing_reagent_worklist(self):
        self._continue_setup()
        series = self.experiment.experiment_design.worklist_series
        for worklist in series:
            if worklist.index == 1: worklist.index = 3
        self._test_and_expect_errors('Could not get worklist for addition ' \
                                     'of transfection reagent')
