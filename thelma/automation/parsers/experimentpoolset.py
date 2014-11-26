"""
:Date: 2011 July
:Author: AAB, berger at cenix-bioscience dot com

This is an Excel parser getting molecule design pool sets from Excel Files.
The molecule design pool IDs can for instance be used for the generation of
ISOs.

About Molecule Design Pools
..........................

.. currentmodule:: thelma.entities.moleculedesign

:class:`PoolSet` object contain a number of molecule design pools. There
are 2 possible types of molecule design pool sets:

    * *Library*: These are predefined sets used for multiple purposes.
    * *Custom*: These are (smaller) sets for to specific tasks.

The molecule design pool sets generated by the handler of this parser are
treated as custom sets.

.. currentmodule:: thelma.entities.experiment

Molecule design pool sets can be part of experiment metadata
(:class:`ExperimentMetadata`). However, there are only required if there are
floating ISO positions in the experiment metadata's ISO request
(:class:`thelma.entities.iso.IsoRequest`).

Parsing Notes
.............

The molecule design pools have to be specified on an Excel Sheet called
\'*Molecule Design Pool IDs*\' (case-insensitive). The parser will only search
the first column of the sheet.

The parsing proceeds as follows:

 1. open workbook
 2. get molecule design ID sheet
 3. get all IDs and convert them into integers (:class:`int`)


Composition of Source Files
...........................

* The excel sheet containing the ISO layout to be parsed must be
  called \'*Molecule Design Pool IDs*\' (case-insensitive).
* The molecule design pool IDs must be specified in the first column of the
  sheet. Other columns are ignored.
* There can be only one molecule design pool ID per cell.
* Parsing is interrupted as soon there is an empty cell.

:note: Sheet with other names will be ignored.
:note: xlsx files are not supported.

Implementation
..............
"""

from thelma.automation.parsers.base import ExcelFileParser
from thelma.entities.utils import label_from_number
from pyramid.compat import string_types

__docformat__ = "reStructuredText en"

__all__ = ['ExperimentPoolSetParser',
           ]


class ExperimentPoolSetParser(ExcelFileParser):
    """
    This parser parses lists of molecule designs. It returns a molecule
    design pool set
    (:class:`thelma.entities.moleculedesign.MoleculeDesignPoolSet`).
    """
    #: Name of the parser (requested by logs).
    NAME = 'Experiment Pool Set Parser'
    #: Name of the sheet containing the molecule design list.
    SHEET_NAME = 'Molecule Design Pools'
    #: The name of the column containing the molecule design pools IDs.
    COLUMN_NAME = 'Molecule Design Pool ID'

    def __init__(self, stream, parent=None):
        ExcelFileParser.__init__(self, stream, parent=parent)
        #: The Excel sheet containing the data.
        self.sheet = None
        #: a list of molecule design pool IDs (before validation)
        self.molecule_design_pool_ids = None
        #: The index of the column containing the molecule design pool IDs.
        self.column_index = None
        #: The message that is launched upon abort.
        self.abort_message = None

    def run(self):
        """
        Parses the molecule design pool ID list sheet.
        """
        self.reset()
        self.add_info('Start parsing of the molecule design pool list ...')
        if not self.has_errors():
            wb = self.open_workbook()
            self.sheet = self.__get_sheet(wb)
            if not self.has_errors():
                self.__parse_headers()
            if not self.has_errors():
                self.__parse_column()
            if not self.has_errors():
                self.add_info('Parsing completed.')

    def reset(self):
        """
        Resets the parser.
        """
        ExcelFileParser.reset(self)
        self.column_index = None
        self.molecule_design_pool_ids = set()
        self.abort_message = None

    def __get_sheet(self, workbook):
        """
        Checks whether there is a valid sheet in the excel file.
        """

        sheet = None
        for sheet_name in workbook.sheet_names():
            if sheet_name.upper().replace('_', ' ') == self.SHEET_NAME.upper():
                sheet = self.get_sheet_by_name(workbook, sheet_name)
                break
        if sheet is None:
            self.abort_execution = True
            self.abort_message = 'There is no molecule design pool list sheet ' \
                    'in this Excel File! A valid sheet must be called ' \
                    '"%s" (case-insensitive).' % (self.SHEET_NAME)
        return sheet

    def __parse_headers(self):
        """
        Parses the sheet headers and derives the column index of the molecule
        design pool ID column.
        """
        self.add_info('Search for molecule design pool column ...')

        row_index = 0
        column_number = self.get_sheet_column_number(self.sheet)
        for column_index in range(column_number):
            cell_value = self.get_cell_value(self.sheet, row_index,
                                             column_index)
            header = str(cell_value).strip()
            header = header.replace('_', ' ').replace('-', ' ')
            if header.upper() == self.COLUMN_NAME.upper():
                self.column_index = column_index
                break

        if self.column_index is None:
            msg = 'Could not find a column for the molecule design pool IDs! ' \
                  'A valid column must be called "%s" (case-insensitive).' \
                   % (self.COLUMN_NAME)
            self.add_error(msg)

    def __parse_column(self):
        """
        Gets the molecule design IDs and stores them.
        """
        row_index = 1
        row_count = self.get_sheet_row_number(self.sheet)
        while row_index < row_count:
            cell_value = self.get_cell_value(self.sheet, row_index,
                                             self.column_index)
            if cell_value is None:
                cell_name = self.get_cell_name(row_index, self.column_index)
                msg = 'Empty Cell in Row %i. Molecule design pool set ' \
                      'parsing is stopped here. All pool that have been ' \
                      'found so far are stored. Continue parsing of the ' \
                      'remaining sheets.' % (row_index + 1)
                warn_msg = self.format_log_message(self.SHEET_NAME, cell_name,
                                                   msg)
                self.add_warning(warn_msg)
                break
            pool_id = self.__get_integer_id(cell_value, row_index)
            if pool_id is None: break
            self.__check_for_duplicate_id(pool_id, row_index)
            self.molecule_design_pool_ids.add(pool_id)
            row_index += 1

        if len(self.molecule_design_pool_ids) < 1:
            self.abort_message = 'There are no molecule design pool IDs on ' \
                                 'the molecule design sheet!'
            self.abort_execution = True

    def __get_integer_id(self, cell_value, row_index):
        """
        Converts the parsed ID into an integer.
        """
        if isinstance(cell_value, int):
            result = cell_value
        elif isinstance(cell_value, float):
            result = int(cell_value)
        elif isinstance(cell_value, string_types):
            # FIXME: This is highly suspicious - do we really want to parse
            #        1.99999 as 1??
            if '.' in cell_value:
                cell_value = cell_value.split('.')[0]
            try:
                result = int(cell_value)
            except ValueError:
                result = None
                cell_name = '%s%i' \
                            % (label_from_number(self.column_index + 1),
                               row_index + 1)
                msg = 'There is a non-number character in row %i. ' \
                      % (row_index + 1)
                error_msg = self.format_log_message(self.SHEET_NAME,
                                                    cell_name, msg)
                self.add_error(error_msg)
            if not result is None:
                result = int(cell_value)
        return result

    def __check_for_duplicate_id(self, pool_id, row_index):
        """
        Checks whether the current molecule design has been found before.
        """
        if pool_id in self.molecule_design_pool_ids:
            cell_name = '%s%i' % (label_from_number(self.column_index + 1),
                                  row_index + 1)
            msg = 'Duplicate molecule design pool ID %i in row %i!' \
                  % (pool_id, row_index + 1)
            warning_msg = self.format_log_message(self.SHEET_NAME, cell_name,
                                                  msg)
            self.add_warning(warning_msg)
