#"""
#Tests for classes involved in the library creation ISO optimisation.
#
#AAB
#"""
#from everest.repositories.rdb.testing import RdbContextManager
#from everest.testing import check_attributes
#from thelma.automation.tools.iso.optimizer import IsoCandidate
#from thelma.automation.tools.libcreation.base import POOL_STOCK_RACK_CONCENTRATION
#from thelma.automation.tools.libcreation.optimizer \
#    import LibraryCreationTubePicker
#from thelma.automation.tools.libcreation.optimizer import LibraryCandidate
#from thelma.automation.tools.semiconstants import get_rack_position_from_label
#from thelma.automation.tools.stock.base import get_default_stock_concentration
#from thelma.automation.tools.utils.base import create_in_term_for_db_queries
#from thelma.automation.tools.utils.base \
#    import CONCENTRATION_CONVERSION_FACTOR
#from thelma.interfaces import IMoleculeDesign
#from thelma.models.moleculedesign import MoleculeDesignPool
#from thelma.models.moleculetype import MOLECULE_TYPE_IDS
#from thelma.tests.tools.tooltestingutils import TestingLog
#from thelma.tests.tools.tooltestingutils import ToolsAndUtilsTestCase
#
#
#class LibraryCandidateTestCase(ToolsAndUtilsTestCase):
#
#    def set_up(self):
#        ToolsAndUtilsTestCase.set_up(self)
#        self.md1 = self._get_entity(IMoleculeDesign, '11')
#        self.md2 = self._get_entity(IMoleculeDesign, '12')
#        md_set = [self.md1, self.md2]
#        self.pool = MoleculeDesignPool(molecule_designs=set(md_set),
#                                       default_stock_concentration=0.00005)
#        self.pool.id = -1
#
#    def tear_down(self):
#        ToolsAndUtilsTestCase.tear_down(self)
#        del self.md1
#        del self.md2
#        del self.pool
#
#    def __get_data(self):
#        return dict(pool=self.pool)
#
#    def __get_test_candidate(self):
#        return LibraryCandidate(**self.__get_data())
#
#    def __create_iso_candidate(self, md_id):
#        pool_id = md_id * 2
#        iso_candidate = IsoCandidate(pool_id=pool_id,
#                        rack_barcode='%05i' % (pool_id),
#                        rack_position=get_rack_position_from_label('A1'),
#                        container_barcode='1%04i' % (pool_id),
#                        concentration=50000)
#        return iso_candidate
#
#    def test_init(self):
#        attrs = self.__get_data()
#        lc = LibraryCandidate(**attrs)
#        self.assert_is_not_none(lc)
#        check_attributes(lc, attrs)
#
#    def test_get_molecule_design_ids(self):
#        lc = self.__get_test_candidate()
#        lc_ids = lc.get_molecule_design_ids()
#        self.assert_equal(sorted(lc_ids), [11, 12])
#
#    def test_iso_candidates(self):
#        lc = self.__get_test_candidate()
#        self.assert_false(lc.has_iso_candidate(11))
#        self.assert_false(lc.has_iso_candidate(12))
#        iso_cand = self.__create_iso_candidate(11)
#        lc.set_iso_candidate(11, iso_cand)
#        self.assert_true(lc.has_iso_candidate(11))
#        self.assert_false(lc.has_iso_candidate(12))
#        self.assert_raises(AttributeError, lc.set_iso_candidate,
#                           *(11, iso_cand))
#        lc.set_iso_candidate(12, iso_cand)
#
#    def test_get_tube_barcodes(self):
#        lc = self.__get_test_candidate()
#        iso_cand11 = self.__create_iso_candidate(11)
#        iso_cand12 = self.__create_iso_candidate(12)
#        lc.set_iso_candidate(11, iso_cand11)
#        lc.set_iso_candidate(12, iso_cand12)
#        self.assert_equal(lc.get_tube_barcodes(),
#                [iso_cand11.container_barcode, iso_cand12.container_barcode])
#
#    def test_is_completed(self):
#        lc = self.__get_test_candidate()
#        self.assert_false(lc.is_completed())
#        iso_cand11 = self.__create_iso_candidate(11)
#        iso_cand12 = self.__create_iso_candidate(12)
#        lc.set_iso_candidate(11, iso_cand11)
#        self.assert_false(lc.is_completed())
#        lc.set_iso_candidate(12, iso_cand12)
#        self.assert_true(lc.is_completed())
#
#    def test_replace_candidates(self):
#        lc = self.__get_test_candidate()
#        iso_cand11 = self.__create_iso_candidate(11)
#        iso_cand12 = self.__create_iso_candidate(12)
#        lc.set_iso_candidate(11, iso_cand11)
#        lc.set_iso_candidate(12, iso_cand12)
#        self.assert_equal(lc.get_tube_barcodes(),
#                [iso_cand11.container_barcode, iso_cand12.container_barcode])
#        iso_cand13 = self.__create_iso_candidate(13)
#        lc.replace_candidate(12, iso_cand13)
#        self.assert_equal(lc.get_tube_barcodes(),
#                [iso_cand11.container_barcode, iso_cand13.container_barcode])
#
#
#class LibraryCreationTubePickerTestCase(ToolsAndUtilsTestCase):
#
#    def set_up(self):
#        ToolsAndUtilsTestCase.set_up(self)
#        self.log = TestingLog()
#        self.molecule_design_pools = []
#        self.stock_concentration = get_default_stock_concentration(
#                                                    MOLECULE_TYPE_IDS.SIRNA)
#        self.take_out_volume = 3
#        self.excluded_racks = None
#        self.requested_tubes = None
#        self.md_map = dict()
#        # make sure to set up the correct combinations
#        #: maps single molecule pool IDs onto molecule design IDs
#        self.single_pool_map = {118802 : 10247988, 118803 : 10247989,
#                                124054 : 10331565, 124055 : 10331566,
#                                205230 : 213458, 132080 : 10339512}
#        # maps md ID lists onto pool IDs (pools are made up for this test)
#        self.pool_mds = {1 : [118802, 118803], 2: [124054, 124055],
#                         3 : [205230, 132080]}
#        self.query_pool_id = 205230
#
#    def tear_down(self):
#        ToolsAndUtilsTestCase.tear_down(self)
#        del self.log
#        del self.molecule_design_pools
#        del self.stock_concentration
#        del self.take_out_volume
#        del self.excluded_racks
#        del self.requested_tubes
#        del self.md_map
#        del self.single_pool_map
#        del self.pool_mds
#        del self.query_pool_id
#
#    def _create_tool(self):
#        self.tool = LibraryCreationTubePicker(log=self.log,
#                        molecule_design_pools=self.molecule_design_pools,
#                        stock_concentration=self.stock_concentration,
#                        take_out_volume=self.take_out_volume,
#                        excluded_racks=self.excluded_racks,
#                        requested_tubes=self.requested_tubes)
#
#    def __continue_setup(self):
#        self.__create_pools()
#        self._create_tool()
#
#    def __create_pools(self):
#        pool_stock_conc = POOL_STOCK_RACK_CONCENTRATION \
#                          / CONCENTRATION_CONVERSION_FACTOR
#        for pool_id, single_pool_ids in self.pool_mds.iteritems():
#            mds = set()
#            for single_pool_id in single_pool_ids:
#                md_id = self.single_pool_map[single_pool_id]
#                md = self._get_entity(IMoleculeDesign, str(md_id))
#                mds.add(md)
#            pool = MoleculeDesignPool(molecule_designs=mds,
#                                default_stock_concentration=pool_stock_conc)
#            pool.id = pool_id
#            self.molecule_design_pools.append(pool)
#
#    def __set_excluded_racks(self, del_pool_mds=True):
#        with RdbContextManager() as session:
#            # get racks to be excluded
#            query = 'SELECT r.barcode AS rack_barcode ' \
#                    'FROM rack r, containment rc, sample s, stock_sample ss ' \
#                    'WHERE r.rack_id = rc.holder_id ' \
#                    'AND r.rack_type = \'TUBERACK\' ' \
#                    'AND rc.held_id = s.container_id ' \
#                    'AND s.sample_id = ss.sample_id ' \
#                    'AND ss.molecule_design_set_id = %i' % (self.query_pool_id)
#            result = session.query('rack_barcode').from_statement(query).all()
#            rack_barcodes = []
#            for record in result: rack_barcodes.append(record[0])
#            if len(rack_barcodes) < 1: raise ValueError('no rack found')
#            self.excluded_racks = rack_barcodes
#            if del_pool_mds:
#                del_pool_id = None
#                for pool_id, single_pools_ids in self.pool_mds.iteritems():
#                    if self.query_pool_id in single_pools_ids:
#                        del_pool_id = pool_id
#                        break
#                del self.pool_mds[del_pool_id]
#
#    def __check_result(self, lib_cands=None):
#        if lib_cands is None:
#            lib_cands = self.tool.get_result()
#        self.assert_is_not_none(lib_cands)
#        self.assert_equal(len(lib_cands), len(self.pool_mds))
#        pools = []
#        for lib_cand in lib_cands:
#            self.assert_true(lib_cand.is_completed())
#            pool_id = lib_cand.pool.id
#            pools.append(pool_id)
#        self.assert_equal(sorted(pools), sorted(self.pool_mds.keys()))
#
#    def test_result(self):
#        self.__continue_setup()
#        self.__check_result()
#
#    def test_excluded_racks(self):
#        self.__set_excluded_racks()
#        self.__continue_setup()
#        lib_cands = self.tool.get_result()
#        self.assert_is_not_none(lib_cands)
#        self.assert_equal(len(lib_cands), len(self.pool_mds))
#        pools = []
#        for lib_cand in lib_cands:
#            self.assert_true(lib_cand.is_completed())
#            pool_id = lib_cand.pool.id
#            pools.append(pool_id)
#        self.assert_equal(sorted(pools), sorted(self.pool_mds.keys()))
#
#    def test_requested_racks(self):
#        self.query_pool_id = 205230
#        # get tube for comparison
#        self.__set_excluded_racks(del_pool_mds=False)
#        marker_racks = self.excluded_racks
#        self.assert_true(len(marker_racks) > 0)
#        self.excluded_racks = None
#        marker_pool = None
#        for pool_id, single_pools_ids in self.pool_mds.iteritems():
#            if self.query_pool_id in single_pools_ids:
#                marker_pool = pool_id
#                break
#        self.__continue_setup()
#        libcands = self.tool.get_result()
#        for libcand in libcands:
#            if not libcand.pool.id == marker_pool: continue
#            ori_tube_barcodes = libcand.get_tube_barcodes()
#        # exclude the racks
#        with RdbContextManager() as session:
#            barcodes_str = create_in_term_for_db_queries(ori_tube_barcodes,
#                                                         as_string=True)
#            query = 'SELECT r.barcode AS rack_barcode ' \
#                    'FROM rack r, container_barcode cb, containment rc ' \
#                    'WHERE r.rack_id = rc.holder_id ' \
#                    'AND rc.held_id = cb.container_id ' \
#                    'AND cb.barcode IN %s' % (barcodes_str)
#            result = session.query('rack_barcode').from_statement(query).all()
#            self.excluded_racks = []
#            for record in result:
#                if record[0] in marker_racks:
#                    self.excluded_racks.append(record[0])
#                    break
#        self._create_tool()
#        libcands = self.tool.get_result()
#        for libcand in libcands:
#            if not libcand.pool.id == marker_pool: continue
#            self.requested_tubes = libcand.get_tube_barcodes()
#            self.assert_not_equal(sorted(self.requested_tubes),
#                                  sorted(ori_tube_barcodes))
#        self.assert_true(len(self.requested_tubes) > 0)
#        # request tubes
#        self.excluded_racks = None
#        self._create_tool()
#        libcands = self.tool.get_result()
#        for libcand in libcands:
#            if not libcand.pool.id == marker_pool: continue
#            tube_barcodes = libcand.get_tube_barcodes()
#            self.assert_equal(sorted(self.requested_tubes),
#                              sorted(tube_barcodes))
#
#    def test_no_stock_samples(self):
#        del self.single_pool_map[205230]
#        self.single_pool_map[840963] = 213548
#        self.pool_mds[3][0] = 840963
#        self.take_out_volume = 30
#        self.__continue_setup()
#        libcands = self.tool.get_result()
#        self.assert_is_not_none(libcands)
#        self._check_warning_messages('Could not find suitable source stock ' \
#                            'tubes for the following molecule design pools')
#
#    def test_double_molecule_design_set(self):
#        self.pool_mds[1] = [205230, 118803]
#        self.__continue_setup()
#        self.__check_result()
#        found_tubes = []
#        for libcand in self.tool.get_result():
#            tube_barcodes = libcand.get_tube_barcodes()
#            for barcode in tube_barcodes:
#                self.assert_false(barcode in found_tubes)
#                found_tubes.append(barcode)
#
#    def test_invalid_input_values(self):
#        self.__continue_setup()
#        md_pools = self.molecule_design_pools
#        self.molecule_design_pools = None
#        self._test_and_expect_errors('The library pool list must be a list')
#        self.molecule_design_pools = []
#        self._test_and_expect_errors('The pool list is empty!')
#        self.molecule_design_pools = md_pools
#        sc = self.stock_concentration
#        self.stock_concentration = -2
#        self._test_and_expect_errors('The stock concentration must be a ' \
#                                     'positive number')
#        self.stock_concentration = sc
#        tv = self.take_out_volume
#        self.take_out_volume = -2
#        self._test_and_expect_errors('The stock take out volume must be a ' \
#                                     'positive number')
#        self.take_out_volume = tv
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
#        self._test_and_expect_errors()
#
#    def test_no_stock_sample(self):
#        self.take_out_volume = 100000
#        self.__continue_setup()
#        self._test_and_expect_errors('Did not find any suitable stock sample!')
#
#    def test_stock_concentration(self):
#        self.stock_concentration = 15
#        self.__continue_setup()
#        self._test_and_expect_errors('Did not find any suitable stock sample!')
#
#    def test_no_library_candidates(self):
#        self.single_pool_map = {205205 : 10247988, 689600 : 75}
#        # maps md ID lists onto pool IDs (pools are made up for this test)
#        self.pool_mds = {1 : [205205, 689600]}
#        self.query_pool_id = 205205
#        self.__set_excluded_racks(del_pool_mds=False)
#        self.__continue_setup()
#        self._test_and_expect_errors('Did not find any library candidate!')
