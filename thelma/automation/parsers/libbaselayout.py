"""
Parses the excel sheet that provides the base layout for a library.

Composition of Source Files
...........................

 * The excel sheet containing the layout is called \'Base Layout\'.
 * The rack layout starts in cell B2, with the column headers being presented
   in row 1 and the row header being presented in column A.
 * Empty cells within the layout are considered as negative (= they will not
   contain library samples) and wells with any character inside will be
   regarded as positive (= they will contain library samples).

AAB
"""
from thelma.automation.parsers.base import ExcelFileParser
from thelma.automation.parsers.base import RackPositionParsingContainer
from thelma.automation.parsers.base import RackShapeParsingContainer
from thelma.models.utils import label_from_number

__docformat__ = "reStructuredText en"

__all__ = ['LibraryBaseLayoutParser',
           ]


class LibraryBaseLayoutParser(ExcelFileParser):
    """
    Parses a excel sheet that provides the base layout for a library
    creation ISO request.
    """

    NAME = 'Library Base Layout Parser'

    #: The name of the sheet containing the layout
    SHEET_NAME = 'Base Layout'

    #: list of valid rack dimensions
    RACK_SHAPES = [(8, 12), (16, 24), (32, 48)]

    #: The cell in the sheet that holds the A1 position of the layout.
    TOP_LEFT_POSITION = (0, 0)

    def __init__(self, stream, log):
        """
        :param stream: open Excel file to be parsed

        :param log: The log to write into.
        :type log: :class:`thelma.parsers.errors.ThelmaLog`
        """
        ExcelFileParser.__init__(self, stream=stream, log=log)

        #: The sheet to be parsed.
        self.sheet = None

        #: The rack shape of the layout as rack shape container.
        self.shape = None

        #: Lists the wells that contain characters (positive wells)
        #: as :class:`RackPositionParsingContainers`.
        self.contained_wells = None

    def reset(self):
        ExcelFileParser.reset(self)
        self.shape = None
        self.contained_wells = []

    def parse(self):
        self.reset()
        self.add_info('Start parsing ...')

        wb = self.open_workbook()
        self.sheet = self.get_sheet_by_name(wb, self.SHEET_NAME)

        if not self.has_errors(): self.__determine_layout_dimension()
        if not self.has_errors(): self.__find_sample_wells()
        if not self.has_errors():
            self.add_info('Parsing completed.')

    def __determine_layout_dimension(self):
        """
        Makes sure the layout is in the right position and determines
        the layout dimension.
        """
        self.add_debug('Determine layout dimension ...')

        first_col_value = self.get_cell_value(self.sheet,
                    self.TOP_LEFT_POSITION[0] + 1, self.TOP_LEFT_POSITION[1])
        is_layout = first_col_value == 'A'

        if not is_layout:
            msg = 'Error when trying to locate the layout. Please make sure ' \
                  'the columns header start in row 2 in column A.'
            self.add_error(msg)
            return None

        row_number = self.get_sheet_row_number(self.sheet)
        col_number = self.get_sheet_column_number(self.sheet)
        rack_row, rack_column = 0, 0
        start_row = self.TOP_LEFT_POSITION[0]
        start_column = self.TOP_LEFT_POSITION[1]
        # get number of rows, row labels are alphanumeric
        while True:
            row_cell_value = self.get_cell_value(self.sheet,
                                    (start_row + rack_row + 1), start_column)
            if row_cell_value != label_from_number(rack_row + 1): break
            rack_row += 1
            if (start_row + rack_row + 1) >= row_number: break
        # get number of columns, column labels are numbers
        while True:
            column_cell_value = self.get_cell_value(self.sheet, start_row,
                                 (start_column + rack_column + 1))
            if column_cell_value != (rack_column + 1): break
            rack_column += 1
            if (start_column + rack_column + 1) >= col_number: break

        if not (rack_row, rack_column) in self.RACK_SHAPES:
            msg = 'Invalid layout block shape (%ix%i).' % (rack_row,
                                                           rack_column)
            self.add_error(msg)
        else:
            self.shape = RackShapeParsingContainer(self, rack_row, rack_column)

    def __find_sample_wells(self):
        """
        Each well containing at least 1 character is regarded as positive
        and added to the list.
        """
        self.add_debug('Search wells ...')

        for r in range(self.shape.row_number):
            table_row = self.TOP_LEFT_POSITION[0] + 1 + r
            for c in range(self.shape.column_number):
                table_col = self.TOP_LEFT_POSITION[1] + 1 + c
                cell_value = self.get_cell_value(self.sheet, table_row,
                                                 table_col)
                if cell_value is None or len(cell_value) < 1: continue
                pos_container = RackPositionParsingContainer(self, r, c)
                self.contained_wells.append(pos_container)
