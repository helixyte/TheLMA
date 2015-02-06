"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

General
.......

.. currentmodule:: thelma.entities.liquidtransfer

With this parser one can derive the data for a sample transfer worklist
series from an XLS file (see :class:`WorklistSeries`).

Worklists
.........

You can schedule several steps in a row by defining several steps.
For each step you have to provide a source plate or reservoir and
a target plate. The outcome will be converted into :class:`PlannedWorklists`
or :class:`ExecutedWorklists` by the handler.

All plates and reservoirs must have an ID (to be listed in the
`Racks and Reservoirs` section of the document. This section contains
an internal identifier for each rack or reservoir and a specification.
The specification can either be a barcode (for entities already existing
in the database or a reservoir specs name (for future or temporary items,
see :class:`ReservoirSpecs`)).

Layouts and Tags
................

The source and target positions for each transfer step are painted into
a 2D layout. There must be a transfer volume for each transfer which can
either be a common volume for the complete step or different for each
transfer. Common volumes are specified with the step. If you specified
different volume, there volume has to be a volume for each painted transfer.

Each transfer must have exactly one source well in the source layout of
the step. There can be different target wells, though.

The same layout can be shared by different racks or reservoirs. In this
the handler will create transfers for all rack permutations.


Parsing Notes
.............

  1. Parse label (used for planned worklist labels).
  2. Parse racks and reservoirs specifications
  3. For each layouts: parse factor definition, parse layouts, read codes


Composition of Source File
..........................

  * The excel sheet containing the layouts must be called \'*SAMPLE TRANSFER*\'.
  * The sheet contains a \'Label\' section at the top. This section contains
    a label (prefix) used to generate the planned worklist labels.
  * The \'Label\' section contains a \'Label\' marker in column A
    (case insensitive) and the actual value adjacent in column B.
  * Below the \'LABEL\' section there is the \'Racks and Reservoirs\' section.
  * The \'Racks and Reservoirs\' section is marked by the string
    \'RACKS AND RESERVOIRS\' (case insensitive) in column A. Below the marker
    there is table with 3 columns (headers \'ID\', \'Barcode\', \'Specs\').
  * Each racks or reservoir must have an ID. Furthermore, each record must
    have a barcode or reservoir specs name (\'Specs\' column). A record can
    have both.
  * Below the \'Racks and Reservoirs\' section the user can specify the
    different step. Each step will be converted into a PlannedWorklist by
    the handler.
  * A new step is marked by the keyword \'STEP\' (case insensitive) plus a
    digit.
  * Next to the step definition one can specify the transfer volume for
    the transfer in this step. This is only possible if there is the same
    transfer volume for all transfers. The unit for volume is ul.
  * Below the marker there is a code definition table. It is marked by the
    keyword \'*FACTOR*\' in column A . One cell below the factor marker there
    must be the marker \'*LEVELS*\' (this originates from the experiment
    design and ISO request parsers).
  * If the first column to the right of the tag (factor) marker contains
    the marker string \'*CODE*\' (case-insensitive), the values in this
    column are interpreted as tag value codes. Otherwise, the colour of
    each tag value cell is used to determine the value code.
  * The first column to the right of the \'FACTOR\' (or \'CODE\') marker
    contains the tag predicate \'TRANSFER VOLUME\' which allows to define
    distinct transfer volume for each transfer marked here.
  * All other tag definition are ignored and left to the user for notes and
    documentation.
  * Each non-empty cell below the \'Code\' or \'Transfer Volume\' markers
    declares a tag value. Tag values must be unique. The first empty cell
    indicates the end of the tag value declarations.
  * Rack layouts are detected by their top left (origin) cell. The origin
    cell itself is empty and has a cell containing a *1* to the right
    and a cell containing an *A* below.
  * Cells in the column below the origin cell must contain consecutive
    labels. The first empty cell indicates the end of the row labels.
  * Cells in the row right to the origin cell contain consecutive
    numbers. The first empty cell indicates the end of the column labels.
  * The shape of the layout (i.e., the number of rows and columns)
    must match one of the allowed standard shapes.
  * In the cell above the origin cell of the rack layout is the racks
    specifier which declares the plates to apply this layout to.
  * The racks specifier may mark a plate or a reservoir.
  * The racks specifier starts with the keyword \'*SOURCE*\' or \'*TARGET*\'
    (to mark the function), followed the keyword \'*PLATE*\', \'*PLATES*\'
    or \'*RESERVOIR*\' and the the internal identifier of the rack or
    reservoir as listed in the the \'Racks and Reservoirs\' section.
  * All keywords are case-insensitive.

:note: xlsx files are not supported.

Implementation
..............
"""
from thelma.tools.parsers.base import ExcelLayoutFileParser
from thelma.tools.parsers.base import ExcelLayoutSheetParsingContainer
from thelma.tools.parsers.base import ExcelParsingContainer
from thelma.tools.parsers.base import RackParsingContainer
from thelma.tools.parsers.base import TagDefinitionParsingContainer
from thelma.tools.utils.base import add_list_map_element
from thelma.tools.utils.base import is_valid_number
from thelma.tools.utils.layouts import ParameterAliasValidator

__docformat__ = "reStructuredText en"
__all__ = ['GenericSampleTransferPlanParser',
           'TransferParsingContainer']


class GenericSampleTransferPlanParser(ExcelLayoutFileParser):
    """
    This is the actual parser for generic sample transfer worklist series
    parsing.
    """
    NAME = 'Generic Sample Transfer Plan Parser'

    HAS_COMMON_LAYOUT_DIMENSION = False

    #: The name of the sheet to be parsed.
    SHEET_NAME = 'Sample Transfer'

    #: Marks the label section (prefix for worklists labels).
    WORKLIST_PREFIX_MARKER = 'label'

    #: Marks the racks and reservoir section.
    RACK_SECTION_MARKER = 'racks_and_reservoirs'
    #: The column name for the rack identifiers within the racks section.
    RACK_IDENTIFIER_COLUMN_NAME = 'id'
    #: The column name for the rack barcode within the racks section.
    RACK_BARCODE_COLUMN_NAME = 'barcode'
    #: The column name for the rack specs within the racks section.
    RACK_SPECS_COLUMN_NAME = 'specs'

    #: Marks a new step definition.
    STEP_MARKER = 'step'
    #: Marks a transfer volume tag definition.
    TRANSFER_VOLUME_MARKER = 'transfer volume'
    #: Marks a diluent tag definition (dilutions only).
    DILUENT_MARKER = 'diluent'

    #: The base tag name for the transfer tags (that define the source
    #: and target positions). The placeholder stands for the step number.
    TRANSFER_TAG_BASE_NAME = 'transfer'

    #: The index of the role in the layout specifier (split by white space).
    SPECIFIER_ROLE_INDEX = 0
    #: The index of the type in the layout specifier (split by white space).
    SPECIFIER_TYPE_INDEX = 1

    #: Part of a rack specifier. Marks a plate or rack.
    RACK_MARKERS = ['plate', 'rack']
    #: Part of a rack specifier. Marks a reservoir.
    RESERVOIR_MARKER = 'reservoir'

    def __init__(self, stream, parent=None):

        ExcelLayoutFileParser.__init__(self, stream, parent=parent)
        #: Used to recognise transfer volume tag definitions.
        self.transfer_volume_validator = ParameterAliasValidator(
                                         self.TRANSFER_VOLUME_MARKER)
        #: User to recognise diluent tag definitions.
        self.diluent_validator = ParameterAliasValidator(self.DILUENT_MARKER)
        #: Is set by the handler.
        self.source_role_marker = None
        #: Is set by the handler.
        self.target_role_marker = None
        #: Is used to generate the label of the resulting worklists.
        self.worklist_prefix = None
        #: Maps the racks and reservoirs found onto their identifiers
        #: (as :class:`_TransferRackParsingContainer` objects).
        self.rack_containers = None
        #: Maps steps container (:class:`_TransferStepParsingContainer`)
        #: onto step numbers.
        self.step_containers = None

    def reset(self):
        ExcelLayoutFileParser.reset(self)
        self.worklist_prefix = None
        self.rack_containers = dict()
        self.step_containers = dict()

    def run(self):
        self.reset()
        self.add_info('Start parsing ...')
        wb = self.open_workbook()
        self.sheet = self.get_sheet_by_name(wb, self.SHEET_NAME,
                                            raise_error=True)
        if not self.has_errors():
            parsing_container = _GenericSampleTransferParsingContainer(self)
        if not self.has_errors():
            parsing_container.find_worklist_prefix()
        if not self.has_errors():
            parsing_container.parse_rack_definitions()
        if not self.has_errors():
            parsing_container.parse_steps()
        if not self.has_errors():
            parsing_container.find_layouts()
        if not self.has_errors():
            parsing_container.check_transfers()
        if not self.has_errors():
            self.add_info('Parsing completed.')


class _GenericSampleTransferParsingContainer(ExcelLayoutSheetParsingContainer):
    """
    This parsing container parses the data sheet for the
    :class:`GenericSampleTransferParser`.
    """

    def __init__(self, parser):
        ExcelLayoutSheetParsingContainer.__init__(self, parser=parser,
                                                  sheet=parser.sheet)

        #: Contains the current step parsing container.
        self.__current_step = None
        #: The transfer volume tag definition for the current step.
        self.__current_vol_predicate = None
        #: The diluent tag definition for the current step.
        self.__current_dil_predicate = None

        #: Maps the step container onto starting rows (to allow for
        #: layout association).
        self.__steps_by_row = dict()

        #: Stores the step container for each layout container.
        self.__steps_by_layout = dict()

    def find_worklist_prefix(self):
        """
        Parses the label prefix used to generate the labels of the
        resulting worklists.
        """
        self._create_debug_info('Parse worklist prefix ...')

        wl_prefix = None

        while not self._end_reached:
            prefix_marker = self._get_cell_value(self._current_row, 0)
            prefix_marker = self._convert_keyword(prefix_marker)
            if prefix_marker == self._parser.WORKLIST_PREFIX_MARKER:
                wl_prefix = self._get_cell_value(self._current_row, 1)
                break
            self._step_to_next_row()

        if wl_prefix is None:
            msg = 'Unable to find label section! The section is marked with ' \
                  'the keyword "%s" in column A!' \
                   % (self._parser.WORKLIST_PREFIX_MARKER)
            self._create_error(msg)
        elif len(wl_prefix) < 2:
            msg = 'The worklist prefix must be at least 2 characters long!'
            self._create_error(msg, self._get_cell_name(self._current_row, 0))
        else:
            self._parser.worklist_prefix = wl_prefix

    def parse_rack_definitions(self):
        """
        Parses the Rack and Reservoir section.
        """
        self._create_debug_info('Parse racks and reservoirs ...')

        indices = None
        if self.__find_rack_section():
            indices = self.__get_rack_definition_indices()

        self._step_to_next_row()
        while indices is not None and not self._end_reached:
            rack_id = self._get_cell_value(self._current_row,
                            indices[self._parser.RACK_IDENTIFIER_COLUMN_NAME])
            if rack_id is None: break
            barcode = self._get_cell_value(self._current_row,
                            indices[self._parser.RACK_BARCODE_COLUMN_NAME])
            if isinstance(barcode, int): barcode = '%08i' % (barcode)
            specs = self._get_cell_value(self._current_row,
                            indices[self._parser.RACK_SPECS_COLUMN_NAME])
            rack_container = _TransferRackParsingContainer(parser=self._parser,
                    identifier=rack_id, barcode=barcode, specs=specs,
                    row_index=self._current_row)
            if self._parser.rack_containers.has_key(rack_id):
                msg = 'Duplicate rack or reservoir identifier "%s"!' % (rack_id)
                self._create_error(msg)
                break
            else:
                self._parser.rack_containers[rack_id] = rack_container
            self._step_to_next_row()

        if not self._parser.has_errors() and \
                                    len(self._parser.rack_containers) < 1:
            msg = 'There are no racks and reservoirs defined!'
            self._create_error(msg)

    def __find_rack_section(self):
        """
        Finds the beginning of the racks and reservoir section. The section
        is marked by a keyword.
        """
        marker_found = False
        while not self._end_reached and not marker_found:
            self._step_to_next_row()
            rack_marker = self._get_cell_value(self._current_row, 0)
            rack_marker = self._convert_keyword(rack_marker)
            if rack_marker == self._parser.RACK_SECTION_MARKER:
                marker_found = True

        if not marker_found:
            msg = 'Unable to find rack and reservoir section. The section ' \
                  'is marked by the keyword "%s" in column A!' \
                  % (self._parser.RACK_SECTION_MARKER)
            self._create_error(msg)

        return marker_found

    def __get_rack_definition_indices(self):
        """
        The columns are recognised by name.
        """
        self._create_debug_info('Parse racks and reservoirs ...')

        self._step_to_next_row()
        if self._end_reached: return None

        indices = {self._parser.RACK_IDENTIFIER_COLUMN_NAME : None,
                   self._parser.RACK_BARCODE_COLUMN_NAME : None,
                   self._parser.RACK_SPECS_COLUMN_NAME : None}

        for col_index in range(self._col_number):
            cell_value = self._get_cell_value(self._current_row, col_index)
            cell_value = self._convert_keyword(cell_value)
            if indices.has_key(cell_value):
                if indices[cell_value] is not None:
                    msg = 'Duplicate %s definition in the racks and ' \
                          'reservoir section!' % (cell_value)
                    cell_name = self._get_cell_name(self._current_row,
                                                    col_index)
                    self._create_error(msg, cell_name)
                    return None
                indices[cell_value] = col_index
                if not None in indices.values(): break

        missing_columns = []
        for col_name, col_index in indices.iteritems():
            if col_index is None: missing_columns.append(col_name)
        if len(missing_columns) > 0:
            msg = 'Unable to find the following definitions in the racks ' \
                  'and reservoir section: %s.' \
                   % (', '.join(sorted(missing_columns)))
            self._create_error(msg)
            return None

        return indices

    def parse_steps(self):
        """
        Looks for step markers and parses their content.
        """
        self._create_debug_info('Parse steps ...')

        while not self._end_reached:
            step_marker = self._get_cell_value(self._current_row, 0)
            step_marker = self._convert_keyword(step_marker)
            if step_marker.startswith(self._parser.STEP_MARKER):
                self.__current_step = _TransferStepParsingContainer(
                          step_marker=step_marker, parser=self._parser,
                          starting_row=self._current_row)
                self.__current_vol_predicate = None
                self.__current_dil_predicate = None

                if self.__current_step.number is None: break
                if not self.__parse_and_check_step(): break

            self._step_to_next_row()

        if len(self._parser.step_containers) < 1:
            msg = 'Unable to find a step definition in this file!'
            self._create_error(msg)

    def __parse_and_check_step(self):
        """
        Parses volume tag definition, default volume and transfer codes.
        Transfer codes are parsed separately even is there is already a
        volume tag definition because in some special case some codes
        might get lost otherwise.
        """
        # store (there is no need to continue if there is a duplicate number)
        step_number = self.__current_step.number
        if self._parser.step_containers.has_key(step_number):
            msg = 'Duplicate step number %i!' % (step_number)
            self._create_error(msg)
            return False
        else:
            self._parser.step_containers[step_number] = self.__current_step
            self.__steps_by_row[self.__current_step.starting_row] = \
                                                        self.__current_step

        # Is there a valid tag definition section? If yes, parse it.
        self._step_to_next_row()
        current_tags = self._parse_tag_definitions()
        if self._parser.has_errors():
            return False
        elif current_tags is None:
            msg = 'There should be a factor definition in row %i (step %i)! ' \
                  'If you do not need this step, remove it completely, ' \
                  'please.' % ((self._current_row + 1),
                               self.__current_step.number)
            self._create_error(msg)
            return False

        # get volume values and parse transfer codes
        self.__set_step_volumes_and_diluents(current_tags)
        self.__init_step_transfer_codes()
        if self._parser.has_errors() is None: return False

        return True

    def _get_tag_label(self, column_index):
        """
        The generic sample transfer parser only regards transfer volume
        tags.
        """
        tag_label = ExcelLayoutSheetParsingContainer._get_tag_label(self,
                                                            column_index)
        if tag_label is None: return None
        adj_tag_label = '%s_%i' % (tag_label, self.__current_step.number)

        if self._parser.transfer_volume_validator.has_alias(tag_label):
            self.__current_vol_predicate = adj_tag_label
            return adj_tag_label
        elif self._parser.diluent_validator.has_alias(tag_label):
            self.__current_dil_predicate = adj_tag_label
            return adj_tag_label
        else:
            return None

    def _has_valid_tag_values(self, values):
        """
        This parser allows for codes without value.
        """
        return True

    def __set_step_volumes_and_diluents(self, current_tags):
        """
        Parses the volume data (default values and potential tag definition)
        and sets the potential diluent tag definition for a step.
        """
        for tag_definition in current_tags.values():
            if tag_definition.predicate == self.__current_vol_predicate:
                self.__current_step.volume_tag_definition = tag_definition
            elif tag_definition.predicate == self.__current_dil_predicate:
                self.__current_step.diluent_tag_definition = tag_definition

        step_number = self.__current_step.number
        default_volume = self._get_cell_value(self.__current_step.starting_row,
                                              1)
        if not default_volume is None and \
                         (isinstance(default_volume, str) or \
                         (default_volume <= 0)): # regard: None < 0 is True!
            msg = 'Invalid default transfer volume for step %i: "%s". ' \
                  'Enter a positive numbers or leave the field blank, please.' \
                   % (step_number, default_volume)
            self._create_error(msg, self._get_cell_name(self._current_row, 1))
        else:
            self.__current_step.default_volume = default_volume

        volume_tf = self.__current_step.volume_tag_definition
        if default_volume is not None and volume_tf is not None:
            msg = 'There is a default volume and individual volumes for ' \
                  'step %i. Please decide for one!' % (step_number)
            self._create_error(msg)
        elif default_volume is None and volume_tf is None:
            msg = 'There are no volumes for step %i!' % (step_number)
            self._create_error(msg)

    def __init_step_transfer_codes(self):
        """
        Initialises the transfer codes for a particular step.
        """
        self._current_row = self.__current_step.starting_row + 2

        codes = []
        while not self._end_reached:
            code = self._get_cell_value(self._current_row,
                                        self._CODE_COLUMN_INDEX)
            if code is None: break
            codes.append(code)
            self._step_to_next_row()

        if len(codes) < 1:
            msg = 'There are no codes for step %i!' \
                   % (self.__current_step.number)
            cell_name = self._get_cell_name(
                            self.__current_step.starting_row + 2, 1)
            self._create_error(msg, cell_name)

        # there must be at least one codes, otherwise we would have got an
        # error when looking for the tag definition
        for code in codes: self.__current_step.add_transfer_code(code)

        transfer_tag_def = self.__current_step.transfer_tag_definition
        self._tags.add(transfer_tag_def)
        add_list_map_element(self._tags_by_row,
                         self.__current_step.get_transfer_tag_row_index(),
                         transfer_tag_def)

    def _parse_layout_specifiers(self, layout_specifier, layout_container):
        """
        The rack must have already been registered. Also they are set as
        source or target rack for a step.
        """
        cell_name = layout_container.get_starting_cell_name()

        if layout_specifier is None:
            msg = 'There is a rack specifier missing!'
            self._create_error(msg, cell_name)
            return None

        step_container = self.__get_current_step_container()
        if step_container is None: return None
        self.__steps_by_layout[layout_container.get_unique_key()] = \
                                                                step_container

        msg = 'Invalid rack specifier "%s". The rack specifier must start ' \
              'with "%s" or "%s", followed by "%s" or "%s" and at least one ' \
              'rack identifier from the "%s" section.' % (layout_specifier,
               self._parser.source_role_marker, self._parser.target_role_marker,
               ', '.join(self._parser.RACK_MARKERS),
                self._parser.RESERVOIR_MARKER, self._parser.RACK_SECTION_MARKER)

        if not isinstance(layout_specifier, str):
            self._create_error(msg, cell_name)
            return None

        tokens = layout_specifier.split(' ')
        if not len(tokens) > 2:
            self._create_error(msg, cell_name)
            return None

        role_token = tokens[self._parser.SPECIFIER_ROLE_INDEX]
        role = step_container.add_layout(role_token, layout_container,
                                         cell_name)
        if role is None: return None
        type_token = self._convert_keyword(
                                    tokens[self._parser.SPECIFIER_TYPE_INDEX])
        valid_markers = self._parser.RACK_MARKERS \
                        + [self._parser.RESERVOIR_MARKER]
        marker_found = False
        for valid_marker in valid_markers:
            if type_token.startswith(valid_marker):
                marker_found = True
                break
        if not marker_found:
            self._create_error(msg, cell_name)
            return None

        rack_containers = []
        # we do not know whether there are white spaces between the rack IDs
        # that is onto how many tokens there are distributed
        rack_ids = ','.join(tokens[2:])
        for rack_id in rack_ids.split(','):
            rack_id = rack_id.strip()
            if len(rack_id) < 1: continue
            if not self._parser.rack_containers.has_key(rack_id):
                msg = 'Unknown rack identifier "%s"! All racks must be ' \
                      'listed in the "%s" section!' % (rack_id,
                      self._parser.RACK_SECTION_MARKER)
                self._create_error(msg, cell_name)
                return None
            rack_container = self._parser.rack_containers[rack_id]
            rack_containers.append(rack_container)
            add_list_map_element(step_container.rack_containers, role, rack_id)

        if len(rack_containers) < 1:
            msg = 'There are no rack tokens in this layout specifier!'
            self._create_error(msg, cell_name)
            return None

        return rack_containers

    def __get_current_step_container(self):
        """
        Returns the step container for the layout that is currently parsed.
        There must always be one, otherwise the layout alignment step of
        the would have failed.
        """
        step_container = None
        for row_index in sorted(self.__steps_by_row.keys(), reverse=True):
            if row_index > self._current_row: continue
            step_container = self.__steps_by_row[row_index]
            break

        return step_container

    def _parse_layout_codes(self, layout_container, tag_definitions):
        """
        We want to assign the data directly to the step containers instead
        of to the layout containers.
        """
        step_container = self.__steps_by_layout[
                                            layout_container.get_unique_key()]
        role = step_container.get_role_for_layout(layout_container)
        if role is None: return None

        for cell_indices in layout_container.get_all_layout_cells():
            table_row, table_col = cell_indices[0], cell_indices[1]
            pos_container = layout_container.get_rack_position_container(
                                                                cell_indices)
            code = self._get_cell_value(table_row, table_col)
            if code is None: continue
            volume = None
            diluent = None
            for tag_definition in tag_definitions:
                vol_tf = step_container.volume_tag_definition
                dil_tf = step_container.diluent_tag_definition
                if vol_tf is not None and tag_definition == vol_tf:
                    volume = self._get_tag_value_for_code(tag_definition, code)
                elif dil_tf is not None and tag_definition == dil_tf:
                    diluent = self._get_tag_value_for_code(tag_definition, code)
            step_container.add_transfer_data(role, code, volume, diluent,
                                             pos_container)

    def check_transfers(self):
        """
        Makes sure there is a valid number of source and target positions
        for each recorded transfer.
        """
        ambiguous = []
        invalid_volume = []

        for step_container in self.__steps_by_row.values():
            for transfer_container in step_container.get_transfer_containers():
                # the 2 getters also catch code without any source or target
                src_positions = transfer_container.get_source_positions()
                trg_positions = transfer_container.get_target_positions()
                if src_positions is None or trg_positions is None: continue
                if len(src_positions) > 1 and len(trg_positions) > 1:
                    info = '%s (step %i)' % (transfer_container.code,
                                             step_container.number)
                    ambiguous.append(info)
                if not is_valid_number(transfer_container.volume):
                    info = '%s (step %i, code %s)' % (transfer_container.volume,
                            step_container.number, transfer_container.code)
                    invalid_volume.append(info)

        if len(ambiguous) > 0:
            msg = 'You must not have multiple source AND target positions ' \
                  'for a code since the system cannot figure out the correct ' \
                  'association in this case. You can either have multiple ' \
                  'source positions OR multiple target positions. The ' \
                  'following transfers violate this rule: %s.' \
                   % (', '.join(ambiguous)) # do not sort!
            self._create_error(msg)

        if len(invalid_volume) > 0:
            msg = 'The transfer volume must be a positive number. The ' \
                  'following transfers have invalid numbers: %s' \
                  % (', '.join(invalid_volume)) # do not sort!
            self._create_error(msg)


class _TransferRackParsingContainer(RackParsingContainer):
    """
    Parsing container subclass for the storage of reservoirs or plates
    involved in generic sample transfer plan definitions.
    """
    _PARSER_CLS = GenericSampleTransferPlanParser

    def __init__(self, parser, identifier, barcode, specs, row_index):
        """
        Constructor:

        :param parser: parser the data shall be passed to
        :type parser: :class:`GenericSampleTransferPlanParser`

        :param identifier: A string that identifies the plate or reservoir
            within the sheet.
        :type identifier: :class:`str`

        :param barcode: the barcode for this rack container
        :type barcode: :class:`str`

        :param specs: the name of the reservoirs specs for this rack
        :type specs: :class:`str`

        :param row_index: index of the row containing the rack identifier
            (for error messages).
        :type row_index: :class:`int
        """
        RackParsingContainer.__init__(self, parser=parser,
                                      rack_label=identifier)

        #: the barcode for this rack container
        self.barcode = barcode
        #: the name of the reservoirs specs for this rack
        self.specs = specs

        if not (isinstance(barcode, str) or isinstance(specs, str)):
            msg = 'You need to provide a barcode or a specs name for each ' \
                  'rack or reservoir definition. Definition "%s" in row ' \
                  '%i lacks both values!' % (self.rack_label, row_index + 1)
            self._create_error(msg)

    @property
    def identifier(self):
        """
        A string that identifies the plate or reservoir within the sheet.
        """
        return self.rack_label

    def __repr__(self):
        str_format = '<%s %s, specs: %s>'
        params = (self.__class__.__name__, self.rack_label, self.specs)
        return str_format % params


class _TransferStepParsingContainer(ExcelParsingContainer):
    """
    A parsing container collecting the data for one step.
    """
    _PARSER_CLS = GenericSampleTransferPlanParser

    def __init__(self, parser, step_marker, starting_row):
        """
        Constructor:

        :param parser: The parser this container belongs to.
        :type parser: :class:`GenericSampleTransferPlanParser`

        :param step_marker: The step marker indicating this step. It
            contains a keyword an integer number.
        :class step_marker: :class:`str`

        :param starting_row: The row index of the step marker.
        :type starting_row: :class:`int`
        """
        ExcelParsingContainer.__init__(self, parser=parser)

        #: The row index of the step marker.
        self.__starting_row = starting_row
        #: Step number define the order or transfers.
        self.__number = None
        self.__parse_step_marker(step_marker)

        #: The :class:`TagDefinitionParsingContainer` containing the codes
        #: for the transfers.
        self.transfer_tag_definition = None
        if self.__number is not None:
            predicate = self._parser.TRANSFER_TAG_BASE_NAME + '%i' \
                        % (self.__number)
            self.transfer_tag_definition = TagDefinitionParsingContainer(
                        parser=self._parser, tag_predicate=predicate,
                        start_row_index=(starting_row + 1))
        #: A transfer volume applying to all transfers in this step (optional).
        self.default_volume = None
        #: The :class:`TagDefinitionParsingContainer` containing the codes
        #: for transfer volumes.
        self.volume_tag_definition = None
        #: The :class:`TagDefinitionParsingContainer` containing the codes
        #: for diluent (dilutions only) volumes.
        self.diluent_tag_definition = None

        #: The layouts for this step mapped onto roles (there can only be
        #: one layout for each role).
        self.layouts = dict()
        #: The rack containers for this step mapped onto roles.
        self.rack_containers = dict()

        #: Stores the transfer parsing containers for this step mapped onto
        #: codes.
        self.__transfer_containers = dict()

    @property
    def number(self):
        """
        Step number define the order or transfers.
        """
        return self.__number

    @property
    def starting_row(self):
        """
        The row index of the step marker.
        """
        return self.__starting_row

    def get_transfer_tag_row_index(self):
        """
        Used to register the tag in the layout sheet parsing container.

        The index must be the same row index as the factor marker (that is
        one higher than the :attr:`__starting_row`) to ensure it is
        stored along with the potential volume tag definition
        """
        return (self.__starting_row + 1)

    def __parse_step_marker(self, step_marker):
        """
        The step marker must match the following pattern: "Step [integer]"
        with the integer being the step number.
        """
        tokens = step_marker.split('_')
        cell_name = self._parser.get_cell_name(self.__starting_row, 0)
        err_msg = 'Invalid step marker "%s". A valid step marker must match ' \
                  'the following pattern: "Step [integer]".' % (step_marker)
        if not len(tokens) == 2:
            self._create_error(err_msg, cell_name)
        else:
            num_str = tokens[1]
            try:
                num_str = num_str.strip()
                self.__number = int(num_str)
            except ValueError:
                self._create_error(err_msg, cell_name)

    def add_transfer_code(self, code):
        """
        Adds a transfer that will be used later to recognise source and
        target wells in the layouts.
        """
        if self.transfer_tag_definition.has_code(code):
            msg = 'Duplicate code "%s" for step %i!' % (code, self.__number)
            self._create_error(msg)
        else:
            self.transfer_tag_definition.add_code_and_value(code, code)

    def add_layout(self, role_token, layout_container, cell_name):
        """
        Parses the role of a layout and add it to the :attr:`layouts` map.

        :param role_token: The first part of the layout specifier.
        :type role_token: :class:`str`

        :param layout_container: The layout container to be added.
        :type layout_container: :class:`LayoutParsingContainer`

        :param cell_name: name of the cell of the layout specifier
            (for error messages)
        :type cell_name: :class:`str`

        :return: the role for this layout
        """
        conv_token = role_token.lower().strip()
        if conv_token == self._parser.source_role_marker:
            role = self._parser.source_role_marker
        elif conv_token == self._parser.target_role_marker:
            role = self._parser.target_role_marker
        else:
            msg = 'Unable to determine role for this layout! You have used ' \
                  '"%s". Use "%s" or "%s", please!' \
                  % (role_token, self._parser.source_role_marker,
                     self._parser.target_role_marker)
            self._create_error(msg, cell_name)
            return None

        if self.layouts.has_key(role):
            msg = 'There are several %s layouts for step %i!' % (role,
                                                                 self.__number)
            self._create_error(msg)
            return None

        self.layouts[role] = layout_container
        return role

    def get_role_for_layout(self, layout_container):
        """
        Returns the role for the passed layout or records an error.
        """
        role = None
        for layout_role, layout in self.layouts.iteritems():
            if layout == layout_container:
                role = layout_role
                break

        if role is None:
            msg = 'Programming error. Layout %s is not known for step %i!' \
                  % (layout_container, self.__number)
            self._create_error(msg)
            return None

        return role

    def add_transfer_data(self, role, code, volume, diluent, pos_container):
        """
        Fetches or creates the transfer container for this code and add the
        volume and position data to it.
        """
        if volume is None: volume = self.default_volume

        if self.__transfer_containers.has_key(code):
            transfer_container = self.__transfer_containers[code]
        else:
            transfer_container = TransferParsingContainer(parser=self._parser,
                                    code=code, diluent=diluent, volume=volume,
                                    step_number=self.__number)
            self.__transfer_containers[code] = transfer_container

        transfer_container.add_position(role, pos_container)

    def get_transfer_containers(self):
        """
        Returns the transfer containers for this step.
        """
        return self.__transfer_containers.values()

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
                self.__number == other.number

    def __str__(self):
        return '%i' % (self.__number)

    def __repr__(self):
        str_format = '<%s %i>'
        params = (self.__class__.__name__, self.__number)
        return str_format % params


class TransferParsingContainer(ExcelParsingContainer):
    """
    Stores the data for one single transfer (corresponds to one code in
    one step).
    """
    _PARSER_CLS = GenericSampleTransferPlanParser

    def __init__(self, parser, code, volume, step_number, diluent):
        """
        Constructor:

        :param parser: The parser this container belongs to.
        :type parser: :class:`GenericSampleTransferPlanParser`

        :param code: The code for the transfer from the sheet (used as ID
            within the step).

        :param volume: The volume for the step.
        :type volume: positive number

        :param step_number: The number of the step this transfer belongs to.
        :type step_number: :class:`int`

        :param diluent: Applies only to sample dilutions.
        :type diluent: :class:`str`
        """
        ExcelParsingContainer.__init__(self, parser=parser)

        self.code = code
        self.step_number = step_number
        self.volume = volume
        self.diluent = diluent

        self.positions = dict()

    def add_position(self, role, pos_container):
        """
        Adds the position to the position list of the given role.

        :param role: source or target
            (see :class:`TransferStepParsingContainer`)
        :type role: :class:`str`

        :param pos_container: The position to store
        :type pos_container: :class:`RackPositionParsingContainer`
        """
        add_list_map_element(self.positions, role, pos_container)

    def get_source_positions(self):
        """
        Returns the source positions for this transfer.
        """
        return self.__get_role_positions(self._parser.source_role_marker)

    def get_target_positions(self):
        """
        Returns the source positions for this transfer.
        """
        return self.__get_role_positions(self._parser.target_role_marker)

    def __get_role_positions(self, role):
        """
        Returns the position container list for the specified role or records
        an error if there are no positions for the specified role.
        """
        if self.positions.has_key(role): return self.positions[role]

        msg = 'There are no %s positions for transfer %s in step %i!' \
              % (role, self.code, self.step_number)
        self._create_error(msg)

        return None

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
                other.code == self.code and \
                other.step_number == self.step_number

    def __str__(self):
        return self.code

    def __repr__(self):
        str_format = '<%s %s, step number: %i>'
        params = (self.__class__.__name__, self.code, self.step_number)
        return str_format % params
