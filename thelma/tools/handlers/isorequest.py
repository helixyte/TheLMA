"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

:Date: 2011 Aug 1st
:Author: AAB, berger at cenix-bioscience dot com

.. currentmodule:: thelma.tools.metadata.generation

This is the handler for ISO and transfection parsing. It converts the parsing
result into an IsoRequest object (including checks).

The tools are components of the :class:`ExperimentMetadataGenerator`.

"""
from datetime import date

from everest.entities.utils import get_root_aggregate
from everest.entities.utils import slug_from_identifier
from thelma.tools.handlers.base \
    import MoleculeDesignPoolLayoutParserHandler
from thelma.tools.parsers.isorequest import IsoRequestParser
from thelma.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.tools.semiconstants import get_experiment_metadata_type
from thelma.tools.semiconstants import get_positions_for_shape
from thelma.tools.metadata.base import TransfectionAssociationData
from thelma.tools.metadata.base import TransfectionLayout
from thelma.tools.metadata.base import TransfectionParameters
from thelma.tools.metadata.base import TransfectionPosition
from thelma.tools.utils.base import MAX_PLATE_LABEL_LENGTH
from thelma.tools.utils.base import add_list_map_element
from thelma.tools.utils.base import are_equal_values
from thelma.tools.utils.base import get_trimmed_string
from thelma.tools.utils.base import is_larger_than
from thelma.tools.utils.base import is_valid_number
from thelma.tools.utils.converters import LibraryBaseLayoutConverter
from thelma.tools.utils.iso import IsoRequestParameters
from thelma.tools.utils.layouts import EMPTY_POSITION_TYPE
from thelma.tools.utils.layouts import FIXED_POSITION_TYPE
from thelma.tools.utils.layouts import FLOATING_POSITION_TYPE
from thelma.tools.utils.layouts import LIBRARY_POSITION_TYPE
from thelma.tools.utils.layouts import MOCK_POSITION_TYPE
from thelma.tools.utils.layouts import UNTRANSFECTED_POSITION_TYPE
from thelma.tools.utils.layouts import UNTREATED_POSITION_TYPE
from thelma.tools.utils.racksector import QuadrantIterator
from thelma.interfaces import IMoleculeDesignLibrary
from thelma.interfaces import IMoleculeDesignPool
from thelma.entities.iso import LabIsoRequest
from thelma.entities.tagging import TaggedRackPositionSet
from thelma.entities.user import User


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

    **Return Value:** ISO request (:class:`thelma.entities.iso.IsoRequest`).
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
    #: By default, only fixed and empty position types are allowed.
    ALLOWED_POSITION_TYPES = {FIXED_POSITION_TYPE, EMPTY_POSITION_TYPE}
    #: A list of parameters that do not need to specified at all.
    OPTIONAL_PARAMETERS = None
    #: A list of the metadata values that have be specified (as metadata).
    REQUIRED_METADATA = None
    #: A list of metadata values that are allowed be specified as metadata.
    ALLOWED_METADATA = {PLATE_SET_LABEL_KEY, DELIVERY_DATE_KEY, COMMENT_KEY,
                        NUMBER_ALIQUOT_KEY, IsoRequestParameters.ISO_VOLUME,
                        IsoRequestParameters.ISO_CONCENTRATION,
                        TransfectionParameters.FINAL_CONCENTRATION,
                        TransfectionParameters.REAGENT_NAME,
                        TransfectionParameters.REAGENT_DIL_FACTOR}
    #: The ISO request parameters that might be specified in a layout as list.
    ISO_REQUEST_LAYOUT_PARAMETERS = None
    #: The transfection parameters that might be specified in a layout as list.
    TRANSFECTION_LAYOUT_PARAMETERS = None
    #: A list of numerical parameter values.
    _NUMERICAL_PARAMETERS = {IsoRequestParameters.ISO_VOLUME,
                             IsoRequestParameters.ISO_CONCENTRATION,
                             TransfectionParameters.FINAL_CONCENTRATION,
                             TransfectionParameters.REAGENT_DIL_FACTOR}

    def __init__(self, stream, requester, parent=None):
        """
        Constructor.

        :param requester: the user requesting the ISO
        :type requester: :class:`thelma.entities.user.User`
        """
        MoleculeDesignPoolLayoutParserHandler.__init__(self, stream,
                                                       parent=parent)
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
        # (see :class:`thelma.entities.aggregates.Aggregate`)
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
        self.__missing_pool = dict()
        self._invalid_vol = []
        self._invalid_conc = []
        self._invalid_name = []
        self._invalid_df = []
        self.__invalid_pool = dict()
        self._invalid_fconc = []
        self._has_volume_layout = False
        self._has_name_layout = False
        self._has_reagent_df_layout = False
        self.__invalid_position_type = dict()
        self.__unknown_position_type = dict()
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
    def create(cls, experiment_type_id, stream, requester, parent):
        """
        Factory method creating a handler for the passed experiment type.
        """
        kw = dict(stream=stream, requester=requester, parent=parent)
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
        return None if self.return_value is None else self.__association_data

    def has_iso_sheet(self):
        """
        Returns *True* if the parser could find an ISO sheet in the source file,
        and *False* if it did not find a sheet with a valid name. This
        distinction becomes important when deciding whether or not the
        superior tool shall try to extract an ISO request layout from the
        experiment design.
        """
        return not self.parser.sheet is None

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
        valid_parameters = dict()
        layout_parameters = set(self.ISO_REQUEST_LAYOUT_PARAMETERS \
                                + self.TRANSFECTION_LAYOUT_PARAMETERS)
        ign_parameters = {TransfectionParameters.POS_TYPE,
                          TransfectionParameters.OPTIMEM_DIL_FACTOR}
        for parameter in layout_parameters:
            if parameter in ign_parameters: continue
            alias_list = TransfectionParameters.get_all_alias(parameter)
            valid_parameters[parameter] = alias_list

        return valid_parameters

    def _convert_results_to_entity(self):
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

    def _add_position_to_layout(self, pos_container, kw):
        rack_pos = self._convert_to_rack_position(pos_container)
        kw['rack_position'] = rack_pos
        tf_pos = TransfectionPosition(**kw)
        self.transfection_layout.add_position(tf_pos)

    def _get_value_for_rack_pos(self, parameter_container, pos_label):
        """
        Retrieves the value of a parameter for a specified
        rack position.
        """
        if not parameter_container.well_map.has_key(pos_label):
            return None
        value = parameter_container.well_map[pos_label]
        return value

    def _get_position_type(self, pool_id, pos_label):
        """
        If the position type is not allowed for this experiment scenario,
        an error is recorded an the return value is *None*.
        """
        if is_valid_number(pool_id, is_integer=True):
            return FIXED_POSITION_TYPE

        pos_type = self._run_and_record_error(
                                TransfectionParameters.get_position_type,
                                base_msg=None, error_types={ValueError},
                                **dict(molecule_design_pool=pool_id))
        if pos_type is None:
            add_list_map_element(self.__unknown_position_type, pool_id,
                                 pos_label)
            return None

        if not pos_type in self.ALLOWED_POSITION_TYPES:
            add_list_map_element(self.__invalid_position_type, pos_type,
                                 pos_label)
            return None

        return pos_type

    def _get_molecule_design_pool_for_id(self, pool_id, pos_type, pos_label):
        """
        Returns the molecule design set or placeholder for a molecule design
        pool ID.
        """
        if not pos_type == FIXED_POSITION_TYPE: return pool_id

        if self._pool_map.has_key(pool_id): return self._pool_map[pool_id]

        pool = self._pool_aggregate.get_by_id(int(pool_id))
        if pool is None:
            pool = self._pool_aggregate.get_by_id(int(pool_id))
            if pool is None:
                add_list_map_element(self.__invalid_pool, pool_id, pos_label)
                return None

        self._pool_map[pool_id] = pool
        return pool

    def _is_valid_reagent_name(self, reagent_name, pos_label):
        """
        Checks whether a value is valid reagent name.
        """
        if reagent_name is None:
            self._invalid_name.append(pos_label)
            return False
        elif len(str(reagent_name)) < 2:
            self._invalid_name.append(pos_label)
            return False

        return True

    def _get_numerical_parameter_value(self, parameter, pos_label, pos_type,
                                       may_be_none):
        """
        Returns the numerical parameter value for the given rack position.
        """
        container = self.parser.parameter_map[parameter]

        if (pos_type == EMPTY_POSITION_TYPE):
            if not container.has_layout: return None
            value = self._get_value_for_rack_pos(container, pos_label)
            if not value is None:
                add_list_map_element(self.__missing_pool, pos_label, parameter)
            return None

        is_mock = (pos_type == MOCK_POSITION_TYPE)
        is_untreated_type = TransfectionParameters.is_untreated_type(pos_type)

        if not container.has_layout:
            if is_mock and parameter in TransfectionParameters.\
                                                        MOCK_NON_PARAMETERS:
                return TransfectionPosition.NONE_REPLACER
            elif is_untreated_type:
                return TransfectionPosition.NONE_REPLACER
            else:
                return self._metadata_lookup[parameter]

        value = self._get_value_for_rack_pos(container, pos_label)
        error_list = self.__invalid_lookup[parameter]

        if is_mock:
            if not TransfectionPosition.is_valid_mock_value(value, parameter):
                error_list.append(pos_label)
                return None
        elif is_untreated_type:
            if not TransfectionPosition.is_valid_untreated_value(value):
                error_list.append(pos_label)
                return None
        else:
            value = self._get_value_for_rack_pos(container, pos_label)
            if not self._is_valid_numerical(value, pos_label, may_be_none,
                                            error_list): return None
        return value

    def _get_final_concentration(self, pos_label, pos_type, may_be_none=None):
        """
        Helper function returning the final concentration for the given
        rack position.
        """
        parameter = TransfectionParameters.FINAL_CONCENTRATION
        return self._get_numerical_parameter_value(parameter, pos_label,
                                                   pos_type, may_be_none)

    def _get_iso_concentration(self, pos_label, pos_type, may_be_none=None):
        """
        Returns the ISO concentration for the given rack position.
        """
        parameter = IsoRequestParameters.ISO_CONCENTRATION
        return self._get_numerical_parameter_value(parameter, pos_label,
                                                   pos_type, may_be_none)

    def _get_iso_volume(self, pos_label, pos_type, may_be_none=None):
        """
        Helper function returning the ISO volume for the given rack position.
        """
        parameter = IsoRequestParameters.ISO_VOLUME
        return self._get_numerical_parameter_value(parameter, pos_label,
                                                   pos_type, may_be_none)

    def _get_reagent_name(self, pos_label, pos_type):
        """
        Returns the reagent name for the given rack position.
        """
        if self.parser.parameter_map.has_key(
                                        TransfectionParameters.REAGENT_NAME):
            container = self.parser.parameter_map[
                                        TransfectionParameters.REAGENT_NAME]
            has_layout = container.has_layout
        else:
            has_layout = False

        if (pos_type == EMPTY_POSITION_TYPE):
            if not has_layout: return None
            value = self._get_value_for_rack_pos(container, pos_label)
            if not value is None:
                add_list_map_element(self.__missing_pool, pos_label,
                                     TransfectionParameters.REAGENT_NAME)
            return None

        is_untreated_type = TransfectionParameters.is_untreated_type(pos_type)

        if not has_layout:
            if is_untreated_type:
                return TransfectionPosition.NONE_REPLACER
            else:
                return self._reagent_name_metadata

        reagent_name = self._get_value_for_rack_pos(container, pos_label)
        if is_untreated_type:
            if not TransfectionPosition.is_valid_untreated_value(reagent_name):
                self._invalid_name.append(pos_label)
                return None
        elif not self._is_valid_reagent_name(reagent_name, pos_label):
            return None

        return reagent_name

    def _get_reagent_dilution_factor(self, pos_label, pos_type):
        """
        Returns the reagent name for the given rack position.
        """
        parameter = TransfectionParameters.REAGENT_DIL_FACTOR
        rdf = self._get_numerical_parameter_value(parameter, pos_label, pos_type,
                                                  may_be_none=True)
        if (is_valid_number(rdf) and float(rdf) < 1):
            self._invalid_df.append(pos_label)
            return None
        return rdf

    def _record_errors(self):
        """
        Records the errors that have been collected during layout filling.
        """
        if not self.transfection_layout.\
                                has_consistent_volumes_and_concentrations():
            msg = 'There are positions in this ISO request layout that lack ' \
                  'either an ISO volume or an ISO concentration. If you set ' \
                  'a value for one position, you need to set it for all ' \
                  'other positions as well (mock, untreated and ' \
                  'untransfected positions are excepted).'
            self.add_error(msg)

        if len(self.__missing_pool) > 0:
            msg = 'Some position have parameter values although there is no ' \
                  'pool for them: %s.' % (self._get_joined_map_str(
                       self.__missing_pool))
            self.add_error(msg)

        if len(self.__invalid_pool) > 0:
            msg = 'The following molecule design pools are unknown: %s.' \
                  % (self._get_joined_map_str(self.__invalid_pool,
                     sort_lists=False))
            self.add_error(msg)

        if len(self._invalid_vol) > 0:
            msg = 'Some positions in the ISO request layout have invalid ISO ' \
                  'volumes. The volume must be a positive number or left ' \
                  'blank. Untreated position may have a volume "None", ' \
                  '"untreated" or "untransfected". Affected positions: %s.' \
                  % (self._get_joined_str(self._invalid_vol))
            self.add_error(msg)

        if len(self._invalid_conc) > 0:
            msg = 'Some positions in the ISO request layout have invalid ISO ' \
                  'concentration. The concentration must be a positive ' \
                  'number or left blank. Mock and untreated positions may ' \
                  'have the values "None", "mock", "untreated" or ' \
                  '"untransfected". Affected positions: %s.' \
                  % (self._get_joined_str(self._invalid_conc))
            self.add_error(msg)

        if len(self._invalid_name) > 0:
            msg = 'Invalid or missing reagent name for the following rack ' \
                  'positions in the ISO request layout: %s. The reagent ' \
                  'name must have a length of at least 2! Untreated position ' \
                  'may have the values "None", "untreated" or "untransfected".' \
                   % (self._get_joined_str(self._invalid_name))
            self.add_error(msg)

        if len(self._invalid_df) > 0:
            msg = 'Invalid or missing reagent dilution factor for rack ' \
                  'positions in the ISO request layout: %s. The dilution ' \
                  'factor must be 1 or larger! Untreated position may have ' \
                  'the values "None", "untreated" or "untransfected".' \
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

        if len(self.__unknown_position_type) > 0:
            msg = 'Unable to determine the position type for the following ' \
                  'pool IDs: %s. Allowed position types for this type of ' \
                  'experiment are: %s.' % (self._get_joined_map_str(
                   self.__unknown_position_type, sort_lists=False),
                   self._get_joined_str(self.ALLOWED_POSITION_TYPES))
            self.add_error(msg)

        if len(self.__invalid_position_type) > 0:
            msg = 'The following position types are not allowed in the ISO ' \
                  'request layout for this experiment metadata type (%s): %s.' \
                  % (get_experiment_metadata_type(self.SUPPORTED_SCENARIO).\
                    display_name, self._get_joined_map_str(
                            self.__invalid_position_type, sort_lists=False))
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

    def _sort_floatings(self):
        """
        In 96-well layouts the sorting is done by position. 384-well layouts
        must comply to rack sectors. Sorting then is done by rack sector.
        Assumes that we have floatings in the first place.
        """
        if self.transfection_layout.shape.name == RACK_SHAPE_NAMES.SHAPE_96:
            self._sort_floatings_by_position()
        elif not self.transfection_layout.has_final_concentrations():
            msg = 'If you use floating positions in an 384-well ISO request ' \
                  'layout you have to provide final concentration to enable ' \
                  'sorting by sectors. Please regard, that the  ' \
                  'different concentrations for a molecule design pool must ' \
                  'be located in the same rack sector and that the ' \
                  'distribution of concentrations must be the same for all ' \
                  'quadrants. If you have questions, ask IT, please.'
            self.add_error(msg)
        else:
            self.__association_data = self.__get_association_data()
            if not self.__association_data is None:
                parent_sectors = set(
                        self.__association_data.parent_sectors.values())
                if parent_sectors == {None}: # all sectors independent
                    self._sort_floatings_by_position()
                else:
                    self.__adjust_floatings_for_concentrations()

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
        association_data, regard_controls = \
            TransfectionAssociationData.find(self.transfection_layout, self)
        if association_data is None:
            msg = 'Error when trying to associated rack sectors! The ' \
                  'floating positions in 384-well ISO request layouts must ' \
                  'be arranged in rack sectors to enable the use of the ' \
                  'CyBio robot during ISO generation. If floating molecule ' \
                  'design pools shall occur several times, all occurrences ' \
                  'must be located in the same rack sector and that the ' \
                  'distribution of concentrations must be the same for all ' \
                  'quadrants. If you have questions, ask IT, please.'
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
        final_concentrations = association_data.sector_concentrations

        iso_map = dict()
        final_map = dict()
        for sector_index, iso_conc in iso_concentrations.iteritems():
            final_conc = final_concentrations[sector_index]
            if not iso_conc is None:
                add_list_map_element(iso_map, iso_conc, final_conc)
            if not final_conc is None:
                add_list_map_element(final_map, final_conc, iso_conc)

        prom_iso_conc = dict()
        for iso_conc, final_concentrations in iso_map.iteritems():
            if len(set(final_concentrations)) > 1:
                prom_iso_conc[iso_conc] = final_concentrations
        if len(prom_iso_conc) > 0:
            msg = 'Some ISO concentrations in the layout that are ' \
                  'involved in rack sector formation are related to more ' \
                  'than one distinct final concentration: %s.' \
                   % (self._get_joined_map_str(prom_iso_conc,
                      str_pattern='ISO conc: %s uM (final concentrations: %s)',
                      all_strs=False))
            self.add_error(msg)
            return False

        prom_final_conc = dict()
        for final_conc, iso_concentrations in final_map.iteritems():
            if len(set(iso_concentrations)) > 1:
                prom_final_conc[final_conc] = iso_concentrations
        if len(prom_final_conc) > 0:
            msg = 'Some final concentrations in the layout that are ' \
                  'involved in rack sector formation are related to more ' \
                  'than one distinct ISO concentration: %s.' \
                   % (self._get_joined_map_str(prom_final_conc,
                      str_pattern='final conc: %s uM (ISO concentrations: %s)',
                      all_strs=False))
            self.add_error(msg)
            return False

        return True

    def __adjust_floatings_for_concentrations(self):
        """
        Adjust the floating positions in case of several occurrences of a
        pool within a quadrant.
        """
        associated_sectors = sorted(self.__association_data.associated_sectors)
        quadrant_iter = QuadrantIterator(number_sectors=4)

        counter = 0
        for quadrant_wps in quadrant_iter.get_all_quadrants(
                                    working_layout=self.transfection_layout):
            for sectors in associated_sectors:
                new_placeholder = None
                for sector_index in sectors:
                    tf_pos = quadrant_wps[sector_index]
                    if tf_pos is None or not tf_pos.is_floating: continue
                    if new_placeholder is None:
                        counter += 1
                        new_placeholder = TransfectionParameters.\
                                          get_floating_placeholder(counter)
                    tf_pos.molecule_design_pool = new_placeholder

    def __create_iso_request(self):
        """
        Creates the IsoRequest object used as output value.
        """

        self.add_info('Create ISO request ...')

        metadata_value_map = self.parser.metadata_value_map
        number_aliquots = self.__get_number_aliquots(metadata_value_map)
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

    def __get_number_aliquots(self, metadata_value_map):
        """
        The default value for the number of aliquots is always one.
        In some scenarios this value might be overwritten.
        """
        if not self.NUMBER_ALIQUOT_KEY in self.ALLOWED_METADATA:
            return 1

        number_aliquots = metadata_value_map[self.NUMBER_ALIQUOT_KEY]
        if number_aliquots is None: return 1

        if not is_valid_number(number_aliquots, is_integer=True):
            msg = 'The number of aliquots must be a positive integer ' \
                  '(obtained: %s).' % (number_aliquots)
            self.add_error(msg)
            return None
        else:
            return int(number_aliquots)

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

    **Return Value:** ISO request (:class:`thelma.entities.iso.IsoRequest`).
    """
    SUPPORTED_SCENARIO = EXPERIMENT_SCENARIOS.OPTIMISATION

    ALLOWED_POSITION_TYPES = {FIXED_POSITION_TYPE, EMPTY_POSITION_TYPE,
                    FLOATING_POSITION_TYPE, MOCK_POSITION_TYPE,
                    UNTREATED_POSITION_TYPE, UNTRANSFECTED_POSITION_TYPE}

    OPTIONAL_PARAMETERS = [IsoRequestParameters.ISO_VOLUME,
                           IsoRequestParameters.ISO_CONCENTRATION,
                           TransfectionParameters.FINAL_CONCENTRATION]
    REQUIRED_METADATA = [IsoRequestParserHandler.PLATE_SET_LABEL_KEY]

    ISO_REQUEST_LAYOUT_PARAMETERS = IsoRequestParameters.ALL
    TRANSFECTION_LAYOUT_PARAMETERS = [
                            TransfectionParameters.FINAL_CONCENTRATION,
                            TransfectionParameters.REAGENT_NAME,
                            TransfectionParameters.REAGENT_DIL_FACTOR]

    def _create_positions(self):
        self.add_debug('Create transfection positions ...')

        parameter_map = self.parser.parameter_map
        pool_container = parameter_map[
                                    IsoRequestParameters.MOLECULE_DESIGN_POOL]

        for pos_container in self.parser.shape.position_containers:
            pos_label = pos_container.label

            pool_id = self._get_value_for_rack_pos(pool_container, pos_label)
            pos_type = self._get_position_type(pool_id, pos_label)
            if pos_type is None: continue

            pool = self._get_molecule_design_pool_for_id(pool_id, pos_type,
                                                         pos_label)

            iso_volume = self._get_iso_volume(pos_label, pos_type, True)
            iso_conc = self._get_iso_concentration(pos_label, pos_type, True)
            final_conc = self._get_final_concentration(pos_label, pos_type,
                                                       True)
            reagent_name = self._get_reagent_name(pos_label, pos_type)
            reagent_df = self._get_reagent_dilution_factor(pos_label, pos_type)

            if pos_type == EMPTY_POSITION_TYPE or pool is None: continue
            kw = dict(molecule_design_pool=pool,
                      iso_volume=iso_volume, iso_concentration=iso_conc,
                      reagent_name=reagent_name, reagent_dil_factor=reagent_df,
                      final_concentration=final_conc)
            self._add_position_to_layout(pos_container, kw)

    def _check_layout_validity(self, has_floatings):
        """
        Checks scenario-dependent properties of the transfection layout.
        """
        IsoRequestParserHandler._check_layout_validity(self, has_floatings)
        self.__check_for_unrequired_untreated_positions()

    def __check_for_unrequired_untreated_positions(self):
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
            msg = 'There are untreated or untransfected positions in your ' \
                  'ISO request layout! You do not need to mark them here, ' \
                  'because the system considers them to be empty and will ' \
                  'not transfer them to the experiment cell plates!'
            self.add_warning(msg)


class IsoRequestParserHandlerScreen(IsoRequestParserHandler):
    """
    A IsoRequestParserHandler for screening experiments.

    **Return Value:** ISO request (:class:`thelma.entities.iso.IsoRequest`).
    """
    SUPPORTED_SCENARIO = EXPERIMENT_SCENARIOS.SCREENING
    ALLOWED_POSITION_TYPES = {FIXED_POSITION_TYPE, FLOATING_POSITION_TYPE,
                              MOCK_POSITION_TYPE, UNTREATED_POSITION_TYPE,
                              UNTRANSFECTED_POSITION_TYPE, EMPTY_POSITION_TYPE}

    OPTIONAL_PARAMETERS = [IsoRequestParameters.ISO_CONCENTRATION,
                           IsoRequestParameters.ISO_VOLUME]
    REQUIRED_METADATA = [IsoRequestParserHandler.PLATE_SET_LABEL_KEY,
                         IsoRequestParserHandler.NUMBER_ALIQUOT_KEY,
                         TransfectionParameters.REAGENT_NAME,
                         TransfectionParameters.REAGENT_DIL_FACTOR]

    ISO_REQUEST_LAYOUT_PARAMETERS = [IsoRequestParameters.MOLECULE_DESIGN_POOL,
                             IsoRequestParameters.ISO_CONCENTRATION]
    TRANSFECTION_LAYOUT_PARAMETERS = [
                                    TransfectionParameters.FINAL_CONCENTRATION]

    def get_iso_volume(self):
        """
        Returns the ISO volume from the sheet (there is only a metadata value).
        """
        if self.return_value is None:
            result = None
        else:
            result = self._metadata_lookup[IsoRequestParameters.ISO_VOLUME]
        return result

    def _create_positions(self):
        self.add_debug('Create transfection positions ...')

        parameter_map = self.parser.parameter_map
        pool_container = parameter_map[
                                    IsoRequestParameters.MOLECULE_DESIGN_POOL]
        iso_volume = self._metadata_lookup[IsoRequestParameters.ISO_VOLUME]
        reagent_df = self._metadata_lookup[
                                    TransfectionParameters.REAGENT_DIL_FACTOR]
        reagent_name = self._reagent_name_metadata

        for pos_container in self.parser.shape.position_containers:
            pos_label = pos_container.label

            pool_id = self._get_value_for_rack_pos(pool_container, pos_label)
            pos_type = self._get_position_type(pool_id, pos_label)
            if pos_type is None: continue

            pool = self._get_molecule_design_pool_for_id(pool_id, pos_type,
                                                         pos_label)

            final_conc = self._get_final_concentration(pos_label, pos_type,
                                                       False)
            iso_conc = self._get_iso_concentration(pos_label, pos_type,
                                                   False)

            if pos_type == EMPTY_POSITION_TYPE or pool is None: continue
            if TransfectionParameters.is_untreated_type(pos_type):
                use_reaged_df = pos_type
                use_reagent_name = pos_type
                use_iso_vol = pos_type
            else:
                use_reaged_df = reagent_df
                use_reagent_name = reagent_name
                use_iso_vol = iso_volume

            kw = dict(molecule_design_pool=pool, iso_volume=use_iso_vol,
                  iso_concentration=iso_conc, final_concentration=final_conc,
                  reagent_dil_factor=use_reaged_df,
                  reagent_name=use_reagent_name)
            self._add_position_to_layout(pos_container, kw)


class IsoRequestParserHandlerLibrary(IsoRequestParserHandler):
    """
    A IsoRequestParserHandler for library screening experiments.

    **Return Value:** ISO request (:class:`thelma.entities.iso.IsoRequest`).
    """
    SUPPORTED_SCENARIO = EXPERIMENT_SCENARIOS.LIBRARY
    ALLOWED_POSITION_TYPES = {FIXED_POSITION_TYPE, EMPTY_POSITION_TYPE,
                          LIBRARY_POSITION_TYPE, MOCK_POSITION_TYPE,
                          UNTREATED_POSITION_TYPE, UNTRANSFECTED_POSITION_TYPE}

    OPTIONAL_PARAMETERS = []
    REQUIRED_METADATA = [IsoRequestParserHandler.LIBRARY_KEY,
                         TransfectionParameters.FINAL_CONCENTRATION,
                         TransfectionParameters.REAGENT_NAME,
                         TransfectionParameters.REAGENT_DIL_FACTOR]

    ISO_REQUEST_LAYOUT_PARAMETERS = [IsoRequestParameters.MOLECULE_DESIGN_POOL]
    TRANSFECTION_LAYOUT_PARAMETERS = []

    ALLOWED_METADATA = [IsoRequestParserHandler.PLATE_SET_LABEL_KEY,
                        IsoRequestParserHandler.DELIVERY_DATE_KEY,
                        IsoRequestParserHandler.COMMENT_KEY,
                        IsoRequestParserHandler.LIBRARY_KEY,
                        IsoRequestParserHandler.NUMBER_ALIQUOT_KEY,
                        TransfectionParameters.FINAL_CONCENTRATION,
                        TransfectionParameters.REAGENT_NAME,
                        TransfectionParameters.REAGENT_DIL_FACTOR]

    _NUMERICAL_PARAMETERS = [TransfectionParameters.FINAL_CONCENTRATION,
                             TransfectionParameters.REAGENT_DIL_FACTOR]

    def __init__(self, stream, requester, parent=None):
        IsoRequestParserHandler.__init__(self, stream, requester,
                                         parent=parent)
        #: The molecule design library used
        #: (:class:`thelma.entities.library.MoleculeDesignLibrary`)
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
        self.__library = lib_agg.get_by_slug(slug_from_identifier(lib_name))
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
        converter = LibraryBaseLayoutConverter(self.__library.rack_layout,
                                               parent=self)
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

            pool_id = self._get_value_for_rack_pos(pool_container, pos_label)
            pos_type = self._get_position_type(pool_id, pos_label)
            pool = self._get_molecule_design_pool_for_id(pool_id, pos_type,
                                                         pos_label)
            if pos_type is None or pool is None: continue

            if TransfectionParameters.is_untreated_type(pos_type):
                use_reagent_name = pos_type
                use_reagent_df = pos_type
                use_final_conc = pos_type
            else:
                if pos_type == MOCK_POSITION_TYPE:
                    use_final_conc = pos_type
                else:
                    use_final_conc = final_conc
                use_reagent_df = reagent_df
                use_reagent_name = self._reagent_name_metadata

            kw = dict(molecule_design_pool=pool,
                      final_concentration=use_final_conc,
                      reagent_name=use_reagent_name,
                      reagent_dil_factor=use_reagent_df)
            self._add_position_to_layout(pos_container, kw)

    def _check_layout_validity(self, has_floatings): #pylint: disable=W0613
        """
        We do not need to check the ISO concentration, since this is set
        by the library. Instead, we need to make sure that all library
        positions are set correctly (and non-library positions
        are not taken by library positions) and that there is at least one
        control (fixed position).
        """
        library_positions = set(self.__lib_base_layout.get_positions())
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
            msg = 'There are no fixed positions in this ISO request layout!'
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

    **Return Value:** ISO request (:class:`thelma.entities.iso.IsoRequest`).
    """
    SUPPORTED_SCENARIO = EXPERIMENT_SCENARIOS.MANUAL
    ALLOWED_POSITION_TYPES = {FIXED_POSITION_TYPE, EMPTY_POSITION_TYPE}

    OPTIONAL_PARAMETERS = []
    REQUIRED_METADATA = [IsoRequestParserHandler.PLATE_SET_LABEL_KEY]
    ALLOWED_METADATA = [IsoRequestParserHandler.PLATE_SET_LABEL_KEY,
                        IsoRequestParserHandler.DELIVERY_DATE_KEY,
                        IsoRequestParserHandler.COMMENT_KEY,
                        IsoRequestParameters.ISO_CONCENTRATION,
                        IsoRequestParameters.ISO_VOLUME]

    ISO_REQUEST_LAYOUT_PARAMETERS = IsoRequestParameters.ALL
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

            pool_id = self._get_value_for_rack_pos(pool_container, pos_label)
            pos_type = self._get_position_type(pool_id, pos_label)
            # only fixed and empty are allowed
            if pos_type is None: continue
            pool = self._get_molecule_design_pool_for_id(pool_id, pos_type,
                                                         pos_label)

            iso_vol = self._get_iso_volume(pos_label, pos_type, False)
            iso_conc = self._get_iso_concentration(pos_label, pos_type, False)
            if pool is None: continue

            kw = dict(molecule_design_pool=pool,
                      iso_volume=iso_vol, iso_concentration=iso_conc)
            self._add_position_to_layout(pos_container, kw)


class IsoRequestParserHandlerOrder(IsoRequestParserHandler):
    """
    A IsoRequestParserHandler for orders without experiment.
    These transfection layouts only contains pools and volumes. All
    pools are ordered in stock concentration and may occur only once
    per layout.

    **Return Value:** ISO request (:class:`thelma.entities.iso.IsoRequest`).
    """
    SUPPORTED_SCENARIO = EXPERIMENT_SCENARIOS.ORDER_ONLY

    ALLOWED_POSITION_TYPES = {FIXED_POSITION_TYPE, EMPTY_POSITION_TYPE}

    ALLOWED_METADATA = [IsoRequestParserHandler.PLATE_SET_LABEL_KEY,
                        IsoRequestParserHandler.DELIVERY_DATE_KEY,
                        IsoRequestParserHandler.COMMENT_KEY,
                        IsoRequestParameters.ISO_VOLUME]
    OPTIONAL_PARAMETERS = []
    REQUIRED_METADATA = [IsoRequestParserHandler.PLATE_SET_LABEL_KEY]

    ISO_REQUEST_LAYOUT_PARAMETERS = [IsoRequestParameters.MOLECULE_DESIGN_POOL,
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

            pool_id = self._get_value_for_rack_pos(pool_container, pos_label)
            pos_type = self._get_position_type(pool_id, pos_label)
            # only fixed and empty are allowed
            if pos_type is None: continue
            pool = self._get_molecule_design_pool_for_id(pool_id, pos_type,
                                                         pos_label)

            iso_volume = self._get_iso_volume(pos_label, pos_type, False)
            if pool is None: continue

            kw = dict(molecule_design_pool=pool, iso_volume=iso_volume)
            self._add_position_to_layout(pos_container, kw)

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
