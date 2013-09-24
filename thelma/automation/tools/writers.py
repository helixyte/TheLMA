"""
:Date: 12 Aug 2011
:Author: AAB, berger at cenix-bioscience dot com

This is an abstract super class for CSV stream generators.
"""

from StringIO import StringIO
from thelma.automation.tools.base import BaseAutomationTool
from zipfile import BadZipfile
import logging
import zipfile

__docformat__ = 'reStructuredText en'

__all__ = ['LINEBREAK_CHAR',
           'CsvWriter',
           'CsvColumnParameters',
           'TxtWriter',
           'create_zip_archive',
           'read_zip_archive',
           'merge_csv_streams']


#: The character used to mark line breaks (default: Windows = \'\\r\\n',
#: Mac = \'\\n\').
LINEBREAK_CHAR = '\r\n'


class CsvWriter(BaseAutomationTool):
    """
    A base tool to generate CSV file streams.

    **Return Value:** a file stream (CSV format)
    """

    #: The delimiter used to separate columns.
    DELIMITER = ','

    def __init__(self, log=None, logging_level=logging.WARNING,
                 add_default_handlers=False, depending=True):
        """
        Constructor:

        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param logging_level: the desired minimum log leve l
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*

        :param depending: Defines whether a tool can be initialized directly
            (*False*) of if it is always called by other tools (*True*).
            Depending tools must obtain a log and are not capable to
            reset a log.
        :type depending: :class:`bool`
        :default depending: *True*
        """
        BaseAutomationTool.__init__(self, log, logging_level,
                                    add_default_handlers, depending)

        #: The stream to be generated.
        self.__stream = None

        #: Maps :class:`CsvColumnDictionary`s onto column indices.
        self._index_map = None
        #: A list with of :class:`CsvColumnDictionary` (to be set by the
        #: subclasses).
        self._column_map_list = None

        #: A boolean that defines whether to print a header.
        self._write_headers = True

    def reset(self):
        """
        Resets all attributes except for the user input.
        """
        BaseAutomationTool.reset(self)
        self.__stream = None
        self._column_map_list = None
        self._index_map = None

    def run(self):
        """
        Creates a stream and write the data into it.
        """
        self.reset()
        self.add_info('Start CSV generation ...')
        self._init_column_map_list()
        if not self.has_errors(): self.__init_index_map()
        if not self.has_errors(): self.__init_stream()
        if not self.has_errors(): self.__write_stream()
        if not self.has_errors():
            self.add_info('CSV generation complete.')
            self.return_value = self.__stream

    def get_result(self, write_headers=True, run=True): #pylint: disable=W0221
        """
        Returns the return value.

        :param write_headers: A boolean that defines whether to print a header.
        :type write_headers: :class:`boolean`
        :default write_headers: *True*
        :param run: Determines whether the tool shall call the
                :func:`run` method (it can also be called separately).
        :type run: :class:`boolean`
        :default run: *True*
        """
        self._write_headers = write_headers
        if run: self.run()
        return self.return_value

    def _init_column_map_list(self):
        """
        Creates the :attr:`_column_map_list`
        """
        raise NotImplementedError('Abstract method.')

    def __init_index_map(self):
        """
        Checks the validity of the passed column map and generates the
        :attr:`_index_map`.
        """
        if self.__validate_column_maps():
            index_map = dict()
            for column_map in self._column_map_list:
                index_map[column_map.column_index] = column_map
            self._index_map = index_map

    def __validate_column_maps(self):
        """
        Checks the validity of the :attr:`column_map_list` (classes,
        index consistency, etc.).
        """

        if self._column_map_list is None:
            self.add_error('The column map list must not be None!')
            return False

        if len(self._column_map_list) < 1:
            self.add_error('The column map must not be empty!')
            return False

        indices = []
        for column_parameters in self._column_map_list:
            if isinstance(column_parameters, list):
                for msg in column_parameters:
                    self.add_error(msg)
                return False
            column_index = column_parameters.column_index
            if column_index in indices:
                msg = 'Duplicate column index %i (column %s).' \
                      % (column_index, column_parameters.header_name)
                self.add_error(msg)
                return False
            indices.append(column_index)

        indices.sort()
        for i in range(len(indices)):
            if not i == indices[i]:
                msg = 'No parameters for column index %i!' % (i)
                self.add_error(msg)
                return False

        return True

    def __init_stream(self):
        """
        Initialises the stream.
        """
        self.add_debug('Initialize stream ...')
        self.__stream = StringIO()

    def __write_stream(self):
        """
        Writes the body into the stream.
        """

        self.add_debug('Prepare body ...')

        line_count = len(self._index_map[0].value_list)

        for column_map in self._column_map_list:
            value_list = column_map.value_list
            if len(value_list) != line_count:
                msg = 'The columns have different numbers of values!'
                self.add_error(msg)
        if line_count < 1:
            self.add_error('There is no data to be printed!')

        if not self.has_errors() and self._write_headers:
            self.__write_header()
        if not self.has_errors():
            self.__write_data_lines(line_count)
            self.__stream.seek(0)

    def __write_header(self):
        """
        Writes the column header line into the stream.
        """

        if self._write_headers:
            indices = self._index_map.keys()
            indices.sort()
            header_values = []
            for index in indices:
                column_map = self._index_map[index]
                header_values.append(column_map.header_name)
            self.__write_line(header_values)

    def __write_line(self, line_values):
        """
        Generates a writable line from a list of values.
        """
        raw_line = self.DELIMITER.join(str(i) for i in line_values)
        w_line = '%s%s' % (raw_line, LINEBREAK_CHAR)
        self.__stream.write(w_line)

    def __write_data_lines(self, line_count):
        """
        Generates the actual data lines and writes them into the stream.
        """
        self.add_debug('Print data lines ...')

        indices = self._index_map.keys()
        indices.sort()

        for i in range(line_count):
            data_values = []
            for column_index in indices:
                value_list = self._index_map[column_index].value_list
                data_values.append(value_list[i])
            self.__write_line(data_values)


class CsvColumnParameters(object):
    """
    This class collects data required to create a column in an CSV file
    (column index, a header and a value list).
    """

    #: The index of the column within the CSV.
    column_index = None
    #: The header for the column.
    header_name = None
    #: A list containing the values for this column.
    value_list = None

    def __init__(self, column_index, header_name, value_list):
        """
        Constructor:

        :param column_index: The index of the column within the CSV.
        :type column_index: :class:`int`

        :param header_name: The column header.
        :type header_name: :class:`basestring`

        :param value_list: A list containing the values for this column.
        :type value_list: list with atomic values
        """

        self.column_index = column_index
        self.header_name = header_name
        self.value_list = value_list

    @classmethod
    def create_csv_parameter_map(cls, column_index, header_name, value_list):
        """
        Creates an instance of :class:`CsvColumnParameters` using the passed
        values. The values are checked for validity. If at least one parameter
        is not valid, the method will return a list of errors instead.

        :param column_index: The index of the column within the CSV.
        :type column_index: :class:`int`

        :param header_name: The column header.
        :type header_name: :class:`basestring`

        :param value_list: A list containing the values for this column.
        :type value_list: list with atomic values
        :return: A valid :class:`CsvColumnParameters` object or an error
            message.
        """

        errors = CsvColumnParameters.check_validity(column_index,
                                                      header_name, value_list)
        if len(errors) > 0: return errors
        return CsvColumnParameters(column_index, header_name, value_list)

    @classmethod
    def check_validity(cls, column_index, header_name, value_list):
        """
        Checks whether all input values are valid.

        :param column_index: The index of the column within the CSV.
        :type column_index: :class:`int`

        :param header_name: The column header.
        :type header_name: :class:`basestring`

        :param value_list: A list containing the values for this column.
        :type value_list: list with atomic values
        :return: A list with error messages.
        """

        errors = []
        if column_index is None:
            errors.append('The column index must not be None!')
        if not isinstance(column_index, int):
            errors.append('The column index must be an integer!')
        if header_name is None or len(header_name) < 1:
            errors.append('The header name must not be None or empty!')
        if not isinstance(header_name, basestring):
            errors.append('The header name must be string or unicode!')
        if value_list is None:
            errors.append('You must pass a value list!')
        if len(value_list) < 1:
            errors.append('The value list does not contain any values!')
        return errors

    def __str__(self):
        return '%s column map' % (self.header_name)

    def __repr__(self):
        str_format = '<CsVColumnParameters %s, index: %s>'
        params = (self.header_name, self.column_index)
        return str_format % params


class TxtWriter(BaseAutomationTool):
    """
    A base tool to generate TXT file streams.

    **Return Value:** a file stream (TXT format)
    """

    def __init__(self, log=None, logging_level=logging.WARNING,
                 add_default_handlers=False, depending=True):
        """
        Constructor:

        :param log: The ThelmaLog you want to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param logging_level: the desired minimum log leve l
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*

        :param depending: Defines whether a tool can be initialized directly
            (*False*) of if it is always called by other tools (*True*).
            Depending tools must obtain a log and are not capable to
            reset a log.
        :type depending: :class:`bool`
        :default depending: *True*
        """
        BaseAutomationTool.__init__(self, log, logging_level,
                                    add_default_handlers, depending)

        #: The stream to be generated.
        self._stream = None

    def reset(self):
        """
        Resets all values except for the initialization values.
        """
        BaseAutomationTool.reset(self)
        self._stream = None

    def run(self):
        """
        Runs stream writer.
        """
        self.reset()
        self.add_info('Start TXT stream generation ...')
        self._check_input()
        if not self.has_errors(): self.__init_stream()
        if not self.has_errors(): self._write_stream_content()
        if not self.has_errors():
            self._stream.seek(0)
            self.return_value = self._stream
            self.add_info('Report generation completed.')

    def _check_input(self):
        """
        Checks if the tools has obtained correct input values.
        """
        raise NotImplementedError('Abstract method.')

    def __init_stream(self):
        """
        Initialises the stream.
        """
        self.add_debug('Initialise stream ...')
        self._stream = StringIO()

    def _write_stream_content(self):
        """
        Writes into the streams.
        """
        raise NotImplementedError('Abstract method.')

    def _write_headline(self, header_text, underline_char='-',
                        preceding_blank_lines=3, trailing_blank_lines=1):
        """
        Writes a header with the given features:

        :param header_text: The text for the head line.
        :type header_text: :class:`str`

        :param underline_char: The character that shall be used for underlining.
        :type underline_char: :class:`str`
        :default underline_char: \'-\'

        :param preceding_blank_lines: The number of blank lines before the
            head line.
        :type preceding_blank_lines: :class:`int`
        :default preceding_blank_lines: *3*

        :param trailing_blank_lines: The number of blank lines after the
            header line.
        :type trailing_blank_lines: :class:`int`
        :default trailing_blank_lines: *1*
        """

        preceding_lines = LINEBREAK_CHAR * preceding_blank_lines
        trailing_lines = LINEBREAK_CHAR * trailing_blank_lines
        underlining = underline_char * len(header_text)

        header_section = preceding_lines + header_text + LINEBREAK_CHAR \
                         + underlining + LINEBREAK_CHAR \
                         + trailing_lines
        self._stream.write(header_section)

    def _write_body_lines(self, line_list):
        """
        Writes the body of a section. The content of the body must be passed
        as a list of lines. Use this method to make sure you are applying the
        write line break character.

        :param line_list: The lines to be written as list.
        :type line_list: :class:`list`
        """

        content = LINEBREAK_CHAR.join(line_list)
        self._stream.write(content)


def create_zip_archive(zip_stream, stream_map):
    """
    Creates a zip archive from a stream.

    :param zip_stream: The file stream.
    :type zip_stream: :class:`StringIO`

    :param stream_map: The file streams mapped onto file names.
    :type stream_map: :class:`dict`

    :return: zip archive
    """
    archive = zipfile.ZipFile(zip_stream, 'a', zipfile.ZIP_DEFLATED, False)

    for zip_fn, stream in stream_map.iteritems():
        archive.writestr(zip_fn, stream.read())

    # Mark the files as having been created on Windows so that
    # Unix permissions are not inferred as 0000
    for zfile in archive.filelist: zfile.create_system = 0
    archive.close()

    return archive

def read_zip_archive(zip_stream):
    """
    Converts a zip stream into zip archive. Returns *None* if there are no
    file names in the zip stream. Otherwise the function will return
    a dictionary with file names as keys and streams as values.

    :param zip_stream: The file stream containing the archive.
    :type zip_stream: :class:`StringIO`

    :return: The file streams in the archive mapped onto file names.
    """
    try:
        archive = zipfile.ZipFile(zip_stream, 'r', zipfile.ZIP_DEFLATED, False)
    except BadZipfile:
        return None

    zip_map = dict()
    for fn in archive.namelist():
        content = archive.read(fn)
        zip_map[fn] = StringIO(content)
    return zip_map

def merge_csv_streams(stream_map):
    """
    Merges the given streams into one.

    :param stream_map: The streams mapped onto job indices or another
        number value suitable for sorting.
    :type stream_map: :class:`dict`

    :return: The merged stream.
    """
    if len(stream_map) == 1: return stream_map.values()[0]

    merged_stream = None

    indices = stream_map.keys()
    indices.sort()
    for i in indices:
        stream = stream_map[i]
        stream.seek(0)

        if merged_stream is None:
            merged_stream = StringIO()
            content = stream.read()
            merged_stream.write(content)
            continue

        content_lines = stream.read().split(LINEBREAK_CHAR)
        for j in range(len(content_lines)):
            if j == 0: continue
            c_line = content_lines[j]
            if len(c_line) < 1: continue
            merged_stream.write('%s%s' % (c_line, LINEBREAK_CHAR))

    merged_stream.seek(0)
    return merged_stream
