#"""
#Parses the excel file containing molecule design IDs for the pool libraries.
#
#Composition of Source Files
#...........................
#
# * The excel sheet containing the molecule designs in called
#   \'Molecule Designs\'.
# * The column containing the molecule designs is called \'Molecule Design IDs\'.
# * The column headers are expected in the first row.
# * The molecule designs in the column are separated by a comma.
# * Molecule design IDs must be integers.
# * Parsing is interrupted as soon there is an empty cell.
#
#AAB
#"""
#from thelma.automation.parsers.base import ExcelFileParser
#from thelma.automation.tools.utils.base import is_valid_number
#
#__docformat__ = "reStructuredText en"
#
#__all__ = ['LibraryMemberParser',
#           ]
#
#
#class LibraryMemberParser(ExcelFileParser):
#    """
#    Parses the excel sheet that provides the molecule designs for the
#    pools of a library.
#    """
#
#    #: name of the parser (requested by logs).
#    NAME = 'Library Member Parser'
#    #: name of the sheet containing the molecule design list.
#    SHEET_NAME = 'Molecule Designs'
#    #: The name of the column containing the molecule design pools IDs.
#    COLUMN_NAME = 'Molecule Design IDs'
#    #: Separates the molecule designs in one cell.
#    DELIMITER = ','
#
#    def __init__(self, stream, parent=None):
#        ExcelFileParser.__init__(self, stream, parent=parent)
#        #: The Excel sheet containing the data.
#        self.sheet = None
#        #: The molecule design lists founds (each record is a list
#        #: molecule design IDs).
#        self.molecule_design_lists = None
#        #: The index of the column containing the molecule design IDs.
#        self.__column_index = None
#
#    def reset(self):
#        ExcelFileParser.reset(self)
#        self.__column_index = None
#        self.molecule_design_lists = []
#
#    def run(self):
#        self.reset()
#        self.add_info('Start parsing ...')
#        wb = self.open_workbook()
#        self.sheet = self.get_sheet_by_name(wb, self.SHEET_NAME)
#        if not self.has_errors():
#            self.__determine_column_index()
#        if not self.has_errors():
#            self.__parse_column()
#        if not self.has_errors():
#            self.add_info('Parsing completed.')
#
#    def __determine_column_index(self):
#        """
#        The column is found by name.
#        """
#        self.add_debug('Find column index ...')
#
#        row_index = 0
#        column_number = self.get_sheet_column_number(self.sheet)
#
#        for col_index in range(column_number):
#            cell_value = self.get_cell_value(self.sheet, row_index, col_index)
#            cell_value = str(cell_value).replace('_', ' ')
#            if cell_value.upper() == self.COLUMN_NAME.upper():
#                self.__column_index = col_index
#                break
#
#        if self.__column_index is None:
#            msg = 'Unable to find molecule design column. A valid column ' \
#                  'must be called "%s" (case-insensitive).' % (self.COLUMN_NAME)
#            self.add_error(msg)
#
#    def __parse_column(self):
#        """
#        Finds the molecule design IDs.
#        """
#        self.add_debug('Parse column ...')
#
#        row_index = 1
#        row_count = self.get_sheet_row_number(self.sheet)
#
#        invalid_numbers = []
#
#        while row_index < row_count:
#            cell_value = self.get_cell_value(self.sheet, row_index,
#                                             self.__column_index)
#            if cell_value is None: break
#            md_ids = str(cell_value).split(self.DELIMITER)
#            valid = True
#            for md_id in md_ids:
#                if not is_valid_number(md_id, is_integer=True):
#                    info = '%i (%s)' % ((row_index + 1), md_ids)
#                    invalid_numbers.append(info)
#                    valid = False
#                    break
#            if valid:
#                md_ids = [int(md_id) for md_id in md_ids]
#                self.molecule_design_lists.append(md_ids)
#            row_index += 1
#
#        if len(self.molecule_design_lists) < 1:
#            msg = 'There are no molecule designs in the column!'
#            self.add_error(msg)
#
#        if len(invalid_numbers) > 0:
#            msg = 'Some cells contain invalid molecule design IDs: %s.' \
#                  % (', '.join(invalid_numbers))
#            self.add_error(msg)
