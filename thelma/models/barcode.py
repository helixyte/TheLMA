"""
BarcodePrintJob model classes.

TR
"""

from everest.entities.base import Entity

__docformat__ = 'reStructuredText en'
__author__ = 'Tobias Rothe'
__all__ = ['BarcodePrintJob']


class BarcodePrintJob(Entity):
    """
    Represents an external barcode.

    **Equality Condition**: equal :attr:`id`
    """

    #: A csv list of barcodes (unique).
    barcodes = None
    #: A csv list of labels.
    labels = None
    #: The printer for the barcode
    printer = None
    #: The type for the barcode
    type = None

    # pylint:disable=W0622
    def __init__(self, barcodes='', labels=None, printer=None, type=None, **kw):
        Entity.__init__(self, **kw)
        self.barcodes = barcodes
        self.labels = labels
        self.printer = printer
        self.type = type
    # pylint:enable=W0622

    def __str__(self):
        return str(self.barcodes)

    def __repr__(self):
        str_format = '<%s id: %s, barcodes: %s, printer: %s, type: %s, ' \
                 'manufacturer: %s>'
        params = (self.__class__.__name__, self.id, self.barcodes,
                  self.printer, self.type)
        return str_format % params
