"""
Tests for stock transfer related tools.

AAB, Jan 2012
"""
from everest.entities.utils import get_root_aggregate
from thelma.automation.tools.iso.prep_utils import IsoControlRackLayout
from thelma.automation.tools.iso.prep_utils import IsoControlRackPosition
from thelma.automation.tools.iso.prep_utils import PrepIsoLayout
from thelma.automation.tools.iso.prep_utils import PrepIsoPosition
from thelma.automation.tools.iso.prep_utils import RequestedStockSample
from thelma.automation.tools.iso.stocktransfer \
    import IsoControlStockRackExecutor
from thelma.automation.tools.iso.stocktransfer \
    import IsoControlStockRackVerifier
from thelma.automation.tools.iso.stocktransfer \
    import IsoControlStockRackWorklistWriter
from thelma.automation.tools.iso.stocktransfer \
    import IsoControlTransferOverviewWriter
from thelma.automation.tools.iso.stocktransfer \
    import IsoSampleStockRackExecutor
from thelma.automation.tools.iso.stocktransfer \
    import IsoSampleStockRackJobCreator
from thelma.automation.tools.iso.stocktransfer \
    import IsoSampleStockRackVerifier
from thelma.automation.tools.iso.stocktransfer \
    import IsoSampleStockRackWorklistWriter
from thelma.automation.tools.iso.stockworklist \
    import SingleStockRackLayoutOptimiser
from thelma.automation.tools.iso.stockworklist \
    import StockTransferWorklistGenerator96
from thelma.automation.tools.semiconstants \
    import get_experiment_type_robot_optimisation
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.tools.semiconstants import get_384_rack_shape
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_experiment_metadata_type
from thelma.automation.tools.semiconstants import get_experiment_type_screening
from thelma.automation.tools.semiconstants import get_item_status_future
from thelma.automation.tools.semiconstants import get_item_status_managed
from thelma.automation.tools.semiconstants import get_positions_for_shape
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.stock.base import STOCK_DEAD_VOLUME
from thelma.automation.tools.stock.base import get_default_stock_concentration
from thelma.automation.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import FIXED_POSITION_TYPE
from thelma.automation.tools.utils.base import MOCK_POSITION_TYPE
from thelma.automation.tools.utils.base import TransferTarget
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.worklists.series import ContainerTransferJob
from thelma.interfaces import IJobType
from thelma.interfaces import IMoleculeDesign
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
from thelma.models.iso import IsoControlStockRack
from thelma.models.iso import IsoPreparationPlate
from thelma.models.iso import IsoSampleStockRack
from thelma.models.job import IsoJob
from thelma.models.liquidtransfer import ExecutedWorklist
from thelma.models.liquidtransfer import PlannedContainerTransfer
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.moleculetype import MOLECULE_TYPE_IDS
from thelma.models.rack import PlateSpecs
from thelma.models.rack import TubeRackSpecs
from thelma.models.racklayout import RackLayout
from thelma.models.sample import Molecule
from thelma.models.sample import Sample
from thelma.models.utils import get_user
from thelma.tests.tools.tooltestingutils import FileCreatorTestCase
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase
import zipfile


class StockTaking96TestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.log = TestingLog()
        self.iso = None
        self.iso_label = 'stock_worklist_test'
        self.stock_rack = None
        self.shape = get_96_rack_shape()
        self.user = get_user('it')
        self.status = get_item_status_future()
        self.molecule_type = get_root_aggregate(IMoleculeType).\
                             get_by_id(MOLECULE_TYPE_IDS.SIRNA)
        self.stock_concentration = get_default_stock_concentration(
                                                            self.molecule_type)
        self.preparation_layout = None
        self.preparation_plate = None
        self.iso_prep_plate = None
        self.stock_worklist = None
        self.issr = None
        # 205200 and 2025201 are siRNAs, 1056000 is a pool
        self.pool_map = {
            205200 : self._get_entity(IMoleculeDesignPool, '205200'),
            205201 : self._get_entity(IMoleculeDesignPool, '205201'),
            1056000 : self._get_entity(IMoleculeDesignPool, '1056000')}
        # key: rack position, value: (pool ID, iso conc, parent well, req_vol,
        # iso wells); estimated iso volume: 10 ul
        self.position_data = dict(A1=(205200, 10000, None, 51,
                                      ['A1', 'A2', 'A3', 'A4']),
                                  B1=(205201, 10000, None, 45, ['B1', 'B2']),
                                  B3=(205201, 5000, 'B1', 30, ['B3', 'B4']),
                                  C1=(205202, 10000, None, 36, ['C1']),
                                  C2=(205202, 5000, 'C1', 32, ['C2']),
                                  C3=(205202, 2000, 'C2', 30, ['C3']),
                                  C4=(205202, 1000, 'C3', 20, ['C4']),
                                  D1=('mock', None, None, 20, ['D1']))
        self.stock_rack_barcode = '09999911'
        self.prep_plate_barcode = '09999922'
        self.iso_volume = 10
        self.supplier = self._get_entity(IOrganization)
        self.tube_specs = TubeSpecs(label='stock_test_tube_specs',
                    max_volume=0.001500,
                    dead_volume=STOCK_DEAD_VOLUME / VOLUME_CONVERSION_FACTOR)
        self.tube_rack_specs = None
        self.well_specs = WellSpecs(label='stock_test_well_specs',
                                    max_volume=0.000300,
                                    dead_volume=0.000010,
                                    plate_specs=None)
        self.plate_specs = PlateSpecs(label='stock_test_plate_specs',
                                      shape=self.shape,
                                      well_specs=self.well_specs)
        self.src_starting_vol = 0.000050 # 50 ul
        self.inactivate_pos = None
        self.scenario = get_experiment_type_robot_optimisation()

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.log
        del self.iso
        del self.iso_label
        del self.stock_rack
        del self.shape
        del self.status
        del self.molecule_type
        del self.stock_concentration
        del self.preparation_layout
        del self.preparation_plate
        del self.iso_prep_plate
        del self.stock_worklist
        del self.issr
        del self.position_data
        del self.stock_rack_barcode
        del self.prep_plate_barcode
        del self.iso_volume
        del self.supplier
        del self.tube_specs
        del self.tube_rack_specs
        del self.well_specs
        del self.plate_specs
        del self.src_starting_vol
        del self.inactivate_pos
        del self.scenario

    def _continue_setup(self):
        self._create_prep_layout()
        self._create_stock_rack()
        self._create_preparation_plate()
        self._create_stock_worklist()
        self._create_test_iso()
        self._create_issr()
        self._create_tool()

    def _create_prep_layout(self):
        self.preparation_layout = PrepIsoLayout(shape=self.shape)
        for pos_label, data_tuple in self.position_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            pool_id = data_tuple[0]
            pool = self._get_pool(pool_id)
            prep_conc = data_tuple[1]
            parent_well = data_tuple[2]
            if not parent_well is None:
                parent_well = get_rack_position_from_label(parent_well)
            req_volume = data_tuple[3]
            target_labels = data_tuple[4]
            transfer_targets = []
            for target_label in target_labels:
                target_pos = get_rack_position_from_label(target_label)
                tt = TransferTarget(rack_position=target_pos,
                                    transfer_volume=self.iso_volume)
                transfer_targets.append(tt)
            pos_type = FIXED_POSITION_TYPE
            if pool_id == MOCK_POSITION_TYPE:
                pos_type = MOCK_POSITION_TYPE
                tube_barcode = None
            else:
                tube_barcode = '%08i' % (pool_id)
            prep_pos = PrepIsoPosition(rack_position=rack_pos,
                                position_type=pos_type,
                                prep_concentration=prep_conc,
                                required_volume=req_volume,
                                parent_well=parent_well,
                                transfer_targets=transfer_targets,
                                molecule_design_pool=pool,
                                stock_tube_barcode=tube_barcode)
            self.preparation_layout.add_position(prep_pos)
            if pos_label == self.inactivate_pos: prep_pos.inactivate()

    def _create_stock_rack(self, ignore_pos=[]): #pylint: disable=W0102
        self.tube_rack_specs = TubeRackSpecs(label='stock_test_tube_rack_specs',
                                             shape=self.shape,
                                             tube_specs=[self.tube_specs])
        self.stock_rack = self.tube_rack_specs.create_rack(label='stock_rack',
                                                           status=self.status)
        self.stock_rack.barcode = self.stock_rack_barcode
        starting_wells = self.preparation_layout.get_starting_wells()
        for rack_pos, prep_pos in starting_wells.iteritems():
            if prep_pos.is_inactivated: continue
            if rack_pos in ignore_pos: continue
            barcode = prep_pos.stock_tube_barcode
            tube = self.tube_specs.create_tube(item_status=self.status,
                                               barcode=barcode, location=None)
            ContainerLocation(container=tube, rack=self.stock_rack,
                              position=rack_pos)
            self.stock_rack.containers.append(tube)
            sample = Sample(self.src_starting_vol, tube)
            if prep_pos.is_mock: continue
            pool = prep_pos.molecule_design_pool
            conc = self.stock_concentration / (len(pool.molecule_designs)
                                            * CONCENTRATION_CONVERSION_FACTOR)
            for md in pool.molecule_designs:
                mol = Molecule(molecule_design=md, supplier=self.supplier)
                sample.make_sample_molecule(mol, conc)

    def _create_preparation_plate(self):
        self.preparation_plate = self.plate_specs.create_rack(
                                        label='prep_plate', status=self.status)
        self.preparation_plate.barcode = self.prep_plate_barcode
        self.iso_prep_plate = IsoPreparationPlate(iso=self.iso,
                                                  plate=self.preparation_plate)

    def _create_stock_worklist(self):
        label = '%s%s' % (self.iso_label,
                          StockTransferWorklistGenerator96.WORKLIST_SUFFIX)
        self.stock_worklist = PlannedWorklist(label=label)
        for rack_pos, prep_pos in self.preparation_layout.iterpositions():
            if prep_pos.is_mock or prep_pos.is_inactivated: continue
            if not prep_pos.parent_well is None: continue
            take_out_volume = prep_pos.get_stock_takeout_volume()
            volume = take_out_volume / VOLUME_CONVERSION_FACTOR
            pct = PlannedContainerTransfer(volume=volume,
                        source_position=rack_pos, target_position=rack_pos)
            self.stock_worklist.planned_transfers.append(pct)

    def _create_test_iso(self):
        iso_request = self._create_iso_request(
                                iso_layout=RackLayout(shape=self.shape),
                                requester=self.user)
        self.iso = Iso(label='stock_test_iso',
                       rack_layout=self.preparation_layout.create_rack_layout(),
                       iso_preparation_plate=self.iso_prep_plate,
                       iso_request=iso_request)
        ExperimentMetadata(label='test_em',
                           subproject=self._get_entity(ISubproject),
                           iso_request=iso_request,
                           number_replicates=1,
                           experiment_metadata_type=self.scenario,
                           ticket_number=1)
        IsoJob(label='test_iso_job',
               job_type=self._get_entity(IJobType, 'iso-batch'),
               isos=[self.iso])

    def _create_issr(self):
        self.issr = IsoSampleStockRack(iso=self.iso,
                            rack=self.stock_rack, sector_index=0,
                            planned_worklist=self.stock_worklist)

    def _test_invalid_iso(self):
        self._continue_setup()
        self.iso = self.iso.iso_request
        self._test_and_expect_errors('The ISO must be a Iso object')

    def _test_invalid_preparation_layout(self):
        self._continue_setup()
        self.iso.rack_layout = None
        self._test_and_expect_errors('Error when trying to convert ' \
                                     'preparation layout.')

    def _test_no_sample_stock_racks(self):
        self._continue_setup()
        self.iso.iso_sample_stock_racks = []
        self._test_and_expect_errors('There are no ISO sample stock racks ' \
                                     'for this ISO!')

    def _test_no_preparation_plate(self):
        self._continue_setup()
        self.iso.iso_preparation_plate = None
        self._test_and_expect_errors('There is no preparation plate for ' \
                                     'this ISO!')

    def _test_verifier_error(self):
        self.shape = get_384_rack_shape()
        self._continue_setup()
        self._test_and_expect_errors('Error in the verifier!')

    def _test_no_verification(self):
        self._continue_setup()
        a1_pos = get_rack_position_from_label('A1')
        self.preparation_layout.del_position(a1_pos)
        self.iso.rack_layout = self.preparation_layout.create_rack_layout()
        self._test_and_expect_errors('The stock racks are not ' \
                                     'compatible with the ISO!')


class IsoSampleStockRackVerifier96TestCase(StockTaking96TestCase):

    def set_up(self):
        StockTaking96TestCase.set_up(self)
        self.sample_stock_racks = None

    def tear_down(self):
        StockTaking96TestCase.tear_down(self)
        del self.sample_stock_racks

    def _create_tool(self):
        self.tool = IsoSampleStockRackVerifier(log=self.log,
                            preparation_layout=self.preparation_layout,
                            sample_stock_racks=self.sample_stock_racks)

    def _continue_setup(self, ignore_pos=[]): #pylint: disable=W0221, W0102
        self._create_prep_layout()
        self._create_stock_rack(ignore_pos=ignore_pos)
        self._create_preparation_plate()
        self._create_stock_worklist()
        self._create_test_iso()
        self._create_issr()
        self.sample_stock_racks = {0 : self.issr}
        self._create_tool()

    def test_result(self):
        self._continue_setup()
        compatible = self.tool.get_result()
        self.assert_is_not_none(compatible)
        self.assert_true(compatible)

    def test_result_inactivated_position(self):
        self.inactivate_pos = 'A1'
        self._continue_setup()
        compatible = self.tool.get_result()
        self.assert_is_not_none(compatible)
        self.assert_true(compatible)

    def test_invalid_prep_layout(self):
        self._continue_setup()
        self.preparation_layout = self.preparation_layout.create_rack_layout()
        self._test_and_expect_errors('The preparation layout must be a ' \
                                     'PrepIsoLayout object')

    def test_invalid_sample_stock_racks(self):
        self._continue_setup()
        self.sample_stock_racks = self.issr
        self._test_and_expect_errors('The sample stock rack map must be a ' \
                                     'dict object')
        self.sample_stock_racks = dict(A=self.issr)
        self._test_and_expect_errors('The sector index must be a int object')
        self.sample_stock_racks = {0 : 3}
        self._test_and_expect_errors('The sample stock rack must be a ' \
                                     'IsoSampleStockRack object')

    def test_no_tube_rack(self):
        self._continue_setup()
        self.issr.rack = None
        self._test_and_expect_errors('The stock rack for sector 1 is missing!')

    def test_unsupported_rack_shape(self):
        self.shape = get_384_rack_shape()
        self._continue_setup()
        self._test_and_expect_errors('Unsupported rack shape "16x24"')

    def test_additional_tube(self):
        self._continue_setup()
        c1_pos = get_rack_position_from_label('C1')
        self.preparation_layout.del_position(c1_pos)
        b1_pos = get_rack_position_from_label('B1')
        self.preparation_layout.del_position(b1_pos)
        compatible = self.tool.get_result()
        self.assert_is_not_none(compatible)
        self.assert_false(compatible)
        self._check_error_messages('There are molecule designs for ' \
                    'positions that should be empty in the stock tube rack')

    def test_missing_tube(self):
        c1_pos = get_rack_position_from_label('C1')
        self._continue_setup(ignore_pos=[c1_pos])
        compatible = self.tool.get_result()
        self.assert_is_not_none(compatible)
        self.assert_false(compatible)
        self._check_error_messages('Some molecule designs expected for stock ' \
                                   'tube rack 09999911 (sector 1) are missing')

    def test_mismatching_tube(self):
        self._continue_setup()
        c1_pos = get_rack_position_from_label('C1')
        pp = self.preparation_layout.get_working_position(c1_pos)
        pp.molecule_design_pool = self._get_pool(205205)
        compatible = self.tool.get_result()
        self.assert_is_not_none(compatible)
        self.assert_false(compatible)
        self._check_error_messages('Some molecule designs in stock tube ' \
                    'rack 09999911 (sector 1) do not match the expected ' \
                    'molecule design:')

    def test_not_covered_by_stock_rack(self):
        self._continue_setup()
        self.position_data['E1'] = (205205, 10000, None, 50, ['E1'])
        self.preparation_layout = PrepIsoLayout(get_96_rack_shape())
        self._create_prep_layout()
        self._create_tool()
        compatible = self.tool.get_result()
        self.assert_is_not_none(compatible)
        self.assert_false(compatible)
        self._check_error_messages('The following preparation positions are ' \
                                   'not covered by a stock rack')


class IsoSampleStockRackExecutor96TestCase(StockTaking96TestCase):

    def _create_tool(self):
        self.tool = IsoSampleStockRackExecutor(iso=self.iso,
                            user=self.user)

    def _test_and_expect_errors(self, msg=None):
        StockTaking96TestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_executed_stock_worklists())
        self.assert_is_none(self.tool.get_working_layout())

    def __check_result(self, number_transfers=3):
        updated_iso = self.tool.get_result()
        self.assert_is_not_none(updated_iso)
        self.assert_equal(updated_iso.status, ISO_STATUS.IN_PROGRESS)
        for issr in updated_iso.iso_sample_stock_racks:
            worklist = issr.planned_worklist
            self.assert_equal(len(worklist.executed_worklists), 1)
            for ew in worklist.executed_worklists:
                self.__check_worklist(ew, number_transfers)
        self.__check_stock_rack(updated_iso)
        self.__check_preparation_plate(updated_iso)
        executed_worklists = self.tool.get_executed_stock_worklists()
        self.assert_equal(len(executed_worklists), 1)
        for ew in executed_worklists.values():
            self.__check_worklist(ew, number_transfers)
        pl = self.tool.get_working_layout()
        self.assert_equal(pl, self.preparation_layout)

    def __check_worklist(self, ew, number_transfers):
        self.assert_equal(len(ew.executed_transfers), number_transfers)
        for et in ew.executed_transfers:
            self.assert_is_not_none(et.timestamp)
            self.assert_equal(et.user, self.user)

    def __check_stock_rack(self, updated_iso):
        stock_rack = updated_iso.iso_sample_stock_racks[0].rack
        for container in stock_rack.containers:
            rack_pos = container.location.position
            prep_pos = self.preparation_layout.get_working_position(rack_pos)
            take_out_volume = prep_pos.get_stock_takeout_volume()
            expected_volume = self.src_starting_vol * VOLUME_CONVERSION_FACTOR \
                              - take_out_volume
            sample_volume = container.sample.volume * VOLUME_CONVERSION_FACTOR
            self.assert_equal(sample_volume, expected_volume)

    def __check_preparation_plate(self, updated_iso):
        self.assert_equal(updated_iso.preparation_plate.status.name,
                          ITEM_STATUS_NAMES.MANAGED)
        for container in updated_iso.preparation_plate.containers:
            rack_pos = container.location.position
            prep_pos = self.preparation_layout.get_working_position(rack_pos)
            sample = container.sample
            if prep_pos is None:
                self.assert_is_none(sample)
                continue
            if not prep_pos.parent_well is None or prep_pos.is_mock \
                                                or prep_pos.is_inactivated:
                self.assert_is_none(sample)
                continue
            expected_volume = prep_pos.get_stock_takeout_volume()
            self._compare_sample_volume(sample, expected_volume)
            pool = prep_pos.molecule_design_pool
            self._compare_sample_and_pool(sample, pool)

    def test_result(self):
        self._continue_setup()
        self.__check_result()

    def test_result_inactivated_position(self):
        self.inactivate_pos = 'A1'
        self._continue_setup()
        self.__check_result(number_transfers=2)

    def test_invalid_iso(self):
        self._test_invalid_iso()

    def test_invalid_user(self):
        self._continue_setup()
        self.user = 'test'
        self._test_and_expect_errors('The user must be a User object')

    def test_invalid_preparation_layout(self):
        self._test_invalid_preparation_layout()

    def test_no_sample_stock_racks(self):
        self._test_no_sample_stock_racks()

    def test_no_preparation_plate(self):
        self._test_no_preparation_plate()

    def test_verifier_error(self):
        self._test_verifier_error()

    def test_no_verification(self):
        self._test_no_verification()

    def test_execution_failure(self):
        self.src_starting_vol = 4 / VOLUME_CONVERSION_FACTOR
        self._continue_setup()
        self._test_and_expect_errors('Error during serial worklist execution')

    def test_previous_execution(self):
        self._continue_setup()
        ExecutedWorklist(planned_worklist=self.stock_worklist)
        self._test_and_expect_errors('The stock transfer has already been ' \
                                     'executed!')

    def test_unexpected_status(self):
        self._continue_setup()
        self.iso.status = ISO_STATUS.IN_PROGRESS
        self._test_and_expect_errors('Unexpected ISO status: "in_progress"')


class IsoSampleStockRackWriter96TestCase(StockTaking96TestCase,
                                         FileCreatorTestCase):

    def set_up(self):
        FileCreatorTestCase.set_up(self)
        StockTaking96TestCase.set_up(self)
        self.WL_PATH = 'thelma:tests/tools/iso/csv_files/'

    def tear_down(self):
        StockTaking96TestCase.tear_down(self)
        del self.WL_PATH

    def _create_tool(self):
        self.tool = IsoSampleStockRackWorklistWriter(iso=self.iso, log=self.log)

    def __check_result(self, file_name):
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 1)
        tool_content = None
        for fil in zip_archive.namelist(): tool_content = zip_archive.read(fil)
        self._compare_csv_file_content(tool_content, file_name)
        zip_map = self.tool.get_zip_map()
        self.assert_equal(len(zip_map), 1)
        stream = zip_map.values()[0]
        self._compare_csv_file_stream(stream, file_name)

    def test_result(self):
        self._continue_setup()
        self.__check_result('stock_transfer_96.csv')

    def test_result_inactivated_position(self):
        self.inactivate_pos = 'A1'
        self._continue_setup()
        self.__check_result('stock_transfer_96_inactivated_pos.csv')

    def test_invalid_iso(self):
        self._test_invalid_iso()

    def test_invalid_preparation_layout(self):
        self._test_invalid_preparation_layout()

    def test_no_sample_stock_racks(self):
        self._test_no_sample_stock_racks()

    def test_no_preparation_plate(self):
        self._test_no_preparation_plate()

    def test_no_verification(self):
        self._test_no_verification()

    def test_verifier_error(self):
        self._test_verifier_error()

    def test_series_writing_failure(self):
        self.src_starting_vol = 4 / VOLUME_CONVERSION_FACTOR
        self._continue_setup()
        self._test_and_expect_errors('Error during serial worklist ' \
                                     'file generation.')


class StockTaking384TestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.preparation_layout = PrepIsoLayout(shape=get_384_rack_shape())
        self.iso_label = 'stock_taking_test'
        self.iso = None
        self.stock_concentration = 50000
        self.log = TestingLog()
        self.execute_control_transfer = True
        # data tuple: molecule design, iso conc, parent well, req vol, pos type
        self.position_data = dict(
                # first quadrant
                A1=[205200, 10000, None, 30, 'fixed'],
                A2=[205201, 10000, None, 30, 'fixed'],
                B1=[205203, 10000, None, 30, 'floating'],
                B2=[205204, 10000, None, 30, 'floating'],
                # second quadrant
                A3=[205205, 10000, None, 30, 'floating'],
                A4=[205206, 10000, None, 30, 'floating'],
                B3=[205207, 10000, None, 30, 'floating'],
                B4=[205208, 10000, None, 30, 'floating'],
                # third quadrant
                C1=[205209, 10000, None, 30, 'floating'],
                C2=[205210, 10000, None, 30, 'floating'],
                D1=[205212, 10000, None, 30, 'floating'],
                D2=[205214, 10000, None, 30, 'floating'],
                # fourth quadrant
                C3=['mock', None, None, 30, 'mock'],
                C4=['mock', None, None, 30, 'mock'],
                D3=[205200, 10000, None, 30, 'fixed'],
                D4=[205201, 10000, None, 30, 'fixed'])
        self.sector_data = {
                0 : ['A1', 'A3', 'C1', 'C3'], 1 : ['A2', 'A4', 'C2', 'C4'],
                2 : ['B1', 'B3', 'D1', 'D3'], 3 : ['B2', 'B4', 'D2', 'D4']}
        self.source_positions = dict(A1=['A1', 'A2', 'B1', 'B2'],
                                     A2=['A3', 'A4', 'B3', 'B4'],
                                     B1=['C1', 'C2', 'D1', 'D2'],
                                     B2=['C3', 'C4', 'D3', 'D4'])
        self.iso_volume = 10
        self.take_out_volume = 6
        self.floating_pools = [205203, 205204, 205205, 205206, 205207, 205208,
                                205209, 205210, 205212, 205214]
        self.control_pools = [205200, 205201]
        #: other setup data
        self.user = get_user('it')
        self.tube_specs = TubeSpecs(label='stock_test_tube_specs',
                    max_volume=0.001500,
                    dead_volume=STOCK_DEAD_VOLUME / VOLUME_CONVERSION_FACTOR)
        self.tube_rack_shape = get_96_rack_shape()
        self.tube_rack_specs = None
        self.src_starting_volume = 50 / VOLUME_CONVERSION_FACTOR
        self.well_specs = WellSpecs(label='stock_test_well_specs',
                                    max_volume=0.000300,
                                    dead_volume=0.000010,
                                    plate_specs=None)
        self.plate_specs = PlateSpecs(label='stock_test_plate_specs',
                                      shape=get_384_rack_shape(),
                                      well_specs=self.well_specs)
        self.prep_plate_barcode = '09999922'
        self.stock_racks = dict()
        self.status = get_item_status_managed()
        self.prep_status = get_item_status_future()
        self.iso_prep_plate = None
        self.preparation_plate = None
        self.worklists = dict()
        self.inactivated_pos = None
        self.experiment_type_id = EXPERIMENT_SCENARIOS.SCREENING

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.preparation_layout
        del self.iso_label
        del self.iso
        del self.stock_concentration
        del self.log
        del self.execute_control_transfer
        del self.position_data
        del self.sector_data
        del self.source_positions
        del self.iso_volume
        del self.take_out_volume
        del self.floating_pools
        del self.control_pools
        del self.tube_specs
        del self.tube_rack_shape
        del self.tube_rack_specs
        del self.src_starting_volume
        del self.well_specs
        del self.plate_specs
        del self.prep_plate_barcode
        del self.stock_racks
        del self.status
        del self.prep_status
        del self.iso_prep_plate
        del self.preparation_plate
        del self.worklists
        del self.inactivated_pos
        del self.experiment_type_id

    def _continue_setup(self, single_stock_rack=False):
        single_stock_rack = self._set_scenario_specific_values(
                                                            single_stock_rack)
        self._create_pool_map()
        self._create_preparation_layout()
        self._create_preparation_plate()
        if single_stock_rack:
            self._create_single_stock_rack()
        else:
            self._create_stock_racks_and_worklists()
        self._create_test_iso()
        self._create_control_stock_rack()
        self._create_issrs()
        self._create_tool()

    def _set_scenario_specific_values(self, single_stock_rack):
        if self.experiment_type_id == EXPERIMENT_SCENARIOS.OPTIMISATION:
            self.__set_opti_values()
            single_stock_rack = True
        elif self.experiment_type_id == EXPERIMENT_SCENARIOS.ORDER_ONLY:
            self.__set_order_values()
            single_stock_rack = True
        return single_stock_rack

    def __set_opti_values(self):
        del self.position_data['D3']
        del self.position_data['D4']
        self.floating_pools = self.floating_pools + self.control_pools

    def __set_order_values(self):
        # data tuple: molecule design, iso conc, parent well, req vol, pos type
        self.position_data = dict(
                        B2=[205201, 50000, None, 1, 'fixed'],
                        B4=[330001, 10000, None, 1, 'fixed'],
                        B6=[333803, 5000000, None, 1, 'fixed'],
                        B8=[1056000, 10000, None, 1, 'fixed'],
                        B10=[180202, 50000, None, 1, 'fixed'])
        self.control_pools = [205201, 330001, 333803, 1056000, 180202]
        self.floating_pools = self.control_pools
        self.take_out_volume = 1

    def _continue_setup_inactivated_position(self):
        self.inactivated_pos = 'B1'
        self.floating_pools.remove(205203)
        self._continue_setup()

    def _create_pool_map(self):
        all_pools = set(self.floating_pools + self.control_pools)
        for pool_id in all_pools:
            self._get_pool(pool_id)

    def _create_preparation_layout(self):
        for pos_label, pos_data in self.position_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            tt = TransferTarget(rack_position=rack_pos,
                                transfer_volume=self.iso_volume)
            parent_well = pos_data[2]
            if not parent_well is None:
                parent_well = get_rack_position_from_label(parent_well)
            tube_barcode = None
            if not pos_data[4] == MOCK_POSITION_TYPE:
                tube_barcode = '%04i' % (pos_data[0])
            pool = self._get_pool(pos_data[0])
            pp = PrepIsoPosition(rack_position=rack_pos,
                                 molecule_design_pool=pool,
                                 position_type=pos_data[4],
                                 required_volume=pos_data[3],
                                 transfer_targets=[tt],
                                 prep_concentration=pos_data[1],
                                 parent_well=parent_well,
                                 stock_rack_barcode=str(pos_data[0]),
                                 stock_tube_barcode=tube_barcode)
            self.preparation_layout.add_position(pp)
            if pos_label == self.inactivated_pos: pp.inactivate()

    def _create_preparation_plate(self):
        self.preparation_plate = self.plate_specs.create_rack(
                        label='stock_test_prep_plate', status=self.prep_status)
        self.preparation_plate.barcode = self.prep_plate_barcode

    def _create_stock_racks_and_worklists(self):
        self.tube_rack_specs = TubeRackSpecs(label='stock_test_tube_rack_specs',
                                             shape=self.tube_rack_shape,
                                             tube_specs=[self.tube_specs])
        for sector_index in self.sector_data.keys():
            worklist = PlannedWorklist(label=('Q%i' % (sector_index + 1)))
            barcode = '0999991%i' % (sector_index + 1)
            tube_rack = self.tube_rack_specs.create_rack(status=self.status,
                                            label='Q%i' % (sector_index + 1))
            tube_rack.barcode = barcode
            for src_label, target_labels in self.source_positions.iteritems():
                trg_label = target_labels[sector_index]
                src_pos = get_rack_position_from_label(src_label)
                trg_pos = get_rack_position_from_label(trg_label)
                prep_pos = self.preparation_layout.get_working_position(trg_pos)
                if prep_pos.is_inactivated: continue
                pool_id = prep_pos.molecule_design_pool_id
                if not pool_id in self.floating_pools: continue
                pool = prep_pos.molecule_design_pool
                tube_barcode = prep_pos.stock_tube_barcode
                tube = self.tube_specs.create_tube(item_status=self.status,
                        barcode=tube_barcode, location=None)
                ContainerLocation(container=tube, rack=tube_rack,
                                  position=src_pos)
                tube_rack.containers.append(tube)
                sample = Sample(self.src_starting_volume, tube)
                conc = self.stock_concentration \
                                         / (len(pool.molecule_designs) \
                                           * CONCENTRATION_CONVERSION_FACTOR)
                for md in pool.molecule_designs:
                    mol = Molecule(molecule_design=md, supplier=None)
                    sample.make_sample_molecule(mol, conc)
                volume = self.take_out_volume / VOLUME_CONVERSION_FACTOR
                pct = PlannedContainerTransfer(volume=volume,
                            source_position=src_pos, target_position=trg_pos)
                worklist.planned_transfers.append(pct)

            self.stock_racks[sector_index] = tube_rack
            self.worklists[sector_index] = worklist

    def _create_single_stock_rack(self):
        self.tube_rack_specs = TubeRackSpecs(label='stock_test_tube_rack_specs',
                                             shape=self.tube_rack_shape,
                                             tube_specs=[self.tube_specs])
        sector_index = 0
        barcode = '0999991%i' % (sector_index + 1)
        tube_rack = self.tube_rack_specs.create_rack(status=self.status,
                                        label='Q%i' % (sector_index + 1))
        tube_rack.barcode = barcode
        worklist = PlannedWorklist(label='single_biomek')
        for rack_pos, prep_pos in self.preparation_layout.iterpositions():
            pool = prep_pos.molecule_design_pool
            pool_id = prep_pos.molecule_design_pool_id
            if prep_pos.is_inactivated: continue
            if not pool_id in self.floating_pools: continue
            tube_barcode = prep_pos.stock_tube_barcode
            tube = self.tube_specs.create_tube(item_status=self.status,
                    barcode=tube_barcode, location=None)
            ContainerLocation(container=tube, rack=tube_rack,
                              position=rack_pos)
            tube_rack.containers.append(tube)
            sample = Sample(self.src_starting_volume, tube)
            conc = self.stock_concentration \
                                         / (len(pool.molecule_designs) \
                                         * CONCENTRATION_CONVERSION_FACTOR)
            for md in pool.molecule_designs:
                mol = Molecule(molecule_design=md, supplier=None)
                sample.make_sample_molecule(mol, conc)
            volume = self.take_out_volume / VOLUME_CONVERSION_FACTOR
            pct = PlannedContainerTransfer(volume=volume,
                        source_position=rack_pos, target_position=rack_pos)
            worklist.planned_transfers.append(pct)
        self.stock_racks[0] = tube_rack
        self.worklists[0] = worklist

    def _create_test_iso(self):
        iso_request = self._create_iso_request(requester=self.user,
                            iso_layout=RackLayout(shape=get_384_rack_shape()))
        self.iso = Iso(label='stock_test_iso',
                       rack_layout=self.preparation_layout.create_rack_layout(),
                       iso_request=iso_request)
        self.iso_prep_plate = IsoPreparationPlate(iso=self.iso,
                                    plate=self.preparation_plate)

    def _create_control_stock_rack(self):
        em_type = get_experiment_metadata_type(self.experiment_type_id)
        ExperimentMetadata(label='test_em', iso_request=self.iso.iso_request,
                           number_replicates=1,
                           subproject=self._get_entity(ISubproject),
                           experiment_metadata_type=em_type)
        iso_job = IsoJob(label='test_iso_job', isos=[self.iso],
                         job_type=self._get_entity(IJobType, 'iso-batch'))
        control_rack = self.tube_rack_specs.create_rack(status=self.status,
                                                label='control_stock_rack')
        icsr = IsoControlStockRack(iso_job=iso_job, rack=control_rack,
                            rack_layout=RackLayout(shape=get_96_rack_shape()),
                            planned_worklist=PlannedWorklist(
                                            label='control_stock_transfer'))
        if self.execute_control_transfer:
            ExecutedWorklist(planned_worklist=icsr.planned_worklist)

    def _create_issrs(self):
        for sector_index, tube_rack in self.stock_racks.iteritems():
            worklist = self.worklists[sector_index]
            IsoSampleStockRack(iso=self.iso, rack=tube_rack,
                        sector_index=sector_index, planned_worklist=worklist)
        if len(self.stock_racks) > 1:
            self.iso.status = ISO_STATUS.PREPARED

    def _test_invalid_iso(self):
        self._continue_setup()
        self.iso = self.iso.iso_request
        self._test_and_expect_errors('The ISO must be a Iso object')

    def _test_invalid_preparation_layout(self):
        self._continue_setup()
        self.iso.rack_layout = RackLayout(shape=get_384_rack_shape())
        self._test_and_expect_errors('Error when trying to convert ' \
                                     'preparation layout.')

    def _test_missing_stock_racks(self):
        self._create_pool_map()
        self._create_preparation_layout()
        self._create_preparation_plate()
        self._create_stock_racks_and_worklists()
        self._create_test_iso()
        self._create_tool()
        self._test_and_expect_errors('There are no ISO sample stock racks ' \
                                     'for this ISO!')

    def _test_missing_preparation_plate(self):
        self._continue_setup()
        self.iso.iso_preparation_plate = None
        self._test_and_expect_errors('There is no preparation plate for ' \
                                     'this ISO!')

    def _test_verifier_error(self):
        self.tube_rack_shape = get_384_rack_shape()
        self._continue_setup()
        self._test_and_expect_errors('Error in the verifier!')

    def _test_no_verification(self):
        self._continue_setup()
        b1_pos = get_rack_position_from_label('B1')
        self.preparation_layout.del_position(b1_pos)
        self.iso.rack_layout = self.preparation_layout.create_rack_layout()
        self._test_and_expect_errors('The stock racks are not compatible ' \
                                     'with the ISO!')

    def _test_failed_transfer_job_generation(self):
        self.execute_control_transfer = False
        self._continue_setup()
        self._test_and_expect_errors('Error when trying to create ' \
                                     'transfer jobs.')




class SingleStockRackLayoutOptimiserTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.log = TestingLog()
        self.requested_stock_samples = []
        # molecule design pool id - target pos label, expected src pos label
        self.position_data = {205201 : ['B2', 'A1'], 205202 : ['C2', 'C1'],
                              205203 : ['E2', 'B1'], 205204 : ['F2', 'D1'],
                              205206 : ['B3', 'G1'], 205205 : ['C3', 'E1'],
                              205207 : ['E3', 'H1'], 205208 : ['F3', 'F1']}

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.log
        del self.requested_stock_samples
        del self.position_data

    def _create_tool(self):
        self.tool = SingleStockRackLayoutOptimiser(log=self.log,
                        requested_stock_samples=self.requested_stock_samples)

    def __continue_setup(self):
        self.__create_requested_stock_samples()
        self._create_tool()

    def __create_requested_stock_samples(self):
        for pool_id, pos_data in self.position_data.iteritems():
            pool = self._get_pool(pool_id)
            trg_pos = get_rack_position_from_label(pos_data[0])
            rss = RequestedStockSample(pool=pool,
                    stock_concentration=50000, take_out_volume=1,
                    stock_tube_barcode='1%04i' % (pool_id),
                    stock_rack_barcode='09999999', target_position=trg_pos)
            self.requested_stock_samples.append(rss)

    def test_result(self):
        self.__continue_setup()
        optimised_layout = self.tool.get_result()
        self.assert_is_not_none(optimised_layout)
        self.assert_equal(len(optimised_layout), len(self.position_data))
        for rack_pos, prep_pos in optimised_layout.iterpositions():
            pool_id = prep_pos.molecule_design_pool_id
            exp_pos = self.position_data[pool_id][1]
            self.assert_equal(rack_pos.label, exp_pos)

    def test_invalid_requested_stock_samples(self):
        self.requested_stock_samples = []
        self._test_and_expect_errors('There are no requested stock samples ' \
                                     'in the list')
        self.requested_stock_samples = [1]
        self._test_and_expect_errors('The requested stock sample must be a ' \
                                     'RequestedStockSample object')
        self.requested_stock_samples = dict()
        self._test_and_expect_errors('The requested stock sample list must be ' \
                                     'a list')

    def test_no_one_to_one_support(self):
        self.position_data = dict()
        pool_id = 205201
        for rack_pos in get_positions_for_shape(get_384_rack_shape()):
            if not len(self.position_data) == 0:
                pool_id = max(self.position_data.keys()) + 1
            pool = None
            while pool is None:
                try:
                    pool = self._get_pool(pool_id)
                except ValueError:
                    pool_id += 1
                else:
                    break
            self.position_data[pool_id] = [rack_pos.label,
                                           rack_pos.label]
            if len(self.position_data) > 100: break
        self.__continue_setup()
        self._test_and_expect_errors('One-to-one sorting is not supported. ' \
                        'There must not be more than 96 molecule design pools')


class IsoSampleStockRackVerifier384TestCase(StockTaking384TestCase):

    def set_up(self):
        StockTaking384TestCase.set_up(self)
        self.sample_stock_racks = dict()

    def tear_down(self):
        StockTaking384TestCase.tear_down(self)
        del self.sample_stock_racks

    def _create_tool(self):
        self.tool = IsoSampleStockRackVerifier(log=self.log,
                            preparation_layout=self.preparation_layout,
                            sample_stock_racks=self.sample_stock_racks)

    def _continue_setup(self, single_stock_rack=False):
        single_stock_rack = self._set_scenario_specific_values(
                                                            single_stock_rack)
        self._create_pool_map()
        self._create_preparation_layout()
        self._create_preparation_plate()
        if single_stock_rack:
            self._create_single_stock_rack()
        else:
            self._create_stock_racks_and_worklists()
        self._create_test_iso()
        self._create_issrs()
        for issr in self.iso.iso_sample_stock_racks:
            self.sample_stock_racks[issr.sector_index] = issr
        self._create_tool()

    def __test_and_expect_success(self, single_stock_rack=False,
                                  inactivate_position=False):
        if inactivate_position:
            self._continue_setup_inactivated_position()
        else:
            self._continue_setup(single_stock_rack)
        compatible = self.tool.get_result()
        self.assert_is_not_none(compatible)
        self.assert_true(compatible)

    def test_result_4_racks(self):
        self.__test_and_expect_success()

    def test_result_1_rack(self):
        self.__test_and_expect_success(single_stock_rack=True)

    def test_result_opti(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.OPTIMISATION
        self.__test_and_expect_success()

    def test_result_order(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.ORDER_ONLY
        self.__test_and_expect_success()

    def test_result_inactivated_position(self):
        self.__test_and_expect_success(inactivate_position=True)

    def test_invalid_prep_layout(self):
        self._continue_setup()
        self.preparation_layout = self.preparation_layout.create_rack_layout()
        self._test_and_expect_errors('The preparation layout must be a ' \
                                     'PrepIsoLayout object')

    def test_invalid_sample_stock_racks(self):
        self._continue_setup()
        issr = self.iso.iso_sample_stock_racks[0]
        self.sample_stock_racks = issr
        self._test_and_expect_errors('The sample stock rack map must be a ' \
                                     'dict object')
        self.sample_stock_racks = dict(A=issr)
        self._test_and_expect_errors('The sector index must be a int object')
        self.sample_stock_racks = {0 : 3}
        self._test_and_expect_errors('The sample stock rack must be a ' \
                                     'IsoSampleStockRack object')

    def test_no_tube_rack(self):
        self._continue_setup()
        for issr in self.iso.iso_sample_stock_racks:
            if issr.sector_index == 1: issr.rack = None
        self._test_and_expect_errors('The stock rack for sector 2 is missing!')

    def test_unsupported_rack_shape(self):
        self.tube_rack_shape = get_384_rack_shape()
        self._continue_setup()
        self._test_and_expect_errors('Unsupported rack shape "16x24" for ' \
                                     'stock tube rack.')

    def test_additional_tube(self):
        self._continue_setup()
        b1_pos = get_rack_position_from_label('B1')
        self.preparation_layout.del_position(b1_pos)
        compatible = self.tool.get_result()
        self.assert_is_not_none(compatible)
        self.assert_false(compatible)
        self._check_error_messages('There are molecule designs for positions ' \
                                'that should be empty in the stock tube rack')

    def test_missing_tube(self):
        self._continue_setup()
        tube_rack = self.sample_stock_racks[0].rack
        del tube_rack.containers[0] # tube_rack.remove_tube does not work
        # because the container locations to not properly store tubes that have
        # not been to a session before
        compatible = self.tool.get_result()
        self.assert_is_not_none(compatible)
        self.assert_false(compatible)
        self._check_error_messages('Some molecule designs expected for stock ' \
                                   'tube rack 09999911 (sector 1) are missing')

    def test_mismatching_tube(self):
        self._continue_setup()
        md99 = self._get_entity(IMoleculeDesign, '99')
        stock_rack = self.iso.iso_sample_stock_racks[0]
        for container in stock_rack.rack.containers:
            sm = container.sample.sample_molecules[0]
            sm.molecule.molecule_design = md99
            break
        compatible = self.tool.get_result()
        self.assert_is_not_none(compatible)
        self.assert_false(compatible)
        self._check_error_messages('Some molecule designs in stock tube rack ' \
            '09999911 (sector 1) do not match the expected molecule design:')

    def test_not_covered_by_stock_rack(self):
        self._continue_setup()
        self.position_data['E1'] = (205210, 10000, None, 30, 'fixed')
        self.preparation_layout = PrepIsoLayout(get_384_rack_shape())
        self._create_preparation_layout()
        self._create_tool()
        compatible = self.tool.get_result()
        self.assert_is_not_none(compatible)
        self.assert_false(compatible)
        self._check_error_messages('The following preparation positions are ' \
                                   'not covered by a stock rack')


class IsoSampleStockRackJobCreator384TestCase(StockTaking384TestCase):

    def set_up(self):
        StockTaking384TestCase.set_up(self)
        self.sample_stock_racks = dict()

    def tear_down(self):
        StockTaking384TestCase.tear_down(self)
        del self.sample_stock_racks

    def _create_tool(self):
        self.tool = IsoSampleStockRackJobCreator(log=self.log,
                            preparation_plate=self.preparation_plate,
                            sample_stock_racks=self.sample_stock_racks)

    def _continue_setup(self, single_stock_rack=False):
        self._create_pool_map()
        self._create_preparation_layout()
        self._create_preparation_plate()
        if single_stock_rack:
            self._create_single_stock_rack()
        else:
            self._create_stock_racks_and_worklists()
        self._create_test_iso()
        self._create_control_stock_rack()
        self._create_issrs()
        for issr in self.iso.iso_sample_stock_racks:
            self.sample_stock_racks[issr.sector_index] = issr
        self._create_tool()

    def test_result_4(self):
        self._continue_setup(single_stock_rack=False)
        transfer_jobs = self.tool.get_result()
        self.assert_is_not_none(transfer_jobs)
        sectors = []
        for transfer_job in transfer_jobs:
            self.assert_true(isinstance(transfer_job, ContainerTransferJob))
            sector_index = transfer_job.index
            sectors.append(sector_index)
            self.assert_equal(transfer_job.target_rack.barcode,
                              self.prep_plate_barcode)
            expected_source_barcode = self.stock_racks[sector_index].barcode
            self.assert_equal(transfer_job.source_rack.barcode,
                              expected_source_barcode)
            self.assert_true(transfer_job.is_biomek_transfer)
            self.assert_equal(transfer_job.min_transfer_volume, 1)
            self.assert_is_none(transfer_job.max_transfer_volume)
            marker = 'Q%i' % (sector_index + 1)
            self.assert_true(marker in transfer_job.planned_worklist.label)
        for i in range(4):
            self.assert_true(i in sectors)
        self.assert_equal(len(sectors), 4)

    def test_result_1(self):
        self._continue_setup(single_stock_rack=True)
        transfer_jobs = self.tool.get_result()
        self.assert_is_not_none(transfer_jobs)
        self.assert_equal(len(transfer_jobs), 1)
        transfer_job = transfer_jobs[0]
        self.assert_equal(transfer_job.index, 0)
        self.assert_equal(transfer_job.target_rack.barcode,
                          self.prep_plate_barcode)
        self.assert_equal(transfer_job.source_rack.barcode,
                          self.stock_racks[0].barcode)
        self.assert_is_not_none(transfer_job.planned_worklist)
        self.assert_equal(transfer_job.min_transfer_volume, 1)
        self.assert_is_none(transfer_job.max_transfer_volume)

    def test_invalid_preparation_plate(self):
        self._continue_setup()
        self.preparation_plate = None
        self._test_and_expect_errors('The preparation plate must be a ' \
                                     'Plate object')

    def test_invalid_sample_stock_racks(self):
        self._continue_setup()
        issr = self.iso.iso_sample_stock_racks[0]
        self.sample_stock_racks = issr
        self._test_and_expect_errors('The sample stock rack map must be a ' \
                                     'dict object')
        self.sample_stock_racks = dict(A=issr)
        self._test_and_expect_errors('The sector index must be a int object')
        self.sample_stock_racks = {0 : 3}
        self._test_and_expect_errors('The sample stock rack must be a ' \
                                     'IsoSampleStockRack object')

    def test_missing_controls_wrong_plate_status(self):
        self.execute_control_transfer = False
        self._continue_setup()
        self._test_and_expect_errors('The sample stock transfers for this ' \
                    'ISO cannot be processed yet because the control have ' \
                    'not been transferred to the preparation plate so far.')
        self.preparation_plate.status = get_item_status_managed()
        self._create_tool()
        transfer_jobs = self.tool.get_result()
        self.assert_is_not_none(transfer_jobs)

    def test_missing_controls_missing_control_rack(self):
        self._continue_setup(single_stock_rack=True)
        self.iso.iso_job.iso_control_stock_rack = None
        self._test_and_expect_errors('The sample stock transfers for this ' \
                    'ISO cannot be processed yet because the control have ' \
                    'not been transferred to the preparation plate so far.')
        self.iso.iso_request.experiment_metadata.experiment_metadata_type = \
                                    get_experiment_type_robot_optimisation()
        self._create_tool()
        transfer_jobs = self.tool.get_result()
        self.assert_is_not_none(transfer_jobs)


class IsoSampleStockRack384ExecutorTestCase(StockTaking384TestCase):

    def _create_tool(self):
        self.tool = IsoSampleStockRackExecutor(iso=self.iso,
                            user=self.user)

    def _test_and_expect_errors(self, msg=None):
        StockTaking384TestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_executed_stock_worklists())
        self.assert_is_none(self.tool.get_working_layout())

    def __check_result(self, updated_iso, number_transfers,
                       expected_iso_status=ISO_STATUS.IN_PROGRESS):
        self.assert_is_not_none(updated_iso)
        self.assert_equal(updated_iso.status, expected_iso_status)
        for issr in updated_iso.iso_sample_stock_racks:
            worklist = issr.planned_worklist
            self.assert_equal(len(worklist.executed_worklists), 1)
            for ew in worklist.executed_worklists:
                self.__check_worklist(ew, number_transfers)
        self.__check_preparation_plate(updated_iso)
        executed_worklists = self.tool.get_executed_stock_worklists()
        self.assert_equal(len(executed_worklists),
                          len(updated_iso.iso_sample_stock_racks))
        for ew in executed_worklists.values():
            self.__check_worklist(ew, number_transfers)
        pl = self.tool.get_working_layout()
        self.assert_equal(pl, self.preparation_layout)

    def __check_worklist(self, ew, number_transfers):
        if self.inactivated_pos is None:
            self.assert_equal(len(ew.executed_transfers), number_transfers)
        else:
            self.assert_true(len(ew.executed_transfers) in number_transfers)
        for et in ew.executed_transfers:
            self.assert_is_not_none(et.timestamp)
            self.assert_equal(et.user, self.user)

    def __check_preparation_plate(self, updated_iso):
        for container in updated_iso.preparation_plate.containers:
            rack_pos = container.location.position
            prep_pos = self.preparation_layout.get_working_position(rack_pos)
            sample = container.sample
            if prep_pos is None:
                self.assert_is_none(sample)
                continue
            pool = prep_pos.molecule_design_pool
            pool_id = prep_pos.molecule_design_pool_id
            if not prep_pos.parent_well is None or prep_pos.is_mock or \
                                        not pool_id in self.floating_pools:
                self.assert_is_none(sample)
                continue
            expected_volume = self.take_out_volume
            self._compare_sample_volume(sample, expected_volume)
            self._compare_sample_and_pool(sample, pool)

    def __check_stock_racks(self):
        expected_volume = self.src_starting_volume * VOLUME_CONVERSION_FACTOR \
                          - self.take_out_volume
        for sector_index, stock_rack in self.stock_racks.iteritems():
            src_positions = []
            for src_label, target_labels in self.source_positions.iteritems():
                trg_label = target_labels[sector_index]
                pos_data = self.position_data[trg_label]
                if not pos_data[0] in self.floating_pools: continue
                src_positions.append(src_label)
            for container in stock_rack.containers:
                pos_label = container.location.position.label
                sample = container.sample
                if not pos_label in src_positions:
                    self.assert_is_none(sample)
                    continue
                self._compare_sample_volume(sample, expected_volume)

    def __check_single_stock_rack(self):
        # check stock rack
        stock_rack = self.stock_racks[0]
        expected_volume = self.src_starting_volume * VOLUME_CONVERSION_FACTOR \
                          - self.take_out_volume
        for container in stock_rack.containers:
            sample = container.sample
            rack_pos = container.location.position
            prep_pos = self.preparation_layout.get_working_position(rack_pos)
            if prep_pos is None:
                self.assert_is_none(sample)
                continue
            pool_id = prep_pos.molecule_design_pool_id
            if not prep_pos.parent_well is None or prep_pos.is_mock or \
                    not pool_id in self.floating_pools:
                self.assert_is_none(sample)
                continue
            self._compare_sample_volume(sample, expected_volume)

    def test_result_4_racks(self):
        self.position_data['C3'] = (205215, 10000, None, 30, 'floating')
        self.position_data['C4'] = (205216, 10000, None, 30, 'floating')
        self.floating_pools.append(205215)
        self.floating_pools.append(205216)
        self._continue_setup(single_stock_rack=False)
        updated_iso = self.tool.get_result()
        self.__check_result(updated_iso, number_transfers=3)
        self.__check_stock_racks()

    def test_result_1_racks(self):
        self._continue_setup(single_stock_rack=True)
        updated_iso = self.tool.get_result()
        self.__check_result(updated_iso,
                            number_transfers=len(self.floating_pools))
        self.__check_single_stock_rack()

    def test_result_inactivated_positions(self):
        self._continue_setup_inactivated_position()
        updated_iso = self.tool.get_result()
        self.__check_result(updated_iso, number_transfers=[2, 3])
        self.__check_stock_racks()

    def test_result_opti(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.OPTIMISATION
        self._continue_setup()
        updated_iso = self.tool.get_result()
        self.__check_result(updated_iso,
                            number_transfers=len(self.floating_pools))
        self.__check_single_stock_rack()

    def test_result_order(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.ORDER_ONLY
        self._continue_setup()
        updated_iso = self.tool.get_result()
        self.__check_result(updated_iso, expected_iso_status=ISO_STATUS.DONE,
                            number_transfers=len(self.position_data))
        self.__check_single_stock_rack()
        self.assert_equal(updated_iso.status, ISO_STATUS.DONE)

    def test_invalid_user(self):
        self._continue_setup(single_stock_rack=False)
        self.user = self.user.username
        self._test_and_expect_errors('The user must be a User object')

    def test_invalid_iso(self):
        self._test_invalid_iso()

    def test_invalid_preparation_layout(self):
        self._test_invalid_preparation_layout()

    def test_missing_stock_racks(self):
        self._test_missing_stock_racks()

    def test_missing_preparation_plate(self):
        self._test_missing_preparation_plate()

    def test_verifier_error(self):
        self._test_verifier_error()

    def test_no_verification(self):
        self._test_no_verification()

    def test_failed_transfer_job_generation(self):
        self._test_failed_transfer_job_generation()

    def test_execution_failure(self):
        self.src_starting_volume = 5 / VOLUME_CONVERSION_FACTOR
        self._continue_setup()
        self._test_and_expect_errors('Error during serial worklist execution')

    def test_previous_execution(self):
        self._continue_setup()
        for worklist in self.worklists.values():
            ExecutedWorklist(planned_worklist=worklist)
            break
        self._test_and_expect_errors('The stock transfer has already been ' \
                                     'executed!')

    def test_unexpected_status(self):
        self._continue_setup()
        self.iso.status = ISO_STATUS.IN_PROGRESS
        self._test_and_expect_errors('Unexpected ISO status: "in_progress"')


class IsoSampleStockRack384WorklistWriterTestCase(StockTaking384TestCase,
                                               FileCreatorTestCase):

    def set_up(self):
        StockTaking384TestCase.set_up(self)
        self.WL_PATH = 'thelma:tests/tools/iso/csv_files/'
        self.CYBIO_FILE = 'sample_stock_transfer_cybio.txt'

    def tear_down(self):
        StockTaking384TestCase.tear_down(self)
        del self.WL_PATH
        del self.CYBIO_FILE

    def _create_tool(self):
        self.tool = IsoSampleStockRackWorklistWriter(iso=self.iso, log=self.log)

    def __check_result(self, reference_file, number_files):
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = zipfile.ZipFile(zip_stream, 'a',
                                             zipfile.ZIP_DEFLATED, False)
        self.assert_equal(len(zip_archive.namelist()), number_files)
        tool_content = None
        for fil in zip_archive.namelist():
            tool_content = zip_archive.read(fil)
            if self.tool.BIOMEK_FILE_NAME[2:] in fil:
                self._compare_csv_file_content(tool_content,
                                                       reference_file)
            else:
                self._compare_txt_file_content(tool_content, self.CYBIO_FILE)
        zip_map = self.tool.get_zip_map()
        self.assert_equal(len(zip_map), number_files)

    def test_result_4(self):
        self._continue_setup(single_stock_rack=False)
        self.__check_result('sample_stock_transfer_384_4.csv', 2)

    def test_result_1(self):
        self._continue_setup(single_stock_rack=True)
        self.__check_result('sample_stock_transfer_384_1.csv', 1)

    def test_result_inactivated_position(self):
        self._continue_setup_inactivated_position()
        self.__check_result('sample_stock_transfer_384_4_inact.csv', 2)

    def test_result_opti(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.OPTIMISATION
        self._continue_setup()
        self.__check_result('sample_stock_transfer_384_opti.csv', 1)

    def test_result_order_only(self):
        self.experiment_type_id = EXPERIMENT_SCENARIOS.ORDER_ONLY
        self._continue_setup()
        self.__check_result('sample_stock_transfer_384_order.csv', 1)

    def test_invalid_iso(self):
        self._test_invalid_iso()
        self.assert_is_none(self.tool.get_zip_map())

    def test_invalid_preparation_layout(self):
        self._test_invalid_preparation_layout()
        self.assert_is_none(self.tool.get_zip_map())

    def test_missing_stock_racks(self):
        self._test_missing_stock_racks()
        self.assert_is_none(self.tool.get_zip_map())

    def test_missing_preparation_plate(self):
        self._test_missing_preparation_plate()
        self.assert_is_none(self.tool.get_zip_map())

    def test_verifier_error(self):
        self._test_verifier_error()
        self.assert_is_none(self.tool.get_zip_map())

    def test_no_verification(self):
        self._test_no_verification()
        self.assert_is_none(self.tool.get_zip_map())

    def test_series_writing_failure(self):
        self.src_starting_volume = 5 / VOLUME_CONVERSION_FACTOR
        self._continue_setup()
        self._test_and_expect_errors('Error during serial worklist ' \
                                     'file generation.')
        self.assert_is_none(self.tool.get_zip_map())

    def test_failed_transfer_job_generation(self):
        self._test_failed_transfer_job_generation()

    def test_multiple_volumes(self):
        self._continue_setup(single_stock_rack=False)
        issr = self.iso.iso_sample_stock_racks[0]
        for pct in issr.planned_worklist.planned_transfers:
            volume = pct.volume * 2
            pct.volume = volume
            break
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = self._get_zip_archive(zip_stream)
        self.assert_equal(len(zip_archive.namelist()), 1)
        self._check_warning_messages('Unable to create CyBio file because ' \
                                'some rack sectors have more than one volume')


class IsoControlStockRackTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.control_layout = IsoControlRackLayout()
        self.job_label = 'test_iso_job'
        self.log = TestingLog()
        self.iso_job = None
        self.icsr = None
        self.number_isos = 2
        self.stock_worklist = None
        self.job_type = self._get_entity(IJobType, 'iso-batch')
        # molecule design pool id, target labels
        self.md_map = dict(A1=(205200, ['A1', 'A2']), B1=(1056000, ['B1']))
        # target label, transfer volume
        self.volume_map = dict(A1=3, A2=6, B1=6)
        # other setup values
        self.user = get_user('it')
        self.tube_specs = TubeSpecs(label='stock_test_tube_specs',
                    max_volume=0.001500,
                    dead_volume=STOCK_DEAD_VOLUME / VOLUME_CONVERSION_FACTOR)
        self.tube_rack_specs = None
        self.well_specs = WellSpecs(label='stock_test_well_specs',
                                    max_volume=0.000300,
                                    dead_volume=0.000010,
                                    plate_specs=None)
        self.plate_specs = PlateSpecs(label='stock_test_plate_specs',
                                      shape=get_384_rack_shape(),
                                      well_specs=self.well_specs)
        self.src_starting_vol = 50 / VOLUME_CONVERSION_FACTOR
        self.tube_rack_shape = get_96_rack_shape()
        self.status = get_item_status_managed()
        self.stock_rack = None
        self.prep_plate_barcodes = {0 : '09999990', 1: '09999991' }
        self.stock_rack_barcode = '09999992'

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.control_layout
        del self.job_label
        del self.log
        del self.iso_job
        del self.icsr
        del self.number_isos
        del self.stock_worklist
        del self.job_type
        del self.md_map
        del self.volume_map
        del self.tube_specs
        del self.tube_rack_specs
        del self.well_specs
        del self.plate_specs
        del self.src_starting_vol
        del self.tube_rack_shape
        del self.status
        del self.stock_rack
        del self.prep_plate_barcodes
        del self.stock_rack_barcode

    def _continue_setup(self):
        self._create_control_layout()
        self._create_tube_rack()
        self._create_test_job()
        self._create_stock_worklist()
        self._create_control_stock_rack()
        self._create_tool()

    def _create_control_layout(self):
        for pos_label, pos_data in self.md_map.iteritems():
            tts = []
            for target_label in pos_data[1]:
                transfer_volume = self.volume_map[target_label]
                tt = TransferTarget(rack_position=target_label,
                                    transfer_volume=transfer_volume)
                tts.append(tt)
            rack_pos = get_rack_position_from_label(pos_label)
            pool = self._get_pool(pos_data[0])
            control_pos = IsoControlRackPosition(rack_position=rack_pos,
                                molecule_design_pool=pool,
                                transfer_targets=tts)
            self.control_layout.add_position(control_pos)

    def _create_tube_rack(self):
        self.tube_rack_specs = TubeRackSpecs(label='test_control_rack',
                    shape=self.tube_rack_shape, tube_specs=[self.tube_specs])
        self.stock_rack = self.tube_rack_specs.create_rack(
                        label='test_control_stock_rack', status=self.status)
        self.stock_rack.barcode = self.stock_rack_barcode
        for control_pos in self.control_layout.get_sorted_working_positions():
            rack_pos = control_pos.rack_position
            barcode = '%06i' % (control_pos.molecule_design_pool_id)
            tube = self.tube_specs.create_tube(item_status=self.status,
                        barcode=barcode, location=None)
            ContainerLocation(container=tube, rack=self.stock_rack,
                              position=rack_pos)
            self.stock_rack.containers.append(tube)
            sample = Sample(self.src_starting_vol, tube)
            pool = control_pos.molecule_design_pool
            conc = 50000 / (len(pool) * CONCENTRATION_CONVERSION_FACTOR)
            for md in pool:
                mol = Molecule(molecule_design=md, supplier=None)
                sample.make_sample_molecule(mol, conc)

    def _create_test_job(self):
        iso_request = self._create_iso_request(
                    iso_layout=RackLayout(shape=get_384_rack_shape()),
                    requester=self.user)
        ExperimentMetadata(label='test_em', number_replicates=2,
                    subproject=self._create_subproject(),
                    iso_request=iso_request,
                    experiment_metadata_type=get_experiment_type_screening(),
                    ticket_number=123)
        isos = []
        for i in range(self.number_isos):
            prep_plate = self.__create_prep_plate(i)
            iso = Iso(label='test_iso%i' % (i), iso_request=iso_request)
            IsoPreparationPlate(iso=iso, plate=prep_plate)
            isos.append(iso)
        self.iso_job = IsoJob(label=self.job_label, job_type=self.job_type,
                              isos=isos)

    def __create_prep_plate(self, counter):
        preparation_plate = self.plate_specs.create_rack(
                        status=self.status, label='control_test_prep_plate')
        preparation_plate.barcode = self.prep_plate_barcodes[counter]
        return preparation_plate

    def _create_stock_worklist(self):
        self.stock_worklist = PlannedWorklist(label='control_stock_test')
        for control_pos in self.control_layout.working_positions():
            source_pos = control_pos.rack_position
            for tt in control_pos.transfer_targets:
                volume = tt.transfer_volume / VOLUME_CONVERSION_FACTOR
                target_pos = get_rack_position_from_label(tt.position_label)
                pct = PlannedContainerTransfer(volume=volume,
                                    source_position=source_pos,
                                    target_position=target_pos)
                self.stock_worklist.planned_transfers.append(pct)

    def _create_control_stock_rack(self):
        self.icsr = IsoControlStockRack(iso_job=self.iso_job,
                    rack=self.stock_rack,
                    rack_layout=self.control_layout.create_rack_layout(),
                    planned_worklist=self.stock_worklist)

    def _test_invalid_iso_job(self):
        self._continue_setup()
        self.iso_job = self.icsr
        self._test_and_expect_errors('The ISO job must be a IsoJob object')

    def _test_no_isos(self):
        self._continue_setup()
        self.iso_job.isos = []
        self._test_and_expect_errors('There are no ISOs in this ISO job!')

    def _test_no_iso_control_stock_rack(self):
        self._continue_setup()
        self.iso_job.iso_control_stock_rack = None
        self._test_and_expect_errors('Could not find ISO control stock ' \
                                     'rack for this ISO job')

    def _test_no_stock_tube_rack(self):
        self._continue_setup()
        self.icsr.rack = None
        self._test_and_expect_errors('Could not find tube rack for this ' \
                                     'ISO control stock rack!')

    def _test_invalid_control_layout(self):
        self._continue_setup()
        self.icsr.rack_layout = None
        self._test_and_expect_errors('Could not find rack layout for the ' \
                                     'ISO control stock rack!')
        self.icsr.rack_layout = RackLayout(shape=get_96_rack_shape())
        self._test_and_expect_errors('Error when trying to convert control ' \
                                     'rack layout!')

    def _test_no_planned_worklist(self):
        self._continue_setup()
        self.icsr.planned_worklist = None
        self._test_and_expect_errors('Could not find planned worklist for ' \
                                     'this ISO control rack!')

    def _test_no_preparation_plate(self):
        self._continue_setup()
        for iso in self.iso_job:
            iso.iso_preparation_plate = None
            break
        self._test_and_expect_errors('The following ISO do not have ' \
                                     'preparation plates:')

    def _test_verification_error(self):
        self._continue_setup()
        well_specs = WellSpecs(label='invalid', max_volume=10, dead_volume=5,
                               plate_specs=None)
        plate_specs = PlateSpecs(label='invalid', shape=get_96_rack_shape(),
                                 well_specs=well_specs)
        plate = plate_specs.create_rack(label='invalid',
                                        status=get_item_status_managed())
        self.icsr.rack = plate
        self._test_and_expect_errors('Error in the verifier!')

    def _test_no_verification(self):
        self._continue_setup()
        a1_pos = get_rack_position_from_label('A1')
        self.control_layout.del_position(a1_pos)
        self.icsr.rack_layout = self.control_layout.create_rack_layout()
        self._test_and_expect_errors('The stock rack is not compatible with ' \
                                     'the ISO job!')


class IsoControlStockRackVerifierTestCase(IsoControlStockRackTestCase):

    def _create_tool(self):
        self.tool = IsoControlStockRackVerifier(stock_rack=self.stock_rack,
                            control_layout=self.control_layout, log=self.log)

    def test_result(self):
        self._continue_setup()
        compatible = self.tool.get_result()
        self.assert_is_not_none(compatible)
        self.assert_true(compatible)

    def test_invalid_control_layout(self):
        self._continue_setup()
        self.control_layout = self.control_layout.create_rack_layout()
        self._test_and_expect_errors()

    def test_invalid_stock_rack(self):
        self._continue_setup()
        self.stock_rack = self.iso_job.isos[0].preparation_plate
        self._test_and_expect_errors('The rack must be a TubeRack object')

    def test_rack_shape_mismatch(self):
        self.tube_rack_shape = get_384_rack_shape()
        self._continue_setup()
        compatible = self.tool.get_result()
        self.assert_is_not_none(compatible)
        self.assert_false(compatible)
        self._check_error_messages('The rack shapes of the expected ' \
                        'layout (8x12) and the rack (16x24) do not match!')

    def test_additional_positions(self):
        self._continue_setup()
        b1_pos = get_rack_position_from_label('B1')
        self.control_layout.del_position(b1_pos)
        self.icsr.rack_layout = self.control_layout.create_rack_layout()
        compatible = self.tool.get_result()
        self.assert_is_not_none(compatible)
        self.assert_false(compatible)
        self._check_error_messages('Some positions in the rack contain ' \
                        'molecule designs although they should be empty:')

    def test_missing_position(self):
        self._continue_setup()
        # add position to layout (re-create layout because it is already closed)
        self.md_map['C1'] = (205205, ['C1'])
        self.volume_map['C1'] = 3
        self.control_layout = IsoControlRackLayout()
        self._create_control_layout()
        self._create_tool()
        compatible = self.tool.get_result()
        self.assert_is_not_none(compatible)
        self.assert_false(compatible)
        self._check_error_messages('Some expected molecule designs are ' \
                                   'missing in the rack:')

    def test_molecule_design_mismatch(self):
        self._continue_setup()
        for control_pos in self.control_layout.working_positions():
            control_pos.molecule_design_pool = self._get_pool(205205)
            break
        self.icsr.rack_layout = self.control_layout.create_rack_layout()
        compatible = self.tool.get_result()
        self.assert_is_not_none(compatible)
        self.assert_false(compatible)
        self._check_error_messages('The molecule designs of the following ' \
                                   'positions do not match:')



class IsoControlTransferRackOverviewWriterTestCase(IsoControlStockRackTestCase,
                                                   FileCreatorTestCase):

    def set_up(self):
        IsoControlStockRackTestCase.set_up(self)
        self.WL_PATH = 'thelma:tests/tools/iso/csv_files/'
        self.TEST_FILE = 'control_transfer_overview.txt'
        self.barcodes = self.prep_plate_barcodes.values()

    def tear_down(self):
        IsoControlStockRackTestCase.tear_down(self)
        del self.WL_PATH
        del self.TEST_FILE
        del self.barcodes

    def _create_tool(self):
        self.tool = IsoControlTransferOverviewWriter(stock_rack=self.stock_rack,
                preparation_plates_barcodes=self.barcodes,
                control_layout=self.control_layout, log=self.log)

    def test_result(self):
        self._continue_setup()
        tool_stream = self.tool.get_result()
        self.assert_is_not_none(tool_stream)
        self._compare_txt_file_stream(tool_stream, self.TEST_FILE)

    def test_invalid_control_layout(self):
        self._continue_setup()
        self.control_layout = self.control_layout.create_rack_layout()
        self._test_and_expect_errors('The control layout must be a ' \
                                     'IsoControlRackLayout object')

    def test_invalid_stock_rack(self):
        self._continue_setup()
        self.stock_rack = self.user
        self._test_and_expect_errors('The stock rack must be a TubeRack object')

    def test_invalid_preparation_plate_barcodes(self):
        self._continue_setup()
        self.barcodes = self.prep_plate_barcodes
        self._test_and_expect_errors('The preparation plates list must be a ' \
                                     'list object')
        self.barcodes = [123]
        self._test_and_expect_errors('The barcode must be a basestring object')


class IsoControlStockRackExecutorTestCase(IsoControlStockRackTestCase):

    def _create_tool(self):
        self.tool = IsoControlStockRackExecutor(iso_job=self.iso_job,
                                                user=self.user)

    def _test_and_expect_errors(self, msg=None):
        IsoControlStockRackTestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_executed_stock_worklists())
        self.assert_is_none(self.tool.get_working_layout())

    def __check_worklist(self, ew):
        self.assert_equal(len(ew.executed_transfers), len(self.volume_map))
        for et in ew.executed_transfers:
            self.assert_is_not_none(et.timestamp)
            self.assert_equal(et.user, self.user)

    def __check_stock_rack(self, icsr, updated_job):
        well_data = dict()
        for container in icsr.rack.containers:
            pos_label = container.location.position.label
            take_out_volume = 0
            pos_data = self.md_map[pos_label]
            for trg_label in pos_data[1]:
                well_data[trg_label] = pos_data[0]
                take_out_volume += self.volume_map[trg_label]
            expected_volume = self.src_starting_vol * VOLUME_CONVERSION_FACTOR \
                              - (take_out_volume * len(updated_job))
            self._compare_sample_volume(container.sample, expected_volume)
        return well_data

    def __check_preparation_plates(self, updated_job, well_data):
        conc = 50000
        pools = self.control_layout.get_pools()
        for iso in updated_job:
            prep_plate = iso.preparation_plate
            for container in prep_plate.containers:
                pos_label = container.location.position.label
                sample = container.sample
                if not self.volume_map.has_key(pos_label):
                    self.assert_is_none(sample)
                    continue
                expected_volume = self.volume_map[pos_label]
                self._compare_sample_volume(sample, expected_volume)
                exp_conc = round(
                                float(conc) / (len(sample.sample_molecules)), 2)
                for sm in sample.sample_molecules:
                    sm_conc = sm.concentration * CONCENTRATION_CONVERSION_FACTOR
                    self.assert_equal(sm_conc, exp_conc)
                pool_id = well_data[pos_label]
                md_pool = pools[pool_id]
                self._compare_sample_and_pool(sample, md_pool)

    def test_result(self):
        self._continue_setup()
        updated_job = self.tool.get_result()
        self.assert_is_not_none(updated_job)
        for iso in updated_job.isos:
            self.assert_equal(iso.status, ISO_STATUS.PREPARED)
        self.assert_equal(updated_job.label, self.iso_job.label)
        icsr = updated_job.iso_control_stock_rack
        worklist = icsr.planned_worklist
        self.assert_equal(len(worklist.executed_worklists), len(updated_job))
        self.assert_equal(len(updated_job), len(self.iso_job))
        for ew in worklist.executed_worklists: self.__check_worklist(ew)
        mds = self.__check_stock_rack(icsr, updated_job)
        self.__check_preparation_plates(updated_job, mds)
        executed_worklists = self.tool.get_executed_stock_worklists()
        self.assert_is_not_none(executed_worklists)
        self.assert_equal(len(executed_worklists), len(updated_job))
        for ew in executed_worklists.values(): self.__check_worklist(ew)
        cl = self.tool.get_working_layout()
        self.assert_equal(cl, self.control_layout)

    def test_invalid_iso_job(self):
        self._test_invalid_iso_job()

    def test_no_isos(self):
        self._test_no_isos()

    def test_invalid_user(self):
        self._continue_setup()
        self.user = self.user.username
        self._test_and_expect_errors('The user must be a User object')

    def test_no_stock_tube_rack(self):
        self._test_no_stock_tube_rack()

    def test_no_iso_control_stock_rack(self):
        self._test_no_iso_control_stock_rack()

    def test_no_planned_worklist(self):
        self._test_no_planned_worklist()

    def test_no_preparation_plate(self):
        self._test_no_preparation_plate()

    def test_invalid_control_layout(self):
        self._test_invalid_control_layout()

    def test_verification_error(self):
        self._test_verification_error()

    def test_no_verification(self):
        self._test_no_verification()

    def test_series_execution_failure(self):
        self.src_starting_vol = 5 / VOLUME_CONVERSION_FACTOR
        self._continue_setup()
        self._test_and_expect_errors('Error during serial worklist execution!')

    def test_previous_execution(self):
        self._continue_setup()
        ExecutedWorklist(planned_worklist=self.stock_worklist)
        self._test_and_expect_errors('The stock transfer has already been ' \
                                     'executed!')

    def test_unexpected_status(self):
        self._continue_setup()
        for iso in self.iso_job.isos:
            iso.status = ISO_STATUS.PREPARED
            break
        self._test_and_expect_errors('Unexpected status "prepared" for ISO')


class IsoControlStockRackWorklistWriterTestCase(IsoControlStockRackTestCase,
                                                FileCreatorTestCase):

    def set_up(self):
        IsoControlStockRackTestCase.set_up(self)
        self.WL_PATH = 'thelma:tests/tools/iso/csv_files/'
        self.BIOMEK_FILE = 'control_stock_transfer.csv'
        self.INFO_FILE = 'control_transfer_overview.txt'

    def tear_down(self):
        IsoControlStockRackTestCase.tear_down(self)
        del self.WL_PATH
        del self.BIOMEK_FILE
        del self.INFO_FILE

    def _create_tool(self):
        self.tool = IsoControlStockRackWorklistWriter(iso_job=self.iso_job)

    def test_result(self):
        self._continue_setup()
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        zip_archive = zipfile.ZipFile(zip_stream, 'a',
                                             zipfile.ZIP_DEFLATED, False)
        self.assert_equal(len(zip_archive.namelist()), 2)
        for fil in zip_archive.namelist():
            tool_content = zip_archive.read(fil)
            if self.tool.INFO_FILE_NAME[2:] in fil:
                self._compare_txt_file_content(tool_content, self.INFO_FILE)
            else:
                self._compare_csv_file_content(tool_content,
                                                       self.BIOMEK_FILE)

    def test_invalid_iso_job(self):
        self._test_invalid_iso_job()

    def test_no_isos(self):
        self._test_no_isos()

    def test_no_stock_tube_rack(self):
        self._test_no_stock_tube_rack()

    def test_no_planned_worklist(self):
        self._test_no_planned_worklist()

    def test_no_preparation_plate(self):
        self._test_no_preparation_plate()

    def test_no_iso_control_stock_rack(self):
        self._test_no_iso_control_stock_rack()

    def test_invalid_control_layout(self):
        self._test_invalid_control_layout()

    def test_verification_error(self):
        self._test_verification_error()

    def test_no_verification(self):
        self._test_no_verification()

    def test_serial_writer_failure(self):
        self.src_starting_vol = 5 / VOLUME_CONVERSION_FACTOR
        self._continue_setup()
        self._test_and_expect_errors('Error during serial worklist ' \
                                     'file generation!')
