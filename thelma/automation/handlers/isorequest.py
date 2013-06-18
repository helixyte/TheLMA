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
from thelma.automation.tools.semiconstants import get_min_transfer_volume
from thelma.automation.tools.semiconstants import PIPETTING_SPECS_NAMES
from thelma.automation.handlers.base \
    import MoleculeDesignPoolLayoutParserHandler
from thelma.automation.parsers.isorequest import IsoRequestParser
from thelma.automation.tools.libcreation.base import LibraryBaseLayoutConverter
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionAssociationData
from thelma.automation.tools.metadata.transfection_utils import \
        TransfectionLayout
from thelma.automation.tools.metadata.transfection_utils import \
        TransfectionParameters
from thelma.automation.tools.metadata.transfection_utils import \
        TransfectionPosition
from thelma.automation.tools.semiconstants \
    import get_experiment_type_manual_optimisation
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.tools.semiconstants import get_experiment_metadata_type
from thelma.automation.tools.semiconstants import get_positions_for_shape
from thelma.automation.tools.utils.base import EMPTY_POSITION_TYPE
from thelma.automation.tools.utils.base import FIXED_POSITION_TYPE
from thelma.automation.tools.utils.base import FLOATING_POSITION_TYPE
from thelma.automation.tools.utils.base import MAX_PLATE_LABEL_LENGTH
from thelma.automation.tools.utils.base import MOCK_POSITION_TYPE
from thelma.automation.tools.utils.base import UNTREATED_POSITION_TYPE
from thelma.automation.tools.utils.base import add_list_map_element
from thelma.automation.tools.utils.base import get_trimmed_string
from thelma.automation.tools.utils.base import is_valid_number
from thelma.automation.tools.utils.iso import IsoParameters
from thelma.automation.tools.utils.iso import IsoPosition
from thelma.automation.tools.utils.racksector import QuadrantIterator
from thelma.interfaces import IMoleculeDesignLibrary
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import IOrganization
from thelma.models.iso import IsoRequest
from thelma.models.moleculedesign import MoleculeDesignPool
from thelma.models.tagging import TaggedRackPositionSet
from thelma.models.user import User

__docformat__ = 'reStructuredText en'

__all__ = ['IsoRequestParserHandler',
           'IsoRequestParserHandlerOpti',
           'IsoRequestParserHandlerScreen',
           'IsoRequestParserHandlerLibrary',
           'IsoRequestParserHandlerManual']


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

    #: The maximum lenght a plate set label may have.
    MAX_PLATE_SET_LABEL_LEN = MAX_PLATE_LABEL_LENGTH - 4

    #: Can molecule design pools be ordered in stock concentration?
    ALLOWS_STOCK_CONCENTRATION = False
    #: By default, all position types are allowed.
    ALLOWED_POSITION_TYPES = [FIXED_POSITION_TYPE, FLOATING_POSITION_TYPE,
                              MOCK_POSITION_TYPE, UNTREATED_POSITION_TYPE,
                              EMPTY_POSITION_TYPE]

    #: A list of parameters that do not need to specified at all.
    OPTIONAL_PARAMETERS = None
    #: A list of the metadata values that have be specified (as metadata).
    REQUIRED_METADATA = None
    #: A list of metadata values that are allowed be specified as metadata.
    ALLOWED_METADATA = [PLATE_SET_LABEL_KEY, DELIVERY_DATE_KEY, COMMENT_KEY,
                        NUMBER_ALIQUOT_KEY, IsoParameters.ISO_CONCENTRATION,
                        IsoParameters.ISO_VOLUME, IsoParameters.SUPPLIER,
                        TransfectionParameters.FINAL_CONCENTRATION,
                        TransfectionParameters.REAGENT_NAME,
                        TransfectionParameters.REAGENT_DIL_FACTOR]

    #: The ISO parameters that might be specified in a layout as list.
    ISO_LAYOUT_PARAMETERS = None
    #: The transfection parameters that might be specified in a layout as list.
    TRANSFECTION_LAYOUT_PARAMETERS = None

    #: A list of numerical parameter values.
    _NUMERICAL_PARAMETERS = [IsoParameters.ISO_VOLUME,
                             IsoParameters.ISO_CONCENTRATION,
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
        # The organization aggregate
        # (see :class:`thelma.models.aggregates.Aggregate`)
        # used to obtain suppliers from organization names.
        self._organization_agg = get_root_aggregate(IOrganization)
        # Stores the suppliers for the different supplier names.
        self._supplier_map = dict()

        #: The tagged rack position sets for tags that are not part of the
        #: transfection layout mapped onto their rack position set hash values.
        self.__additional_trps = dict()
        #: The transfection layout as rack layout.
        self.__rack_layout = None

        #: The name of the transfection reagent (metadata value).
        self._reagent_name_metadata = None
        #: The supplier for the molecule design pools (metadata value).
        self._supplier_metadata = None

        #: Stores distinct ISO concentration for screening cases.
        self._iso_concentrations = dict()

        # List for error collection.
        self._invalid_vol = []
        self._invalid_conc = []
        self._invalid_name = []
        self._invalid_df = []
        self._invalid_pool = []
        self._invalid_fconc = []
        self._unknown_supplier = set()
        self._has_volume_layout = False
        self._has_name_layout = False
        self._has_reagent_df_layout = False
        self._invalid_position_type = dict()

        # lookups for numerical values
        self.__invalid_lookup = {IsoParameters.ISO_VOLUME : self._invalid_vol,
            IsoParameters.ISO_CONCENTRATION : self._invalid_conc,
            TransfectionParameters.FINAL_CONCENTRATION : self._invalid_fconc,
            TransfectionParameters.REAGENT_DIL_FACTOR : self._invalid_df}
        self._metadata_lookup = {
            IsoParameters.ISO_VOLUME : None,
            IsoParameters.ISO_CONCENTRATION : None,
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

    def has_iso_sheet(self):
        """
        Returns *True* if the parser could find an ISO sheet in the source file,
        and *False* if it did not find a sheet with a valid name. This
        distinction becomes important when deciding whether or not the
        superior tool shall try to extract an ISO layout from the
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
                                            IsoParameters.MOLECULE_DESIGN_POOL

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
            if parameter == IsoParameters.POS_TYPE: continue
            alias_list = IsoParameters.get_all_alias(parameter)
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
            has_floatings = self.transfection_layout.has_floatings()

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

        supplier_name = self.parser.metadata_value_map[IsoParameters.SUPPLIER]
        supplier = self._get_supplier_for_name(supplier_name)
        if supplier is None and len(self._unknown_supplier) > 0:
            is_valid_metadata = False
        else:
            self._supplier_metadata = supplier

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
        if self._is_valid_numerical(metadata_value, 'default value',
                                    may_be_none, error_list):
            self._metadata_lookup[parameter] = metadata_value
            return True
        else:
            return False

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

    def _get_supplier_for_name(self, supplier_name):
        """
        Checks and returns the supplier for a supplier name.
        """
        if self._supplier_map.has_key(supplier_name):
            return self._supplier_map[supplier_name]
        elif supplier_name is None or len(supplier_name) < 2:
            return None
        elif isinstance(supplier_name, basestring) and \
                supplier_name.lower() == IsoPosition.ANY_SUPPLIER_INDICATOR:
            return None

        supplier = self._organization_agg.get_by_slug(supplier_name.lower())
        if supplier is None:
            self._unknown_supplier.add(supplier_name)
            return None
        else:
            self._supplier_map[supplier_name] = supplier
            return supplier

    def _create_positions(self):
        """
        Creates the actual transfection positions for the layout.
        """
        self.add_error('Abstract method: _create_positions()')

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
                IsoParameters.ISO_CONCENTRATION, pos_label, is_mock,
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
        parameter = IsoParameters.ISO_VOLUME
        return self._get_numerical_parameter_value(parameter, pos_label,
                                         is_mock, is_untreated, may_be_none)

    def _get_supplier(self, pos_label, pool):
        """
        Helper function returning the supplier for the given
        rack position.
        """
        if not isinstance(pool, MoleculeDesignPool):
            return None

        if self._supplier_metadata is not None:
            return self._supplier_metadata

        container = self.parser.parameter_map[IsoParameters.SUPPLIER]
        supplier_name = self._get_value_for_rack_pos(container, pos_label)
        if supplier_name is None: return None

        supplier = self._get_supplier_for_name(supplier_name)
        return supplier

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
            msg = 'There are positions in this ISO layout that lack either ' \
                  'an ISO volume or an ISO concentration. If you set a value ' \
                  'for one position, you need to set it for all other ' \
                  'positions as well (exception: mock positions do not ' \
                  'need a concentration).'
            self.add_error(msg)

        if len(self._invalid_pool) > 0:
            msg = 'The following molecule design pools are unknown: %s.' \
                  % (', '.join(sorted(self._invalid_pool)))
            self.add_error(msg)

        if len(self._invalid_vol) > 0:
            msg = 'Some positions in the ISO layout have invalid ISO volumes. ' \
                  'The volume must be a positive number or left blank. ' \
                  'Untreated position may have a volume "None" or ' \
                  '"untreated". Affected positions: %s.' \
                  % (', '.join(sorted(self._invalid_vol)))
            self.add_error(msg)

        if len(self._invalid_conc) > 0:
            msg = 'Some positions in the ISO layout have invalid ISO ' \
                  'concentration. The concentration must be a positive number ' \
                  'or left blank. Mock and untreated positions may have the ' \
                  'values "None", "mock" and "untreated". Affected ' \
                  'positions: %s.' % (', '.join(sorted(self._invalid_conc)))
            self.add_error(msg)

        if len(self._invalid_name) > 0:
            msg = 'Invalid or missing reagent name for the following rack ' \
                  'positions: %s. The reagent name must have a length of at ' \
                  'least 2! Untreated position may have the values "None" ' \
                  'or "untreated".' % (', '.join(sorted(self._invalid_name)))
            self.add_error(msg)

        if len(self._invalid_df) > 0:
            msg = 'Invalid or missing reagent dilution factor for rack ' \
                  'positions: %s. The dilution factor must be a positive ' \
                  'number! Untreated position may have the values "None" ' \
                  'or "untreated".' % (', '.join(sorted(self._invalid_df)))
            self.add_error(msg)

        if len(self._invalid_fconc) > 0:
            msg = 'Invalid final concentration for the following rack ' \
                  'positions: %s. The final concentration must be a positive ' \
                  'number! Mock and untreated positions may have the ' \
                  'values "None", "mock" and "untreated".' \
                   % (', '.join(sorted(self._invalid_fconc)))
            self.add_error(msg)

        if len(self._unknown_supplier) > 0:
            msg = 'Some suppliers could not be found in the DB: %s. Please ' \
                  'check the spelling.' % (list(self._unknown_supplier))
            self.add_error(msg)

        if len(self._invalid_position_type) > 0:
            type_positions = []
            for pos_type, positions in self._invalid_position_type.iteritems():
                pos_type_str = '%s (%s)' % (pos_type,
                                           ', '.join(sorted(positions)))
                type_positions.append(pos_type_str)
            msg = 'There are some positions in the ISO layout that are ' \
                  'not allowed for this type of experiment metadata (%s): %s.' \
                  % (get_experiment_metadata_type(self.SUPPORTED_SCENARIO).\
                    display_name, ' -- '.join(type_positions))
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

            if iso_conc > stock_conc:
                larger_than_stock_concentration.append(rack_pos.label)
            elif iso_conc == stock_conc:
                equals_stock_concentration.append(rack_pos.label)

        if len(equals_stock_concentration) > 0 and \
                                    not self.ALLOWS_STOCK_CONCENTRATION:
            equals_stock_concentration.sort()
            msg = 'Ordering molecule design pools in stock concentration is ' \
                  'not allowed for this kind of experiment metadata. ' \
                  'Lower the concentration or switch to experiment type ' \
                  '"%s", please. Stock concentration have been ordered ' \
                  'for the following positions: %s.' \
                  % (get_experiment_type_manual_optimisation().display_name,
                     equals_stock_concentration)
            self.add_error(msg)

        if len(larger_than_stock_concentration) > 0:
            larger_than_stock_concentration.sort()
            msg = 'Some concentrations you have ordered are larger than ' \
                  'the stock concentration for that molecule type ' \
                  '(%s nM): %s.' % (get_trimmed_string(stock_conc),
                                    ', '.join(larger_than_stock_concentration))
            self.add_error(msg)

        if not has_controls:
            msg = 'There are no fixed positions in this ISO layout!'
            self.add_error(msg)

    def _sort_floatings(self):
        """
        By default, floating placeholders in the layout are sorted by position.
        """
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
                new_placeholder = '%s%03i' % (IsoParameters.FLOATING_INDICATOR,
                                              counter)
                old_new_map[old_placeholder] = new_placeholder
            else:
                new_placeholder = old_new_map[old_placeholder]
            tf_pos.molecule_design_pool = new_placeholder

    def __create_iso_request(self):
        """
        Creates the IsoRequest object used as output value.
        """

        self.add_info('Create ISO request ...')

        metadata_value_map = self.parser.metadata_value_map
        plate_set_label = self._get_plate_set_label(metadata_value_map)
        comment = metadata_value_map[self.COMMENT_KEY]
        delivery_date = self.__get_date(metadata_value_map)
        number_aliquots = self._get_number_aliquots(metadata_value_map)

        if self.has_errors(): return None

        iso_request = IsoRequest(self.__rack_layout,
                                 requester=self.requester,
                                 number_aliquots=number_aliquots,
                                 delivery_date=delivery_date,
                                 plate_set_label=plate_set_label,
                                 worklist_series=None,
                                 comment=comment)

        if not self.has_errors():
            self.return_value = iso_request
            self.add_info('ISO request creating complete.')

    def _get_plate_set_label(self, metadata_value_map):
        """
        Obtains and checks the plate set label. In non-library scenarios
        the plate set label is specified in the excel sheet.
        """
        self.add_debug('Obtain plate set label ...')

        plate_set_label = metadata_value_map[self.PLATE_SET_LABEL_KEY]
        plate_set_label = plate_set_label.replace(' ', '_')

        if len(plate_set_label) > self.MAX_PLATE_SET_LABEL_LEN:
            msg = 'The maximum length for plate set labels is %i characters ' \
                  '(obtained: "%s", %i characters).' \
                   % (self.MAX_PLATE_SET_LABEL_LEN, plate_set_label,
                      len(plate_set_label))
            self.add_error(msg)

        return plate_set_label

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

    def _get_number_aliquots(self, metadata_value_map): #pylint: disable=W0613
        """
        Obtains the number of aliquots. It is 1 by default, except for
        screening cases.
        """
        return 1

    def __store_other_tags(self):
        """
        Stores non-parameter tags to the ISO layout. The tags are added later
        after the transfection layout has been completed.
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
        for parameter in IsoParameters.ALL:
            self.__forbidden_add_tag_params[parameter] = False
            validator = IsoParameters.create_validator_from_parameter(parameter)
            self.__forbidden_add_tag_validators[parameter] = validator

        for parameter in TransfectionParameters.ALL:
            if parameter in IsoParameters.ALL: continue
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
                                  ', '.join(found_parameters))
            self.add_error(msg)


class IsoRequestParserHandlerOpti(IsoRequestParserHandler):
    """
    A IsoRequestParserHandler for optimisation experiments.

    **Return Value:** ISO request (:class:`thelma.models.iso.IsoRequest`).
    """
    SUPPORTED_SCENARIO = EXPERIMENT_SCENARIOS.OPTIMISATION

    OPTIONAL_PARAMETERS = [IsoParameters.SUPPLIER,
                           IsoParameters.ISO_VOLUME,
                           IsoParameters.ISO_CONCENTRATION,
                           TransfectionParameters.FINAL_CONCENTRATION]
    REQUIRED_METADATA = [IsoRequestParserHandler.PLATE_SET_LABEL_KEY]

    ISO_LAYOUT_PARAMETERS = IsoParameters.ALL
    TRANSFECTION_LAYOUT_PARAMETERS = [
                            TransfectionParameters.FINAL_CONCENTRATION,
                            TransfectionParameters.REAGENT_NAME,
                            TransfectionParameters.REAGENT_DIL_FACTOR]

    def _create_positions(self):
        self.add_debug('Create transfection positions ...')

        parameter_map = self.parser.parameter_map
        pool_container = parameter_map[IsoParameters.MOLECULE_DESIGN_POOL]

        for pos_container in self.parser.shape.position_containers:
            pos_label = pos_container.label

            # Check properties
            pool_id = self._get_value_for_rack_pos(pool_container, pos_label)
            pool = self._get_molecule_design_pool_for_id(pool_id, pos_label)
            if pool is None: continue

            is_mock = (pool == MOCK_POSITION_TYPE)
            is_untreated = (pool == UNTREATED_POSITION_TYPE)

            supplier = self._get_supplier(pos_label, pool)
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
                            reagent_dil_factor=reagent_df, supplier=supplier,
                            final_concentration=final_conc)
            self.transfection_layout.add_position(tf_pos)

    def __get_reagent_df(self, pos_label, is_untreated):
        """
        Helper function returning the reagent dilution factor for the given
        rack position.
        """
        parameter = TransfectionParameters.REAGENT_DIL_FACTOR
        return self._get_numerical_parameter_value(parameter, pos_label, False,
                                                   is_untreated)

    def _check_layout_validity(self, has_floatings):
        """
        Checks scenario-dependent properties of the transfection layout.
        """
        IsoRequestParserHandler._check_layout_validity(self, has_floatings)

        pool_count = self.transfection_layout.get_molecule_design_pool_count()

        tf_shape_name = self.transfection_layout.shape.name
        if tf_shape_name == RACK_SHAPE_NAMES.SHAPE_384 and pool_count > 96:
            msg = '384-well optimisation ISO layouts with more than ' \
                  '96 distinct molecule design pool IDs are not supported. ' \
                  'Talk to the stock management and the IT unit, please.'
            self.add_error(msg)


class IsoRequestParserHandlerScreen(IsoRequestParserHandler):
    """
    A IsoRequestParserHandler for screening experiments.

    **Return Value:** ISO request (:class:`thelma.models.iso.IsoRequest`).
    """
    SUPPORTED_SCENARIO = EXPERIMENT_SCENARIOS.SCREENING

    OPTIONAL_PARAMETERS = [IsoParameters.SUPPLIER,
                           IsoParameters.ISO_CONCENTRATION,
                           IsoParameters.ISO_VOLUME]
    REQUIRED_METADATA = [IsoRequestParserHandler.PLATE_SET_LABEL_KEY,
                         IsoRequestParserHandler.NUMBER_ALIQUOT_KEY,
                         TransfectionParameters.REAGENT_NAME,
                         TransfectionParameters.REAGENT_DIL_FACTOR]

    ISO_LAYOUT_PARAMETERS = [IsoParameters.MOLECULE_DESIGN_POOL,
                             IsoParameters.ISO_CONCENTRATION]
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

        #: The molecule type of the fixed molecule design pools.
        self.__molecule_type = None

        #: Intermediate error storage
        self.__several_molecule_types = set()

        #: The rack sector association data.
        self.__association_data = None

    def get_molecule_type(self):
        """
        Returns the molecule type of the fixed positions.
        """
        if self.return_value is None: return None
        return self.__molecule_type

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
        return self._metadata_lookup[IsoParameters.ISO_VOLUME]

    def _create_positions(self):
        self.add_debug('Create transfection positions ...')

        parameter_map = self.parser.parameter_map
        pool_container = parameter_map[IsoParameters.MOLECULE_DESIGN_POOL]
        iso_volume = self._metadata_lookup[IsoParameters.ISO_VOLUME]
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
            is_untreated = (pool == UNTREATED_POSITION_TYPE)

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

            passed_supplier = self._supplier_metadata
            if not isinstance(pool, MoleculeDesignPool):
                passed_supplier = None

            if not is_valid_position: continue

            rack_pos = self._convert_to_rack_position(pos_container)
            if is_untreated:
                tf_pos = TransfectionPosition.create_untreated_position(
                          rack_position=rack_pos,
                          final_concentration=final_conc)
            else:
                tf_pos = TransfectionPosition(rack_position=rack_pos,
                          molecule_design_pool=pool,
                          iso_volume=iso_volume,
                          iso_concentration=iso_conc,
                          final_concentration=final_conc,
                          reagent_name=self._reagent_name_metadata,
                          reagent_dil_factor=reagent_df,
                          supplier=passed_supplier)
            self.transfection_layout.add_position(tf_pos)

    def _get_molecule_design_pool_for_id(self, pool_id, pos_label):
        """
        Returns the molecule design set or placeholder for a molecule design
        pool ID.
        """
        pool = IsoRequestParserHandler._get_molecule_design_pool_for_id(self,
                                                      pool_id, pos_label)
        if not isinstance(pool, MoleculeDesignPool): return pool

        #pylint: disable=E1103
        if self.__molecule_type is None:
            self.__molecule_type = pool.molecule_type
        elif not pool.molecule_type == self.__molecule_type:
            self.__several_molecule_types.add(str(pool.molecule_type.name))
            return None
        #pylint: enable=E1103
        return pool

    def _record_errors(self):
        """
        Records the errors that have been collected during layout filling.
        """
        IsoRequestParserHandler._record_errors(self)

        if len(self.__several_molecule_types) > 0:
            self.__several_molecule_types.add(str(self.__molecule_type.name))
            msg = 'There is more than one molecule type in the ISO ' \
                  'layout: %s.' % (list(self.__several_molecule_types))
            self.add_error(msg)

    def _sort_floatings(self):
        """
        Sorting can be by position (most cases) or position and associated
        sectors (for 384-well layouts with more than 1 concentration).
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

    def __get_association_data(self):
        """
        Returns the ISO association data for the screening layout.
        """
        try:
            association_data = TransfectionAssociationData(log=self.log,
                                transfection_layout=self.transfection_layout)
        except ValueError:
            msg = 'Error when trying to associated rack sectors!'
            self.add_error(msg)
            return None
        else:
            if self.__has_consistent_final_concentration(association_data):
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
                if not fc == final_conc:
                    info = 'ISO %.1f nM (final concentrations: %1.f nM and ' \
                           '%.1f nM)' % (iso_conc, fc, final_conc)
                    invalid_concentrations.append(info)
            else:
                iso_conc_map[iso_conc] = final_conc

            if final_conc_map.has_key(final_conc):
                ic = final_conc_map[final_conc]
                if not ic == iso_conc:
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
                                IsoParameters.FLOATING_INDICATOR, counter)
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
            msg = 'The concentrations within the ISO layout are not ' \
                  'consistent. Some sample positions have more or different ' \
                  'concentrations than others. Please regard, that the  ' \
                  'different concentrations for a molecule design pool must ' \
                  'be located in the same rack sector and that the ' \
                  'diestribution of concentrations must be the same for all ' \
                  'quadrants. If you have questions, ask Anna, please.'
            self.add_error(msg)

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

    OPTIONAL_PARAMETERS = [IsoParameters.SUPPLIER]
    REQUIRED_METADATA = [IsoRequestParserHandler.LIBRARY_KEY,
                         TransfectionParameters.FINAL_CONCENTRATION,
                         TransfectionParameters.REAGENT_NAME,
                         TransfectionParameters.REAGENT_DIL_FACTOR]

    ISO_LAYOUT_PARAMETERS = [IsoParameters.MOLECULE_DESIGN_POOL]
    TRANSFECTION_LAYOUT_PARAMETERS = []

    ALLOWED_METADATA = [IsoRequestParserHandler.DELIVERY_DATE_KEY,
                        IsoRequestParserHandler.COMMENT_KEY,
                        IsoRequestParserHandler.LIBRARY_KEY,
                        IsoParameters.SUPPLIER,
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
        if self.return_value is None: return None
        return self._reagent_name_metadata

    def get_reagent_dil_factor(self):
        """
        Returns the final transfection reagent dilution factor.
        """
        if self.return_value is None: return None
        return self._metadata_lookup[TransfectionParameters.REAGENT_DIL_FACTOR]

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

        return is_valid_metadata

    def __fetch_library_base_layout(self):
        """
        Converts the base layout of the library (defines which positions
        must contain samples and which are allowed to take up other
        ISO position types).
        """
        converter = LibraryBaseLayoutConverter(log=self.log,
                    rack_layout=self.__library.iso_request.iso_layout)
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
        self.add_debug('Create transfection positions ...')

        parameter_map = self.parser.parameter_map
        pool_container = parameter_map[IsoParameters.MOLECULE_DESIGN_POOL]
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

            passed_supplier = self._supplier_metadata
            if not isinstance(pool, MoleculeDesignPool):
                passed_supplier = None

            rack_pos = self._convert_to_rack_position(pos_container)
            if pool == UNTREATED_POSITION_TYPE:
                tf_pos = TransfectionPosition.create_untreated_position(
                          rack_position=rack_pos)
            elif pool == MOCK_POSITION_TYPE:
                tf_pos = TransfectionPosition.create_mock_position(
                          rack_position=rack_pos,
                          reagent_name=self._reagent_name_metadata,
                          reagent_dil_factor=reagent_df)
            else:
                tf_pos = TransfectionPosition(rack_position=rack_pos,
                          molecule_design_pool=pool,
                          final_concentration=final_conc,
                          reagent_name=self._reagent_name_metadata,
                          reagent_dil_factor=reagent_df,
                          supplier=passed_supplier)
            self.transfection_layout.add_position(tf_pos)

    def _check_layout_validity(self, has_floatings): #pylint: disable=W0613
        """
        We do not need to check the ISO concentration, since this is set
        by the library. Instead, we need to make sure that all library
        positions are taken by floating positions (and non-library positions
        are not taken by floating) and that there is at least one control.
        """
        sample_positions = self.__lib_base_layout.get_positions()
        missing_sample_pos = []
        invalid_sample_pos = []

        has_controls = False
        for rack_pos in get_positions_for_shape(self.transfection_layout.shape):
            pos_in_base_layout = rack_pos in sample_positions
            tf_pos = self.transfection_layout.get_working_position(rack_pos)
            if tf_pos is None:
                is_floating = False
            else:
                is_floating = tf_pos.is_floating
                if tf_pos.is_fixed: has_controls = True
            if not pos_in_base_layout and is_floating:
                invalid_sample_pos.append(rack_pos.label)
            elif pos_in_base_layout and not is_floating:
                missing_sample_pos.append(rack_pos.label)

        if not has_controls:
            msg = 'There are no fixed positions in this ISO layout!'
            self.add_error(msg)

        if len(missing_sample_pos) > 0:
            msg = 'The following positions are reserved for library samples: ' \
                  '%s. You have assigned a different position type to them.' \
                  % (', '.join(sorted(missing_sample_pos)))
            self.add_error(msg)

        if len(invalid_sample_pos) > 0:
            msg = 'The following positions must not be samples: %s.' \
                  % (', '.join(sorted(invalid_sample_pos)))
            self.add_error(msg)

    def _get_plate_set_label(self, metadata_value_map):
        """
        In library scenarios the plate set label is the library name. The label
        is not used like in other requests because the library plates are
        already labelled.
        """
        return self.__library.label


class IsoRequestParserHandlerManual(IsoRequestParserHandler):
    """
    A IsoRequestParserHandler for manual optimisation experiments.
    It is a special case since it parses a pure :class:`IsoLayout` without
    transfection values.

    **Return Value:** ISO request (:class:`thelma.models.iso.IsoRequest`).
    """
    SUPPORTED_SCENARIO = EXPERIMENT_SCENARIOS.MANUAL

    OPTIONAL_PARAMETERS = [IsoParameters.SUPPLIER]
    REQUIRED_METADATA = [IsoRequestParserHandler.PLATE_SET_LABEL_KEY]
    ALLOWED_METADATA = [IsoRequestParserHandler.PLATE_SET_LABEL_KEY,
                        IsoRequestParserHandler.DELIVERY_DATE_KEY,
                        IsoRequestParserHandler.COMMENT_KEY,
                        IsoParameters.ISO_CONCENTRATION,
                        IsoParameters.ISO_VOLUME, IsoParameters.SUPPLIER]

    ALLOWS_STOCK_CONCENTRATION = True
    ALLOWED_POSITION_TYPES = [FIXED_POSITION_TYPE, EMPTY_POSITION_TYPE]

    ISO_LAYOUT_PARAMETERS = IsoParameters.ALL
    TRANSFECTION_LAYOUT_PARAMETERS = []

    #: A list of numerical parameter values.
    _NUMERICAL_PARAMETERS = [IsoParameters.ISO_VOLUME,
                             IsoParameters.ISO_CONCENTRATION]

    def _create_positions(self):
        """
        Only molecule design pools can be specified via layout.
        """
        self.add_debug('Create transfection positions ...')

        parameter_map = self.parser.parameter_map
        pool_container = parameter_map[IsoParameters.MOLECULE_DESIGN_POOL]

        for pos_container in self.parser.shape.position_containers:
            pos_label = pos_container.label

            # Check properties
            pool_id = self._get_value_for_rack_pos(pool_container, pos_label)
            pool = self._get_molecule_design_pool_for_id(pool_id, pos_label)
            if pool is None: continue

            supplier = self._get_supplier(pos_label, pool)
            iso_volume = self._get_iso_volume(pos_label, False, False, False)
            iso_conc = self._get_iso_concentration(pos_label, False, False,
                                                   False)

            # Create position
            rack_pos = self._convert_to_rack_position(pos_container)
            tf_pos = TransfectionPosition(rack_position=rack_pos,
                                molecule_design_pool=pool, iso_volume=iso_volume,
                                iso_concentration=iso_conc,
                                supplier=supplier)
            self.transfection_layout.add_position(tf_pos)

    def _check_layout_validity(self, has_floatings): #pylint: disable=W0613
        """
        Pools that are ordered in stock concentration may occur only once.
        Floating position cannot occur since they are an invalid position type.
        """
        IsoRequestParserHandler._check_layout_validity(self, has_floatings)

        if has_floatings:
            msg = 'ISO layout for manual optimisations must not contain ' \
                  'floating positions!'
            self.add_error(msg)

        mdp_count = dict()
        for tf_pos in self.transfection_layout.working_positions():
            pool_id = tf_pos.molecule_design_pool_id
            if pool_id is None: continue
            if not mdp_count.has_key(pool_id): mdp_count[pool_id] = 0
            mdp_count[pool_id] += 1

        if len(mdp_count) < 1:
            max_well_number = 0
        else:
            max_well_number = max(mdp_count.values())
        if max_well_number > 1:
            msg = 'Each molecule design pool may occur only once for ISO ' \
                  'layouts of %s experiments. If you want to order multiple ' \
                  'wells switch to experiment type "%s", please.' \
                  % (self.SUPPORTED_SCENARIO,
                     get_experiment_type_manual_optimisation().display_name)
            self.add_error(msg)
        else:
            self.__check_dilution_concentrations()

            # TODO: review after ISO genertion refactoring
#        IsoRequestParserHandler._check_layout_validity(self, has_floatings)
#
#        pool_count = dict()
#        stock_conc_pools = set()
#
#        for tf_pos in self.transfection_layout.working_positions():
#            pool_id = tf_pos.molecule_design_pool_id
#            if pool_id is None: continue
#            if not pool_count.has_key(pool_id): pool_count[pool_id] = 0
#            pool_count[pool_id] += 1
#            if tf_pos.iso_concentration == tf_pos.stock_concentration:
#                stock_conc_pools.add(pool_id)
#
#        invalid = []
#        for pool_id in stock_conc_pools:
#            count = pool_count[pool_id]
#            if count > 1: invalid.append(pool_id)
#        if len(pool_count) > 96:
#            msg = '384-well manual optimisation ISO layouts with more than ' \
#                  '96 distinct molecule design pools are not supported. ' \
#                  'Talk to the stock management and the IT unit, please.'
#            self.add_error(msg)
#        elif len(invalid) > 0:
#            msg = 'If you order a molecule design pool in stock ' \
#                  'concentration, this pool may only occur once on the ISO ' \
#                  'plate. The following pools violate this rule: %s.' \
#                  % (', '.join([str(pool_id) for pool_id in sorted(invalid)]))
#            self.add_error(msg)
#        else:
#            self.__check_dilution_concentrations()

    def __check_dilution_concentrations(self):
        """
        Makes sure that the requested volumes can be obtained for the given
        concentrations.
        """
        min_cybio_transfer_volume = get_min_transfer_volume(
                                                    PIPETTING_SPECS_NAMES.CYBIO)
        insufficient_volumes = []

        for rack_pos, tf_pos in self.transfection_layout.iterpositions():
            if not tf_pos.is_fixed: continue
            iso_conc = tf_pos.iso_concentration
            stock_conc = tf_pos.stock_concentration
            if iso_conc == stock_conc: continue

            dil_factor = stock_conc / iso_conc
            take_out_volume = tf_pos.iso_volume / dil_factor
            buffer_volume = tf_pos.iso_volume - take_out_volume

            if take_out_volume < min_cybio_transfer_volume or \
                                    buffer_volume < min_cybio_transfer_volume:
                if take_out_volume < buffer_volume:
                    required_volume = dil_factor * min_cybio_transfer_volume
                else:
                    corr_factor = min_cybio_transfer_volume / buffer_volume
                    required_volume = tf_pos.iso_volume * corr_factor
                info = '%s (found %.1f ul, required: %.1f ul)' \
                        % (rack_pos.label, tf_pos.iso_volume, required_volume)
                insufficient_volumes.append(info)

        if len(insufficient_volumes) > 0:
            msg = 'The volumes you have requested are not sufficient to ' \
                  'prepare the requested dilution of the stock concentration ' \
                  '(assumed minimum volume for each buffer and sample ' \
                  '%s ul). Increase the requested volume or order stock ' \
                  'concentration, please. Details: %s.' \
                  % (min_cybio_transfer_volume, insufficient_volumes)
            self.add_error(msg)

    def _sort_floatings(self):
        """
        Sorts the floating placeholders in the layout.
        """
        self.add_error('Programming error: This method should never be ' \
                   'called for the %s subclass.' % (self.__class__.__name__))


class IsoRequestParserHandlerOrder(IsoRequestParserHandler):
    """
    A IsoRequestParserHandler for orders without experiment.
    These transfection layouts only contains pools and volumes. All
    pools are ordered in stock concentration and may occur only once
    per layout.

    **Return Value:** ISO request (:class:`thelma.models.iso.IsoRequest`).
    """
    SUPPORTED_SCENARIO = EXPERIMENT_SCENARIOS.ORDER_ONLY

    ALLOWS_STOCK_CONCENTRATION = True
    ALLOWED_POSITION_TYPES = [FIXED_POSITION_TYPE, EMPTY_POSITION_TYPE]

    ALLOWED_METADATA = [IsoRequestParserHandler.PLATE_SET_LABEL_KEY,
                        IsoRequestParserHandler.DELIVERY_DATE_KEY,
                        IsoRequestParserHandler.COMMENT_KEY,
                        IsoParameters.ISO_VOLUME, IsoParameters.SUPPLIER]
    OPTIONAL_PARAMETERS = [IsoParameters.SUPPLIER]
    REQUIRED_METADATA = [IsoRequestParserHandler.PLATE_SET_LABEL_KEY]

    ISO_LAYOUT_PARAMETERS = [IsoParameters.MOLECULE_DESIGN_POOL,
                             IsoParameters.ISO_VOLUME,
                             IsoParameters.SUPPLIER]
    TRANSFECTION_LAYOUT_PARAMETERS = []

    _NUMERICAL_PARAMETERS = [IsoParameters.ISO_VOLUME]

    def _get_plate_set_label(self, metadata_value_map):
        """
        Since there is only one plate the plate set label is taken over
        directly and may occupy the full 24 positions.
        """
        self.add_debug('Obtain plate set label ...')

        plate_set_label = metadata_value_map[self.PLATE_SET_LABEL_KEY]
        plate_set_label = plate_set_label.replace(' ', '_')

        if len(plate_set_label) > MAX_PLATE_LABEL_LENGTH:
            msg = 'The maximum length for plate set labels is %i characters ' \
                  '(obtained: "%s", %i characters).' \
                   % (MAX_PLATE_LABEL_LENGTH, plate_set_label,
                      len(plate_set_label))
            self.add_error(msg)

        return plate_set_label

    def _create_positions(self):
        """
        Only molecule design pools can be specified via layout.
        """
        self.add_debug('Create transfection positions ...')

        parameter_map = self.parser.parameter_map
        pool_container = parameter_map[IsoParameters.MOLECULE_DESIGN_POOL]

        for pos_container in self.parser.shape.position_containers:
            pos_label = pos_container.label

            # Check properties
            pool_id = self._get_value_for_rack_pos(pool_container, pos_label)
            pool = self._get_molecule_design_pool_for_id(pool_id, pos_label)
            if pool is None: continue

            supplier = self._get_supplier(pos_label, pool)
            iso_volume = self._get_iso_volume(pos_label, False, False, False)

            # Create position
            rack_pos = self._convert_to_rack_position(pos_container)
            tf_pos = TransfectionPosition(rack_position=rack_pos,
                                molecule_design_pool=pool, iso_volume=iso_volume,
                                supplier=supplier)
            self.transfection_layout.add_position(tf_pos)

    def _check_layout_validity(self, has_floatings):
        """
        Each pool may occur only once.
        Floating position cannot occur since they are an invalid position type.
        """
        IsoRequestParserHandler._check_layout_validity(self, has_floatings)

        count_map = dict()
        for tf_pos in self.transfection_layout.working_positions():
            pool_id = tf_pos.molecule_design_pool_id
            if not count_map.has_key(pool_id):
                count_map[pool_id] = 0
            count_map[pool_id] += 1

        more_than_one = []
        for pool_id, pool_count in count_map.iteritems():
            if pool_count > 1: more_than_one.append(pool_id)
        if len(more_than_one) > 0:
            msg = 'In an ISO request without experiment, each molecule ' \
                  'design pool may occur only once. The following pools ' \
                  'occur several times: %s.' % (', '.join([str(pool_id) \
                                    for pool_id in sorted(more_than_one)]))
            self.add_error(msg)

    def _sort_floatings(self):
        """
        Sorts the floating placeholders in the layout.
        """
        self.add_error('Programming error: This method should never be ' \
                   'called for the %s subclass.' % (self.__class__.__name__))


#: Lookup storing the handler classes for each experiment type.
_HANDLER_CLASSES = {
            EXPERIMENT_SCENARIOS.OPTIMISATION : IsoRequestParserHandlerOpti,
            EXPERIMENT_SCENARIOS.SCREENING : IsoRequestParserHandlerScreen,
            EXPERIMENT_SCENARIOS.LIBRARY : IsoRequestParserHandlerLibrary,
            EXPERIMENT_SCENARIOS.MANUAL : IsoRequestParserHandlerManual,
            EXPERIMENT_SCENARIOS.ORDER_ONLY : IsoRequestParserHandlerOrder
                     }
