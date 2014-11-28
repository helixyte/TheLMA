"""
Parses the excel file containing molecule design IDs for a pool stock sample
creation ISO request.

Composition of Source Files
...........................

 * The excel sheet containing the molecule designs in called
   \'Molecule Designs\'.
 * The column containing the molecule designs is called \'Molecule Design IDs\'.
 * The column containing pool IDs for the final pools s is called
   \'Molecule Design Pool IDs\' or \'Pool IDs\'.
 * At least one of the 2 columns must be present.
 * The column headers are expected in the first row.
 * The molecule designs in the column are separated by a comma.
 * The pool column must only contain 1 ID per row.
 * All IDs must be integers.
 * Parsing is interrupted as soon there is an empty cell in the present columns.

AAB
"""
from thelma.tools.parsers.base import ExcelFileParser
from thelma.tools.parsers.base import ExcelSheetParsingContainer
from thelma.tools.utils.base import is_valid_number


__docformat__ = "reStructuredText en"
__all__ = ['PoolCreationSetParser',
           '_PoolCreationSetParsingContainer']


class PoolCreationSetParser(ExcelFileParser):
    """
    Parses the excel sheet that provides the molecule designs for the
    pools of a pool creation ISO request.
    """
    #: name of the parser (requested by logs).
    NAME = 'Stock Sample Pool Order Parser'
    #: name of the sheet containing the molecule design list.
    SHEET_NAME = 'Molecule Designs'
    #: Valid names for the column containing the pools IDs for the final
    #: molecule design pools.
    POOL_COLUMN_NAMES = ['Molecule Design Pool IDs', 'Pool IDs']
    #: The name of the column containing the single molecule design IDs.
    MOLECULE_DESIGN_COLUMN_NAME = 'Molecule Design IDs'
    #: Separates the molecule designs in one cell.
    DELIMITER = ','

    def __init__(self, stream, parent=None):
        ExcelFileParser.__init__(self, stream, parent=parent)
        #: The molecule design pool IDs mapped onto row index.
        self.pool_ids = None
        #: The molecule design lists found (each record is a list
        #: molecule design IDs) mapped onto row index.
        self.molecule_design_lists = None

    def reset(self):
        ExcelFileParser.reset(self)
        self.pool_ids = dict()
        self.molecule_design_lists = dict()

    def run(self):
        self.reset()
        self.add_info('Start parsing ...')
        wb = self.open_workbook()
        self.sheet = self.get_sheet_by_name(wb, self.SHEET_NAME,
                                            raise_error=True)
        if not self.has_errors():
            parsing_container = _PoolCreationSetParsingContainer(self,
                                                                 self.sheet)
            parsing_container.determine_column_indices()
        if not self.has_errors():
            parsing_container.parse_columns()
        if not self.has_errors():
            self.add_info('Parsing completed.')


class _PoolCreationSetParsingContainer(ExcelSheetParsingContainer):
    """
    Intermediate storage of the content of a pool stock sample creation
    file.
    """
    _PARSER_CLS = PoolCreationSetParser

    def __init__(self, parser, sheet):
        """
        Constructor.

        :param parser: the parser this container belongs to
        :type parser: :class:`ExcelFileParser`
        :param sheet: the excel sheet this container deals with
        """
        ExcelSheetParsingContainer.__init__(self, parser, sheet)
        #: The index of the column containing the final pool IDs.
        self.__pool_column_index = None
        #: The index of the column containing the molecule design IDs.
        self.__single_md_column_index = None

    def determine_column_indices(self):
        """
        The columns are found by name.
        """
        self._create_debug_info('Find column index ...')
        row_index = 0
        md_column_name = self._parser.MOLECULE_DESIGN_COLUMN_NAME.upper()
        pool_column_names = [name.upper() for name in \
                             self._parser.POOL_COLUMN_NAMES]
        for col_index in range(self._col_number):
            if (self.__single_md_column_index is not None and \
                                self.__pool_column_index is not None): break
            cell_value = self._get_cell_value(row_index, col_index)
            cell_value = str(cell_value).replace('_', ' ')
            cell_value = cell_value.upper()
            if cell_value == md_column_name:
                self.__single_md_column_index = col_index
                continue
            elif cell_value in pool_column_names:
                self.__pool_column_index = col_index
                continue
        if self.__single_md_column_index is None and \
                                            self.__pool_column_index is None:
            msg = 'Unable to find a molecule design data column. A valid ' \
                  'column must be called "%s" for single molecule design ID ' \
                  'lists or %s for final pool IDs (all case-insensitive).' \
                  % (self._parser.MOLECULE_DESIGN_COLUMN_NAME,
                     ' or '.join(['"%s"' % (name) for name in \
                                  self._parser.POOL_COLUMN_NAMES]))
            self._create_error(msg)

    def parse_columns(self):
        """
        Searches the found columns for IDs.
        """
        self._create_debug_info('Parse column ...')
        invalid_mds = []
        invalid_pools = []
        self._step_to_next_row()
        while not self._end_reached:
            # Get cell values.
            md_value = None
            if self.__single_md_column_index is not None:
                md_value = self._get_cell_value(self._current_row,
                                                self.__single_md_column_index)
            pool_value = None
            if self.__pool_column_index is not None:
                pool_value = self._get_cell_value(self._current_row,
                                                 self.__pool_column_index)
            if md_value is None and pool_value is None:
                self._end_reached = True
                break
            # Check pool IDs.
            if not pool_value is None and not is_valid_number(pool_value,
                                                              is_integer=True):
                info = 'row %i (%s)' % (self._current_row + 1, pool_value)
                invalid_pools.append(info)
            elif not pool_value is None:
                self._parser.pool_ids[self._current_row] = pool_value
            # Check single molecule design IDs.
            if md_value is not None:
                md_ids = str(md_value).split(self._parser.DELIMITER)
                valid = True
                for md_id in md_ids:
                    if not is_valid_number(md_id, is_integer=True):
                        info = 'row %i (%s)' % ((self._current_row + 1),
                                                '-'.join(md_ids))
                        invalid_mds.append(info)
                        valid = False
                if valid:
                    md_ids = [int(md_id) for md_id in md_ids]
                    self._parser.molecule_design_lists[self._current_row] = \
                                                                        md_ids
            self._step_to_next_row()
        if len(self._parser.molecule_design_lists) < 1 and \
                                            len(self._parser.pool_ids) < 1:
            msg = 'There is no design data in the columns!'
            self._create_error(msg)
        if len(invalid_mds) > 0:
            msg = 'Some rows contain invalid molecule design IDs: %s.' \
                  % (', '.join(invalid_mds))
            self._create_error(msg)
        if len(invalid_pools) > 0:
            msg = 'Some rows contain invalid pool IDs: %s.' \
                  % (', '.join(invalid_pools))
            self._create_error(msg)
