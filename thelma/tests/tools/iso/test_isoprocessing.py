"""
Tests for biomek ISO processing worklist writers.

AAB, Jan 2012
"""
from everest.entities.utils import get_root_aggregate
from thelma.automation.tools.semiconstants import get_experiment_type_order
from thelma.automation.tools.iso.prep_utils import ISO_LABELS
from thelma.automation.tools.iso.isoprocessing \
    import IsoProcessingWorklistWriter
from thelma.automation.tools.iso.isoprocessing import IsoProcessingExecutor
from thelma.automation.tools.iso.preplayoutfinder import PrepLayoutFinder
from thelma.automation.tools.iso.processingworklist \
    import IsoWorklistSeriesGenerator
from thelma.automation.tools.iso.stocktransfer \
    import IsoSampleStockRackWorklistWriter
from thelma.automation.tools.semiconstants \
    import get_experiment_type_manual_optimisation
from thelma.automation.tools.semiconstants \
    import get_experiment_type_robot_optimisation
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.tools.semiconstants import get_384_rack_shape
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_experiment_type_screening
from thelma.automation.tools.semiconstants import get_item_status_future
from thelma.automation.tools.semiconstants import get_item_status_managed
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.stock.base import get_default_stock_concentration
from thelma.automation.tools.utils.iso import IsoLayout
from thelma.automation.tools.utils.iso import IsoPosition
from thelma.automation.tools.worklists.base import VOLUME_CONVERSION_FACTOR
from thelma.interfaces import IJobType
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import IMoleculeType
from thelma.interfaces import IOrganization
from thelma.interfaces import ISubproject
from thelma.models.container import ContainerLocation
from thelma.models.container import TubeSpecs
from thelma.models.container import WellSpecs
from thelma.models.experiment import ExperimentMetadata
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import Iso
from thelma.models.iso import IsoAliquotPlate
from thelma.models.iso import IsoControlStockRack
from thelma.models.iso import IsoPreparationPlate
from thelma.models.iso import IsoRequest
from thelma.models.iso import IsoSampleStockRack
from thelma.models.job import IsoJob
from thelma.models.liquidtransfer import ExecutedWorklist
from thelma.models.liquidtransfer import PlannedContainerTransfer
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.liquidtransfer import WorklistSeries
from thelma.models.liquidtransfer import WorklistSeriesMember
from thelma.models.moleculedesign import MoleculeDesignPoolSet
from thelma.models.moleculetype import MOLECULE_TYPE_IDS
from thelma.models.rack import PlateSpecs
from thelma.models.rack import TubeRackSpecs
from thelma.models.racklayout import RackLayout
from thelma.models.sample import Molecule
from thelma.models.sample import Sample
from thelma.models.utils import get_user
from thelma.tests.tools.tooltestingutils import FileCreatorTestCase
from thelma.tests.tools.tooltestingutils import SilentLog
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase


class IsoProcessingTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.silent_log = SilentLog()
        self.iso = None
        self.setup_includes_stock_transfer = False
        self.preparation_plate = None
        self.prep_plate_barcode = '09999922'
        self.shape_iso = None
        self.iso_layout = None
        self.preparation_layout = None
        self.sample_stock_racks = dict()
        self.stock_transfer_worklists = dict()
        self.stock_rack_barcodes = dict()
        self.aliquot_plate_barcodes = None
        self.experiment_type = None
        self.execute_control_transfer = True
        self.inactivated_positions = []
        # key: rack position, value: (md pool ID, iso conc, parent well,
        # req_vol, iso wells); estimated iso volume: 10 ul
        self.position_data = None
        self.iso_volume = 10
        self.expected_buffer_transfers = None
        # other setup values
        self.iso_request = None
        self.user = get_user('it')
        self.executor_user = get_user('brehm')
        self.status_managed = get_item_status_managed()
        self.status_future = get_item_status_future()
        md_type = get_root_aggregate(IMoleculeType).\
                  get_by_id(MOLECULE_TYPE_IDS.SIRNA)
        self.stock_concentration = get_default_stock_concentration(md_type)
        self.prep_plate_status = self.status_future
        self.well_dead_vol = 10 / VOLUME_CONVERSION_FACTOR
        self.well_specs = None
        self.plate_specs = None
        self.tube_specs = TubeSpecs(label='iso_processing_tube_specs',
                        max_volume=1000 / VOLUME_CONVERSION_FACTOR,
                        dead_volume=5 / VOLUME_CONVERSION_FACTOR,
                        tube_rack_specs=None)
        self.tube_rack_specs = TubeRackSpecs(label='iso_processing_rack_specs',
                                            shape=get_96_rack_shape(),
                                            tube_specs=[self.tube_specs])
        self.stock_src_volume = 50 / VOLUME_CONVERSION_FACTOR
        self.float_map = dict()
        self.control_map = dict()
        self.mol_map = dict()
        self.supplier = self._get_entity(IOrganization)

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.silent_log
        del self.iso
        del self.setup_includes_stock_transfer
        del self.preparation_plate
        del self.prep_plate_barcode
        del self.shape_iso
        del self.iso_layout
        del self.preparation_layout
        del self.sample_stock_racks
        del self.stock_transfer_worklists
        del self.stock_rack_barcodes
        del self.aliquot_plate_barcodes
        del self.experiment_type
        del self.execute_control_transfer
        del self.inactivated_positions
        del self.position_data
        del self.iso_volume
        del self.expected_buffer_transfers
        del self.iso_request
        del self.status_managed
        del self.status_future
        del self.stock_concentration
        del self.prep_plate_status
        del self.well_dead_vol
        del self.well_specs
        del self.plate_specs
        del self.tube_specs
        del self.tube_rack_specs
        del self.stock_src_volume
        del self.float_map
        del self.control_map
        del self.mol_map
        del self.supplier

    def _continue_setup(self):
        self.__create_iso_layout()
        self.__create_test_iso_request()
        self.__create_preparation_layout()
        self.__create_test_worklist_series()
        self.__replace_preparation_floatings()
        self.__create_iso()
        self._create_stock_racks_and_worklists()
        self.__create_plate_specs()
        self._create_preparation_plate()
        self.__create_aliquot_plates()
        self._execute_control_transfer()
        if self.setup_includes_stock_transfer: self._execute_stock_transfer()
        self._create_tool()

    def __create_iso_layout(self):
        self.iso_layout = IsoLayout(shape=self.shape_iso)
        for src_label, trg_data in self.position_data.iteritems():
            iso_conc = trg_data[1]
            iso_volume = self.iso_volume
            pool = self._get_pool(trg_data[0])
            if len(trg_data) > 4:
                trg_labels = trg_data[4]
            else:
                trg_labels = [src_label]
            for trg_label in trg_labels:
                rack_pos = get_rack_position_from_label(trg_label)
                iso_pos = IsoPosition(rack_position=rack_pos,
                        molecule_design_pool=pool, iso_volume=iso_volume,
                        iso_concentration=iso_conc)
                self.iso_layout.add_position(iso_pos)

    def __create_test_iso_request(self):
        self.iso_request = IsoRequest(requester=self.user,
                            iso_layout=self.iso_layout.create_rack_layout(),
                            plate_set_label='iso_processing_request',
                            number_aliquots=len(self.aliquot_plate_barcodes))
        pool = self._get_entity(IMoleculeDesignPool, '205200')
        pool_set = MoleculeDesignPoolSet(molecule_type=pool.molecule_type,
                                         molecule_design_pools=set([pool]))
        ExperimentMetadata(label='test_em',
                           subproject=self._get_entity(ISubproject),
                           number_replicates=3,
                           experiment_metadata_type=self.experiment_type,
                           ticket_number=213,
                           iso_request=self.iso_request,
                           molecule_design_pool_set=pool_set)

    def __create_preparation_layout(self):
        kw = dict(iso_layout=self.iso_layout, iso_request=self.iso_request,
                  log=self.silent_log)
        finder = PrepLayoutFinder.create(**kw)
        self.preparation_layout = finder.get_result()
        for pp in self.preparation_layout.working_positions():
            if pp.is_mock: continue
            if pp.rack_position.label in self.inactivated_positions: continue
            pool_id = pp.molecule_design_pool_id
            if isinstance(pool_id, int):
                barcode = '%06i' % (pool_id)
            elif self.float_map.has_key(pool_id):
                barcode = '%06i' % (self.float_map[pool_id])
            else:
                barcode = '000000'
            pp.stock_tube_barcode = barcode
        self.preparation_layout.set_floating_stock_concentration(
                                                    self.stock_concentration)

    def __create_test_worklist_series(self):
        series_generator = IsoWorklistSeriesGenerator(
                    iso_request=self.iso_request, log=self.silent_log,
                    preparation_layout=self.preparation_layout)
        worklist_series = series_generator.get_result()
        if worklist_series is not None and len(worklist_series) > 0:
            # can be 0 for manual scenarios
            self.iso_request.worklist_series = worklist_series

    def __replace_preparation_floatings(self):
        del_positions = []
        for prep_pos in self.preparation_layout.working_positions():
            if prep_pos.is_inactivated: continue
            pool_id = prep_pos.molecule_design_pool_id
            if self.float_map.has_key(pool_id):
                new_pool_id = self.float_map[pool_id]
                prep_pos.molecule_design_pool = self._get_pool(new_pool_id)
            elif not self.control_map.has_key(pool_id):
                # create missing floats
                del_positions.append(prep_pos.rack_position)
        for rack_pos in del_positions:
            self.preparation_layout.del_position(rack_pos)

    def __create_iso(self):
        label = ISO_LABELS.create_iso_label(iso_request=self.iso_request)
        self.iso = Iso(label=label, iso_request=self.iso_request,
                   rack_layout=self.preparation_layout.create_rack_layout())
        IsoJob(label='iso_processing_test_job',
                 job_type=self._get_entity(IJobType, 'iso-batch'),
                 isos=[self.iso])

    def _create_stock_racks_and_worklists(self):
        raise NotImplementedError('Abstract method.')

    def __create_plate_specs(self):
        self.well_specs = WellSpecs(label='iso_processing_well_specs',
                        max_volume=200 / VOLUME_CONVERSION_FACTOR,
                        dead_volume=self.well_dead_vol,
                        plate_specs=None)
        self.plate_specs = PlateSpecs(label='iso_processing_plate_specs',
                                      shape=self.shape_iso,
                                      well_specs=self.well_specs)

    def _create_preparation_plate(self):
        self.preparation_plate = self.plate_specs.create_rack(
                    label='preparation plate', status=self.prep_plate_status)
        self.preparation_plate.barcode = self.prep_plate_barcode
        IsoPreparationPlate(iso=self.iso, plate=self.preparation_plate)

    def __create_aliquot_plates(self):
        for barcode in self.aliquot_plate_barcodes:
            aliquot_plate = self.plate_specs.create_rack(
                    label='aliquot plate', status=self.status_future)
            aliquot_plate.barcode = barcode
            IsoAliquotPlate(iso=self.iso, plate=aliquot_plate)

    def _execute_control_transfer(self):
        if self.shape_iso.name == RACK_SHAPE_NAMES.SHAPE_384 and \
                    self.experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
            control_rack = self.tube_rack_specs.create_rack(
                                            status=self.status_managed,
                                            label='test_control_stock_rack')
            icsr = IsoControlStockRack(iso_job=self.iso.iso_job,
                        rack=control_rack,
                        rack_layout=get_96_rack_shape(),
                        planned_worklist=PlannedWorklist(label='controls'))
            if self.execute_control_transfer:
                ExecutedWorklist(planned_worklist=icsr.planned_worklist)
            self.iso.status = ISO_STATUS.PREPARED

    def _execute_stock_transfer(self):
        for container in self.preparation_plate.containers:
            rack_pos = container.location.position
            prep_pos = self.preparation_layout.get_working_position(rack_pos)
            if prep_pos is None: continue
            if prep_pos.is_inactivated: continue
            pool_id = prep_pos.molecule_design_pool_id
            if self.experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING and \
                            not pool_id in self.float_map.values(): continue
            if prep_pos.is_mock: continue
            if not prep_pos.parent_well is None: continue
            take_out_vol = prep_pos.get_stock_takeout_volume()
            sample = Sample(take_out_vol / VOLUME_CONVERSION_FACTOR,
                            container)
            if self.shape_iso.name == RACK_SHAPE_NAMES.SHAPE_384 and \
                            self.control_map.has_key(pool_id): continue
            pool = self._get_pool(pool_id)
            conc = pool.default_stock_concentration / (len(pool))
            for md in pool:
                mol = self.mol_map[md.id]
                sample.make_sample_molecule(mol, conc)
        self.preparation_plate.status = self.status_managed
        for issr in self.sample_stock_racks.values():
            ExecutedWorklist(planned_worklist=issr.planned_worklist)
        self.iso.status = ISO_STATUS.IN_PROGRESS

    def _test_invalid_iso(self):
        self._continue_setup()
        self.iso = self.iso_request
        self._test_and_expect_errors('ISO must be a Iso object')

    def _test_invalid_user(self):
        self._continue_setup()
        self.executor_user = self.user.username
        self._test_and_expect_errors('user must be a User object')

    def _test_invalid_preparation_layout(self):
        self._continue_setup()
        self.iso.rack_layout = RackLayout(shape=self.shape_iso)
        self._test_and_expect_errors('Error when trying to convert ' \
                                     'preparation plate layout.')

    def _test_missing_preparation_plate(self):
        self._continue_setup()
        self.iso.iso_preparation_plate = None
        self._test_and_expect_errors('Could not find preparation plate for ' \
                                     'this ISO!')

    def _test_invalid_aliquot_plate(self):
        self._continue_setup()
        for iap in self.iso.iso_aliquot_plates:
            iap.plate = None
        self._test_and_expect_errors('Invalid aliquot plate!')
        self._check_error_messages('Could not find aliquot plates for ' \
                                   'this ISO!')

    def _test_no_aliquot_plates(self):
        self.aliquot_plate_barcodes = []
        self._continue_setup()
        self._test_and_expect_errors('Could not find aliquot plates for ' \
                                     'this ISO!')

    def _test_no_sample_stock_racks(self):
        self._continue_setup()
        self.iso.iso_sample_stock_racks = []
        self._test_and_expect_errors('There are no ISO sample stock racks ' \
                                     'for this ISO!')

    def _test_missing_worklist_series(self):
        self._continue_setup()
        self.iso_request.worklist_series = None

        self._test_and_expect_errors('There is no processing series for ' \
                                     'this ISO request!')

    def _test_incomplete_worklist_series(self):
        self._continue_setup()
        ws = WorklistSeries()
        pw = PlannedWorklist(label='wl')
        WorklistSeriesMember(planned_worklist=pw, worklist_series=ws, index=0)
        self.iso_request.worklist_series = ws
        self._test_and_expect_errors('The processing series for this ISO ' \
                                     'request is incomplete (length: 1).')

    def _test_verification_error(self):
        self.setup_includes_stock_transfer = False
        self.tube_rack_specs.shape = get_384_rack_shape()
        self._continue_setup()
        self._test_and_expect_errors('Error in the stock rack verifier!')
        self._execute_stock_transfer()
        self._create_tool()
        self.assert_is_not_none(self.tool.get_result())

    def _test_no_verification(self):
        self.setup_includes_stock_transfer = False
        self._continue_setup()
        a1_pos = get_rack_position_from_label('A1')
        self.preparation_layout.del_position(a1_pos)
        self.iso.rack_layout = self.preparation_layout.create_rack_layout()
        self._test_and_expect_errors('The stock racks are not compatible ' \
                                     'with the ISO!')

    def _test_state_detection_error(self):
        self.setup_includes_stock_transfer = False
        self.prep_plate_status = self.status_managed
        self._continue_setup()
        for issr in self.sample_stock_racks.values():
            ExecutedWorklist(planned_worklist=issr.planned_worklist)
            break
        self._test_and_expect_errors()

    def _test_previous_execution(self):
        self._continue_setup()
        for iap in self.iso.iso_aliquot_plates:
            iap.plate.status = get_item_status_managed()
            break
        self._test_and_expect_errors('The ISO processing worklist series ' \
                                     'has already been executed before!')

    def _test_unexpected_status(self, iso_status, include_stock_transfer=False):
        self.setup_includes_stock_transfer = include_stock_transfer
        self._continue_setup()
        self.iso.status = iso_status
        self._test_and_expect_errors('Unexpected ISO status')

    def _check_execution_result(self, run_setup=True):
        if run_setup: self._continue_setup()
        updated_iso = self.tool.get_result()
        self.assert_is_not_none(updated_iso)
        self.assert_equal(updated_iso.status, ISO_STATUS.DONE)
        self._check_sample_stock_rack(updated_iso)
        self.__check_preparation_plate(updated_iso)
        self.__check_aliquot_plate(updated_iso)
        if self.experiment_type.id == EXPERIMENT_SCENARIOS.ORDER_ONLY:
            self.assert_is_none(updated_iso.iso_request.worklist_series)
        else:
            self.__check_worklist_series(updated_iso)

    def _check_sample_stock_rack(self, updated_iso):
        raise NotImplementedError('Abstract method.')

    def __check_preparation_plate(self, updated_iso):
        prep_plate = updated_iso.iso_preparation_plate.plate
        self.assert_equal(prep_plate.barcode, self.prep_plate_barcode)
        well_dead_vol = self.well_dead_vol * VOLUME_CONVERSION_FACTOR
        for container in prep_plate.containers:
            rack_pos = container.location.position
            sample = container.sample
            prep_pos = self.preparation_layout.get_working_position(rack_pos)
            if prep_pos is None:
                self.assert_is_none(sample)
                continue
            if prep_pos.is_inactivated:
                self.assert_is_none(sample)
                continue
            sample_volume = sample.volume * VOLUME_CONVERSION_FACTOR
            if self.experiment_type.id == EXPERIMENT_SCENARIOS.ORDER_ONLY:
                self.assert_equal(sample_volume, self.iso_volume)
            else:
                self.assert_true(sample_volume >= well_dead_vol)
            if prep_pos.is_mock: continue
            pool = prep_pos.molecule_design_pool
            conc = prep_pos.prep_concentration / len(pool)
            self._compare_sample_and_pool(sample, pool, conc)

    def __check_aliquot_plate(self, updated_iso):
        self.assert_equal(len(updated_iso.iso_aliquot_plates),
                          updated_iso.iso_request.number_aliquots)
        for iap in updated_iso.iso_aliquot_plates:
            aliquot_plate = iap.plate
            self.assert_true(aliquot_plate.barcode \
                              in self.aliquot_plate_barcodes)
            self.assert_equal(aliquot_plate.status.name,
                              ITEM_STATUS_NAMES.MANAGED)
            for container in aliquot_plate.containers:
                rack_pos = container.location.position
                iso_pos = self.iso_layout.get_working_position(rack_pos)
                sample = container.sample
                if iso_pos is None or \
                                rack_pos.label in self.inactivated_positions:
                    self.assert_is_none(sample)
                    continue
                elif iso_pos.is_floating and \
                    not self.float_map.has_key(iso_pos.molecule_design_pool_id):
                    self.assert_is_none(sample)
                    continue
                if self.experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING \
                            and iso_pos.is_mock: continue
                expected_volume = self.iso_volume
                self._compare_sample_volume(sample, expected_volume)
                if iso_pos.is_mock: continue
                pool_id = iso_pos.molecule_design_pool_id
                if self.float_map.has_key(pool_id):
                    pool_id = self.float_map[pool_id]
                pool = self._get_pool(pool_id)
                conc = iso_pos.iso_concentration / len(pool)
                self._compare_sample_and_pool(sample, pool, conc)

    def __check_worklist_series(self, updated_iso):
        ws = updated_iso.iso_request.worklist_series
        index_map = dict()
        for worklist in ws: index_map[worklist.index] = worklist
        last_index = max(index_map.keys())
        for worklist in ws:
            if worklist.index == 0: # buffer addition
                self.assert_equal(len(worklist.executed_worklists), 1)
                ew = worklist.executed_worklists[0]
                self.assert_equal(len(ew.executed_transfers),
                                  self.expected_buffer_transfers)
                for ecd in ew.executed_transfers:
                    self._check_executed_transfer(ecd,
                                        TRANSFER_TYPES.CONTAINER_DILUTION)
            elif worklist.index == last_index:
                self.assert_equal(len(worklist.executed_worklists), 1)
                ew = worklist.executed_worklists[0]
                if self.experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
                    expected_transfers = self.iso_request.number_aliquots
                    exp_type = TRANSFER_TYPES.RACK_TRANSFER
                else:
                    expected_transfers = len(self.iso_layout) \
                                         - len(self.inactivated_positions)
                    exp_type = TRANSFER_TYPES.CONTAINER_TRANSFER
                self.assert_equal(len(ew.executed_transfers),
                                  expected_transfers)
                for ect in ew.executed_transfers:
                    self._check_executed_transfer(ect, exp_type)
            else:
                self.assert_equal(len(worklist.executed_worklists), 1)
                ew = worklist.executed_worklists[0]
                self.assert_true(len(ew.executed_transfers) > 0)
                if self.experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
                    exp_type = TRANSFER_TYPES.RACK_TRANSFER
                else:
                    exp_type = TRANSFER_TYPES.CONTAINER_TRANSFER
                for ect in ew.executed_transfers:
                    self._check_executed_transfer(ect, exp_type)


class IsoProcessing96TestCase(IsoProcessingTestCase):

    def set_up(self):
        IsoProcessingTestCase.set_up(self)
        self.shape_iso = get_96_rack_shape()
        self.stock_rack_barcode = '09999911'
        self.stock_rack_barcodes = {0 : self.stock_rack_barcode}
        self.aliquot_plate_barcodes = ['09999933']
        self.experiment_type = get_experiment_type_robot_optimisation()
        # key: rack position, value: (md ID, iso conc, parent well, req_vol,
        # iso wells); estimated iso volume: 10 ul
        self.position_data = dict(
                  A1=(205200, 10000, None, 51, ['A1', 'A2', 'A3', 'A4']),
                  B1=(205201, 10000, None, 45, ['B1', 'B2']),
                  B3=(205201, 5000, 'B1', 30, ['B3', 'B4']),
                  C1=(205202, 10000, None, 36, ['C1']),
                  C2=(205202, 5000, 'C1', 32, ['C2']),
                  C3=(205202, 2000, 'C2', 30, ['C3']),
                  C4=(205202, 1000, 'C3', 20, ['C4']),
                  D1=('mock', None, None, 20, ['D1']))
        # key: rack position, value: (pool ID, iso conc, parent well, req_vol,
        # iso wells); estimated iso volume: 10 ul
        self.position_data_one_conc = dict(
                  A1=(205200, 10000, None, 51, ['A1', 'A2', 'A3', 'A4']),
                  B1=(205201, 10000, None, 30, ['B1', 'B2']),
                  C1=(205202, 10000, None, 20, ['C1']),
                  D1=('mock', None, None, 20, ['D1']))
        self.float_map = dict(md_1=205200, md_2=205201, md_3=1056000,
                              mock='mock')
        self.control_map = {
            205200 : self._get_entity(IMoleculeDesignPool, '205200'),
            205201 : self._get_entity(IMoleculeDesignPool, '205201'),
            205202 : self._get_entity(IMoleculeDesignPool, '1056000')}
        self.expected_buffer_transfers = len(self.position_data)

    def tear_down(self):
        IsoProcessingTestCase.tear_down(self)
        del self.position_data_one_conc
        del self.stock_rack_barcode

    def _continue_setup_manual(self, with_dilution=True):
        if with_dilution:
            # key: rack position, value: (md pool ID, iso conc, parent well,
            # req_vol, iso wells); estimated iso volume 10 ul
            self.position_data = dict(
                        A1=(205200, 50000, None, 10, ['A1']),
                        A2=(205202, 40000, None, 10, ['A2']))
        else:
            # key: rack position, value: (md pool ID, iso conc, parent well,
            # req_vol, iso wells); estimated iso volume 10 ul
            self.position_data = dict(
                    A1=(205200, 50000, None, 10, ['A1']),
                    A2=(1056000, 10000, None, 10, ['A2']))

        self.setup_includes_stock_transfer = True
        self.experiment_type = get_experiment_type_manual_optimisation()
        self.aliquot_plate_barcodes = []
        self.expected_buffer_transfers = 1
        self._continue_setup()

    def _create_stock_racks_and_worklists(self):
        self.__create_stock_transfer_worklists()
        self.__create_stock_racks()

    def __create_stock_transfer_worklists(self):
        stock_worklist = PlannedWorklist(label='stock_transfer_biomek')
        starting_wells = self.preparation_layout.get_starting_wells()
        for rack_pos, prep_pos in starting_wells.iteritems():
            if prep_pos.is_mock or prep_pos.is_inactivated: continue
            take_out_volume = prep_pos.get_stock_takeout_volume()
            pct = PlannedContainerTransfer(source_position=rack_pos,
                        target_position=rack_pos,
                        volume=take_out_volume / VOLUME_CONVERSION_FACTOR)
            stock_worklist.planned_transfers.append(pct)
        self.stock_transfer_worklists[0] = stock_worklist

    def __create_stock_racks(self):
        stock_rack = self.tube_rack_specs.create_rack(label='stock_rack',
                                                    status=self.status_managed)
        stock_rack.barcode = self.stock_rack_barcode
        starting_wells = self.preparation_layout.get_starting_wells()
        for rack_pos, prep_pos in starting_wells.iteritems():
            if prep_pos.is_mock or prep_pos.is_inactivated: continue
            barcode = prep_pos.stock_tube_barcode
            tube = self.tube_specs.create_tube(item_status=self.status_managed,
                                               barcode=barcode, location=None)
            ContainerLocation(container=tube, rack=stock_rack,
                              position=rack_pos)
            stock_rack.containers.append(tube)
            sample = Sample(self.stock_src_volume, tube)
            pool = prep_pos.molecule_design_pool
            stock_conc = pool.default_stock_concentration
            conc = stock_conc / len(pool)
            for md in pool:
                mol = Molecule(molecule_design=md, supplier=self.supplier)
                self.mol_map[md.id] = mol
                sample.make_sample_molecule(mol, conc)
        worklist = self.stock_transfer_worklists[0]
        issr = IsoSampleStockRack(iso=self.iso, sector_index=0,
                                  rack=stock_rack, planned_worklist=worklist)
        self.sample_stock_racks[0] = issr

    def _check_sample_stock_rack(self, updated_iso):
        # Check stock rack and worklist
        for issr in updated_iso.iso_sample_stock_racks:
            sector_index = issr.sector_index
            worklist = issr.planned_worklist
            self.assert_equal(len(worklist.executed_worklists), 1)
            if not self.setup_includes_stock_transfer:
                ew = worklist.executed_worklists[0]
                self.assert_equal(len(ew.executed_transfers), 3)
                for et in ew.executed_transfers:
                    self._check_executed_transfer(et,
                                            TRANSFER_TYPES.CONTAINER_TRANSFER)
            stock_rack = issr.rack
            self.assert_equal(stock_rack.barcode,
                              self.stock_rack_barcodes[sector_index])
            for container in stock_rack.containers:
                rack_pos = container.location.position
                pos_label = rack_pos.label
                sample = container.sample
                if not self.position_data.has_key(pos_label):
                    self.assert_is_none(sample)
                    continue
                prep_pos = self.preparation_layout.get_working_position(
                                                                rack_pos)
                if prep_pos.is_mock or not prep_pos.parent_well is None:
                    self.assert_is_none(sample)
                    continue
                expected_volume = self.stock_src_volume \
                                  * VOLUME_CONVERSION_FACTOR
                if not self.setup_includes_stock_transfer:
                    take_out_volume = prep_pos.get_stock_takeout_volume()
                    expected_volume -= take_out_volume
                self._compare_sample_volume(sample, expected_volume)

    def _test_manual_optimisation_without_dilution(self):
        self._continue_setup_manual(with_dilution=False)
        self._test_and_expect_errors('This ISO does not require further ' \
                         'processing. The preparation plate can be passed to ' \
                         'the lab directly.')


class IsoProcessingWorklistWriter96TestCase(IsoProcessing96TestCase,
                                            FileCreatorTestCase):

    def set_up(self):
        IsoProcessing96TestCase.set_up(self)
        self.WL_PATH = 'thelma:tests/tools/iso/csv_files/'

    def tear_down(self):
        IsoProcessing96TestCase.tear_down(self)
        del self.WL_PATH

    def _create_tool(self):
        self.tool = IsoProcessingWorklistWriter(iso=self.iso)

    def test_result_without_stock(self):
        self.setup_includes_stock_transfer = True
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 5)
        for fil in zip_archive.namelist():
            tool_content = zip_archive.read(fil)
            if self.tool.ANNEALING_FILE_SUFFIX[2:] in fil:
                self._compare_csv_file_content(tool_content,
                                                'buffer_96.csv')
            elif self.tool.TRANSFER_FILE_SUFFIX[2:] in fil:
                self._compare_csv_file_content(tool_content,
                                                'aliquot_transfer_96.csv')
            else:
                wl_number = fil[-5]
                exp_file_name = 'processing_dilution96_%s.csv' % (wl_number)
                self._compare_csv_file_content(tool_content,
                                                       exp_file_name)

    def test_result_with_stock(self):
        self.setup_includes_stock_transfer = False
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 6)
        for fil in zip_archive.namelist():
            tool_content = zip_archive.read(fil)
            if self.tool.ANNEALING_FILE_SUFFIX[2:] in fil:
                self._compare_csv_file_content(tool_content,
                                                'buffer_96.csv')
            elif self.tool.TRANSFER_FILE_SUFFIX[2:] in fil:
                self._compare_csv_file_content(tool_content,
                                                'aliquot_transfer_96.csv')
            elif IsoSampleStockRackWorklistWriter.BIOMEK_FILE_NAME[2:] in fil:
                self._compare_csv_file_content(tool_content,
                                                'stock_transfer_96.csv')
            else:
                wl_number = fil[-5]
                exp_file_name = 'processing_dilution96_%s.csv' % (wl_number)
                self._compare_csv_file_content(tool_content,
                                                       exp_file_name)

    def test_result_one_concentration_without_stock(self):
        self.setup_includes_stock_transfer = True
        self.position_data = self.position_data_one_conc
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_is_not_none(zip_archive)
        self.assert_equal(len(zip_archive.namelist()), 2)
        for fil in zip_archive.namelist():
            tool_content = zip_archive.read(fil)
            if self.tool.ANNEALING_FILE_SUFFIX[2:] \
                in fil:
                self._compare_csv_file_content(tool_content,
                                            'buffer_96_one_conc.csv')
            elif self.tool.TRANSFER_FILE_SUFFIX[2:] \
                in fil:
                self._compare_csv_file_content(tool_content,
                                            'aliquot_transfer_96_one_conc.csv')

    def test_result_one_concentration_with_stock(self):
        self.setup_includes_stock_transfer = False
        self.position_data = self.position_data_one_conc
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_is_not_none(zip_archive)
        self.assert_equal(len(zip_archive.namelist()), 3)
        for fil in zip_archive.namelist():
            tool_content = zip_archive.read(fil)
            if self.tool.ANNEALING_FILE_SUFFIX[2:] in fil:
                self._compare_csv_file_content(tool_content,
                                            'buffer_96_one_conc.csv')
            elif self.tool.TRANSFER_FILE_SUFFIX[2:] in fil:
                self._compare_csv_file_content(tool_content,
                                            'aliquot_transfer_96_one_conc.csv')
            else:
                self._compare_csv_file_content(tool_content,
                                             'stock_transfer_96_one_conc.csv')

    def test_result_manual_with_dilution(self):
        self._continue_setup_manual()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 1)
        for fil in zip_archive.namelist():
            tool_content = zip_archive.read(fil)
            self._compare_csv_file_content(tool_content, 'buffer_manual.csv')

    def test_result_manual_without_dilution(self):
        self._test_manual_optimisation_without_dilution()

    def test_result_inactivated_position(self):
        self.setup_includes_stock_transfer = True
        self.inactivated_positions = ['B1', 'B3']
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 5)
        for fil in zip_archive.namelist():
            tool_content = zip_archive.read(fil)
            if self.tool.ANNEALING_FILE_SUFFIX[2:] in fil:
                self._compare_csv_file_content(tool_content,
                                    'buffer_96_inactivated_pos.csv')
            elif self.tool.TRANSFER_FILE_SUFFIX[2:] in fil:
                self._compare_csv_file_content(tool_content,
                                    'aliquot_transfer_96_inactivated_pos.csv')
            else:
                wl_number = fil[-5]
                if wl_number == '1':
                    exp_file_name = 'processing_dilution96_inact_1.csv'
                else:
                    exp_file_name = 'processing_dilution96_%s.csv' % (wl_number)
                self._compare_csv_file_content(tool_content,
                                                       exp_file_name)

    def test_invalid_iso(self):
        self._test_invalid_iso()

    def test_invalid_preparation_layout(self):
        self._test_invalid_preparation_layout()

    def test_missing_preparation_plate(self):
        self._test_missing_preparation_plate()

    def test_invalid_aliquot_plate(self):
        self._test_invalid_aliquot_plate()

    def test_no_aliquot_plates(self):
        self._test_no_aliquot_plates()

    def test_no_sample_stock_racks(self):
        self._test_no_sample_stock_racks()

    def test_missing_worklist_series(self):
        self._test_missing_worklist_series()

    def test_incomplete_worklist_series(self):
        self._test_incomplete_worklist_series()

    def test_verification_error(self):
        self._test_verification_error()

    def test_no_verification(self):
        self._test_no_verification()

    def test_state_detection_error(self):
        self._test_state_detection_error()

    def test_stock_transfer_error(self):
        self.setup_includes_stock_transfer = False
        self.stock_src_volume = 10 / VOLUME_CONVERSION_FACTOR
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to generate files ' \
                                     'for the sample stock transfer.')
        self._execute_stock_transfer()
        self._create_tool()
        self.assert_is_not_none(self.tool.get_result())

    def test_serial_writing_failure(self):
        self.well_dead_vol = self.well_dead_vol * 3
        self._continue_setup()
        self._test_and_expect_errors('Error during serial worklist ' \
                                     'file generation.')

class IsoProcessingExecutor96TestCase(IsoProcessing96TestCase):

    def _create_tool(self):
        self.tool = IsoProcessingExecutor(iso=self.iso, user=self.executor_user)

    def _test_and_expect_errors(self, msg=None):
        IsoProcessing96TestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_executed_stock_worklists())
        self.assert_is_none(self.tool.get_working_layout())

    def _check_execution_result(self, run_setup=True):
        IsoProcessing96TestCase._check_execution_result(self, run_setup)
        stock_ews = self.tool.get_executed_stock_worklists()
        self.assert_is_not_none(stock_ews)
        if self.setup_includes_stock_transfer:
            self.assert_equal(len(stock_ews), 0)
        else:
            self.assert_equal(len(stock_ews), 1)
            ew = stock_ews.values()[0]
            self.assert_equal(len(ew.executed_transfers), 3)
            for et in ew.executed_transfers:
                self._check_executed_transfer(et,
                                              TRANSFER_TYPES.CONTAINER_TRANSFER)
        tool_layout = self.tool.get_working_layout()
        self.assert_is_not_none(tool_layout)
        self.assert_equal(tool_layout, self.preparation_layout)

    def test_result_without_stock(self):
        self.setup_includes_stock_transfer = True
        self._check_execution_result()

    def test_result_with_stock(self):
        self.setup_includes_stock_transfer = False
        self._check_execution_result()

    def test_result_one_concentration_without_stock(self):
        self.setup_includes_stock_transfer = True
        self.position_data = self.position_data_one_conc
        self.expected_buffer_transfers = len(self.position_data)
        self._check_execution_result()

    def test_result_one_concentration_with_stock(self):
        self.setup_includes_stock_transfer = False
        self.position_data = self.position_data_one_conc
        self.expected_buffer_transfers = len(self.position_data)
        self._check_execution_result()

    def test_result_manual_with_dilution(self):
        self._continue_setup_manual()
        self._check_execution_result(run_setup=False)

    def test_manual_optimisation_without_dilution(self):
        self._test_manual_optimisation_without_dilution()

    def test_result_inactivated_positions(self):
        self.inactivated_positions = ['B1', 'B2', 'B3', 'B4']
        self.setup_includes_stock_transfer = True
        self.expected_buffer_transfers = 6
        self._check_execution_result()

    def test_invalid_iso(self):
        self._test_invalid_iso()

    def test_invalid_user(self):
        self._test_invalid_user()

    def test_invalid_preparation_layout(self):
        self._test_invalid_preparation_layout()

    def test_missing_preparation_plate(self):
        self._test_missing_preparation_plate()

    def test_invalid_aliquot_plate(self):
        self._test_invalid_aliquot_plate()

    def test_no_aliquot_plates(self):
        self._test_no_aliquot_plates()

    def test_no_sample_stock_racks(self):
        self._test_no_sample_stock_racks()

    def test_missing_worklist_series(self):
        self._test_missing_worklist_series()

    def test_incomplete_worklist_series(self):
        self._test_incomplete_worklist_series()

    def test_verification_error(self):
        self._test_verification_error()

    def test_no_verification(self):
        self._test_no_verification()

    def test_state_detection_error(self):
        self._test_state_detection_error()

    def test_series_execution_failure(self):
        self.well_dead_vol = self.well_dead_vol * 3
        self._continue_setup()
        self._test_and_expect_errors('Error during serial transfer execution.')

    def test_previous_execution(self):
        self._test_previous_execution()

    def test_unexpected_status_with_stock_transfer(self):
        self._test_unexpected_status(ISO_STATUS.IN_PROGRESS,
                                     include_stock_transfer=False)

    def test_unexpected_status_without_stock_transfer(self):
        self._test_unexpected_status(ISO_STATUS.QUEUED,
                                     include_stock_transfer=True)


class IsoProcessing384TestCase(IsoProcessingTestCase):

    def set_up(self):
        IsoProcessingTestCase.set_up(self)
        self.create_single_stock_rack = False
        self.shape_iso = get_384_rack_shape()
        self.stock_rack_barcodes = {0 : '09999911', 1: '09999912',
                                    2 : '09999913', 3: '09999914'}
        self.aliquot_plate_barcodes = ['09999931', '09999932']
        self.experiment_type = get_experiment_type_screening()
        self.expected_transfers_per_stock_transfer = [3]
        # data tuple: molecule design, iso conc, parent well, req vol
        # key: rack position, value: (md ID, iso conc, parent well, req_vol,
        # iso wells); estimated iso volume: 10 ul
        self.position_data = dict(
                # first quadrant
                A1=(205200, 10000, None, 30), A2=(205201, 10000, None, 30),
                B1=('md_001', 10000, None, 30), B2=('md_002', 10000, None, 30),
                # second quadrant
                A3=('md_003', 10000, None, 30), A4=('md_004', 10000, None, 30),
                B3=('md_005', 10000, None, 30), B4=('md_006', 10000, None, 30),
                # third quadrant
                C1=('md_007', 10000, None, 30), C2=('md_008', 10000, None, 30),
                D1=('md_009', 10000, None, 30), D2=('md_010', 10000, None, 30),
                # fourth quadrant
                C3=('mock', None, None, 30), C4=('mock', None, None, 30),
                D3=(205200, 10000, None, 30), D4=(205201, 10000, None, 30))
        self.sector_data = {
                0 : ['A1', 'A3', 'C1', 'C3'], 1 : ['A2', 'A4', 'C2', 'C4'],
                2 : ['B1', 'B3', 'D1', 'D3'], 3 : ['B2', 'B4', 'D2', 'D4']}
        self.source_positions = dict(A1=['A1', 'A2', 'B1', 'B2'],
                                     A2=['A3', 'A4', 'B3', 'B4'],
                                     B1=['C1', 'C2', 'D1', 'D2'],
                                     B2=['C3', 'C4', 'D3', 'D4'])
        self.position_data_multi_conc = dict(
                # first quadrant
                A1=('md_001', 10000, None, 30), A2=('md_001', 5000, 'A1', 20),
                B1=('md_002', 10000, None, 30), B2=('md_002', 5000, 'B1', 20),
                # second quadrant
                A3=('md_003', 10000, None, 30), A4=('md_003', 5000, 'A3', 20),
                B3=('md_004', 10000, None, 30), B4=('md_004', 5000, 'B3', 20),
                # third quadrant
                C1=('md_005', 10000, None, 30), C2=('md_005', 5000, 'C1', 20),
                D1=(205200, 10000, None, 30), D2=(205200, 5000, 'D1', 20),
                # fourth quadrant
                C3=(205200, 10000, None, 30), C4=(205200, 5000, 'C3', 20),
                D3=('mock', None, None, 30), D4=('mock', None, None, 20))
        self.position_data_aliquot_buffer = dict(
                # first quadrant
                A1=(205200, 100, None, 30), A2=(205201, 100, None, 30),
                B1=('md_001', 100, None, 30), B2=('md_002', 100, None, 30),
                # second quadrant
                A3=('md_003', 100, None, 30), A4=('md_004', 100, None, 30),
                B3=('md_005', 100, None, 30), B4=('md_006', 100, None, 30),
                # third quadrant
                C1=('md_007', 100, None, 30), C2=('md_008', 100, None, 30),
                D1=('md_009', 100, None, 30), D2=('md_010', 100, None, 30),
                # fourth quadrant
                C3=('mock', None, None, 30), C4=('mock', None, None, 30),
                D3=(205200, 100, None, 30), D4=(205201, 100, None, 30))
        self.float_map = dict(md_001=205203, md_002=205204, md_003=205205,
                              md_004=205206, md_005=205207, md_006=205208,
                              md_007=205209, md_008=205210, md_009=205212,
                              md_010=205214)
        self.control_map = {
            205200 : self._get_entity(IMoleculeDesignPool, '205200'),
            205201 : self._get_entity(IMoleculeDesignPool, '205201') }
        self.expected_buffer_transfers = len(self.position_data) - 2 # mocks

    def tear_down(self):
        IsoProcessingTestCase.tear_down(self)
        del self.create_single_stock_rack
        del self.expected_transfers_per_stock_transfer
        del self.sector_data
        del self.source_positions
        del self.position_data_multi_conc
        del self.position_data_aliquot_buffer

    def _continue_setup_multi_conc(self):
        self.position_data = self.position_data_multi_conc
        del self.sector_data[1]
        del self.sector_data[3]
        self.expected_buffer_transfers = len(self.position_data) - 2
        self._continue_setup()

    def _continue_setup_opti(self):
        self.setup_includes_stock_transfer = False
        self.create_single_stock_rack = True
        self.experiment_type = get_experiment_type_robot_optimisation()
        self.aliquot_plate_barcodes = self.aliquot_plate_barcodes[:1]
        self.position_data = dict(
                # first quadrant
                A1=(205203, 10000, None, 30), A2=(205203, 5000, 'A1', 20),
                B1=(205204, 10000, None, 30), B2=(205204, 5000, 'B1', 20),
                # second quadrant
                A3=(205205, 10000, None, 30), A4=(205205, 5000, 'A3', 20),
                B3=(205206, 10000, None, 30), B4=(205206, 5000, 'B3', 20),
                # third quadrant
                C1=(205207, 10000, None, 30), C2=(205207, 5000, 'C1', 20),
                D1=(205200, 10000, None, 45, ['D1', 'E1']),
                D2=(205200, 5000, 'D1', 30, ['D2', 'E2']),
                # fourth quadrant
                C3=(205201, 10000, None, 30), C4=(205201, 5000, 'C3', 20),
                D3=('mock', None, None, 30), D4=('mock', None, 'D3', 0))
        control_mds = [205203, 205204, 205205, 205206, 205207, 205200,
                       205201, 'mock']
        self.control_map = dict()
        for control_md in control_mds: self.float_map[control_md] = control_md
        self.expected_transfers_per_stock_transfer = [7]
        self.expected_buffer_transfers = 15
        self._continue_setup()

    def _continue_setup_order_only(self):
        self.setup_includes_stock_transfer = False
        self.create_single_stock_rack = True
        self.experiment_type = get_experiment_type_order()
        self.aliquot_plate_barcodes = list()
        # key: rack position, value: (md pool ID, iso conc, parent well,
        # req_vol, iso wells); estimated iso volume: 1 ul
        self.iso_volume = 1
        self.position_data = dict(
                        B2=[205201, 50000, None, 1],
                        B4=[330001, 10000, None, 1],
                        B6=[333803, 5000000, None, 1],
                        B8=[1056000, 10000, None, 1],
                        B10=[180202, 50000, None, 1])
        control_mds = [205201, 330001, 333803, 1056000, 180202]
        for control_md in control_mds: self.float_map[control_md] = control_md
        self.control_map = dict()
        self.expected_transfers_per_stock_transfer = [5]
        self._continue_setup()

    def _continue_setup_empty_floatings(self):
        del self.float_map['md_010']
        self._continue_setup()
        del self.position_data['D2']
        self.expected_transfers_per_stock_transfer = [2, 3]
        self.expected_buffer_transfers = len(self.position_data) - 2 # 2 mocks

    def _create_stock_racks_and_worklists(self):
        if self.create_single_stock_rack:
            self.__create_single_stock_rack()
        else:
            self.__create_sector_stock_rack()

    def __create_sector_stock_rack(self):
        for sector_index in self.sector_data.keys():
            worklist = PlannedWorklist('Q%i' % (sector_index + 1))
            barcode = self.stock_rack_barcodes[sector_index]
            stock_rack = self.tube_rack_specs.create_rack(
                                label='Q%i' % (sector_index + 1),
                                status=self.status_managed)
            stock_rack.barcode = barcode
            for src_label, trg_labels in self.source_positions.iteritems():
                trg_label = trg_labels[sector_index]
                src_pos = get_rack_position_from_label(src_label)
                trg_pos = get_rack_position_from_label(trg_label)
                prep_pos = self.preparation_layout.get_working_position(trg_pos)
                if prep_pos is None: continue # mock positions
                if not prep_pos.parent_well is None or prep_pos.is_inactivated:
                    continue
                pool_id = prep_pos.molecule_design_pool_id
                if not pool_id in self.float_map.values(): continue
                tube_barcode = prep_pos.stock_tube_barcode
                tube = self.tube_specs.create_tube(barcode=tube_barcode,
                        item_status=self.status_managed, location=None)
                ContainerLocation(container=tube, rack=stock_rack,
                                  position=src_pos)
                stock_rack.containers.append(tube)
                tube.make_sample(self.stock_src_volume)
                pool = self._get_pool(pool_id)
                conc = pool.default_stock_concentration / (len(pool))
                for md in pool:
                    mol = Molecule(molecule_design=md, supplier=self.supplier)
                    self.mol_map[md.id] = mol
                    tube.sample.make_sample_molecule(mol, conc)
                take_out_vol = prep_pos.get_stock_takeout_volume()
                volume = take_out_vol / VOLUME_CONVERSION_FACTOR
                pct = PlannedContainerTransfer(volume=volume,
                            source_position=src_pos, target_position=trg_pos)
                worklist.planned_transfers.append(pct)
            issr = IsoSampleStockRack(iso=self.iso, rack=stock_rack,
                                      sector_index=sector_index,
                                      planned_worklist=worklist)
            self.sample_stock_racks[sector_index] = issr
            self.stock_transfer_worklists[sector_index] = worklist

    def __create_single_stock_rack(self):
        worklist = PlannedWorklist(label='single_biomek')
        barcode = self.stock_rack_barcodes[0]
        stock_rack = self.tube_rack_specs.create_rack(label='single_biomek',
                                                status=self.status_managed)
        stock_rack.barcode = barcode
        for rack_pos, prep_pos in self.preparation_layout.iterpositions():
            if prep_pos.is_mock or prep_pos.is_inactivated: continue
            if not prep_pos.parent_well is None: continue
            pool_id = prep_pos.molecule_design_pool_id
            if not pool_id in self.float_map.values(): continue
            tube_barcode = prep_pos.stock_tube_barcode
            tube = self.tube_specs.create_tube(
                                item_status=self.status_managed,
                                barcode=tube_barcode, location=None)
            ContainerLocation(container=tube, rack=stock_rack,
                              position=rack_pos)
            stock_rack.containers.append(tube)
            sample = Sample(self.stock_src_volume, tube)
            pool = self._get_pool(pool_id)
            conc = pool.default_stock_concentration / (len(pool))
            for md in pool:
                mol = Molecule(molecule_design=md, supplier=self.supplier)
                self.mol_map[md.id] = mol
                sample.make_sample_molecule(mol, conc)
            take_out_volume = prep_pos.get_stock_takeout_volume()
            volume = take_out_volume / VOLUME_CONVERSION_FACTOR
            pct = PlannedContainerTransfer(volume=volume,
                        source_position=rack_pos, target_position=rack_pos)
            worklist.planned_transfers.append(pct)
        issr = IsoSampleStockRack(iso=self.iso, rack=stock_rack,
                                  sector_index=0, planned_worklist=worklist)
        self.sample_stock_racks[0] = issr
        self.stock_transfer_worklists[0] = worklist

    def _create_preparation_plate(self):
        IsoProcessingTestCase._create_preparation_plate(self)
        for well in self.preparation_plate.containers:
            rack_pos = well.location.position
            prep_pos = self.preparation_layout.get_working_position(rack_pos)
            if prep_pos is None: continue
            if not prep_pos.parent_well is None or prep_pos.is_inactivated or \
                    not prep_pos.is_fixed:
                continue
            pool_id = prep_pos.molecule_design_pool_id
            if not self.control_map.has_key(pool_id): continue
            takeout_volume = prep_pos.get_stock_takeout_volume()
            sample = Sample(takeout_volume / VOLUME_CONVERSION_FACTOR, well)
            pool = self._get_pool(pool_id)
            conc = pool.default_stock_concentration / (len(pool))
            for md in pool:
                mol = Molecule(molecule_design=md, supplier=self.supplier)
                self.mol_map[md.id] = mol
                sample.make_sample_molecule(mol, conc)

    def _check_sample_stock_rack(self, updated_iso):
        if self.create_single_stock_rack:
            meth = self.__check_single_stock_rack
        else:
            meth = self.__check_sector_stock_rack
        for issr in updated_iso.iso_sample_stock_racks:
            sector_index = issr.sector_index
            worklist = issr.planned_worklist
            self.assert_equal(len(worklist.executed_worklists), 1)
            if not self.setup_includes_stock_transfer:
                ew = worklist.executed_worklists[0]
                self.assert_true(len(ew.executed_transfers) in \
                                 self.expected_transfers_per_stock_transfer)
                for et in ew.executed_transfers:
                    self._check_executed_transfer(et,
                                            TRANSFER_TYPES.CONTAINER_TRANSFER)
            stock_rack = issr.rack
            self.assert_equal(stock_rack.barcode,
                              self.stock_rack_barcodes[sector_index])
            meth(stock_rack, sector_index)

    def __check_sector_stock_rack(self, stock_rack, sector_index):
        src_positions = dict()
        for src_label, target_labels in self.source_positions.iteritems():
            trg_label = target_labels[sector_index]
            rack_pos = get_rack_position_from_label(trg_label)
            prep_pos = self.preparation_layout.get_working_position(rack_pos)
            if prep_pos is None: continue
            pool_id = prep_pos.molecule_design_pool_id
            if not pool_id in self.float_map.values(): continue
            take_out_vol = prep_pos.get_stock_takeout_volume()
            src_positions[src_label] = take_out_vol
        for container in stock_rack.containers:
            pos_label = container.location.position.label
            sample = container.sample
            if not src_positions.has_key(pos_label):
                self.assert_is_none(sample)
                continue
            expected_volume = self.stock_src_volume * VOLUME_CONVERSION_FACTOR
            if not self.setup_includes_stock_transfer:
                expected_volume -= src_positions[pos_label]
            self._compare_sample_volume(sample, expected_volume)

    def __check_single_stock_rack(self, stock_rack, sector_index): #pylint: disable=W0613
        for container in stock_rack.containers:
            rack_pos = container.location.position
            pos_label = rack_pos.label
            sample = container.sample
            if not self.position_data.has_key(pos_label):
                self.assert_is_none(sample)
                continue
            prep_pos = self.preparation_layout.get_working_position(
                                                            rack_pos)
            if prep_pos.is_mock or not prep_pos.parent_well is None:
                self.assert_is_none(sample)
                continue
            expected_volume = self.stock_src_volume \
                              * VOLUME_CONVERSION_FACTOR
            if not self.setup_includes_stock_transfer:
                take_out_volume = prep_pos.get_stock_takeout_volume()
                expected_volume -= take_out_volume
            self._compare_sample_volume(sample, expected_volume)

    def _test_no_sample_stock_racks(self):
        self.stock_rack_barcodes = dict()
        self.sector_data = dict()
        self._continue_setup()
        self._test_and_expect_errors('There are no ISO sample stock racks ' \
                                     'for this ISO!')

    def _test_failed_stock_transfer_job_generation(self):
        self.setup_includes_stock_transfer = False
        self.execute_control_transfer = False
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to generate stock ' \
                                     'transfer jobs.')

    def _test_order_with_executed_stock_transfer(self):
        self._continue_setup_order_only()
        self._execute_stock_transfer()
        self._test_and_expect_errors('The transfer from the stock to ' \
             'preparation plate has already taken place for this ISO. ' \
             'ISOs for "ISO without experiment" scenarios are already ' \
             'completed with this step and do not require further processing.')


class IsoProcessingWorklistWriter384TestCase(IsoProcessing384TestCase,
                                            FileCreatorTestCase):

    def set_up(self):
        IsoProcessing384TestCase.set_up(self)
        self.WL_PATH = 'thelma:tests/tools/iso/csv_files/'

    def tear_down(self):
        IsoProcessing384TestCase.tear_down(self)
        del self.WL_PATH

    def _create_tool(self):
        self.tool = IsoProcessingWorklistWriter(iso=self.iso)

    def test_result_one_conc_without_stock(self):
        self.setup_includes_stock_transfer = True
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 2)
        for fil in zip_archive.namelist():
            tool_content = zip_archive.read(fil)
            if self.tool.ANNEALING_FILE_SUFFIX[2:] in fil:
                self._compare_csv_file_content(tool_content,
                                        'buffer_384_one_conc.csv')
            else:
                self._compare_txt_file_content(tool_content,
                                        'aliquot_transfer_384_one_conc.txt')

    def test_result_one_conc_with_stock(self):
        self.setup_includes_stock_transfer = False
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 4)
        for fil in zip_archive.namelist():
            tool_content = zip_archive.read(fil)
            if self.tool.ANNEALING_FILE_SUFFIX[2:] in fil:
                self._compare_csv_file_content(tool_content,
                                        'buffer_384_one_conc.csv')
            elif self.tool.CYBIO_FILE_SUFFIX[2:] in fil:
                self._compare_txt_file_content(tool_content,
                                        'aliquot_transfer_384_one_conc.txt')
            elif 'cybio' in fil:
                self._compare_txt_file_content(tool_content,
                                        'sample_stock_transfer_cybio.txt')
            else:
                self._compare_csv_file_content(tool_content,
                                        'sample_stock_transfer_384_4.csv')

    def test_result_multi_conc_without_stock(self):
        self.setup_includes_stock_transfer = True
        self._continue_setup_multi_conc()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        self._check_warning_messages('Attention! There is an dilution step ' \
                    'that needs to be carried out with the CyBio before the ' \
                    'preparation plate is replicated!')
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 2)
        for fil in zip_archive.namelist():
            tool_content = zip_archive.read(fil)
            if self.tool.ANNEALING_FILE_SUFFIX[2:] in fil:
                self._compare_csv_file_content(tool_content,
                                        'buffer_384_multi_conc.csv')
            else:
                self._compare_txt_file_content_without_order(tool_content,
                                        'processing_cybio_384_multi_conc.txt')

    def test_result_multi_conc_with_stock(self):
        self.setup_includes_stock_transfer = False
        self._continue_setup_multi_conc()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        self._check_warning_messages('Attention! There is an dilution step ' \
                    'that needs to be carried out with the CyBio before the ' \
                    'preparation plate is replicated!')
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 4)
        for fil in zip_archive.namelist():
            tool_content = zip_archive.read(fil)
            if self.tool.ANNEALING_FILE_SUFFIX[2:] in fil:
                self._compare_csv_file_content(tool_content,
                                'buffer_384_multi_conc.csv')
            elif self.tool.CYBIO_FILE_SUFFIX[2:] in fil:
                self._compare_txt_file_content_without_order(tool_content,
                                'processing_cybio_384_multi_conc.txt')
            elif 'cybio' in fil:
                self._compare_txt_file_content(tool_content,
                                'sample_stock_transfer_cybio_multi_conc.txt')
            else:
                self._compare_csv_file_content(tool_content,
                                'sample_stock_transfer_384_4_multi_conc.csv')

    def test_result_empty_floating_positions(self):
        self.setup_includes_stock_transfer = True
        self._continue_setup_empty_floatings()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 2)
        for fil in zip_archive.namelist():
            tool_content = zip_archive.read(fil)
            if self.tool.ANNEALING_FILE_SUFFIX[2:] in fil:
                self._compare_csv_file_content(tool_content,
                                        'buffer_384_one_conc_empty_floats.csv')
            else:
                self._compare_txt_file_content(tool_content,
                                        'aliquot_transfer_384_one_conc.txt')

    def test_result_single_stock_rack(self):
        self.setup_includes_stock_transfer = False
        self.create_single_stock_rack = True
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 3)
        for fil in zip_archive.namelist():
            tool_content = zip_archive.read(fil)
            if self.tool.ANNEALING_FILE_SUFFIX[2:] in fil:
                self._compare_csv_file_content(tool_content,
                                        'buffer_384_one_conc.csv')
            elif self.tool.CYBIO_FILE_SUFFIX[2:] in fil:
                self._compare_txt_file_content(tool_content,
                                        'aliquot_transfer_384_one_conc.txt')
            else:
                self._compare_csv_file_content(tool_content,
                                        'sample_stock_transfer_384_1.csv')

    def test_result_optimization(self):
        self._continue_setup_opti()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 4)
        for fil in zip_archive.namelist():
            tool_content = zip_archive.read(fil)
            if self.tool.ANNEALING_FILE_SUFFIX[2:] in fil:
                self._compare_csv_file_content(tool_content,
                                        'buffer_384_opti.csv')
            elif self.tool.DILUTION_SERIES_FILE_SUFFIX[2:-7] in fil:
                self._compare_csv_file_content(tool_content,
                                        'dilution_384_opti.csv')
            elif self.tool.TRANSFER_FILE_SUFFIX[2:] in fil:
                self._compare_csv_file_content(tool_content,
                                        'aliquot_transfer_384_opti.csv')
            else:
                self._compare_csv_file_content(tool_content,
                                        'sample_stock_transfer_384_opti2.csv')

    def test_result_order(self):
        self._continue_setup_order_only()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 1)
        for fil in zip_archive.namelist():
            tool_content = zip_archive.read(fil)
            self._compare_csv_file_content(tool_content,
                                    'sample_stock_transfer_384_order.csv')

    def test_order_with_executed_stock_transfer(self):
        self._test_order_with_executed_stock_transfer()

    def test_result_aliquot_dilutions(self):
        self.setup_includes_stock_transfer = True
        self.position_data = self.position_data_aliquot_buffer
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        self._check_warning_messages('Attention! The transfer from the ' \
            'preparation plate to the aliquot plates includes a dilution. ' \
            'You have to add buffer to the aliquot plates')
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 3)
        for fil in zip_archive.namelist():
            tool_content = zip_archive.read(fil)
            if self.tool.ALIQUOT_BUFFER_FILE_SUFFIX[2:] in fil:
                self._compare_csv_file_content(tool_content,
                                'buffer_aliquot.csv')
            elif self.tool.CYBIO_FILE_SUFFIX[2:] in fil:
                self._compare_txt_file_content(tool_content,
                                'aliquot_transfer_384_with_aliquot_dil.txt')
            else:
                self._compare_csv_file_content(tool_content,
                                'buffer_384_with_aliquot_dil.csv')

    def test_result_inactivated_positions(self):
        self.setup_includes_stock_transfer = True
        self.inactivated_positions = ['A1'] # md = 11
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 2)
        for fil in zip_archive.namelist():
            tool_content = zip_archive.read(fil)
            if self.tool.ANNEALING_FILE_SUFFIX[2:] in fil:
                self._compare_csv_file_content(tool_content,
                                        'buffer_384_inactivated_position.csv')
            else:
                self._compare_txt_file_content(tool_content,
                                        'aliquot_transfer_384_one_conc.txt')

    def test_invalid_iso(self):
        self._test_invalid_iso()

    def test_invalid_preparation_layout(self):
        self._test_invalid_preparation_layout()

    def test_missing_preparation_plate(self):
        self._test_missing_preparation_plate()

    def test_invalid_aliquot_plate(self):
        self._test_invalid_aliquot_plate()

    def test_no_aliquot_plates(self):
        self._test_no_aliquot_plates()

    def test_no_sample_stock_racks(self):
        self._test_no_sample_stock_racks()

    def test_missing_worklist_series(self):
        self._test_missing_worklist_series()

    def test_incomplete_worklist_series(self):
        self._test_incomplete_worklist_series()

    def test_verification_error(self):
        self._test_verification_error()

    def test_no_verification(self):
        self._test_no_verification()

    def test_stock_transfer_error(self):
        self.setup_includes_stock_transfer = False
        self.stock_src_volume = 10 / VOLUME_CONVERSION_FACTOR
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to generate files ' \
                                     'for the sample stock transfer.')
        self._execute_stock_transfer()
        self._create_tool()
        self.assert_is_not_none(self.tool.get_result())

    def test_serial_writing_failure(self):
        self.well_dead_vol = self.well_dead_vol * 3
        self._continue_setup()
        self._test_and_expect_errors('Error during serial worklist ' \
                                     'file generation.')

    def test_failed_stock_transfer_job_generation(self):
        self._test_failed_stock_transfer_job_generation()


class IsoProcessingExecutor384TestCase(IsoProcessing384TestCase):

    def _create_tool(self):
        self.tool = IsoProcessingExecutor(iso=self.iso, user=self.executor_user)

    def _test_and_expect_errors(self, msg=None):
        IsoProcessing384TestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_executed_stock_worklists())
        self.assert_is_none(self.tool.get_working_layout())

    def _check_execution_result(self, run_setup=True):
        IsoProcessing384TestCase._check_execution_result(self, run_setup)
        tool_layout = self.tool.get_working_layout()
        self.assert_is_not_none(tool_layout)
        self.assert_equal(tool_layout, self.preparation_layout)
        stock_ews = self.tool.get_executed_stock_worklists()
        self.assert_is_not_none(stock_ews)
        if self.setup_includes_stock_transfer:
            self.assert_equal(len(stock_ews), 0)
        else:
            self.assert_equal(len(stock_ews), len(self.sample_stock_racks))
            for ew in stock_ews.values():
                self.assert_true(len(ew.executed_transfers) in \
                                 self.expected_transfers_per_stock_transfer)
                for et in ew.executed_transfers:
                    self._check_executed_transfer(et,
                                            TRANSFER_TYPES.CONTAINER_TRANSFER)

    def test_result_one_conc_without_stock(self):
        self.setup_includes_stock_transfer = True
        self._check_execution_result()

    def test_result_one_conc_with_stock(self):
        self.setup_includes_stock_transfer = False
        self.expected_transfers_per_stock_transfer = [2, 3]
        self._check_execution_result()

    def test_result_multi_conc_without_stock(self):
        self.setup_includes_stock_transfer = True
        self._continue_setup_multi_conc()
        self._check_execution_result(run_setup=False)
        self.assert_equal(len(self.tool.get_messages()), 0)

    def test_result_multi_conc_with_stock(self):
        self.setup_includes_stock_transfer = False
        self.expected_transfers_per_stock_transfer = [2, 3]
        self._continue_setup_multi_conc()
        self._check_execution_result(run_setup=False)
        self.assert_equal(len(self.tool.get_messages()), 0)

    def test_result_single_stock_rack(self):
        self.setup_includes_stock_transfer = False
        self.create_single_stock_rack = True
        self.expected_transfers_per_stock_transfer = [10]
        self._check_execution_result()

    def test_result_optimisation(self):
        self._continue_setup_opti()
        self._check_execution_result(run_setup=False)

    def test_result_order(self):
        self._continue_setup_order_only()
        self._check_execution_result(run_setup=False)

    def test_order_with_executed_stock_transfer(self):
        self._test_order_with_executed_stock_transfer()

    def test_result_empty_floats(self):
        self._continue_setup_empty_floatings()
        self._check_execution_result(run_setup=False)

    def test_result_inactivated_positions(self):
        self.inactivated_positions = ['A1']
        self.setup_includes_stock_transfer = True
        self.expected_buffer_transfers = len(self.position_data) - 3 # 2 mocks
        self._check_execution_result()

    def test_invalid_iso(self):
        self._test_invalid_iso()

    def test_invalid_user(self):
        self._test_invalid_user()

    def test_invalid_preparation_layout(self):
        self._test_invalid_preparation_layout()

    def test_missing_preparation_plate(self):
        self._test_missing_preparation_plate()

    def test_invalid_aliquot_plate(self):
        self._test_invalid_aliquot_plate()

    def test_no_aliquot_plates(self):
        self._test_no_aliquot_plates()

    def test_no_sample_stock_racks(self):
        self._test_no_sample_stock_racks()

    def test_missing_worklist_series(self):
        self._test_missing_worklist_series()

    def test_incomplete_worklist_series(self):
        self._test_incomplete_worklist_series()

    def test_verification_error(self):
        self._test_verification_error()

    def test_no_verification(self):
        self._test_no_verification()

    def test_state_detection_error(self):
        self._test_state_detection_error()

    def test_series_execution_failure(self):
        self.well_dead_vol = self.well_dead_vol * 3
        self._continue_setup()
        self._test_and_expect_errors('Error during serial transfer execution.')

    def test_failed_stock_transfer_job_generation(self):
        self._test_failed_stock_transfer_job_generation()

    def test_previous_execution(self):
        self._test_previous_execution()

    def test_unexpected_status_with_stock_transfer(self):
        self._test_unexpected_status(iso_status=ISO_STATUS.QUEUED,
                                     include_stock_transfer=False)

    def test_unexpected_status_without_stock_transfer(self):
        self._test_unexpected_status(iso_status=ISO_STATUS.PREPARED,
                                     include_stock_transfer=True)
