"""
This handler converts the result of the library base layout parser into
a :class:`LibraryBaseLayout`.

AAB
"""
from thelma.automation.handlers.base import LayoutParserHandler
from thelma.automation.parsers.libbaselayout import LibraryBaseLayoutParser
from thelma.automation.semiconstants import get_rack_position_from_indices
from thelma.automation.tools.iso.libcreation.base import LibraryBaseLayout
from thelma.automation.tools.iso.libcreation.base import \
    LibraryBaseLayoutPosition

__docformat__ = 'reStructuredText en'
__all__ = ['LibraryBaseLayoutParserHandler',
           ]


class LibraryBaseLayoutParserHandler(LayoutParserHandler):
    """
    Converts the results of the :class:`LibraryBaseLayoutParser` into a
    :class:`LibraryBaseLayout`.

    **Return Value:** :class:`LibraryBaseLayout`
    """

    NAME = 'Library Base Layout Parser Handler'

    _PARSER_CLS = LibraryBaseLayoutParser

    def __init__(self, stream, parent=None):
        LayoutParserHandler.__init__(self, stream, parent=parent)
        #: The library base layout.
        self.__base_layout = None

    def reset(self):
        LayoutParserHandler.reset(self)
        self.__base_layout = None

    def _convert_results_to_entity(self):
        """
        Converts the parsing results into a :class:`LibraryBaseLayout`
        (no model class).
        """
        self.add_info('Convert parser results ...')
        if not self.has_errors():
            self.__init_layout()
        if not self.has_errors():
            for rack_pos_container in self.parser.contained_wells:
                rack_pos = get_rack_position_from_indices(
                                row_index=rack_pos_container.row_index,
                                column_index=rack_pos_container.column_index)
                base_pos = LibraryBaseLayoutPosition(rack_pos)
                self.__base_layout.add_position(base_pos)
        if not self.has_errors() and len(self.__base_layout) < 1:
            msg = 'The specified base layout is empty!'
            self.add_error(msg)
        if not self.has_errors():
            self.__base_layout.close()
            self.return_value = self.__base_layout
            self.add_info('Conversion completed.')

    def __init_layout(self):
        # Determines the parsed rack shape to initializes the layout.
        self._determine_rack_shape()
        if not self._rack_shape is None:
            self.__base_layout = LibraryBaseLayout(self._rack_shape)
