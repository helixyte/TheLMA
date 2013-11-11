"""
Tests job creation of lab ISO requests.

AAB
"""
from thelma.automation.tools.iso.lab.jobcreator import LabIsoJobCreator
from thelma.interfaces import IUser
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import IsoAliquotPlate
from thelma.models.iso import IsoJobPreparationPlate
from thelma.models.iso import IsoPreparationPlate
from thelma.models.iso import LabIso
from thelma.models.job import IsoJob
from thelma.models.library import LibraryPlate
from thelma.tests.tools.iso.lab.utils import LAB_ISO_TEST_CASES
from thelma.tests.tools.iso.lab.utils import LabIsoTestCase

class LabIsoJobCreatorTestCase(LabIsoTestCase):

    def set_up(self):
        LabIsoTestCase.set_up(self)
        self.user = self._get_entity(IUser)
        self.excluded_racks = None
        self.requested_tubes = None

    def tear_down(self):
        LabIsoTestCase.tear_down(self)
        del self.excluded_racks
        del self.requested_tubes

    def _create_tool(self):
        self.tool = LabIsoJobCreator(iso_request=self.iso_request,
                     job_owner=self.user,
                     number_isos=self.number_isos,
                     excluded_racks=self.excluded_racks,
                     requested_tubes=self.requested_tubes)

    def _continue_setup(self, file_name=None):
        LabIsoTestCase._continue_setup(self, file_name=file_name)
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
        exp_layout_data = LAB_ISO_TEST_CASES.get_prep_plate_layout_data(
                                                                    self.case)
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

    def __test_and_expect_success(self, case_name):
        self._load_iso_request(case_name)
        self._check_result()

    def test_result_case_order_only(self):
        self.number_isos = 1
        self.__test_and_expect_success(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)

    def test_result_case_no_job_direct(self):
        self.number_isos = 1
        self.__test_and_expect_success(LAB_ISO_TEST_CASES.CASE_NO_JOB_DIRECT)

    def xtest_result_case_no_job_1_prep(self):
        self.number_isos = 1
        self.__test_and_expect_success(LAB_ISO_TEST_CASES.CASE_NO_JOB_1_PREP)
