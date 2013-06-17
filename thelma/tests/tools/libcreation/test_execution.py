"""
Tests for classes involved in library worklist execution

AAB
"""
from everest.entities.utils import get_root_aggregate
from thelma.automation.tools.libcreation.base \
    import MOLECULE_DESIGN_TRANSFER_VOLUME
from thelma.automation.tools.libcreation.base \
    import POOL_STOCK_RACK_CONCENTRATION
from thelma.automation.tools.libcreation.base \
    import PREPARATION_PLATE_CONCENTRATION
from thelma.automation.tools.libcreation.base \
    import get_source_plate_transfer_volume
from thelma.automation.tools.libcreation.base import ALIQUOT_PLATE_CONCENTRATION
from thelma.automation.tools.libcreation.base import ALIQUOT_PLATE_VOLUME
from thelma.automation.tools.libcreation.base import LibraryBaseLayout
from thelma.automation.tools.libcreation.base import LibraryBaseLayoutPosition
from thelma.automation.tools.libcreation.base import LibraryLayout
from thelma.automation.tools.libcreation.base import LibraryPosition
from thelma.automation.tools.libcreation.base import MOLECULE_TYPE
from thelma.automation.tools.libcreation.base import POOL_STOCK_RACK_VOLUME
from thelma.automation.tools.libcreation.base import PREPARATION_PLATE_VOLUME
from thelma.automation.tools.libcreation.base import STARTING_NUMBER_ALIQUOTS
from thelma.automation.tools.libcreation.execution \
    import LibraryCreationBufferWorklistTransferJobCreator
from thelma.automation.tools.libcreation.execution \
    import LibraryCreationExecutor
from thelma.automation.tools.libcreation.execution \
    import LibraryCreationStockRackVerifier
from thelma.automation.tools.libcreation.generation \
    import LibraryCreationWorklistGenerator
from thelma.automation.tools.libcreation.writer \
    import LibraryCreationWorklistWriter
from thelma.automation.tools.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.tools.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.tools.semiconstants import get_384_rack_shape
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_item_status_managed
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.semiconstants import get_reservoir_spec
from thelma.automation.tools.stock.base import get_default_stock_concentration
from thelma.automation.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.worklists.series import ContainerDilutionJob
from thelma.interfaces import IMoleculeDesign
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import IOrganization
from thelma.interfaces import ITubeRack
from thelma.interfaces import ITubeSpecs
from thelma.models.container import Tube
from thelma.models.container import WellSpecs
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import ISO_TYPES
from thelma.models.iso import IsoAliquotPlate
from thelma.models.iso import IsoRequest
from thelma.models.iso import IsoSampleStockRack
from thelma.models.library import LibraryCreationIso
from thelma.models.library import LibrarySourcePlate
from thelma.models.library import MoleculeDesignLibrary
from thelma.models.liquidtransfer import PlannedContainerTransfer
from thelma.models.liquidtransfer import PlannedRackTransfer
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.moleculedesign import MoleculeDesignPool
from thelma.models.rack import PlateSpecs
from thelma.models.rack import TubeRackSpecs
from thelma.models.racklayout import RackLayout
from thelma.models.sample import Molecule
from thelma.models.sample import Sample
from thelma.models.utils import get_user
from thelma.tests.tools.tooltestingutils import SilentLog
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase


class LibraryCreationExecutorBaseTestCase(ToolsAndUtilsTestCase):

    def set_up(self):
        ToolsAndUtilsTestCase.set_up(self)
        self.library = None
        self.libname = 'testlib'
        self.library_iso = None
        self.layout_number = 4
        self.requester = get_user('sachse')
        self.pos_sectors = {0 : ['C3', 'C5', 'E3', 'E5'],
                            1 : ['C2', 'C4', 'E2', 'E4'],
                            2 : ['B5', 'D3'],
                            3 : ['B4', 'D2']}
        # 384 pos - 96 pos
        self.translated_positions = dict(
                            C3='B2', C5='B3', E3='C2', E5='C3',
                            C2='B1', C4='B2', E2='C1', E4='C2',
                            B5='A3', D3='B2',
                            B4='A2', D2='B1')
        # pos label (384) - pool ID, stock tube barcodes
        self.pos_data = dict(
                C3=[1, ['101011', '101012', '101013']],
                C5=[2, ['102014', '102015', '102016']],
                E3=[3, ['103017', '103018', '103019']],
                E5=[4, ['104020', '104021', '104022']],
                C2=[5, ['105023', '105024', '105025']],
                C4=[6, ['106026', '106027', '106028']],
                E2=[7, ['107029', '107030', '107031']],
                E4=[8, ['108032', '108033', '108034']],
                B5=[9, ['109035', '109036', '109037']],
                D3=[10, ['110038', '110039', '110040']],
                B4=[11, ['111041', '111042', '111043']],
                D2=[12, ['112044', '112045', '112046']])
        self.pool_tube_barcode_pattern = '20%02i'
        # pool id, molecule design IDs
        self.pool_mds = {
                1 : [11, 12, 13], 2 : [14, 15, 16], 3 : [17, 18, 19],
                4 : [20, 21, 22], 5 : [23, 24, 25], 6 : [26, 27, 28],
                7 : [29, 30, 31], 8 : [32, 33, 34], 9 : [35, 36, 37],
                10 : [38, 39, 40], 11 : [41, 42, 43], 12 : [44, 45, 46]}
        self.pool_id_modifier = 9999999
        self.pool_map = dict()
        self.md_map = dict()
        self.base_layout = None
        self.library_layout = None
        self.stock_conc = get_default_stock_concentration(MOLECULE_TYPE)
        self.worklist_series = None
        self.executor_user = get_user('it')
        self.pool_stock_rack_barcodes = {0 : '09990000', 1 : '09990001',
                                         2 : '09990002', 3 : '09990003'}
        self.pool_stock_racks = dict()
        self.tube_destination_racks = {
                        0 : ['09888101', '09888102', '09888103'],
                        1 : ['09888201', '09888202', '09888203'],
                        2 : ['09888301', '09888302', '09888303'],
                        3 : ['09888401', '09888402', '09888403']}
        self.single_stock_racks = dict()
        self.prep_plate_barcodes = {0 : '09955001', 1 : '09955002',
                                    2 : '09955003', 3 : '09955004'}
        self.aliquot_barcode_pattern = '0994400%i'
        self.starting_volume = 30 / VOLUME_CONVERSION_FACTOR
        self.tube_specs = self._get_entity(ITubeSpecs)
        self.tube_rack_specs = TubeRackSpecs(label='testspecs',
                        shape=get_96_rack_shape(), tube_specs=[self.tube_specs])
        self.status = get_item_status_managed()
        self.supplier = self._get_entity(IOrganization)
        self.rack_agg = get_root_aggregate(ITubeRack)
        self.missing_lib_pos = []

    def tear_down(self):
        ToolsAndUtilsTestCase.tear_down(self)
        del self.library
        del self.libname
        del self.library_iso
        del self.layout_number
        del self.pos_sectors
        del self.requester
        del self.pool_stock_rack_barcodes
        del self.pool_stock_racks
        del self.tube_destination_racks
        del self.single_stock_racks
        del self.prep_plate_barcodes
        del self.aliquot_barcode_pattern
        del self.pool_tube_barcode_pattern
        del self.starting_volume
        del self.base_layout
        del self.library_layout
        del self.worklist_series
        del self.tube_rack_specs
        del self.tube_specs
        del self.status
        del self.supplier
        del self.missing_lib_pos

    def _continue_setup(self):
        self.__create_mds_and_pools()
        self.__create_layouts()
        self.__create_worklist_series()
        self.__create_iso_request()
        self.__create_library_iso()
        self.__create_library_plates()
        self.__create_pool_stock_racks()
        self.__create_iso_sample_stock_racks()
        self.__create_single_md_racks()
        self._create_tool()

    def __create_mds_and_pools(self):
        pool_stock_conc = get_default_stock_concentration(MOLECULE_TYPE, 3) \
                          / CONCENTRATION_CONVERSION_FACTOR
        stock_set_agg = get_root_aggregate(IMoleculeDesignPool)
        for pool_id, md_ids in self.pool_mds.iteritems():
            mds = set()
            for md_id in md_ids:
                md = self._get_entity(IMoleculeDesign, str(md_id))
                self.md_map[md_id] = md
                mds.add(md)
            pool = MoleculeDesignPool(molecule_designs=mds,
                                    default_stock_concentration=pool_stock_conc)
            pool.id = pool_id + self.pool_id_modifier
            self.pool_map[pool.id] = pool
            stock_set_agg.add(pool)

    def __create_layouts(self):
        shape = get_384_rack_shape()
        self.base_layout = LibraryBaseLayout(shape=shape)
        self.library_layout = LibraryLayout(shape=shape)
        for pos_labels in self.pos_sectors.values():
            for pos_label in pos_labels:
                rack_pos = get_rack_position_from_label(pos_label)
                base_pos = LibraryBaseLayoutPosition(rack_position=rack_pos)
                self.base_layout.add_position(base_pos)
                if pos_label in self.missing_lib_pos: continue
                pos_data = self.pos_data[pos_label]
                pool_id = pos_data[0] + self.pool_id_modifier
                pool = self.pool_map[pool_id]
                lib_pos = LibraryPosition(rack_position=rack_pos,
                                          pool=pool,
                                          stock_tube_barcodes=pos_data[1])
                self.library_layout.add_position(lib_pos)

    def __create_worklist_series(self):
        generator = LibraryCreationWorklistGenerator(log=SilentLog(),
                    base_layout=self.base_layout, library_name=self.libname,
                    stock_concentration=self.stock_conc)
        self.worklist_series = generator.get_result()

    def __create_iso_request(self):
        iso_request = IsoRequest(
                    iso_layout=self.base_layout.create_rack_layout(),
                    requester=self.requester,
                    number_plates=3,
                    number_aliquots=STARTING_NUMBER_ALIQUOTS,
                    plate_set_label=self.libname,
                    worklist_series=self.worklist_series,
                    iso_type=ISO_TYPES.LIBRARY_CREATION)
        md_type = self.pool_map.values()[0].molecule_type
        pool_set = self.library_layout.get_pool_set(md_type)
        self.library = MoleculeDesignLibrary(label=self.libname,
                molecule_design_pool_set=pool_set, iso_request=iso_request,
                final_volume=ALIQUOT_PLATE_VOLUME / VOLUME_CONVERSION_FACTOR,
                final_concentration=ALIQUOT_PLATE_CONCENTRATION \
                                    / CONCENTRATION_CONVERSION_FACTOR)

    def __create_library_iso(self):
        md_type = self.library.molecule_design_pool_set.molecule_type
        self.library_iso = \
            LibraryCreationIso(ticket_number=1,
                               layout_number=self.layout_number,
                               label='%s-%i' % (self.libname, self.layout_number),
                               molecule_design_pool_set=
                                    self.library_layout.get_pool_set(md_type),
                               rack_layout=
                                    self.library_layout.create_rack_layout(),
                               iso_request=self.library.iso_request)

    def __create_library_plates(self):
        well_specs = WellSpecs(label='testwellspecs',
                max_volume=100 / VOLUME_CONVERSION_FACTOR,
                dead_volume=10 / VOLUME_CONVERSION_FACTOR, plate_specs=None)
        plate_specs_96 = PlateSpecs(label='testpaltespecs96',
                                    shape=get_96_rack_shape(),
                                    well_specs=well_specs)
        for sector_index in self.pos_sectors.keys():
            label = 'lib_source_plate_%i' % (sector_index)
            plate = plate_specs_96.create_rack(label=label, status=self.status)
            plate.barcode = self.prep_plate_barcodes[sector_index]
            LibrarySourcePlate(iso=self.library_iso, plate=plate,
                               sector_index=sector_index)
        plate_specs_384 = PlateSpecs(label='testplatespecs384',
                                    shape=get_384_rack_shape(),
                                    well_specs=well_specs)
        for i in range(STARTING_NUMBER_ALIQUOTS):
            label = 'aliquot_%i' % (i)
            barcode = self.aliquot_barcode_pattern % (i)
            plate = plate_specs_384.create_rack(label=label, status=self.status)
            plate.barcode = barcode
            IsoAliquotPlate(iso=self.library_iso, plate=plate)

    def __create_pool_stock_racks(self):
        for sector_index, pos_labels in self.pos_sectors.iteritems():
            rack = self.tube_rack_specs.create_rack(status=self.status,
                                        label='sector_%i' % (sector_index))
            rack.barcode = self.pool_stock_rack_barcodes[sector_index]
            self.pool_stock_racks[sector_index] = rack
            for pos_label_384 in pos_labels:
                if pos_label_384 in self.missing_lib_pos: continue
                pos_label_96 = self.translated_positions[pos_label_384]
                rack_pos = get_rack_position_from_label(pos_label_96)
                pos_data = self.pos_data[pos_label_384]
                pool_id = pos_data[0]
                tube_barcode = self.pool_tube_barcode_pattern % (pool_id)
                tube = Tube.create_from_rack_and_position(specs=self.tube_specs,
                                status=self.status, barcode=tube_barcode,
                                rack=rack, position=rack_pos)
                rack.containers.append(tube)

    def __create_iso_sample_stock_racks(self):
        writer_cls = LibraryCreationWorklistWriter
        volume = MOLECULE_DESIGN_TRANSFER_VOLUME / VOLUME_CONVERSION_FACTOR
        for sector_index, pos_labels in self.pos_sectors.iteritems():
            dest_barcodes = self.tube_destination_racks[sector_index]
            wl_label = writer_cls.SAMPLE_STOCK_WORKLIST_LABEL + \
                writer_cls.SAMPLE_STOCK_WORKLIST_DELIMITER.join(dest_barcodes)
            worklist = PlannedWorklist(label=wl_label)
            for pos_label_384 in pos_labels:
                if pos_label_384 in self.missing_lib_pos: continue
                pos_label_96 = self.translated_positions[pos_label_384]
                rack_pos = get_rack_position_from_label(pos_label_96)
                pct = PlannedContainerTransfer(volume=volume,
                            source_position=rack_pos, target_position=rack_pos)
                worklist.planned_transfers.append(pct)
            IsoSampleStockRack(iso=self.library_iso,
                        rack=self.pool_stock_racks[sector_index],
                        sector_index=sector_index, planned_worklist=worklist)

    def __create_single_md_racks(self):
        conc = self.stock_conc / CONCENTRATION_CONVERSION_FACTOR
        for sector_index, rack_barcodes in \
                                    self.tube_destination_racks.iteritems():
            self.single_stock_racks[sector_index] = []
            for i in range(len(rack_barcodes)):
                rack_barcode = rack_barcodes[i]
                rack = self.tube_rack_specs.create_rack(label=rack_barcode,
                                                        status=self.status)
                rack.barcode = rack_barcode
                for pos_label_384 in self.pos_sectors[sector_index]:
                    if pos_label_384 in self.missing_lib_pos: continue
                    pos_label_96 = self.translated_positions[pos_label_384]
                    rack_pos_96 = get_rack_position_from_label(pos_label_96)
                    pos_data = self.pos_data[pos_label_384]
                    pool_id = pos_data[0]
                    md_id = self.pool_mds[pool_id][i]
                    md = self.md_map[md_id]
                    tube_barcode = pos_data[1][i]
                    tube = Tube.create_from_rack_and_position(
                                specs=self.tube_specs, status=self.status,
                                barcode=tube_barcode, rack=rack,
                                position=rack_pos_96)
                    rack.containers.append(tube)
                    sample = Sample(volume=self.starting_volume, container=tube)
                    mol = Molecule(molecule_design=md, supplier=self.supplier)
                    sample.make_sample_molecule(molecule=mol,
                                                concentration=conc)
                self.single_stock_racks[sector_index].append(rack)
                self.rack_agg.add(rack)


class LibraryCreationBufferWorklistTransferJobCreatorTestCase(
                                        LibraryCreationExecutorBaseTestCase):

    def set_up(self):
        LibraryCreationExecutorBaseTestCase.set_up(self)
        self.create_pool_stock_racks = True
        self.ignored_positions = {0 : [], 1 : [], 2 : [],
                                  3 : [get_rack_position_from_label('B4')]}

    def _create_tool(self):
        self.tool = LibraryCreationBufferWorklistTransferJobCreator(
                                log=TestingLog(),
                                library_creation_iso=self.library_iso,
                                pool_stock_racks=self.pool_stock_racks,
                                ignored_positions=self.ignored_positions)

    def test_result(self):
        self._continue_setup()
        transfer_jobs = self.tool.get_result()
        self.assert_is_not_none(transfer_jobs)
        exp_length = len(self.pos_sectors) * 2
        self.assert_equal(len(transfer_jobs), exp_length)
        rs_quarter = get_reservoir_spec(RESERVOIR_SPECS_NAMES.QUARTER_MODULAR)
        prep_plate_barcodes = []
        stock_rack_barcodes = []
        for job_index, transfer_job in transfer_jobs.iteritems():
            self.assert_true(isinstance(transfer_job, ContainerDilutionJob))
            self.assert_equal(transfer_job.reservoir_specs.name,
                              rs_quarter.name)
            self.assert_equal(transfer_job.source_rack_barcode,
                              self.tool.BUFFER_RESERVOIR_BARCODE)
            ign_pos = []
            if transfer_job.planned_worklist.label.endswith('4'):
                ign_pos = self.ignored_positions[3]
            self.assert_equal(transfer_job.ignored_positions, ign_pos)
            target_barcode = transfer_job.target_rack.barcode
            if job_index < len(self.pos_sectors):
                stock_rack_barcodes.append(target_barcode)
            else:
                prep_plate_barcodes.append(target_barcode)
        self.assert_equal(sorted(stock_rack_barcodes),
                          sorted(self.pool_stock_rack_barcodes.values()))
        self.assert_equal(sorted(prep_plate_barcodes),
                          sorted(self.prep_plate_barcodes.values()))

    def test_invalid_input_values(self):
        self._continue_setup()
        lci = self.library_iso
        self.library_iso = None
        self._test_and_expect_errors('The library creation ISO must be a ' \
                                     'LibraryCreationIso')
        self.library_iso = lci
        self.ignored_positions = None
        self._test_and_expect_errors()
        self.ignored_positions = {'2' : []}
        self._test_and_expect_errors()
        self.ignored_positions = {2 : 2}
        self._test_and_expect_errors()
        self.ignored_positions = {}
        rack = self.pool_stock_racks.values()[0]
        self.pool_stock_racks = []
        self._test_and_expect_errors('The pool stock rack map must be a dict')
        self.pool_stock_racks = dict()
        self._test_and_expect_errors('There are no racks in the pool stock ' \
                                     'rack map!')
        self.pool_stock_racks = {1 : 1}
        self._test_and_expect_errors('The pool stock rack must be a TubeRack')
        self.pool_stock_racks = {'1' : rack}
        self._test_and_expect_errors('The sector index must be a int')

    def test_missing_worklist_series(self):
        self._continue_setup()
        self.library_iso.iso_request.worklist_series = None
        self._test_and_expect_errors()

    def test_missing_pool_stock_worklist(self):
        self._continue_setup()
        generator = LibraryCreationWorklistGenerator
        for worklist in self.library_iso.iso_request.worklist_series:
            if generator.LIBRARY_STOCK_BUFFER_WORKLIST_LABEL[2:-2] in \
                                                        worklist.label:
                worklist.label = 'invalid'
                break
        self._test_and_expect_errors('Some stock buffer worklists are missing')

    def test_missing_pool_source_worklist(self):
        self._continue_setup()
        generator = LibraryCreationWorklistGenerator
        for worklist in self.library_iso.iso_request.worklist_series:
            if generator.LIBRARY_PREP_BUFFER_WORKLIST_LABEL[2:-2] in \
                                                        worklist.label:
                worklist.label = 'invalid'
                break
        self._test_and_expect_errors('Some source buffer worklists are missing')


class LibraryCreationExecutorTestCase(LibraryCreationExecutorBaseTestCase):

    def _create_tool(self):
        self.tool = LibraryCreationExecutor(user=self.executor_user,
                            library_creation_iso=self.library_iso)

    def _test_and_expect_errors(self, msg=None):
        LibraryCreationExecutorBaseTestCase._test_and_expect_errors(self,
                                                                    msg=msg)
        self.assert_is_none(self.tool.get_working_layout())
        self.assert_is_none(self.tool.get_executed_stock_worklists())

    def __check_result(self):
        updated_iso = self.tool.get_result()
        self.assert_is_not_none(updated_iso)
        self.assert_equal(updated_iso.status, ISO_STATUS.DONE)
        self.__check_worklists(updated_iso)
        self.__check_single_md_racks()
        self.__check_pool_stock_rack(updated_iso)
        self.__check_preparation_plates(updated_iso)
        self.__check_aliquot_plates(updated_iso)
        self.assert_equal(self.tool.get_working_layout(),
                          self.library_layout)
        stw = self.tool.get_executed_stock_worklists()
        self.assert_equal(len(stw), 12)

    def __check_worklists(self, updated_iso):
        worklist_series = updated_iso.iso_request.worklist_series
        for worklist in worklist_series:
            if 'stock_buffer' in worklist.label:
                self.assert_equal(len(worklist.executed_worklists), 1)
            elif 'prep_buff' in worklist.label:
                self.assert_equal(len(worklist.executed_worklists), 1)
            elif 'stock_to_prep' in worklist.label:
                self.assert_equal(len(worklist.executed_worklists), 1)
                source_racks = []
                target_racks = []
                ew = worklist.executed_worklists[0]
                self.assert_equal(len(ew.executed_transfers), 4)
                for ert in ew.executed_transfers:
                    source_racks.append(ert.source_rack.barcode)
                    target_racks.append(ert.target_rack.barcode)
                self.assert_equal(sorted(source_racks),
                            sorted(self.pool_stock_rack_barcodes.values()))
                self.assert_equal(sorted(target_racks),
                            sorted(self.prep_plate_barcodes.values()))
            elif 'prep_to_aliquot' in worklist.label:
                self.assert_equal(len(worklist.executed_worklists), 1)
                ew = worklist.executed_worklists[0]
                self.assert_equal(len(ew.executed_transfers), 32)
                target_racks = set()
                source_racks = set()
                for ert in ew.executed_transfers:
                    for ert in ew.executed_transfers:
                        source_racks.add(ert.source_rack.barcode)
                        target_racks.add(ert.target_rack.barcode)
                self.assert_equal(sorted(source_racks),
                                  sorted(self.prep_plate_barcodes.values()))
                self.assert_equal(len(target_racks), 8)
            else:
                raise ValueError('unknown worklist "%s"' % (worklist.label))

    def __check_single_md_racks(self):
        exp_volume = (self.starting_volume * VOLUME_CONVERSION_FACTOR) \
                     - MOLECULE_DESIGN_TRANSFER_VOLUME
        for sector_index, racks in self.single_stock_racks.iteritems():
            exp_positions = []
            for pos_label in self.pos_sectors[sector_index]:
                if pos_label in self.missing_lib_pos: continue
                translated_pos = self.translated_positions[pos_label]
                exp_positions.append(translated_pos)
            for rack in racks:
                for tube in rack.containers:
                    pos_label = tube.location.position.label
                    if not pos_label in exp_positions:
                        self.assert_is_none(tube.sample)
                        continue
                    self._compare_sample_volume(tube.sample, exp_volume)

    def __check_pool_stock_rack(self, updated_iso):
        indices = []
        for issr in updated_iso.iso_sample_stock_racks:
            sector_index = issr.sector_index
            indices.append(sector_index)
            sector_labels = self.pos_sectors[sector_index]
            exp_positions = dict()
            for label in sector_labels:
                if label in self.missing_lib_pos: continue
                translated_label = self.translated_positions[label]
                exp_positions[translated_label] = label
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
                    self.assert_equal(target_rack,
                                self.pool_stock_rack_barcodes[sector_index])
                self.assert_equal(sorted(wl_labels),
                                  sorted(exp_positions.keys()))
            # check rack
            rack = issr.rack
            self.assert_equal(rack.status.name, ITEM_STATUS_NAMES.MANAGED)
            self.assert_equal(len(rack.containers), len(exp_positions))
            conc = round((POOL_STOCK_RACK_CONCENTRATION / 3.), 2)
            exp_volume = POOL_STOCK_RACK_VOLUME \
                         - get_source_plate_transfer_volume()
            found_labels = []
            for tube in rack.containers:
                pos_label = tube.location.position.label
                found_labels.append(pos_label)
                self.assert_true(exp_positions.has_key(pos_label))
                label_384 = exp_positions[pos_label]
                pos_data = self.pos_data[label_384]
                pool_id = pos_data[0]
                pool = self.pool_map[pool_id + self.pool_id_modifier]
                self._compare_sample_and_pool(tube.sample, pool, conc)
                self._compare_sample_volume(tube.sample, exp_volume)
            self.assert_equal(sorted(found_labels),
                              sorted(exp_positions.keys()))
        self.assert_equal(sorted(indices), sorted(self.pos_sectors.keys()))

    def __check_preparation_plates(self, updated_iso):
        indices = []
        exp_volume = round(PREPARATION_PLATE_VOLUME \
                     - (STARTING_NUMBER_ALIQUOTS * ALIQUOT_PLATE_VOLUME), 1)
        # the calculated concencentration would be 420
        # due to pipetting step size we end up with 423.4
        conc = round((PREPARATION_PLATE_CONCENTRATION / 3.), 2)
        for lsp in updated_iso.library_source_plates:
            sector_index = lsp.sector_index
            indices.append(sector_index)
            sector_labels = self.pos_sectors[sector_index]
            exp_positions = dict()
            for label in sector_labels:
                if label in self.missing_lib_pos: continue
                translated_label = self.translated_positions[label]
                exp_positions[translated_label] = label
            plate = lsp.plate
            self.assert_equal(plate.status.name, ITEM_STATUS_NAMES.MANAGED)
            found_labels = []
            for well in plate.containers:
                pos_label = well.location.position.label
                if not exp_positions.has_key(pos_label):
                    self.assert_is_none(well.sample)
                    continue
                found_labels.append(pos_label)
                label_384 = exp_positions[pos_label]
                pos_data = self.pos_data[label_384]
                pool_id = pos_data[0]
                pool = self.pool_map[pool_id + self.pool_id_modifier]
                self._compare_sample_and_pool(well.sample, pool)
                for sm in well.sample.sample_molecules:
                    sm_conc = sm.concentration * CONCENTRATION_CONVERSION_FACTOR
                    diff = sm_conc - conc
                    self.assert_true(diff < 5)
                    self.assert_true(diff > -5)
                self._compare_sample_volume(well.sample, exp_volume)
            self.assert_equal(sorted(found_labels),
                              sorted(exp_positions.keys()))

    def __check_aliquot_plates(self, updated_isos):
        # the calculated concencentration would be 420
        # due to pipetting step size we end up with 423.4
        self.assert_equal(len(updated_isos.iso_aliquot_plates), 8)
        conc = round((ALIQUOT_PLATE_CONCENTRATION / 3.), 2)
        exp_volume = ALIQUOT_PLATE_VOLUME
        for iap in updated_isos.iso_aliquot_plates:
            plate = iap.plate
            self.assert_equal(plate.status.name, ITEM_STATUS_NAMES.MANAGED)
            found_positions = []
            for well in plate.containers:
                rack_pos = well.location.position
                label = rack_pos.label
                if not self.pos_data.has_key(label) or \
                                                label in self.missing_lib_pos:
                    self.assert_is_none(well.sample)
                    continue
                found_positions.append(rack_pos)
                pos_data = self.pos_data[label]
                pool_id = pos_data[0]
                pool = self.pool_map[pool_id + self.pool_id_modifier]
                self._compare_sample_and_pool(well.sample, pool)
                for sm in well.sample.sample_molecules:
                    sm_conc = sm.concentration * CONCENTRATION_CONVERSION_FACTOR
                    diff = sm_conc - conc
                    self.assert_true(diff < 5)
                    self.assert_true(diff > -5)
                self._compare_sample_volume(well.sample, exp_volume)
            self._compare_pos_sets(self.library_layout.get_positions(),
                                   found_positions)

    def test_result(self):
        self._continue_setup()
        self.__check_result()

    def test_result_missing_position(self):
        self.missing_lib_pos = ['B4']
        self._continue_setup()
        self.__check_result()

    def test_invalid_input_values(self):
        self._continue_setup()
        eu = self.executor_user
        self.executor_user = None
        self._test_and_expect_errors('The user must be a User object')
        self.executor_user = eu
        self.library_iso.status = 'invalid'
        self._test_and_expect_errors('Unexpected ISO status: "invalid"')
        self.library_iso = None
        self._test_and_expect_errors('The library creation ISO must be a ' \
                                     'LibraryCreationIso object')

    def test_libary_layout_converion_error(self):
        self._continue_setup()
        self.library_iso.rack_layout = RackLayout()
        self._test_and_expect_errors('Error when trying to convert ' \
                                     'library layout.')

    def test_rack_not_found(self):
        self._continue_setup()
        writer_cls = LibraryCreationWorklistWriter
        for issr in self.library_iso.iso_sample_stock_racks:
            worklist = issr.planned_worklist
            new_label = writer_cls.SAMPLE_STOCK_WORKLIST_LABEL \
                + writer_cls.SAMPLE_STOCK_WORKLIST_DELIMITER.join(
                                        ['09888501', '09888502', '09888503'])
            worklist.label = new_label
            break
        self._test_and_expect_errors('The following single molecule design ' \
                    'source stock racks have not been found in the DB: ' \
                    '09888501, 09888502, 09888503')

    def test_no_verification(self):
        self._continue_setup()
        rack_pos = get_rack_position_from_label('B4')
        self.library_layout.del_position(rack_pos)
        self.library_iso.rack_layout = self.library_layout.create_rack_layout()
        self._test_and_expect_errors('The stock racks with the single ' \
                  'molecule designs are not compatible to the expected layout')

    def test_buffer_job_creation_failure(self):
        self._continue_setup()
        self.library.iso_request.worklist_series = None
        self._test_and_expect_errors('Unable to get buffer transfer jobs!')

    def test_missing_preparation_jobs_worklist(self):
        self._continue_setup()
        for worklist in self.library.iso_request.worklist_series:
            if 'stock_to_prep' in worklist.label:
                worklist.label = 'invalid'
                break
        self._test_and_expect_errors('Unable to find worklist for the ' \
                'transfer from pool stock racks to library source ' \
                '(prepraration) plates.')

    def test_invalid_preparation_jobs_worklist(self):
        self._continue_setup()
        for worklist in self.library.iso_request.worklist_series:
            if 'stock_to_prep' in worklist.label:
                prt = PlannedRackTransfer(volume=1,
                        source_sector_index=0, target_sector_index=1,
                        sector_number=4)
                worklist.planned_transfers.append(prt)
                break
        self._test_and_expect_errors('The worklist for the transfer from ' \
                 'pool stock rack preparation plate has an unexpected length')

    def test_missing_aliquot_plate_worklist(self):
        self._continue_setup()
        for worklist in self.library.iso_request.worklist_series:
            if 'prep_to_aliquot' in worklist.label:
                worklist.label = 'invalid'
                break
        self._test_and_expect_errors('Unable to find worklist for the ' \
                                     'transfer to the aliquot plates.')

    def test_series_execution_error(self):
        self.starting_volume = 5 / VOLUME_CONVERSION_FACTOR
        self._continue_setup()
        self._test_and_expect_errors('Error during serial transfer execution.')


class LibraryCreationStockRackVerifierTestCase(
                                    LibraryCreationExecutorBaseTestCase):

    def _create_tool(self):
        self.tool = LibraryCreationStockRackVerifier(
                            library_layout=self.library_layout,
                            stock_racks=self.single_stock_racks,
                            log=TestingLog())

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
        ll = self.library_layout
        self.library_layout = None
        self._test_and_expect_errors('The library layout must be a ' \
                                     'LibraryLayout')
        self.library_layout = ll
        self.single_stock_racks = []
        self._test_and_expect_errors('The stock rack map must be a dict')
        self.single_stock_racks = {'1' : []}
        self._test_and_expect_errors('The sector index must be a int')
        self.single_stock_racks = {1 : 2}
        self._test_and_expect_errors('The rack list must be a list')

    def test_missing_tube(self):
        self._continue_setup()
        md = self._get_entity(IMoleculeDesign, '1001')
        pool_stock_conc = get_default_stock_concentration(MOLECULE_TYPE, 3) \
                          / CONCENTRATION_CONVERSION_FACTOR
        new_pool = MoleculeDesignPool(molecule_designs=set([md]),
                            default_stock_concentration=pool_stock_conc)
        new_pool.id = -1
        new_rack_pos = get_rack_position_from_label('A1')
        new_lib_pos = LibraryPosition(rack_position=new_rack_pos,
                              pool=new_pool,
                              stock_tube_barcodes=['invalid'])
        self.library_layout.add_position(new_lib_pos)
        self._test_and_expect_failure('There are some molecule designs ' \
                        'missing in the prepared stock racks for sector 1')

    def test_additional_tubes(self):
        self._continue_setup()
        rack_pos = get_rack_position_from_label('B4')
        self.library_layout.del_position(rack_pos)
        self._test_and_expect_failure('The stock racks for sector 4 contain ' \
                                    'molecule designs that should not be there')

    def test_mismatching_tubes(self):
        self._continue_setup()
        b4_pos = get_rack_position_from_label('B4')
        d2_pos = get_rack_position_from_label('D2')
        lp_b4 = self.library_layout.get_working_position(b4_pos)
        lp_d2 = self.library_layout.get_working_position(d2_pos)
        b4_pool = lp_b4.pool
        d2_pool = lp_d2.pool
        lp_b4.pool = d2_pool
        lp_d2.pool = b4_pool
        self._test_and_expect_failure('Some molecule designs in the stock ' \
                            'racks or sector 4 do not match the expected ones')
