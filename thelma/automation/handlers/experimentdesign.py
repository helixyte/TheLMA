"""
.. currentmodule:: thelma.automation.tools.metadata.generation

This is the handler for experiment design parsers. It is a component of the
:class:`ExperimentMetadataGenerator`.
"""
from thelma.automation.handlers.base \
    import MoleculeDesignPoolLayoutParserHandler
from thelma.automation.parsers.experimentdesign \
    import ExperimentDesignParser
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionParameters
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionPosition
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import get_positions_for_shape
from thelma.automation.tools.utils.base import add_list_map_element
from thelma.automation.tools.utils.base import is_valid_number
from thelma.automation.tools.utils.layouts import MOCK_POSITION_TYPE
from thelma.models.experiment import ExperimentDesign
from thelma.models.experiment import ExperimentDesignRack
from thelma.models.experiment import ExperimentMetadataType
from thelma.models.racklayout import RackLayout
from thelma.models.tagging import TaggedRackPositionSet
from thelma.models.user import User



__docformat__ = 'reStructuredText en'

__all__ = ['_SUPPORTED_SCENARIOS',
           '_SCENARIO_PARAMETERS',
           'ExperimentDesignParserHandler',
           ]


class _SUPPORTED_SCENARIOS(object):
    """
    Scenario supported by the experiment design parser handler.
    """
    #: A list of all supported scenarios.
    ALL = [EXPERIMENT_SCENARIOS.SCREENING, EXPERIMENT_SCENARIOS.OPTIMISATION,
           EXPERIMENT_SCENARIOS.MANUAL, EXPERIMENT_SCENARIOS.ISO_LESS,
           EXPERIMENT_SCENARIOS.LIBRARY]


class _SCENARIO_PARAMETERS(object):
    """
    Mandatory and forbidden parameters for the supported scenarios.
    """
    #: Parameters (factors) that are potentionally found in an experiment
    #: design.
    POTENTIAL_PARAMETERS = [TransfectionParameters.MOLECULE_DESIGN_POOL,
                            TransfectionParameters.REAGENT_NAME,
                            TransfectionParameters.REAGENT_DIL_FACTOR,
                            TransfectionParameters.FINAL_CONCENTRATION]
    #: Potential parameters that are numerical.
    NUMERICAL_PARAMETERS = [TransfectionParameters.FINAL_CONCENTRATION,
                            TransfectionParameters.REAGENT_DIL_FACTOR]

    #: Transfection parameters that need to be specified in the layout.
    MANDATORY_PARAMETERS = {
                EXPERIMENT_SCENARIOS.SCREENING : [],
                EXPERIMENT_SCENARIOS.LIBRARY : [],
                EXPERIMENT_SCENARIOS.ISO_LESS : [],
                EXPERIMENT_SCENARIOS.OPTIMISATION : [
                            TransfectionParameters.MOLECULE_DESIGN_POOL,
                            TransfectionParameters.FINAL_CONCENTRATION],
                EXPERIMENT_SCENARIOS.MANUAL : POTENTIAL_PARAMETERS
                            }

    #: Transfection parameters that must *not* be specified in the layout.
    FORBIDDEN_PARAMETERS = {
                EXPERIMENT_SCENARIOS.SCREENING : POTENTIAL_PARAMETERS,
                EXPERIMENT_SCENARIOS.ISO_LESS : POTENTIAL_PARAMETERS,
                EXPERIMENT_SCENARIOS.LIBRARY : POTENTIAL_PARAMETERS,
                EXPERIMENT_SCENARIOS.OPTIMISATION : [],
                EXPERIMENT_SCENARIOS.MANUAL : []
                            }

    #: Scenarios that do no allow for a sheet called "Transfection".
    TRANSFECTION_SHEET_SCENARIOS = [EXPERIMENT_SCENARIOS.OPTIMISATION,
                                    EXPERIMENT_SCENARIOS.MANUAL]



class ExperimentDesignParserHandler(MoleculeDesignPoolLayoutParserHandler):
    """
    This tool obtains a valid experiment design from an experiment metadata
    file. There are different subclasses for the different experiment
    scenarios.

    **Return Value:** Experiment Design
        (:class:`thelma.models.experiment.ExperimentDesign`)
    """
    NAME = 'Experiment Design Parser Handler'

    _PARSER_CLS = ExperimentDesignParser

    TAG_DOMAIN = ExperimentDesign.DOMAIN

    #: The names of the sheet to parsed in any scenario.
    BASIC_SHEET_NAMES = ['Seeding', 'Treatment', 'Assay']
    #: The name of the transfection sheet (for non-screening caes).
    TRANSFECTION_SHEET_NAME = 'Transfection'

    def __init__(self, stream, requester, scenario, log):
        """
        Constructor:

        :param stream: stream of the file to be parsed

        :param requester: the user uploading the experiment design
        :type requester: :class:`thelma.models.user.User`

        :param scenario: The scenario (experiment metadata types) defines the
            mandatory and forbidden parameters for a design rack layout and the
            names of the sheets to be parsed.
        :type scenario: :class:`thelma.models.experiment.ExperimentMetadataType`

        :param log: The ThelmaLog you want to write in.
        :type log: :class:`thelma.ThelmaLog`
        """
        MoleculeDesignPoolLayoutParserHandler.__init__(self, log=log,
                                                       stream=stream)

        #: The user uploading the file.
        self.requester = requester

        #: A :class:`ExperimentMetadataType` supported by this handler subclass.
        self.scenario = scenario

        #: Transfection parameters that need to be specified in the layout.
        self.__mandatory_parameters = None
        #: Transfection parameters that must *not* be specified in the layout.
        self.__forbidden_parameters = None
        #: Stores the presence of parameters (a parameter has to be
        #: specified for each non-empty well or not at all).
        self.__parameter_presence = dict()

        #: The designs racks for the experiment design.
        self.__design_racks = []

    def _initialize_parser_keys(self):
        """
        Initialises floating related aliases within the parser.
        """
        MoleculeDesignPoolLayoutParserHandler._initialize_parser_keys(self)

        sheet_names = set()
        for sheet_name in self.BASIC_SHEET_NAMES: sheet_names.add(sheet_name)

        if isinstance(self.scenario, ExperimentMetadataType) and \
                            self.scenario.id in \
                            _SCENARIO_PARAMETERS.TRANSFECTION_SHEET_SCENARIOS:
            sheet_names.add(self.TRANSFECTION_SHEET_NAME)
        self.parser.sheet_names = sheet_names

    def _convert_results_to_model_entity(self):
        """
        Assembles and experiment design from the parsed sheets.
        """
        self.add_info('Start experiment design generation ...')

        self._check_input()
        if not self.has_errors():
            self.__set_scenario_values()
            self._determine_rack_shape()
        if not self.has_errors():
            self.__create_design_racks()
            self.__check_design_racks()
        if not self.has_errors():
            self.return_value = ExperimentDesign(rack_shape=self._rack_shape,
                            experiment_design_racks=self.__design_racks)
            self.add_info('Experiment design creation completed.')

    def _check_input(self):
        """
        Checks the validity of the initialisation values.
        """
        self.add_debug('Check input values ...')

        self._check_input_class('requester', self.requester, User)

        if self._check_input_class('experiment metadata type', self.scenario,
                                   ExperimentMetadataType):
            if not self.scenario.id in _SUPPORTED_SCENARIOS.ALL:
                d_names = EXPERIMENT_SCENARIOS.get_displaynames(
                                                    _SUPPORTED_SCENARIOS.ALL)
                msg = 'Unknown scenario: "%s". Allowed scenarios: %s.' \
                      % (self.scenario.display_name, ', '.join(d_names))
                self.add_error(msg)

    def __set_scenario_values(self):
        """
        Sets the mandatory and forbidden parameters for the chosen scenario.
        """
        self.add_debug('Set scenario values ...')

        self.__mandatory_parameters = _SCENARIO_PARAMETERS.MANDATORY_PARAMETERS[
                                                              self.scenario.id]
        self.__forbidden_parameters = _SCENARIO_PARAMETERS.FORBIDDEN_PARAMETERS[
                                                              self.scenario.id]

        for parameter in _SCENARIO_PARAMETERS.POTENTIAL_PARAMETERS:
            if parameter == TransfectionParameters.MOLECULE_DESIGN_POOL:
                continue
            self.__parameter_presence[parameter] = False

    def __create_design_racks(self):
        """
        Creates an experiment design object from the parsed data.
        """
        for rack_container in self.parser.rack_map.values():
            label = str(rack_container.rack_label)
            trp_sets = self.__create_tagged_position_sets(rack_container)
            rack_layout = RackLayout(shape=self._rack_shape,
                                     tagged_rack_position_sets=trp_sets)
            design_rack = ExperimentDesignRack(label=label,
                                rack_layout=rack_layout,
                                experiment_design=None, worklist_series=None)
            self.__design_racks.append(design_rack)

    def __create_tagged_position_sets(self, rack_container):
        """
        Creates :class:`TaggedRackPositionSets` for a design rack layout.
        """
        self.add_debug('Create tagged rack positions sets ...')
        tagged_rack_positions = []

        position_set_map = {} # maps rack position sets on hash values
        tag_set_map = {} # maps tag lists on hash values

        for layout_key in rack_container.layout_container_keys:
            layout_container = self.parser.layout_map[layout_key]
            for tag_container, pos_containers in layout_container.\
                                                tag_data.iteritems():
                pos_set = self._convert_to_rack_position_set(pos_containers)
                hash_value = pos_set.hash_value
                tag = self._convert_to_tag(tag_container)
                if position_set_map.has_key(hash_value):
                    tag_set_map[hash_value].append(tag)
                else:
                    position_set_map[hash_value] = pos_set
                    tag_set_map[hash_value] = [tag]

        for hash_value in position_set_map.keys():
            rps = position_set_map[hash_value]
            tags = set(tag_set_map[hash_value])
            trps = TaggedRackPositionSet(tags, rps, self.requester)
            tagged_rack_positions.append(trps)

        return tagged_rack_positions

    def __check_design_racks(self):
        """
        Checks the presence of parameters for each rack design rack.
        """
        self.add_debug('Check design racks ...')

        validators = dict()
        for parameter in _SCENARIO_PARAMETERS.POTENTIAL_PARAMETERS:
            validator = TransfectionParameters.create_validator_from_parameter(
                                                                     parameter)
            validators[parameter] = validator

        for design_rack in self.__design_racks:
            value_maps = self.__get_values_for_rack_layout(validators,
                                                           design_rack.layout)
            if self.__check_for_molecule_designs(value_maps, design_rack.label):
                self.__check_numerical_values(value_maps, design_rack.label)
                self.__check_reagent_name(value_maps, design_rack.label)
                self.__check_value_presence(value_maps, design_rack.label)

    def __get_values_for_rack_layout(self, validators, rack_layout):
        """
        Finds the parameters values for each position in a design rack layout.
        """
        shape_positions = get_positions_for_shape(self._rack_shape)

        # Initialise the value maps
        value_maps = dict()
        for parameter in validators.keys():
            rack_pos_dict = dict()
            for rack_pos in shape_positions:
                rack_pos_dict[rack_pos] = None
            value_maps[parameter] = rack_pos_dict

        for trps in rack_layout.tagged_rack_position_sets:
            for tag in trps.tags:
                for parameter, validator in validators.iteritems():
                    if validator.has_alias(tag.predicate):
                        value_map = value_maps[parameter]
                        for rack_pos in trps.rack_position_set:
                            value_map[rack_pos] = tag.value

        return value_maps

    def __check_for_molecule_designs(self, value_maps, label):
        """
        Checks whether there are molecule designs in the layout.
        """
        pool_parameter = TransfectionParameters.MOLECULE_DESIGN_POOL

        has_pools = False
        for value in value_maps[pool_parameter].values():
            if not value is None:
                has_pools = True
                break

        if not has_pools and pool_parameter in self.__mandatory_parameters:
            msg = 'There are no molecule design pools in the layout for ' \
                  'design rack %s.' % (label)
            self.add_error(msg)
            return False
        elif has_pools and pool_parameter in self.__forbidden_parameters:
            msg = 'There are molecule design pools in the layout for design ' \
                  'rack %s. This is not allowed for the current scenario (%s).' \
                  % (label, self.scenario.display_name)
            self.add_error(msg)
            return False

        return True

    def __check_numerical_values(self, value_maps, label):
        """
        Checks the values of the numerical parameters.
        """
        invalid_numericals = dict()
        invalid_mock = dict()
        invalid_untreated = dict()

        pool_map = value_maps[TransfectionParameters.MOLECULE_DESIGN_POOL]
        for parameter, value_map in value_maps.iteritems():
            if not parameter in _SCENARIO_PARAMETERS.NUMERICAL_PARAMETERS:
                continue
            for rack_pos, value in value_map.iteritems():
                if value is None: continue

                pool = pool_map[rack_pos]

                if (pool == MOCK_POSITION_TYPE):
                    if parameter == TransfectionParameters.FINAL_CONCENTRATION \
                                and not TransfectionPosition.\
                                        is_valid_mock_value(value):
                        add_list_map_element(invalid_mock, parameter,
                                             rack_pos.label)

                elif TransfectionParameters.is_untreated_type(pool):
                    if parameter in (TransfectionParameters.FINAL_CONCENTRATION,
                                TransfectionParameters.REAGENT_DIL_FACTOR) \
                                and not TransfectionPosition.\
                                        is_valid_untreated_value(value):
                        add_list_map_element(invalid_untreated, parameter,
                                             rack_pos.label)

                elif not is_valid_number(value):
                    info = '%s (%s)' % (rack_pos.label, value)
                    add_list_map_element(invalid_numericals, parameter, info)

        if len(invalid_numericals) > 0:
            records_str = self.__get_error_record_string(invalid_numericals)
            msg = 'The levels of some factors must be positive numbers. The ' \
                  'following positions in design rack %s have invalid ' \
                  'values: %s.' % (label, records_str)
            self.add_error(msg)

        if len(invalid_mock) > 0:
            records_str = self.__get_error_record_string(invalid_mock)
            msg = 'The levels of some factors for mock positions allow only ' \
                  'for the values "None" or "mock" (or no level). Some ' \
                  'positions in design rack "%s" have invalid levels. ' \
                  'Affected positions: %s.' % (label, records_str)
            self.add_error(msg)

        if len(invalid_untreated) > 0:
            records_str = self.__get_error_record_string(invalid_untreated)
            msg = 'The levels of some factors for untreated positions allow ' \
                  'only for the values "None" and "untreated" (or no level). ' \
                  'Some position in design rack "%s" have invalid levels. ' \
                  'Affected positions: %s.' % (label, records_str)
            self.add_error(msg)

    def __check_reagent_name(self, value_maps, label):
        """
        Checks the reagent name for each rack position in a layout
        (if this parameter is an allowed one). The reagent name must have a
        special value for untreated positions and be at least two character
        long for other positions.
        """
        if not TransfectionParameters.REAGENT_NAME \
                                            in self.__forbidden_parameters:

            pool_map = value_maps[TransfectionParameters.MOLECULE_DESIGN_POOL]
            name_map = value_maps[TransfectionParameters.REAGENT_NAME]

            invalid_untreated = []
            invalid_others = []

            for rack_pos, reagent_name in name_map.iteritems():
                if reagent_name is None: continue

                pool = pool_map[rack_pos]
                if TransfectionParameters.is_untreated_type(pool):
                    if not TransfectionPosition.is_valid_untreated_value(
                                                                reagent_name):
                        invalid_untreated.append(rack_pos.label)
                elif not len(reagent_name) > 1:
                    invalid_others.append(rack_pos.label)

            if len(invalid_untreated):
                msg = 'Untreated position must only have the reagent names ' \
                      '"None", "untreated" or no reagent name at all. The ' \
                      'following untreated positions in design rack "%s" ' \
                      'have invalid reagent names: %s.' \
                       % (label, ', '.join(sorted(invalid_untreated)))
                self.add_error(msg)

            if len(invalid_others):
                msg = 'The reagent name must be at least 2 characters long. ' \
                      'The following positions in design rack "%s" have ' \
                      'invalid reagent names: %s.' \
                       % (label, ', '.join(sorted(invalid_others)))
                self.add_error(msg)

    def __check_value_presence(self, value_maps, label):
        """
        Checks the presence of mandatory, optional and forbidden parameters
        for each rack position in a layout.
        """
        pool_map = value_maps[TransfectionParameters.MOLECULE_DESIGN_POOL]
        pool_forbidden = TransfectionParameters.MOLECULE_DESIGN_POOL in \
                         self.__forbidden_parameters

        non_empty = []
        missing_value = dict()
        additional_values = dict()
        inconsistent_optionals = dict()

        for rack_pos in get_positions_for_shape(self._rack_shape):
            pool_id = pool_map[rack_pos]

            is_untreated = (isinstance(pool_id, basestring) and \
                      TransfectionParameters.is_untreated_type(pool_id.lower()))
            if is_untreated: continue

            if pool_id is None: # Empty position should not have values
                for parameter, value_map in value_maps.iteritems():
                    if not value_map[rack_pos] is None:
                        non_empty.append(rack_pos.label)
                        break
                if not pool_forbidden: continue

            for parameter, value_map in value_maps.iteritems():
                if parameter == TransfectionParameters.MOLECULE_DESIGN_POOL:
                    continue
                elif pool_id == MOCK_POSITION_TYPE and \
                    parameter == TransfectionParameters.FINAL_CONCENTRATION:
                    continue

                value = value_map[rack_pos]

                # Check consistency of definition
                present_parameter = self.__parameter_presence[parameter]
                if present_parameter and value is None:
                    if not inconsistent_optionals.has_key(parameter):
                        inconsistent_optionals[parameter] = []
                    inconsistent_optionals[parameter].append(rack_pos.label)
                elif not present_parameter and not value is None and \
                                                            not pool_forbidden:
                    self.__parameter_presence[parameter] = True

                # Check mandatory and forbidden parameters
                if parameter in self.__mandatory_parameters and \
                                                            value is None:
                    if not missing_value.has_key(parameter):
                        missing_value[parameter] = []
                    missing_value[parameter].append(rack_pos.label)
                elif parameter in self.__forbidden_parameters and \
                                                        not value is None:
                    if not additional_values.has_key(parameter):
                        additional_values[parameter] = []
                    info = '%s (%s)' % (rack_pos.label, value)
                    additional_values[parameter].append(info)

        # Error recording
        if len(non_empty) > 0 and not pool_forbidden:
            msg = 'Some rack positions in design rack %s contain values ' \
                  'although there are no molecule designs for them: %s.' \
                   % (label, ', '.join(sorted(non_empty)))
            self.add_error(msg)

        if len(missing_value) > 0:
            records_str = self.__get_error_record_string(missing_value)
            msg = 'There are mandatory values missing for some rack ' \
                  'positions in design rack %s: %s. Assumed scenario: %s.' \
                   % (label, records_str, self.scenario.display_name)
            self.add_error(msg)

        if len(additional_values) > 0:
            records_str = self.__get_error_record_string(additional_values)
            msg = 'Some factors must not be specified in %s scenarios. The ' \
                  'following position in design rack %s contain ' \
                  'specifications for forbidden factors: %s.' \
                  % (self.scenario.display_name, label, records_str)
            self.add_error(msg)

        if len(inconsistent_optionals) > 0:
            records_str = self.__get_error_record_string(inconsistent_optionals)
            msg = 'If you specify a factor, you have to specify it for each ' \
                  'non-empty well in all design racks. The following wells ' \
                  'in design rack %s lack a specification: %s.' \
                   % (label, records_str)
            self.add_error(msg)

    def __get_error_record_string(self, recorded_events):
        """
        Converts a dictionary of recorded errors events into a string.
        """
        records = []
        for parameter, infos in recorded_events.iteritems():
            infos.sort()
            record = '%s: %s' % (parameter.replace('_', ' '), ', '.join(infos))
            records.append(record)
        records_str = ' - '.join(records)

        return records_str
