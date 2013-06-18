"""
Tests for classes involved in pool stock sample generation worklist execution

AAB
"""
from everest.entities.utils import get_root_aggregate
from thelma.automation.tools.libcreation.base import LibraryLayout
from thelma.automation.tools.libcreation.base import LibraryPosition
from thelma.automation.tools.poolcreation.execution \
    import PoolCreationStockRackVerifier
from thelma.automation.tools.poolcreation.execution import PoolCreationExecutor
from thelma.automation.tools.poolcreation.writer \
    import PoolCreationWorklistWriter
from thelma.automation.tools.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_item_status_managed
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.interfaces import IMoleculeDesign
from thelma.interfaces import IOrganization
from thelma.interfaces import ITubeRack
from thelma.interfaces import ITubeSpecs
from thelma.models.container import Tube
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import IsoSampleStockRack
from thelma.models.library import LibraryCreationIso
from thelma.models.liquidtransfer import PlannedContainerTransfer
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.moleculedesign import MoleculeDesignPool
from thelma.models.rack import TubeRackSpecs
from thelma.models.racklayout import RackLayout
from thelma.models.sample import Molecule
from thelma.models.sample import Sample
from thelma.models.utils import get_user
from thelma.tests.tools.poolcreation.utils import PoolCreationTestCase
from thelma.tests.tools.tooltestingutils import TestingLog

class PoolCreationExecutorBaseTestCase(PoolCreationTestCase):

    def set_up(self):
        PoolCreationTestCase.set_up(self)
        self.TEST_FILE_PATH = 'thelma:tests/tools/poolcreation/execution/'
        self.VALID_FILE = 'valid_file.xls'
        self.log = TestingLog()
        self.executor_user = get_user('brehm')
        self.iso_request_label = 'pool_creation_executor_test'
        self.target_volume = 30 # 30 ul
        self.target_concentration = 10000 # 1 uM
        self.take_out_volume = 2
        self.layout_number = 4
        self.pool_creation_iso = None
        self.pool_iso_layout = None
        self.iso_label = '%s-%i' % (self.iso_request_label, self.layout_number)
        self.pool_stock_rack_barcode = '09999999'
        self.pool_stock_rack = None
        self.tube_destination_barcodes = ['08000001', '08000002', '08000003']
        self.tube_destination_racks = []
        self.pool_map = dict()
        self.md_map = dict()
        # pos label - pool ID, stock tube barcodes
        self.pos_data = dict(A1=[1061383, ['10101', '10102', '10103']],
                             B1=[1060579, ['10201', '10202', '10203']],
                             C1=[1065744, ['10301', '10302', '10303']],
                             D1=[1061384, ['10401', '10402', '10403']])
        # pool ID - molecule design IDs
        self.pool_mds = { 1061383 : [10314608, 10317098, 10341387],
                          1060579 : [10247987, 10331564, 10339510],
                          1065744 : [10326002, 10332635, 10337472],
                          1061384 : [10320568, 10322383, 10330045] }
        self.starting_volume = 30 / VOLUME_CONVERSION_FACTOR
        self.tube_specs = self._get_entity(ITubeSpecs)
        self.tube_rack_specs = TubeRackSpecs(label='testspecs',
                        shape=get_96_rack_shape(), tube_specs=[self.tube_specs])
        self.pool_tube_barcode_pattern = '20%07i'
        self.stock_conc = 50000 # 50 uM
        self.supplier = self._get_entity(IOrganization, 'ambion')
        self.rack_agg = get_root_aggregate(ITubeRack)

    def tear_down(self):
        PoolCreationTestCase.tear_down(self)
        del self.take_out_volume
        del self.layout_number
        del self.pool_creation_iso
        del self.pool_iso_layout
        del self.iso_label
        del self.pool_stock_rack_barcode
        del self.pool_stock_rack
        del self.tube_destination_barcodes
        del self.tube_destination_racks
        del self.pos_data
        del self.pool_mds
        del self.starting_volume
        del self.tube_specs
        del self.tube_rack_specs
        del self.pool_tube_barcode_pattern
        del self.stock_conc
        del self.supplier
        del self.rack_agg

    def _continue_setup(self): #pylint: disable=W0221
        PoolCreationTestCase._continue_setup(self, file_name=self.VALID_FILE)
        self.__create_pool_and_md_map()
        self._create_library_layout()
        self.__create_pool_iso()
        self.__create_pool_stock_rack()
        self.__create_single_md_racks()
        self.__create_iso_sample_stock_rack()
        self._create_tool()

    def __create_pool_and_md_map(self):
        for pool in self.library.molecule_design_pool_set:
            self.pool_map[pool.id] = pool
            for md in pool: self.md_map[md.id] = md

    def _create_library_layout(self):
        self.pool_iso_layout = LibraryLayout(shape=get_96_rack_shape())
        for pos_label, data_tuple in self.pos_data.iteritems():
            rack_pos = get_rack_position_from_label(pos_label)
            pool = self.pool_map[data_tuple[0]]
            lib_pos = LibraryPosition(rack_position=rack_pos, pool=pool,
                                      stock_tube_barcodes=data_tuple[1])
            self.pool_iso_layout.add_position(lib_pos)

    def __create_pool_iso(self):
        self.pool_creation_iso = LibraryCreationIso(ticket_number=123,
                        layout_number=self.layout_number, label=self.iso_label,
                        iso_request=self.library.iso_request,
                        rack_layout=self.pool_iso_layout.create_rack_layout())

    def __create_pool_stock_rack(self):
        status = get_item_status_managed()
        self.pool_stock_rack = self.tube_rack_specs.create_rack(status=status,
                                                label='test_pool_stock_rack')
        self.pool_stock_rack.barcode = self.pool_stock_rack_barcode
        for pos_label in self.pos_data.keys():
            rack_pos = get_rack_position_from_label(pos_label)
            lib_pos = self.pool_iso_layout.get_working_position(rack_pos)
            tube_barcode = self.pool_tube_barcode_pattern % (lib_pos.pool.id)
            tube = Tube.create_from_rack_and_position(specs=self.tube_specs,
                          status=status, barcode=tube_barcode,
                          rack=self.pool_stock_rack, position=rack_pos)
            self.pool_stock_rack.containers.append(tube)

    def __create_single_md_racks(self):
        status = get_item_status_managed()
        conc = self.stock_conc / CONCENTRATION_CONVERSION_FACTOR
        for i in range(len(self.tube_destination_barcodes)):
            barcode = self.tube_destination_barcodes[i]
            rack = self.tube_rack_specs.create_rack(label=barcode,
                                                    status=status)
            rack.barcode = barcode
            for pos_label, data_tuple in self.pos_data.iteritems():
                rack_pos = get_rack_position_from_label(pos_label)
                pool_id = data_tuple[0]
                md_id = self.pool_mds[pool_id][i]
                md = self.md_map[md_id]
                tube_barcode = data_tuple[1][i]
                tube = Tube.create_from_rack_and_position(specs=self.tube_specs,
                                      status=status, barcode=tube_barcode,
                                      rack=rack, position=rack_pos)
                sample = Sample(volume=self.starting_volume, container=tube)
                mol = Molecule(molecule_design=md, supplier=self.supplier)
                sample.make_sample_molecule(molecule=mol, concentration=conc)
                rack.containers.append(tube)
            self.tube_destination_racks.append(rack)
            self.rack_agg.add(rack)

    def __create_iso_sample_stock_rack(self):
        volume = self.take_out_volume / VOLUME_CONVERSION_FACTOR
        writer_cls = PoolCreationWorklistWriter
        wl_label = writer_cls.SAMPLE_STOCK_WORKLIST_LABEL + \
                writer_cls.SAMPLE_STOCK_WORKLIST_DELIMITER.join(
                                                self.tube_destination_barcodes)
        worklist = PlannedWorklist(label=wl_label)
        for pos_label in self.pos_data.keys():
            rack_pos = get_rack_position_from_label(pos_label)
            pct = PlannedContainerTransfer(volume=volume,
                           source_position=rack_pos, target_position=rack_pos)
            worklist.planned_transfers.append(pct)
        IsoSampleStockRack(iso=self.pool_creation_iso,
                           rack=self.pool_stock_rack,
                           sector_index=0,
                           planned_worklist=worklist)


class PoolCreationStockRackVerifierTestCase(PoolCreationExecutorBaseTestCase):

    def _create_tool(self):
        self.tool = PoolCreationStockRackVerifier(
                            library_layout=self.pool_iso_layout,
                            stock_racks=self.tube_destination_racks,
                            log=self.log)

    def _test_and_expect_failure(self, msg):
        self._create_tool()
        result = self.tool.get_result()
        self.assert_is_not_none(result)
        self.assert_false(result)
        self._check_error_messages(msg)

    def test_result(self):
        self._continue_setup()
        result = self.tool.get_result()
        self.assert_is_not_none(result)
        self.assert_true(result)

    def test_invalid_input_values(self):
        self._continue_setup()
        ll = self.pool_iso_layout
        self.pool_iso_layout = None
        self._test_and_expect_errors('The pool creation ISO layout must be a ' \
                                     'LibraryLayout')
        self.pool_iso_layout = ll
        self.tube_destination_racks = dict()
        self._test_and_expect_errors('The stock rack list must be a list')
        self.tube_destination_racks = [123]
        self._test_and_expect_errors('The stock rack must be a TubeRack ' \
                                     'object (obtained: int)')

    def test_missing_tube(self):
        self._continue_setup()
        md = self._get_entity(IMoleculeDesign, '1001')
        new_pool = MoleculeDesignPool(molecule_designs=set([md]))
        new_pool.id = -1
        new_rack_pos = get_rack_position_from_label('A1')
        new_lib_pos = LibraryPosition(rack_position=new_rack_pos,
                              pool=new_pool,
                              stock_tube_barcodes=['invalid'])
        self.pool_iso_layout.add_position(new_lib_pos)
        self._test_and_expect_failure('There are some molecule designs ' \
                  'missing in the prepared single design stock racks: 1001.')

    def test_additional_tubes(self):
        self._continue_setup()
        rack_pos = get_rack_position_from_label('B1')
        self.pool_iso_layout.del_position(rack_pos)
        self._test_and_expect_failure('The single design stock racks contain ' \
              'molecule designs that should not be there: B1 in 08000001 ' \
              '(found: 10247987), B1 in 08000002 (found: 10331564), B1 ' \
              'in 08000003 (found: 10339510).')

    def test_mismatching_tubes(self):
        self._continue_setup()
        a1_pos = get_rack_position_from_label('A1')
        c1_pos = get_rack_position_from_label('C1')
        lp_a1 = self.pool_iso_layout.get_working_position(a1_pos)
        lp_c1 = self.pool_iso_layout.get_working_position(c1_pos)
        a1_pool = lp_a1.pool
        c1_pool = lp_c1.pool
        lp_a1.pool = c1_pool
        lp_c1.pool = a1_pool
        self._test_and_expect_failure('Some molecule designs in the single ' \
              'design stock racks do not match the expected ones')


class PoolCreationExecutorTestCase(PoolCreationExecutorBaseTestCase):

    def _create_tool(self):
        self.tool = PoolCreationExecutor(
                             pool_creation_iso=self.pool_creation_iso,
                             user=self.executor_user)

    def _test_and_expect_errors(self, msg=None):
        PoolCreationExecutorBaseTestCase._test_and_expect_errors(self, msg=msg)
        self.assert_is_none(self.tool.get_working_layout())
        self.assert_is_none(self.tool.get_executed_stock_worklists())

    def _check_result(self):
        updated_iso = self.tool.get_result()
        self.assert_is_not_none(updated_iso)
        self.assert_equal(updated_iso.status, ISO_STATUS.DONE)
        self.__check_worklists(updated_iso)
        self.__check_single_md_racks()
        self.__check_pool_stock_rack(updated_iso)

    def __check_worklists(self, updated_iso):
        worklist_series = updated_iso.iso_request.worklist_series
        self.assert_equal(len(worklist_series), 1)
        worklist = worklist_series.get_worklist_for_index(0)
        self.assert_equal(len(worklist.executed_worklists), 1)
        ew = worklist.executed_worklists[0]
        self.assert_equal(len(ew.executed_transfers), len(self.pos_data))
        found_positions = []
        buffer_volume = self.target_volume - (self.take_out_volume * 3)
        for et in ew.executed_transfers:
            self._check_executed_transfer(et, TRANSFER_TYPES.CONTAINER_DILUTION)
            volume = et.planned_transfer.volume * VOLUME_CONVERSION_FACTOR
            self.assert_equal(volume, buffer_volume)
            found_positions.append(et.planned_transfer.target_position.label)
        self.assert_equal(sorted(found_positions), sorted(self.pos_data.keys()))

    def __check_single_md_racks(self):
        exp_volume = (self.starting_volume * VOLUME_CONVERSION_FACTOR) \
                     - self.take_out_volume
        exp_positions = self.pos_data.keys()
        for rack in self.tube_destination_racks:
            for tube in rack.containers:
                pos_label = tube.location.position.label
                if not pos_label in exp_positions:
                    self.assert_is_none(tube.sample)
                    continue
                self._compare_sample_volume(tube.sample, exp_volume)

    def __check_pool_stock_rack(self, updated_iso):
        issrs = updated_iso.iso_sample_stock_racks
        self.assert_equal(len(issrs), 1)
        issr = issrs[0]
        exp_positions = self.pos_data.keys()
        # check worklists
        src_racks = set()
        worklist = issr.planned_worklist
        self.assert_equal(len(worklist.executed_worklists), 3)
        for ew in worklist.executed_worklists:
            self.assert_equal(len(ew.executed_transfers),
                              len(exp_positions))
            wl_labels = []
            for ect in ew.executed_transfers:
                self._check_executed_transfer(ect,
                                    TRANSFER_TYPES.CONTAINER_TRANSFER)
                wl_labels.append(ect.planned_transfer.target_position.label)
                src_racks.add(ect.source_container.location.rack.barcode)
                target_rack = ect.target_container.location.rack.barcode
                self.assert_equal(target_rack, self.pool_stock_rack_barcode)
            self.assert_equal(sorted(wl_labels), sorted(exp_positions))
        self.assert_equal(sorted(list(src_racks)),
                          sorted(self.tube_destination_barcodes))
        # check rack
        rack = issr.rack
        self.assert_equal(rack.status.name, ITEM_STATUS_NAMES.MANAGED)
        self.assert_equal(len(rack.containers), len(exp_positions))
        conc = round((self.target_concentration / 3.), 2)
        exp_volume = self.target_volume
        found_labels = []
#        exp_mt = self.library.molecule_design_pool_set.molecule_type
        for tube in rack.containers:
            pos_label = tube.location.position.label
            found_labels.append(pos_label)
            self.assert_true(pos_label in exp_positions)
            pos_data = self.pos_data[pos_label]
            pool_id = pos_data[0]
            pool = self.pool_map[pool_id]
            sample = tube.sample
            self._compare_sample_and_pool(sample, pool, conc)
            self._compare_sample_volume(sample, exp_volume)
            # TODO: reactivate one we found a way to do this
#            self.assert_true(isinstance(sample, StockSample))
#            self.assert_equal(sample.supplier, self.supplier)
#            self.assert_equal(sample.molecule_type, exp_mt)
        self.assert_equal(sorted(found_labels), sorted(exp_positions))

    def test_result(self):
        self._continue_setup()
        self._check_result()

    def test_invalid_input_values(self):
        self._continue_setup()
        pci = self.pool_creation_iso
        self.pool_creation_iso = None
        self._test_and_expect_errors('The pool creation ISO must be a ' \
                             'LibraryCreationIso object (obtained: NoneType).')
        self.pool_creation_iso = pci
        self.executor_user = None
        self._test_and_expect_errors('The user must be a User object ' \
                                     '(obtained: NoneType).')

    def test_layout_converter_failure(self):
        self._continue_setup()
        self.pool_creation_iso.rack_layout = RackLayout(
                                                shape=get_96_rack_shape())
        self._test_and_expect_errors('Error when trying to convert library ' \
                                     'layout.')

    def test_unexpected_iso_sample_stock_racks(self):
        self._continue_setup()
        self.pool_creation_iso.iso_sample_stock_racks = []
        self._test_and_expect_errors('There is an unexpected number of ISO ' \
                'sample stock racks attached to this ISO (0). There should ' \
                'be exactly one!')

    def test_unknown_source_rack(self):
        self._continue_setup()
        self.tube_destination_barcodes[0] = '09876543'
        wl = self.pool_creation_iso.iso_sample_stock_racks[0].planned_worklist
        writer_cls = PoolCreationWorklistWriter
        wl_label = writer_cls.SAMPLE_STOCK_WORKLIST_LABEL + \
                writer_cls.SAMPLE_STOCK_WORKLIST_DELIMITER.join(
                                                self.tube_destination_barcodes)
        wl.label = wl_label
        self._test_and_expect_errors()

    def test_no_verification(self):
        self._continue_setup()
        rack_pos = get_rack_position_from_label('B1')
        self.pool_iso_layout.del_position(rack_pos)
        self.pool_creation_iso.rack_layout = \
                                    self.pool_iso_layout.create_rack_layout()
        self._test_and_expect_errors('The stock racks with the single ' \
                 'molecule designs are not compatible to the expected layout!')

    def test_series_execution_error(self):
        self.starting_volume = 5 / VOLUME_CONVERSION_FACTOR
        self._continue_setup()
        self._test_and_expect_errors('Error during serial transfer execution.')

# TODO: review after we found a way to create stock samples
#    def test_different_suppliers(self):
#        self.assert_is_not_none(self.supplier)
#        self._continue_setup()
#        for tube in self.tube_destination_racks[0].containers:
#            for sm in tube.sample.sample_molecules:
#                new_supplier = self._get_entity(IOrganization, 'cenix')
#                sm.molecule.supplier = new_supplier
#                break
#            break
#        self._test_and_expect_errors('The designs for some of the pools ' \
#                 'originate from different suppliers: A1 (pool: 1061383, ' \
#                 'found: Ambion, Cenix')
