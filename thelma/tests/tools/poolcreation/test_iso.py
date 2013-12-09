"""
Tests for classes involved in the population of pool creation ISOs
"""
from everest.repositories.rdb.testing import RdbContextManager
from thelma.automation.tools.libcreation.base import LibraryBaseLayout
from thelma.automation.tools.libcreation.base import LibraryBaseLayoutPosition
from thelma.automation.tools.libcreation.base import LibraryLayoutConverter
from thelma.automation.tools.poolcreation.iso import PoolCreationIsoPopulator
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.models.library import LibraryCreationIso
from thelma.models.moleculedesign import MoleculeDesignPoolSet
from thelma.models.racklayout import RackLayout
from thelma.tests.tools.poolcreation.utils import PoolCreationTestCase
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.automation.tools.semiconstants import get_positions_for_shape

class PoolCreationPopulatorTestCase(PoolCreationTestCase):

    def set_up(self):
        PoolCreationTestCase.set_up(self)
        self.TEST_FILE_PATH = 'thelma:tests/tools/poolcreation/iso/'
        self.VALID_FILE = 'valid_file.xls'
        self.number_isos = 1
        self.excluded_racks = None
        self.requested_tubes = None
        self.iso_request_label = 'pool_creation_populator_test'
        self.target_volume = 30
        self.target_concentration = 10000

    def tear_down(self):
        PoolCreationTestCase.tear_down(self)
        del self.number_isos
        del self.excluded_racks
        del self.requested_tubes

    def _create_tool(self):
        self.tool = PoolCreationIsoPopulator(pool_creation_library=self.library,
                                     number_isos=self.number_isos,
                                     excluded_racks=self.excluded_racks,
                                     requested_tubes=self.requested_tubes)

    def _continue_setup(self, file_name=None):
        PoolCreationTestCase._continue_setup(self, file_name)
        self.__create_isos()
        self._create_tool()

    def __create_isos(self):
        iso_request = self.library.iso_request
        for i in range(iso_request.number_plates):
            layout_number = i + 1
            label = '%s-%i' % (self.iso_request_label, layout_number)
            LibraryCreationIso(ticket_number=i,
                               layout_number=layout_number,
                               iso_request=iso_request,
                               label=label,
                               rack_layout=RackLayout())
        self.assert_equal(len(iso_request.isos), iso_request.number_plates)

    def __check_result(self, exp_layout_numbers=None):
        if exp_layout_numbers is None:
            exp_layout_numbers = []
            for i in range(self.number_isos):
                exp_layout_numbers.append(i + 1)
        new_isos = self.tool.get_result()
        self.assert_is_not_none(new_isos)
        self.assert_equal(len(new_isos), len(exp_layout_numbers))
        found_pools = []
        for lci in new_isos:
            self.assert_true(isinstance(lci, LibraryCreationIso))
            layout_number = lci.layout_number
            exp_label = '%s-%i' % (self.iso_request_label, layout_number)
            self.assert_equal(exp_label, lci.label)
            self.__check_layout(lci, found_pools)

    def __check_layout(self, lci, found_pools):
        converter = LibraryLayoutConverter(rack_layout=lci.rack_layout,
                                           log=TestingLog())
        lib_layout = converter.get_result()
        exp_positions = []
        exp_length = len(lci.molecule_design_pool_set)
        for rack_pos in get_positions_for_shape(lib_layout.shape,
                                                vertical_sorting=True):
            if len(exp_positions) == exp_length: break
            exp_positions.append(rack_pos)
        self._compare_pos_sets(exp_positions, lib_layout.get_positions())
        iso_pools = []
        for lib_pos in lib_layout.working_positions():
            pool_id = lib_pos.pool.id
            self.assert_false(pool_id in found_pools)
            found_pools.append(found_pools)
            iso_pools.append(pool_id)
            self.assert_equal(len(lib_pos.stock_tube_barcodes), 3)
        set_pools = []
        for pool in lci.molecule_design_pool_set:
            set_pools.append(pool.id)
        self.assert_equal(sorted(set_pools), sorted(iso_pools))

    def __set_excluded_racks(self, pool_id):
        with RdbContextManager() as session:
            # get racks to be excluded
            query = 'SELECT r.barcode AS rack_barcode ' \
                    'FROM rack r, containment rc, sample s, stock_sample ss ' \
                    'WHERE r.rack_id = rc.holder_id ' \
                    'AND r.rack_type = \'TUBERACK\' ' \
                    'AND rc.held_id = s.container_id ' \
                    'AND s.sample_id = ss.sample_id ' \
                    'AND ss.molecule_design_set_id = %i' % (pool_id)
            result = session.query('rack_barcode').from_statement(query).all()
            rack_barcodes = []
            for record in result: rack_barcodes.append(record[0])
            if len(rack_barcodes) < 1: raise ValueError('no rack found')
            self.excluded_racks = rack_barcodes

    def test_result(self):
        self._continue_setup()
        self.__check_result()

    def test_result_number_isos(self):
        self.number_isos = 1
        self._continue_setup()
        self.__check_result()

    def test_not_enough_candidates(self):
        self.number_isos = 7
        self._continue_setup()
        self.__check_result([1, 2])
        self._check_warning_messages('There is not enough candidates left to ' \
                    'populate all positions for the requested number of ' \
                    'ISOs. Number of generated ISOs: 2')

    def test_iso_picking(self):
        self._continue_setup()
        self.number_isos = 1
        # isos with tagged rack positions sets are not picked
        for lci in self.library.iso_request.isos:
            if lci.layout_number == 1:
                base_layout = LibraryBaseLayout(shape=get_96_rack_shape())
                a1_pos = get_rack_position_from_label('A1')
                base_pos = LibraryBaseLayoutPosition(rack_position=a1_pos)
                base_layout.add_position(base_pos)
                lci.rack_layout = base_layout.create_rack_layout()
        self.__check_result([2])

    def test_pool_queueing(self):
        self._continue_setup()
        pools = set()
        for md_pool in self.library.molecule_design_pool_set:
            pools.add(md_pool)
            if len(pools) > 3: break
        md_type = self.library.molecule_design_pool_set.molecule_type
        pool_set = MoleculeDesignPoolSet(molecule_type=md_type,
                                         molecule_design_pools=pools)
        for lci in self.library.iso_request.isos:
            if lci.layout_number == 1:
                base_layout = LibraryBaseLayout(shape=get_96_rack_shape())
                a1_pos = get_rack_position_from_label('A1')
                base_pos = LibraryBaseLayoutPosition(rack_position=a1_pos)
                base_layout.add_position(base_pos)
                lci.rack_layout = base_layout.create_rack_layout()
                lci.molecule_design_pool_set = pool_set
        self._create_tool()
        self.__check_result([2])
        for lci in self.tool.return_value:
            lci_set = lci.molecule_design_pool_set
            for md_pool in lci_set:
                self.assert_false(md_pool in pools)

    def test_excluded_racks(self):
        # make sure there is more than one stock tube for the chosen single
        # design pool
        md_id = 213458
        self.number_isos = 1
        self.__set_excluded_racks(pool_id=205230)
        self._continue_setup('excluded_racks.xls')
        new_isos = self.tool.get_result()
        for lci in new_isos:
            for md_pool in lci.molecule_design_pool_set:
                for md in md_pool:
                    self.assert_not_equal(md.id, md_id)
        self._check_warning_messages('There is not enough candidates left ' \
                         'to populate all positions for the requested ' \
                         'number of ISOs.')
        # compare
        for lci in new_isos:
            lci.rack_layout = RackLayout()
            lci.molecule_design_pool_set = None
        self.excluded_racks = None
        has_md = False
        self._create_tool()
        new_isos = self.tool.get_result()
        for lci in new_isos:
            for md_pool in lci.molecule_design_pool_set:
                for md in md_pool:
                    if md.id == md_id:
                        has_md = True
                        break
        self.assert_true(has_md)

    def test_invalid_input_values(self):
        self._continue_setup()
        lib = self.library
        self.library = None
        self._test_and_expect_errors('The pool creation library must be ' \
                                     'a MoleculeDesignLibrary object')
        self.library = lib
        self.number_isos = -1
        self._test_and_expect_errors('The number of ISOs order must be a ' \
                                     'positive integer')
        self.number_isos = 2
        self.excluded_racks = dict()
        self._test_and_expect_errors('The excluded racks list must be a ' \
                                     'list object')
        self.excluded_racks = [123, 456]
        self._test_and_expect_errors('The excluded rack barcode must be a ' \
                                     'basestring object')
        self.excluded_racks = []
        self.requested_tubes = dict()
        self._test_and_expect_errors('The requested tubes list must be a list')
        self.requested_tubes = [123, 456]
        self._test_and_expect_errors('The requested tube barcode must be a ' \
                                     'basestring')

    def test_no_queued_molecules(self):
        self._continue_setup()
        for lci in self.library.iso_request.isos:
            if lci.layout_number == 1:
                base_layout = LibraryBaseLayout(shape=get_96_rack_shape())
                a1_pos = get_rack_position_from_label('A1')
                base_pos = LibraryBaseLayoutPosition(rack_position=a1_pos)
                base_layout.add_position(base_pos)
                lci.rack_layout = base_layout.create_rack_layout()
                lci.molecule_design_pool_set = \
                        self.library.molecule_design_pool_set
        self._test_and_expect_errors('There are no unused molecule design ' \
                                     'pools left!')

    def test_optimizer_failure(self):
        # make sure there is more than one stock tube for the chosen single
        # design pool
        self.__set_excluded_racks(pool_id=205230)
        self._continue_setup('optimizer_failure.xls')
        self._test_and_expect_errors('Error when trying to pick tubes.')
