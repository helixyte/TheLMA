"""
"""
from thelma.tools.iso.libcreation.report import \
    LibraryCreationTicketGenerator
from thelma.tools.iso.poolcreation.generation import \
    StockSampleCreationIsoGenerator

__docformat__ = 'reStructuredText en'
__all__ = ['LibraryCreationIsoGenerator',
           ]


class LibraryCreationIsoGenerator(StockSampleCreationIsoGenerator):
    """
    Generates ticket(s) and ISOs for a library creation ISO request.

    Same functionality as the base class except for different tool name
    and ticket headers.
    """
    NAME = 'Library Creation ISO Generator'
    TICKET_GENERATOR_CLASS = LibraryCreationTicketGenerator
