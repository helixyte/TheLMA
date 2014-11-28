"""
:Date: 2011-05
:Author: AAB, berger at cenix-bioscience dot com

"""
from StringIO import StringIO

from pyramid.compat import ascii_native_
from pyramid.compat import string_types
from xlrd import XLRDError
from xlrd import open_workbook

from thelma.tools.messagerecorder import MessageRecorder
from thelma.tools.base import BaseTool
from thelma.tools.utils.base import add_list_map_element
from thelma.tools.utils.base import get_trimmed_string
from thelma.tools.utils.base import is_valid_number
from thelma.entities.utils import label_from_number


__docformat__ = 'reStructuredText en'
__all__ = ['BaseParser',
           'ParsingContainer',
           'RackShapeParsingContainer',
           'RackPositionParsingContainer',
           'TxtFileParser',
           'ExcelFileParser',
           'ExcelParsingContainer',
           'ExcelSheetParsingContainer',
           'LayoutParsingContainer',
           'TagDefinitionParsingContainer',
           'TagParsingContainer',
           'RackParsingContainer',
           'ExcelMoleculeDesignPoolLayoutParser',
           'ExcelMoleculeDesignPoolLayoutParsingContainer']


class BaseParser(BaseTool): # still abstract pylint:disable=W0223
    """
    Abstract base class for all parsers in TheLMA.

    Parsers work on file streams. They parse and collect data (using
    :class:`ParsingContainer`s) and present them in an ordered manner.

    Parsers do not use or interact with TheLMA specific modules. All
    external transfers are taken over by specialized parser handlers (see
    :class:`thelma.parsers.handlers.base.BaseParserHandler`). They are
    initialized and run by the parser handlers.

    Parsing is performed using only default python classes and parsing
    containers. The final conversion of the data into entity objects and the
    checks related to them are also performed by the parser handler.
    """
    def __init__(self, stream, parent=None):
        """
        Constructor.

        :param stream: The open file to parse.
        :type stream: :class:`stream`
        """
        BaseTool.__init__(self, parent=parent)
        #: The stream to be parsed.
        self.stream = stream
        #: Is set to true if the parser attempts to run.
        self.has_run = False
        #: If *True* if the parsing process is aborted at the next
        #: :func:`has_errors` check. This variable is used if you want to abort
        #: parsing without raising an error.
        self.abort_execution = False

    def reset(self):
        """
        Resets the parser. Call this before running the parser.
        """
        MessageRecorder.reset(self)
        self.has_run = False

    def __str__(self):
        return '<Parser: %s, errors: %i>' % (self.NAME, self._error_count)


class ParsingContainer(object):
    """
    Abstract class for intermediate data storage classes. ParsingContainers
    store intermediate data, i.e. data that cannot directly be converted
    into entity objects upon parsing.
    """
    #: The parser class this container is designed for.
    _PARSER_CLS = BaseParser

    def __init__(self, parser):
        """
        Constructor.

        :param parser: The parser this container belongs to.
        :type parser: :class:`BaseParser`
        """
        self._parser = parser
        if not issubclass(self._parser.__class__, self._PARSER_CLS):
            msg = 'Unexpected parser class "%s". Expected: %s or subclass.' \
                   % (self._parser.__class__.__name__,
                      self._PARSER_CLS.__name__)
            self._parser.add_error(msg)


class RackShapeParsingContainer(ParsingContainer):
    """
    Parsing container for RackShapes.
    """
    def __init__(self, parser, row_number, column_number):
        """
        Constructor.

        :param int row_number: The number of rows for this rack shape.
        :param int column_number: The number of columns for this rack shape.
        """
        ParsingContainer.__init__(self, parser)
        self.row_number = row_number
        self.column_number = column_number

    @property
    def name(self):
        """
        The name of the rack shape represented by this container.
        """
        return '%ix%i' % (self.row_number, self.column_number)

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return isinstance(other, RackShapeParsingContainer) \
            and self.row_number == other.row_number \
            and self.column_number == other.column_number

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def position_containers(self):
        """
        List of all rack positions contained in this rack shape
        (:class:`RackPositionContainer`).
        """
        pos_containers = []
        row_index, column_index = 0, 0
        while row_index < self.row_number:
            while column_index < self.column_number:
                pos_container = RackPositionParsingContainer(
                        self._parser, row_index, column_index)
                pos_containers.append(pos_container)
                column_index += 1
            row_index += 1
            column_index = 0
        return pos_containers


class RackPositionParsingContainer(ParsingContainer):
    """
    Parsing container for RackPositions.
    """
    def __init__(self, parser, row_index, column_index):
        """
        Constructor.

        :param int row_index: The index of this well's row in the rack shape.
        :param int column_index: The index of this well's columns in the rack
            shape.
        """
        ParsingContainer.__init__(self, parser)
        self.row_index = row_index
        self.column_index = column_index

    def __str__(self):
        return self.label

    def __repr__(self):
        str_format = '<%s %s>'
        params = (self.__class__.__name__, self.label)
        return str_format % params

    def __eq__(self, other):
        return isinstance(other, RackPositionParsingContainer) \
            and self.row_index == other.row_index \
            and self.column_index == other.column_index

    @property
    def label(self):
        """
        The label for this rack position.
        """
        return '%s%d' % (label_from_number(self.row_index + 1),
                         self.column_index + 1)


class TxtFileParser(BaseParser): # still abstract pylint: disable=W0223
    """
    Abstract base class for all TXT-based parsers (incl. CSV files).
    """
    def __init__(self, stream, parent=None):
        BaseParser.__init__(self, stream, parent=parent)
        #: The content of the file split into lines.
        self._lines = None

    def reset(self):
        """
        Reset all parser values except for initialisation values.
        """
        BaseParser.reset(self)
        self._lines = None

    def _split_into_lines(self):
        """
        Splits the content of the file into lines.
        """
        self.add_debug('Split into lines ...')
        if isinstance(self.stream, (file, StringIO)):
            self.stream.seek(0)
            self._lines = [line.strip() for line in self.stream.readlines()]
        elif isinstance(self.stream, basestring):
            strm = StringIO(self.stream)
            self._lines = [line.strip() for line in strm.readlines()]
        else:
            msg = 'Unknown type for stream: %s. Provide a basestring, a file ' \
                  'or a %s object please.' % (self.stream.__class__.__name__,
                                              StringIO.__name__)
            self.add_error(msg)


class ExcelFileParser(BaseParser): # still abstract pylint: disable=W0223
    """
    Abstract base class for all Excel file parsers.
    """
    NAME = 'ExcelFileParser'

    def __init__(self, stream, parent=None):
        BaseParser.__init__(self, stream, parent=parent)
        #: The sheet that is parsed at the moment.
        self.sheet = None

    def open_workbook(self):
        """
        Opens the Excel file as workbook and performs some checks.

        Records a critical error if the workbook can not be opened.

        :returns: Workbook.
        """
        self.reset()
        self.add_info('Open workbook ...')
        self.has_run = True
        try:
            wb = open_workbook(file_contents=self.stream,
                                formatting_info=True,
                                on_demand=True)
        except XLRDError:
            wb = None
            msg = 'Could not open Excel File.'
            self.add_critical_error(ValueError(msg))
        else:
            self.add_info('Opening workbook completed.')
        return wb

    def get_sheet_by_name(self, workbook, sheet_name, raise_error=True):
        """
        Returns the sheet with the specified name from the given workbook.

        :param workbook: The workbook containing the sheet.
        :param str sheet_name: The name of the sheet.
        :param bool raise_error: If set, the parser raises an error if there
            is no sheet wit this name (default: *False*).
        :returns: Sheet with the specified name.
        """
        sheet = None
        names = [sheet_name, sheet_name.lower(), sheet_name.upper()]
        for name in names:
            try:
                sheet = workbook.sheet_by_name(name)
            except XLRDError:
                pass
            else:
                break
        if sheet is None and raise_error:
            msg = 'There is no sheet called "%s"' % (sheet_name)
            self.add_error(ValueError(msg))
        return sheet

    def get_sheet_name(self, sheet):
        """
        Returns the name of the given sheet.

        :returns: Name of the sheet.
        :rtype: :class:`string`
        """
        return sheet.name

    def get_sheet_shape(self, sheet):
        """
        Returns a 2-tuple containing the dimension (number of rows,
        number of columns) of the given sheet.

        :param sheet: The Excel sheet to query the shape of.
        :returns: Number of rows (:class:`int`), Number of columns (:class:`int`)
        :rtype: :class:`tuple`
        """
        return sheet.nrows, sheet.ncols

    def get_sheet_row_number(self, sheet):
        """
        Returns the number of rows for the given sheet.

        :returns: Number of rows.
        :rtype: :class:`int`
        """
        return sheet.nrows

    def get_sheet_column_number(self, sheet):
        """
        Returns the number of columns for the given sheet.

        :return: Number of columns.
        :rtype: :class:`int`
        """
        return sheet.ncols

    def get_cell_value(self, sheet, row_index, column_index):
        """
        Returns the value of the specified in the given sheet.
        Converts the passed cell value either into
        a ascii string (if basestring) or a number (if non_string).
        """
        cell_value = sheet.cell_value(row_index, column_index)
        cell_name = '%s%i' % (label_from_number(column_index + 1),
                              row_index + 1)
        sheet_name = self.get_sheet_name(sheet)
        conv_value = None
        if isinstance(cell_value, string_types):
            try:
                conv_value = ascii_native_(cell_value)
            except UnicodeEncodeError:
                msg = 'Unknown character in cell %s (sheet "%s"). Remove ' \
                      'or replace the character, please.' \
                      % (cell_name, sheet_name)
                self.add_error(msg)
            else:
                if conv_value == '':
                    conv_value = None
                else:
                    # Try to convert to an int or float.
                    try:
                        conv_value = int(conv_value)
                    except ValueError:
                        try:
                            conv_value = float(conv_value)
                        except ValueError:
                            pass
        elif isinstance(cell_value, (float, int)):
            if is_valid_number(value=cell_value, is_integer=True):
                conv_value = int(cell_value)
            else:
                conv_value = cell_value
        else:
            msg = 'There is some unknown content in cell %s (sheet %s).' \
                  % (cell_name, sheet_name)
            self.add_error(msg)
        return conv_value

    @staticmethod
    def get_cell_name(row_index, column_index):
        """
        Convenience method deriving an Excel cell label from a row and
        column index.

        :returns: Cell name.
        :rtype: :class:`str`
        """
        if row_index is None or column_index is None:
            result = None
        else:
            result = '%s%i' \
                     % (label_from_number(column_index + 1), row_index + 1)
        return result

    @classmethod
    def format_log_message(cls, sheet_name, cell_name, message):
        """
        Adds sheet and cell information to the given log message.
        """
        if cell_name is None:
            msg = 'On sheet "%s": %s' % (sheet_name, message)
        else:
            msg = 'On sheet "%s" cell %s: %s' \
                  % (sheet_name, cell_name, message)
        return msg


class ExcelParsingContainer(ParsingContainer):
    """
    Abstract class for intermediate data storage when parsing Excel files.
    """
    _PARSER_CLS = ExcelFileParser

    def _create_error(self, msg, cell_name=None):
        """
        Convenience method. Records an error message in the parser.

        :param str msg: The error message.
        :param str cell_name: The name of the cell the error occurred in.
        """
        sheet_name = self.__get_sheet_name()
        msg = self._PARSER_CLS.format_log_message(sheet_name, cell_name, msg)
        self._parser.add_error(msg)

    def _create_warning(self, msg):
        """
        Convenience method. Records a warning message in the parser.

        :param str msg: The warning message
        """
        sheet_name = self.__get_sheet_name()
        msg = self._PARSER_CLS.format_log_message(sheet_name, None, msg)
        self._parser.add_warning(msg)

    def _create_info(self, msg):
        """
        Convenience method. Records an info message in the parser.

        :param str msg: The info message.
        """
        sheet_name = self.__get_sheet_name()
        msg = self._PARSER_CLS.format_log_message(sheet_name, None, msg)
        self._parser.add_info(msg)

    def _create_debug_info(self, msg):
        """
        Convenience method. Records a debug message in the parser.

        :param str msg: The debugging message.
        """
        sheet_name = self.__get_sheet_name()
        msg = self._PARSER_CLS.format_log_message(sheet_name, None, msg)
        self._parser.add_debug(msg)

    def _convert_keyword(self, keyword):
        """
        Applies some format adjustment to keywords to enable comparisons.
        """
        keyword = str(keyword).strip()
        keyword = keyword.replace(' ', '_')
        keyword = keyword.replace('-', '_')
        keyword = keyword.lower()
        return keyword

    def __get_sheet_name(self):
        return self._parser.get_sheet_name(self._parser.sheet)


class ExcelSheetParsingContainer(ExcelParsingContainer):
    """
    Responsible for parsing a particular excel sheet.
    """
    def __init__(self, parser, sheet):
        """
        :param sheet: The excel sheet associated with this container.
        """
        ExcelParsingContainer.__init__(self, parser=parser)
        #: The associated Excel sheet.
        self._sheet = sheet
        self._current_row = 0
        self._row_number = self._parser.get_sheet_row_number(sheet)
        self._col_number = self._parser.get_sheet_column_number(sheet)
        #: Can be used to abort parsing of cancel progress in rows.
        self._end_reached = False

    def _check_for_end(self):
        """
        Sets the :attr:`_end_reached` flag. The effect on the parsing process
        depends on the derived class. Per default, this flag is set to *True*
        if the row tracker (:attr:`_current_row`) hits the last row of the
        sheet.
        """
        if self._current_row > (self._row_number - 1):
            self._end_reached = True

    def _step_to_next_row(self):
        """
        Increases the internal row count and checks for the end of document.
        """
        self._current_row += 1
        self._check_for_end()

    def _get_cell_value(self, row_index, column_index):
        """
        Convenience method returning the content of a cell. Converts the
        passed cell value either into a ascii string (if basestring) or a
        number (if possible).

        :param int row_index: The row index of the cell.
        :param int column_index: The column index of the cell.
        :returns: The cell value.
        """
        return self._parser.get_cell_value(self._sheet, row_index,
                                           column_index)

    def _get_cell_name(self, row_index, column_index):
        """
        Convenience method deriving an excel cell label from a row and
        column index.

        :returns: Cell name.
        :rtype: :class:`str`
        """
        return ExcelFileParser.get_cell_name(row_index, column_index)


class ExcelLayoutFileParser(ExcelFileParser): #pylint: disable=W0223
    """
    Abstract base class for :class:`ExcelFileParser`s that process Excel
    sheets containing layout and tags.
    """
    #: Flag indicating if all layouts have to have the same dimension
    #: (default: *True*).
    HAS_COMMON_LAYOUT_DIMENSION = True

    def __init__(self, stream, parent=None):
        ExcelFileParser.__init__(self, stream, parent=parent)
        #: Defines the allow rack shapes (needs to set by the handler).
        self.allowed_rack_dimensions = None
        #: Stores the racks found in the source file
        # key: rack_label, value: RackParsingContainer
        self.rack_map = {}
        #: Stores the layouts found in the source file
        # key: string [sheet_name][top_left_row][top_left_column],
        # value: LayoutParsingContainer
        self.layout_map = {}
        #: Flag indicating if layouts have a rack specifier (used to determine
        #: the starting cell name) - default: *True*.
        self.layouts_have_specifiers = True
        #: The rack dimensions for the layouts
        #: (:class:`RackShapeParsingContainer`) (only set if
        #: :attr:`HAS_COMMON_LAYOUT_DIMENSION`).
        self.shape = None


class ExcelLayoutSheetParsingContainer(ExcelSheetParsingContainer):
    """
    Specialized :class:`ExcelSheetParsingContainer` for Excel sheets
    containing layout and tags.
    """
    _PARSER_CLS = ExcelLayoutFileParser
    #: Marker telling the parser when to finish the parsing the current sheet
    #: (must be located in column A by default).
    _END_MARKER = 'end'
    #: Marks a new factor/tag definition.
    _FACTOR_MARKER = 'factor'
    #: Marks the start of the levels (must be located under a factor marker).
    _LEVEL_MARKER = 'level'
    #: Marks the code column (must be located to the right of a factor marker).
    _CODE_MARKER = 'code'
    #: The index of the column containing the code values.
    _CODE_COLUMN_INDEX = 1
    #
    __INVALID_FACTOR_DEF_MSG = 'Invalid factor definition! There must be a ' \
                               '"Code" marker next to and a "Level" marker ' \
                               'below the "Factor" marker!'

    def __init__(self, parser, sheet):
        ExcelSheetParsingContainer.__init__(self, parser=parser, sheet=sheet)
        #: Store all tag containers found.
        self._tags = set()
        #: The tag container sorted by starting row.
        self._tags_by_row = dict()
        #: Remember the largest tag defintion column index (to speed up
        #: layout search).
        self.__max_tag_column_index = 0

    def _check_for_end(self):
        """
        Extends the super class method to also check for the presence of
        the :attr:`_END_MARKER` (in the first column).
        """
        ExcelSheetParsingContainer._check_for_end(self)
        if not self._end_reached:
            first_col_value = self._get_cell_value(self._current_row, 0)
            if isinstance(first_col_value, str) and \
                                first_col_value.lower() == self._END_MARKER:
                self._end_reached = True

    def _parse_tag_definitions(self):
        """
        Checks the current row for a tag definition start (Factor marker).
        If it finds a marker, it parses the referring definition.
        """
        if not self.__is_tag_definition():
            current_tags = None
        else:
            starting_row = self._current_row
            current_tags = dict()
            for col_index in range(2, self._col_number):
                tag_label = self._get_tag_label(col_index)
                if tag_label is None:
                    break
                tag_definition = \
                        self._init_tag_definition_container(tag_label)
                if tag_definition is None:
                    break
                current_tags[col_index] = tag_definition
            self.__parse_tag_codes_and_values(current_tags)
            self._check_last_tags(current_tags)
            self._tags_by_row[starting_row] = current_tags.values()
            if len(current_tags) > 0:
                self.__max_tag_column_index = max(self.__max_tag_column_index,
                                              max(current_tags.keys()))
        return current_tags

    def __is_tag_definition(self):
        # Checks if the current row contains a tag definition. All three
        # markers (factor, code, level) must be in place.
        cell_value = self._get_cell_value(self._current_row, 0)
        if not isinstance(cell_value, str):
            result = False
        elif not cell_value.lower().startswith(self._FACTOR_MARKER):
            result = False
        else:
            code_cell_value = self._get_cell_value(self._current_row, 1)
            if not isinstance(code_cell_value, str) \
               or not code_cell_value.lower() == self._CODE_MARKER:
                cell_name = self._get_cell_name(self._current_row, 1)
                self._create_error(self.__INVALID_FACTOR_DEF_MSG, cell_name)
                result = False
            elif self._current_row + 1 >= self._row_number:
                cell_name = self._get_cell_name(self._current_row, 0)
                self._create_error(self.__INVALID_FACTOR_DEF_MSG, cell_name)
                result = False
            else:
                lc_value = self._get_cell_value(self._current_row + 1, 0)
                if not isinstance(lc_value, str) \
                   or not lc_value.lower().startswith(self._LEVEL_MARKER):
                    cell_name = self._get_cell_name(self._current_row + 1, 0)
                    self._create_error(self.__INVALID_FACTOR_DEF_MSG,
                                       cell_name)
                    result = False
                else:
                    # Success!
                    result = True
        return result

    def _get_tag_label(self, column_index):
        """
        Convenience method returning a tag label. All tag labels are strings.
        Returns *None* if the tag label is an empty string.

        Overwrite this method to address special formats (e.g. keyword
        conversion, case-sensitivity, whitespaces, etc.).

        :returns: Tag label.
        :rtype: :class:`str`
        """
        tag_label = self._get_cell_value(self._current_row, column_index)
        if tag_label is None:
            result = None
        else:
            result = ascii_native_(tag_label)
        return result

    def _init_tag_definition_container(self, predicate):
        """
        Initialises a new tag container and stores in the :attr:`_tags` set.
        Overwrite this method if you need to apply additional checks.
        """
        container = TagDefinitionParsingContainer(parser=self._parser,
                                        tag_predicate=predicate,
                                        start_row_index=self._current_row)
        if container in self._tags:
            result = None
            msg = 'Duplicate tag "%s"!' % (predicate)
            self._create_error(msg)
        else:
            result = container
            self._tags.add(container)
        return result

    def __parse_tag_codes_and_values(self, current_tags):
        """
        If a code is *None*, the parsing aborts. There must be a level
        (tag value) for each code.
        """
        self._step_to_next_row()
        invalid = False
        while not self._end_reached:
            if invalid:
                break
            code = self._get_cell_value(self._current_row,
                                        self._CODE_COLUMN_INDEX)
            if code is None:
                self.__check_level_consistency(current_tags)
                break
            all_values = []
            for col_index, tag_definition in current_tags.iteritems():
                cell_value = self._get_cell_value(self._current_row, col_index)
                tag_definition.add_code_and_value(cell_value, code)
                if not cell_value is None:
                    all_values.append(cell_value)
            if self._parser.has_errors():
                break
            if not self._has_valid_tag_values(all_values):
                break
            self._step_to_next_row()

    def __check_level_consistency(self, current_tags):
        """
        Makes sure there is no level if there is no code. Otherwise some
        layout might accidently be assigned to other tag definitions
        (if there are levels but no codes for a tag).
        """
        for col_index, tag_definition in current_tags.iteritems():
            if tag_definition.inactive:
                continue
            level_value = self._get_cell_value(self._current_row, col_index)
            if not level_value is None:
                msg = 'There are levels in definition for factor "%s" ' \
                      'that do not have a code!' % (tag_definition.predicate)
                cell_name = self._get_cell_name(self._current_row, col_index)
                self._create_error(msg, cell_name)

    def _has_valid_tag_values(self, values):
        """
        Allows to perform additional checks on the value set of a tag
        definition. By default, there must be at least one value.

        :returns: Result of the check.
        :rtype: :class:`bool`
        """
        if len(values) < 1:
            msg = 'There is a code without label!'
            cell_name = self._get_cell_name(self._current_row,
                                            self._CODE_COLUMN_INDEX)
            self._create_error(msg, cell_name)
            result = False
        else:
            result = True
        return result

    def _check_last_tags(self, current_tags):
        """
        Performs checks on the tags of the current definition.
        By default, empty tags are removed.
        """
        del_indices = []
        for col_index, tag_definition in current_tags.iteritems():
            if len(tag_definition.values) < 1:
                del_indices.append(col_index)
        for col_index in del_indices:
            tag_definition = current_tags[col_index]
            self._tags.remove(tag_definition)
            del current_tags[col_index]

    def find_layouts(self):
        """
        Looks for layout definitions, associates them with tags and racks
        and parses its codes.
        """
        self._current_row = 1
        self._end_reached = False
        layout_found = False
        while not self._end_reached:
            for col_index in range(self.__max_tag_column_index,
                                   self._col_number):
                if self._parser.has_errors():
                    break
                layout_container = self.__get_layout(col_index)
                if self._parser.has_errors():
                    break
                if layout_container is None:
                    continue
                layout_found = True
                # associate tags
                tag_definitions = None
                for row_index in sorted(self._tags_by_row.keys(),
                                        reverse=True):
                    if row_index > self._current_row:
                        continue
                    tag_definitions = self._tags_by_row[row_index]
                    break
                if tag_definitions is None:
                    msg = 'Unable to find tags (factors) for layout in row ' \
                          '%i! Please check the alignment of your layouts!' \
                          % (self._current_row + 1)
                    self._create_error(msg)
                    break
                if len(tag_definitions) > 0:
                    self._parse_layout_codes(layout_container, tag_definitions)
            self._step_to_next_row()
        if not layout_found and not self._parser.has_errors():
            msg = 'Could not find a layout definition on this sheet. ' \
                  'Please make sure you have indicated them correctly.'
            self._create_error(msg)

    def __get_layout(self, col_index):
        """
        Fetches the layout located at the current position (if there is any)
        and links it to the the rack containers associated to it.
        """
        cell_value = self._get_cell_value(self._current_row, col_index)
        is_layout = cell_value == 'A' \
                    and self._col_number >= col_index + 1 \
                    and self._get_cell_value(self._current_row - 1,
                                             col_index + 1) == 1
        result = None
        if is_layout:
            ori_row = self._current_row - 1
            ori_col = col_index
            top_left_pos = (ori_row, ori_col)
            shape = self.__parse_layout_shape(ori_row, ori_col)
            if not shape is None:
                layout_specifier = self._get_cell_value(ori_row - 1, ori_col)
                layout_container = \
                    LayoutParsingContainer(parser=self._parser,
                                           shape=shape,
                                           top_left_position=top_left_pos)
                rack_containers = \
                        self._parse_layout_specifiers(layout_specifier,
                                                      layout_container)
                if not rack_containers is None:
                    # Store racks.
                    for rack_container in rack_containers:
                        rack_container.add_layout_container(layout_container)
                        rack_label = rack_container.rack_label
                        if not self._parser.rack_map.has_key(rack_label):
                            self._parser.rack_map[rack_label] = rack_container
                    # Success!
                    result = layout_container
        return result

    def __parse_layout_shape(self, start_row, start_col):
        """
        Determines the dimensions of plate layout definition.
        """
        rack_row = 0
        rack_col = 0
        # Get number of rows, row labels are alphanumeric.
        while rack_row + start_row + 2 < self._row_number:
            row_value = self._get_cell_value(start_row + rack_row + 1,
                                             start_col)
            if row_value != label_from_number(rack_row + 1):
                break
            rack_row += 1
        # Get number of columns, column labels are numbers.
        while start_col + rack_col + 1 < self._col_number:
            col_value = self._get_cell_value(start_row,
                                             start_col + rack_col + 1)
            if col_value != rack_col + 1:
                break
            rack_col += 1
        if not (rack_row, rack_col) in self._parser.allowed_rack_dimensions:
            msg = 'Invalid layout block shape (%ix%i). Make sure you ' \
                  'have placed an "%s" maker, too.' % (rack_row, rack_col,
                                                       self._END_MARKER)
            self._create_error(msg, self._get_cell_name(start_row, start_col))
            result = None
        else:
            shape = RackShapeParsingContainer(self._parser, rack_row,
                                              rack_col)
            result = shape
            if self._parser.HAS_COMMON_LAYOUT_DIMENSION:
                if self._parser.shape is None:
                    self._parser.shape = shape
                elif not shape == self._parser.shape:
                    msg = 'There are 2 different layout shapes in the file ' \
                          '(%s and %s). For this parser, all layout ' \
                          'dimensions have to be the same.' \
                          % (shape, self._parser.shape)
                    self._create_error(msg)
                    result = None
        return result

    def _parse_layout_specifiers(self, layout_specifier, layout_container):
        """
        Returns the RackParsingContainers for the racks associated with
        this layout.
        """
        raise NotImplementedError('Abstract method')

    def _parse_layout_codes(self, layout_container, tag_definitions):
        """
        Gets the tag values for the codes of this layout container
        and stores them in the layout container.
        """
        for cell_indices in layout_container.get_all_layout_cells():
            table_row, table_col = cell_indices[0], cell_indices[1]
            code = self._get_cell_value(table_row, table_col)
            if code is None:
                continue
            for tag_definition in tag_definitions:
                value = self._get_tag_value_for_code(tag_definition, code)
                if value is None:
                    break
                layout_container.add_tagged_position(tag_definition.predicate,
                                                     value, cell_indices)

    def _get_tag_value_for_code(self, tag_definition, code):
        """
        Fetches the tag value for a particular code.
        Overwrite this method if you need to perform specific checks.
        """
        return tag_definition.get_value_for_code(code)


class LayoutParsingContainer(ExcelParsingContainer):
    """
    ParsingContainer subclass for the storage of layouts.

    A LayoutParsingContainer corresponds to one layout (rack
    pattern) definition in the source Excel file.
    """
    _PARSER_CLS = ExcelLayoutFileParser

    def __init__(self, parser, shape, top_left_position):
        """
        Constructor.

        :param shape: the dimension of the layout (row number and column number)
        :type shape: :class:`RackShapeparsingContainer`
        :param top_left_position: top left position of the layout
            pattern within the Excel File, also used as key for
            the layout container
        :type top_left_position: tuple (row_index (int), column_index (int))
        """
        ExcelParsingContainer.__init__(self, parser)
        self.shape = shape
        self.top_left_position = top_left_position
        self.layout_cells = None
        #: Stores the position for each tag predicate-value combination.
        self.tag_data = dict()
        #: Map with key: position_set hash_value and value: tags for this set.
        self.positions_tag_map = {}

    def get_all_layout_cells(self):
        """
        Returns the sheet indices for each cell beloning the layout.

        :rtype: list of tuples (row_index (int), column_index (int))
        """
        if self.layout_cells is None:
            layout_cells = []
            for row in range(self.shape.row_number):
                row_index = self.top_left_position[0] + 1 + row
                for column in range(self.shape.column_number):
                    column_index = self.top_left_position[1] + 1 + column
                    layout_cells.append((row_index, column_index))
            self.layout_cells = layout_cells
        return self.layout_cells

    def get_unique_key(self):
        """
        Returns a unique key of the LayoutParsingContainer composed
        of the name of sheet and its top left position.

        :rtype: string
        """
        return '%s%i%i' % (self._parser.get_sheet_name(self._parser.sheet),
                           self.top_left_position[0],
                           self.top_left_position[1])

    def get_starting_cell_name(self):
        """
        Returns the cell name of the top left position.
        """
        if self._parser.layouts_have_specifiers:
            row_index = self.top_left_position[0] - 1
        else:
            row_index = self.top_left_position[0]
        return self._PARSER_CLS.get_cell_name(row_index,
                                              self.top_left_position[1])

    def add_tagged_position(self, tag_predicate, tag_value, cell_indices):
        """
        Stores the tag data in the :attr:`tag_data` map.
        """
        tag_container = TagParsingContainer(parser=self._parser,
                                    predicate=tag_predicate, value=tag_value)
        rack_pos_container = self.get_rack_position_container(cell_indices)
        add_list_map_element(self.tag_data, tag_container, rack_pos_container)

    def get_rack_position_container(self, cell_indices):
        """
        Converts the given cell indices into a rack position parsing container
        (using the top left position of the layout container as offset).
        """
        return RackPositionParsingContainer(parser=self._parser,
              row_index=(cell_indices[0] - self.top_left_position[0] - 1),
              column_index=(cell_indices[1] - self.top_left_position[1] - 1))

    def __str__(self):
        return self.get_starting_cell_name()


class TagDefinitionParsingContainer(ExcelParsingContainer):
    """
    ParsingContainer subclass for the storage of a tags including all its
    value-code pairs.

    A TagParsingContainer corresponds to one tag-value-code definition in the
    source excel file.
    """
    _PARSER_CLS = ExcelLayoutFileParser

    def __init__(self, parser, tag_predicate, start_row_index):
        """
        Constructor.

        :param str tag_predicate: predicate of the tag (string)
        :param int start_row_index: row index of the factor marker for this
            tag definition
        """
        ExcelParsingContainer.__init__(self, parser)
        self.predicate = tag_predicate
        self.start_row_index = start_row_index
        self.values = []
        self.__code_map = {}
        self.inactive = False

    def has_code(self, code):
        """
        Evaluates whether the given codes has already been registered before.
        """
        return self.__code_map.has_key(code)

    def add_code_and_value(self, value, code):
        """
        Adds a value (level) and its code this tag.

        :param str value: The value.
        :param str code: The code for the value.
        """
        if value is None or value == '':
            self.inactive = True
        else:
            if not self.inactive:
                if self.__code_map.has_key(code):
                    msg = 'Duplicate code "%s" for factor "%s".' \
                          % (code, self.predicate)
                    self._create_error(msg)
                else:
                    if not value in self.values:
                        self.values.append(value)
                    self.__code_map[code] = value

    def get_value_for_code(self, code):
        """
        Returns the tag value encrypted by the code.

        :param code: Tag value code (string of pattern-color-definition).
        :returns: associated tag value (if any; string)
        """
        try:
            result = self.__code_map[code]
        except KeyError:
            msg = 'Tag value (level) code "%s" not found for factor "%s".' \
                   % (get_trimmed_string(code), self.predicate)
            self._create_error(msg)
            result = None
        return result

    def __eq__(self, other):
        return self.predicate == other.predicate

    def __hash__(self):
        return hash(self.predicate)

    def __str__(self):
        return '<%s %s>' % (self.__class__.__name__, self.predicate)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__ , self.predicate)


class TagParsingContainer(ExcelParsingContainer):
    """
    Simple parsing container storing a tag predicate and value.
    """
    _PARSER_CLS = BaseParser

    def __init__(self, parser, predicate, value):
        """
        Constructor.

        :param str predicate: The tag predicate is the factor name.
        :param value: The tag value is the level.
        """
        ExcelParsingContainer.__init__(self, parser)
        #: The tag predicate is the factor name.
        self.predicate = predicate
        #: The tag value is the level.
        self.value = value

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
             self.predicate == other.predicate and \
             self.value == other.value

    def __hash__(self):
        return hash('%s%s' % (self.predicate, self.value))


    def __str__(self):
        return '<%s %s:%s>' % (self.__class__.__name__, self.predicate,
                               self.value)

    def __repr__(self):
        return '<%s %s:%s>' % (self.__class__.__name__ , self.predicate,
                               self.value)


class RackParsingContainer(ExcelParsingContainer):
    """
    Parsing container representing a rack or design rack.

    The content of the rack is defined by layouts
    (stored in :class:LayoutParsingContainers).
    """
    _PARSER_CLS = ExcelLayoutFileParser

    def __init__(self, parser, rack_label):
        """
        Constructor.

        :param str rack_label: Number or barcode of the design_rack; also
            serves as key.
        """
        ExcelParsingContainer.__init__(self, parser)
        #: barcode or number of the rack, also serves as key
        self.rack_label = rack_label
        #: list of LayoutParsingContainer keys (top_left_positions)
        #: associated to that rack
        self.layout_container_keys = []

    def add_layout_container(self, layout_container):
        """
        Adds a LayoutParsingContainerKey to this parsing container.
        Also passes the layout container to the layout map of the parser
        if it does not know the layout container yet.

        :param layout_container: the layout container to associate
        :type layout_container: :class:`LayoutParsingContainer`
        """
        layout_key = layout_container.get_unique_key()
        self.layout_container_keys.append(layout_key)
        if not layout_key in self._parser.layout_map:
            self._parser.layout_map[layout_key] = layout_container

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
                 self.rack_label == other.rack_label

    def __str__(self):
        return self.rack_label

    def __repr__(self):
        str_format = '<%s %s>'
        params = (self.__class__.__name__, self.rack_label)
        return str_format % params


class ExcelMoleculeDesignPoolLayoutParser(ExcelLayoutFileParser): #pylint: disable=W0223
    """
    Excel layout parser for files that might contain molecule design pool
    layouts (floating positions must be replaced by markers depending on the
    position).
    """
    #: A marker used in files to indicate (customized) molecule design pool ID
    #: placeholders.
    FLOATING_MARKER = 'sample'

    def __init__(self, stream, parent=None):
        ExcelLayoutFileParser.__init__(self, stream, parent=parent)
        #: Aliases for molecule design predicates.
        self.molecule_design_id_predicates = []
        #: Counts the molecule designs for floating positions.
        self.floating_counter = 0
        #: Maps codes for floating positions onto tag_values.
        self.floating_map = {}
        #: Indicator for molecule design tag values of floating positions.
        self.no_id_indicator = None
        #: This is the tag defintion container for molecule design pools.
        self.pool_tag_definition = None

    def reset(self):
        ExcelLayoutFileParser.reset(self)
        self.floating_counter = 0
        self.floating_map = {}
        self.pool_tag_definition = None

    def _check_and_replace_floatings(self):
        """
        If there is only one distinct marker for the floating ISO positions
        in the layouts each position will get an own molecule design pool.
        """
        if len(self.floating_map) == 1:
            self._replace_floatings()

    def _replace_floatings(self):
        """
        Replaces the markers floating ISO for each floating ISO position
        by an own molecule design pool placeholder.
        """
        pool_predicate = self.pool_tag_definition.predicate
        for layout_container in self.layout_map.values():
            pool_tag = None
            for tag_container in layout_container.tag_data.keys():
                if not tag_container.predicate == pool_predicate:
                    continue
                elif not isinstance(tag_container.value, str):
                    continue
                elif self.no_id_indicator in tag_container.value:
                    pool_tag = tag_container
                    break
            if pool_tag is None:
                continue
            positions = layout_container.tag_data[pool_tag]
            del layout_container.tag_data[pool_tag]
            counter = 0
            for pos_container in layout_container.shape.position_containers:
                if not pos_container in positions:
                    continue
                counter += 1
                placeholder = '%s%03i' % (self.no_id_indicator, counter)
                new_tag = TagParsingContainer(parser=self,
                                predicate=pool_predicate, value=placeholder)
                layout_container.tag_data[new_tag] = [pos_container]


class ExcelMoleculeDesignPoolLayoutParsingContainer(#pylint: disable=W0223
                                            ExcelLayoutSheetParsingContainer):
    """
    Excel layout sheet parsing container for sheets that might contain
    molecule design pool layouts (floating positions must be replaced
    by markers depending on the position).
    """
    _PARSER_CLS = ExcelMoleculeDesignPoolLayoutParser

    def _init_tag_definition_container(self, predicate):
        """
        We also need to check whether the predicate is a molecule design
        pool alias.
        """
        container = ExcelLayoutSheetParsingContainer.\
                        _init_tag_definition_container(self, predicate)
        result = container
        if not container is None:
            conv_predicate = self._convert_keyword(predicate)
            for alias in self._parser.molecule_design_id_predicates:
                md_alias = self._convert_keyword(alias)
                if md_alias == conv_predicate:
                    if not self._parser.pool_tag_definition is None:
                        result = None
                        msg = 'There are 2 different molecule design pool ' \
                              'tag definitions ("%s" and "%s")!' \
                               % (self._parser.pool_tag_definition.predicate,
                                  predicate)
                        self._create_error(msg)
                    self._parser.pool_tag_definition = container
                    break
        return result

    def _get_tag_value_for_code(self, tag_definition, code):
        """
        In case of floating molecule design pools we might have to replace the
        tag value by a floating placeholder.
        """
        tag_value = ExcelLayoutSheetParsingContainer._get_tag_value_for_code(
                                                    self, tag_definition, code)
        if self._parser.pool_tag_definition is None:
            result = tag_value
        elif not (tag_definition == self._parser.pool_tag_definition and
                  self._parser.FLOATING_MARKER in str(tag_value).lower()):
            result = tag_value
        else:
            result = self.__get_floating_md_tag_value(code)
        return result

    def __get_floating_md_tag_value(self, code):
        """
        Derives a sample_marker for FloatingIsoPositions.
        """
        if code in self._parser.floating_map:
            result = self._parser.floating_map[code]
        else:
            self._parser.floating_counter += 1
            tag_value = self._parser.no_id_indicator + \
                                '%03i' % (self._parser.floating_counter)
            self._parser.floating_map[code] = tag_value
            result = tag_value
        return result
