#"""
#Tests for classes involved in library creation ISO population
#
#AAB
#"""
#from everest.entities.utils import get_root_aggregate
#from everest.testing import RdbContextManager
#from pkg_resources import resource_filename # pylint: disable=E0611,F0401
#from thelma.automation.tools.libcreation.base import LibraryBaseLayout
#from thelma.automation.tools.libcreation.base import LibraryBaseLayoutPosition
#from thelma.automation.tools.libcreation.base import LibraryLayoutConverter
#from thelma.automation.tools.libcreation.base import NUMBER_MOLECULE_DESIGNS
#from thelma.automation.tools.libcreation.base import STARTING_NUMBER_ALIQUOTS
#from thelma.automation.tools.libcreation.generation import LibraryGenerator
#from thelma.automation.tools.libcreation.iso import LibraryCreationIsoPopulator
#from thelma.automation.tools.semiconstants import get_384_rack_shape
#from thelma.automation.tools.semiconstants import get_rack_position_from_label
#from thelma.interfaces import IMoleculeDesignPool
#from thelma.models.library import LibraryCreationIso
#from thelma.models.moleculedesign import MoleculeDesignPoolSet
#from thelma.models.racklayout import RackLayout
#from thelma.models.utils import get_user
#from thelma.tests.tools.tooltestingutils import TestingLog
#from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase
#
#
#class LibraryCreationIsoPopulatorTestCase(ToolsAndUtilsTestCase):
#
#    def set_up(self):
#        ToolsAndUtilsTestCase.set_up(self)
#        self.library = None
#        self.number_isos = 2
#        self.excluded_racks = None
#        self.requested_tubes = None
#        self.pos_sectors = {0 : ['C3', 'C5', 'E3', 'E5'],
#                            1 : ['C2', 'C4', 'E2', 'E4'],
#                            2 : ['B5', 'D3'],
#                            3 : ['B4', 'D2']}
#        self.stream = None
#        self.requester = get_user('sachse')
#        self.FILE_PATH = 'thelma:tests/tools/libcreation/iso/'
#        self.valid_file = 'valid_file.xls'
#        self.libname = 'testlib'
#
#    def tear_down(self):
#        ToolsAndUtilsTestCase.tear_down(self)
#        del self.library
#        del self.number_isos
#        del self.excluded_racks
#        del self.requested_tubes
#        del self.pos_sectors
#        del self.stream
#        del self.requester
#        del self.FILE_PATH
#        del self.valid_file
#        del self.libname
#
#    def _create_tool(self):
#        self.tool = LibraryCreationIsoPopulator(number_isos=self.number_isos,
#                                molecule_design_library=self.library,
#                                excluded_racks=self.excluded_racks,
#                                requested_tubes=self.requested_tubes)
#
#    def __continue_setup(self, file_name=None):
#        if file_name is None: file_name = self.valid_file
#        self.__read_file(file_name)
#        self.__create_library()
#        self.__add_pool_ids()
#        self.__create_isos()
#        self._create_tool()
#
#    def __read_file(self, file_name):
#        fn = self.FILE_PATH + file_name
#        f = resource_filename(*fn.split(':'))
#        stream = open(f, 'rb')
#        self.stream = stream.read()
#
#    def __create_library(self):
#        generator = LibraryGenerator(library_name=self.libname,
#                                     stream=self.stream,
#                                     requester=self.requester)
#        self.library = generator.get_result()
#
#    def __add_pool_ids(self):
#        # since we do not persist anything the new stock sampple pools do not
#        # have IDs yet
#        agg = get_root_aggregate(IMoleculeDesignPool)
#        last_id = 99999999
#        for md_pool in self.library.molecule_design_pool_set:
#            if md_pool.id is None:
#                md_pool.id = last_id
#                last_id += 1
#                agg.add(md_pool)
#
#    def __create_isos(self):
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
#    def __check_result(self, exp_layout_numbers=None):
#        if exp_layout_numbers is None:
#            exp_layout_numbers = []
#            for i in range(self.number_isos):
#                exp_layout_numbers.append(i + 1)
#        new_isos = self.tool.get_result()
#        self.assert_is_not_none(new_isos)
#        self.assert_equal(len(new_isos), len(exp_layout_numbers))
#        found_pools = []
#        for lci in new_isos:
#            self.assert_true(isinstance(lci, LibraryCreationIso))
#            layout_number = lci.layout_number
#            exp_label = '%s-%i' % (self.libname, layout_number)
#            self.assert_equal(exp_label, lci.label)
#            self.__check_plates(lci)
#            if not (len(exp_layout_numbers) != self.number_isos and \
#                                    layout_number == max(exp_layout_numbers)):
#                self.__check_layout(lci, found_pools)
#
#    def __check_plates(self, lci):
#        self.assert_equal(len(lci.library_source_plates), len(self.pos_sectors))
#        self.assert_equal(len(lci.iso_aliquot_plates), STARTING_NUMBER_ALIQUOTS)
#        found_indices = []
#        for lsp in lci.library_source_plates:
#            label = lsp.plate.label
#            sector_index = lsp.sector_index
#            self.assert_true(self.libname in label)
#            self.assert_true(str(lci.layout_number) in label)
#            label_index = int(label[-1]) - 1
#            self.assert_equal(sector_index, label_index)
#            found_indices.append(sector_index)
#        self.assert_equal(sorted(found_indices),
#                          sorted(self.pos_sectors.keys()))
#        iap_numbers = []
#        for iap in lci.iso_aliquot_plates:
#            label = iap.plate.label
#            iap_number = int(label[-1])
#            iap_numbers.append(iap_number)
#        self.assert_equal(range(1, STARTING_NUMBER_ALIQUOTS + 1),
#                          sorted(iap_numbers))
#
#    def __check_layout(self, lci, found_pools):
#        converter = LibraryLayoutConverter(rack_layout=lci.rack_layout,
#                                           log=TestingLog())
#        lib_layout = converter.get_result()
#        exp_positions = []
#        for labels in self.pos_sectors.values():
#            for pos_label in labels:
#                rack_pos = get_rack_position_from_label(pos_label)
#                exp_positions.append(rack_pos)
#        self.assert_equal(len(exp_positions), len(lib_layout))
#        self._compare_pos_sets(exp_positions, lib_layout.get_positions())
#        iso_mds = []
#        for lib_pos in lib_layout.working_positions():
#            pool_id = lib_pos.pool.id
#            self.assert_false(pool_id in found_pools)
#            found_pools.append(pool_id)
#            iso_mds.append(pool_id)
#            self.assert_equal(len(lib_pos.stock_tube_barcodes),
#                              NUMBER_MOLECULE_DESIGNS)
#        set_mds = []
#        for md_pool in lci.molecule_design_pool_set:
#            set_mds.append(md_pool.id)
#        self.assert_equal(sorted(set_mds), sorted(iso_mds))
#
#    def __set_excluded_racks(self, pool_id):
#        with RdbContextManager() as session:
#            # get racks to be excluded
#            query = 'SELECT r.barcode AS rack_barcode ' \
#                    'FROM rack r, containment rc, sample s, stock_sample ss ' \
#                    'WHERE r.rack_id = rc.holder_id ' \
#                    'AND r.rack_type = \'TUBERACK\' ' \
#                    'AND rc.held_id = s.container_id ' \
#                    'AND s.sample_id = ss.sample_id ' \
#                    'AND ss.molecule_design_set_id = %i' % (pool_id)
#            result = session.query('rack_barcode').from_statement(query).all()
#            rack_barcodes = []
#            for record in result: rack_barcodes.append(record[0])
#            if len(rack_barcodes) < 1: raise ValueError('no rack found')
#            self.excluded_racks = rack_barcodes
#
#    def test_result(self):
#        self.__continue_setup()
#        self.__check_result()
#
#    def test_result_number_isos(self):
#        self.number_isos = 1
#        self.__continue_setup()
#        self.__check_result()
#
#    def test_not_enough_candidates(self):
#        self.number_isos = 7
#        self.__continue_setup()
#        self.__check_result([1, 2, 3])
#        self._check_warning_messages('There is not enough library candidates ' \
#                    'left to populate all positions for the requested number ' \
#                    'of ISOs. Number of generated ISOs: 3')
#
#    def test_iso_picking(self):
#        self.__continue_setup()
#        self.number_isos = 1
#        # isos with tagged rack positions sets are not picked
#        for lci in self.library.iso_request.isos:
#            if lci.layout_number in (1, 2):
#                base_layout = LibraryBaseLayout(shape=get_384_rack_shape())
#                a1_pos = get_rack_position_from_label('A1')
#                base_pos = LibraryBaseLayoutPosition(rack_position=a1_pos)
#                base_layout.add_position(base_pos)
#                lci.rack_layout = base_layout.create_rack_layout()
#        self.__check_result([3])
#
#    def test_pool_queueing(self):
#        self.__continue_setup()
#        pools = set()
#        for md_pool in self.library.molecule_design_pool_set:
#            pools.add(md_pool)
#            if len(pools) > 3: break
#        md_type = self.library.molecule_design_pool_set.molecule_type
#        pool_set = MoleculeDesignPoolSet(molecule_type=md_type,
#                                         molecule_design_pools=pools)
#        for lci in self.library.iso_request.isos:
#            if lci.layout_number == 1:
#                base_layout = LibraryBaseLayout(shape=get_384_rack_shape())
#                a1_pos = get_rack_position_from_label('A1')
#                base_pos = LibraryBaseLayoutPosition(rack_position=a1_pos)
#                base_layout.add_position(base_pos)
#                lci.rack_layout = base_layout.create_rack_layout()
#                lci.molecule_design_pool_set = pool_set
#        self.number_isos = 7
#        self.__check_result([2, 3])
#        for lci in self.tool.return_value:
#            lci_set = lci.molecule_design_pool_set
#            for md_pool in lci_set:
#                self.assert_false(md_pool in pools)
#
#    def test_excluded_racks(self):
#        del self.pos_sectors[0]
#        del self.pos_sectors[1]
#        del self.pos_sectors[2]
#        # must be the MD ID of the of single MD pool you want to use
#        # make sure to adjust the test file
#        md_id = 213458
#        self.number_isos = 1
#        self.__set_excluded_racks(pool_id=205230)
#        self.__continue_setup('excluded_racks.xls')
#        new_isos = self.tool.get_result()
#        for lci in new_isos:
#            for md_pool in lci.molecule_design_pool_set:
#                for md in md_pool:
#                    self.assert_not_equal(md.id, md_id)
#        self._check_warning_messages('There is not enough library ' \
#                'candidates left to populate all positions for the ' \
#                'requested number of ISOs')
#        # compare
#        for lci in new_isos:
#            lci.rack_layout = RackLayout()
#            lci.molecule_design_pool_set = None
#        self.excluded_racks = None
#        has_md = False
#        self._create_tool()
#        new_isos = self.tool.get_result()
#        for lci in new_isos:
#            for md_pool in lci.molecule_design_pool_set:
#                for md in md_pool:
#                    if md.id == md_id:
#                        has_md = True
#                        break
#        self.assert_true(has_md)
#
#    def test_invalid_input_values(self):
#        self.__continue_setup()
#        lib = self.library
#        self.library = None
#        self._test_and_expect_errors('The molecule design library must be ' \
#                                     'a MoleculeDesignLibrary object')
#        self.library = lib
#        self.number_isos = -1
#        self._test_and_expect_errors('he number of ISOs order must be a ' \
#                                     'positive integer')
#        self.number_isos = 2
#        self.excluded_racks = dict()
#        self._test_and_expect_errors('The excluded racks list must be a ' \
#                                     'list object')
#        self.excluded_racks = [123, 456]
#        self._test_and_expect_errors('The excluded rack barcode must be a ' \
#                                     'basestring object')
#        self.excluded_racks = []
#        self.requested_tubes = dict()
#        self._test_and_expect_errors('The requested tubes list must be a list')
#        self.requested_tubes = [123, 456]
#        self._test_and_expect_errors('The requested tube barcode must be a ' \
#                                     'basestring')
#
#    def test_no_queued_molecules(self):
#        self.__continue_setup()
#        for lci in self.library.iso_request.isos:
#            if lci.layout_number == 1:
#                base_layout = LibraryBaseLayout(shape=get_384_rack_shape())
#                a1_pos = get_rack_position_from_label('A1')
#                base_pos = LibraryBaseLayoutPosition(rack_position=a1_pos)
#                base_layout.add_position(base_pos)
#                lci.rack_layout = base_layout.create_rack_layout()
#                lci.molecule_design_pool_set = \
#                        self.library.molecule_design_pool_set
#        self._test_and_expect_errors('There are no unused molecule design ' \
#                                     'pools left!')
#
#    def test_base_layout_converter_failure(self):
#        self.__continue_setup()
#        self.library.iso_request.iso_layout = None
#        self._test_and_expect_errors('Error when trying to fetch ' \
#                                     'library base layout.')
#
#    def test_optimizer_failure(self):
#        # make sure to use the proper MD ID in the test file
#        self.__set_excluded_racks(pool_id=205230)
#        self.__continue_setup('optimizer_failure.xls')
#        self._test_and_expect_errors('Error when trying to pick tubes.')
