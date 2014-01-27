"""
Tests for tools involved in the population of stock sample generation ISOs.

AAB
"""
from everest.repositories.rdb.testing import RdbContextManager
from thelma.automation.tools.iso import get_job_creator
from thelma.automation.tools.iso.poolcreation.jobcreator import StockSampleCreationIsoJobCreator
from thelma.automation.tools.iso.poolcreation.jobcreator \
    import StockSampleCreationIsoPopulator
from thelma.automation.tools.iso.poolcreation.jobcreator \
    import StockSampleCreationIsoResetter
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.models.iso import ISO_STATUS
from thelma.models.utils import get_user
from thelma.tests.tools.iso.poolcreation.utils \
    import StockSampleCreationTestCase2
from thelma.tests.tools.iso.poolcreation.utils import SSC_TEST_DATA
from thelma.tests.tools.iso.poolcreation.utils \
    import StockSampleCreationTestCase3
from thelma.tests.tools.tooltestingutils import TestingLog

class _StockSampleCreationIsoTestCase(StockSampleCreationTestCase2):

    def set_up(self):
        StockSampleCreationTestCase2.set_up(self)
        self.compare_iso_layout_positions = False
        self.isos_to_generate = 1
        self.excluded_racks = None
        self.requested_tubes = None

    def tear_down(self):
        StockSampleCreationTestCase2.tear_down(self)
        del self.isos_to_generate
        del self.excluded_racks
        del self.requested_tubes

    def _continue_setup(self, file_name=None):
        StockSampleCreationTestCase2._continue_setup(self, file_name=file_name)
        self._create_tool()

    def _check_resulting_isos(self, isos, exp_layout_nums, exp_warning):
        self.assert_is_not_none(isos)
        self.assert_equal(len(isos), len(exp_layout_nums))
        labels = []
        layout_nums = []
        for iso in isos:
            labels.append(iso.label)
            layout_num = iso.layout_number
            layout_nums.append(layout_num)
            self.assert_equal(iso.status, ISO_STATUS.QUEUED)
            self._check_pool_set(iso.molecule_design_pool_set, layout_num)
            self._check_iso_layout(iso.rack_layout, layout_num)
        self.assert_equal(sorted(layout_nums), exp_layout_nums)
        exp_labels = []
        for layout_num in exp_layout_nums:
            exp_labels.append(SSC_TEST_DATA.ISO_LABELS[layout_num])
        self.assert_equal(sorted(labels), sorted(exp_labels))
        warn = 'There is not enough candidates left to populate all ' \
                'positions for the requested number of ISOs.'
        msgs = ' '.join(self.tool.get_messages())
        if exp_warning:
            self.assert_true(warn in msgs)
        else:
            self.assert_false(warn in msgs)

    def _test_invalid_input_values(self):
        self._continue_setup()
        ori_ir = self.iso_request
        self.iso_request = self._create_lab_iso_request()
        self._test_and_expect_errors('The ISO request must be a ' \
            'StockSampleCreationIsoRequest object (obtained: LabIsoRequest)')
        self.iso_request = ori_ir
        self.isos_to_generate = 0
        self._test_and_expect_errors('The number of ISOs order must be a ' \
                                     'positive integer (obtained: 0).')
        self.isos_to_generate = -1
        self._test_and_expect_errors('The number of ISOs order must be a ' \
                                     'positive integer (obtained: -1).')
        self.isos_to_generate = 0.4
        self._test_and_expect_errors('The number of ISOs order must be a ' \
                                     'positive integer (obtained: 0.4).')
        self.isos_to_generate = 1
        self.excluded_racks = dict()
        self._test_and_expect_errors('The excluded rack list must be a list ' \
                                     'object (obtained: dict)')
        self.excluded_racks = [1]
        self._test_and_expect_errors('The excluded rack must be a basestring ' \
                                     'object (obtained: int).')
        self.excluded_racks = None
        self.requested_tubes = dict()
        self._test_and_expect_errors('The requested tube list must be a list ' \
                                     'object (obtained: dict).')
        self.requested_tubes = [1]
        self._test_and_expect_errors('The requested tube must be a ' \
                                     'basestring object (obtained: int)')
        self.requested_tubes = None

    def _prepare_one_iso(self):
        self.number_isos = 2
        self._continue_setup()
        pools = []
        mt = None
        for pool in self.iso_request.molecule_design_pool_set:
            pools.append(pool)
            if len(pools) == 96:
                mt = pool.molecule_type
                break
        pool_set = self._create_molecule_design_pool_set(molecule_type=mt,
                                            molecule_design_pools=set(pools))
        trps = self._create_tagged_rack_position_set()
        iso = self.isos[1]
        iso.molecule_design_pool_set = pool_set
        iso.rack_layout.tagged_rack_position_sets.append(trps)

    def _set_excluded_racks(self, session):
        self.excluded_racks = []
        missing_pool_id = 298381 # belongs to pool 10247990 (in 1063102)
        query = 'SELECT r.barcode AS rack_barcode ' \
                'FROM rack r, containment rc, sample s, stock_sample ss ' \
                'WHERE r.rack_id = rc.holder_id ' \
                'AND r.rack_type = \'TUBERACK\' ' \
                'AND rc.held_id = s.container_id ' \
                'AND ss.sample_id = s.sample_id ' \
                'AND ss.molecule_design_set_id = %i' % (missing_pool_id)
        result = session.query('rack_barcode').from_statement(query).all()
        for record in result: self.excluded_racks.append(record[0])
        if len(self.excluded_racks) < 1: raise ValueError('no rack found')
        return missing_pool_id


class StockSampleCreationIsoPopulatorTestCase(_StockSampleCreationIsoTestCase):

    def set_up(self):
        _StockSampleCreationIsoTestCase.set_up(self)
        self.log = TestingLog()

    def tear_down(self):
        _StockSampleCreationIsoTestCase.tear_down(self)
        del self.log

    def _create_tool(self):
        self.tool = StockSampleCreationIsoPopulator(log=self.log,
                            iso_request=self.iso_request,
                            number_isos=self.isos_to_generate,
                            excluded_racks=self.excluded_racks,
                            requested_tubes=self.requested_tubes)

    def test_result_1_out_of_1(self):
        self._continue_setup()
        isos = self.tool.get_result()
        self._check_resulting_isos(isos, [1], False)

    def test_result_1_from_2(self):
        self._prepare_one_iso()
        isos = self.tool.get_result()
        self._check_resulting_isos(isos, [2], True)

    def test_result_2_from_2(self):
        self.number_isos = 2
        self.isos_to_generate = 2
        self._continue_setup()
        isos = self.tool.get_result()
        self._check_resulting_isos(isos, [1, 2], True)

    def test_2_from_1(self):
        self.isos_to_generate = 2
        self._continue_setup()
        isos = self.tool.get_result()
        self._check_resulting_isos(isos, [1], True)

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_no_unused_pools_left(self):
        self._continue_setup()
        self._generate_iso_layouts()
        self._generate_pool_sets()
        self._test_and_expect_errors('There are no unused molecule design ' \
                                     'pools left!')

    def test_volume_calculation_failure(self):
        self._continue_setup()
        self.iso_request.stock_volume = 1 / VOLUME_CONVERSION_FACTOR
        self._test_and_expect_errors('Unable to determine stock transfer ' \
            'volume: The target volume you have requested (1 ul) is too low ' \
            'for the required dilution (1:15) since the CyBio cannot pipet ' \
            'less than 1.0 ul per transfer. The volume that has to be taken ' \
            'from the stock for each single molecule design would be lower ' \
            'that that. Increase the target volume to 15.0 ul or increase ' \
            'the target concentration.')

    def test_exluded_racks_and_missing_pool_candidate(self):
        with RdbContextManager() as session:
            self._continue_setup()
            self._set_excluded_racks(session)
            self._create_tool()
            isos = self.tool.get_result()
            self.assert_is_not_none(isos)
            iso = isos[0]
            self.assert_equal(iso.layout_number, 1)
            pool_set = iso.molecule_design_pool_set
            self.assert_equal(len(pool_set), 10)
            self._check_warning_messages('Unable to find valid tubes for the ' \
                                         'following pools: 1063102.')

    def test_tube_picking_failure(self):
        self._continue_setup()
        self.iso_request.stock_volume = 1000 / VOLUME_CONVERSION_FACTOR
        self._test_and_expect_errors('Error when trying to pick tubes.')


class StockSampleCreationIsoJobCreatorTestCase(_StockSampleCreationIsoTestCase):

    def set_up(self):
        _StockSampleCreationIsoTestCase.set_up(self)
        self.job_owner = get_user('brehm')
        self.use_factory = True

    def tear_down(self):
        _StockSampleCreationIsoTestCase.tear_down(self)
        del self.job_owner
        del self.use_factory

    def _create_tool(self):
        kw = dict(iso_request=self.iso_request, job_owner=self.job_owner,
                number_isos=self.isos_to_generate,
                excluded_racks=self.excluded_racks,
                requested_tubes=self.requested_tubes)
        if self.use_factory:
            self.tool = get_job_creator(**kw)
        else:
            self.tool = StockSampleCreationIsoJobCreator(**kw)

    def __check_result(self, exp_layout_nums, exp_warning):
        iso_job = self.tool.get_result()
        self.assert_is_not_none(iso_job)
        self._check_resulting_isos(iso_job.isos, exp_layout_nums, exp_warning)
        self.assert_equal(iso_job.label, 'ssgen_test_job_01')
        self.assert_equal(iso_job.user, self.job_owner)
        self.assert_equal(iso_job.number_stock_racks, 0)
        self.assert_equal(iso_job.iso_job_stock_racks, [])
        self.assert_equal(iso_job.iso_job_preparation_plates, [])
        self.assert_is_none(iso_job.worklist_series)

    def test_result_1_from_1(self):
        self._continue_setup()
        self.__check_result([1], False)

    def test_result_1_from_2(self):
        self._prepare_one_iso()
        self.__check_result([2], True)

    def test_result_2_from_2(self):
        self.number_isos = 2
        self.isos_to_generate = 2
        self._continue_setup()
        self.__check_result([1, 2], True)

    def test_result_2_from_1(self):
        self.isos_to_generate = 2
        self._continue_setup()
        self.__check_result([1], True)

    def test_invalid_input_value(self):
        self.use_factory = False
        self._test_invalid_input_values()
        self.job_owner = self.job_owner.username
        self._test_and_expect_errors('The job owner must be a User ' \
                                     'object (obtained: unicode)')

    def test_excluded_racks(self):
        with RdbContextManager() as session:
            self._continue_setup()
            self._set_excluded_racks(session)
            self._create_tool()
            iso_job = self.tool.get_result()
            self.assert_is_not_none(iso_job)
            self._check_warning_messages('Unable to find valid tubes for ' \
                                         'the following pools: 1063102.')


class StockSampleCreationIsoResetterTestCase(StockSampleCreationTestCase3):

    def set_up(self):
        StockSampleCreationTestCase3.set_up(self)
        self.number_isos = 2
        self.use_isos = []

    def tear_down(self):
        StockSampleCreationTestCase3.tear_down(self)
        del self.use_isos

    def _create_tool(self):
        self.tool = StockSampleCreationIsoResetter(isos=self.use_isos)

    def _continue_setup(self, file_name=None):
        StockSampleCreationTestCase3._continue_setup(self,
                                                     file_name=file_name)
        self.use_isos = self.isos.values()
        self._create_tool()

    def __check_result(self, num_isos):
        for iso in self.isos.values():
            self.assert_is_not_none(iso.molecule_design_pool_set)
            self.assert_not_equal(
                            len(iso.rack_layout.tagged_rack_position_sets), 0)
        isos = self.tool.get_result()
        self.assert_is_not_none(isos)
        self.assert_equal(len(isos), num_isos)
        for iso in isos:
            self.assert_is_none(iso.molecule_design_pool_set)
            self.assert_equal(len(iso.rack_layout.tagged_rack_position_sets), 0)
        for iso in self.isos.values():
            if iso in self.use_isos:
                meth1 = self.assert_is_none
                meth2 = self.assert_equal
            else:
                meth1 = self.assert_is_not_none
                meth2 = self.assert_not_equal
            meth1(iso.molecule_design_pool_set)
            meth2(*(len(iso.rack_layout.tagged_rack_position_sets), 0))

    def test_result(self):
        self._continue_setup()
        self.__check_result(2)

    def test_result_only_one(self):
        self._continue_setup()
        self.use_isos = [self.isos[1]]
        self._create_tool()
        self.__check_result(1)

    def test_invalid_input(self):
        self._continue_setup()
        self.use_isos = dict()
        self._test_and_expect_errors('The ISO list must be a list object ' \
                                     '(obtained: dict)')
        self.use_isos = [self._create_lab_iso()]
        self._test_and_expect_errors('The ISO must be a ' \
                        'StockSampleCreationIso object (obtained: LabIso).')
        self.use_isos = []
        self._test_and_expect_errors('The ISO list is empty!')
        iso = self.isos[1]
        iso.status = ISO_STATUS.CANCELLED
        self.use_isos = [iso]
        self._test_and_expect_errors('The following ISOs cannot be reset ' \
            'because there are either completed or cancelled: ssgen_test_01.')
        iso.status = ISO_STATUS.DONE
        self._test_and_expect_errors('The following ISOs cannot be reset ' \
            'because there are either completed or cancelled: ssgen_test_01.')
