"""
Tests for tools that deal with the processing of lab ISOs. This comprises both
the transfers from stock and the actual series processing.

AAB
"""
from thelma.automation.semiconstants import RACK_SPECS_NAMES
from thelma.automation.semiconstants import get_384_rack_shape
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.automation.semiconstants import get_item_status_future
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.iso.lab import get_worklist_executor
from thelma.automation.tools.iso.lab import get_worklist_writer
from thelma.automation.tools.iso.lab.base import FinalLabIsoLayout
from thelma.automation.tools.iso.lab.base import FinalLabIsoPosition
from thelma.automation.tools.iso.lab.base import LABELS
from thelma.automation.tools.iso.lab.base import LAB_ISO_ORDERS
from thelma.automation.tools.iso.lab.base import LabIsoPrepLayout
from thelma.automation.tools.iso.lab.base import LabIsoPrepPosition
from thelma.automation.tools.iso.lab.processing import LabIsoPlateVerifier
from thelma.automation.tools.iso.lab.processing import WriterExecutorIsoJob
from thelma.automation.tools.iso.lab.processing import WriterExecutorLabIso
from thelma.automation.tools.iso.lab.processing import _LabIsoWriterExecutorTool
from thelma.automation.tools.worklists.series import SerialWriterExecutorTool
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.utils.layouts import FIXED_POSITION_TYPE
from thelma.automation.utils.layouts import FLOATING_POSITION_TYPE
from thelma.automation.utils.layouts import MOCK_POSITION_TYPE
from thelma.automation.utils.layouts import TransferTarget
from thelma.automation.utils.layouts import UNTRANSFECTED_POSITION_TYPE
from thelma.automation.utils.layouts import UNTREATED_POSITION_TYPE
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import IsoAliquotPlate
from thelma.models.iso import IsoPreparationPlate
from thelma.models.iso import LabIso
from thelma.models.job import IsoJob
from thelma.models.rack import RACK_TYPES
from thelma.models.racklayout import RackLayout
from thelma.models.utils import get_user
from thelma.tests.tools.iso.lab.utils import LAB_ISO_TEST_CASES
from thelma.tests.tools.iso.lab.utils import LabIsoTestCase2
from thelma.tests.tools.iso.lab.utils import TestLibraryGenerator
from thelma.tests.tools.iso.lab.utils import TestTubeGenerator
from thelma.tests.tools.tooltestingutils import FileCreatorTestCase
from thelma.tests.tools.utils.utils import VerifierTestCase


class LabIsoPlateVerifierTestCase(VerifierTestCase):

    def set_up(self):
        VerifierTestCase.set_up(self)
        self.plate_type = RACK_TYPES.PLATE
        self.lab_iso_plate = None
        self.for_job = False
        self.lab_iso_layout = None
        self.test_final_layout = True # other the layout is prep plate layouts
        #: pos label - pool ID, pos type, for job
        self.position_data = dict(
                a1=[205201, FIXED_POSITION_TYPE, True],
                b1=[330001, FIXED_POSITION_TYPE, True],
                c1=[205203, FLOATING_POSITION_TYPE, False],
                d1=[205204, FLOATING_POSITION_TYPE, False],
                e1=[205205, FLOATING_POSITION_TYPE, False])
        self.rack_specs = RACK_SPECS_NAMES.from_name(
                                                RACK_SPECS_NAMES.STANDARD_96)

    def tear_down(self):
        VerifierTestCase.tear_down(self)
        del self.lab_iso_plate
        del self.for_job
        del self.lab_iso_layout
        del self.test_final_layout

    def _create_tool(self):
        self.tool = LabIsoPlateVerifier(self.lab_iso_plate, self.for_job,
                                        lab_iso_layout=self.lab_iso_layout)

    def _init_layout(self):
        if self.test_final_layout:
            self.layout = FinalLabIsoLayout(shape=self.shape)
        else:
            self.layout = LabIsoPrepLayout(shape=self.shape)

    def _get_position_kw(self, pos_label, pos_data):
        kw = dict(rack_position=get_rack_position_from_label(pos_label),
                  molecule_design_pool=self._get_pool(pos_data[0]),
                  concentration=1000,
                  volume=10,
                  position_type=pos_data[1])
        if self.test_final_layout:
            kw['from_job'] = pos_data[2]
        else:
            kw['external_targets'] = [TransferTarget(kw['rack_position'],
                                                     1, 'a')]
        return kw

    def _add_position(self, pos_label, pos_data):
        kw = self._get_position_kw(pos_label, pos_data)
        if self.test_final_layout:
            pos_cls = FinalLabIsoPosition
        else:
            pos_cls = LabIsoPrepPosition
        pos = pos_cls(**kw)
        self.layout.add_position(pos)

    def _fill_rack(self, session):
        for well in self.rack.containers:
            pos_label = well.location.position.label.lower()
            if not self.position_data.has_key(pos_label): continue
            pos_data = self.position_data[pos_label]
            if self.test_final_layout:
                if pos_data[2] == self.for_job:
                    continue
            else:
                pos_type = pos_data[1]
                if pos_type == FIXED_POSITION_TYPE and self.for_job:
                    continue
                elif pos_type == FLOATING_POSITION_TYPE and not self.for_job:
                    continue
            self._add_sample(well, pos_data[0])

    def _create_other_objects(self):
        iso = self._create_lab_iso()
        if self.test_final_layout:
            self.lab_iso_plate = IsoAliquotPlate(iso=iso, rack=self.rack)
            self.lab_iso_layout = self.layout
        else:
            self.lab_iso_plate = IsoPreparationPlate(iso=iso, rack=self.rack,
                                 rack_layout=self.layout.create_rack_layout())

    def test_result_aliquot_plate_iso(self):
        self._continue_setup()
        self._test_and_expect_compliance()

    def test_result_aliquot_plate_job(self):
        self.for_job = True
        self._continue_setup()
        self._test_and_expect_compliance()

    def test_result_library_plate(self):
        self.for_job = True
        self._continue_setup()
        lib_creator = TestLibraryGenerator()
        self.lab_iso_plate = self._create_library_plate(
                            molecule_design_library=lib_creator.library,
                            rack=self.rack)
        self._test_and_expect_compliance()

    def test_result_prep_plate_iso(self):
        self.test_final_layout = False
        self._continue_setup()
        self._test_and_expect_compliance()

    def test_result_prep_plate_job(self):
        self.test_final_layout = False
        self.for_job = True
        self._continue_setup()
        self._test_and_expect_compliance()

    def test_result_job_prep_plate(self):
        self.test_final_layout = False
        self.for_job = True
        self._continue_setup()
        iso_job = self._create_iso_job(isos=[self.lab_iso_plate.iso])
        self.lab_iso_plate = self._create_iso_job_preparation_plate(
                                            iso_job=iso_job, rack=self.rack)
        self._test_and_expect_compliance()

    def test_invalid_input_values(self):
        self._continue_setup()
        ori_plate = self.lab_iso_plate
        self.lab_iso_plate = self.lab_iso_plate.rack
        self._test_and_expect_errors('The lab ISO plate must be an ' \
                'IsoPlate, LibraryPlate or an IsoJobPreparationPlate ' \
                '(obtained: Plate).')
        self.lab_iso_plate = ori_plate
        self.for_job = None
        self._test_and_expect_errors('The "for job" flag must be a bool ' \
                                     'object (obtained: NoneType).')
        self.for_job = False
        self.lab_iso_layout = 123
        self._test_and_expect_errors('The reference layout must be a ' \
                                     'LabIsoLayout object (obtained: int)')
        self.lab_iso_layout = None
        self._test_and_expect_errors('The reference layout for a final ISO ' \
                                     'plate must not be None!')

    def test_layout_conversion_error(self):
        self.test_final_layout = False
        self._continue_setup()
        self.lab_iso_plate.rack_layout = RackLayout(shape=self.shape)
        self._test_and_expect_errors('Error when trying to convert ' \
                                     'preparation plate layout!')

    def test_unexpected_plate_type(self):
        self.test_final_layout = False
        self._continue_setup()
        self.lab_iso_plate = self._create_iso_sector_preparation_plate()
        self._test_and_expect_errors('Unexpected ISO plate type: ' \
                                     'IsoSectorPreparationPlate')

    def test_and_expect_missing_sample(self):
        self._continue_setup()
        rack_pos = get_rack_position_from_label('g8')
        tt = TransferTarget(rack_pos, 1)
        # without transfer target the position is ignored
        fp = FinalLabIsoPosition(rack_position=rack_pos,
                                 molecule_design_pool=self._get_pool(205215),
                                 position_type=FIXED_POSITION_TYPE,
                                 concentration=1000, volume=10, from_job=True,
                                 transfer_targets=[tt])
        self.layout.add_position(fp)
        self._test_and_expect_missing_sample()

    def test_and_expect_additional_samples(self):
        self._continue_setup()
        rack_pos = get_rack_position_from_label('a1')
        self.layout.del_position(rack_pos)
        self._test_and_expect_additional_samples()

    def test_and_expect_mismatching_samples(self):
        self._continue_setup()
        rack_pos = get_rack_position_from_label('a1')
        fp = self.layout.get_working_position(rack_pos)
        fp.molecule_design_pool = self._get_pool(205215)
        tt = TransferTarget(rack_pos, 1)
        fp.transfer_targets = [tt] # otherwise the position is ignored
        self._test_and_expect_mismatching_samples()

    def test_and_expect_rack_shape_mismatch(self):
        self.shape = get_384_rack_shape()
        self._continue_setup()
        self._test_and_expect_rack_shape_mismatch()


class _LabIsoWriterExecutorToolTestCase(LabIsoTestCase2,
                                        FileCreatorTestCase):

    def set_up(self):
        LabIsoTestCase2.set_up(self)
        self.mode = None
        self.iso_status = ISO_STATUS.QUEUED
        self.tube_generator = None
        self.processing_order = None
        self.stock_tube_start_vol = 100 / VOLUME_CONVERSION_FACTOR
        self.final_plates = dict()
        self.prep_plates = dict()
        self.job_plates = dict()
        self.executor_user = get_user('tondera')
        self.new_iso_status = None
        self.num_files = 0
        self.num_executed_processing_worklists = 0
        self.inaccurate_concentrations = dict()
        self.inactivated_pool_id = None
        self.inactivated_positions = set()

    def tear_down(self):
        LabIsoTestCase2.tear_down(self)
        del self.mode
        del self.iso_status
        del self.tube_generator
        del self.processing_order
        del self.stock_tube_start_vol
        del self.final_plates
        del self.prep_plates
        del self.job_plates
        del self.new_iso_status
        del self.num_files
        del self.num_executed_processing_worklists
        del self.inaccurate_concentrations
        del self.inactivated_pool_id
        del self.inactivated_positions

    def _continue_setup(self, file_name=None):
        LabIsoTestCase2._continue_setup(self, file_name=file_name)
        self._generate_stock_racks(entity=self.entity)
        self.__fill_stock_racks()
        iso_status = self.__get_iso_status()
        self.__sort_plates()
        if not iso_status == ISO_STATUS.QUEUED:
            self.__fill_plates()
        self._create_tool()

    def _create_tool(self):
        if self.mode == SerialWriterExecutorTool.MODE_PRINT_WORKLISTS:
            self.tool = get_worklist_writer(entity=self.entity)
        else:
            self.tool = get_worklist_executor(entity=self.entity,
                                              user=self.executor_user)

    def __fill_stock_racks(self):
        try:
            self.tube_generator = TestTubeGenerator(self.rack_generator.\
                                                tube_rack_specs.tube_specs[0])
        except AttributeError:
            pass
        for rack_label in self.stock_racks.keys():
            layout = self.stock_rack_layouts[rack_label]
            rack = self.rack_generator.label_map[rack_label]
            for rack_pos, sr_pos in layout.iterpositions():
                pool = sr_pos.molecule_design_pool
                if pool.id == self.inactivated_pool_id: continue
                self.tube_generator.create_tube(rack=rack, rack_pos=rack_pos,
                                pool=pool, tube_barcode=sr_pos.tube_barcode,
                                volume=self.stock_tube_start_vol)

    def __get_iso_status(self):
        self.processing_order = LAB_ISO_ORDERS.get_order(self.entity)
        if (self.processing_order == LAB_ISO_ORDERS.JOB_FIRST and \
                                                            not self.FOR_JOB):
            iso_status = ISO_STATUS.IN_PROGRESS
        elif (self.processing_order == LAB_ISO_ORDERS.ISO_FIRST and \
                                                            self.FOR_JOB):
            iso_status = ISO_STATUS.IN_PROGRESS
        else:
            iso_status = ISO_STATUS.QUEUED
        for iso in self.isos.values():
            iso.status = iso_status
        return iso_status

    def __sort_plates(self):
        for iso_label, iso in self.isos.iteritems():
            if not self.FOR_JOB and not iso_label == self._USED_ISO_LABEL:
                continue
            for iap in iso.final_plates:
                plate = iap.rack
                self.final_plates[plate.label] = plate
            for ipp in iso.iso_preparation_plates:
                plate = ipp.rack
                self.prep_plates[plate.label] = plate
        if self.FOR_JOB:
            for ijpp in self.iso_job.iso_job_preparation_plates:
                plate = ijpp.rack
                self.job_plates[plate.label] = plate

    def __fill_plates(self):
        plate_data = LAB_ISO_TEST_CASES.get_plate_intermediate_data(self.case)
        for plate_label, starting_data in plate_data.iteritems():
            plate = self.rack_generator.label_map[plate_label]
            for well in plate.containers:
                pos_label = well.location.position.label.lower()
                if not starting_data.has_key(pos_label): continue
                pos_data = starting_data[pos_label]
                sample_hash = '%s:%s' % (plate_label, pos_label)
                if sample_hash in self.inactivated_positions:
                    continue
                pool = self._get_pool(pos_data[0])
                if not well.sample is None:
                    msg = 'There is already a sample for position %s in ' \
                          'plate %s.' % (pos_label, plate_label)
                    raise ValueError(msg)
                self._create_test_sample(well, pool, volume=pos_data[1],
                                         target_conc=pos_data[2])

    def _test_and_expect_success(self, case_name):
        self._load_iso_request(case_name)
        self._check_result()

    def _check_result(self):
        if self.mode == self.tool.MODE_PRINT_WORKLISTS:
            self.__check_result_writer()
        else:
            self.__check_result_executor()

    def _test_and_expect_no_processing(self, case_name):
        self._load_iso_request(case_name)
        if self.FOR_JOB:
            msg = 'There are no samples added via the ISO job, thus there is ' \
                  'no job processing required!'
        else:
            msg = 'All samples for this ISO are handled by the ISO job, ' \
                  'thus, there is no specific ISO handling required!'
        self._test_and_expect_errors(msg)

    def __check_result_writer(self):
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        self.assert_is_none(self.tool.get_executed_stock_worklists())
        self.__check_zip_stream(zip_stream)
        self.__check_writer_entities()

    def __check_zip_stream(self, zip_stream):
        archive = self._get_zip_archive(zip_stream)
        namelist = archive.namelist()
        self.assert_equal(len(namelist), self.num_files)
        if self.inactivated_pool_id is None:
            self.WL_PATH = LAB_ISO_TEST_CASES.get_worklist_file_dir(self.case)
        else:
            self.WL_PATH = LAB_ISO_TEST_CASES.get_worklist_file_dir(
                                                               'inactivation')
        for fn in namelist:
            tool_content = archive.read(fn)
            if self.tool.FILE_NAME_INSTRUCTIONS[2:] in fn:
                self.__compare_instructions_file(tool_content)
            elif '.csv' in fn:
                self._compare_csv_file_content(tool_content, fn)
            else:
                self._compare_txt_file_content(tool_content, fn)

    def __compare_instructions_file(self, tool_content):
        ori_path = self.WL_PATH
        self.WL_PATH = LAB_ISO_TEST_CASES.INSTRUCTIONS_FILE_PATH
        fn = LAB_ISO_TEST_CASES.get_instruction_file(self.case, self.FOR_JOB)
        self._compare_txt_file_content(tool_content, fn)
        self.WL_PATH = ori_path

    def __check_writer_entities(self):
        iso = self.isos[self._USED_ISO_LABEL]
        exp_status = self.__get_iso_status()
        for iso_label, iso in self.isos.iteritems():
            if not self.FOR_JOB and not iso_label == self._USED_ISO_LABEL:
                continue
            self.assert_equal(iso.status, exp_status)
        # we cannot check the plate and rack volumes because the series tools
        # might execute some jobs - as long as the transaction is aborted after
        # worklist generation everything is fine

    def __check_result_executor(self):
        updated_entity = self.tool.get_result()
        self.assert_is_not_none(updated_entity)
        if self.FOR_JOB:
            self.assert_true(isinstance(updated_entity, IsoJob))
        else:
            self.assert_true(isinstance(updated_entity, LabIso))
        for iso_label, iso in self.isos.iteritems():
            if not self.FOR_JOB and not iso_label == self._USED_ISO_LABEL:
                continue
            self.assert_equal(iso.status, self.new_iso_status)
            if self.new_iso_status == ISO_STATUS.DONE:
                self.__check_final_iso_state(iso)
            else:
                self.__check_intermediate_iso_state(iso)
        if self.new_iso_status == ISO_STATUS.DONE:
            self.__check_final_state_job()
        else:
            self.__check_intermediate_state_job()
        self.__check_stock_racks()
        self.__check_processing_worklists()

    def __check_final_iso_state(self, iso):
        # final plates
        final_plate_labels = LAB_ISO_TEST_CASES.\
                             get_final_plate_labels_after_completion(
                                                        self.case)[iso.label]
        found_final_plates = []
        for fp in iso.final_plates:
            plate = fp.rack
            found_final_plates.append(plate.label)
            self.__check_final_iso_plate(plate, iso.label)
        self.assert_equal(len(final_plate_labels),
                          len(found_final_plates))
        # preparation plates
        for ipp in iso.iso_preparation_plates:
            self.__check_final_prep_plate_state(ipp.rack, False, 1)
        # library plates status
        if LAB_ISO_TEST_CASES.is_library_case(self.case) and self.FOR_JOB:
            for lib_plate in iso.library_plates:
                self.assert_true(lib_plate.has_been_used)

    def __check_final_iso_plate(self, plate, iso_label):
        ir_data = LAB_ISO_TEST_CASES.get_iso_request_layout_data(self.case)
        iso_data = LAB_ISO_TEST_CASES.get_final_plate_layout_data(
                                                        self.case)[iso_label]
        sample_wells = []
        for well in plate.containers:
            pos_label = well.location.position.label.lower()
            if not ir_data.has_key(pos_label):
                if not well.sample is None:
                    msg = 'There is an unexpected sample in well %s in ' \
                          'plate %s!' % (pos_label, plate.label)
                    raise AssertionError(msg)
                continue
            ir_details = ir_data[pos_label]
            sample_wells.append(pos_label)
            pos_type = ir_details[1]
            if pos_type in (UNTREATED_POSITION_TYPE,
                            UNTRANSFECTED_POSITION_TYPE):
                if not well.sample is None:
                    msg = 'There is an unexpected sample in well %s in ' \
                          'plate %s (untreated type)!' % (pos_label,
                                                          plate.label)
                    raise AssertionError(msg)
                continue
            sample = well.sample
            sample_info = 'position %s in final plate %s' % (pos_label,
                                                             plate.label)
            sample_hash = '%s:%s' % (plate.label, pos_label)
            if sample_hash in self.inactivated_positions:
                if not sample is None:
                    msg = 'Unexpected sample in %s (%s ul). This sample ' \
                          'should have been inactivated!' % (sample_info,
                           sample.volume * VOLUME_CONVERSION_FACTOR)
                    raise AssertionError(msg)
                continue
            self._compare_sample_volume(sample, ir_details[2], sample_info)
            if pos_type == MOCK_POSITION_TYPE:
                self.assert_equal(len(sample.sample_molecules), 0)
                continue
            if pos_type == FIXED_POSITION_TYPE:
                pool = self._get_pool(ir_details[0])
            else: # floating
                pool = self._get_pool(iso_data[pos_label][0])
            if self.inaccurate_concentrations.has_key(sample_hash):
                conc = self.inaccurate_concentrations[sample_hash]
            else:
                conc = ir_details[3] / float(pool.number_designs)
            self._compare_sample_and_pool(sample, pool, conc, sample_info)
        self.assert_equal(sorted(sample_wells), sorted(ir_data.keys()))

    def __check_final_prep_plate_state(self, plate, is_job_plate, num_execs):
        if is_job_plate:
            plate_inf = LAB_ISO_TEST_CASES.get_job_plate_layout_data(self.case)
        else:
            plate_inf = LAB_ISO_TEST_CASES.get_prep_plate_layout_data(self.case)
            num_execs *= self.iso_request.number_aliquots
        plate_data = plate_inf[plate.label]
        sample_wells = []
        for well in plate.containers:
            pos_label = well.location.position.label.lower()
            if not plate_data.has_key(pos_label):
                if not well.sample is None:
                    msg = 'There is an unexpected sample in well %s in ' \
                          'plate %s!' % (pos_label, plate.label)
                    raise AssertionError(msg)
                continue
            pos_data = plate_data[pos_label]
            sample_wells.append(pos_label)
            sample = well.sample
            sample_info = '%s in plate %s' % (pos_label, plate.label)
            sample_hash = '%s:%s' % (plate.label, pos_label)
            if sample_hash in self.inactivated_positions:
                if not sample is None:
                    msg = 'Unexpected sample in %s. This position should ' \
                          'have been inactivated!' % (sample_info)
                    raise AssertionError(msg)
                continue
            exp_vol = pos_data[2]
            for tt in pos_data[4]: # internal targets
                exp_vol -= (tt.transfer_volume * num_execs)
            for tt in pos_data[5]: # external targets
                exp_vol -= (tt.transfer_volume * num_execs)
            self._compare_sample_volume(sample, exp_vol, sample_info)
            pool = self._get_pool(pos_data[0])
            if self.inaccurate_concentrations.has_key(sample_hash):
                conc = self.inaccurate_concentrations[sample_hash]
            else:
                conc = pos_data[3] / float(pool.number_designs)
            self._compare_sample_and_pool(sample, pool, conc, sample_info)
        self.assert_equal(sorted(sample_wells), sorted(plate_data.keys()))

    def __check_final_state_job(self):
        num_execs = len(self.isos) * self.iso_request.number_aliquots
        for ijpp in self.iso_job.iso_job_preparation_plates:
            self.__check_final_prep_plate_state(ijpp.rack, True, num_execs)

    def __check_intermediate_iso_state(self, iso):
        interm_data = LAB_ISO_TEST_CASES.get_plate_intermediate_data(self.case)
        # final plates
        final_plate_labels = LAB_ISO_TEST_CASES.get_final_plate_labels(
                                                        self.case)[iso.label]
        found_final_plates = []
        for fp in iso.final_plates:
            plate = fp.rack
            found_final_plates.append(plate.label)
            self.__check_intermediate_plate_state(plate, interm_data)
        self.assert_equal(sorted(final_plate_labels),
                          sorted(found_final_plates))
        # iso preparation plates
        prep_plates = LAB_ISO_TEST_CASES.get_prep_plate_layout_data(
                                                        self.case).keys()
        exp_prep_plates = []
        for plate_label in prep_plates:
            if not iso.label in plate_label: continue
            exp_prep_plates.append(plate_label)
        found_prep_plates = []
        for ipp in iso.iso_preparation_plates:
            plate = ipp.rack
            found_prep_plates.append(plate.label)
            self.__check_intermediate_plate_state(plate, interm_data)
        self.assert_equal(sorted(exp_prep_plates), sorted(found_prep_plates))

    def __check_intermediate_state_job(self):
        interm_data = LAB_ISO_TEST_CASES.get_plate_intermediate_data(self.case)
        job_plates = LAB_ISO_TEST_CASES.get_job_plate_layout_data(
                                                            self.case).keys()
        found_job_plates = []
        for ijpp in self.iso_job.iso_job_preparation_plates:
            plate = ijpp.rack
            found_job_plates.append(plate.label)
            self.__check_intermediate_plate_state(plate, interm_data)
        self.assert_equal(sorted(found_job_plates), sorted(job_plates))

    def __check_intermediate_plate_state(self, plate, interm_data):
        if interm_data.has_key(plate.label):
            self.__compare_plate_to_data(plate, interm_data[plate.label])
        else:
            self.__assert_plate_is_empty(plate)

    def __check_stock_racks(self):
        if self.FOR_JOB:
            wl_props = LAB_ISO_TEST_CASES.\
                       get_stock_rack_worklist_series_for_job(self.case)
        else:
            wl_props = LAB_ISO_TEST_CASES.\
                       get_stock_rack_worklist_series_for_iso(self.case)
        takeout_volumes = dict()
        all_ews = []
        for sr_label, stock_rack in self.stock_racks.iteritems():
            values = LABELS.parse_rack_label(sr_label)
            rack_marker = values[LABELS.MARKER_RACK_MARKER]
            # check worklist series
            ws = stock_rack.worklist_series
            exp_wls = dict()
            for wl_label, wl_prop in wl_props.iteritems():
                if rack_marker in wl_label:
                    exp_wls[wl_label] = wl_prop
            self.assert_equal(len(exp_wls), len(ws))
            for wl in ws:
                wl_label = wl.label
                props = exp_wls[wl_label]
                self.assert_equal(wl.pipetting_specs, props[1])
                exec_num = 1
                if self.FOR_JOB:
                    values = LABELS.parse_worklist_label(wl_label)
                    marker = values[LABELS.MARKER_WORKLIST_TARGET]
                    if not LABELS.ROLE_PREPARATION_JOB in marker:
                        exec_num = len(self.isos)
                ews = wl.executed_worklists
                all_ews.extend(ews)
                self.assert_equal(len(ews), exec_num)
                for ew in ews:
                    for elt in ew:
                        src_tube_barcode = elt.source_container.barcode
                        self.assert_equal(elt.user, self.executor_user)
                        self.assert_is_not_none(elt.timestamp)
                        vol = elt.planned_liquid_transfer.volume \
                              * VOLUME_CONVERSION_FACTOR
                        if takeout_volumes.has_key(src_tube_barcode):
                            takeout_volumes[src_tube_barcode] += vol
                        else:
                            takeout_volumes[src_tube_barcode] = vol
            # check rack volumes
            rack = stock_rack.rack
            starting_vol = self.stock_tube_start_vol * VOLUME_CONVERSION_FACTOR
            for tube in rack.containers:
                vol = tube.sample.volume * VOLUME_CONVERSION_FACTOR
                src_tube_barcode = tube.barcode
                exp_vol = starting_vol - takeout_volumes[src_tube_barcode]
                self._compare_sample_volume(tube.sample, exp_vol)
        tool_ews = self.tool.get_executed_stock_worklists()
        self.assert_equal(sorted(tool_ews), sorted(all_ews))

    def __check_processing_worklists(self):
        if self.FOR_JOB:
            exp_proc_wls = LAB_ISO_ORDERS.get_sorted_worklists_for_job(
                                            self.entity, self.processing_order)
        else:
            exp_proc_wls = LAB_ISO_ORDERS.get_sorted_worklists_for_iso(
                                            self.entity, self.processing_order)
        self.assert_equal(len(exp_proc_wls),
                          self.num_executed_processing_worklists)
        for wl in exp_proc_wls:
            exec_num = 1
            if self.FOR_JOB:
                exec_num = len(self.isos) * self.iso_request.number_aliquots
                values = LABELS.parse_worklist_label(wl.label)
                rack_marker = values[LABELS.MARKER_WORKLIST_TARGET]
                if LABELS.ROLE_PREPARATION_JOB in rack_marker:
                    exec_num = 1
                elif LABELS.ROLE_PREPARATION_ISO in rack_marker:
                    exec_num = len(self.isos)
            ews = wl.executed_worklists
            self.assert_equal(len(ews), exec_num)
            for ew in ews:
                for elt in ew:
                    self.assert_equal(elt.user, self.executor_user)
                    self.assert_is_not_none(elt.timestamp)

    def __compare_plate_to_data(self, plate, exp_data):
        for well in plate.containers:
            pos_label = well.location.position.label.lower()
            # plate label - pos_label: pool (or None for buffer only), volume,
            # pool conc
            if not exp_data.has_key(pos_label):
                if not well.sample is None:
                    msg = 'There is an unexpected sample in position %s of ' \
                          'plate %s!' % (pos_label, plate.label)
                    raise AssertionError(msg)
                continue
            sample = well.sample
            pos_data = exp_data[pos_label]
            pool = self._get_pool(pos_data[0])
            sample_info = 'position %s in plate %s' % (pos_label, plate.label)
            sample_hash = '%s:%s' % (plate.label, pos_label)
            if sample_hash in self.inactivated_positions:
                if sample is not None:
                    msg = 'There is a sample for %s. The position should ' \
                          'have not been inactivated!' % (sample_info)
                    raise AssertionError(msg)
                continue
            self._compare_sample_volume(sample, pos_data[1], sample_info)
            if pool is None: # mock type
                self.assert_equal(len(sample.sample_molecules), 0)
                continue
            if self.inaccurate_concentrations.has_key(sample_hash):
                conc = self.inaccurate_concentrations[sample_hash]
            else:
                conc = float(pos_data[2]) / pool.number_designs
            self._compare_sample_and_pool(sample, pool, conc, sample_info)

    def __assert_plate_is_empty(self, plate):
        for well in plate.containers:
            if not well.sample is None:
                msg = 'There is an unexpected sample in position %s of ' \
                      'the empty plate %s!' % (well.location.position.label,
                                               plate.label)
                raise AssertionError(msg)

    def _test_and_expect_errors(self, msg=None):
        LabIsoTestCase2._test_and_expect_errors(self, msg=msg)
        if isinstance(self.tool, _LabIsoWriterExecutorTool):
            self.assert_is_none(self.tool.get_executed_stock_worklists())
            self.assert_is_none(self.tool.get_stock_rack_data())

    def _test_position_inactivation(self):
        self._set_inactivation_data()
        self._load_iso_request()
        self._inactivate_position()
        self._check_result()

    def _set_inactivation_data(self):
        # inactivate pool 205207 (in stock rack 3) in all layouts and remove
        # the data from the stock rack layout and worklists
        self.inactivated_pool_id = 205207
        self.inactivated_positions = {'123_iso_01_a:c4', 'asso_simple_1:c4',
                                      '123_iso_01_p:c4'}
        self.case = LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE

    def _inactivate_position(self):
        for iso_label, iso in self.isos.iteritems():
            layout = self.iso_layouts[iso_label]
            for fp in layout.working_positions():
                if fp.is_floating and \
                        fp.molecule_design_pool.id == self.inactivated_pool_id:
                    fp.inactivate()
            iso.rack_layout = layout.create_rack_layout()
            for ipp in iso.iso_preparation_plates:
                layout = self.prep_layouts[ipp.rack.label]
                for pp in layout.working_positions():
                    if pp.is_floating and \
                       pp.molecule_design_pool.id == self.inactivated_pool_id:
                        pp.inactivate()
                ipp.rack_layout = layout.create_rack_layout()
            for stock_rack in iso.iso_sector_stock_racks:
                layout = self.stock_rack_layouts[stock_rack.label]
                del_positions = set()
                for sr_pos in layout.working_positions():
                    if sr_pos.molecule_design_pool.id \
                                                == self.inactivated_pool_id:
                        del_positions.add(sr_pos.rack_position)
                for rack_pos in del_positions:
                    layout.del_position(rack_pos)
                stock_rack.rack_layout = layout.create_rack_layout()
                ws = stock_rack.worklist_series
                for worklist in ws:
                    plts = worklist.planned_liquid_transfers
                    del_plts = []
                    for plt in worklist:
                        if plt.source_position in del_positions:
                            del_plts.append(plt)
                    for plt in del_plts:
                        plts.remove(plt)

    def _test_invalid_input_values(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE)
        if self.FOR_JOB:
            msg = 'The entity must be a IsoJob object (obtained: NoneType).'
            attr_name = 'iso_job'
            tool_cls = WriterExecutorIsoJob
        else:
            msg = 'The entity must be a LabIso object (obtained: NoneType)'
            attr_name = 'iso'
            tool_cls = WriterExecutorLabIso
        ori_entity = self.entity
        self.entity = None
        self._expect_error(TypeError, self._create_tool,
                'Unexpected entity class (NoneType). The entity must be a ' \
                'LabIso or a IsoJob!')
        kw = {attr_name : self.entity, 'mode' : self.mode}
        self.tool = tool_cls(**kw)
        res = self.tool.get_result()
        self.assert_is_none(res)
        self._check_error_messages(msg)
        self.entity = ori_entity
        if self.mode == _LabIsoWriterExecutorTool.MODE_EXECUTE:
            ori_user = self.executor_user
            self.executor_user = None
            self._test_and_expect_errors('The user must be a User object ' \
                                         '(obtained: NoneType).')
            self.executor_user = ori_user
        if self.FOR_JOB:
            self.entity.isos = []
            self._test_and_expect_errors('There are no ISOs in this ISO job!')

    def _test_final_layout_conversion_error(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        iso = self.isos[self._USED_ISO_LABEL]
        iso.rack_layout = RackLayout()
        self._test_and_expect_errors('Error when trying to convert final ' \
                                     'layout for ISO "123_iso_01".')

    def _test_unexpected_iso_status(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        exp_status = self.__get_iso_status().replace('_', ' ')
        iso = self.isos[self._USED_ISO_LABEL]
        iso.status = ISO_STATUS.PREPARED
        self._test_and_expect_errors('Unexpected ISO status: 123_iso_01 ' \
                         '(expected: %s, found: prepared)!' % (exp_status))

    def _test_samples_in_empty_plate(self):
        # The expected ISO status must be queued. The sample is added to the
        # final plate.
        if self.FOR_JOB:
            case_name = LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT
        else:
            case_name = LAB_ISO_TEST_CASES.CASE_ORDER_ONLY
        self._load_iso_request(case_name)
        plate = self.rack_generator.label_map['123_iso_01_a']
        c = 0
        for well in plate.containers:
            well.make_sample(volume=0.000001)
            c += 1
            if c == 2: break
        self._test_and_expect_errors('Plate 123_iso_01_a should be empty ' \
                    'but there are samples in the following positions: A1, A2')

    def _test_preparation_plate_layout_conversion_error(self):
        # The expected ISO status must be queued.
        if self.FOR_JOB:
            self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_NO_CYBIO)
            iso_plate = self.entity.iso_job_preparation_plates[0]
        else:
            self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_JOB_LAST)
            iso_plate = self.entity.iso_preparation_plates[0]
        iso_plate.rack_layout = RackLayout()
        self._test_and_expect_errors('Error when trying to convert layout of ' \
                                     'plate "%s"' % (iso_plate.rack.label))

    def _test_verification_error(self):
        # The expected ISO status must be in progress.
        if self.FOR_JOB:
            self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_JOB_LAST)
            iso_plate = self.entity.iso_job_preparation_plates[0]
        else:
            self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_NO_CYBIO)
            iso_plate = self.entity.iso_preparation_plates[0]
        plate_info = '%s (%s)' % (iso_plate.rack.barcode, iso_plate.rack.label)
        iso_plate.rack_layout = RackLayout()
        self._test_and_expect_errors('Error when trying to verify plate %s' \
                                     % (plate_info))

    def _test_rack_shape_mismatch(self):
        # The expected ISO status must be in progress.
        if self.FOR_JOB:
            self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_JOB_LAST)
            iso_plate = self.entity.iso_job_preparation_plates[0]
        else:
            self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_NO_CYBIO)
            iso_plate = self.entity.iso_preparation_plates[0]
        layout = self._get_layout_from_preparation_plate(iso_plate)
        alt_shape = get_96_rack_shape()
        if layout.shape == alt_shape:
            alt_shape = get_384_rack_shape()
        layout.shape = alt_shape
        iso_plate.rack_layout = layout.create_rack_layout()
        plate_info = '%s (%s)' % (iso_plate.rack.barcode, iso_plate.rack.label)
        self._test_and_expect_errors('Rack %s does not match the expected ' \
                                     'layout' % (plate_info))

    def _test_stock_rack_verification_error(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        if self.FOR_JOB:
            stock_rack = self.entity.iso_job_stock_racks[0]
        else:
            stock_rack = self.entity.iso_sector_stock_racks[0]
        stock_rack.rack_layout = RackLayout()
        rack_info = '%s (%s)' % (stock_rack.rack.barcode, stock_rack.label)
        self._test_and_expect_errors('Error when trying to verify stock rack ' \
                                     '%s' % (rack_info))

    def _test_stock_rack_verification_failure(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        if self.FOR_JOB:
            stock_rack = self.entity.iso_job_stock_racks[0]
        else:
            stock_rack = self.entity.iso_sector_stock_racks[0]
        for tube in stock_rack.rack.containers:
            tube.sample.volume = 1 / VOLUME_CONVERSION_FACTOR
            break
        rack_info = '%s (%s)' % (stock_rack.rack.barcode, stock_rack.label)
        self._test_and_expect_errors('Stock rack %s does not match the ' \
                                     'expected layout.' % (rack_info))

    def _test_inconsistent_stock_rack_worklist_label(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        if self.FOR_JOB:
            stock_rack = self.entity.iso_job_stock_racks[0]
        else:
            stock_rack = self.entity.iso_sector_stock_racks[0]
        worklist = stock_rack.worklist_series.get_worklist_for_index(0)
        value_parts = LABELS.parse_worklist_label(worklist.label)
        source_rack_marker = 's#7'
        new_label = LABELS.create_worklist_label(123,
                        value_parts[LABELS.MARKER_WORKLIST_NUM],
                        value_parts[LABELS.MARKER_WORKLIST_TARGET],
                        source_rack_marker)
        worklist.label = new_label
        self._test_and_expect_errors('Inconsistent stock rack for worklist ' \
                    '"123_1_s#7_to_a" (stock rack: %s).' % (stock_rack.label))

    def _test_duplicate_preparation_markers_for_iso(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE)
        iso = self.isos[self._USED_ISO_LABEL]
        prep_plate = iso.iso_preparation_plates[0].rack
        new_label = '9' + prep_plate.label
        new_plate = prep_plate.specs.create_rack(
                            status=get_item_status_future(),
                            label=new_label, barcode='09876543')
        layout = self.prep_layouts[prep_plate.label]
        iso.add_preparation_plate(new_plate, layout.create_rack_layout())
        sample_data = dict()
        if not self.FOR_JOB:
            for well in prep_plate.containers:
                if well.sample is None: continue
                rack_pos = well.location.position
                sample_data[rack_pos] = well.sample
            for well in new_plate.containers:
                rack_pos = well.location.position
                if not sample_data.has_key(rack_pos): continue
                ori_sample = sample_data[rack_pos]
                sample = well.make_sample(ori_sample.volume)
                for sm in ori_sample.sample_molecules:
                    mol = self._create_molecule(supplier=self.supplier,
                                molecule_design=sm.molecule.molecule_design)
                    sample.make_sample_molecule(molecule=mol,
                                                concentration=sm.concentration)
        self._test_and_expect_errors('There is more than 1 plates for ' \
                'preparation marker "p": 123_iso_01_p, 9123_iso_01_p!')

    def _test_executed_stock_transfers(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        if self.FOR_JOB:
            stock_rack = self.entity.iso_job_stock_racks[0]
        else:
            stock_rack = self.entity.iso_sector_stock_racks[0]
        ws = stock_rack.worklist_series
        labels = []
        for worklist in ws:
            self._create_executed_worklist(planned_worklist=worklist,
                                           executed_liquid_transfers=[])
            labels.append(worklist.label)
        self._test_and_expect_errors('The following stock transfers have ' \
            'already been executed before: %s!' % (', '.join(sorted(labels))))


class LabIsoWriterTestCase(_LabIsoWriterExecutorToolTestCase):

    FOR_JOB = False

    def set_up(self):
        _LabIsoWriterExecutorToolTestCase.set_up(self)
        self.mode = WriterExecutorLabIso.MODE_PRINT_WORKLISTS

    def test_case_order_only(self):
        self.num_files = 2
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)

    def test_case_no_job_direct(self):
        self.num_files = 3
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_NO_JOB_DIRECT)

    def test_case_no_job_one_prep(self):
        self.num_files = 5
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_NO_JOB_1_PREP)

    def test_case_no_job_complex(self):
        self.num_files = 9
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_NO_JOB_COMPLEX)

    def test_case_association_direct(self):
        self.num_files = 3
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)

    def test_case_association_96(self):
        self.num_files = 4
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_96)

    def test_case_association_simple(self):
        self.num_files = 4
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE)

    def test_case_association_no_cybio(self):
        self.num_files = 4
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_ASSOCIATION_NO_CYBIO)

    def test_case_association_2_aliquots(self):
        self.num_files = 4
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_ASSOCIATION_2_ALIQUOTS)

    def test_case_association_job_last(self):
        self.num_files = 7
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_ASSOCIATION_JOB_LAST)

    def test_case_association_several_conc(self):
        self.num_files = 4
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SEVERAL_CONC)

    def test_case_library_simple(self):
        self._test_and_expect_no_processing(
                                LAB_ISO_TEST_CASES.CASE_LIBRARY_SIMPLE)

    def test_case_library_2_aliquots(self):
        self._test_and_expect_no_processing(
                                LAB_ISO_TEST_CASES.CASE_LIBRARY_2_ALIQUOTS)

    def test_position_inactivation(self):
        self.num_files = 4
        self._test_position_inactivation()

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_final_layout_conversion_error(self):
        self._test_final_layout_conversion_error()

    def test_unexpected_iso_status(self):
        self._test_unexpected_iso_status()

    def test_samples_in_empty_plate(self):
        self._test_samples_in_empty_plate()

    def test_preparation_plate_layout_conversion_error(self):
        self._test_preparation_plate_layout_conversion_error()

    def test_verification_error(self):
        self._test_verification_error()

    def test_rack_shape_mismatch(self):
        self._test_rack_shape_mismatch()

    def test_stock_rack_verification_error(self):
        self._test_stock_rack_verification_error()

    def test_stock_rack_shape_mismatch(self):
        self._test_stock_rack_verification_failure()

    def test_inconsistent_stock_rack_worklist_label(self):
        self._test_inconsistent_stock_rack_worklist_label()

    def test_duplicate_preparation_markers_for_iso(self):
        self._test_duplicate_preparation_markers_for_iso()

    def test_executed_stock_transfers(self):
        self._test_executed_stock_transfers()


class IsoJobWriterTestCase(_LabIsoWriterExecutorToolTestCase):

    FOR_JOB = True

    def set_up(self):
        _LabIsoWriterExecutorToolTestCase.set_up(self)
        self.mode = WriterExecutorIsoJob.MODE_PRINT_WORKLISTS

    def test_case_order_only(self):
        self._test_and_expect_no_processing(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)

    def test_case_no_job_direct(self):
        self._test_and_expect_no_processing(
                                LAB_ISO_TEST_CASES.CASE_NO_JOB_DIRECT)

    def test_case_no_job_one_prep(self):
        self._test_and_expect_no_processing(
                                LAB_ISO_TEST_CASES.CASE_NO_JOB_1_PREP)

    def test_case_no_job_complex(self):
        self._test_and_expect_no_processing(
                                LAB_ISO_TEST_CASES.CASE_NO_JOB_COMPLEX)

    def test_case_association_direct(self):
        self.num_files = 3
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)

    def test_case_association_96(self):
        self._test_and_expect_no_processing(
                                    LAB_ISO_TEST_CASES.CASE_ASSOCIATION_96)

    def test_case_association_simple(self):
        self.num_files = 3
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE)

    def test_case_association_no_cybio(self):
        self.num_files = 4
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_ASSOCIATION_NO_CYBIO)

    def test_case_association_2_aliquots(self):
        self.num_files = 3
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_ASSOCIATION_2_ALIQUOTS)

    def test_case_association_job_last(self):
        self.num_files = 5
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_ASSOCIATION_JOB_LAST)

    def test_case_association_several_conc(self):
        self.num_files = 5
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SEVERAL_CONC)

    def test_case_library_simple(self):
        self.num_files = 4
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_LIBRARY_SIMPLE)

    def test_case_library_2_aliquots(self):
        self.num_files = 4
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_LIBRARY_2_ALIQUOTS)

    def test_position_inactivation(self):
        self.num_files = 3
        self._test_position_inactivation()

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_final_layout_conversion_error(self):
        self._test_final_layout_conversion_error()

    def test_unexpected_iso_status(self):
        self._test_unexpected_iso_status()

    def test_samples_in_empty_plate(self):
        self._test_samples_in_empty_plate()

    def test_preparation_plate_layout_conversion_error(self):
        self._test_preparation_plate_layout_conversion_error()

    def test_verification_error(self):
        self._test_verification_error()

    def test_rack_shape_mismatch(self):
        self._test_rack_shape_mismatch()

    def test_stock_rack_verification_error(self):
        self._test_stock_rack_verification_error()

    def test_stock_rack_shape_mismatch(self):
        self._test_stock_rack_verification_failure()

    def test_inconsistent_stock_rack_worklist_label(self):
        self._test_inconsistent_stock_rack_worklist_label()

    def test_executed_stock_transfers(self):
        self._test_executed_stock_transfers()


class LabIsoExecutorTestCase(_LabIsoWriterExecutorToolTestCase):

    FOR_JOB = False

    def set_up(self):
        _LabIsoWriterExecutorToolTestCase.set_up(self)
        self.mode = WriterExecutorLabIso.MODE_EXECUTE

    def test_case_order_only(self):
        self.new_iso_status = ISO_STATUS.DONE
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)

    def test_case_no_job_one_prep(self):
        self.new_iso_status = ISO_STATUS.DONE
        self.num_executed_processing_worklists = 3
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_NO_JOB_1_PREP)

    def test_case_no_job_direct(self):
        self.new_iso_status = ISO_STATUS.DONE
        self.num_executed_processing_worklists = 1
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_NO_JOB_DIRECT)

    def test_case_no_job_complex(self):
        self.new_iso_status = ISO_STATUS.DONE
        self.num_executed_processing_worklists = 7
        self.inaccurate_concentrations = {
            # instead of 1953125
            '123_iso_01_p:d1' : 1958333.33,
            # instead of 15625
            '123_iso_01_p:d2' : 15666.67,
            # instead of 125
            '123_iso_01_p:d3' : 125.33}
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_NO_JOB_COMPLEX)

    def test_case_association_direct(self):
        self.new_iso_status = ISO_STATUS.DONE
        self._test_and_expect_success(
                                    LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)

    def test_case_association_96(self):
        self.new_iso_status = ISO_STATUS.DONE
        self.num_executed_processing_worklists = 4
        self._test_and_expect_success(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_96)

    def test_case_association_simple(self):
        self.new_iso_status = ISO_STATUS.DONE
        self.num_executed_processing_worklists = 1
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE)

    def test_case_association_no_cybio(self):
        self.new_iso_status = ISO_STATUS.DONE
        self.num_executed_processing_worklists = 2
        self.inaccurate_concentrations = {
            # instead of 750
            '123_iso_01_p:d1' : 749.63, '123_iso_01_p:d2' : 749.63}
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_NO_CYBIO)

    def test_case_association_2_aliquots(self):
        self.new_iso_status = ISO_STATUS.DONE
        self.num_executed_processing_worklists = 1
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_2_ALIQUOTS)

    def test_case_association_job_last(self):
        self.new_iso_status = ISO_STATUS.IN_PROGRESS
        self.num_executed_processing_worklists = 3
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_JOB_LAST)

    def test_case_association_several_conc(self):
        self.new_iso_status = ISO_STATUS.IN_PROGRESS
        self.num_executed_processing_worklists = 4
        self.inaccurate_concentrations = {
                # instead of 1500 nM
                '123_iso_01_p:b2' : 1501.5, '123_iso_01_p:b3' : 1501.5,
                '123_iso_01_p:b4' : 1501.5, '123_iso_01_p:d2' : 1501.5,
                '123_iso_01_p:d3' : 1501.5, '123_iso_01_p:d4' : 1501.5}
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SEVERAL_CONC)

    def test_case_library_simple(self):
        self._test_and_expect_no_processing(
                            LAB_ISO_TEST_CASES.CASE_LIBRARY_SIMPLE)

    def test_case_library_2_aliquots(self):
        self._test_and_expect_no_processing(
                                LAB_ISO_TEST_CASES.CASE_LIBRARY_2_ALIQUOTS)

    def test_position_inactivation(self):
        self.new_iso_status = ISO_STATUS.DONE
        self.num_executed_processing_worklists = 1
        self._test_position_inactivation()

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_final_layout_conversion_error(self):
        self._test_final_layout_conversion_error()

    def test_unexpected_iso_status(self):
        self._test_unexpected_iso_status()

    def test_samples_in_empty_plate(self):
        self._test_samples_in_empty_plate()

    def test_preparation_plate_layout_conversion_error(self):
        self._test_preparation_plate_layout_conversion_error()

    def test_verification_error(self):
        self._test_verification_error()

    def test_rack_shape_mismatch(self):
        self._test_rack_shape_mismatch()

    def test_stock_rack_verification_error(self):
        self._test_stock_rack_verification_error()

    def test_stock_rack_shape_mismatch(self):
        self._test_stock_rack_verification_failure()

    def test_inconsistent_stock_rack_worklist_label(self):
        self._test_inconsistent_stock_rack_worklist_label()

    def test_duplicate_preparation_markers_for_iso(self):
        self._test_duplicate_preparation_markers_for_iso()

    def test_executed_stock_transfers(self):
        self._test_executed_stock_transfers()


class IsoJobExecutorTestCase(_LabIsoWriterExecutorToolTestCase):

    FOR_JOB = True

    def set_up(self):
        _LabIsoWriterExecutorToolTestCase.set_up(self)
        self.mode = WriterExecutorIsoJob.MODE_EXECUTE

    def test_case_order_only(self):
        self._test_and_expect_no_processing(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)

    def test_case_no_job_direct(self):
        self._test_and_expect_no_processing(
                            LAB_ISO_TEST_CASES.CASE_NO_JOB_DIRECT)

    def test_case_no_job_one_prep(self):
        self._test_and_expect_no_processing(
                            LAB_ISO_TEST_CASES.CASE_NO_JOB_1_PREP)

    def test_case_no_job_complex(self):
        self._test_and_expect_no_processing(
                            LAB_ISO_TEST_CASES.CASE_NO_JOB_COMPLEX)

    def test_case_association_direct(self):
        self.new_iso_status = ISO_STATUS.IN_PROGRESS
        self.num_executed_processing_worklists = 1
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)

    def test_case_association_96(self):
        self._test_and_expect_no_processing(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_96)

    def test_case_association_simple(self):
        self.new_iso_status = ISO_STATUS.IN_PROGRESS
        self.num_executed_processing_worklists = 2
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE)

    def test_case_association_no_cybio(self):
        self.new_iso_status = ISO_STATUS.IN_PROGRESS
        self.num_executed_processing_worklists = 4
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_NO_CYBIO)

    def test_case_association_2_aliquots(self):
        self.new_iso_status = ISO_STATUS.IN_PROGRESS
        self.num_executed_processing_worklists = 2
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_2_ALIQUOTS)

    def test_case_association_job_last(self):
        self.new_iso_status = ISO_STATUS.DONE
        self.num_executed_processing_worklists = 3
        self.inaccurate_concentrations = {
            # instead of 50 nM
            'ass_job_last_2:b3' : 49.88, 'ass_job_last_1:b3' : 49.88,
            # instead of 100 nM
            'ass_job_last_2:e3' : 99.77, 'ass_job_last_1:e3' : 99.77,
            # instead of 750 nM
            '123_job_01_jp:e1' : 749.63, '123_job_01_jp:e2' : 748.3,
            '123_job_01_jp:e3' : 749.63}
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_JOB_LAST)

    def test_case_association_several_conc(self):
        self.new_iso_status = ISO_STATUS.DONE
        self.num_executed_processing_worklists = 4
        self.inaccurate_concentrations = {
            # instead of 50 nM
            'ass_sev_conc_1:b5' : 49.88, 'ass_sev_conc_2:b5' : 49.88,
            # instead of 100 nM
            'ass_sev_conc_1:f5' : 99.77, 'ass_sev_conc_2:f5' : 99.77,
            # instead of 750
            '123_job_01_jp:f1' : 749.63, '123_job_01_jp:f2' : 748.3,
            '123_job_01_jp:f3' : 749.63}
        self._test_and_expect_success(
                            LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SEVERAL_CONC)

    def test_case_library_simple(self):
        self.new_iso_status = ISO_STATUS.DONE
        self.num_executed_processing_worklists = 3
        self.inaccurate_concentrations = {
            # instead of 1270
            'testlib_l1_r2:b2' : 1269.04, 'testlib_l1_r2:i10' : 1269.04,
            'testlib_l2_r2:b2' : 1269.04, 'testlib_l2_r2:i10' : 1269.04,
            'testlib_l1_r2:d2' : 1270.72, 'testlib_l1_r2:k10' : 1270.72,
            'testlib_l2_r2:d2' : 1270.72, 'testlib_l2_r2:k10' : 1270.72,
            # instead of 423.3
            'testlib_l1_r2:f2' : 423.57, 'testlib_l1_r2:m10' : 423.57,
            'testlib_l2_r2:f2' : 423.57, 'testlib_l2_r2:m10' : 423.57,
            # instead of 2540
            '123_job_01_jp:b1' : 2538.07, '123_job_01_jp:d1' : 2541.44,
            # instead of 846.667
            '123_job_01_jp:f1' : 847.14}
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_LIBRARY_SIMPLE)

    def test_case_library_2_aliquots(self):
        self.new_iso_status = ISO_STATUS.DONE
        self.num_executed_processing_worklists = 3
        self.inaccurate_concentrations = {
            # instead of 1270
            'testlib_l1_r2:b2' : 1268.12, 'testlib_l1_r2:i10' : 1268.12,
            'testlib_l1_r3:b2' : 1268.12, 'testlib_l1_r3:i10' : 1268.12,
            'testlib_l2_r2:b2' : 1268.12, 'testlib_l2_r2:i10' : 1268.12,
            'testlib_l2_r3:b2' : 1268.12, 'testlib_l2_r3:i10' : 1268.12,
            'testlib_l1_r2:d2' : 1268.94, 'testlib_l1_r2:k10' : 1268.94,
            'testlib_l1_r3:d2' : 1268.94, 'testlib_l1_r3:k10' : 1268.94,
            'testlib_l2_r2:d2' : 1268.94, 'testlib_l2_r2:k10' : 1268.94,
            'testlib_l2_r3:d2' : 1268.94, 'testlib_l2_r3:k10' : 1268.94,
            # instead of 423.3
            'testlib_l1_r2:f2' : 422.98, 'testlib_l1_r2:m10' : 422.98,
            'testlib_l1_r3:f2' : 422.98, 'testlib_l1_r3:m10' : 422.98,
            'testlib_l2_r2:f2' : 422.98, 'testlib_l2_r2:m10' : 422.98,
            'testlib_l2_r3:f2' : 422.98, 'testlib_l2_r3:m10' : 422.98,
            # instead of 2540
            '123_job_01_jp:b1' : 2536.23, '123_job_01_jp:d1' : 2537.88,
            # instead of 846.667
            '123_job_01_jp:f1' : 845.96}
        self._test_and_expect_success(
                                LAB_ISO_TEST_CASES.CASE_LIBRARY_2_ALIQUOTS)

    def test_position_inactivation(self):
        self.new_iso_status = ISO_STATUS.IN_PROGRESS
        self.num_executed_processing_worklists = 2
        self._test_position_inactivation()

    def test_invalid_input_values(self):
        self._test_invalid_input_values()

    def test_final_layout_conversion_error(self):
        self._test_final_layout_conversion_error()

    def test_unexpected_iso_status(self):
        self._test_unexpected_iso_status()

    def test_samples_in_empty_plate(self):
        self._test_samples_in_empty_plate()

    def test_preparation_plate_layout_conversion_error(self):
        self._test_preparation_plate_layout_conversion_error()

    def test_verification_error(self):
        self._test_verification_error()

    def test_rack_shape_mismatch(self):
        self._test_rack_shape_mismatch()

    def test_stock_rack_verification_error(self):
        self._test_stock_rack_verification_error()

    def test_stock_rack_shape_mismatch(self):
        self._test_stock_rack_verification_failure()

    def test_inconsistent_stock_rack_worklist_label(self):
        self._test_inconsistent_stock_rack_worklist_label()

    def test_executed_stock_transfers(self):
        self._test_executed_stock_transfers()
