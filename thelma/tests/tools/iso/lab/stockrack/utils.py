"""
Base classes for stock rack assignments in lab ISO processing.

AAB
"""
from thelma.tests.tools.iso.lab.utils import LAB_ISO_TEST_CASES
from thelma.tests.tools.iso.lab.utils import LabIsoTestCase2


class LabIsoStockRackTestCase(LabIsoTestCase2):

    def set_up(self):
        LabIsoTestCase2.set_up(self)
        self.rack_barcodes = []
        self.WL_PATH = 'thelma:tests/tools/iso/lab/stockrack/'

    def tear_down(self):
        LabIsoTestCase2.tear_down(self)
        del self.rack_barcodes

    def _continue_setup(self, file_name=None):
        LabIsoTestCase2._continue_setup(self, file_name=file_name)
        self._create_destination_racks()

    def _create_destination_racks(self):
        sr_map = LAB_ISO_TEST_CASES.get_stock_rack_labels(self.case)
        for rack_labels in sr_map.values():
            for rack_label in rack_labels:
                rack = self.rack_generator.get_tube_rack(rack_label)
                self.rack_barcodes.append(rack.barcode)

