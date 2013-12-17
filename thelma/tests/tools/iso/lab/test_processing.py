"""
Tests for tools that deal with the processing of lab ISOs. This comprises both
the transfers from stock and the actual series processing.

AAB
"""
from thelma.automation.semiconstants import RACK_SPECS_NAMES
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.iso.lab.base import FinalLabIsoLayout
from thelma.automation.tools.iso.lab.base import FinalLabIsoPosition
from thelma.automation.tools.iso.lab.base import LabIsoPrepLayout
from thelma.automation.tools.iso.lab.base import LabIsoPrepPosition
from thelma.automation.tools.iso.lab.processing import LabIsoPlateVerifier
from thelma.automation.utils.layouts import FIXED_POSITION_TYPE
from thelma.automation.utils.layouts import FLOATING_POSITION_TYPE
from thelma.models.iso import IsoAliquotPlate
from thelma.models.iso import IsoPreparationPlate
from thelma.models.rack import RACK_TYPES
from thelma.tests.tools.iso.lab.utils import LAB_ISO_TEST_CASES
from thelma.tests.tools.iso.lab.utils import LabIsoTestCase2
from thelma.tests.tools.tooltestingutils import TestingLog
from thelma.tests.tools.utils.utils import VerifierTestCase
from thelma.tests.tools.iso.lab.utils import TestLibraryGenerator
from thelma.automation.utils.layouts import TransferTarget
from thelma.models.racklayout import RackLayout
from thelma.automation.semiconstants import get_384_rack_shape
from thelma.tests.tools.tooltestingutils import FileCreatorTestCase
from thelma.models.iso import ISO_STATUS
from thelma.tests.tools.iso.lab.utils import TestTubeGenerator
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.iso.lab.base import LAB_ISO_ORDERS
from thelma.automation.tools.iso.lab.base import LABELS
from thelma.models.utils import get_user
from thelma.tests.tools.tooltestingutils import SilentLog
from thelma.automation.tools.iso.lab.processing import WriterExecutorLabIso
from thelma.automation.tools.iso.lab.processing import WriterExecutorIsoJob
from thelma.automation.tools.worklists.series import SerialWriterExecutorTool
from thelma.automation.tools.iso.lab import get_worklist_writer
from thelma.automation.tools.iso.lab import get_worklist_executor

class LabIsoPlateVerifierTestCase(VerifierTestCase):

    def set_up(self):
        VerifierTestCase.set_up(self)
        self.plate_type = RACK_TYPES.PLATE
        self.log = TestingLog()
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
        self.tool = LabIsoPlateVerifier(log=self.log,
                                        lab_iso_plate=self.lab_iso_plate,
                                        for_job=self.for_job,
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
        fp = FinalLabIsoPosition(rack_position=rack_pos,
                                 molecule_design_pool=self._get_pool(205215),
                                 position_type=FIXED_POSITION_TYPE,
                                 concentration=1000, volume=10, from_job=True)
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
            self.tool = get_worklist_writer(entity=self.entity,
                                            add_default_handlers=True)
        else:
            self.tool = get_worklist_executor(entity=self.entity,
                                              user=self.executor_user,
                                              add_default_handlers=True)

    def __fill_stock_racks(self):
        self.tube_generator = TestTubeGenerator(self.rack_generator.\
                                                tube_rack_specs.tube_specs[0])
        for rack_label in self.stock_racks.keys():
            layout = self.stock_rack_layouts[rack_label]
            rack = self.rack_generator.label_map[rack_label]
            for rack_pos, sr_pos in layout.iterpositions():
                self.tube_generator.create_tube(rack=rack,
                       rack_pos=rack_pos, pool=sr_pos.molecule_design_pool,
                       tube_barcode=sr_pos.tube_barcode,
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
                plate = ipp.plate
                self.prep_plates[plate.label] = plate
        if self.FOR_JOB:
            for ijpp in self.iso_job.iso_job_preparation_plates:
                plate = ijpp.plate
                self.job_plates[plate.label] = plate

    def __fill_plates(self):
        plate_data = LAB_ISO_TEST_CASES.get_plate_intermediate_data(self.case)
        for plate_label, starting_data in plate_data.iteritems():
            plate = self.rack_generator.label_map[plate_label]
            for well in plate.containers:
                pos_label = well.location.position.label.lower()
                if not starting_data.has_key(pos_label): continue
                pos_data = starting_data[pos_label]
                pool = self._get_pool(pos_data[0])
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

    def __check_result_writer(self):
        zip_stream = self.tool.get_result()
        self.assert_is_not_none(zip_stream)
        self.__check_zip_stream(zip_stream)
        self.__check_writer_entities()

    def __check_zip_stream(self, zip_stream):
        archive = self._get_zip_archive(zip_stream)
        namelist = archive.namelist()
        # TODO:

    def __check_writer_entities(self):
        iso = self.isos.values()[self._USED_ISO_LABEL]
        exp_status = self.__get_iso_status()
        self.assert_equal(iso.status, exp_status)
        # TODO:


    def __check_result_executor(self):
        pass # TODO:


class LabIsoWriterTestCase(_LabIsoWriterExecutorToolTestCase):

    FOR_JOB = False

    def set_up(self):
        _LabIsoWriterExecutorToolTestCase.set_up(self)
        self.mode = WriterExecutorLabIso.MODE_PRINT_WORKLISTS

    def xtest_case_association_direct(self):
        self._test_and_expect_success(
                                    LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
