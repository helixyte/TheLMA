"""
:Date: 2011 May
:Author: AAB, berger at cenix-bioscience dot com

.. currentmodule:: thelma.automation.tools.metadata.generation

This is the experiment design Excel file parser for Thelma. It is a component
of the :class:`ExperimentMetadataGenerator`.


Experiments and Plates
......................
The experiment design defines the parameters for the experiments
of an subproject. They may include one or several experiments. At this,
one experiment corresponds to one source rack.

Layouts and Tags
................
Each plate (rack) has a layout. The layout defines which experimental
parameters are applied to which well. Parameters are stated as machine tags
(triple tags).

.. currentmodule:: thelma.models.tagging

A machine tag (see :class:`Tag`) is composed of three parts:

  * **domain**
        a domain or namespace (HERE: *experimentdata*)
  * **predicate** (former *factor*)
        an experimental parameter (e.g. cell density)
  * **value** (former *level*)
        The actual value of a parameter
        (e.g. a certain cell density).
        There are several values for each predicate.

Predicates and values can be defined freely by the user. Thus, they
do not need to be present in the DB before.

:Note: Predicates of ISO layout parameter tags must comply with the referring
    naming conditions. However, ISO layouts can also be specified separately.

.. currentmodule:: thelma.models.experiment

The complete set of value/position-pairs for all tags of one rack defines
an :class:`ExperimentDesignRack`.

Parsing Notes
.............

Experiment design data is specified on up to four sheets within an experimental
metadata Excel file (see :mod:`thelma.automation.tools.metadata.generation`).
Detailed information about the composition of the sheets are given in the
`Composition of Source Files`_ section.

The parsing will proceed as follows:

 1. get sheet
 2. parse the tag definitions (including values and codes)
 3. find layout definitions of the sheet and determine the basic
    information (position on the sheet, associated racks, plate shape)
 4. parse the layouts using codes and value definitions
 5. repeat steps for each remaining sheet

.. currentmodule:: thelma.automation.parsers.base

The parsed data is stored in :class:`ParsingContainer` objects. It will be
employed by the parser's handler later on to generate an experiment design
object (:class:`thelma.models.experiment.ExperimentDesign`).

Composition of Source Files
...........................

* Valid sheets must be called \'*SEEDING*\', \'*TRANSFECTION*\',
  \'*TREATMENT*\' or \'*ASSAY*\' (all case-insensitive).
* Each parsed sheet contains factor (tag) definitions and graphical rack
  layouts.
* Tags (factors) are marked with the string *\'FACTOR*\' or *\'TAG*\'
  (both case insensitive) in the first column of the sheet.
* The string \'*END*\' (case insensitive) marks the end of the section
  where tag or layout information should be extracted.
* A rack layout is associated with a tag (factor) if it is placed between
  the row containing the tag (factor) marker and either the next tag marker
  or the end marker.
* The first column to the right of the tag (factor) marker contains
  the marker string \'*CODE*\' (case-insensitive).
* The first column to the right of the \'*CODE*\' marker *must* contain
  a label, which is taken as the tag predicate.
* If additional columns to the right of the tag label contain
  a label, they are interpreted as additional tags (\'associated tags\' or
  \'related tags\'). The codes for the values of these tags are the
  same like the codes for the 'main' tag in the first column.
  Values of related tags can thereby have more than one code.
* Below the tag marker is a cell with the marker string \'*LEVELS*\'
  (case insensitive).
* Each non-empty cell below the tag (factor) label cell declares a tag
  value. Tag values must be unique. The first empty cell indicates
  the end of the tag value declarations.
* In case one or several related tag labels were declared next to the
  main tag label, tag values are read from the corresponding cells in each
  tag value (level) row. Values of associated tags need not be unique and
  can also be empty (in which case the resulting tag value is *None*).
* Rack layouts are detected by their top left (origin) cell. The origin
  cell itself is empty and has a cell containing a *1* to the right
  and a cell containing an *A* below.
* Cells in the column below the origin cell must contain consecutive
  labels. The first empty cell indicates the end of the row labels.
* Cells in the row right to the origin cell contain consecutive
  numbers. The first empty cell indicates the end of the column labels.
* The shape of the layout (i.e., the number of rows and columns)
  must match one of the allowed standard shapes_
* In the cell above the origin cell of the rack layout is the racks
  specifier which declares the plates to apply this layout to.
* The racks specifier must match the following EBNF notation: ::

    racks_spec = ("Plates "  | "Plate ") , token , {"," token};
    token = {rack_barcode} | {rack_num} | ( {rack_num} , "-" , {rack_num} );
    rack_barcode = 8*{digit}
    rack_num = nonzero_digit , {digit};
    nonzero_digit = "1"|"2"|"3"|"4"|"5"|"6"|"7"|"8"|"9";
    digit = "0"|digit;


:note: Missing sheets will be ignored.
:note: xlsx files are not supported.

Implementation
..............
"""

from thelma.automation.parsers.base import ExcelMoleculeDesignPoolLayoutParser
from thelma.automation.parsers.base \
    import ExcelMoleculeDesignPoolLayoutParsingContainer
from thelma.automation.parsers.base import RackParsingContainer
from thelma.automation.tools.utils.base import get_trimmed_string

__docformat__ = "reStructuredText en"

__all__ = ['ExperimentDesignParser',
           '_ExperimentDesignSheetParsingContainer']

class ExperimentDesignParser(ExcelMoleculeDesignPoolLayoutParser):
    """
    This is the actual parser class for Experimental Meta Data Excel files.
    """

    #: name of the parser (requested by logs)
    NAME = 'Experiment Design Parser'

    """ .. _shapes:""" #pylint: disable=W0105
    #: list of valid rack dimensions
    RACK_SHAPES = [(8, 12), (16, 24), (32, 48)]

    def __init__(self, stream, log):
        """
        :param stream: open Excel file to be parsed

        :param log: The ThelmaLog you want to write in.
        :type log: :class:`thelma.ThelmaLog`
        """
        ExcelMoleculeDesignPoolLayoutParser.__init__(self, stream, log)

        #: The names of the sheets to be parsed (set by the handler).
        self.sheet_names = None

        #: A list of all tag predicates (factors) found in the file (to
        #: detect duplicates).
        self.tag_predicates = set()

    def parse(self):
        """
        Parses the experiment design tabs of the specified file.
        """
        self.reset()
        self.log.add_info('Start parsing ...')
        if not self.has_errors():
            wb = self.open_workbook()
            sheets = self.__get_sheets(wb)
        if not self.has_errors():
            for sheet_name in sheets:
                self.__parse_sheet(wb, sheet_name)
                self.__reset_sheet_values()
                if self.has_errors(): break
        if not self.has_errors(): self._check_and_replace_floatings()

    def has_shape(self):
        """
        Returns whether the shape of the experiment design has
        been defined already.

        :rtype: :class:`boolean`
        """
        if self.shape is None: return False
        else:
            return True

    def __get_sheets(self, wb):
        """
        Gets the sheet names to parse
        """

        self.add_info('Validate sheets to be parsed ...')
        sheet_names = []
        for sheet_name in self.sheet_names:
            if self.__check_sheet_name(sheet_name, wb, False) == True:
                sheet_names.append(sheet_name)

        return sheet_names

    def __check_sheet_name(self, sheet_name, wb, record=True):
        """
        Checks if there is a sheet with this name.
        """
        valid_sheet = False
        sheet = self.get_sheet_by_name(wb, sheet_name, raise_error=record)
        if not sheet is None: valid_sheet = True
        return valid_sheet

    def __parse_sheet(self, workbook, sheet_name):
        """
        Parses one sheet.
        """
        self.add_info('Start parsing of "%s" sheet ...' % (sheet_name))
        self.sheet = self.get_sheet_by_name(workbook, sheet_name)
        sheet_container = _ExperimentDesignSheetParsingContainer(self,
                                                                self.sheet)
        sheet_container.parse_tag_definitions()
        if not self.has_errors() and not sheet_container.is_empty():
            sheet_container.find_layouts()

    def __reset_sheet_values(self):
        self.sheet = None


class _ExperimentDesignSheetParsingContainer(
                            ExcelMoleculeDesignPoolLayoutParsingContainer):
    """
    ParsingContainer subclass performing the single steps of the parsing
    and storing the intermediate information of an Excel sheet.
    The data is passed back to the parser as soon it is in a hierarchy
    that can be used for the creation of a experiment design object.
    """
    _PARSER_CLS = ExperimentDesignParser

    def is_empty(self):
        """
        If there are no tag definitions in the container, it is
        considered as empty.
        """
        if len(self._tags) < 1:
            return True
        else:
            return False

    def parse_tag_definitions(self):
        """
        Parses tags, values and codes (including associated tags) of a
        sheet and stores them as TagParsingContainer objects in the
        tags list of the SheetParsingContainer.
        """
        self._create_debug_info('Parse tag definitions ...')

        while not self._end_reached:
            self._parse_tag_definitions()
            if self._parser.has_errors(): break
            self._step_to_next_row()

    def _init_tag_definition_container(self, predicate):
        """
        The tags must also be unique in the scope of the other sheets.
        """
        container = ExcelMoleculeDesignPoolLayoutParsingContainer.\
                        _init_tag_definition_container(self, predicate)
        if container is None: return None
        if container.predicate in self._parser.tag_predicates:
            msg = 'Duplicate factor name "%s"!' % (predicate)
            self._create_error(msg)
            return None

        self._parser.tag_predicates.add(predicate)
        return container

    def _parse_layout_specifiers(self, layout_specifier, layout_container):
        """
        Retrieves the rack labels for the current layout definition.
        """
        if not self.__is_rack_specifer(layout_specifier):
            return None
        rack_labels = self.__get_rack_labels(layout_specifier)
        if rack_labels is None: return None
        rack_containers = []
        for rack_label in rack_labels:
            if self._parser.rack_map.has_key(rack_label):
                rack_container = self._parser.rack_map[rack_label]
            else:
                rack_container = RackParsingContainer(parser=self._parser,
                                                      rack_label=rack_label)
            rack_containers.append(rack_container)
        return rack_containers

    def __is_rack_specifer(self, rack_specifier):
        """
        Makes sure the rack labels for the current layout definition
        are specified in the correct form.
        """
        if not (rack_specifier.upper().startswith('PLATES ') or \
                rack_specifier.upper().startswith('PLATE ')):
            msg = 'Invalid rack specifier: %s.' % (rack_specifier)
            self._create_error(msg)
            return False
        return True

    def __get_rack_labels(self, rack_specifier):
        """
        Gets the rack labels for a verified rack specifier.
        """
        rack_labels = []
        tokens = rack_specifier[rack_specifier.find(' ') + 1:].split(',')
        for token in tokens:
            token = token.strip()
            if len(token) < 1: continue
            if '-' in token:
                start, stop = token.split('-')
                try:
                    # only number-specified racks might be specified in ranges
                    rack_nums = range(int(start), int(stop) + 1)
                    if len(rack_nums) < 1:
                        msg = 'Unable to parse rack range "%s".' % (token)
                        self._create_error(msg)
                    else:
                        for rack_num in rack_nums:
                            rack_labels.append(get_trimmed_string(rack_num))
                except ValueError:
                    msg = 'Invalid range "%s" in racks ' \
                          'specifier "%s".' % (token, rack_specifier)
                    self._create_error(msg)
                    return None
            else:
                rack_labels.append(get_trimmed_string(token))
                # without out a range it can be a rack_numer (int) or a barcode

        if len(rack_labels) < 1: return None
        return rack_labels
