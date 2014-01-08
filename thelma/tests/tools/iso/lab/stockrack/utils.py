"""
Base classes for stock rack assignments in lab ISO processing.

AAB
"""
from everest.entities.utils import get_root_aggregate
from thelma.automation.semiconstants import get_96_rack_shape
from thelma.interfaces import ITubeRack
from thelma.models.racklayout import RackLayout
from thelma.tests.tools.iso.lab.utils import LAB_ISO_TEST_CASES
from thelma.tests.tools.iso.lab.utils import LabIsoTestCase2


class LabIsoStockRackTestCase(LabIsoTestCase2):

    def set_up(self):
        LabIsoTestCase2.set_up(self)
        self.rack_barcodes = []
        self.WL_PATH = 'thelma:tests/tools/iso/lab/stockrack/'
        self.filter_destination_racks = True

    def tear_down(self):
        LabIsoTestCase2.tear_down(self)
        del self.rack_barcodes
        del self.filter_destination_racks

    def _continue_setup(self, file_name=None):
        LabIsoTestCase2._continue_setup(self, file_name=file_name)
        self._create_destination_racks()

    def _create_destination_racks(self):
        sr_map = LAB_ISO_TEST_CASES.get_stock_rack_labels(self.case)
        tube_rack_agg = get_root_aggregate(ITubeRack)
        for rack_labels in sr_map.values():
            for rack_label in rack_labels:
                if self.filter_destination_racks and \
                                not self.entity.label in rack_label:
                    continue
                rack = self.rack_generator.get_tube_rack(rack_label)
                self.rack_barcodes.append(rack.barcode)
                tube_rack_agg.add(rack)

    def _test_invalid_input_value_entity(self):
        ori_entity = self.entity
        self.entity = self.entity.label
        if self.FOR_JOB:
            exp_msg = 'The entity must be a IsoJob object (obtained: str).'
        else:
            exp_msg = 'The entity must be a LabIso object (obtained: str).'
        self._test_and_expect_errors(exp_msg)
        self.entity = ori_entity

    def _test_invalid_input_value_rack_barcodes(self):
        ori_barodes = self.rack_barcodes
        self.rack_barcodes = dict()
        self._test_and_expect_errors('The barcode list must be a list ' \
                                     'object (obtained: dict).')
        self.rack_barcodes = [1]
        self._test_and_expect_errors('The barcode must be a basestring ' \
                                     'object (obtained: int).')
        self.rack_barcodes = []
        self._test_and_expect_errors('The barcode list is empty!')
        self.rack_barcodes = ori_barodes

    def _test_unknown_rack_barcodes(self):
        self.rack_barcodes = ['00000000', '00000001']
        self._test_and_expect_errors('Rack 00000000 has not been found in ' \
                                     'the DB!')
        self._check_error_messages('Rack 00000001 has not been found in ' \
                                   'the DB!')

    def _test_not_enough_rack_barcodes_iso(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_JOB_LAST)
        self.rack_barcodes = self.rack_barcodes[:1]
        self._test_and_expect_errors('The number of stock rack barcodes is ' \
                                     'too low! Expected: 4, found: 1.')

    def _test_final_layout_conversion_error(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        self.isos[self._USED_ISO_LABEL].rack_layout = \
                                            RackLayout(get_96_rack_shape())
        if self.FOR_JOB:
            exp_msg = 'Error when trying to convert layout for final plate ' \
                      'layout for ISO "123_iso_01"'
        else:
            exp_msg = 'Error when trying to convert layout for final ISO ' \
                      'plate layout.'
        self._test_and_expect_errors(exp_msg)

    def _test_iso_preparation_layout_conversion_error(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE)
        iso = self.isos[self._USED_ISO_LABEL]
        iso.iso_preparation_plates[0].rack_layout = \
                                            RackLayout(get_96_rack_shape())
        if self.FOR_JOB:
            exp_msg = 'Error when trying to convert ISO preparation plate ' \
                      'layout for plate "123_iso_01_p".'
        else:
            exp_msg = 'Error when trying to convert layout for ISO ' \
                      'preparation plate "123_iso_01_p".'
        self._test_and_expect_errors(exp_msg)

    def _test_job_preparation_layout_conversion_error(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_JOB_LAST)
        prep_plate = self.iso_job.iso_job_preparation_plates[0]
        prep_plate.rack_layout = RackLayout(get_96_rack_shape())
        self._test_and_expect_errors('Error when trying to convert layout ' \
                      'for job preparation plate "123_job_01_jp"')

    def _test_job_different_final_layouts(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_DIRECT)
        iso = self.isos[self._USED_ISO_LABEL]
        layout = self._get_layout_from_iso(iso)
        del_pos = None
        for fp in layout.get_sorted_working_positions():
            if fp.is_fixed:
                del_pos = fp.rack_position
                break
        layout.del_position(del_pos)
        iso.rack_layout = layout.create_rack_layout()
        self._test_and_expect_errors('The final layout for the ISOs in ' \
                'this job differ! Reference ISO: 123_iso_01. Differing ISOs: ' \
                '123_iso_02.')

    def _test_job_different_iso_preparation_positions(self):
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ASSOCIATION_SIMPLE)
        iso = self.isos[self._USED_ISO_LABEL]
        prep_plate = iso.iso_preparation_plates[0]
        layout = self._get_layout_from_preparation_plate(prep_plate)
        del_pos = None
        for fp in layout.get_sorted_working_positions():
            if fp.is_fixed:
                del_pos = fp.rack_position
                break
        layout.del_position(del_pos)
        prep_plate.rack_layout = layout.create_rack_layout()
        self._test_and_expect_errors('The ISO preparation plates for rack ' \
                                     'type "p" are inconsistent!')

    def _test_job_no_starting_wells(self):
        self.filter_destination_racks = False
        self._load_iso_request(LAB_ISO_TEST_CASES.CASE_ORDER_ONLY)
        self.iso_job.number_stock_racks = 1
        self._test_and_expect_errors('You do not need an XL20 worklist for ' \
                'this ISO job because all pools are prepared directly via ' \
                'the ISO processing.')
