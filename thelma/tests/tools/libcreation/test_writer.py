#"""
#Tests for classes involved in library worklist writing
#
#AAB
#"""
#from everest.entities.utils import get_root_aggregate
#from everest.repositories.rdb.testing import RdbContextManager
#from pkg_resources import resource_filename # pylint: disable=E0611,F0401
#from thelma.automation.tools.libcreation.base \
#    import PREPARATION_PLATE_CONCENTRATION
#from thelma.automation.tools.libcreation.base \
#import MOLECULE_DESIGN_TRANSFER_VOLUME
#from thelma.automation.tools.libcreation.base import ALIQUOT_PLATE_CONCENTRATION
#from thelma.automation.tools.libcreation.base import ALIQUOT_PLATE_VOLUME
#from thelma.automation.tools.libcreation.base import LibraryBaseLayout
#from thelma.automation.tools.libcreation.base import LibraryBaseLayoutPosition
#from thelma.automation.tools.libcreation.base import LibraryLayout
#from thelma.automation.tools.libcreation.base import LibraryLayoutConverter
#from thelma.automation.tools.libcreation.base import LibraryPosition
#from thelma.automation.tools.libcreation.base import MOLECULE_TYPE
#from thelma.automation.tools.libcreation.base import NUMBER_MOLECULE_DESIGNS
#from thelma.automation.tools.libcreation.base import STARTING_NUMBER_ALIQUOTS
#from thelma.automation.tools.libcreation.generation \
#    import LibraryCreationWorklistGenerator
#from thelma.automation.tools.libcreation.generation import LibraryGenerator
#from thelma.automation.tools.libcreation.iso import LibraryCreationIsoPopulator
#from thelma.automation.tools.libcreation.writer \
#    import LibraryCreationCyBioOverviewWriter
#from thelma.automation.tools.libcreation.writer \
#    import LibraryCreationWorklistWriter
#from thelma.automation.tools.libcreation.writer \
#    import LibraryCreationXL20ReportWriter
#from thelma.automation.tools.semiconstants import get_384_rack_shape
#from thelma.automation.tools.semiconstants import get_item_status_future
#from thelma.automation.tools.semiconstants import get_item_status_managed
#from thelma.automation.tools.semiconstants import get_rack_position_from_label
#from thelma.automation.tools.stock.base import get_default_stock_concentration
#from thelma.automation.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
#from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
#from thelma.automation.tools.worklists.tubehandler import TubeTransferData
#from thelma.automation.tools.worklists.tubehandler import XL20WorklistWriter
#from thelma.automation.tools.writers import LINEBREAK_CHAR
#from thelma.interfaces import IMoleculeDesign
#from thelma.interfaces import IMoleculeDesignPool
#from thelma.interfaces import IMoleculeType
#from thelma.interfaces import IPlateSpecs
#from thelma.interfaces import ITube
#from thelma.interfaces import ITubeRack
#from thelma.interfaces import ITubeRackSpecs
#from thelma.interfaces import ITubeSpecs
#from thelma.models.container import ContainerLocation
#from thelma.models.container import Tube
#from thelma.models.iso import ISO_STATUS
#from thelma.models.iso import IsoAliquotPlate
#from thelma.models.iso import IsoRequest
#from thelma.models.library import LibraryCreationIso
#from thelma.models.library import LibrarySourcePlate
#from thelma.models.library import MoleculeDesignLibrary
#from thelma.models.liquidtransfer import TRANSFER_TYPES
#from thelma.models.moleculedesign import MoleculeDesignPool
#from thelma.models.moleculedesign import MoleculeDesignPoolSet
#from thelma.models.racklayout import RackLayout
#from thelma.models.sample import Sample
#from thelma.models.utils import get_user
#from thelma.tests.tools.tooltestingutils import FileCreatorTestCase
#from thelma.tests.tools.tooltestingutils import SilentLog
#from thelma.tests.tools.tooltestingutils import TestingLog
#
#
#class LibraryCreationWriterTestCase(FileCreatorTestCase):
#
#    def set_up(self):
#        FileCreatorTestCase.set_up(self)
#        self.libname = 'testlib'
#        self.log = TestingLog()
#        self.library_creation_iso = None
#        self.layout_number = 4
#        self.iso_label = '%s-%i' % (self.libname, self.layout_number)
#        self.library = None
#        self.iso_request = None
#        self.pool_stock_rack_barcodes = {0 : '09990000', 1 : '09990001',
#                                         2 : '09990002', 3 : '09990003'}
#        self.pool_stock_racks = dict()
#        self.tube_destination_racks = {
#                        0 : ['09888101', '09888102', '09888103'],
#                        1 : ['09888201', '09888202', '09888203'],
#                        2 : ['09888301', '09888302', '09888303'],
#                        3 : ['09888401', '09888402', '09888403']}
#        self.plate_specs = self._get_entity(IPlateSpecs)
#        self.status = get_item_status_future()
#        self.WL_PATH = 'thelma:tests/tools/libcreation/writer/'
#        self.pos_sectors = {0 : ['C3', 'C5'],
#                            1 : ['C2', 'C4'],
#                            2 : ['B5'],
#                            3 : ['B4']}
#        # label - pool ID, stock tube barcodes
#        self.pos_data = dict(
#                C3=[900000001, ['10101', '10102', '10103']],
#                C5=[900000002, ['10201', '10202', '10203']],
#                C2=[900000003, ['10301', '10302', '10303']],
#                C4=[900000004, ['10401', '10402', '10403']],
#                B5=[900000005, ['10501', '10502', '10503']],
#                B4=[900000006, ['10601', '10602', '10603']])
#        self.tube_src_positions = {
#                '10101': 'A1', '10102' : 'A2', '10103' : 'A3',
#                '10201': 'B1', '10202' : 'B2', '10203' : 'B3',
#                '10301': 'C1', '10302' : 'C2', '10303' : 'C3',
#                '10401': 'D1', '10402' : 'D2', '10403' : 'D3',
#                '10501': 'E1', '10502' : 'E2', '10503' : 'E3',
#                '10601': 'F1', '10602' : 'F2', '10603' : 'F3'}
#
#        # pool ID - md IDs
#        self.md_map = {900000001 : [11, 12, 13], 900000002 : [14, 15, 16],
#                       900000003 : [17, 18, 19], 900000004 : [20, 21, 22],
#                       900000005 : [23, 24, 25], 900000006 : [26, 27, 28]}
#        self.prep_plate_barcodes = {0 : '09955001', 1 : '09955002',
#                                    2 : '09955003', 3 : '09955004'}
#        self.base_layout = None
#        self.library_layout = None
#        self.worklist_series = None
#        self.user = get_user('it')
#        self.stock_conc = get_default_stock_concentration(MOLECULE_TYPE)
#        self.add_rack_to_agg = False
#        self.create_pool_stock_racks = False
#        self.source_rack_barcode = '09777777'
#
#    def tear_down(self):
#        FileCreatorTestCase.tear_down(self)
#        del self.log
#        del self.library_creation_iso
#        del self.layout_number
#        del self.iso_label
#        del self.library
#        del self.iso_request
#        del self.pool_stock_rack_barcodes
#        del self.pool_stock_racks
#        del self.tube_destination_racks
#        del self.plate_specs
#        del self.status
#        del self.pos_sectors
#        del self.pos_data
#        del self.tube_src_positions
#        del self.md_map
#        del self.prep_plate_barcodes
#        del self.base_layout
#        del self.library_layout
#        del self.worklist_series
#        del self.stock_conc
#        del self.add_rack_to_agg
#        del self.create_pool_stock_racks
#        del self.source_rack_barcode
#
#    def _continue_setup(self):
#        self._create_layouts()
#        self.__create_worklist_series()
#        self._create_library_iso_request()
#        self._create_test_library()
#        self._create_library_iso()
#        self._create_library_source_plates()
#        self._create_aliquot_plates()
#        if self.create_pool_stock_racks: self._create_sample_stock_racks()
#        if self.add_rack_to_agg: self.__create_tube_racks()
#        self._create_tool()
#
#    def _create_layouts(self):
#        pool_agg = get_root_aggregate(IMoleculeDesignPool)
#        shape = get_384_rack_shape()
#        self.library_layout = LibraryLayout(shape=shape)
#        self.base_layout = LibraryBaseLayout(shape=shape)
#        pool_stock_conc = get_default_stock_concentration(MOLECULE_TYPE, 3) \
#                     / CONCENTRATION_CONVERSION_FACTOR
#        for pos_label, pos_data in self.pos_data.iteritems():
#            rack_pos = get_rack_position_from_label(pos_label)
#            base_pos = LibraryBaseLayoutPosition(rack_position=rack_pos)
#            self.base_layout.add_position(base_pos)
#            pool_id = pos_data[0]
#            md_ids = self.md_map[pool_id]
#            mds = []
#            for md_id in md_ids:
#                md = self._get_entity(IMoleculeDesign, str(md_id))
#                mds.append(md)
#            pool = MoleculeDesignPool(molecule_designs=set(mds),
#                                default_stock_concentration=pool_stock_conc)
#            pool.id = pool_id
#            pool_agg.add(pool)
#            self.pool_map[pool_id] = pool
#            lib_pos = LibraryPosition(rack_position=rack_pos, pool=pool,
#                                      stock_tube_barcodes=pos_data[1])
#            self.library_layout.add_position(lib_pos)
#
#    def __create_worklist_series(self):
#        generator = LibraryCreationWorklistGenerator(log=self.log,
#                            base_layout=self.base_layout,
#                            stock_concentration=self.stock_conc,
#                            library_name=self.libname)
#        self.worklist_series = generator.get_result()
#
#    def _create_library_iso_request(self):
#        self.iso_request = IsoRequest(requester=self.user,
#                        iso_layout=self.base_layout.create_rack_layout(),
#                        number_plates=3,
#                        number_aliquots=STARTING_NUMBER_ALIQUOTS,
#                        plate_set_label=self.libname,
#                        worklist_series=self.worklist_series)
#
#    def _create_test_library(self):
#        md_type = self._get_entity(IMoleculeType, MOLECULE_TYPE)
#        pool_set = MoleculeDesignPoolSet(molecule_type=md_type,
#                                         molecule_design_pools=
#                                                set(self.pool_map.values()))
#        self.library = \
#                MoleculeDesignLibrary(molecule_design_pool_set=pool_set,
#                  label=self.libname, iso_request=self.iso_request,
#                  final_volume=ALIQUOT_PLATE_VOLUME / VOLUME_CONVERSION_FACTOR,
#                  final_concentration=ALIQUOT_PLATE_CONCENTRATION \
#                                      / CONCENTRATION_CONVERSION_FACTOR)
#
#    def _create_library_iso(self):
#        self.library_creation_iso = LibraryCreationIso(ticket_number=14,
#                        layout_number=self.layout_number, label='testlib-4',
#                        rack_layout=self.library_layout.create_rack_layout(),
#                        iso_request=self.iso_request)
#
#    def _create_sample_stock_racks(self):
#        tube_rack_specs = self._get_entity(ITubeRackSpecs)
#        for sector_index, barcode in self.pool_stock_rack_barcodes.iteritems():
#            label = 'pool_stock_rack_Q%i' % (sector_index + 1)
#            rack = tube_rack_specs.create_rack(label=label,
#                                               status=get_item_status_managed())
#            rack.barcode = barcode
#            self.pool_stock_racks[sector_index] = rack
#
#    def _create_library_source_plates(self):
#        populator = LibraryCreationIsoPopulator
#        for sector_index, barcode in self.prep_plate_barcodes.iteritems():
#            label = populator.PREP_PLATE_LABEL_PATTERN % (self.libname,
#                            self.layout_number, PREPARATION_PLATE_CONCENTRATION,
#                            sector_index + 1)
#            plate = self.plate_specs.create_rack(status=self.status,
#                                                 label=label)
#            plate.barcode = barcode
#            LibrarySourcePlate(iso=self.library_creation_iso,
#                               plate=plate, sector_index=sector_index)
#
#    def _create_aliquot_plates(self):
#        populator = LibraryCreationIsoPopulator
#        for i in range(STARTING_NUMBER_ALIQUOTS):
#            label = populator.ALIQUOT_PLATE_LABEL_PATTERN % (self.libname,
#                            self.layout_number, ALIQUOT_PLATE_CONCENTRATION,
#                            i + 1)
#            plate = self.plate_specs.create_rack(status=self.status,
#                                                 label=label)
#            plate.barcode = '0994400%i' % (i)
#            IsoAliquotPlate(iso=self.library_creation_iso, plate=plate)
#
#    def __create_tube_racks(self):
#        rack_agg = get_root_aggregate(ITubeRack)
#        tube_agg = get_root_aggregate(ITube)
#        tube_rack_specs = self._get_entity(ITubeRackSpecs)
#        tube_specs = self._get_entity(ITubeSpecs)
#        status = get_item_status_managed()
#        rack_counter = -1
#        # tube destination racks (tube transfer targets)
#        for sector_index in sorted(self.tube_destination_racks.keys()):
#            barcodes = sorted(self.tube_destination_racks[sector_index])
#            for barcode in barcodes:
#                tube_rack = tube_rack_specs.create_rack(status=status,
#                                                        label=barcode)
#                tube_rack.barcode = barcode
#                tube_rack.id = rack_counter
#                rack_counter -= 1
#                rack_agg.add(tube_rack)
#        # pool stock racks
#        tube_counter = 0
#        for sector_index in sorted(self.pool_stock_rack_barcodes.keys()):
#            barcode = self.pool_stock_rack_barcodes[sector_index]
#            tube_rack = tube_rack_specs.create_rack(status=status,
#                                                    label=barcode)
#            tube_rack.barcode = barcode
#            tube_rack.id = rack_counter
#            rack_counter -= 1
#            for pos_label in self.pos_sectors[sector_index]:
#                rack_pos = get_rack_position_from_label(pos_label)
#                tube_barcodes = '1%04i' % (tube_counter)
#                tube_counter += 1
#                for tube_barcode in tube_barcodes:
#                    tube = tube_specs.create_tube(item_status=status,
#                                    location=None, barcode=tube_barcode)
#                    ContainerLocation(container=tube, rack=tube_rack,
#                                      position=rack_pos)
#            rack_agg.add(tube_rack)
#        # tube transfer source rack
#        source_rack = tube_rack_specs.create_rack(status=status,
#                                            label='tt source rack')
#        source_rack.barcode = self.source_rack_barcode
#        for tube_barcode, pos_label in self.tube_src_positions.iteritems():
#            rack_pos = get_rack_position_from_label(pos_label)
#            tube = tube_specs.create_tube(item_status=status, location=None,
#                                          barcode=tube_barcode)
#            ContainerLocation(container=tube, rack=source_rack,
#                              position=rack_pos)
#            tube_agg.add(tube)
#        rack_agg.add(source_rack)
#
#
#class LibraryCreationXL20ReportWriterTestCase(LibraryCreationWriterTestCase):
#
#    def set_up(self):
#        LibraryCreationWriterTestCase.set_up(self)
#        self.tube_transfers = []
#        self.__create_tube_transfers()
#        self.sector_index = 2
#        self.rack_locations = {'09999999' : 'freezer1 (shelf 2)',
#                               '09999998' : None}
#        self.txt_file = 'xl20report.txt'
#
#    def tear_down(self):
#        LibraryCreationWriterTestCase.tear_down(self)
#        del self.tube_transfers
#        del self.rack_locations
#        del self.sector_index
#        del self.txt_file
#
#    def __create_tube_transfers(self):
#        tt_data = [['1001', '09999999', 'A1', '09000000', 'A1'],
#                   ['1003', '09999999', 'B1', '09000000', 'B2'],
#                   ['1009', '09999998', 'A1', '09000000', 'C3'],
#                   ['1010', '09999998', 'B1', '09000001', 'A1']]
#        for data_list in tt_data:
#            tt = TubeTransferData(tube_barcode=data_list[0],
#                              src_rack_barcode=data_list[1],
#                              src_pos=get_rack_position_from_label(data_list[2]),
#                              trg_rack_barcode=data_list[3],
#                              trg_pos=get_rack_position_from_label(data_list[4]))
#            self.tube_transfers.append(tt)
#
#    def _create_tool(self):
#        self.tool = LibraryCreationXL20ReportWriter(log=self.log,
#                            tube_transfers=self.tube_transfers,
#                            library_name=self.libname,
#                            layout_number=self.layout_number,
#                            sector_index=self.sector_index,
#                            source_rack_locations=self.rack_locations)
#
#    def test_result(self):
#        self._create_tool()
#        tool_stream = self.tool.get_result()
#        self.assert_is_not_none(tool_stream)
#        self._compare_txt_file_stream(tool_stream, self.txt_file,
#                                      ignore_lines=[0])
#
#    def test_invalid_input_value(self):
#        self.tube_transfers = dict()
#        self._test_and_expect_errors('The tube transfer list must be a list')
#        self.tube_transfers = [1]
#        self._test_and_expect_errors('The tube transfer must be a ' \
#                                     'TubeTransferData')
#        self.tube_transfers = []
#        self.__create_tube_transfers()
#        self.libname = 13
#        self._test_and_expect_errors('The library name must be a basestring')
#        self.libname = 'testlib'
#        self.layout_number = '4'
#        self._test_and_expect_errors('The layout number must be a int')
#        self.layout_number = 4
#        self.sector_index = 1.3
#        self._test_and_expect_errors('The sector index must be a int')
#        self.sector_index = 2
#        self.rack_locations = []
#        self._test_and_expect_errors('The rack location map must be a dict')
#
#
#
#
#
#
#class LibraryCreationCyBioOverviewWriterTestCase(LibraryCreationWriterTestCase):
#
#    def set_up(self):
#        LibraryCreationWriterTestCase.set_up(self)
#        self.txt_file = 'overview.txt'
#
#    def tear_down(self):
#        LibraryCreationWriterTestCase.tear_down(self)
#        del self.txt_file
#
#    def _create_tool(self):
#        self.tool = LibraryCreationCyBioOverviewWriter(log=self.log,
#                            library_creation_iso=self.library_creation_iso,
#                            pool_stock_racks=self.pool_stock_rack_barcodes,
#                            tube_destination_racks=self.tube_destination_racks)
#
#    def test_result(self):
#        self._continue_setup()
#        tool_stream = self.tool.get_result()
#        self.assert_is_not_none(tool_stream)
#        self._compare_txt_file_stream(tool_stream, self.txt_file)
#
#    def test_invalid_input_values(self):
#        self._continue_setup()
#        self.library_creation_iso.status = 'invalid'
#        self._test_and_expect_errors('Unexpected ISO status: "invalid"')
#        self.library_creation_iso.status = ISO_STATUS.QUEUED
#        lci = self.library_creation_iso
#        self.library_creation_iso = None
#        self._test_and_expect_errors('The library creation ISO must be a ' \
#                                     'LibraryCreationIso object')
#        self.library_creation_iso = lci
#        self.pool_stock_rack_barcodes = []
#        self._test_and_expect_errors('The pool stock rack map must be a dict')
#        self.pool_stock_rack_barcodes = {1 : 1}
#        self._test_and_expect_errors('The barcode in the pool stock rack map ' \
#                                     'must be a basestring')
#        self.pool_stock_rack_barcodes = {'2' : '2'}
#        self._test_and_expect_errors('The sector index in the pool stock ' \
#                                     'rack map must be a int')
#        self.pool_stock_rack_barcodes = {}
#        self._test_and_expect_errors('There are no barcodes in the pool ' \
#                                     'stock rack map!')
#        self.pool_stock_rack_barcodes = {1 : '1'}
#        self.tube_destination_racks = []
#        self._test_and_expect_errors('The tube destination rack map must be ' \
#                                     'a dict')
#        self.tube_destination_racks = {1 : 1}
#        self._test_and_expect_errors('The barcode list in the tube ' \
#                                     'destination map must be a list')
#        self.tube_destination_racks = {'1' : '1'}
#        self._test_and_expect_errors('The sector index in the tube ' \
#                                     'destination map must be a int')
#        self.tube_destination_racks = {}
#        self._test_and_expect_errors('There are no barcodes in the ' \
#                                     'destination rack map!')
#
#
#class LibraryCreationWorklistWriterBaseTestCase(FileCreatorTestCase):
#    """
#    This is a base test case that is used both by the actual writer and
#    the trac tool uploading its content.
#    """
#
#    def set_up(self):
#        FileCreatorTestCase.set_up(self)
#        self.library = None
#        self.libname = 'testlib'
#        self.library_iso = None
#        self.number_isos = 1
#        self.pos_sectors = {0 : ['C3', 'C5', 'E3', 'E5'],
#                            1 : ['C2', 'C4', 'E2', 'E4'],
#                            2 : ['B5', 'D3'],
#                            3 : ['B4', 'D2']}
#        # 384 pos - 96 pos
#        self.translated_positions = dict(
#                            C3='B2', C5='B3', E3='C2', E5='C3',
#                            C2='B1', C4='B2', E2='C1', E4='C2',
#                            B5='A3', D3='B2',
#                            B4='A2', D2='B1')
#        self.stream = None
#        self.requester = get_user('sachse')
#        self.WL_PATH = 'thelma:tests/tools/libcreation/writer/'
#        self.valid_file = 'valid_file.xls'
#        self.pool_stock_rack_barcodes = {0 : '09990000', 1 : '09990001',
#                                         2 : '09990002', 3 : '09990003'}
#        self.tube_destination_racks = {
#                        0 : ['09888101', '09888102', '09888103'],
#                        1 : ['09888201', '09888202', '09888203'],
#                        2 : ['09888301', '09888302', '09888303'],
#                        3 : ['09888401', '09888402', '09888403']}
#        self.pool_stock_racks = dict()
#        self.prep_plate_barcodes = {0 : '09955001', 1 : '09955002',
#                                    2 : '09955003', 3 : '09955004'}
#        self.aliquot_barcode_pattern = '0994400%i'
#
#    def tear_down(self):
#        FileCreatorTestCase.tear_down(self)
#        del self.library
#        del self.libname
#        del self.library_iso
#        del self.number_isos
#        del self.pos_sectors
#        del self.stream
#        del self.requester
#        del self.valid_file
#        del self.pool_stock_rack_barcodes
#        del self.pool_stock_racks
#        del self.tube_destination_racks
#        del self.prep_plate_barcodes
#        del self.aliquot_barcode_pattern
#
#    def _continue_setup(self, session):
#        self.__read_file()
#        self.__create_library()
#        self.__add_pool_ids(session)
#        self._create_isos()
#        self.__populate_iso()
#        self.__create_racks(session)
#        self._create_tool()
#
#    def __read_file(self):
#        fn = self.WL_PATH + self.valid_file
#        f = resource_filename(*fn.split(':'))
#        stream = open(f, 'rb')
#        self.stream = stream.read()
#
#    def __create_library(self):
#        generator = LibraryGenerator(library_name=self.libname,
#                                     stream=self.stream,
#                                     requester=self.requester,
#                                     logging_level=30)
#        self.library = generator.get_result()
#
#    def __add_pool_ids(self, session):
#        # since we do not persist anything the new stock sample pools do not
#        # have IDs yet
#        last_id = 99999999
#        for md_pool in self.library.molecule_design_pool_set:
#            if md_pool.id is None:
#                md_pool.id = last_id
#                last_id += 1
#                session.add(md_pool)
#        session.commit()
#
#    def _create_isos(self):
#        raise NotImplementedError('Abstract method')
#
#    def __populate_iso(self):
#        populator = LibraryCreationIsoPopulator(
#                                molecule_design_library=self.library,
#                                number_isos=self.number_isos)
#        isos = populator.get_result()
#        self.assert_is_not_none(isos)
#        self.library_iso = isos[0]
#        for lsp in self.library_iso.library_source_plates:
#            barcode = self.prep_plate_barcodes[lsp.sector_index]
#            lsp.plate.barcode = barcode
#        for iap in self.library_iso.iso_aliquot_plates:
#            label = iap.plate.label
#            num = int(label[-1]) - 1
#            barcode = self.aliquot_barcode_pattern % (num)
#            iap.plate.barcode = barcode
#
#    def __create_racks(self, session):
#        tube_rack_specs = self._get_entity(ITubeRackSpecs)
#        tube_specs = self._get_entity(ITubeSpecs)
#        status = get_item_status_managed()
#        rack_counter = -1
#        # tube destination racks (tube transfer targets)
#        for sector_index in sorted(self.tube_destination_racks.keys()):
#            barcodes = sorted(self.tube_destination_racks[sector_index])
#            for barcode in barcodes:
#                tube_rack = tube_rack_specs.create_rack(status=status,
#                                                        label=barcode)
#                tube_rack.barcode = barcode
#                tube_rack.id = rack_counter
#                rack_counter -= 1
#                session.add(tube_rack)
#        # pool stock racks
#        tube_counter = 0
#        for sector_index in sorted(self.pool_stock_rack_barcodes.keys()):
#            barcode = self.pool_stock_rack_barcodes[sector_index]
#            tube_rack = tube_rack_specs.create_rack(status=status,
#                                                    label=barcode)
#            tube_rack.barcode = barcode
#            tube_rack.id = rack_counter
#            rack_counter -= 1
#            labels = self.pos_sectors[sector_index]
#            for pos_label in labels:
#                translated_pos = self.translated_positions[pos_label]
#                rack_pos = get_rack_position_from_label(translated_pos)
#                tube_barcode = '1%04i' % (tube_counter)
#                tube_counter += 1
#                tube = Tube.create_from_rack_and_position(specs=tube_specs,
#                                        status=status, rack=tube_rack,
#                                        position=rack_pos, barcode=tube_barcode)
#                session.add(tube)
#            session.add(tube_rack)
#            session.commit()
#            self.assert_equal(len(tube_rack.containers), len(labels))
#
#
#class LibraryCreationWorklistWriterTestCase(
#                                LibraryCreationWorklistWriterBaseTestCase):
#
#    def _create_tool(self):
#        self.tool = LibraryCreationWorklistWriter(
#                            library_creation_iso=self.library_iso,
#                            tube_destination_racks=self.tube_destination_racks,
#                            pool_stock_racks=self.pool_stock_rack_barcodes)
#
#    def _create_isos(self):
#        iso_request = self.library.iso_request
#        for i in range(iso_request.number_plates):
#            layout_number = i + 1
#            label = '%s-%i' % (self.libname, layout_number)
#            LibraryCreationIso(ticket_number=i,
#                               layout_number=layout_number,
#                               iso_request=iso_request,
#                               label=label,
#                               rack_layout=RackLayout())
#        self.assert_equal(len(iso_request.isos), iso_request.number_plates)
#
#    def __check_file_map(self, file_map):
#        self.assert_is_not_none(file_map)
#        self.assert_equal(len(file_map), 9)
#        for fn, stream in file_map.iteritems():
#            if 'xl20_worklist' in fn:
#                self.__check_xl20_worklist(fn, stream)
#            elif 'xl20_report' in fn:
#                self.__check_xl20_report(fn, stream)
#            elif 'CyBio_instructions' in fn:
#                self._compare_txt_file_stream(stream, 'all_overview.txt')
#            else:
#                raise ValueError('unknown file: %s' % fn)
#
#    def __check_xl20_worklist(self, file_name, stream):
#        sector_index = int(file_name[-5]) - 1
#        writer = XL20WorklistWriter
#        target_rack_barcodes = set()
#        lines = stream.read().split(LINEBREAK_CHAR)
#        trg_labels = set()
#        for i in range(len(lines)):
#            if i == 0: continue
#            lin = lines[i].strip()
#            if len(lin) < 1: continue
#            tokens = lin.split(writer.DELIMITER)
#            trg_rack = tokens[writer.DEST_RACK_INDEX]
#            target_rack_barcodes.add(trg_rack)
#            trg_label = tokens[writer.DEST_POSITION_INDEX]
#            trg_labels.add(trg_label)
#        trg_barcodes = list(target_rack_barcodes)
#        self.assert_equal(len(trg_barcodes), NUMBER_MOLECULE_DESIGNS)
#        self.assert_equal(sorted(trg_barcodes),
#                          sorted(self.tube_destination_racks[sector_index]))
#        exp_labels = []
#        for pos_label in self.pos_sectors[sector_index]:
#            exp_labels.append(self.translated_positions[pos_label])
#        self.assert_equal(sorted(list(trg_labels)), sorted(exp_labels))
#
#    def __check_xl20_report(self, file_name, tool_stream):
#        sector_index = int(file_name[-5]) - 1
#        writer = LibraryCreationXL20ReportWriter
#        tool_content = tool_stream.read()
#        self.assert_true(self.libname in tool_content)
#        exp_num_tubes = len(self.pos_sectors[sector_index]) \
#                        * NUMBER_MOLECULE_DESIGNS
#        self.assert_true(writer.TUBE_NO_LINE % (exp_num_tubes) in tool_content)
#        self.assert_true(writer.SECTOR_NUMBER_LINE % (sector_index + 1) \
#                         in tool_content)
#        self.assert_true(writer.LAYOUT_NUMBER_LINE % (
#                            self.library_iso.layout_number) in tool_content)
#        exp_racks = self.tube_destination_racks[sector_index]
#        for trg_rck in exp_racks:
#            self.assert_true(trg_rck in tool_content)
#
#    def __check_iso(self):
#        issrs = self.library_iso.iso_sample_stock_racks
#        self.assert_equal(len(issrs), len(self.pos_sectors))
#        exp_volume = MOLECULE_DESIGN_TRANSFER_VOLUME
#        found_sectors = []
#        for issr in issrs:
#            sector_index = issr.sector_index
#            exp_positions = []
#            for pos_label in self.pos_sectors[sector_index]:
#                translated_label = self.translated_positions[pos_label]
#                exp_positions.append(translated_label)
#            found_sectors.append(sector_index)
#            worklist = issr.planned_worklist
#            self.assert_equal(len(worklist.label.split(
#                                self.tool.SAMPLE_STOCK_WORKLIST_DELIMITER)), 3)
#            self.assert_equal(len(worklist.planned_transfers),
#                              len(exp_positions))
#            found_targets = []
#            for pct in worklist.planned_transfers:
#                self.assert_equal(pct.type, TRANSFER_TYPES.CONTAINER_TRANSFER)
#                self._compare_transfer_volume(pct, exp_volume)
#                found_targets.append(pct.target_position.label)
#            self.assert_equal(sorted(found_targets), sorted(exp_positions))
#
#    def test_result(self):
#        with RdbContextManager() as session:
#            self._continue_setup(session)
#            file_map = self.tool.get_result()
#            self.__check_file_map(file_map)
#            self.__check_iso()
#
#    def test_result_empty_floating_positions(self):
#        with RdbContextManager() as session:
#            b4_label = 'B4'
#            self.pos_sectors[3] = ['D2']
#            del self.translated_positions[b4_label]
#            self._continue_setup(session)
#            converter = LibraryLayoutConverter(log=SilentLog(),
#                                    rack_layout=self.library_iso.rack_layout)
#            lib_layout = converter.get_result()
#            pos_384 = get_rack_position_from_label(b4_label)
#            lib_layout.del_position(pos_384)
#            self.library_iso.rack_layout = lib_layout.create_rack_layout()
#            file_map = self.tool.get_result()
#            self.__check_file_map(file_map)
#            self.__check_iso()
#
#    def test_invalid_input_values(self):
#        with RdbContextManager() as session:
#            self._continue_setup(session)
#            lci = self.library_iso
#            self.library_iso.status = 'invalid'
#            self._test_and_expect_errors()
#            self.library_iso = None
#            self._test_and_expect_errors()
#            lci.status = ISO_STATUS.QUEUED
#            self.library_iso = lci
#            self.pool_stock_rack_barcodes = []
#            self._test_and_expect_errors('The pool stock rack map must be a ' \
#                                         'dict')
#            self.pool_stock_rack_barcodes = {1 : 1}
#            self._test_and_expect_errors('The barcode in the pool stock rack ' \
#                                         'map must be a basestring')
#            self.pool_stock_rack_barcodes = {'2' : '2'}
#            self._test_and_expect_errors('The sector index in the pool stock ' \
#                                         'rack map must be a int')
#            self.pool_stock_rack_barcodes = {}
#            self._test_and_expect_errors('There are no barcodes in the pool ' \
#                                         'stock rack map!')
#            self.pool_stock_rack_barcodes = {1 : '1'}
#            self.tube_destination_racks = []
#            self._test_and_expect_errors('The tube destination rack map must ' \
#                                         'be a dict')
#            self.tube_destination_racks = {1 : 1}
#            self._test_and_expect_errors('The barcode list in the tube ' \
#                                         'destination map must be a list')
#            self.tube_destination_racks = {'1' : '1'}
#            self._test_and_expect_errors('The sector index in the tube ' \
#                                         'destination map must be a int')
#            self.tube_destination_racks = {}
#            self._test_and_expect_errors('There are no barcodes in the ' \
#                                         'destination rack map!')
#
#    def test_unknown_rack_barcode(self):
#        with RdbContextManager() as session:
#            self._continue_setup(session)
#            self.pool_stock_rack_barcodes[2] = '0001'
#            self._test_and_expect_errors('The following racks have not been ' \
#                                         'found in the DB')
#
#    def test_library_layout_conversion_failure(self):
#        with RdbContextManager() as session:
#            self._continue_setup(session)
#            self.library_iso.rack_layout = RackLayout()
#            self._test_and_expect_errors('Error when trying to convert ' \
#                                         'library layout')
#
#    def test_invalid_tube_destination_rack(self):
#        with RdbContextManager() as session:
#            self._continue_setup(session)
#            tube_rack_barcode = self.tube_destination_racks[0][0]
#            rack_agg = get_root_aggregate(ITubeRack)
#            rack = rack_agg.get_by_slug(tube_rack_barcode)
#            self.assert_is_not_none(rack)
#            tube_specs = self._get_entity(ITubeSpecs)
#            Tube.create_from_rack_and_position(specs=tube_specs,
#                        status=get_item_status_managed(),
#                        barcode='1222', rack=rack,
#                        position=get_rack_position_from_label('A1'))
#            self._test_and_expect_errors('The following tube destination ' \
#                                         'racks you have chosen are not empty')
#
#    def test_invalid_pool_stock_rack_additional(self):
#        with RdbContextManager() as session:
#            self._continue_setup(session)
#            rack_barcode = self.pool_stock_rack_barcodes[0]
#            rack_agg = get_root_aggregate(ITubeRack)
#            rack = rack_agg.get_by_slug(rack_barcode)
#            self.assert_is_not_none(rack)
#            tube_specs = self._get_entity(ITubeSpecs)
#            Tube.create_from_rack_and_position(specs=tube_specs,
#                        status=get_item_status_managed(),
#                        barcode='1222', rack=rack,
#                        position=get_rack_position_from_label('A1'))
#            file_map = self.tool.get_result()
#            self.__check_file_map(file_map)
#            self.__check_iso()
#            self._check_warning_messages('located in positions that should ' \
#                                         'be empty')
#
#    def test_invalid_pool_stock_rack_not_empty(self):
#        with RdbContextManager() as session:
#            self._continue_setup(session)
#            rack_barcode = self.pool_stock_rack_barcodes[0]
#            rack_agg = get_root_aggregate(ITubeRack)
#            rack = rack_agg.get_by_slug(rack_barcode)
#            self.assert_is_not_none(rack)
#            tube = rack.containers[0]
#            Sample(volume=5, container=tube)
#            self._test_and_expect_errors('are not empty')
#
#    def test_invalid_pool_stock_rack_missing(self):
#        with RdbContextManager() as session:
#            self._continue_setup(session)
#            rack_barcode = self.pool_stock_rack_barcodes[0]
#            rack_agg = get_root_aggregate(ITubeRack)
#            rack = rack_agg.get_by_slug(rack_barcode)
#            self.assert_is_not_none(rack)
#            del rack.containers[0]
#            self._test_and_expect_errors('There are some tubes missing in ' \
#                                         'the pool stock rack for sector 1')
#
#    def test_missing_tubes(self):
#        with RdbContextManager() as session:
#            self._continue_setup(session)
#            converter = LibraryLayoutConverter(log=SilentLog(),
#                                    rack_layout=self.library_iso.rack_layout)
#            lib_layout = converter.get_result()
#            for lib_pos in lib_layout.working_positions():
#                lib_pos.stock_tube_barcodes[0] = '122222'
#                break
#            self.library_iso.rack_layout = lib_layout.create_rack_layout()
#            self._test_and_expect_errors('Could not find tubes for the ' \
#                                         'following tube barcodes: 122222')
