"""
:Date: 2011 July
:Author: AAB, berger at cenix-bioscience dot com

.. currentmodule:: thelma.automation.tools.metadata.generation

This is an ISO Excel file parser for Thelma. It is a component of the
:class:`ExperimentMetadataGenerator`.

The exact constraints depend on the experiment type of the associated metadata.


ISO
...

.. currentmodule:: thelma.models.moleculedesign

ISOs (= \'*internal sample orders*\') define the positions of molecule design
set on an experiment source plate. There four possible types of well types:

.. _position_type:

    * **Empty position**
        A well without a molecule designs.
    * **Fixed position**
        A well containing a defined :class:`MoleculeDesignPool`.
    * **Floating position**
        A well containing a molecule design set that is not specified. The
        available molecule design to fill this position are stored
        in the :class:`MoleculeDesignSet` of a subproject
        (:class:`thelma.models.subproject.Subproject`).
    * **Mock position**
        A well containing transfection reagent but not molecule designs.

Different types of wells might requires additional data such as volumes and
concentrations. The exact requirement depend on the experiment type.

Layouts and Tags
................

.. currentmodule:: thelma.automation.parsers.base

The ISOs are specified in 2D layouts and stored as atomic values and in
:class:`ParsingContainer` objects. These data will then be converted into
a ISO request object by the parsers handler. At this, the handler will store
information as :ref:`machine tags <machinetags>`
(:class:`thelma.models.tagging.Tag`).

There are always **up to 7** machine tags per ISO layout position:

    1. :ref:`position type <position_type>` (empty, fixed, floating, library,
        untreated, untransfected)
    2. molecule design pool (storing the molecule design pool ID or a
       placeholder - placeholder are equal to the position type they stand
       for, the only exception is \'sample\' which stands for \'floating\')
    3. optional: reagent name (the name of RNAi agent)
    4. optional: reagent dilution factor (the volume of the RNAi agent)
    5. optional: ISO volume
    6. optional: ISO concentration
    7. optional: final concentration

:Note: The position type is determined automatically depending on the
    the molecule design specification.

.. _machinetags:

Machine Tags
............

.. currentmodule:: thelma.models.tagging

A machine tag (triple tag, see: :class:`Tag`) is composed of three parts:

  * **domain**
        a domain or namespace (HERE: *iso*)
  * **predicate** (former *factor*)
        an experimental parameter (e.g. concentration)
  * **value** (former *level*)
        The actual value of a parameter
        (e.g. a certain cell density).
        There are several values for each predicate.


The domain is set by the system. It does not occur within
the parsing process. The predicates need to match the system's parameter
names (case-insensitive). Values can be defined freely by the user.
They are the actual values for the parameters.


Parsing Notes
.............

.. currentmodule:: thelma.models.iso

ISO layouts are specified on a separate sheet of experimental meta data
Excel files (see :mod:`thelma.automation.tools.metadata.generation`).
Detailed information about their composition are given in the
`Composition of Source Files`_ section.
The parsing will proceed as follows:

 1. open source file
 2. get ISO sheet
 3. parse ISO metadata
 4. parse the tag definitions (including values and codes) of the ISO sheet
 5. find layout definitions of the sheet and determine the basic information
    (position on the sheet, associated racks, plate shape)
 6. parse the layouts using codes and value definitions

:Note: The tag constraint (mandatory and optional tags, definition mode
    such as via metadata, via layout or both) is defined by the experiment
    type and set by the parser handler.

The ISO rack layout object can be stored in the database (as conventional
rack layout in the \'*rack_layout*\' table). The ISO request is stored
in the \'*iso_request*\' table.

.. currentmodule:: thelma.parsers.implementation.excel

All intermediate data is stored in parsing container object (see:
:class:`ExcelParsingContainer`)
first since it cannot be converted into model objects due to the
different hierarchical structure.

Composition of Source Files
...........................

* The excel sheet containing the ISO layout to be parsed must be
  called \'*ISO*\' and be part of the experiment meta data file
  (see :mod:`thelma.automation.parsers.experimentdesign`).
* The ISO sheet contains ISO metadata, factor (tag) definitions
  and graphical rack layouts.
* The metadata is specified in the top cells second column. There are
  different options that marked with the following key words (all case
  insensitive, arbitrary order): \'*ISO CONCENTRATION*\', \'*ISO VOLUME*\'
  \'*DELIVERY DATE*\', \'*PLATE SET LABEL*\', \'*COMMENT*\',
  \'*REAGENT NAME*\', \'*REAGENT VOLUME*\', \'*NUMBER OF ALIQUOTS\'*
  (screening only), \'*FINAL CONCENTRATION*\',
  \'LIBRARY\' (library screening only)
  and \'*MOLECULE DESIGN LIBRARY*\' (library screening only). The allowed
  and required keywords are defined by the experiment scenario and are
  set by an external parser handler.
* The key word must be located in the first column of the sheet in the
  same row as the referring value.
* The value for the plate set label must be specified. All other values are
  optional.
* Values in the metadata part for parameters will be treated as default values
  (position-specific parameters such as the concentration for mock positions
  is always *None* are always set to valid values).
  There can only be either a default value or a layout specification.
* The delivery date must be specified the following way: ::

    dd.MM.yyyy         (day-month-year)

* Tags (factors) are marked with the string *\'FACTOR*\'
  (case-insensitive) in the first column of the sheet.
* The string \'*END*\' (case insensitive) marks the end of the section
  where tag or layout information should be extracted.
* A rack layout is associated with a tag (factor) if it is placed between
  the row containing the tag (factor) marker and either the next tag marker
  or the end marker.
* There are 7 possible parameter tags (factors) for layouts:
  \'*MOLECULE DESIGN*\', \'*ISO VOLUME*\', \'*ISO CONCENTRATION*\',
  \'*REAGENT NAME*\', \'*REAGENT VOLUME*\' and \'*FINAL CONCENTRATION*\'
  (all case-insensitive). The allowed and required parameters
  are defined by the experiment scenario and are set by an external parser
  handler. Other factor names can be used as well. They will not be regarded in
  the ISO and transfection process.
* The first column to the right of the tag (factor) marker contains
  the marker string \'*CODE*\' (case-insensitive).
* The first column to the right of the tag marker (or the \'*CODE*\' marker,
  if present) *must* contain a label, which is taken as the tag predicate.
* If additional columns to the right of the tag label contain
  a label, they are interpreted as predicates for additional tags
  (\'associated tags\' or \'related tags\'). The codes for the values of these
  tags are the same like the codes for the \'main\' tag in the first column.
  Values of related tags can thereby have more than one code.
* Below the tag marker is a cell with the marker string \'*LEVELS*\'
  (case-insensitive).
* Each non-empty cell below the tag (factor) label cell declares a tag
  value. Tag values must be unique. The first empty cell indicates
  the end of the tag value declarations.
* In case one or several related tag labels were declared next to the
  main tag label, tag values are read from the corresponding cells in each
  tag value (level) row. Values of associated tags need not be unique and
  can also be empty (in which case the resulting tag value is *None*).
* Rack layouts are detected by their top left (origin) cell. The original
  cell itself is empty and has a cell containing a *1* to the right
  and a cell containing an *A* below.
* Cells in the column below the origin cell must contain consecutive
  labels. The first empty cell indicates the end of the row labels.
* Cells in the row right to the origin cell contain consecutive
  numbers. The first empty cell indicates the end of the column labels.
* The shape of the layout (i.e., the number of rows and columns)
  must match one of the allowed standard shapes.
* Since there is only 4 valid tags (factors) for ISO layout there can
  only be 4 layout definitions at maximum.


:note: Sheet with other names will be ignored.
:note: xlsx files are not supported.

Implementation
..............
"""

from thelma.automation.parsers.base \
        import ExcelMoleculeDesignPoolLayoutParsingContainer
from thelma.automation.parsers.base import ExcelMoleculeDesignPoolLayoutParser
from thelma.automation.parsers.base import ExcelParsingContainer
from thelma.automation.parsers.base import RackParsingContainer

__docformat__ = "reStructuredText en"
__all__ = ['IsoRequestParser',
           '_IsoSheetParsingContainer',
           '_ParameterContainer']


class IsoRequestParser(ExcelMoleculeDesignPoolLayoutParser):
    """
    This is the actual parser class for parsing ISO excel files.
    """
    #: name of the parser (requested by logs)
    NAME = 'ISO Parser'
    #: name of the sheet containing the ISO layout
    SHEET_NAME = 'ISO'
    #: Values in the metadata which can be ignored (because they only
    #: serve the purpose to mark filed to fill in).
    METADATA_IGNORE_VALUES = ['optional', 'dd.mm.yyyy', '']

    def __init__(self, stream, parent=None):
        ExcelMoleculeDesignPoolLayoutParser.__init__(self, stream,
                                                     parent=parent)
        self.layouts_have_specifiers = False
        # I. Tag-related values.
        #: The tag predicate for molecule design tags (set by the handler).
        self.molecule_design_parameter = None
        #: The parameters that might be specified by layouts (with their
        #: predicates and aliases mapped onto the parameter name).
        self.layout_parameters = None
        #: List of optional parameters that do not have to be specified
        #: (set by the handler).
        self.optional_parameters = None
        # II. Metadata-related values (set by the handler).
        #: List of valid meta data specifiers (list of :class:`string`).
        self.allowed_metadata = None
        #: List of required meta data specifiers
        self.required_metadata = None
        # III. Storage of the parsed data
        #: Stores the values for the ISO metadata.
        self.metadata_value_map = dict()
        #: Stores the :class:`_ParameterContainer` for each allowed parameter.
        self.parameter_map = dict()

    def reset(self):
        """
        Reset the values that have not been set by the handler.
        """
        ExcelMoleculeDesignPoolLayoutParser.reset(self)
        self.metadata_value_map = None
        self.parameter_map = None

    def run(self):
        """
        Parses the ISO sheet.
        """
        self.reset()
        self.add_debug('Start ISO parsing ...')
        if not self.has_errors():
            wb = self.open_workbook()
            self.sheet = self.__get_sheet(wb)
            if not self.has_errors():
                sheet_container = _IsoSheetParsingContainer(self)
                self.metadata_value_map = \
                        sheet_container.parse_iso_meta_data()
            if not self.has_errors():
                sheet_container.parse_tag_definitions()
            if not self.has_errors():
                sheet_container.find_layouts()
            if not self.has_errors():
                self._check_and_replace_floatings()
                self.parameter_map = \
                    sheet_container.update_parameter_containers()
            if not self.has_errors():
                self.add_info('Parsing completed.')

    def has_shape(self):
        """
        Returns whether the shape of the ISO has
        been defined already.

        :rtype: :class:`boolean`
        """
        return not self.shape is None

    def __get_sheet(self, workbook):
        # Returns the sheet for the ISO.
        sheet = None
        for sheet_name in workbook.sheet_names():
            if sheet_name.upper() == self.SHEET_NAME:
                sheet = self.get_sheet_by_name(workbook, sheet_name)
                if not sheet is None:
                    break
        if sheet is None:
            self.abort_execution = True
        return sheet


class _IsoSheetParsingContainer(ExcelMoleculeDesignPoolLayoutParsingContainer):
    """
    ParsingContainer subclass performing the single steps of the parsing
    and storing the intermediate information of an ISO Excel sheet.
    """
    _PARSER_CLS = IsoRequestParser

    def __init__(self, parser):
        ExcelMoleculeDesignPoolLayoutParsingContainer.__init__(self, parser,
                                                               parser.sheet)
        self._create_info('Parse ISO sheet ...')
        #: stores the values for the different metadata specifications
        self.metadata_dict = {}
        for metadata_marker in self._parser.allowed_metadata:
            self.metadata_dict[metadata_marker] = None
        #: The name of the molecule design parameter.
        self.molecule_design_parameter = self._parser.molecule_design_parameter
        #: stores the parameter containers
        self.parameter_map = {}
        for parameter, alias_list in self._parser.layout_parameters.iteritems():
            self.parameter_map[parameter] = \
                _ParameterContainer(self._parser, parameter, alias_list)
        # III instance variables for intermediate data storage
        #: This is only a placeholder - there is always only one rack.
        self.__rack_container = RackParsingContainer(parser=self._parser,
                                                     rack_label='ISO plate')
        #: a list of all layout containers
        self.__layout_containers = []

    def parse_iso_meta_data(self):
        """
        Parses the metadata section of the ISO sheet.
        """
        self._create_info("Parse ISO metadata ...")
        invalid_markers = []
        while not self._end_reached:
            metadata_marker = self._get_cell_value(self._current_row, 0)
            if metadata_marker is None \
               or not isinstance(metadata_marker, str):
                break
            metadata_marker = self._convert_keyword(metadata_marker)

            if not metadata_marker in self._parser.allowed_metadata:
                invalid_markers.append(metadata_marker.replace('_', ' '))
            else:
                metadata_value = self._get_cell_value(self._current_row, 1)
                if metadata_value in self._parser.METADATA_IGNORE_VALUES:
                    metadata_value = None
                self.metadata_dict[metadata_marker] = metadata_value
            self._step_to_next_row()
        if len(invalid_markers) > 0:
            msg = 'Unknown metadata specifiers: %s. Please use only the ' \
                  'following specifiers: %s.' \
                   % (', '.join(sorted(invalid_markers)),
                      ', '.join(sorted(self._parser.allowed_metadata)))
            self._create_error(msg)
            result = None
        else:
            self.__metadata_complete()
            self.__set_default_parameters()
            result = self.metadata_dict
        return result

    def __metadata_complete(self):
        # Checks whether there are missing metadata specifications.
        missing_specifications = []
        for metadata_marker in self._parser.required_metadata:
            metadata_value = self.metadata_dict[metadata_marker]
            if metadata_value is None or len(str(metadata_value)) < 1:
                missing_specifications.append(metadata_marker)
        if len(missing_specifications) > 0:
            msg = 'Could not find value for the following ISO meta data ' \
                  'specifications: %s' % (', '.join(missing_specifications))
            self._create_error(msg)

    def __set_default_parameters(self):
        # Sets the default values for the required parameters.
        for parameter in self.parameter_map.keys():
            if parameter == self.molecule_design_parameter:
                continue
            if not self.metadata_dict.has_key(parameter):
                continue
            default_value = self.metadata_dict[parameter]
            self.parameter_map[parameter].default_value = default_value

    def parse_tag_definitions(self):
        """
        Parses tags, values and codes (including associated tags) of a
        sheet and stores them as TagParsingContainer objects in the
        tags list of the SheetParsingContainer.
        """
        self._create_debug_info('Parse tag definitions ...')
        while not self._end_reached:
            self._parse_tag_definitions()
            if self._parser.has_errors():
                break
            self._step_to_next_row()
        if not self._parser.has_errors():
            self.__assign_parameters()

    def __assign_parameters(self):
        """
        Assigns tag definition containers to parameter containers and
        checks whether there is a valid definition for each parameter.
        """
        for parameter_container in self.parameter_map.values():
            parameter = parameter_container.parameter_name
            alias_list = parameter_container.tag_predicates
            tag_definition = \
                self.__get_tag_definition_for_parameter(parameter_container)
            parameter_container.tag_definition = tag_definition
            if parameter in self._parser.optional_parameters:
                continue
            elif parameter == self.molecule_design_parameter:
                if tag_definition is None:
                    msg = 'Could not find a tag definition for molecule ' \
                          'design pool IDs!'
                    self._create_error(msg)
                else:
                    self._parser.pool_tag_definition = tag_definition
            else:
                if tag_definition is None \
                   and parameter_container.default_value is None:
                    msg = 'There are no values specified for the parameter ' \
                          '"%s". Please give a default value at the ' \
                          'beginning of the sheet or specify the values as ' \
                          'factor and levels. Valid factor names are: %s.'  \
                           % (parameter_container.parameter_name,
                              ', '.join(alias_list))
                    self._create_error(msg)

    # pylint: disable=W0613
    def _parse_layout_specifiers(self, layout_specifier, layout_containers):
        """
        On ISO sheets there is only one rack.
        """
        return [self.__rack_container]
    # pylint: enable=W0613

    def _parse_layout_codes(self, layout_container, tag_definitions):
        """
        We must distinguish between parameter and normal tags.
        For non-parameter tags, the data is passed to the layout
        containers, for parameters it is stored in the layout containers.

        We could also do this afterwards, but then it is harder to distinguish
        between parameter tags and other tags.
        """
        for tag_definition in tag_definitions:
            predicate = tag_definition.predicate
            parameter_container = self.__get_parameter_for_predicate(predicate)
            if parameter_container is not None:
                parameter_container.add_layout_container(layout_container)

        ExcelMoleculeDesignPoolLayoutParsingContainer._parse_layout_codes(self,
                                              layout_container, tag_definitions)

    def update_parameter_containers(self):
        """
        Transfers the tag data items from the layout container to the ISO
        parameter containers and removes the referring tag definitions and
        tag data items from non-parameter lists (since all tag data there
        will be converted into additional layout tags later).
        """
        for parameter_container in self.parameter_map.values():
            if not parameter_container.has_layout:
                continue
            layout_container = parameter_container.layout_container
            del_tags = []
            for tag_container, positions in layout_container.\
                                            tag_data.iteritems():
                if not parameter_container.predicate_is_alias(
                                            tag_container.predicate):
                    continue
                tag_value = tag_container.value
                for pos_container in positions:
                    parameter_container.add_tag_value(tag_value, pos_container)
                    if self._parser.has_errors():
                        return None
                del_tags.append(tag_container)
            for tag_container in del_tags:
                del layout_container.tag_data[tag_container]
            self._tags.remove(parameter_container.tag_definition)
        return self.parameter_map

    def __get_parameter_for_predicate(self, tag_predicate):
        # Checks whether the a tag predicate specifies either a molecule
        # design or a concentration.
        result = None
        for parameter_container in self.parameter_map.values():
            if parameter_container.predicate_is_alias(tag_predicate):
                result = parameter_container
                break
        return result

    def __get_tag_definition_for_parameter(self, parameter_container):
        # Gets a tag definition container by its predicate.
        result = None
        for tag_definition in self._tags:
            if parameter_container.predicate_is_alias(
                                                    tag_definition.predicate):
                result = tag_definition
                break
        return result


class _ParameterContainer(ExcelParsingContainer):
    """
    ParsingContainer subclass for the storage of ISO request parameter data.
    """

    def __init__(self, parser, parameter_name, tag_predicates):
        """
        Constructor.

        :param str parameter_name: The name of the parameter.
        :param tag_predicates: A list of aliases (valid tag predicates)
            for this parameter.
        """
        ExcelParsingContainer.__init__(self, parser)
        #: The name of the parameter.
        self.parameter_name = parameter_name
        #: A list of valid predicates for this parameter.
        self.tag_predicates = self.__init_predicates(tag_predicates)
        #: Dedicates whether there is a well-wise specification for this
        #: parameter.
        self.has_layout = False
        #: The parameter's tag container
        #: (:class:`thelma.parsers.bsae.TagDefinitionParsingContainer`)
        self.tag_definition = None
        #: The parameter's :class:`IsoLayoutParsingContainer`
        self.layout_container = None
        #: Stores the values for the all wells (wells as rack position labels).
        self.well_map = {}
        #: The default value (as given in the metadata specification).
        self.default_value = None

    def predicate_is_alias(self, predicate):
        """
        Checks whether a predicate is a valid alias for this parameter.
        """
        conv_predicate = self._convert_keyword(predicate)
        return conv_predicate in self.tag_predicates

    def __init_predicates(self, alias_list):
        # Initialises a list with converted aliases.
        return [self._convert_keyword(alias) for alias in alias_list]

    def add_layout_container(self, layout_container):
        """
        Adds the layout container for this parameter and sets the
        :attr:`has_layout` attribute to true. This is not done earlier
        to ensure that parameters that have tag definitions but no layouts
        are not listed.
        """
        self.layout_container = layout_container
        self.has_layout = True

    def add_tag_value(self, tag_value, position_container):
        """
        Adds a tag value for a position (stored in the :attr:`well_map`).
        """
        if self.default_value is not None:
            msg = 'You have specified both a default value and a layout ' \
                  'for the "%s" parameter! Please choose one option.' \
                  % (self.parameter_name)
            self._create_error(msg)
        else:
            self.well_map[position_container.label] = tag_value

    def __str__(self):
        return self.parameter_name

    def __repr__(self):
        return '<ParameterParsingContainer %s>' % (self.parameter_name)
