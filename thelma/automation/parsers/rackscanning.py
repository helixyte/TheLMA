"""
.. currentmodule:: thelma.models.rack

General
.......

This parser deals with rack scanning output files. These file contain the tube
barcodes for each position of a 96-well tube rack in TXT format.


Composition of Source Files
...........................

* The first line contains the marker \'Date & time of Trace = \' plus
  a time stamp in format %d %b %Y %I:%M:%S %p (for key see
  `Timestamp Parsing Key`_). *Example:* ::

      Date & time of Trace = 23 Aug 2012 01:42:01 PM

* The second line contains the marker \'Rack Base Name:\' plus the
  8-digit rack barcode of the scanned rack (always starting with \'0\',
  see also: :attr:`RACK_BARCODE_REGEXP`). *Example:* ::

      Rack Base Name: 02498606

* The following list the rack positions and the scanned barcodes. Each line
  contains one data pair, the values are separated by \';\'.
  The first element of the line is the rack position label (with a two-digit
  column number, see also :attr:`RACK_POSITION_REGEXP`). The second element
  is either the tube barcode or the marker \'No TrakMate\' if the position
  is empty. *Example:* ::

          A01;    1034998087
          A02;    No TrakMate

Timestamp Parsing Key
.....................

According to `http://docs.python.org/library/datetime.html` (23rd Aug 2012):

    %b - Locale's abbreviated month name.
    %s - Day of the month as a decimal number [1, 31].
    %I - Hour (12-hour clock) as a decimal number [01,12].
    %M - Minute as a decimal number [00,59].
    %S - Second as a decimal number [00,61].
    %p - Locale's equivalent of either AM or PM.
    %Y - Year with century as a decimal number.

AAB
"""
from datetime import datetime
from thelma.automation.parsers.base import TxtFileParser
from thelma.utils import as_utc_time

__docformat__ = "reStructuredText en"

__all__ = ['RackScanningParser']


class RackScanningParser(TxtFileParser):
    """
    Parses a rack scanning output file.
    """

    NAME = 'Rack Scanning Output File Parser'

    #: Marks the time stamp line.
    TIMESTAMP_MARKER = 'Date & time of Trace ='
    #: Marks the rack barcode line.
    RACK_BARCODE_MARKER = 'Rack Base Name:'

    #: The format of the timestamp.
    TIMESTAMP_FORMAT = '%d %b %Y %I:%M:%S %p'

    #: Placeholder that is used if there is no tube at a position.
    NO_TUBE_PLACEHOLDER = 'No TrakMate'

    #: The line break character used.
    LINEBREAK_CHAR = '\r\n'
    #: The character used to separate the values of a barcode position line.
    SEPARATOR = ';'

    def __init__(self, stream, log):
        """
        Constructor:

        :param stream: stream of the file to parse.

        :param log: The ThelmaLog to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        TxtFileParser.__init__(self, stream=stream, log=log)

        #: The timestamp parsed from the file.
        self.timestamp = None
        #: The barcode of the rack to parse.
        self.rack_barcode = None

        #: The tube barcode (or None) for each label found (labels are
        #: validated before storage).
        self.position_map = None

    def reset(self):
        """
        Reset all parser values except for initialisation values.
        """
        TxtFileParser.reset(self)
        self.timestamp = None
        self.rack_barcode = None
        self.position_map = dict()

    def parse(self):
        """
        Runs the parser.
        """
        self.reset()
        self.add_info('Start parsing ...')
        self.has_run = True

        self._split_into_lines()
        if not self.has_errors(): self.__parse_timestamp()
        if not self.has_errors(): self.__parse_rack_barcode()
        if not self.has_errors(): self.__parse_position_data()
        if not self.has_errors(): self.add_info('Parsing completed.')

    def __parse_timestamp(self):
        """
        Parses the timestamp.
        """
        self.add_debug('Parse timestamp ...')

        for line in self._lines:
            if self.TIMESTAMP_MARKER in line:
                datestr = line.split(self.TIMESTAMP_MARKER)[1].strip()
                try:
                    self.timestamp = \
                        as_utc_time(datetime.strptime(datestr,
                                                      self.TIMESTAMP_FORMAT))
                except ValueError as errmsg:
                    self.add_error(errmsg)
                break

        if self.timestamp is None:
            msg = 'Unable do find time stamp!'
            self.add_error(msg)

    def __parse_rack_barcode(self):
        """
        Parses the rack barcode.
        """
        self.add_debug('Parse rack barcode ...')

        for line in self._lines:
            if self.RACK_BARCODE_MARKER in line:
                self.rack_barcode = line.split(self.RACK_BARCODE_MARKER)[1].\
                                    strip()
                break

        if self.rack_barcode is None:
            msg = 'Unable to find rack barcode!'
            self.add_error(msg)

    def __parse_position_data(self):
        """
        Parses the position data.
        """
        self.add_debug('Parse position data ...')

        for i in range(len(self._lines)):
            if self.has_errors(): break
            line = self._lines[i]
            if len(line) < 1: continue
            if self.TIMESTAMP_MARKER in line: continue
            if self.RACK_BARCODE_MARKER in line: continue

            msg = 'Unexpected content in line %i: %s' % (i + 1, line)
            if not self.SEPARATOR in line: self.add_error(msg)
            tokens = line.split(self.SEPARATOR)
            if not len(tokens) == 2: self.add_error(msg)
            if self.has_errors(): continue

            pos_label = tokens[0].strip()
            if self.position_map.has_key(pos_label):
                msg = 'Duplicate position label "%s"' % (pos_label)
                self.add_error(msg)
            if self.has_errors(): continue

            tube_barcode = tokens[1].strip()
            if tube_barcode == self.NO_TUBE_PLACEHOLDER: tube_barcode = None
            self.position_map[pos_label] = tube_barcode
