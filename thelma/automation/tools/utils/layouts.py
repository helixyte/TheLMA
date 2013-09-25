"""
Base classes for layout handling.

AAB
"""
from thelma.automation.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import get_converted_number
from thelma.automation.tools.utils.base import get_trimmed_string
from thelma.automation.tools.utils.base import is_valid_number
from thelma.automation.tools.utils.base import sort_rack_positions
from thelma.models.moleculedesign import MoleculeDesignPool
from thelma.models.moleculetype import MoleculeType
from thelma.models.rack import RackPosition
from thelma.models.rack import RackPositionSet
from thelma.models.racklayout import RackLayout
from thelma.models.tagging import Tag
from thelma.models.tagging import TaggedRackPositionSet
from thelma.models.utils import get_user

__docformat__ = "reStructuredText en"

__all__ = ['ParameterSet',
           'ParameterAliasValidator',
           'WorkingPosition',
           'WorkingLayout',
           'MoleculeDesignPoolParameters',
           'FIXED_POSITION_TYPE',
           'FLOATING_POSITION_TYPE',
           'LIBRARY_POSITION_TYPE',
           'EMPTY_POSITION_TYPE',
           'MOCK_POSITION_TYPE',
           'UNTREATED_POSITION_TYPE',
           'UNTRANSFECTED_POSITION_TYPE',
           'MoleculeDesignPoolPosition',
           'MoleculeDesignPoolLayout',
           'TransferTarget',
           'TransferParameters',
           'TransferPosition',
           'TransferLayout']


class ParameterSet(object):
    """
    A list of parameters referring to certain context (e.g. ISO handling,
    dilution preparation). The parameters correspond to the attributes of
    particular WorkingPosition subclasses.

    The values of the parameters also work as default tag predicate for
    tags of the parameter.
    """

    #: The domain for the tags to be generated.
    DOMAIN = None

    #: A list of the attributes/parameters that need to be set.
    REQUIRED = None
    #: A list of all available attributes/parameters.
    ALL = None

    #: A map storing alias predicates for each parameter.
    ALIAS_MAP = dict()
    #: A map storing the domains for each parameter.
    DOMAIN_MAP = dict()

    @classmethod
    def is_valid_parameter(cls, parameter):
        """
        Checks whether a parameter (value) is part of the set.
        """
        for listed_parameter in cls.ALL:
            if listed_parameter == parameter:
                return True
        return False

    @classmethod
    def create_all_validators(cls):
        """
        Factory method creating the parameter alias objects for all
        parameters in this set.

        :return: A map with ParameterSet values as keys and
            ParameterAliasValidator objects as values.
        """
        parameters = dict()
        for parameter in cls.ALL:
            parameter_alias = cls.create_validator_from_parameter(parameter)
            parameters[parameter] = parameter_alias
        return parameters

    @classmethod
    def create_validator_from_parameter(cls, parameter):
        """
        Factory method creating a parameter alias object from an ParameterSet
        value (collections: ).

        :param parameter: The parameter you want to instantiate.
        :type parameter: A value of this parameter set.
        :return: a ParameterAliasValidator object
        """

        validator = ParameterAliasValidator(parameter)
        if cls.ALIAS_MAP.has_key(parameter):
            alias_list = cls.ALIAS_MAP[parameter]
            for alias in alias_list: validator.add_alias(alias)

        return validator

    @classmethod
    def get_all_alias(cls, parameter):
        """
        Returns a list containing all valid alias for a parameter.

        :param parameter: The parameter, whose aliases you want to obtain.
        :type parameter: A value of this parameter set.
        :return: a list parameter aliases (:class:`string` objects)
        """

        alias_set = set([parameter])
        for alias in cls.ALIAS_MAP[parameter]:
            if not alias in alias_set: alias_set.add(alias)
        return alias_set


class ParameterAliasValidator(object):
    """
    This class collects valid tag names for the different ISO parameters.
    """

    def __init__(self, parameter):
        """
        Constructor:

        :param parameter: The parameter name (:class:`IsoParameters` value).
        """
        #: The parameter name (:class:`IsoParameters` value).
        self.parameter = parameter
        #: The list of aliases (strings).
        self.aliases = set()

        corrected_alias = self.__adjust_string(parameter)
        self.aliases.add(corrected_alias)

    def add_alias(self, alias):
        """
        Convenience method adding a valid tag name for the parameter.

        :param alias: An valid tag name indicating this parameter.
        :type alias: :class:`string`
        """
        corrected_alias = self.__adjust_string(alias)
        if not corrected_alias in self.aliases:
            self.aliases.add(corrected_alias)

    def has_alias(self, tag_predicate):
        """
        Checks whether a tag predicate is a valid alias for a parameter.

        :param tag_predicate: A tag predicate.
        :type tag_predicate: :class:`string`
        :return: *True* or *False*
        """
        corrected_predicate = self.__adjust_string(tag_predicate)
        if corrected_predicate in self.aliases:
            return True
        else:
            return False

    def __adjust_string(self, string):
        """
        Applies some cosmetic changes to a string to make sure that string with
        equal content are recognized as equal.
        """
        label = string.strip()
        label = label.replace('_', ' ').replace('-', ' ')
        label = label.lower()
        return label

    def __repr__(self):
        str_format = '<ParameterValidator %s>'
        params = (self.parameter)
        return str_format % params


class WorkingPosition(object):
    """
    Working position comprise a rack position and some additional information
    that are used for a certain context (such as ISO generation).
    Working position conduct checks and validations and provide tags for
    DB rack layouts.

    **Equality condition**: must be implemented by subclasses
    """

    #: The parameter set this working position is associated with
    #: (subclass of :class:`thelma.automation.tools.utils.base.ParameterSet`).
    PARAMETER_SET = ParameterSet

    #: String that is used for a tag if a value is *None*
    NONE_REPLACER = 'None'

    #: If *False* boolean parameters with a false value are not converted
    #: into tags (default: *True*).
    RECORD_FALSE_VALUES = True

    def __init__(self, rack_position):
        """
        Constructor:

        :param rack_position: The rack position in the rack.
        :type rack_position: :class:`thelma.models.rack.RackPosition`
        """

        if not isinstance(rack_position, RackPosition):
            msg = 'The rack position must be a RackPosition object ' \
                  '(obtained type: %s).' % (rack_position.__class__)
            raise ValueError(msg)

        #: The rack position (:class:`thelma.models.rack.RackPosition`).
        self.rack_position = rack_position

    def get_parameter_value(self, parameter):
        """
        Returns the value for the requested parameter.

        :param parameter: A parameter from the :attr:`ParameterSet` associated
            to this working position type.
        :type parameter: :class:`string`
        :return: the attribute mapped onto that parameter
        """
        if not parameter in self.PARAMETER_SET.ALL:
            return None
        parameter_values = self._get_parameter_values_map()
        return parameter_values[parameter]

    def get_parameter_tag(self, parameter):
        """
        Returns the tags for requested parameter.

        :param parameter: A parameter from the :attr:`ParameterSet` associated
            to this working position type.
        :type parameter: :class:`string`
        :return: the tag displaying the data for the parameter
        """
        value = self.get_parameter_value(parameter)

        if value is None:
            value = self.NONE_REPLACER
        elif isinstance(value, bool) and \
                            not self.RECORD_FALSE_VALUES and value == False:
            return None
        else:
            value = self.get_value_string(value)

        domain = self.PARAMETER_SET.DOMAIN_MAP[parameter]
        return Tag(domain, parameter, value)

    def get_tag_set(self):
        """
        Returns the tag set for this working position.
        """
        tag_set = set()
        for parameter in self.PARAMETER_SET.REQUIRED:
            tag = self.get_parameter_tag(parameter)
            if tag is None: continue
            tag_set.add(tag)

        for parameter in self.PARAMETER_SET.ALL:
            if parameter in self.PARAMETER_SET.REQUIRED: continue
            if self.get_parameter_value(parameter) is None: continue
            tag = self.get_parameter_tag(parameter)
            if tag is None: continue
            tag_set.add(tag)

        return tag_set

    def has_tag(self, tag):
        """
        Checks whether a working position complies to a given tag.

        :param tag: The tag to be compared.
        :type tag: :class:`thelma.models.tagging.Tag`

        :return: :class:`boolean`
        """
        tag_set = self.get_tag_set()
        return tag in tag_set

    def _get_parameter_values_map(self):
        """
        Returns a map with key = parameter name, value = associated attribute.
        """
        raise NotImplementedError('Abstract method.')

    @classmethod
    def get_value_string(cls, value):
        """
        Converts a value into a string and chops of ".0" for numbers.
        *None* values are left unaltered.
        """
        if value is None: return value
        string_value = get_trimmed_string(value)
        return string_value

    @classmethod
    def parse_boolean_tag_value(cls, boolean_str):
        """
        Converts a boolean tag value into a boolean.

        :raise ValueError: If the value is not *True* or *False*.
        """
        values = {str(True) : True, str(False) : False}
        if not boolean_str.has_key(boolean_str):
            raise ValueError('Invalid string for boolean conversion: %s' \
                             % (boolean_str))
        return values[boolean_str]

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
                self.rack_position == other.rack_position

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __str__(self):
        return self.rack_position.label


class WorkingLayout(object):
    """
    Working containers for special rack layouts. Working layouts can be
    converted into rack layout (and generated from them by using special tools)
    and mimic some of their behaviour.
    There contain the information of a rack layout but provide a different
    business logic and additional integrity checks.
    """

    #: The working position class this layout is associated with.
    WORKING_POSITION_CLS = WorkingPosition

    def __init__(self, shape):
        """
        Constructor:

        :param shape: The rack shape.
        :type shape: :class:`thelma.models.rack.RackShape`
        """

        #: The dimension of the layout (:class:`thelma.model.rack.RackShape`).
        self.shape = shape
        #: A map storing the :class:`IsoPosition` objects for all rack positions
        #: of the layout.
        self._position_map = dict()
        #: The default user for the tagged position set creation
        #: (:class:`IT_USER` - object of :class:`thelma.models.user.User`).
        self._user = get_user('it')

    def add_position(self, working_position):
        """
        Adds a :class:`Working_position` to the layout.

        :param working_position: The working position to be added.
        :type working_position: :class:`WorkingPosition`
        :raises TypeError: If the added position is not a
            :attr:`WORKING_POSITION_CLASS` object.
        """
        if not (isinstance(working_position, self.WORKING_POSITION_CLS)):
            msg = 'A position to be added must be a %s object (obtained ' \
                  'type: %s).' % (self.WORKING_POSITION_CLS,
                                  working_position.__class__.__name__)
            raise TypeError(msg)

        self._position_map[working_position.rack_position] = working_position

    def del_position(self, rack_position):
        """
        Deletes the working position for that rack position.
        """
        if self._position_map.has_key(rack_position):
            del self._position_map[rack_position]

    def get_working_position(self, rack_position):
        """
        Returns the working position for a certain working position (or *None*
        if there is none).
        """
        if self._position_map.has_key(rack_position):
            return self._position_map[rack_position]
        else:
            return None

    def get_tags(self):
        """
        Returns all tags in this layout.

        :rtype: set of :class:`thelma.models.tagging.Tag`
        """

        tags = set()
        for working_position in self._position_map.values():
            for tag in working_position.get_tag_set():
                if not tag in tags: tags.add(tag)
        return tags

    def get_positions(self):
        """
        Returns all rack positions in this layout.

        :rtype: set of :py:class:`thelma.models.rack.RackPosition`
        """
        return self._position_map.keys()

    def get_tags_for_position(self, rack_position):
        """
        Returns all tags for the given rack position.

        :param rack_position: The rack position whose tags you want to get.
        :type rack_position: :class:`thelma.models.rack.RackPosition`
        :return: All tags for the given position.
        :rtype: set of :py:class:`thelma.models.tagging.Tag`
        """

        if self._position_map.has_key(rack_position):
            return self._position_map[rack_position].get_tag_set()
        else:
            return set()

    def get_positions_for_tag(self, tag):
        """
        Returns all rack position having the given tag.

        :param tag: The tag whose positions you want to get.
        :type tag: :class:`thelma.models.tagging.Tag`
        :return: All positions for the given tag.
        :rtype: set of :class:`thelma.models.rack.RackPosition`
        """

        rack_positions = set()
        for rack_position, working_position in self._position_map.iteritems():
            if working_position.has_tag(tag):
                rack_positions.add(rack_position)
        return rack_positions

    def get_sorted_working_positions(self):
        """
        Returns a list of the working position stored in this layout's
        :attr:`_position_map` sorted by rack position (row-first).

        :return: A list of the working position sorted by rack position.
        """
        sorted_rack_positions = sort_rack_positions(self._position_map.keys())

        working_positions = []
        for rack_pos in sorted_rack_positions:
            working_positions.append(self._position_map[rack_pos])
        return working_positions

    def create_rack_layout(self):
        """
        Creates a conventional (entity) rack_layout from the contained data.
        """
        trps = self.create_tagged_rack_position_sets()
        return RackLayout(self.shape, trps)

    def create_tagged_rack_position_sets(self):
        """
        Creates a list of tagged rack position sets for this layout.
        """

        tag_map = dict()
        for rack_position, working_position in self._position_map.iteritems():
            for tag in working_position.get_tag_set():
                if not tag_map.has_key(tag): tag_map[tag] = set()
                tag_map[tag].add(rack_position)

        rps_map = dict()
        rps_tag_map = dict()
        for tag, pos_set in tag_map.iteritems():
            rack_pos_set = RackPositionSet.from_positions(pos_set)
            hash_value = rack_pos_set.hash_value
            if not rps_map.has_key(hash_value):
                rps_map[hash_value] = rack_pos_set
                rps_tag_map[hash_value] = set()
            rps_tag_map[hash_value].add(tag)

        tagged_rack_position_sets = []
        for hash_value in rps_map.keys():
            rack_pos_set = rps_map[hash_value]
            tags = rps_tag_map[hash_value]
            trps = TaggedRackPositionSet(tags, rack_pos_set, self._user)
            tagged_rack_position_sets.append(trps)

        return tagged_rack_position_sets

    def iterpositions(self):
        """
        Returns the position map iterator.
        """
        return self._position_map.iteritems()

    def working_positions(self):
        """
        Returns the working positions stored in this layout (unsorted).
        """
        return self._position_map.values()

    def __str__(self):
        return '%s' % (self.shape)

    def __repr__(self):
        str_format = '<%s, shape: %s>'
        params = (self.__class__.__name__, self.shape)
        return str_format % params

    def __len__(self):
        """
        Returns the length of the :attr:`_position_map` of the object.
        """
        return len(self._position_map)

    def __eq__(self, other):
        """
        The layouts are equal if their :attr:`position_maps` are
        equal.
        """

        if not isinstance(other, self.__class__): return False

        if self.shape != other.shape: return False
        if len(self) != len(other): return False

        for rack_position in self._position_map.keys():
            other_wp = other.get_working_position(rack_position)
            if other_wp is None:
                return False
            if not other_wp == self._position_map[rack_position]:
                return False

        return True

    def __ne__(self, other):
        return not self.__eq__(other)


class MoleculeDesignPoolParameters(ParameterSet):
    """
    The base parameter for layouts containing molecule design pool data.

    There are six possible types:

        * FIXED: In final state, volume and concentration have to be set.
                 The molecule design pool must be a valid specific design pool.
        * FLOATING: In final state, volume and concentration have to be set. The
                 molecule design pool can be a placeholder for a real molecule
                 design pool.
        * LIBRARY: Library position contain samples. However, the samples are
                 already present in ready-to-use plates and need not be prepared
                 anymore. Accordingly, their data cannot be altered.
        * MOCK: In final state, volume and concentration have to be set,
                 however, there is no molecule design pool.
        * EMPTY: The position is and will remain empty. All values are None.
                 Empty values are not stored in the rack layout.
        * UNTREATED/UNTRANSFECTED: Untreated positions are treated like empty
                 positions. The distinction is requested by the scientists
                 (to mark that their might still be cells, for instance).
    """
    DOMAIN = 'molecule_design_pool'

    #: The molecule design pool (tag value: molecule design pool id).
    MOLECULE_DESIGN_POOL = 'molecule_design_pool_id'

    #: The position type (fixed, floating, mock or empty).
    POS_TYPE = 'position_type'

    #: A map storing alias prediactes for each parameter.
    ALIAS_MAP = {MOLECULE_DESIGN_POOL : ['molecule design set ID',
                                         'molecule design pool'],
                POS_TYPE : []}

    #: The value for fixed type positions.
    FIXED_TYPE_VALUE = 'fixed'
    #: The value for floating type positions.
    FLOATING_TYPE_VALUE = 'floating'
    #: The value for library type positions.
    LIBRARY_TYPE_VALUE = 'library'
    #: The value for empty type positions.
    EMPTY_TYPE_VALUE = 'empty'
    #: The value for mock type positions.
    MOCK_TYPE_VALUE = 'mock'
    #: Untreated positions are treated like empty positions. The distinction
    #: is requested by the scientists. Untreated positions gain
    #: an own position type, however during conversion into a working layout
    #: they will create empty positions.
    UNTREATED_TYPE_VALUE = 'untreated'
    #: See :attr:`UNTREATED_TYPE_VALUE`.
    UNTRANSFECTED_TYPE_VALUE = 'untransfected'
    #: These positions types are regarded as untreated (empty).
    __UNTREATED_TYPES = (UNTREATED_TYPE_VALUE, UNTRANSFECTED_TYPE_VALUE)

    #: Not all layouts allow for untreated positions. Use the flag to specify.
    ALLOWS_UNTREATED_POSITIONS = True

    #: A string that must be present in the beginning molecule design pool tag
    #: value (to mark that the following number as a counter and not molecule
    #: design pool id).
    FLOATING_INDICATOR = 'md_'

    #: These are the values allowed values for parameters that are always
    #: *None* in untreated positions.
    VALID_UNTREATED_NONE_REPLACERS = (None, UNTREATED_TYPE_VALUE.upper(),
                                      WorkingPosition.NONE_REPLACER.upper(),
                                      UNTRANSFECTED_TYPE_VALUE.upper())
    #: These are the values allowed values for parameters that are always
    #: *None* in mock positions.
    VALID_MOCK_NONE_REPLACERS = (None, MOCK_TYPE_VALUE.upper(),
                                 WorkingPosition.NONE_REPLACER.upper())

    @classmethod
    def get_position_type(cls, molecule_design_pool):
        """
        Returns the positions type for an molecule design pool or molecule
        design pool placeholder.

        :return: ISO position type (str)
        """
        if molecule_design_pool is None:
            position_type = cls.EMPTY_TYPE_VALUE
        elif isinstance(molecule_design_pool, basestring) and \
                molecule_design_pool.lower() in cls.__UNTREATED_TYPES:
            position_type = cls.UNTREATED_TYPE_VALUE
        elif isinstance(molecule_design_pool, basestring) and \
                molecule_design_pool.lower() == cls.MOCK_TYPE_VALUE:
            position_type = cls.MOCK_TYPE_VALUE
        elif isinstance(molecule_design_pool, cls.LIBRARY_TYPE_VALUE):
            position_type = cls.LIBRARY_TYPE_VALUE
        elif isinstance(molecule_design_pool, basestring) and \
                cls.FLOATING_INDICATOR in molecule_design_pool:
            position_type = cls.FLOATING_TYPE_VALUE
        elif isinstance(molecule_design_pool, MoleculeDesignPool):
            position_type = cls.FIXED_TYPE_VALUE
        else:
            msg = 'Unable to determine type for molecule design pool: %s.' \
                  % (molecule_design_pool)
            raise ValueError(msg)

        if position_type in cls.__UNTREATED_TYPES and \
                                        not cls.ALLOWS_UNTREATED_POSITIONS:
            msg = 'Untreated and untransfected positions are not allowed!'
            raise ValueError(msg)

        return position_type

    @classmethod
    def is_untreated_type(cls, molecule_design_pool):
        """
        Is the molecule design pool an untreated (or untransfected) type?
        """
        return molecule_design_pool in cls.__UNTREATED_TYPES

    @classmethod
    def is_valid_untreated_value(cls, value):
        """
        Since untreated position lack some parameters (e.g. concentrations)
        the values for these parameters must be *None* or a valid replacer.
        Valid values for are *None*, \'None\' and \'untreated\'.
        """
        return cls.__is_valid_value(value, cls.VALID_UNTREATED_NONE_REPLACERS)

    @classmethod
    def is_valid_mock_value(cls, value):
        """
        Since mock position lack some parameters (e.g. concentrations)
        the values for these parameters must be *None* or a valid replacer.
        Valid values for are *None*, \'None\' and \'mock\'.
        """
        return cls.__is_valid_value(value, cls.VALID_MOCK_NONE_REPLACERS)

    @classmethod
    def __is_valid_value(cls, value, allowed_values):
        """
        Check whether the value is in the given list (case-insensitive).
        """
        value_upper = value
        if isinstance(value, basestring): value_upper = value.upper()
        return value_upper in allowed_values


#: An alias for :attr:`MoleculeDesignPoolParameters.FIXED_TYPE_VALUE`.
FIXED_POSITION_TYPE = MoleculeDesignPoolParameters.FIXED_TYPE_VALUE
#: An alias for :attr:`MoleculeDesignPoolParameters.FLOATING_TYPE_VALUE`.
FLOATING_POSITION_TYPE = MoleculeDesignPoolParameters.FLOATING_TYPE_VALUE
#: An alias for :attr:`MoleculeDesignPoolParameters.LIBRARY_TYPE_VALUE`.
LIBRARY_POSITION_TYPE = MoleculeDesignPoolParameters.LIBRARY_TYPE_VALUE
#: An alias for :attr:`MoleculeDesignPoolParameters.EMPTY_TYPE_VALUE`.
EMPTY_POSITION_TYPE = MoleculeDesignPoolParameters.EMPTY_TYPE_VALUE
#: An alias for :attr:`MoleculeDesignPoolParameters.MOCK_TYPE_VALUE`.
MOCK_POSITION_TYPE = MoleculeDesignPoolParameters.MOCK_TYPE_VALUE
#: An alias for :attr:`MoleculeDesignPoolParameters.UNTREATED_TYPE_VALUE`.
UNTREATED_POSITION_TYPE = MoleculeDesignPoolParameters.UNTREATED_TYPE_VALUE
#: An alias for :attr:`MoleculeDesignPoolParameters.UNTRANSFECTED_TYPE_VALUE`.
UNTRANSFECTED_POSITION_TYPE = MoleculeDesignPoolParameters.\
                              UNTRANSFECTED_TYPE_VALUE


class MoleculeDesignPoolPosition(WorkingPosition):
    """
    An abstract base class for working position storing data about molecule
    design pools.
    """
    PARAMETER_SET = MoleculeDesignPoolParameters

    #: If *False*, position types are not stored in the rack layouts.
    EXPOSE_POSTIIONS_TYPE = True

    def __init__(self, rack_position, molecule_design_pool=None):
        """
        Constructor:

        :param rack_position: The rack position.
        :type rack_position: :class:`thelma.models.rack.RackPosition`.

        :param molecule_design_pool: The molecule design pool for this position
            or a valid placeholder.
        :type molecule_design_pool:
            :class:`thelma.models.moleculedesign.MoleculeDesignPool`
            or :class:`basestring`

        :param molecule_type: The molecule type (required for fixed positions).
        :type molecule_type: :class:`thelma.models.moleculetype.MoleculeType` or
            :class:`str
        """
        if self.__class__ == MoleculeDesignPoolPosition:
            raise NotImplementedError('Abstract class')

        WorkingPosition.__init__(self, rack_position)

        #: The molecule design pool (or placeholder).
        self.molecule_design_pool = molecule_design_pool
        #: The type of the ISO position.
        self.position_type = self.PARAMETER_SET.get_position_type(
                                                    self.molecule_design_pool)

    @classmethod
    def create_empty_position(cls, rack_position):
        """
        Creates a transfection position representing an empty well.

        :param rack_position: The rack position.
        :type rack_position: :class:`thelma.models.rack.RackPosition`.
        :return: A transfection position.
        """
        return cls(rack_position=rack_position)

    @classmethod
    def create_untreated_position(cls, rack_position):
        """
        Creates an untreated ISO position for the given rack position.

        :param rack_position: The rack position.
        :type rack_position: :class:`thelma.models.rack.RackPosition`.
        :return: untreated IsoPosition
        """
        return cls(rack_position=rack_position,
                   molecule_design_pool=cls.PARAMETER_SET.UNTREATED_TYPE_VALUE)

    @property
    def is_empty(self):
        """
        If *True* this position represents a empty or untreated position.
        """
        if self.position_type == self.PARAMETER_SET.EMPTY_TYPE_VALUE or \
                self.position_type == self.PARAMETER_SET.UNTREATED_TYPE_VALUE:
            return True
        else:
            return False

    @property
    def is_untreated_type(self):
        """
        If *True* this position represents an untreated position.
        """
        if self.PARAMETER_SET.is_untreated_type(self.position_type):
            return True
        else:
            return False

    @property
    def is_mock(self):
        """
        If *True* this position represents a mock position.
        """
        if self.position_type == self.PARAMETER_SET.MOCK_TYPE_VALUE:
            return True
        else:
            return False

    @property
    def is_library(self):
        """
        If *True* this position represents a library position.
        """
        if self.position_type == self.PARAMETER_SET.LIBRARY_TYPE_VALUE:
            return True
        else:
            return False

    @property
    def is_floating(self):
        """
        If *True* this position represents a floating position.
        """
        if self.position_type == self.PARAMETER_SET.FLOATING_TYPE_VALUE:
            return True
        else:
            return False

    @property
    def is_fixed(self):
        """
        If *True* this position represents a fixed position.
        """
        if self.position_type == self.PARAMETER_SET.FIXED_TYPE_VALUE:
            return True
        else:
            return False

    @property
    def molecule_design_pool_id(self):
        """
        The molecule design pool ID or the molecule design pool placeholder.
        """
        pool_id = self.molecule_design_pool
        if isinstance(self.molecule_design_pool, MoleculeDesignPool):
            pool_id = self.molecule_design_pool.id #pylint: disable=E1103
        return pool_id

    @property
    def stock_concentration(self):
        """
        The stock concentration stored for this pool in nM (only for positions
        with molecule design pools).
        """
        if isinstance(self.molecule_design_pool, MoleculeDesignPool):
            return self.molecule_design_pool.\
                   default_stock_concentration * CONCENTRATION_CONVERSION_FACTOR
        else:
            return None

    @property
    def molecule_type(self):
        """
        The molecule type of the pool (only for positions with molecule design
        pools).
        """
        if isinstance(self.molecule_design_pool, MoleculeDesignPool):
            return self.molecule_design_pool.molecule_type
        else:
            return None

    @classmethod
    def is_valid_untreated_value(cls, value):
        """
        Since untreated position lack some parameters (e.g. concentrations)
        the values for these parameters must be *None* or a valid replacer.
        Valid values for are *None*, \'None\' and \'untreated\'.

        Invokes :func:`MoleculeDesignPoolParameters.is_valid_untreated_value`
        """
        return cls.PARAMETER_SET.is_valid_untreated_value(value)

    @classmethod
    def is_valid_mock_value(cls, value):
        """
        Since mock position lack some parameters (e.g. concentrations)
        the values for these parameters must be *None* or a valid replacer.
        Valid values for are *None*, \'None\' and \'mock\'.

        Invokes :func:`MoleculeDesignPoolParameters.is_valid_mock_value`
        """
        return cls.PARAMETER_SET.is_valid_mock_value(value)

    def get_tag_set(self):
        """
        Empty and untreated position return only the position type tag.
        All other return all value tags.
        """
        if self.is_empty and not self.is_untreated_type:
            return set([self.get_parameter_tag(self.PARAMETER_SET.POS_TYPE)])
        else:
            return WorkingPosition.get_tag_set(self)

    def get_parameter_tag(self, parameter):
        """
        The return value for position types is *None* if
        :attr:`EXPOSE_POSTIIONS_TYPE` is *False*.
        """
        if parameter == self.PARAMETER_SET.POS_TYPE and \
                                            not self.EXPOSE_POSTIIONS_TYPE:
            return None
        return WorkingPosition.get_parameter_tag(self, parameter)

    def _get_parameter_values_map(self):
        """
        Returns the :attr:`parameter_values_map`
        """
        return {self.PARAMETER_SET.POS_TYPE : self.position_type,
                self.PARAMETER_SET.MOLECULE_DESIGN_POOL :
                                                     self.molecule_design_pool}

    def __eq__(self, other):
        return (isinstance(other, MoleculeDesignPoolPosition) \
                and other.rack_position == self.rack_position \
                and str(other.molecule_design_pool) == \
                                                str(self.molecule_design_pool))

    def str(self):
        return '%s (%s)' % (self.rack_position.label,
                            self.molecule_design_pool_id)

    def __repr__(self):
        str_format = '<%s type: %s, rack position: %s, molecule design ' \
                     'pool: %s>'
        params = (self.__class__.__name__, self.position_type,
                  self.rack_position, self.molecule_design_pool)
        return str_format % params


class MoleculeDesignPoolLayout(WorkingLayout):
    """
    An abstract base class for designs that store molecule design pool
    data.
    """

    WORKING_POSITION_CLS = MoleculeDesignPoolPosition

    def __init__(self, shape):
        """
        Constructor:

        :param shape: The rack shape.
        :type shape: :class:`thelma.models.rack.RackShape`
        """
        if self.__class__ == MoleculeDesignPoolLayout:
            raise NotImplementedError('Abstract class')

        WorkingLayout.__init__(self, shape)

        #: You cannot add new positions to a closed layout.
        self.is_closed = False

        #: The molecule type for floating positions.
        self._floating_molecule_type = None
        #: The stock concentration for floating positions in nM.
        self._floating_stock_concentration = None

    @property
    def floating_molecule_type(self):
        """
        The molecule type for floating positions.
        """
        return self._floating_molecule_type

    def set_floating_molecule_type(self, molecule_type):
        """
        Floating position must all have the same molecule type. If floating
        positions are still marked by placeholders the molecule type cannot
        be read from the pool.

        :param molecule_type: The molecule type for the floating positions.
        :type molecule_type: :class:`thelma.models.moleculetype.MoleculeType`
        """
        if not isinstance(molecule_type, MoleculeType):
            msg = 'The molecule type must be a %s (obtained: %s).' \
                  % (MoleculeType.__name__, molecule_type.__class__.__name__)
            raise TypeError(msg)

        self._floating_molecule_type = molecule_type

    @property
    def floating_stock_concentration(self):
        """
        The stock concentration for floating positions in nM.
        """
        return self._floating_stock_concentration

    def set_floating_stock_concentration(self, stock_concentration):
        """
        Floating position must all have the same stock concentration. If
        floating positions are still marked by placeholders the concentration
        cannot be read from the pool.

        If the stock concentration is smaller than 1, the unit is considered
        to be M (instead of nM) and the value is multiplied by the
        :attr:`CONCENTRATION_CONVERSION_FACTOR`.

        :param stock_concentration: The stock concentration for the floating
            positions in M or nM.
        :type stock_concentration: positive number
        """
        if not is_valid_number(stock_concentration):
            msg = 'The stock concentration must be a positive number ' \
                  '(obtained: %s).' % (stock_concentration)
            raise ValueError(msg)

        if stock_concentration < 1:
            self._floating_stock_concentration = stock_concentration \
                                        * CONCENTRATION_CONVERSION_FACTOR
        else:
            self._floating_stock_concentration = stock_concentration

    def add_position(self, working_position):
        """
        Adds a :class:`Working_position` to the layout.

        :param working_position: The working position to be added.
        :type working_position: :class:`WorkingPosition`
        :raises ValueError: If the added position is not a
            :attr:`WORKING_POSITION_CLASS` object.
        :raises AttributeError: If the layout is closed.
        :raises TypeError: if the position has the wrong type
        """
        if not self.is_closed:
            WorkingLayout.add_position(self, working_position)
        else:
            raise AttributeError('The layout is closed!')

    def has_floatings(self):
        """
        Returns *True* if this layout is having floating position and *False*
        if there are none.
        """
        for pool_pos in self._position_map.values():
            if pool_pos.is_floating: return True
        return False

    def get_floating_positions(self):
        """
        Returns a position dictionary containing only the floating positions
        included in this ISO layout.

        :return: A dictionary (key: floating place holder, value: list of
                 iso_position)
        """
        floatings_positions = dict()
        for pool_pos in self._position_map.values():
            if pool_pos.is_floating:
                placeholder = pool_pos.molecule_design_pool
                if not placeholder in floatings_positions:
                    floatings_positions[placeholder] = []
                floatings_positions[placeholder].append(pool_pos)
        return floatings_positions

    def create_rack_layout(self):
        """
        Creates a conventional (entity) rack_layout from the contained data
        and closes the IsoLayout.
        """
        self.close()
        return WorkingLayout.create_rack_layout(self)

    def close(self):
        """
        Removes all empty positions from the layout. Untreated positions
        are kept.
        """
        if not self.is_closed:

            del_positions = []
            for rack_pos, pool_pos in self._position_map.iteritems():
                if pool_pos.is_untreated_type: continue
                if pool_pos.is_empty: del_positions.append(rack_pos)
            for rack_pos in del_positions: del self._position_map[rack_pos]

            self.is_closed = True


class TransferTarget(object):
    """
    This class represents the target of a transfer.
    """

    #: This character separates the values of transfer target in the info
    #: string.
    INFO_DELIMITER = ':'

    def __init__(self, rack_position, transfer_volume, target_rack_marker=None):
        """
        Constructor:

        :param rack_position: The target position the liquid shall be added to.
        :type rack_position: :class:`thelma.models.rack.RackPosition`

        :param transfer_volume: The volume to be transferred.
        :type transfer_volume: A number.

        :param target_rack_marker: A marker for the target plate (optional).
        :type target_rack_marker: :class:`str`
        :default target_rack_marker: *None*
        """
        if isinstance(rack_position, RackPosition):
            label = rack_position.label
        elif isinstance(rack_position, basestring):
            label = rack_position
        else:
            msg = 'The rack position must be a RackPosition or a string ' \
                  '(obtained: %s).' % (rack_position.__class__.__name__)
            raise TypeError(msg)

        if not is_valid_number(transfer_volume):
            msg = 'The transfer volume must be a positive number ' \
                  '(obtained: %s).' % (transfer_volume)
            raise ValueError(msg)

        if not target_rack_marker is None and \
                            not isinstance(target_rack_marker, basestring):
            msg = 'The tarvget rack marker must be string (obtained: %s)!' \
                  % (target_rack_marker.__class__.__name__)
            raise TypeError(msg)

        #: The target position the liquid shall be added to.
        self.position_label = label
        #: The volume to be transferred.
        self.transfer_volume = get_converted_number(transfer_volume)
        #: A marker for the target plate (optional).
        self.target_rack_marker = target_rack_marker

    @property
    def hash_value(self):
        """
        Contains position label and target rack marker (if there is one).
        """
        if self.target_rack_marker is None:
            raise self.position_label
        return '%s%s' % (self.position_label, self.target_rack_marker)

    @property
    def target_info(self):
        """
        Returns a string encoding the data of this transfer target.
        """
        values = [self.position_label, get_trimmed_string(self.transfer_volume)]
        if not self.target_rack_marker is None:
            values.append(self.target_rack_marker)
        return self.INFO_DELIMITER.join(values)

    @classmethod
    def parse_info_string(cls, info_string):
        """
        Parses the given info string and returns a TransferTarget object
        represented by this string.

        :param info_string: The string encoding the data.
        :type info_string: :class:`str`
        :return: A :class:`TransferTarget` object.
        :raises ValueError: If the string cannot be parsed.
        """
        if not cls.INFO_DELIMITER in info_string:
            msg = 'Could not find "%s" delimiter in info string (obtained: ' \
                  '%s!)' % (cls.INFO_DELIMITER, info_string)
            raise ValueError(msg)

        tokens = info_string.split(cls.INFO_DELIMITER)
        return TransferTarget(*tokens) #pylint: disable=W0142

    def __eq__(self, other):
        return isinstance(other, TransferTarget) and \
               self.position_label == other.position_label

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __str__(self):
        return self.position_label

    def __repr__(self):
        str_format = '<TransferTarget %s (volume: %s)>'
        params = (self.position_label, self.transfer_volume)
        return str_format % params


class TransferParameters(MoleculeDesignPoolParameters):
    """
    A list of transfer parameters. The subclasses might have different
    sets of transfer targets. The sets are handled separately.
    """

    #: The domain for transfer-related tags.
    DOMAIN = 'sample_transfer'

    #: The molecule design pool (tag value: molecule design pool id).
    MOLECULE_DESIGN_POOL = MoleculeDesignPoolParameters.MOLECULE_DESIGN_POOL
    #: The position type (fixed, floating, mock or empty).
    POS_TYPE = MoleculeDesignPoolParameters.POS_TYPE

    #: A list of :class:`TransferTarget` objects. This is the main transfer
    #: target set that is inherited by all subclasses.
    TRANSFER_TARGETS = 'transfer_targets'
    #: Do there have to be transfer targets for the given parameter?
    #: (default for :attr:`TRANSFER_TARGETS` : *False*)
    MUST_HAVE_TRANSFER_TARGETS = {TRANSFER_TARGETS : False}

    #: All parameters that deal with transfer targets.
    TRANSFER_TARGET_PARAMETERS = [TRANSFER_TARGETS]

    #: A list of the attributes/parameters that need to be set.
    REQUIRED = [TRANSFER_TARGETS, MOLECULE_DESIGN_POOL]
    ALL = [TRANSFER_TARGETS, MOLECULE_DESIGN_POOL, POS_TYPE]

    ALIAS_MAP = dict(MoleculeDesignPoolParameters.ALIAS_MAP, **{
                            TRANSFER_TARGETS : ['target_wells']})

    DOMAIN_MAP = {TRANSFER_TARGETS : DOMAIN,
                  MOLECULE_DESIGN_POOL : MoleculeDesignPoolParameters.DOMAIN,
                  POS_TYPE : MoleculeDesignPoolParameters.DOMAIN}

    @classmethod
    def must_have_transfer_targets(cls, parameter_name):
        """
        Do there have to be transfer targets for the given parameter?
        """
        return cls.MUST_HAVE_TRANSFER_TARGETS[parameter_name]


class TransferPosition(MoleculeDesignPoolPosition):
    """
    This class represents the source position for a sample transfer. The
    rack position is at this the *source position* in the source plate.

    The subclasses might have different sets of transfer targets. The sets
    are handled separately (association is made via the )

    **Equality condition**: equal :attr:`rack_position` and
        :attr:`target_positions`.
    """

    #: The parameter set this working position is associated with.
    PARAMETER_SET = TransferParameters

    #: The delimiter for the different target infos.
    TARGETS_DELIMITER = '-'

    def __init__(self, rack_position, molecule_design_pool=None,
                 transfer_targets=None):
        """
        Constructor:

        :param rack_position: The source rack position in the source rack.
        :type rack_position: :class:`thelma.models.rack.RackPosition`

        :param molecule_design_pool: The molecule design pool for this position
            or a valid placeholder.
        :type molecule_design_pool:
            :class:`thelma.models.moleculedesign.MoleculeDesignPool`
            or :class:`basestring`

        :param transfer_targets: The target positions and transfer volumes.
            Some subclasses require transfer targets, in others there are
            optional. This is set in the :attr:`MUST_HAVE_TRANSFER_TARGETS`
            lookup of the :attr:`PARAMETER_SET`.
        :type transfer_targets: list of :class:`TransferTarget`
        """
        if self.__class__ == TransferPosition:
            raise NotImplementedError('Abstract class')

        MoleculeDesignPoolPosition.__init__(self, rack_position=rack_position,
                                    molecule_design_pool=molecule_design_pool)

        #: The target positions and transfer volumes. Some subclasses require
        #: transfer targets, in others there are optional. This is set in
        #: the :attr:`MUST_HAVE_TRANSFER_TARGETS` attribute of the
        #: :attr:`PARAMETER_SET`.
        self.transfer_targets = self._check_transfer_targets(
                        self.PARAMETER_SET.TRANSFER_TARGETS, transfer_targets)

    def _check_transfer_targets(self, parameter_name, target_list,
                                name='transfer targets'):
        """
        Checks the type and presence of transfer targets for the given
        parameter.
        """
        if target_list is None:
            if self.PARAMETER_SET.must_have_transfer_targets(parameter_name):
                msg = 'A %s must have at least one transfer target!' \
                       % (self.__class__.__name__)
                raise ValueError(msg)
            else:
                return []
        elif not isinstance(target_list, list):
            msg = 'The %s must be passed as list (obtained: %s).' \
                  % (name, target_list.__class__.__name__)
            raise TypeError(msg)
        else:
            for tt in target_list:
                if not isinstance(tt, TransferTarget):
                    msg = 'The transfer target must be TransferTarget objects ' \
                          '(obtained: %s).' % (tt.__class__.__name__)
                    raise TypeError(msg)
            return target_list

    def get_transfer_target_list(self, parameter_name=None):
        """
        Returns the target list for the given parameter name. If you do not
        pass a name, the default list (:attr:`transfer_targets`) is returned.
        """
        if parameter_name is None or \
                        parameter_name == self.PARAMETER_SET.TRANSFER_TARGETS:
            return self.transfer_targets
        return None

    def add_transfer_target(self, transfer_target, parameter_name=None):
        """
        Adds a transfer target for the given parameter. If you do not
        specifify a parameter, the default list (:attr:`transfer_targets`)
        will be used.

        :param transfer_target: The target well to be added.
        :type transfer_target: :class:`TransferTarget`

        :param parameter_name: The name of the parameter the transfer target
            belongs to.
        :type parameter_name: :class:`str` (parameter in the
            :attr:`PARAMETER_SET`).
        :default parameter_name: *None* (TRANSFER_TARGETS)

        :raises TypeError: If the transfer target has wrong type.
        :raises ValueError: If the well is already present.
        """
        target_list = self.get_transfer_target_list(parameter_name)

        if not isinstance(transfer_target, TransferTarget):
            msg = 'Transfer targets wells must be TransferTarget objects' \
                  '(obtained: %s, type: %s).' % (transfer_target,
                                        transfer_target.__class__.__name__)
            raise TypeError(msg)

        for tt in target_list:
            if tt.hash_value == transfer_target.hash_value:
                raise ValueError('Duplicate target position %s.' \
                                 % (tt.hash_value))

        target_list.append(transfer_target)

    def get_parameter_tag(self, parameter):
        """
        The method needs to be overwritten because the value for the molecule
        designs tag is a concatenated string.
        """
        if parameter in self.PARAMETER_SET.TRANSFER_TARGET_PARAMETERS:
            return self.get_targets_tag(parameter)
        elif parameter in self.PARAMETER_SET.TRANSFER_TARGET_PARAMETERS \
                    and len(self.get_transfer_target_list(parameter)) == 0:
            return None
        else:
            return MoleculeDesignPoolPosition.get_parameter_tag(self, parameter)

    def get_targets_tag_value(self, parameter_name=None):
        """
        Returns the target well tag value of the specified parameter
        (by default: :attr:`TRANSFER_TARGETS`).
        """
        target_list = self.get_transfer_target_list(parameter_name)
        targets = []
        for tt in target_list: targets.append(tt.target_info)
        return self.TARGETS_DELIMITER.join(sorted(targets))

    @classmethod
    def parse_target_tag_value(cls, target_tag_value):
        """
        Returns a list of transfer targets for the given target tag value.

        :param target_tag_value: The tag value to be parsed.
        :type target_tag_value: :class:`str`
        :return: A list of :class:`TransferTarget` objects.
        :raises ValueError: If the string cannot be parsed or there are
            duplicate targets.
        """
        tokens = target_tag_value.split(cls.TARGETS_DELIMITER)
        target_list = set()
        for token in tokens:
            tt = TransferTarget.parse_info_string(token)
            if tt in target_list:
                msg = 'Duplicate transfer target: %s!' % (tt.hash_value)
                raise ValueError(msg)
            target_list.add(tt)

        return list(target_list)

    def get_targets_tag(self, parameter_name=None):
        """
        Returns the transfer target tag forrthe specified parameter
        (by default: :attr:`TRANSFER_TARGETS`).
        """
        return Tag(TransferParameters.DOMAIN,
                   self.PARAMETER_SET.TRANSFER_TARGETS,
                   self.get_targets_tag_value(parameter_name))

    def _get_parameter_values_map(self):
        """
        Returns a map containing the value for each parameter.
        """
        parameter_map = MoleculeDesignPoolPosition._get_parameter_values_map(
                                                                        self)
        parameter_map[self.PARAMETER_SET.TRANSFER_TARGETS] = \
                                                        self.transfer_targets
        return parameter_map

    def __eq__(self, other):
        if not isinstance(other, TransferPosition): return False
        return self.rack_position == other.rack_position \
            and self.molecule_design_pool == other.molecule_design_pool \
            and self.get_targets_tag_value() == other.get_targets_tag_value()

    def __repr__(self):
        str_format = '<%s rack position: %s, pool: %s, targets: %s>'
        params = (self.__class__.__name__, self.rack_position,
                  self.molecule_design_pool, self.get_targets_tag_value())
        return str_format % params


class TransferLayout(MoleculeDesignPoolLayout):
    """
    A working container for transfer layouts. Transfer layouts are used
    to generate rack layouts for liquid transfer plans (sample transfer type).
    """
    #: The working position class this layout is associated with.
    WORKING_POSITION_CLS = TransferPosition

    #: Short cut to the transfer target parameters of the working position
    #: parameter set.
    _TRANSFER_TARGET_PARAMETERS = WORKING_POSITION_CLS.PARAMETER_SET.\
                                  TRANSFER_TARGET_PARAMETERS

    def __init__(self, shape):
        """
        Constructor:

        :param shape: The rack shape.
        :type shape: :class:`thelma.models.rack.RackShape`
        """
        if self.__class__ == TransferLayout:
            raise NotImplementedError('Abstract class')
        MoleculeDesignPoolLayout.__init__(self, shape=shape)

        #: The transfer targets for each transfer target parameter mapped
        #: onto rack positions.
        self._transfer_target_map = dict()
        for parameter in self._TRANSFER_TARGET_PARAMETERS:
            self._transfer_target_map[parameter] = dict()

    def add_position(self, working_position):
        """
        Adds a :class:`Working_position` to the layout.

        :param working_position: The transfer position to be added.
        :type working_position: :class:`TransferPosition`
        :raises TypeError: If the added position is not a
            :class:`TransferPosition` object.
        """
        if not isinstance(working_position, self.WORKING_POSITION_CLS):
            msg = 'A position to be added must be a %s object (obtained ' \
                  'type: %s).' % (self.WORKING_POSITION_CLS,
                                  working_position.__class__.__name__)
            raise TypeError(msg)

        for parameter in self._TRANSFER_TARGET_PARAMETERS:
            target_list = working_position.get_transfer_target_list(parameter)
            tt_map = self._transfer_target_map[parameter]
            if not len(target_list) < 1:
                for tt in target_list:
                    if tt_map.has_key(tt.hash_value):
                        msg = 'Duplicate target well %s!' % (tt.hash_value)
                        raise ValueError(msg)
                    else:
                        source_label = working_position.rack_position.label
                        tt_map[tt.hash_value] = source_label

        MoleculeDesignPoolLayout.add_position(self, working_position)

    def del_position(self, rack_position):
        """
        Deletes the working position for that rack position.
        """
        tp = self._position_map[rack_position]

        if tp is not None:
            for parameter in self._TRANSFER_TARGET_PARAMETERS:
                target_list = tp.get_transfer_target_list(parameter)
                tt_map = self._transfer_target_map[parameter]
                for tt in target_list:
                    del tt_map[tt.hash_value()]

        if tp is not None:
            del self._position_map[rack_position]


class LibraryLayoutParameters(ParameterSet):
    """
    Marks which position in library are reserved for library position.
    """
    DOMAIN = 'library_base_layout'

    #: If *True* the position in a library plate will contain a library sample.
    IS_LIBRARY_POS = 'is_library_position'

    REQUIRED = [IS_LIBRARY_POS]
    ALL = [IS_LIBRARY_POS]

    ALIAS_MAP = {IS_LIBRARY_POS : ['is_sample_position']}
    DOMAIN_MAP = {IS_LIBRARY_POS : DOMAIN}


class LibraryLayoutPosition(WorkingPosition):
    """
    There is actually only one value for a position in a library layout
    and this is the availability for library samples.

    **Equality condition**: equal :attr:`rack_position` and
        :attr:`is_sample_pos`
    """
    PARAMETER_SET = LibraryLayoutParameters

    RECORD_FALSE_VALUES = False

    def __init__(self, rack_position, is_library_position=True):
        """
        Constructor:

        :param rack_position: The rack position.
        :type rack_position: :class:`thelma.models.rack.RackPosition`.

        :param is_library_position: Is this position reserved for library
            positions?
        :type is_library_position: :class:`bool`
        """
        WorkingPosition.__init__(self, rack_position)

        if not isinstance(is_library_position, bool):
            msg = 'The "library position" flag must be a bool (obtained: %s).' \
                  % (is_library_position.__class__.__name__)
            raise TypeError(msg)

        #: Is this position reserved for library samples?
        self.is_library_position = is_library_position

    def _get_parameter_values_map(self):
        """
        Returns a map with key = parameter name, value = associated attribute.
        """
        return {self.PARAMETER_SET.IS_LIBRARY_POS : self.is_library_position}

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
                other.rack_position == self.rack_position and \
                other.is_library_position == self.is_library_position

    def __repr__(self):
        str_format = '<%s rack position: %s, is library position: %s>'
        params = (self.__class__.__name__, self.rack_position,
                  self.is_library_position)
        return str_format % params


class LibraryLayout(WorkingLayout):
    """
    Defines which position in a library may contain library samples.
    """
    WORKING_POSITION_CLASS = LibraryLayoutPosition

    def __init__(self, shape):
        """
        Constructor:

        :param shape: The rack shape.
        :type shape: :class:`thelma.models.rack.RackShape`
        """
        WorkingLayout.__init__(self, shape)

        #: You cannot add new positions to a closed layout.
        self.is_closed = False

    def add_position(self, working_position):
        """
        Adds a :class:`Working_position` to the layout.

        :param working_position: The working position to be added.
        :type working_position: :class:`LibraryBaseLayoutPosition`

        :raises ValueError: If the added position is not a
            :attr:`WORKING_POSITION_CLASS` object.
        :raises AttributeError: If the layout is closed.
        :raises TypeError: if the position has the wrong type
        """
        if not self.is_closed:
            WorkingLayout.add_position(self, working_position)
        else:
            raise AttributeError('The layout is closed!')

    def close(self):
        """
        Removes all positions that may not contain samples.
        """
        if not self.is_closed:

            del_positions = []
            for rack_pos, libbase_pos in self._position_map.iteritems():
                if not libbase_pos.is_sample_position:
                    del_positions.append(rack_pos)

            for rack_pos in del_positions: del self._position_map[rack_pos]

            self.is_closed = True

    def create_rack_layout(self):
        """
        The layout is closed before rack layout creation.
        """
        self.close()
        return WorkingLayout.create_rack_layout(self)
