"""
BarcodePrintJob resource.

TR
"""

from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import terminal_attribute
from thelma.barcodeprinter import BarcodePrinter
from thelma.barcodeprinter import EmptyBarcode
from thelma.barcodeprinter import SatoUniLocationBarcode
from thelma.barcodeprinter import UniTwoLabelRackBarcode
from thelma.resources.base import RELATION_BASE_URL


__docformat__ = 'reStructuredText en'

__author__ = 'Tobias Rothe'
__date__ = '$Date: 2012-12-18 14:50:32 +0100 (Tue, 18 Dec 2012) $'
__revision__ = '$Rev: 13011 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/resources/barcode.py $'

__all__ = ['BarcodePrintJobMember',
           'BarcodePrintJobCollection',
           ]


class BarcodePrintJobMember(Member):
    relation = "%s/barcode" % RELATION_BASE_URL
    title = attribute_alias('labels')
    barcodes = terminal_attribute(str, 'barcodes')
    labels = terminal_attribute(str, 'labels')
    printer = terminal_attribute(str, 'printer')
    type = terminal_attribute(str, 'type')

class BarcodePrintJobCollection(Collection):
    title = 'BarcodePrintJobs'
    root_name = 'barcodes'
    description = 'Manage barcode print jobs'

    def add(self, member):
        Collection.add(self, member)
        # print the barcode
        barcode_type = member.type
        printer_name = member.printer
        if not member.barcodes is None:
            barcodes = member.barcodes.split(",")
        else:
            barcodes = []
        if not member.labels is None:
            labels = member.labels.split(",")
        else:
            labels = [''] * len(barcodes)
        i = 0
        for barcode in barcodes:
            if barcode_type == "UNIRACK":
                barcode = UniTwoLabelRackBarcode(barcode, labels[i],
                                                 label_row_2=barcode)
            elif barcode_type == "LOCATION":
                barcode = SatoUniLocationBarcode(barcode, labels[i])
            elif barcode_type == "EMPTY":
                # print an empty barcode
                barcode = EmptyBarcode(1)
            else:
                raise ValueError('"%s" is not a valid barcode type'
                                 % barcode_type)
            bcp = BarcodePrinter(printer_name)
            bcp.print_barcode(barcode)
            i += 1
