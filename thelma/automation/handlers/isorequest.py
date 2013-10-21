"""
:Date: 2011 Aug 1st
:Author: AAB, berger at cenix-bioscience dot com

.. currentmodule:: thelma.automation.tools.metadata.generation

This is the handler for ISO and transfection parsing. It converts the parsing
result into an IsoRequest object (including checks).

The tools are components of the :class:`ExperimentMetadataGenerator`.

"""
from datetime import date
from everest.entities.utils import get_root_aggregate
from thelma.automation.handlers.base \
    import MoleculeDesignPoolLayoutParserHandler
from thelma.automation.parsers.isorequest import IsoRequestParser
from thelma.automation.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.semiconstants import get_experiment_metadata_type
from thelma.automation.semiconstants import get_positions_for_shape
from thelma.automation.tools.metadata.base import TransfectionAssociationData
from thelma.automation.tools.metadata.base import TransfectionLayout
from thelma.automation.tools.metadata.base import TransfectionParameters
from thelma.automation.tools.metadata.base import TransfectionPosition
from thelma.automation.utils.base import MAX_PLATE_LABEL_LENGTH
from thelma.automation.utils.base import add_list_map_element
from thelma.automation.utils.base import are_equal_values
from thelma.automation.utils.base import get_trimmed_string
from thelma.automation.utils.base import is_larger_than
from thelma.automation.utils.base import is_valid_number
from thelma.automation.utils.converters import LibraryLayoutConverter
from thelma.automation.utils.iso import IsoRequestParameters
from thelma.automation.utils.layouts import EMPTY_POSITION_TYPE
from thelma.automation.utils.layouts import FIXED_POSITION_TYPE
from thelma.automation.utils.layouts import FLOATING_POSITION_TYPE
from thelma.automation.utils.layouts import LIBRARY_POSITION_TYPE
from thelma.automation.utils.layouts import MOCK_POSITION_TYPE
from thelma.automation.utils.layouts import UNTRANSFECTED_POSITION_TYPE
from thelma.automation.utils.layouts import UNTREATED_POSITION_TYPE
from thelma.automation.utils.racksector import QuadrantIterator
from thelma.interfaces import IMoleculeDesignLibrary
from thelma.interfaces import IMoleculeDesignPool
from thelma.models.iso import LabIsoRequest
from thelma.models.tagging import TaggedRackPositionSet
from thelma.models.user import User

__docformat__ = 'reStructuredText en'

__all__ = ['IsoRequestParserHandler',
           'IsoRequestParserHandlerOpti',
           'IsoRequestParserHandlerScreen',
           'IsoRequestParserHandlerLibrary',
           'IsoRequestParserHandlerManual',
           'IsoRequestParserHandlerOrder']


class IsoRequestParserHandler(MoleculeDesignPoolLayoutParserHandler):
    """
    This tool obtains a valid ISO-and-transfection layout from an experiment
    metadata file. There are special subclass for the different experiment
    scenarios.

    **Return Value:** ISO request (:class:`thelma.models.iso.IsoRequest`).
    """
    NAME = 'ISO Request Parser Handler'

    _PARSER_CLS = IsoRequestParser

    TAG_DOMAIN = TransfectionParameters.DOMAIN

    #: The experiment scenario supported by this class (display name).
    SUPPORTED_SCENARIO = None
    #: This placeholder is used if the user did not specify a plate set label
    #: (ISO request label). The label is replaced by the experiment metadata
    #: label later.
    NO_LABEL_PLACEHOLDER = 'default'


    #: The separator for date tokens (day-month-year)
    DATE_SEPARATOR = '.'
    #: Keyword indicating a delivery date specification.
    DELIVERY_DATE_KEY = 'delivery_date'
    #: Keyword indicating a plate set label specification.
    PLATE_SET_LABEL_KEY = 'plate_set_label'
    #: Keyword indicating a comment.
    COMMENT_KEY = 'comment'
    #: Keyword indicating a number of aliquots specification.
    NUMBER_ALIQUOT_KEY = 'number_of_aliquots'
    #: Keyword indicating a library name (library screenings only).
    LIBRARY_KEY = 'molecule_design_library'

    #: By default, all position types are allowed.
    ALLOWED_POSITION_TYPES = set([FIXED_POSITION_TYPE, FLOATING_POSITION_TYPE,
                              LIBRARY_POSITION_TYPE, MOCK_POSITION_TYPE,
                              UNTREATED_POSITION_TYPE,
                              UNTRANSFECTED_POSITION_TYPE, EMPTY_POSITION_TYPE])

    #: A list of parameters that do not need to specified at all.
    OPTIONAL_PARAMETERS = None
    #: A list of the metadata values that have be specified (as metadata).
    REQUIRED_METADATA = None
    #: A list of metadata values that are allowed be specified as metadata.
    ALLOWED_METADATA = [PLATE_SET_LABEL_KEY, DELIVERY_DATE_KEY, COMMENT_KEY,
                        NUMBER_ALIQUOT_KEY, IsoRequestParameters.ISO_VOLUME,
                        IsoRequestParameters.ISO_CONCENTRATION,
                        TransfectionParameters.FINAL_CONCENTRATION,
                        TransfectionParameters.REAGENT_NAME,
                        TransfectionParameters.REAGENT_DIL_FACTOR]

    #: The ISO parameters that might be specified in a layout as list.
    ISO_LAYOUT_PARAMETERS = None
    #: The transfection parameters that might be specified in a layout as list.
    TRANSFECTION_LAYOUT_PARAMETERS = None

    #: A list of numerical parameter values.
    _NUMERICAL_PARAMETERS = [IsoRequestParameters.ISO_VOLUME,
                             IsoRequestParameters.ISO_CONCENTRATION,
                             TransfectionParameters.FINAL_CONCENTRATION,
                             TransfectionParameters.REAGENT_DIL_FACTOR]


    def __init__(self, stream, requester, log):
        """
        Constructor:

        :param stream: The opened file to be parsed.

        :param requester: the user requesting the ISO
        :type requester: :class:`thelma.models.user.User`

        :param log: The ThelmaLog you want to write in.
        :type log: :class:`thelma.ThelmaLog`
        """
        MoleculeDesignPoolLayoutParserHandler.__init__(self, log=log,
                                                       stream=stream)

        #: The requester for the ISO request.
        self.requester = requester

        #: The transfection layout used to create the ISO rack layout
        self.transfection_layout = None

        #: If there is only one distinct floating position placeholder, this
        #: field will count the number of different floating wells (the numbers
        #: will serve as part of the placeholder).
        self._float_well_counter = 0


        #: Stores the molecule design pools for molecule design set IDs.
        self._pool_map = dict()
        # The molecule design pool aggregate
        # (see :class:`thelma.models.aggregates.Aggregate`)
        # used to obtain check the validity of molecule design pool IDs.
        self._pool_aggregate = get_root_aggregate(IMoleculeDesignPool)

        #: The tagged rack position sets for tags that are not part of the
        #: transfection layout mapped onto their rack position set hash values.
        self.__additional_trps = dict()
        #: The transfection layout as rack layout.
        self.__rack_layout = None

        #: The name of the transfection reagent (metadata value).
        self._reagent_name_metadata = None

        #: Stores distinct ISO concentration for screening cases.
        self._iso_concentrations = dict()

        # List for error collection.
        self._invalid_vol = []
        self._invalid_conc = []
        self._invalid_name = []
        self._invalid_df = []
        self._invalid_pool = []
        self._invalid_fconc = []
        self._has_volume_layout = False
        self._has_name_layout = False
        self._has_reagent_df_layout = False
        self._invalid_position_type = dict()

        # lookups for numerical values
        self.__invalid_lookup = {
            IsoRequestParameters.ISO_VOLUME : self._invalid_vol,
            IsoRequestParameters.ISO_CONCENTRATION : self._invalid_conc,
            TransfectionParameters.FINAL_CONCENTRATION : self._invalid_fconc,
            TransfectionParameters.REAGENT_DIL_FACTOR : self._invalid_df}
        self._metadata_lookup = {
            IsoRequestParameters.ISO_VOLUME : None,
            IsoRequestParameters.ISO_CONCENTRATION : None,
            TransfectionParameters.FINAL_CONCENTRATION : None,
            TransfectionParameters.REAGENT_DIL_FACTOR : None}

        #: Stores additional layout occurrence of parameters (that is invalid
        #: occurrences that have not been expected).
        self.__forbidden_add_tag_params = dict()
        #: Validators for the :attr:`__forbidden_add_tag_params`.
        self.__forbidden_add_tag_validators = dict()

        #: Stores the validators for all transfection layout parameters
        #: (used to identify additional tags).
        self.__all_validators = TransfectionParameters.create_all_validators()

        #: Must the ISO job be processed before the specific ISO (if there
        #: something do be done in the job - default: *True*)?
        self._process_job_first = True
        #: The rack sector association data (if there is one).
        self.__association_data = None

    @classmethod
    def create(cls, experiment_type_id, stream, requester, log):
        """
        Factory method creating a handler for the passed experiment type.
        """
        kw = dict(stream=stream, requester=requester, log=log)
        cls = _HANDLER_CLASSES[experiment_type_id]
        return cls(**kw)

    def get_transfection_layout(self):
        """
        Returns the transfection layout that has been used to create
        the ISO rack layout.

        :return: :class:`TransfectionLayout`
        """
        if self.has_errors() or not self.parsing_completed(): return None

        return self.transfection_layout

    def get_additional_trps(self):
        """
        Returns the additional tags that are not part of the transfection
        layout (mapped onto their rack positions sets).
        """
        if self.return_value is None: return None
        return self.__additional_trps

    def get_association_data(self):
        """
        Return the association data.
        """
        if self.return_value is None: return None
        return self.__association_data

    def has_iso_sheet(self):
        """
        Returns *True* if the parser could find an ISO sheet in the source file,
        and *False* if it did not find a sheet with a valid name. This
        distinction becomes important when deciding whether or not the
        superior tool shall try to extract an ISO request layout from the
        experiment design.
        """

        if self.parser.abort_parsing:
            return False
        else:
            return True

    def _initialize_parser_keys(self):
        """
        Initialises tag predicates and metadata keys within the parser
        (for screening scenarios).
        """
        MoleculeDesignPoolLayoutParserHandler._initialize_parser_keys(self)

        self.parser.molecule_design_parameter = \
                                    IsoRequestParameters.MOLECULE_DESIGN_POOL

        self.parser.layout_parameters = self.__get_layout_parameters()
        self.parser.optional_parameters = self.OPTIONAL_PARAMETERS
        self.parser.allowed_metadata = self.ALLOWED_METADATA
        self.parser.required_metadata = self.REQUIRED_METADATA

    def __get_layout_parameters(self):
        """
        Returns a map of parameters for ISO and transfection that might
        be specified by layouts (with their alias lists as values).
        """
        valid_parameters = {}
        for parameter in self.ISO_LAYOUT_PARAMETERS:
            if parameter == IsoRequestParameters.POS_TYPE: continue
            alias_list = IsoRequestParameters.get_all_alias(parameter)
            valid_parameters[parameter] = alias_list
        for parameter in self.TRANSFECTION_LAYOUT_PARAMETERS:
            alias_list = TransfectionParameters.get_all_alias(parameter)
            valid_parameters[parameter] = alias_list

        return valid_parameters

    def _convert_results_to_model_entity(self):
        """
        Retrieves an ISO request from an ISO sheet.
        """
        self.add_info('Start ISO request generation ... ')

        self.__check_input()
        if not self.has_errors(): self.__generate_transfection_layout()
        if not self.has_errors(): self.__store_other_tags()
        if not self.has_errors(): self.__create_iso_request()

    def __check_input(self):
        """
        Checks if the tool has got all information required to obtain
        the desired information.
        """
        self._check_input_class('requester', self.requester, User)

    def __generate_transfection_layout(self):
        """
        Generates the transfection layout.
        """
        self.add_debug('Generate transfection layout ...')

        self.__init_layout()
        if not self.has_errors():
            self.__fill_layout()
            self._record_errors()
            if FLOATING_POSITION_TYPE in self.ALLOWED_POSITION_TYPES:
                has_floatings = self.transfection_layout.has_floatings()
            else:
                has_floatings = False

        if not self.has_errors(): self._check_layout_validity(has_floatings)

        if not self.has_errors() and has_floatings: self._sort_floatings()

        if not self.has_errors():
            self.__rack_layout = self.transfection_layout.create_rack_layout()

    def __init_layout(self):
        """
        Initialises the transfection layout.
        """
        self._determine_rack_shape()
        if not self.has_errors():
            self.transfection_layout = TransfectionLayout(
                                                        shape=self._rack_shape)

    def __fill_layout(self):
        """
        Fills the transfection layout for screening scenarios.
        """
        self.add_debug('Fill layout ...')

        is_valid_metadata = self._get_metadata_values()
        if is_valid_metadata: self._create_positions()

    def _get_metadata_values(self):
        """
        Fetches and checks the values for the metadata.
        """
        self.add_debug('Check metadata ...')

        is_valid_metadata = True

        for parameter in self._NUMERICAL_PARAMETERS:
            if not self._check_numerical_parameter_metadata(parameter):
                is_valid_metadata = False

        reagent_name = None
        if self.parser.metadata_value_map.has_key(
                                        TransfectionParameters.REAGENT_NAME):
            reagent_name = self.parser.metadata_value_map[
                                            TransfectionParameters.REAGENT_NAME]
        if not reagent_name is None and \
                not self._is_valid_reagent_name(reagent_name, 'default value'):
            is_valid_metadata = False
        else:
            self._reagent_name_metadata = reagent_name

        return is_valid_metadata

    def _check_numerical_parameter_metadata(self, parameter):
        """
        Checks whether the given parameter has a valid metadata value.
        """
        metadata_value = self.parser.metadata_value_map[parameter]

        if parameter in self.REQUIRED_METADATA:
            may_be_none = False
        elif parameter in self.OPTIONAL_PARAMETERS:
            may_be_none = True
        else:
            container = self.parser.parameter_map[parameter]
            may_be_none = container.has_layout

        error_list = self.__invalid_lookup[parameter]
        if not self._is_valid_numerical(metadata_value, 'default value',
                                        may_be_none, error_list):
            return False
        elif (parameter == TransfectionParameters.REAGENT_DIL_FACTOR \
                        and not metadata_value is None and metadata_value < 1):
            self._invalid_df.append('default value')
            return False
        else:
            self._metadata_lookup[parameter] = metadata_value
            return True

    def _is_valid_numerical(self, value, pos_label, may_be_none, error_list):
        """
        Checks whether a value is a valid number and records an error, if
        applicable.
        """
        if value is None:
            if may_be_none: return True
            error_list.append(pos_label)
            return False

        if is_valid_number(value):
            return True
        else:
            error_list.append(pos_label)
            return False

    def _create_positions(self):
        """
        Creates the actual transfection positions for the layout.
        """
        raise NotImplementedError('Abstract method.')

    def _get_value_for_rack_pos(self, parameter_container, pos_label):
        """
        Retrieves the value of a parameter for a specified
        rack position.
        """
        if not parameter_container.well_map.has_key(pos_label):
            return None
        return parameter_container.well_map[pos_label]

    def _get_molecule_design_pool_for_id(self, pool_id, pos_label):
        """
        Returns the molecule design set or placeholder for a molecule design
        pool ID.
        """
        if pool_id is None: return None

        # fixed positions have pool IDs (integer)
        # we cannot use the get_position_type() function because this
        # expects pool entities and we only have pool IDs
        if is_valid_number(pool_id, positive=True, is_integer=True):
            if self._pool_map.has_key(pool_id): return self._pool_map[pool_id]
            pool = self._pool_aggregate.get_by_id(int(pool_id))
            if pool is None:
                info = '%s (%s)' % (get_trimmed_string(pool_id), pos_label)
                self._invalid_pool.append(info)
                return None
            self._pool_map[pool_id] = pool
            return pool

        # other position types can be identified by get_position_type()
        try:
            pos_type = TransfectionParameters.get_position_type(pool_id)
        except ValueError:
            info = '%s (%s)' % (pool_id, pos_label)
            self._invalid_pool.append(info)
            return None

        if not pos_type in self.ALLOWED_POSITION_TYPES:
            add_list_map_element(self._invalid_position_type, pos_type,
                                 pos_label)
            return None

        if pos_type == FLOATING_POSITION_TYPE:
            return pool_id
        else:
            return pos_type # is the same for mock and untreated

    def _is_valid_reagent_name(self, reagent_name, pos_label):
        """
        Checks whether a value is valid reagent name.
        """
        if reagent_name is None:
            self._invalid_name.append(pos_label)
            return False
        elif len(reagent_name) < 2:
            self._invalid_name.append(pos_label)
            return False

        return True

    def _get_numerical_parameter_value(self, parameter, pos_label, is_mock,
                                       is_untreated, may_be_none=False):
        """
        Returns the numerical parameter value for the given rack position.
        """
        container = self.parser.parameter_map[parameter]

        if not container.has_layout:
            if is_mock or is_untreated:
                return TransfectionPosition.NONE_REPLACER
            else:
                return self._metadata_lookup[parameter]

        value = self._get_value_for_rack_pos(container, pos_label)
        error_list = self.__invalid_lookup[parameter]

        if is_mock:
            if not TransfectionPosition.is_valid_mock_value(value):
                error_list.append(pos_label)
                return None
        elif is_untreated:
            if not TransfectionPosition.is_valid_untreated_value(value):
                error_list.append(pos_label)
                return None
        else:
            value = self._get_value_for_rack_pos(container, pos_label)
            if not self._is_valid_numerical(value, pos_label, may_be_none,
                                            error_list): return None
        return value

    def _get_final_concentration(self, pos_label, is_mock, is_untreated,
                                 may_be_none=None):
        """
        Helper function returning the final concentration for the given
        rack position.
        """
        parameter = TransfectionParameters.FINAL_CONCENTRATION
        return self._get_numerical_parameter_value(parameter, pos_label,
                                         is_mock, is_untreated, may_be_none)

    def _get_iso_concentration(self, pos_label, is_mock, is_untreated,
                               may_be_none=None):
        """
        Returns the ISO concentration for the given rack position.
        """
        iso_conc = self._get_numerical_parameter_value(
                IsoRequestParameters.ISO_CONCENTRATION, pos_label, is_mock,
                is_untreated, may_be_none)
        if iso_conc is None: return None

        if not self._iso_concentrations.has_key(iso_conc):
            self._iso_concentrations[iso_conc] = []
        self._iso_concentrations[iso_conc].append(pos_label)

        return iso_conc

    def _get_iso_volume(self, pos_label, is_mock, is_untreated,
                        may_be_none=None):
        """
        Helper function returning the ISO volume for the given rack position.
        """
        parameter = IsoRequestParameters.ISO_VOLUME
        return self._get_numerical_parameter_value(parameter, pos_label,
                                         is_mock, is_untreated, may_be_none)

    def _get_reagent_name(self, pos_label, is_untreated):
        """
        Returns the reagent name for the given rack position.
        """

        container = self.parser.parameter_map[
                                        TransfectionParameters.REAGENT_NAME]

        if not container.has_layout:
            if is_untreated:
                return TransfectionPosition.NONE_REPLACER
            else:
                return self._reagent_name_metadata

        reagent_name = self._get_value_for_rack_pos(container, pos_label)
        if is_untreated:
            if not TransfectionPosition.is_valid_untreated_value(reagent_name):
                self._invalid_name.append(pos_label)
                return None
        elif not self._is_valid_reagent_name(reagent_name, pos_label):
            return None

        return reagent_name

    def _record_errors(self):
        """
        Records the errors that have been collected during layout filling.
        """
        if not self.transfection_layout.\
                                has_consistent_volumes_and_concentrations():
            msg = 'There are positions in this ISO request layout that lack ' \
                  'either an ISO volume or an ISO concentration. If you set ' \
                  'a value for one position, you need to set it for all ' \
                  'other positions as well (exception: mock positions do not ' \
                  'need a concentration).'
            self.add_error(msg)

        if len(self._invalid_pool) > 0:
            msg = 'The following molecule design pools are unknown: %s.' \
                  % (self._get_joined_str(self._invalid_pool))
            self.add_error(msg)

        if len(self._invalid_vol) > 0:
            msg = 'Some positions in the ISO request layout have invalid ISO ' \
                  'volumes. The volume must be a positive number or left ' \
                  'blank. Untreated position may have a volume "None" or ' \
                  '"untreated". Affected positions: %s.' \
                  % (self._get_joined_str(self._invalid_vol))
            self.add_error(msg)

        if len(self._invalid_conc) > 0:
            msg = 'Some positions in the ISO request layout have invalid ISO ' \
                  'concentration. The concentration must be a positive ' \
                  'number or left blank. Mock and untreated positions may ' \
                  'have the values "None", "mock" and "untreated". Affected ' \
                  'positions: %s.' % (self._get_joined_str(self._invalid_conc))
            self.add_error(msg)

        if len(self._invalid_name) > 0:
            msg = 'Invalid or missing reagent name for the following rack ' \
                  'positions in the ISO request layout: %s. The reagent ' \
                  'name must have a length of at least 2! Untreated position ' \
                  'may have the values "None" or "untreated".' \
                   % (self._get_joined_str(self._invalid_name))
            self.add_error(msg)

        if len(self._invalid_df) > 0:
            msg = 'Invalid or missing reagent dilution factor for rack ' \
                  'positions in the ISO request layout: %s. The dilution ' \
                  'factor must be 1 or larger! Untreated position may have ' \
                  'the values "None" or "untreated".' \
                  % (self._get_joined_str(self._invalid_df))
            self.add_error(msg)

        if len(self._invalid_fconc) > 0:
            msg = 'Invalid final concentration for the following rack ' \
                  'positions in the ISO request layout: %s. The final ' \
                  'concentration must be a positive number! Mock and ' \
                  'untreated positions may have the values "None", "mock", ' \
                  '"untreated" or "untransfected" or no value.' \
                  % (self._get_joined_str(self._invalid_fconc))
            self.add_error(msg)

        if len(self._invalid_position_type) > 0:
            type_positions = []
            for pos_type, positions in self._invalid_position_type.iteritems():
                pos_type_str = '%s (%s)' % (pos_type,
                                           self._get_joined_str(positions))
                type_positions.append(pos_type_str)
            msg = 'The following position types are not allowed in the ISO ' \
                  'request layout for this experiment metadata type (%s): %s.' \
                  % (get_experiment_metadata_type(self.SUPPORTED_SCENARIO).\
                    display_name, self._get_joined_str(type_positions,
                                                       separator=' -- '))
            self.add_error(msg)

    def _check_layout_validity(self, has_floatings): #pylint: disable=W0613
        """
        Checks scenario-dependent properties of the transfection layout.
        """
        self.__check_iso_concentration()

    def __check_iso_concentration(self):
        """
        Checks whether the ISO concentration is equal or larger than the stock
        concentration.
        """
        has_controls = False
        equals_stock_concentration = []
        larger_than_stock_concentration = []

        for rack_pos, tf_pos in self.transfection_layout.iterpositions():
            if not tf_pos.is_fixed: continue
            has_controls = True
            iso_conc = tf_pos.iso_concentration
            if iso_conc is None: continue
            stock_conc = tf_pos.stock_concentration

            if is_larger_than(iso_conc, stock_conc):
                larger_than_stock_concentration.append(rack_pos.label)
            elif are_equal_values(iso_conc, stock_conc):
                equals_stock_concentration.append(rack_pos.label)

        if len(larger_than_stock_concentration) > 0:
            larger_than_stock_concentration.sort()
            msg = 'Some concentrations you have ordered are larger than ' \
                  'the stock concentration for that molecule type ' \
                  '(%s nM): %s.' % (get_trimmed_string(stock_conc),
                  self._get_joined_str(larger_than_stock_concentration))
            self.add_error(msg)

        if not has_controls:
            msg = 'There are no fixed positions in this ISO request layout!'
            self.add_error(msg)

    def _check_for_unrequired_untreated_positions(self):
        """
        Technically, untreated position are empty, they contain just cells.
        The distinction serves documentational reasons only and is only
        required in the experiment design. Thus, experiment metadata types
        that provide separate *Transfection* and *ISO* sheets do not need
        to mark untreated positions in the ISO request layout. On the contrary,
        marking them might mislead to the assumption that there was a transfer
        connection between the ISO and experiment wells.
        """
        has_untreated = False
        for tf_pos in self.transfection_layout.working_positions():
            if tf_pos.is_untreated_type:
                has_untreated = True
                break
        if has_untreated:
            msg = 'There are untreated positions in your ISO request layout! ' \
                  'You do not need to mark them here, because the system ' \
                  'considers them to be empty and will not transfer them ' \
                  'to the experiment cell plates!'
            self.add_warning(msg)

    def _sort_floatings(self):
        """
        In 96-well layouts the sorting is done by position. 384-well layouts
        must comply to rack sectors. Sorting then is done by rack sector.
        Assumes that we have floatings in the first place.
        """
        if self.transfection_layout.shape.name == RACK_SHAPE_NAMES.SHAPE_96:
            self._sort_floatings_by_position()
        else:
            self.__association_data = self.__get_association_data()


            if not self.__association_data is None:
                if self.__association_data.number_sectors == 4:
                    associated_sectors = self.__association_data.\
                                         associated_sectors
                    self.__adjust_floatings_for_concentrations(
                                                            associated_sectors)
                else:
                    self._sort_floatings_by_position()

    def _sort_floatings_by_position(self):
        """
        Sorts the floatings placeholders by position.
        """
        old_new_map = dict()

        counter = 0
        for tf_pos in self.transfection_layout.get_sorted_working_positions():
            if not tf_pos.is_floating: continue
            old_placeholder = tf_pos.molecule_design_pool
            if not old_new_map.has_key(old_placeholder):
                counter += 1
                new_placeholder = '%s%03i' % (IsoRequestParameters.FLOATING_INDICATOR,
                                              counter)
                old_new_map[old_placeholder] = new_placeholder
            else:
                new_placeholder = old_new_map[old_placeholder]
            tf_pos.molecule_design_pool = new_placeholder

    def __get_association_data(self):
        """
        The association data always covers floating positions but might
        cover fixed positions, too. Assumes a 384-well layout.
        """
        association_data, regard_controls = TransfectionAssociationData.find(
                                log=self.log, layout=self.transfection_layout)
        if association_data is None:
            msg = 'Error when trying to associated rack sectors!'
            self.add_error(msg)
            return None
        elif self.__has_consistent_final_concentration(association_data):
            self._process_job_first = regard_controls
            return association_data
        else:
            return None

    def __has_consistent_final_concentration(self, association_data):
        """
        Checks whether each ISO concentration has a distinct final
        concentration.
        """
        iso_concentrations = association_data.iso_concentrations

        iso_conc_map = dict()
        final_conc_map = dict()
        invalid_concentrations = []
        for sector_index, final_conc in association_data.sector_concentrations.\
                                      iteritems():
            if final_conc is None: continue
            iso_conc = iso_concentrations[sector_index]
            if iso_conc is None: continue

            if iso_conc_map.has_key(iso_conc):
                fc = iso_conc_map[iso_conc]
                if not are_equal_values(fc, final_conc):
                    info = 'ISO %.1f nM (final concentrations: %1.f nM and ' \
                           '%.1f nM)' % (iso_conc, fc, final_conc)
                    invalid_concentrations.append(info)
            else:
                iso_conc_map[iso_conc] = final_conc

            if final_conc_map.has_key(final_conc):
                ic = final_conc_map[final_conc]
                if not are_equal_values(ic, iso_conc):
                    info = 'final %.1f nM (ISO concentrations: %1.f nM and ' \
                           '%.1f nM)' % (final_conc, ic, iso_conc)
                    invalid_concentrations.append(info)
            else:
                final_conc_map[final_conc] = iso_conc

        if len(invalid_concentrations) > 0:
            msg = 'Some final concentrations in the screening layout are ' \
                  'related to more than one ISO concentration or vice versa: ' \
                  '%s.' % (invalid_concentrations)
            self.add_error(msg)
            return False

        return True

    def __adjust_floatings_for_concentrations(self, associated_sectors):
        """
        Adjust the floating positions in case of multiple concentrations.
        """
        associated_sectors.sort()
        quadrant_iterator = QuadrantIterator(number_sectors=4)

        consistent_concentrations = True
        final_concentrations = None

        counter = 0

        for quadrant_positions in quadrant_iterator.get_all_quadrants(
                                    working_layout=self.transfection_layout):
            for sectors in associated_sectors:
                new_placeholder = None
                concentrations = set()
                for sector_index in sectors:
                    tf_pos = quadrant_positions[sector_index]
                    if tf_pos is None: continue
                    if not tf_pos.is_floating: continue
                    if new_placeholder is None:
                        counter += 1
                        new_placeholder = '%s%03i' % (
                               IsoRequestParameters.FLOATING_INDICATOR, counter)
                    tf_pos.molecule_design_pool = new_placeholder
                    concentrations.add(tf_pos.final_concentration)

                # Check whether all final concentrations are found.
                if len(concentrations) < 1: continue
                if final_concentrations is None:
                    final_concentrations = concentrations
                    continue

                if not len(final_concentrations) == len(concentrations):
                    consistent_concentrations = False
                    break

                for final_conc in concentrations:
                    if not final_conc in final_concentrations:
                        consistent_concentrations = False
                        break

        if not consistent_concentrations:
            msg = 'The concentrations within the ISO request layout are not ' \
                  'consistent. Some sample positions have more or different ' \
                  'concentrations than others. Please regard, that the  ' \
                  'different concentrations for a molecule design pool must ' \
                  'be located in the same rack sector and that the ' \
                  'diestribution of concentrations must be the same for all ' \
                  'quadrants. If you have questions, ask Anna, please.'
            self.add_error(msg)


    def __create_iso_request(self):
        """
        Creates the IsoRequest object used as output value.
        """

        self.add_info('Create ISO request ...')

        metadata_value_map = self.parser.metadata_value_map
        number_aliquots = self._get_number_aliquots(metadata_value_map)
        label = self.__get_iso_request_label(metadata_value_map,
                                             number_aliquots)
        comment = metadata_value_map[self.COMMENT_KEY]
        delivery_date = self.__get_date(metadata_value_map)

        if self.has_errors(): return None

        iso_request = LabIsoRequest(label=label,
                    requester=self.requester,
                    rack_layout=self.__rack_layout,
                    delivery_date=delivery_date,
                    comment=comment,
                    process_job_first=self._process_job_first,
                    number_aliquots=number_aliquots)

        if not self.has_errors():
            self.return_value = iso_request
            self.add_info('ISO request creating complete.')

    def _get_number_aliquots(self, metadata_value_map): #pylint: disable=W0613
        """
        Obtains the number of aliquots. It is 1 by default, except for
        screening cases.
        """
        return 1

    def __get_iso_request_label(self, metadata_value_map, number_aliquots):
        """
        Obtains and checks the plate set label (if there is one specified -
        otherwise the :class:`NO_LABEL_PLACEHOLDER` is returned).
        """
        self.add_debug('Obtain plate set label ...')

        plate_set_label = metadata_value_map[self.PLATE_SET_LABEL_KEY]
        if plate_set_label is None: return self.NO_LABEL_PLACEHOLDER
        plate_set_label = plate_set_label.replace(' ', '_')

        max_len = self.__get_max_iso_request_label_length(number_aliquots)
        if len(plate_set_label) > max_len:
            msg = 'The maximum length for plate set labels is %i characters ' \
                  '(obtained: "%s", %i characters).' \
                   % (max_len, plate_set_label, len(plate_set_label))
            self.add_error(msg)

        return plate_set_label

    def __get_max_iso_request_label_length(self, number_aliquots):
        """
        If there is only one final plate at maximum, we can exploit the whole
        length of the label printer. Otherwise we need to reserve 3 characters
        (2 plus a separator) for the ISO number and 2 (1 plus one separator)
        for the aliquot number if aliquots need to be distinguised.
        """
        if self.SUPPORTED_SCENARIO in EXPERIMENT_SCENARIOS.ONE_PLATE_TYPES:
            return MAX_PLATE_LABEL_LENGTH
        max_len = MAX_PLATE_LABEL_LENGTH - 3 # ISO num
        if number_aliquots > 1: max_len -= 2 # aliquot num
        return max_len

    def __get_date(self, metadata_value_map):
        """
        Obtains the delivery date (if applicable).
        """

        self.add_debug('Obtain delivery date ...')
        date_string = metadata_value_map[self.DELIVERY_DATE_KEY]
        if date_string == None: return None
        if not isinstance(date_string, basestring):
            msg = 'The delivery date has could not be encoded because ' \
                  'Excel has delivered an unexpected format. Make sure the ' \
                  'cell is formatted as "text" and reload the file or adjust ' \
                  'the delivery date manually after upload, please.'
            self.add_warning(msg)
            return None

        if date_string.lower() == 'dd.MM.yyyy'.lower(): return None

        if len(date_string.split(self.DATE_SEPARATOR)) != 3:
            msg = 'Cannot read the delivery date. Please use the ' \
                  'following date format: dd.MM.yyyy'
            self.add_error(msg)
            return None
        year = int(date_string.split(self.DATE_SEPARATOR)[2])
        month = int(date_string.split(self.DATE_SEPARATOR)[1])
        day = int(date_string.split(self.DATE_SEPARATOR)[0])
        delivery_date = date(year, month, day)
        return delivery_date

    def __store_other_tags(self):
        """
        Stores non-parameter tags to the ISO request layout. The tags are added
        later after the transfection layout has been completed.
        """
        self.add_debug('Store additional tags ...')

        self.__init_forbidden_parameters_maps()

        for layout_container in self.parser.layout_map.values():
            for tag_container, pos_containers in \
                                        layout_container.tag_data.iteritems():
                pos_set = self._convert_to_rack_position_set(pos_containers)
                hash_value = pos_set.hash_value
                tag = self._convert_to_tag(tag_container)
                self._check_for_invalid_layout_tag(tag)
                if self.__additional_trps.has_key(hash_value):
                    trps = self.__additional_trps[hash_value]
                    trps.add_tag(tag, self.requester)
                else:
                    trps = TaggedRackPositionSet(set([tag]), pos_set,
                                                 self.requester)
                    self.__additional_trps[hash_value] = trps

        self.__record_invalid_layout_tags_errors()

    def __init_forbidden_parameters_maps(self):
        """
        ISO and transfection parameters must not occur in the additional
        tags (valid occurrences have already been removed from the found tags
        before).
        """
        for parameter in IsoRequestParameters.ALL:
            self.__forbidden_add_tag_params[parameter] = False
            validator = IsoRequestParameters.create_validator_from_parameter(parameter)
            self.__forbidden_add_tag_validators[parameter] = validator

        for parameter in TransfectionParameters.ALL:
            if parameter in IsoRequestParameters.ALL: continue
            self.__forbidden_add_tag_params[parameter] = False
            validator = TransfectionParameters.create_validator_from_parameter(
                                                                     parameter)
            self.__forbidden_add_tag_validators[parameter] = validator

    def _check_for_invalid_layout_tag(self, tag):
        """
        Checks whether there are layout specification tags for parameters
        that might only be defined via metadata.
        """
        predicate = tag.predicate
        for parameter, validator in self.__forbidden_add_tag_validators.\
                                                            iteritems():
            if validator.has_alias(predicate):
                self.__forbidden_add_tag_params[parameter] = True
                break

    def __record_invalid_layout_tags_errors(self):
        """
        Records the errors for invalid layout tags.
        """

        found_parameters = []
        for parameter, is_present in \
                                self.__forbidden_add_tag_params.iteritems():
            if is_present: found_parameters.append(parameter.replace('_', ' '))

        if len(found_parameters) > 0:
            em_type = get_experiment_metadata_type(self.SUPPORTED_SCENARIO)
            msg = 'Some factors must not be specified as layouts, because ' \
                  'there might only be one value for the whole layout (use ' \
                  'the metadata specification in this case) or no value at ' \
                  'all (current experiment type: %s). Invalid factors ' \
                  'found: %s.' % (em_type.display_name,
                                  self._get_joined_str(found_parameters))
            self.add_error(msg)


class IsoRequestParserHandlerOpti(IsoRequestParserHandler):
    """
    A IsoRequestParserHandler for optimisation experiments.

    **Return Value:** ISO request (:class:`thelma.models.iso.IsoRequest`).
    """
    SUPPORTED_SCENARIO = EXPERIMENT_SCENARIOS.OPTIMISATION

    OPTIONAL_PARAMETERS = [IsoRequestParameters.ISO_VOLUME,
                           IsoRequestParameters.ISO_CONCENTRATION,
                           TransfectionParameters.FINAL_CONCENTRATION]
    REQUIRED_METADATA = [IsoRequestParserHandler.PLATE_SET_LABEL_KEY]

    ISO_LAYOUT_PARAMETERS = IsoRequestParameters.ALL
    TRANSFECTION_LAYOUT_PARAMETERS = [
                            TransfectionParameters.FINAL_CONCENTRATION,
                            TransfectionParameters.REAGENT_NAME,
                            TransfectionParameters.REAGENT_DIL_FACTOR]

    def _create_positions(self):
        self.add_debug('Create transfection positions ...')

        parameter_map = self.parser.parameter_map
        pool_container = parameter_map[IsoRequestParameters.MOLECULE_DESIGN_POOL]

        for pos_container in self.parser.shape.position_containers:
            pos_label = pos_container.label

            # Check properties
            pool_id = self._get_value_for_rack_pos(pool_container, pos_label)
            pool = self._get_molecule_design_pool_for_id(pool_id, pos_label)
            if pool is None: continue

            is_mock = (pool == MOCK_POSITION_TYPE)
            is_untreated = TransfectionParameters.is_untreated_type(pool)

            iso_volume = self._get_iso_volume(pos_label, False, is_untreated,
                                              True)
            iso_conc = self._get_iso_concentration(pos_label, is_mock,
                                                   is_untreated, True)
            final_conc = self._get_final_concentration(pos_label, is_mock,
                                                       is_untreated, True)

            reagent_name = self._get_reagent_name(pos_label, is_untreated)
            reagent_df = self.__get_reagent_df(pos_label, is_untreated)

            # Create position
            rack_pos = self._convert_to_rack_position(pos_container)
            tf_pos = TransfectionPosition(rack_position=rack_pos,
                            molecule_design_pool=pool, iso_volume=iso_volume,
                            iso_concentration=iso_conc,
                            reagent_name=reagent_name,
                            reagent_dil_factor=reagent_df,
                            final_concentration=final_conc)
            self.transfection_layout.add_position(tf_pos)

    def __get_reagent_df(self, pos_label, is_untreated):
        """
        Helper function returning the reagent dilution factor for the given
        rack position.
        """
        parameter = TransfectionParameters.REAGENT_DIL_FACTOR
        rdf = self._get_numerical_parameter_value(parameter, pos_label, False,
                                                  is_untreated)
        if rdf is None:
            return None
        elif rdf < 1:
            self._invalid_df.append(pos_label)
            return None
        else:
            return rdf

    def _check_layout_validity(self, has_floatings):
        """
        Checks scenario-dependent properties of the transfection layout.
        """
        IsoRequestParserHandler._check_layout_validity(self, has_floatings)
        self._check_for_unrequired_untreated_positions()


class IsoRequestParserHandlerScreen(IsoRequestParserHandler):
    """
    A IsoRequestParserHandler for screening experiments.

    **Return Value:** ISO request (:class:`thelma.models.iso.IsoRequest`).
    """
    SUPPORTED_SCENARIO = EXPERIMENT_SCENARIOS.SCREENING

    OPTIONAL_PARAMETERS = [IsoRequestParameters.ISO_CONCENTRATION,
                           IsoRequestParameters.ISO_VOLUME]
    REQUIRED_METADATA = [IsoRequestParserHandler.PLATE_SET_LABEL_KEY,
                         IsoRequestParserHandler.NUMBER_ALIQUOT_KEY,
                         TransfectionParameters.REAGENT_NAME,
                         TransfectionParameters.REAGENT_DIL_FACTOR]

    ISO_LAYOUT_PARAMETERS = [IsoRequestParameters.MOLECULE_DESIGN_POOL,
                             IsoRequestParameters.ISO_CONCENTRATION]
    TRANSFECTION_LAYOUT_PARAMETERS = [
                                    TransfectionParameters.FINAL_CONCENTRATION]

    def __init__(self, stream, requester, log):
        """
        Constructor:

        :param stream: The opened file to be parsed.

        :param requester: the user requesting the ISO
        :type requester: :class:`thelma.models.user.User`

        :param log: The ThelmaLog you want to write in.
        :type log: :class:`thelma.ThelmaLog`
        """
        IsoRequestParserHandler.__init__(self, stream=stream, log=log,
                                         requester=requester)

        #: The rack sector association data.
        self.__association_data = None

    def get_association_data(self):
        """
        Return the association data.
        """
        if self.return_value is None: return None
        return self.__association_data

    def get_iso_volume(self):
        """
        Returns the ISO volume from the sheet (there is only a metadata value).
        """
        if self.return_value is None: return None
        return self._metadata_lookup[IsoRequestParameters.ISO_VOLUME]

    def _create_positions(self):
        self.add_debug('Create transfection positions ...')

        parameter_map = self.parser.parameter_map
        pool_container = parameter_map[IsoRequestParameters.MOLECULE_DESIGN_POOL]
        iso_volume = self._metadata_lookup[IsoRequestParameters.ISO_VOLUME]
        reagent_df = self._metadata_lookup[
                                    TransfectionParameters.REAGENT_DIL_FACTOR]

        for pos_container in self.parser.shape.position_containers:
            pos_label = pos_container.label
            is_valid_position = True

            # Check properties
            pool_id = self._get_value_for_rack_pos(pool_container, pos_label)
            pool = self._get_molecule_design_pool_for_id(pool_id, pos_label)
            if pool is None: continue
            is_mock = (pool == MOCK_POSITION_TYPE)
            is_untreated = TransfectionParameters.is_untreated_type(pool)

            final_conc = self._get_final_concentration(pos_label, is_mock,
                                                       is_untreated)
            if final_conc is None and not (is_mock or is_untreated):
                is_valid_position = False
            iso_conc = self._get_iso_concentration(pos_label, is_mock,
                                                   is_untreated, True)
            if (is_mock or is_untreated):
                pass
            elif iso_conc is None and final_conc is None:
                is_valid_position = False

            if not is_valid_position: continue

            rack_pos = self._convert_to_rack_position(pos_container)
            if is_untreated:
                pos_type = pool
                tf_pos = TransfectionPosition.create_untreated_position(
                          rack_position=rack_pos,
                          position_type=pos_type)
            else:
                tf_pos = TransfectionPosition(rack_position=rack_pos,
                          molecule_design_pool=pool,
                          iso_volume=iso_volume,
                          iso_concentration=iso_conc,
                          final_concentration=final_conc,
                          reagent_name=self._reagent_name_metadata,
                          reagent_dil_factor=reagent_df)
            self.transfection_layout.add_position(tf_pos)

    def _get_number_aliquots(self, metadata_value_map):
        """
        Obtains the number of aliquots for screening cases (or the default
        value for optimisations).
        """
        number_aliquots = metadata_value_map[self.NUMBER_ALIQUOT_KEY]
        if not is_valid_number(number_aliquots, is_integer=True):
            msg = 'The number of aliquots must be a positive integer ' \
                  '(obtained: %s).' % (number_aliquots)
            self.add_error(msg)
            return None
        else:
            return int(number_aliquots)


class IsoRequestParserHandlerLibrary(IsoRequestParserHandler):
    """
    A IsoRequestParserHandler for library screening experiments.

    **Return Value:** ISO request (:class:`thelma.models.iso.IsoRequest`).
    """
    SUPPORTED_SCENARIO = EXPERIMENT_SCENARIOS.LIBRARY

    OPTIONAL_PARAMETERS = []
    REQUIRED_METADATA = [IsoRequestParserHandler.LIBRARY_KEY,
                         TransfectionParameters.FINAL_CONCENTRATION,
                         TransfectionParameters.REAGENT_NAME,
                         TransfectionParameters.REAGENT_DIL_FACTOR]

    ISO_LAYOUT_PARAMETERS = [IsoRequestParameters.MOLECULE_DESIGN_POOL]
    TRANSFECTION_LAYOUT_PARAMETERS = []

    ALLOWED_METADATA = [IsoRequestParserHandler.PLATE_SET_LABEL_KEY,
                        IsoRequestParserHandler.DELIVERY_DATE_KEY,
                        IsoRequestParserHandler.COMMENT_KEY,
                        IsoRequestParserHandler.LIBRARY_KEY,
                        TransfectionParameters.FINAL_CONCENTRATION,
                        TransfectionParameters.REAGENT_NAME,
                        TransfectionParameters.REAGENT_DIL_FACTOR]

    _NUMERICAL_PARAMETERS = [TransfectionParameters.FINAL_CONCENTRATION,
                             TransfectionParameters.REAGENT_DIL_FACTOR]

    def __init__(self, stream, requester, log):
        """
        Constructor:

        :param stream: The opened file to be parsed.

        :param requester: the user requesting the ISO
        :type requester: :class:`thelma.models.user.User`

        :param log: The ThelmaLog you want to write in.
        :type log: :class:`thelma.ThelmaLog`
        """
        IsoRequestParserHandler.__init__(self, stream=stream, log=log,
                                         requester=requester)

        #: The molecule design library used
        #: (:class:`thelma.models.library.MoleculeDesignLibrary`)
        self.__library = None
        #: Contains the sample positions blocked by the library.
        self.__lib_base_layout = None

    def reset(self):
        IsoRequestParserHandler.reset(self)
        self.__library = None
        self.__lib_base_layout = None

    def get_library(self):
        """
        Returns the specified molecule design library.
        """
        if self.return_value is None: return None
        return self.__library

    def get_final_concentration(self):
        """
        Returns the final concentration for the experiment cell plates.
        """
        if self.return_value is None: return None
        return self._metadata_lookup[TransfectionParameters.FINAL_CONCENTRATION]

    def get_reagent_name(self):
        """
        Returns the name of the transfection reagent to be used.
        """
        return self._get_additional_value(self._reagent_name_metadata)

    def get_reagent_dil_factor(self):
        """
        Returns the final transfection reagent dilution factor.
        """

        return self._get_additional_value(self._metadata_lookup[
                                    TransfectionParameters.REAGENT_DIL_FACTOR])

    def _get_metadata_values(self):
        """
        We need to fetch the library here.
        """
        is_valid_metadata = IsoRequestParserHandler._get_metadata_values(self)

        lib_name = self.parser.metadata_value_map[self.LIBRARY_KEY]
        lib_agg = get_root_aggregate(IMoleculeDesignLibrary)
        self.__library = lib_agg.get_by_slug(lib_name)
        if self.__library is None:
            msg = 'Unknown library "%s".' % (lib_name)
            self.add_error(msg)
            is_valid_metadata = False
        else:
            self.__fetch_library_base_layout()
            if self.__lib_base_layout is None: is_valid_metadata = False

        return is_valid_metadata

    def __fetch_library_base_layout(self):
        """
        Converts the base layout of the library (defines which positions
        must contain samples and which are allowed to take up other
        ISO request position types).
        """
        converter = LibraryLayoutConverter(log=self.log,
                    rack_layout=self.__library.rack_layout)
        self.__lib_base_layout = converter.get_result()

        if self.__lib_base_layout is None:
            msg = 'Unable to convert library base layout.'
            self.add_error(msg)
        elif not self.__lib_base_layout.shape == self._rack_shape:
            msg = 'Library "%s" requires a %s layout. You have provided a %s ' \
                  'layout.' % (self.__library.label,
                  self.__lib_base_layout.shape.name, self._rack_shape.name)
            self.add_error(msg)

    def _create_positions(self):
        """
        ISO volume and concentration are added later by the robot support
        determiner.
        """
        self.add_debug('Create transfection positions ...')

        parameter_map = self.parser.parameter_map
        pool_container = parameter_map[
                                    IsoRequestParameters.MOLECULE_DESIGN_POOL]
        final_conc = self._metadata_lookup[
                                    TransfectionParameters.FINAL_CONCENTRATION]
        reagent_df = self._metadata_lookup[
                                    TransfectionParameters.REAGENT_DIL_FACTOR]

        for pos_container in self.parser.shape.position_containers:
            pos_label = pos_container.label

            # Check properties
            pool_id = self._get_value_for_rack_pos(pool_container, pos_label)
            pool = self._get_molecule_design_pool_for_id(pool_id, pos_label)
            if pool is None: continue # error

            rack_pos = self._convert_to_rack_position(pos_container)
            if TransfectionParameters.is_untreated_type(pool):
                tf_pos = TransfectionPosition.create_untreated_position(
                          rack_position=rack_pos, position_type=pool)
            elif pool == MOCK_POSITION_TYPE:
                tf_pos = TransfectionPosition.create_mock_position(
                          rack_position=rack_pos)
            elif pool == LIBRARY_POSITION_TYPE:
                tf_pos = TransfectionPosition.create_library_position(
                          rack_position=rack_pos)
            else:
                tf_pos = TransfectionPosition(rack_position=rack_pos,
                          molecule_design_pool=pool)
            self.transfection_layout.add_position(tf_pos)

        for tp in self.transfection_layout.working_positions():
            if tp.is_empty:
                continue
            else:
                if tp.is_mock:
                    tp.final_concentration = MOCK_POSITION_TYPE
                else:
                    tp.final_concentration = final_conc
                tp.reagent_name = self._reagent_name_metadata
                tp.reagent_dil_factor = reagent_df

    def _check_layout_validity(self, has_floatings): #pylint: disable=W0613
        """
        We do not need to check the ISO concentration, since this is set
        by the library. Instead, we need to make sure that all library
        positions are set correctly (and non-library positions
        are not taken by library positions) and that there is at least one
        control (fixed position).
        """
        library_positions = set([self.__lib_base_layout.get_positions()])
        missing_library_pos = []
        invalid_library_pos = []

        has_controls = False
        for rack_pos in get_positions_for_shape(self.transfection_layout.shape):
            pos_in_base_layout = (rack_pos in library_positions)
            tf_pos = self.transfection_layout.get_working_position(rack_pos)
            if tf_pos is None:
                is_library = False
            else:
                is_library = tf_pos.is_library
                if tf_pos.is_fixed: has_controls = True
            if not pos_in_base_layout and is_library:
                invalid_library_pos.append(rack_pos.label)
            elif pos_in_base_layout and not is_library:
                missing_library_pos.append(rack_pos.label)

        if not has_controls:
            msg = 'There are no fixed positions in this ISO reuqest layout!'
            self.add_error(msg)

        if len(missing_library_pos) > 0:
            msg = 'The following positions are reserved for library samples: ' \
                  '%s. You have assigned a different position type to them.' \
                  % (self._get_joined_str(missing_library_pos))
            self.add_error(msg)

        if len(invalid_library_pos) > 0:
            msg = 'The following positions must not be samples: %s.' \
                  % (self._get_joined_str(invalid_library_pos))
            self.add_error(msg)


class IsoRequestParserHandlerManual(IsoRequestParserHandler):
    """
    A IsoRequestParserHandler for manual optimisation experiments.
    There are no transfection values in the layout. Only fixed positions
    are allowed but besides there are no restrictions to the layout.

    **Return Value:** ISO request (:class:`thelma.models.iso.IsoRequest`).
    """
    SUPPORTED_SCENARIO = EXPERIMENT_SCENARIOS.MANUAL

    OPTIONAL_PARAMETERS = []
    REQUIRED_METADATA = [IsoRequestParserHandler.PLATE_SET_LABEL_KEY]
    ALLOWED_METADATA = [IsoRequestParserHandler.PLATE_SET_LABEL_KEY,
                        IsoRequestParserHandler.DELIVERY_DATE_KEY,
                        IsoRequestParserHandler.COMMENT_KEY,
                        IsoRequestParameters.ISO_CONCENTRATION,
                        IsoRequestParameters.ISO_VOLUME]

    ALLOWED_POSITION_TYPES = [FIXED_POSITION_TYPE, EMPTY_POSITION_TYPE]

    ISO_LAYOUT_PARAMETERS = IsoRequestParameters.ALL
    TRANSFECTION_LAYOUT_PARAMETERS = []

    #: A list of numerical parameter values.
    _NUMERICAL_PARAMETERS = [IsoRequestParameters.ISO_VOLUME,
                             IsoRequestParameters.ISO_CONCENTRATION]

    def _create_positions(self):
        """
        Only molecule design pools can be specified via layout.
        """
        self.add_debug('Create transfection positions ...')

        parameter_map = self.parser.parameter_map
        pool_container = parameter_map[
                                    IsoRequestParameters.MOLECULE_DESIGN_POOL]

        for pos_container in self.parser.shape.position_containers:
            pos_label = pos_container.label

            # Check properties
            pool_id = self._get_value_for_rack_pos(pool_container, pos_label)
            pool = self._get_molecule_design_pool_for_id(pool_id, pos_label)
            if pool is None: continue

            iso_volume = self._get_iso_volume(pos_label, False, False, False)
            iso_conc = self._get_iso_concentration(pos_label, False, False,
                                                   False)

            # Create position
            rack_pos = self._convert_to_rack_position(pos_container)
            tf_pos = TransfectionPosition(rack_position=rack_pos,
                            molecule_design_pool=pool, iso_volume=iso_volume,
                            iso_concentration=iso_conc)
            self.transfection_layout.add_position(tf_pos)


class IsoRequestParserHandlerOrder(IsoRequestParserHandler):
    """
    A IsoRequestParserHandler for orders without experiment.
    These transfection layouts only contains pools and volumes. All
    pools are ordered in stock concentration and may occur only once
    per layout.

    **Return Value:** ISO request (:class:`thelma.models.iso.IsoRequest`).
    """
    SUPPORTED_SCENARIO = EXPERIMENT_SCENARIOS.ORDER_ONLY

    ALLOWED_POSITION_TYPES = [FIXED_POSITION_TYPE, EMPTY_POSITION_TYPE]

    ALLOWED_METADATA = [IsoRequestParserHandler.PLATE_SET_LABEL_KEY,
                        IsoRequestParserHandler.DELIVERY_DATE_KEY,
                        IsoRequestParserHandler.COMMENT_KEY,
                        IsoRequestParameters.ISO_VOLUME]
    OPTIONAL_PARAMETERS = []
    REQUIRED_METADATA = [IsoRequestParserHandler.PLATE_SET_LABEL_KEY]

    ISO_LAYOUT_PARAMETERS = [IsoRequestParameters.MOLECULE_DESIGN_POOL,
                             IsoRequestParameters.ISO_VOLUME]
    TRANSFECTION_LAYOUT_PARAMETERS = []

    _NUMERICAL_PARAMETERS = [IsoRequestParameters.ISO_VOLUME]

    def _create_positions(self):
        """
        Only molecule design pools can be specified via layout.
        """
        self.add_debug('Create transfection positions ...')

        parameter_map = self.parser.parameter_map
        pool_container = parameter_map[
                                    IsoRequestParameters.MOLECULE_DESIGN_POOL]

        for pos_container in self.parser.shape.position_containers:
            pos_label = pos_container.label

            # Check properties
            pool_id = self._get_value_for_rack_pos(pool_container, pos_label)
            pool = self._get_molecule_design_pool_for_id(pool_id, pos_label)
            if pool is None: continue

            iso_volume = self._get_iso_volume(pos_label, False, False, False)

            # Create position
            rack_pos = self._convert_to_rack_position(pos_container)
            tf_pos = TransfectionPosition(rack_position=rack_pos,
                            molecule_design_pool=pool, iso_volume=iso_volume)
            self.transfection_layout.add_position(tf_pos)

    def _check_layout_validity(self, has_floatings):
        """
        Each pool may occur only once. Only fixed positions are allowed.
        """
        IsoRequestParserHandler._check_layout_validity(self, has_floatings)

        count_map = dict()
        for tf_pos in self.transfection_layout.working_positions():
            pool_id = tf_pos.molecule_design_pool.id
            if not count_map.has_key(pool_id): count_map[pool_id] = 0
            count_map[pool_id] += 1

        more_than_one = []
        for pool_id, pool_count in count_map.iteritems():
            if pool_count > 1: more_than_one.append(pool_id)
        if len(more_than_one) > 0:
            msg = 'In an ISO request without experiment, each molecule ' \
                  'design pool may occur only once. The following pools ' \
                  'occur several times: %s.' \
                  % (self._get_joined_str(more_than_one, is_strs=False))
            self.add_error(msg)


#: Lookup storing the handler classes for each experiment type.
_HANDLER_CLASSES = {
            EXPERIMENT_SCENARIOS.OPTIMISATION : IsoRequestParserHandlerOpti,
            EXPERIMENT_SCENARIOS.SCREENING : IsoRequestParserHandlerScreen,
            EXPERIMENT_SCENARIOS.LIBRARY : IsoRequestParserHandlerLibrary,
            EXPERIMENT_SCENARIOS.MANUAL : IsoRequestParserHandlerManual,
            EXPERIMENT_SCENARIOS.ORDER_ONLY : IsoRequestParserHandlerOrder
                     }
