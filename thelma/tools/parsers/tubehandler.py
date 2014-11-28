"""
General
.......

This parser deals with XL20 (tubehandler) output files. These are log files
of the XL20 recording information about tube movements between tube racks.
The outcome of the parser is used to update tube locations in the stock.

Composition of Source Files
...........................

  * The output files are plain CSV-files (separator: comma) without header.

  * The columns contain from (left to right):

    1. job id (not needed in Thelma)
    2. step number within the worklist (not needed in Thelma)
    3. date (format: %m/%d/%y - see `Date Format Key`_ for details)
    4. time (format: %H:%M:%S - see `Date Format Key`_ for details)
    5. source rack barcode (8-digit number starting with '0')
    6. source rack position (1 or 2 letters followed by 1 or 2 digits)
    7. target rack barcode (8-digit number starting with '0')
    8. target rack position (1 or 2 letters followed by 1 or 2 digits)
    9. expected tube barcode
    10. found tube barcode
    11. tube weight (not needed in Thelma)
    12. temperature (not needed in Thelma)
    13. error descriptions

    :Note: Barcode and position label verification is taken over by the handler.


Date Format Key
...............

According to `http://docs.python.org/library/datetime.html` (23rd Aug 2012):

    %d - Day of the month as a decimal number [01,31].
    %H - Hour (24-hour clock) as a decimal number [00,23].
    %m - Month as a decimal number [01,12].
    %M - Minute as a decimal number [00,59].
    %S - Second as a decimal number [00,61].
    %y - Year without century as a decimal number [00,99].

AAB
"""

from datetime import datetime
from thelma.tools.parsers.base import ParsingContainer
from thelma.tools.parsers.base import TxtFileParser
from thelma.utils import as_utc_time


__docformat__ = "reStructuredText en"

__all__ = ['XL20OutputParser']


class XL20OutputParser(TxtFileParser):
    """
    Parses a XL20 (tubehandler) output file.
    """
    NAME = 'XL20 Output File Parser'

    #: The expected number of columns for a complete line.
    NUMBER_COLUMNS = 13
    #: The column separator.
    SEPARATOR = ','

    #: The index of the date column.
    DATE_INDEX = 2
    #: The index of the time column.
    TIME_INDEX = 3

    #: The index of the source rack barcode column.
    SOURCE_RACK_BARCODE_INDEX = 4
    #: The index of the source position column.
    SOURCE_POSITION_INDEX = 5
    #: The index of the target rack barcode column.
    TARGET_RACK_BARCODE_INDEX = 6
    #: The index of the target position column.
    TARGET_POSITION_INDEX = 7

    #: The index of the column with the expected tube barcode.
    EXPECTED_TUBE_BACODE_INDEX = 8
    #: The index of the column with tube barcode that has actually been found.
    FOUND_TUBE_BARCODE_INDEX = 9

    #: The index of the error description column.
    ERROR_DESCRIPTION_INDEX = 12

    #: The format of the date.
    DATE_FORMAT = '%m/%d/%y'
    #: The format of the time.
    TIME_FORMAT = '%H:%M:%S'

    def __init__(self, stream, parent=None):
        TxtFileParser.__init__(self, stream, parent=parent)
        #: The tube transfer items found (stored as
        #: :class:`XL20TransferParsingContainer`).
        self.xl20_transfers = None
        # Intermediate error storage
        self.__incomplete_line = None
        self.__error_descriptions = None
        self.__inconsistent_tube_barcodes = None
        self.__invalid_timestamp = None

    def reset(self):
        """
        Reset all parser values except for initialisation values.
        """
        TxtFileParser.reset(self)
        self.xl20_transfers = []
        self.__incomplete_line = []
        self.__error_descriptions = []
        self.__inconsistent_tube_barcodes = []
        self.__invalid_timestamp = []

    def run(self):
        """
        Runs the parser.
        """
        self.reset()
        self.add_info('Start parsing ...')
        self.has_run = True
        self._split_into_lines()
        if not self.has_errors():
            self.__parse_data_lines()
            self.__record_messages()
        if not self.has_errors():
            self.add_info('Parsing completed.')

    def __parse_data_lines(self):
        """
        Parses the content of the file (line-wise).
        """
        self.add_debug('Parse data lines ...')

        for i in range(len(self._lines)):
            line = self._lines[i]
            if len(line) < 1: continue
            transfer_container = self.__parse_line(line, i)
            if not transfer_container is None:
                self.xl20_transfers.append(transfer_container)

    def __parse_line(self, line, i):
        """
        Converts the given line into a storage container instance (requires
        a tube barcode!).
        """
        column_values = line.split(self.SEPARATOR)
        if len(column_values) < self.NUMBER_COLUMNS:
            info = 'line %i (%s)' % (i + 1, line)
            self.__incomplete_line.append(info)
            return None

        error_msg = self.SEPARATOR.join(
                                column_values[self.ERROR_DESCRIPTION_INDEX:])
        if len(error_msg) > 1:
            info = 'line %i ("%s")' % (i + 1, error_msg)
            self.__error_descriptions.append(info)

        expected_tube_barcode = column_values[self.EXPECTED_TUBE_BACODE_INDEX]
        if expected_tube_barcode == '': return None # no data
        found_tube_barcode = column_values[self.FOUND_TUBE_BARCODE_INDEX]
        if not expected_tube_barcode == found_tube_barcode:
            info = 'line %i (%s (expected) and %s (found))' \
                   % (i + 1, expected_tube_barcode, found_tube_barcode)
            self.__inconsistent_tube_barcodes.append(info)

        transfer_container = XL20TransferParsingContainer(parser=self,
                                line_index=i, line_values=column_values)
        if transfer_container.timestamp is None:
            info = 'line %i (%s, %s)' % (i + 1, column_values[self.DATE_INDEX],
                                        column_values[self.TIME_INDEX])
            self.__invalid_timestamp.append(info)

        return transfer_container

    def __record_messages(self):
        """
        Records errors and warnings collected during the parsing process.
        Sorting is not necessary here, because the items of the error
        lists are already in order of the lines.
        """
        self.add_debug('Record errors and warnings ...')

        if len(self.__incomplete_line) > 0:
            msg = 'The following lines are shorter than expected: %s. ' \
                  'Assumed number of values per line: %i.' \
                  % (' - '.join(self.__incomplete_line), self.NUMBER_COLUMNS)
            self.add_error(msg)

        if len(self.__error_descriptions) > 0:
            msg = 'Some lines contain error messages: %s.' \
                  % (' - '.join(self.__error_descriptions))
            self.add_warning(msg)

        if len(self.__inconsistent_tube_barcodes) > 0:
            msg = 'Attention! Expected tube barcode and the tube barcode ' \
                  'actually found do not always match. Details: %s. If you ' \
                  'continue, the following processes will only use the ' \
                  'expected barcodes.' \
                  % (' - '.join(self.__inconsistent_tube_barcodes))
            self.add_warning(msg)

        if len(self.__invalid_timestamp) > 0:
            msg = 'Could not parse the timestamp for the following lines: %s.' \
                  % (' - '.join(self.__invalid_timestamp))
            self.add_error(msg)


class XL20TransferParsingContainer(ParsingContainer):
    """
    Intermediate storage of the content of a XL20 output line.
    """
    def __init__(self, parser, line_index, line_values):
        """
        Constructor:

        :param line_index: The index of the line containing this data.
        :type line_index: :class:`int`

        :param line_values: The line values as list (in the same order as in
            the file.
        :type line_values: :class:`list`
        """
        ParsingContainer.__init__(self, parser=parser)

        #: The number of the line containing this data.
        self.line_number = line_index + 1

        parser = self._parser
        #: The source rack barcode.
        self.source_rack_barcode = line_values[parser.SOURCE_RACK_BARCODE_INDEX]
        #: The source position label.
        self.source_position_label = line_values[parser.SOURCE_POSITION_INDEX]
        #: The target rack barcode.
        self.target_rack_barcode = line_values[parser.TARGET_RACK_BARCODE_INDEX]
        #: The target position label.
        self.target_position_label = line_values[parser.TARGET_POSITION_INDEX]

        #: The barcode of the expected tube.
        self.tube_barcode = line_values[parser.EXPECTED_TUBE_BACODE_INDEX]

        #: The timestamp of the transfer (:class:`datetime` object).
        self.timestamp = self.__convert_timestamp(
                line_values[parser.DATE_INDEX], line_values[parser.TIME_INDEX])

    def __convert_timestamp(self, date_str, time_str):
        """
        Converts date and time strings into a timestamp.
        """
        joined_str = '%s %s' % (date_str, time_str)
        joined_format = '%s %s' % (self._parser.DATE_FORMAT,
                                   self._parser.TIME_FORMAT)
        try:
            timestamp = datetime.strptime(joined_str, joined_format)
        except ValueError:
            return None
        else:
            return as_utc_time(timestamp)

    def __str__(self):
        return '%i:%s' % (self.line_number, self.tube_barcode)

    def __repr__(self):
        str_format = '<%s line %i, tube barcode: %s, from: %s (%s), to: ' \
                     '%s (%s)>'
        params = (self.__class__.__name__, self.line_number, self.tube_barcode,
                  self.source_rack_barcode, self.source_position_label,
                  self.target_rack_barcode, self.target_position_label)
        return str_format % params
