"""
Tests job creation of lab ISO requests.

AAB
"""
from everest.testing import RdbContextManager
from thelma.automation.tools.iso.lab.base import LABELS
from thelma.automation.tools.iso.lab.jobcreator import LabIsoJobCreator
from thelma.automation.tools.iso.lab.planner import LabIsoPlanner
from thelma.automation.tools.iso.lab.planner import LibraryIsoPlanner
from thelma.automation.utils.layouts import FLOATING_POSITION_TYPE
from thelma.interfaces import IUser
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import IsoAliquotPlate
from thelma.models.iso import IsoJobPreparationPlate
from thelma.models.iso import IsoPreparationPlate
from thelma.models.iso import LabIso
from thelma.models.job import IsoJob
from thelma.models.library import LibraryPlate
from thelma.models.moleculedesign import MoleculeDesignPoolSet
from thelma.models.racklayout import RackLayout
from thelma.tests.tools.iso.lab.utils import LAB_ISO_TEST_CASES
from thelma.tests.tools.iso.lab.utils import LabIsoTestCase1
from thelma.tests.tools.iso.lab.utils import POOL_WITHOUT_STOCK_SAMPLE


# TODO: in some cases the process job first flag is not set correctly during
# file upload (e.g. CASE_ASSOCIATION_DIRECT: false false). Fixing this requires
# adjustment of the rack sector associator. I postpone this here, because
# are things are working in principle (also for these cases).

class _LabIsoPlannerDummy(LabIsoPlanner):
    """
    This dummy only reduces the number of transfers required for a CyBio
    to simplify sector testing.
    """
    _MIN_CYBIO_TRANSFER_NUMBER = 6


class _LabIsoJobCreatorDummy(LabIsoJobCreator):
    """
    This dummy only reduces the number of transfers required for a CyBio
    to simplify sector testing.
    """
    def __init__(self, use_library_planner, **kw):
        LabIsoJobCreator.__init__(self, **kw)
        self.use_library_planner = use_library_planner

    def _get_builder_cls(self):
        if self.use_library_planner:
            return LibraryIsoPlanner
        else:
            return _LabIsoPlannerDummy


class LabIsoJobCreatorTestCase(LabIsoTestCase1):

    def set_up(self):
        LabIsoTestCase1.set_up(self)
        self.user = self._get_entity(IUser)
        self.excluded_racks = None
        self.requested_tubes = None
        self.compare_floating_pools = False
        self.use_library_planner = False
        self.case = LAB_ISO_TEST_CASES.CASE_ORDER_ONLY

    def tear_down(self):
        LabIsoTestCase1.tear_down(self)
        del self.excluded_racks
        del self.requested_tubes
        del self.use_library_planner

    def _create_tool(self):
        self.tool = _LabIsoJobCreatorDummy(iso_request=self.iso_request,
                     job_owner=self.user,
                     number_isos=self.number_isos,
                     excluded_racks=self.excluded_racks,
                     requested_tubes=self.requested_tubes,
                     use_library_planner=self.use_library_planner)

    def _continue_setup(self, file_name=None):
        LabIsoTestCase1._continue_setup(self, file_name=file_name)
        if LAB_ISO_TEST_CASES.is_library_case(self.case):
            self.use_library_planner = True
        self._create_tool()

    def _check_result(self):
        iso_job = self.tool.get_result()
        self.assert_is_not_none(iso_job)
        self.__check_iso_job_entity(iso_job)
        self.__check_general_iso_properties(iso_job)
        self.__check_job_preparation_plates(iso_job)
        for iso in iso_job.isos:
            self.__check_final_iso_layout(iso)
            self.__check_final_iso_plates(iso)
            self.__check_iso_preparation_plates(iso)
        self._compare_worklist_series()
        self._compare_worklist_series(iso_job)
        self.__check_pool_sets(iso_job)

    def __check_iso_job_entity(self, iso_job):
        self.assert_true(isinstance(iso_job, IsoJob))
        self.assert_equal(iso_job.label, '123_job_01')
        self.assert_equal(iso_job.user, self.user)
        self.assert_equal(iso_job.number_stock_racks,
                LAB_ISO_TEST_CASES.get_number_job_stock_racks(self.case))
        self.assert_equal(iso_job.iso_job_stock_racks, [])

    def __check_general_iso_properties(self, iso_job):
        exp_labels = LAB_ISO_TEST_CASES.ISO_LABELS[self.case]
        self.assert_equal(len(iso_job.isos), len(exp_labels))
        isos = dict()
        for iso in iso_job.isos:
            self.assert_true(isinstance(iso, LabIso))
            isos[iso.label] = iso
        self.assert_equal(sorted(isos.keys()), sorted(exp_labels))
        excluded_racks_str = None
        if not self.excluded_racks is None:
            excluded_racks_str = '{%s}' % (', '.join(self.excluded_racks))
        requested_tubes_str = None
        if not self.requested_tubes is None:
            requested_tubes_str = '{%s}' % (', '.join(self.excluded_racks))
        for iso_label, iso in isos.iteritems():
            self.assert_equal(iso.number_stock_racks,
                LAB_ISO_TEST_CASES.get_number_iso_stock_racks(self.case)\
                [iso_label])
            self.assert_equal(iso.status, ISO_STATUS.QUEUED)
            self.assert_equal(iso.iso_job.label, iso_job.label)
            self.assert_equal(iso.iso_stock_racks, [])
            self.assert_equal(iso.iso_sector_stock_racks, [])
            self.assert_equal(iso.optimizer_excluded_racks,
                              excluded_racks_str)
            self.assert_equal(iso.optimizer_required_racks,
                              requested_tubes_str)

    def __check_job_preparation_plates(self, iso_job):
        exp_job_data = LAB_ISO_TEST_CASES.get_job_plate_layout_data(self.case)
        self.assert_equal(len(exp_job_data),
                          len(iso_job.iso_job_preparation_plates))
        found_labels = []
        for prep_plate in iso_job.iso_job_preparation_plates:
            self.assert_true(isinstance(prep_plate, IsoJobPreparationPlate))
            self.assert_equal(prep_plate.iso_job.label, iso_job.label)
            self.assert_is_not_none(prep_plate.rack)
            rack_label = prep_plate.rack.label
            if not iso_job.label in rack_label:
                msg = 'The ISO job label (%s) is not part of the job ' \
                      'preparation plate label (%s.)' % (rack_label,
                                                         iso_job.label)
                raise AssertionError(msg)
            found_labels.append(rack_label)
            layout_data = exp_job_data[rack_label]
            self._compare_preparation_layout(layout_data,
                            prep_plate.rack_layout, rack_label, is_job=True)
        self.assert_equal(sorted(found_labels), sorted(exp_job_data.keys()))

    def __check_final_iso_plates(self, iso):
        self.assert_equal(len(iso.final_plates),
                          self.iso_request.number_aliquots)
        exp_plate_labels = LAB_ISO_TEST_CASES.get_final_plate_labels(self.case)\
                           [iso.label]
        self.assert_equal(len(iso.final_plates), len(exp_plate_labels))
        found_labels = []
        is_lib_case = (self.case in LAB_ISO_TEST_CASES.LIBRARY_CASES)
        if is_lib_case:
            exp_shape = LAB_ISO_TEST_CASES.get_library_plate_shape(self.case)
            exp_cls = LibraryPlate
        else:
            exp_shape = LAB_ISO_TEST_CASES.get_aliquot_plate_shape(self.case)
            exp_cls = IsoAliquotPlate
        for final_plate in iso.final_plates:
            plate_label = final_plate.rack.label
            found_labels.append(plate_label)
            self.assert_true(isinstance(final_plate, exp_cls))
            self.assert_is_not_none(final_plate.rack)
            self.assert_equal(final_plate.rack.rack_shape.name, exp_shape)
        self.assert_equal(sorted(found_labels), sorted(exp_plate_labels))

    def __check_final_iso_layout(self, iso):
        exp_layout_data = LAB_ISO_TEST_CASES.get_final_plate_layout_data(
                                                        self.case)[iso.label]
        self._compare_final_iso_layout(exp_layout_data, iso.rack_layout,
                                       iso.label)

    def __check_iso_preparation_plates(self, iso):
        plate_data = LAB_ISO_TEST_CASES.get_prep_plate_layout_data(self.case)
        exp_layout_data = dict()
        for plate_label, layout_data in plate_data.iteritems():
            if iso.label in plate_label:
                exp_layout_data[plate_label] = layout_data
        self.assert_equal(len(exp_layout_data),
                          len(iso.iso_preparation_plates))
        found_labels = []
        for prep_plate in iso.iso_preparation_plates:
            self.assert_true(isinstance(prep_plate, IsoPreparationPlate))
            self.assert_equal(prep_plate.iso.label, iso.label)
            self.assert_is_not_none(prep_plate.rack)
            rack_label = prep_plate.rack.label
            if not iso.label in rack_label:
                msg = 'The ISO label (%s) is not part of the preparation ' \
                      'plate label (%s.)' % (rack_label, iso.label)
                raise AssertionError(msg)
            found_labels.append(rack_label)
            layout_data = exp_layout_data[rack_label]
            self._compare_preparation_layout(layout_data,
                        prep_plate.rack_layout, rack_label)
        self.assert_equal(sorted(found_labels), sorted(exp_layout_data.keys()))

    def __check_pool_sets(self, iso_job):
        exp_pool_sets = LAB_ISO_TEST_CASES.get_pool_set_data(self.case)
        ir_pool_set = self.iso_request.molecule_design_pool_set
        found_pools = set()
        for iso in iso_job:
            pool_set = iso.molecule_design_pool_set
            if exp_pool_sets is None:
                self.assert_is_none(pool_set)
            else:
                self.assert_equal(len(pool_set), len(exp_pool_sets[iso.label]))
                for pool in pool_set:
                    self.assert_false(pool in found_pools)
                    found_pools.add(pool)
                    self.assert_true(pool in ir_pool_set)

    def __test_and_expect_success(self, case_name):
        self._load_iso_request(case_name)
        self._check_result()

    def test_result_case_order_only(self):
        self.number_isos = 1
        self.__test_and_expect_success(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)

    def test_result_case_no_job_direct(self):
        self.number_isos = 1
        self.__test_and_expect_success(LAB_ISO_TEST_CASES.CASE_NO_JOB_DIRECT)

    def test_result_case_no_job_1_prep(self):
        self.number_isos = 1
        self.__test_and_expect_success(LAB_ISO_TEST_CASES.CASE_NO_JOB_1_PREP)

    def test_result_case_no_job_complex(self):
        self.number_isos = 1
        self.__test_and_expect_success(LAB_ISO_TEST_CASES.CASE_NO_JOB_COMPLEX)

    def test_result_case_association_direct(self):
        self.__test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)

    def test_result_case_association_96(self):
        self.__test_and_expect_success(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_96)

    def test_result_case_association_simple(self):
        self.__test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE)

    def test_result_case_assocation_no_cybio(self):
        self.__test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_NO_CYBIO)
        self._check_warning_messages('It would be possible to use the CyBio ' \
                'to transfer fixed and floating positions, but since there ' \
                'are only 4 pools to be transferred the use of the CyBio ' \
                'is disabled (current limit: 6 pools).')

    def test_result_case_association_2_aliquots(self):
        self.__test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_2_ALIQUOTS)

    def test_result_case_association_job_last(self):
        self.__test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_JOB_LAST)

    def test_result_case_association_several_concentrations(self):
        self.__test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SEVERAL_CONC)

    def test_result_case_library_simple(self):
        self.__test_and_expect_success(LAB_ISO_TEST_CASES.CASE_LIBRARY_SIMPLE)

    def test_result_case_library_2_aliquots(self):
        self.__test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_LIBRARY_2_ALIQUOTS)

    def test_excluded_racks(self):
        with RdbContextManager() as session:
            self._continue_setup()
            pool_id = 180005
            # get racks to be excluded
            query = 'SELECT r.barcode AS rack_barcode ' \
                    'FROM rack r, containment rc, sample s, stock_sample ss ' \
                    'WHERE r.rack_id = rc.holder_id ' \
                    'AND r.rack_type = \'TUBERACK\' ' \
                    'AND rc.held_id = s.container_id ' \
                    'AND ss.sample_id = s.sample_id ' \
                    'AND ss.molecule_design_set_id = %i' % (pool_id)
            result = session.query('rack_barcode').from_statement(query).all()
            rack_barcodes = []
            for record in result:
                rack_barcodes.append(record[0])
            self.excluded_racks = rack_barcodes
            self._test_and_expect_errors('Could not find stock tubes for ' \
                        'the following fixed (control pools): 180005 (7 ul)')

    def test_invalid_input_values(self):
        self._continue_setup()
        ori_ir = self.iso_request
        self.iso_request = None
        self._test_and_expect_errors('The ISO request must be a LabIsoRequest' \
                                     ' object (obtained: NoneType)')
        self.iso_request = ori_ir
        ori_owner = self.user
        self.user = self.user.username
        self._test_and_expect_errors('The job owner must be a User object ' \
                                     '(obtained: unicode)')
        self.user = ori_owner
        self.excluded_racks = {}
        self._test_and_expect_errors('The excluded rack list must be a list ' \
                                     'object (obtained: dict)')
        self.excluded_racks = [1]
        self._test_and_expect_errors('The excluded rack must be a basestring ' \
                                     'object (obtained: int)')
        self.excluded_racks = None
        self.requested_tubes = {}
        self._test_and_expect_errors('The requested tube list must be a list ' \
                                     'object (obtained: dict)')
        self.requested_tubes = [1]
        self._test_and_expect_errors('The requested tube must be a ' \
                                     'basestring object (obtained: int)')

    def test_iso_request_error(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE)
        ori_layout = self.iso_request.rack_layout
        self.iso_request.rack_layout = RackLayout()
        self._test_and_expect_errors('Error when trying to convert ISO ' \
                                     'request layout.')
        self.iso_request.rack_layout = ori_layout
        self.iso_request.molecule_design_pool_set = None
        self._test_and_expect_errors('There are no molecule design pools in ' \
                'the molecule design pool set although there are ' \
                'floating positions!')

    def test_sevaral_isos_request_but_no_floatings(self):
        self.number_isos = 3
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)
        ij = self.tool.get_result()
        self.assert_is_not_none(ij)
        self._check_warning_messages('You have requested 3 ISOs. The system ' \
                'will only generate 1 ISO though, because there are no ' \
                'floating positions for this ISO request.')

    def test_not_enough_floating_pools_left(self):
        self.number_isos = 10
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE)
        ij = self.tool.get_result()
        self.assert_is_not_none(ij)
        self._check_warning_messages('You have requested 10 ISOs. ' \
                'The system will only generate 3 ISO though, because there ' \
                'are no more floating positions left for this ISO request')

    def test_above_stock_concentration(self):
        self._continue_setup()
        ir_layout = self._get_layout_from_iso_request()
        for ir_pos in ir_layout.working_positions():
            if ir_pos.is_fixed: ir_pos.iso_concentration = 30000
        self.iso_request.rack_layout = ir_layout.create_rack_layout()
        self._test_and_expect_errors('The ISO concentration for some ' \
            'positions is larger than the stock concentration for the pool: ' \
            'B4 (ISO: 30000 nM, stock: 10000 nM), B8 (ISO: 30000 nM, ' \
            'stock: 10000 nM)')

    def test_no_unused_pools_left(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE)
        iso = self._create_lab_iso(iso_request=self.iso_request,
                 label='123_iso_00',
                 molecule_design_pool_set=\
                                    self.iso_request.molecule_design_pool_set)
        self._test_and_expect_errors('There are no unused molecule design ' \
                                     'pools left!')
        iso.status = ISO_STATUS.CANCELLED
        self._create_tool()
        self._check_result()

    def test_invalid_rack_sectors(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE)
        ir_layout = self._get_layout_from_iso_request()
        for ir_pos in ir_layout.working_positions():
            if ir_pos.is_floating:
                ir_pos.iso_volume = 99
                break
        self.iso_request.rack_layout = ir_layout.create_rack_layout()
        self._test_and_expect_errors('The values for the floating positions ' \
                '(ISO volume and ISO concentration) for the floating ' \
                'positions in the ISO request layout do not comply to ' \
                'the rack sectors! In the current layout samples would be ' \
                'treated differently!')

    def test_order_change(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_JOB_LAST)
        self.iso_request.process_job_first = True
        ij = self.tool.get_result()
        self.assert_is_not_none(ij)
        self._check_warning_messages('The order of job and ISO processing ' \
             'has been changed (from True to False - "True" means job first)')

    def test_floating_candidates_picking_error(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        pool = self._get_pool(POOL_WITHOUT_STOCK_SAMPLE)
        pool_set = MoleculeDesignPoolSet(pool.molecule_type,
                                         molecule_design_pools={pool})
        self.iso_request.molecule_design_pool_set = pool_set
        self._test_and_expect_errors('Error when trying to find floating ' \
                                     'tube candidates!')

    def test_fixed_candidates_picking_error(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE)
        ir_layout = self._get_layout_from_iso_request()
        pool = self._get_pool(POOL_WITHOUT_STOCK_SAMPLE)
        for ir_pos in ir_layout.working_positions():
            if ir_pos.is_fixed and ir_pos.molecule_design_pool.id == 205201:
                ir_pos.molecule_design_pool = pool
        self.iso_request.rack_layout = ir_layout.create_rack_layout()
        self._test_and_expect_errors('Could not find stock tubes for the ' \
                'following fixed (control pools): 689600 (7 ul).')

    def test_library_with_floatings(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_LIBRARY_SIMPLE)
        ir_layout = self._get_layout_from_iso_request()
        for ir_pos in ir_layout.working_positions():
            if ir_pos.is_library:
                ir_pos.position_type = FLOATING_POSITION_TYPE
                ir_pos.molecule_design_pool = 'md_001'
                break
        self.iso_request.rack_layout = ir_layout.create_rack_layout()
        self._test_and_expect_errors('There are both library and floating ' \
                                     'positions in the ISO request layout!')

    def test_library_missing(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_LIBRARY_SIMPLE)
        self.iso_request.molecule_design_library = None
        self._create_tool()
        self._test_and_expect_errors('There is no library for this ISO ' \
                                     'request!')

    def test_library_no_layouts_in_the_queue(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_LIBRARY_SIMPLE)
        for layout_num in self.library_generator.POOL_IDS.keys():
            lib_plate = self.library_generator.library_plates[layout_num][0]
            iso = self._create_lab_iso(iso_request=self.iso_request)
            iso.library_plates.append(lib_plate)
        self._test_and_expect_errors('There are no unused library layouts ' \
                                     'left for this ISO request!')

    def test_not_enough_layouts_left(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_LIBRARY_SIMPLE)
        for layout_num in self.library_generator.POOL_IDS.keys():
            if layout_num == 3: continue # we build 2 ISOs
            lib_plate = self.library_generator.library_plates[layout_num][0]
            iso_label = LABELS.create_iso_label(123, layout_num)
            iso = self._create_lab_iso(iso_request=self.iso_request,
                                       label=iso_label)
            iso.library_plates.append(lib_plate)
        ij = self.tool.get_result()
        self.assert_is_not_none(ij)
        self._check_warning_messages('You have requested 2 ISOs. The system ' \
            'will only generate 1 ISO though, because there are no more ' \
            'library layouts left for this ISO request.')

    def test_library_no_usued_plates_left(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_LIBRARY_SIMPLE)
        lib_plates = self.library_generator.library_plates[1]
        for lib_plate in lib_plates:
            lib_plate.has_been_used = True
        ij = self.tool.get_result()
        self.assert_is_not_none(ij)
        self._check_warning_messages('There are no unused library plates ' \
                'left for some layout numbers that are still in the queue: 1.')

    def test_library_not_enough_plates_left(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_LIBRARY_2_ALIQUOTS)
        lib_plates = self.library_generator.library_plates[1]
        for lib_plate in lib_plates:
            lib_plate.has_been_used = True
        lib_plates[0].has_been_used = False
        ij = self.tool.get_result()
        self.assert_is_not_none(ij)
        self._check_warning_messages('There are not enough unused library ' \
                'plates left for some layout numbers that are still in the ' \
                'queue: 1 (1 plates).')

    def test_library_no_layout_with_sufficient_plates(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_LIBRARY_2_ALIQUOTS)
        for layout_num in self.library_generator.POOL_IDS.keys():
            lib_plates = self.library_generator.library_plates[layout_num]
            for lib_plate in lib_plates:
                lib_plate.has_been_used = True
            lib_plates[0].has_been_used = False
        self._test_and_expect_errors('Cannot generate ISOs because there ' \
            'is no sufficient number of library plates left for any layout ' \
            'still in the queue (1, 2, 3).')
