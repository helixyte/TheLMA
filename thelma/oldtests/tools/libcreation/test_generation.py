#"""
#Tests for tools involved in library creation.
#
#AAB
#"""
#
#from pkg_resources import resource_filename # pylint: disable=E0611,F0401
#from thelma.automation.tools.libcreation.base import LibraryBaseLayout
#from thelma.automation.tools.libcreation.base import LibraryBaseLayoutConverter
#from thelma.automation.tools.libcreation.base import LibraryBaseLayoutPosition
#from thelma.automation.tools.libcreation.base import MOLECULE_TYPE
#from thelma.automation.tools.libcreation.generation \
#    import LibraryCreationWorklistGenerator
#from thelma.automation.tools.libcreation.generation import LibraryGenerator
#from thelma.automation.tools.semiconstants import get_384_rack_shape
#from thelma.automation.tools.semiconstants import get_rack_position_from_label
#from thelma.automation.tools.stock.base import get_default_stock_concentration
#from thelma.models.liquidtransfer import TRANSFER_TYPES
#from thelma.models.moleculetype import MOLECULE_TYPE_IDS
#from thelma.models.utils import get_user
#from thelma.oldtests.tools.tooltestingutils import ToolsAndUtilsTestCase
#
#
#class LibraryGenerationTestCase(ToolsAndUtilsTestCase):
#
#    def set_up(self):
#        ToolsAndUtilsTestCase.set_up(self)
#        self.library_name = 'testlib'
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
#
#    def tear_down(self):
#        ToolsAndUtilsTestCase.tear_down(self)
#        del self.library_name
#        del self.pos_sectors
#        del self.translated_positions
#
#    def _check_worklist_series(self, worklist_series, exp_length):
#        self.assert_is_not_none(worklist_series)
#        self.assert_equal(len(worklist_series), exp_length)
#        self.__check_stock_buffer_worklist(worklist_series)
#        self.__check_prep_buffer_worklist(worklist_series)
#        self.__check_stock_to_prep_worklist(exp_length, worklist_series)
#        self.__check_prep_to_aliquot_worklist(exp_length, worklist_series)
#
#    def __check_stock_buffer_worklist(self, worklist_series):
#        sector_indices = self.pos_sectors.keys()
#        exp_volume = 36
#        for worklist in worklist_series:
#            if not worklist.index < len(sector_indices): continue
#            sector_index = sector_indices[worklist.index]
#            exp_label = LibraryCreationWorklistGenerator.\
#                        LIBRARY_STOCK_BUFFER_WORKLIST_LABEL % (
#                                            self.library_name, sector_index + 1)
#            self.assert_equal(exp_label, worklist.label)
#            exp_positions = []
#            for pos_label in self.pos_sectors[sector_index]:
#                translated_pos = self.translated_positions[pos_label]
#                exp_positions.append(translated_pos)
#            self.assert_equal(len(exp_positions),
#                              len(worklist.planned_transfers))
#            wl_labels = []
#            for pt in worklist.planned_transfers:
#                self.assert_equal(pt.type, TRANSFER_TYPES.CONTAINER_DILUTION)
#                self._compare_transfer_volume(pt, exp_volume)
#                wl_labels.append(pt.target_position.label)
#            self.assert_equal(sorted(wl_labels), sorted(exp_positions))
#
#    def __check_prep_buffer_worklist(self, worklist_series):
#        sector_indices = self.pos_sectors.keys()
#        exp_volume = 43.3 - 5.5
#        for worklist in worklist_series:
#            if worklist.index < len(sector_indices): continue
#            if worklist.index >= len(sector_indices) * 2: continue
#            sector_index = sector_indices[worklist.index - len(sector_indices)]
#            exp_label = LibraryCreationWorklistGenerator.\
#                        LIBRARY_PREP_BUFFER_WORKLIST_LABEL % (
#                                            self.library_name, sector_index + 1)
#            self.assert_equal(worklist.label, exp_label)
#            exp_positions = []
#            for pos_label in self.pos_sectors[sector_index]:
#                translated_pos = self.translated_positions[pos_label]
#                exp_positions.append(translated_pos)
#            self.assert_equal(len(exp_positions),
#                              len(worklist.planned_transfers))
#            wl_labels = []
#            for pt in worklist.planned_transfers:
#                self.assert_equal(pt.type, TRANSFER_TYPES.CONTAINER_DILUTION)
#                self._compare_transfer_volume(pt, exp_volume)
#                wl_labels.append(pt.target_position.label)
#            self.assert_equal(sorted(wl_labels), sorted(exp_positions))
#
#    def __check_stock_to_prep_worklist(self, exp_length, worklist_series):
#        exp_volume = 5.5
#        worklist = None
#        for wl in worklist_series:
#            if wl.index == exp_length - 2:
#                worklist = wl
#                break
#        exp_label = LibraryCreationWorklistGenerator.\
#                    STOCK_TO_PREP_TRANSFER_WORKLIST_LABEL % (self.library_name)
#        self.assert_equal(exp_label, worklist.label)
#        self.assert_equal(len(worklist.planned_transfers), 1)
#        rt = worklist.planned_transfers[0]
#        self.assert_equal(rt.type, TRANSFER_TYPES.RACK_TRANSFER)
#        self._compare_transfer_volume(rt, exp_volume)
#        self.assert_equal(rt.sector_number, 1)
#        self.assert_equal(rt.source_sector_index, 0)
#        self.assert_equal(rt.target_sector_index, 0)
#
#    def __check_prep_to_aliquot_worklist(self, exp_length, worklist_series):
#        exp_volume = 4
#        worklist = None
#        for wl in worklist_series:
#            if wl.index == exp_length - 1:
#                worklist = wl
#                break
#        exp_label = LibraryCreationWorklistGenerator.\
#                    PREP_TO_ALIQUOT_TRANSFER_WORKLIST_LABEL % (
#                                                            self.library_name)
#        self.assert_equal(exp_label, worklist.label)
#        self.assert_equal(len(worklist.planned_transfers),
#                          len(self.pos_sectors))
#        sectors = []
#        for rt in worklist.planned_transfers:
#            self._compare_transfer_volume(rt, exp_volume)
#            self.assert_equal(rt.sector_number, 4)
#            self.assert_equal(rt.source_sector_index, 0)
#            sectors.append(rt.target_sector_index)
#        self.assert_equal(sorted(sectors), sorted(self.pos_sectors.keys()))
#
#
#class LibraryCreationWorklistGeneratorTestCase(LibraryGenerationTestCase):
#
#    def set_up(self):
#        LibraryGenerationTestCase.set_up(self)
#        self.stock_concentration = get_default_stock_concentration(
#                                                        MOLECULE_TYPE_IDS.SIRNA)
#        self.base_layout = None
#
#    def tear_down(self):
#        LibraryGenerationTestCase.tear_down(self)
#        del self.stock_concentration
#        del self.base_layout
#
#    def _create_tool(self):
#        self.tool = LibraryCreationWorklistGenerator(self.base_layout,
#                                                     self.stock_concentration,
#                                                     self.library_name)
#
#    def __continue_setup(self):
#        self.__create_base_layout()
#        self._create_tool()
#
#    def __create_base_layout(self):
#        self.base_layout = LibraryBaseLayout(shape=get_384_rack_shape())
#        for label_list in self.pos_sectors.values():
#            for pos_label in label_list:
#                rack_pos = get_rack_position_from_label(pos_label)
#                base_pos = LibraryBaseLayoutPosition(rack_position=rack_pos)
#                self.base_layout.add_position(base_pos)
#
#    def __check_result(self, exp_length):
#        self.__continue_setup()
#        series = self.tool.get_result()
#        self._check_worklist_series(series, exp_length)
#
#    def test_result(self):
#        self.__check_result(10)
#
#    def test_missing_sectors(self):
#        del self.pos_sectors[2]
#        self.__check_result(8)
#        self._check_warning_messages('Some rack sectors are empty. You do ' \
#                                     'not require stock racks for them')
#
#    def test_invalid_input_values(self):
#        self.__continue_setup()
#        base_layout = self.base_layout
#        self.base_layout = None
#        self._test_and_expect_errors('The base library layout must be ' \
#                                     'a LibraryBaseLayout')
#        self.base_layout = base_layout
#        stock_concentration = self.stock_concentration
#        self.stock_concentration = -3
#        self._test_and_expect_errors('The stock concentration for the single ' \
#                                'source molecules must be a positive number')
#        self.stock_concentration = stock_concentration
#        self.library_name = 13
#        self._test_and_expect_errors('The library name must be a basestring')
#
#
#class LibraryGeneratorTestCase(LibraryGenerationTestCase):
#
#    def set_up(self):
#        LibraryGenerationTestCase.set_up(self)
#        self.stream = None
#        self.requester = get_user('sachse')
#        self.FILE_PATH = 'thelma:tests/tools/libcreation/generation/'
#        self.valid_file = 'valid_file.xls'
#
#    def tear_down(self):
#        LibraryGenerationTestCase.tear_down(self)
#        del self.stream
#        del self.requester
#        del self.FILE_PATH
#        del self.valid_file
#
#    def _create_tool(self):
#        self.tool = LibraryGenerator(library_name=self.library_name,
#                                     stream=self.stream,
#                                     requester=self.requester)
#
#    def __continue_setup(self, file_name=None):
#        if file_name is None: file_name = self.valid_file
#        self.__read_file(file_name)
#        self._create_tool()
#
#    def __read_file(self, file_name):
#        fn = self.FILE_PATH + file_name
#        f = resource_filename(*fn.split(':'))
#        stream = open(f, 'rb')
#        self.stream = stream.read()
#
#    def __test_and_expect_errors(self, file_name, msg):
#        self.__continue_setup(file_name)
#        self._test_and_expect_errors(msg)
#
#    def __check_result(self, exp_worklist_number, number_plates):
#        lib = self.tool.get_result()
#        self.assert_is_not_none(lib)
#        self.assert_equal(lib.label, self.library_name)
#        self.__check_iso_request(lib, number_plates)
#        self.__check_worklist_series(lib, exp_worklist_number)
#        self.__check_pool_set(lib)
#
#    def __check_iso_request(self, lib, number_plates):
#        iso_request = lib.iso_request
#        self.assert_equal(iso_request.plate_set_label, self.library_name)
#        self.assert_equal(len(iso_request.isos), 0)
#        self.assert_equal(iso_request.requester, self.requester)
#        self.assert_is_none(iso_request.experiment_metadata)
#        self.assert_equal(iso_request.number_plates, number_plates)
#        self.assert_equal(iso_request.number_aliquots, 8)
#        exp_positions = []
#        for label_list in self.pos_sectors.values():
#            for pos_label in label_list:
#                rack_pos = get_rack_position_from_label(pos_label)
#                exp_positions.append(rack_pos)
#        converter = LibraryBaseLayoutConverter(iso_request.iso_layout)
#        base_layout = converter.get_result()
#        self.assert_equal(len(base_layout), len(exp_positions))
#        self._compare_pos_sets(exp_positions, base_layout.get_positions())
#
#    def __check_worklist_series(self, lib, exp_worklist_number):
#        worklist_series = lib.iso_request.worklist_series
#        self._check_worklist_series(worklist_series, exp_worklist_number)
#
#    def __check_pool_set(self, lib):
#        pool_set = lib.molecule_design_pool_set
#        self.assert_equal(len(pool_set), 29)
#        self.assert_equal(pool_set.molecule_type.id, MOLECULE_TYPE)
#
#    def test_result(self):
#        self.__continue_setup()
#        self.__check_result(10, number_plates=3)
#
#    def test_valid_file_missing_sector(self):
#        self.__continue_setup('valid_file_missing_sector.xls')
#        del self.pos_sectors[2]
#        del self.pos_sectors[3]
#        self.__check_result(exp_worklist_number=6, number_plates=4)
#        self._check_warning_messages('Some rack sectors are empty. You do ' \
#                                     'not require stock racks for them: 3, 4')
#
#    def test_invalid_input(self):
#        self.__continue_setup()
#        libname = self.library_name
#        self.library_name = 13
#        self._test_and_expect_errors('The library name must be a basestring')
#        self.library_name = libname
#        self.requester = self.requester.username
#        self._test_and_expect_errors('The requester must be a User object')
#
#    def test_invalid_layout(self):
#        self.__test_and_expect_errors('invalid_layout.xls',
#                        'Error when trying to obtain library base layout')
#
#    def test_invalid_pool_set(self):
#        self.__test_and_expect_errors('invalid_pool_set.xls',
#                                'Unable to parse library pool set')
#

