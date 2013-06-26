"""
This module contains classes and functions for semi-constants entities
such as rack shapes, reservoir specs etc., that are used often but
changed rarely.

This also comprises and number of caching classes. The idea of the caching
is to provide a shortcut access to a number of frequently used entities
without having to load the entity from the DB (and thus triggering a
premature autoflush).
The caches can be initialised and cleared using
:func:`initialize_semiconstant_caches` and :func:`clear_semiconstant_caches`.


is to load all entities before a tool is started to avoid autoflushes
during the tool run.

AAB
"""
from everest.entities.utils import get_root_aggregate
from everest.querying.specifications import lt
from everest.repositories.rdb.utils import as_slug_expression
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.interfaces import IExperimentMetadataType
from thelma.interfaces import IItemStatus
from thelma.interfaces import IPipettingSpecs
from thelma.interfaces import IPlateSpecs
from thelma.interfaces import IRackPosition
from thelma.interfaces import IRackShape
from thelma.interfaces import IReservoirSpecs
from thelma.models.experiment import ExperimentMetadataType
from thelma.models.liquidtransfer import PipettingSpecs
from thelma.models.liquidtransfer import ReservoirSpecs
from thelma.models.rack import PlateSpecs
from thelma.models.rack import RACK_POSITION_REGEXP
from thelma.models.rack import RackShape
from thelma.models.status import ITEM_STATUSES
from thelma.models.utils import label_from_number


__docformat__ = 'reStructuredText en'

__all__ = ['SemiconstantCache',
           'ITEM_STATUS_NAMES',
           'get_item_status',
           'get_item_status_managed',
           'get_item_status_future',
           'EXPERIMENT_SCENARIOS',
           'get_experiment_metadata_type',
           'get_experiment_type_robot_optimisation',
           'get_experiment_type_screening',
           'get_experiment_type_manual_optimisation',
           'get_experiment_type_isoless',
           'get_experiment_type_library',
           'get_experiment_type_order',
           'RACK_SHAPE_NAMES',
           'get_96_rack_shape',
           'get_384_rack_shape',
           'get_positions_for_shape',
           'PIPETTING_SPECS_NAMES',
           'get_pipetting_specs',
           'get_pipetting_specs_manual',
           'get_pipetting_specs_cybio',
           'get_pipetting_specs_biomek',
           'get_min_transfer_volume',
           'get_max_transfer_volume',
           'get_max_dilution_factor',
           'RESERVOIR_SPECS_NAMES',
           'get_reservoir_spec',
           'get_reservoir_specs_standard_96',
           'get_reservoir_specs_deep_96',
           'get_reservoir_specs_standard_384',
           'PLATE_SPECS_NAMES',
           'get_plate_specs_from_reservoir_specs',
           'get_reservoir_specs_from_plate_specs',
           'RACK_POSITION_LABELS',
           'get_rack_position_from_label',
           'get_rack_position_from_indices',
           'initialize_semiconstant_caches',
           'clear_semiconstant_caches',
           ]


class SemiconstantCache(object):
    """
    A base class of semi-constant caches.
    Entities are identified by the label or name that is used a slug.
    """

    #: Contains the names of all known entities.
    ALL = None

    #: The marker interface for the supported entity class.
    _MARKER_INTERFACE = None
    #: The aggregate for the entity class.
    _aggregate = None

    #: The cache (entities mapped onto identifiers).
    _cache = dict()

    #: Shall the entity identifier be converted to a slug or be used directly?
    _CONVERT_TO_SLUG = True

    @classmethod
    def from_name(cls, entity_identifier):
        """
        Returns the entity instance for the given name (loads it either from
        the DB or from the cache).

        :param entity_identifier: The name or label that is used as slug
            for the entity.
        :type entity_identifier: :class:`basestring`

        :raises TypeError: If the entity_identifier is not a basestring.
        :raises ValueError: If the entity_identifier is not registered in
            :attr:`ALL`.
        """
        if not isinstance(entity_identifier, basestring):
            msg = 'The entity identifier must be a basestring (obtained: %s).' \
                   % (entity_identifier.__class__.__name__)
            raise TypeError(msg)
        if not cls.is_known_entity(entity_identifier):
            msg = 'Unknown entity identifier "%s".' % (entity_identifier)
            raise ValueError(msg)

        if cls._cache.has_key(entity_identifier):
            return cls._cache[entity_identifier]

        entity = cls._get_entity_from_aggregate(entity_identifier)
        cls._cache[entity_identifier] = entity
        return entity

    @classmethod
    def is_known_entity(cls, entity_identifier):
        """
        Checks whether the given identifier is registered in :attr:`ALL`.
        """
        return entity_identifier in cls.ALL

    @classmethod
    def initialize_cache(cls):
        """
        Loads all known entities from the DB and loads it into the
        :attr:`_cache`. The cache can be cleared by calling
        :func:`clear_chache`.
        """
        for entity_name in cls.ALL:
            entity = cls._get_entity_from_aggregate(entity_name)
            cls._cache[entity_name] = entity

    @classmethod
    def clear_cache(cls):
        """
        Removes all entities from the cache. The cache can be re-initialised
        by calling :func:`initialize_chache`.
        """
        cls._cache = dict()
        cls._aggregate = None

    @classmethod
    def _get_entity_from_aggregate(cls, entity_identifier):
        """
        Retrieves the entity for the given identifier from the aggregate.
        """
        cls._initialize_aggregate()
        if cls._CONVERT_TO_SLUG:
            slug = as_slug_expression(entity_identifier)
        else:
            slug = entity_identifier
        return cls._aggregate.get_by_slug(slug)

    @classmethod
    def _initialize_aggregate(cls):
        """
        Initialises the aggregate for the supported entity class (if it has
        not be initialised so far).
        """
        if cls._aggregate is None:
            cls._aggregate = get_root_aggregate(cls._MARKER_INTERFACE)


class ITEM_STATUS_NAMES(SemiconstantCache):
    """
    Caching and shortcuts for :class:`thelma.models.status.ItemStatus` entities.
    """
    MANAGED = ITEM_STATUSES.MANAGED
    FUTURE = ITEM_STATUSES.FUTURE
    UNMANAGED = ITEM_STATUSES.UNMANAGED
    DESTROYED = ITEM_STATUSES.DESTROYED

    ALL = [MANAGED, FUTURE, UNMANAGED, DESTROYED]
    _MARKER_INTERFACE = IItemStatus

#: A short cut for :func:`ITEM_STATUS_NAMES.from_name`.
get_item_status = ITEM_STATUS_NAMES.from_name

#: A short cut to get the managed item status.
def get_item_status_managed():
    return get_item_status(ITEM_STATUS_NAMES.MANAGED)

#: A short cut to get the future item status.
def get_item_status_future():
    return get_item_status(ITEM_STATUS_NAMES.FUTURE)


class EXPERIMENT_SCENARIOS(SemiconstantCache):
    """
    Caching and shortcuts for
    :class:`thelma.models.experiment.ExperimentMetadataType` entities.
    """
    OPTIMISATION = 'OPTI'
    SCREENING = 'SCREEN'
    MANUAL = 'MANUAL'
    ISO_LESS = 'ISO-LESS'
    LIBRARY = 'LIBRARY'
    ORDER_ONLY = 'ORDER-ONLY'
    QPCR = 'QPCR'

    ALL = [OPTIMISATION, SCREENING, MANUAL, ISO_LESS, LIBRARY, ORDER_ONLY, QPCR]
    _MARKER_INTERFACE = IExperimentMetadataType

    @classmethod
    def get_displaynames(cls, experiment_metadata_types):
        """
        Convenience method returning the display names of the given
        experiment metadata types.

        Invokes :func:`from_name`
        """
        display_names = []
        for em_type in experiment_metadata_types:
            if isinstance(em_type, ExperimentMetadataType):
                display_name = em_type.display_name
            elif isinstance(em_type, basestring):
                entity = cls.from_name(em_type)
                display_name = entity.display_name
            display_names.append(display_name)

        return display_names

#: A shortcut for :func:`EXPERIMENT_SCENARIOS.from_name`.
get_experiment_metadata_type = EXPERIMENT_SCENARIOS.from_name

#: A shortcut to get the robot optimisation experiment metadata type.
def get_experiment_type_robot_optimisation():
    return get_experiment_metadata_type(EXPERIMENT_SCENARIOS.OPTIMISATION)

#: A shortcut to get the screening experiment metadata type.
def get_experiment_type_screening():
    return get_experiment_metadata_type(EXPERIMENT_SCENARIOS.SCREENING)

#: A shortcut to get the manual optimisation experiment metadata type.
def get_experiment_type_manual_optimisation():
    return get_experiment_metadata_type(EXPERIMENT_SCENARIOS.MANUAL)

#: A shortcut to get the ISO-less experiment metadata type.
def get_experiment_type_isoless():
    return get_experiment_metadata_type(EXPERIMENT_SCENARIOS.ISO_LESS)

#: A shortcut to get the library screening experiment metadata type.
def get_experiment_type_library():
    return get_experiment_metadata_type(EXPERIMENT_SCENARIOS.LIBRARY)

#: A shortcut to get the order only experiment metadata type.
def get_experiment_type_order():
    return get_experiment_metadata_type(EXPERIMENT_SCENARIOS.ORDER_ONLY)


class RACK_SHAPE_NAMES(SemiconstantCache):
    """
    Caching and shortcuts for :class:`thelma.models.rack.RackShape` entities.
    """
    SHAPE_96 = '8x12'
    SHAPE_384 = '16x24'

    #: In this case, only the standard shapes with 96 and 384 positions.
    ALL = [SHAPE_96, SHAPE_384]
    _MARKER_INTERFACE = IRackShape

    _POSITION_NUMBERS = {96 : SHAPE_96, 384 : SHAPE_384}

    #: Stores the ordered positions for a certain rack shape (shape name
    #: as key, value is dict with vertical sorting as key, positions as value))
    __shape_positions = dict()

    @classmethod
    def from_positions_count(cls, position_count):
        """
        Returns the rack shape instance for the given name (loads it
        either from the DB or from the cache).

        :Note: Invokes :func:`get_from_name`

        :raises ValueError: If the positions is not associated with a known
            rack shape.
        """
        if not cls._POSITION_NUMBERS.has_key(position_count):
            msg = 'There is no rack shape associated with this position ' \
                  'count (%i positions)!' % (position_count)
            raise ValueError(msg)

        rack_shape_name = cls._POSITION_NUMBERS[position_count]
        return cls.from_name(rack_shape_name)

    @classmethod
    def clear_cache(cls):
        """
        Removes all entities from the cache. The cache can be re-initialised
        by calling :func:`initialize_chache`.
        """
        SemiconstantCache.clear_cache()
        cls.__shape_positions = dict()

    @classmethod
    def get_positions_for_shape(cls, rack_shape, vertical_sorting=False):
        """
        Returns all rack positions (:class:`RackPosition`)
        comprised by this rack shape. The sorting can be horizontal
        (A1, A2, A3, etc.) or vertical (A1, B1, etc.).

        The positions are cached.

        :param rack_shape: A rack shape or its name:
        :type rack_shape: :class:`thelma.models.rack.RackShape` or
            :class:`basestring`

        :param vertical_sorting: Set to *True* for vertical sorting and to
            *False* for horizontal sorting.
        :type vertical_sorting: :class:`bool`
        :default vertical_sorting: *False*

        :return: The rack positions of the rack shape as list sorted by the
            chosen direction.
        """
        if isinstance(rack_shape, RackShape):
            shape_name = rack_shape.name
            shape_entity = rack_shape
        elif isinstance(rack_shape, basestring):
            shape_entity = cls.from_name(rack_shape)
            shape_name = rack_shape
        else:
            msg = 'Unexpected type for rack shape (%s). Allowed types are ' \
                  'string and %s.' % (rack_shape.__class__.__name__,
                                      RackShape.__name__)
            raise TypeError(msg)

        lookup = None
        if cls.__shape_positions.has_key(shape_name):
            lookup = cls.__shape_positions[shape_name]
            if lookup.has_key(vertical_sorting):
                return lookup[vertical_sorting]

        positions = []

        row_values = [0, 'number_rows']
        col_values = [0, 'number_columns']

        if vertical_sorting:
            prime_values = col_values
            sec_values = row_values
        else:
            prime_values = row_values
            sec_values = col_values

        for prime_index in range(getattr(shape_entity, prime_values[1])):
            prime_values[0] = prime_index
            for sec_index in range(getattr(shape_entity, sec_values[1])):
                sec_values[0] = sec_index
                coords = (row_values[0], col_values[0])
                rack_pos = get_rack_position_from_indices(*coords)
                positions.append(rack_pos)

        if lookup is None:
            lookup = {vertical_sorting : positions}
        else:
            lookup[vertical_sorting] = positions
        cls.__shape_positions[shape_name] = lookup

        return positions


#: A shortcut to get the 96-well rack shape.
def get_96_rack_shape():
    return RACK_SHAPE_NAMES.from_name(RACK_SHAPE_NAMES.SHAPE_96)

#: A shortcut to get the 384-well rack shape.
def get_384_rack_shape():
    return RACK_SHAPE_NAMES.from_name(RACK_SHAPE_NAMES.SHAPE_384)

#: A shortcut returning all positions of a rack shape.
def get_positions_for_shape(rack_shape, vertical_sorting=False):
    return RACK_SHAPE_NAMES.get_positions_for_shape(rack_shape,
                                                    vertical_sorting)


class PIPETTING_SPECS_NAMES(SemiconstantCache):
    """
    Caching and shortcuts for
    :class:`thelma.models.liquidtransfer.PipettingSpecs` entities.
    """
    MANUAL = 'manual'
    CYBIO = 'CyBio'
    BIOMEK = 'BioMek'

    ALL = [MANUAL, CYBIO, BIOMEK]
    _MARKER_INTERFACE = IPipettingSpecs

    @classmethod
    def get_min_transfer_volume(cls, pipetting_specs):
        """
        Returns the minimum transfer volume for the given pipetting specs in ul.

        Invokes :func:`from_name`.

        :param pipetting_specs: The pipetting specs whose minimum volume you
            want to get or its name.
        :type pipetting_specs: :class:`basestring` or
            :class:`thelma.models.liquidtransfer.PipettingSpecs`
        :return: The minimum transfer volume in ul.
        """
        if not isinstance(pipetting_specs, PipettingSpecs):
            pipetting_specs = cls.from_name(pipetting_specs)

        return pipetting_specs.min_transfer_volume * VOLUME_CONVERSION_FACTOR

    @classmethod
    def get_max_transfer_volume(cls, pipetting_specs):
        """
        Returns the maximum transfer volume for the given pipetting specs in ul.

        Invokes :func:`from_name`.

        :param pipetting_specs: The pipetting specs whose maximum volume you
            want to get or its name.
        :type pipetting_specs: :class:`basestring` or
            :class:`thelma.models.liquidtransfer.PipettingSpecs`
        :return: The minimum transfer volume in ul.
        """
        if not isinstance(pipetting_specs, PipettingSpecs):
            pipetting_specs = cls.from_name(pipetting_specs)

        return pipetting_specs.max_transfer_volume * VOLUME_CONVERSION_FACTOR

    @classmethod
    def get_max_dilution_factor(cls, pipetting_specs):
        """
        Returns the maximum dilution factor (for a single transfer).
        Pipetting larger dilution might result in inaccurate target
        concentrations or inhomogenous mixing.

        Invokes :func:`from_name`.

        :param pipetting_specs: The pipetting specs whose maximum dilution
            factor you want to get or its name.
        :type pipetting_specs: :class:`basestring` or
            :class:`thelma.models.liquidtransfer.PipettingSpecs`
        :return: The maximum dilution factor for a single transfer.
        """
        if not isinstance(pipetting_specs, PipettingSpecs):
            pipetting_specs = cls.from_name(pipetting_specs)

        return pipetting_specs.max_dilution_factor

#: A short cut for :func:`PIPETTING_SPECS_NAMES.from_name`.
get_pipetting_specs = PIPETTING_SPECS_NAMES.from_name

#: A short cut to get the manual pipetting specs.
def get_pipetting_specs_manual():
    return get_pipetting_specs(PIPETTING_SPECS_NAMES.MANUAL)

#: A short cut to get the CyBio pipetting specs.
def get_pipetting_specs_cybio():
    return get_pipetting_specs(PIPETTING_SPECS_NAMES.CYBIO)

#: A short cut to get the BioMek pipetting specs.
def get_pipetting_specs_biomek():
    return get_pipetting_specs(PIPETTING_SPECS_NAMES.BIOMEK)

#: A short cut for :func:`PIPETTING_SPECS_NAMES.get_min_transfer_volume`.
get_min_transfer_volume = PIPETTING_SPECS_NAMES.get_min_transfer_volume
#: A short cut for :func:`PIPETTING_SPECS_NAMES.get_max_transfer_volume`.
get_max_transfer_volume = PIPETTING_SPECS_NAMES.get_max_transfer_volume
#: A short cut for :func:`PIPETTING_SPECS_NAMES.get_max_dilution_factor`.
get_max_dilution_factor = PIPETTING_SPECS_NAMES.get_max_dilution_factor


class RESERVOIR_SPECS_NAMES(SemiconstantCache):
    """
    Caching and shortcuts for
    :class:`thelma.models.liquidtransfer.ResevoirSpecs` entities.
    """
    QUARTER_MODULAR = 'quarter mod'
    TUBE_24 = 'microfuge plate'
    STANDARD_96 = 'plate 96 std'
    DEEP_96 = 'plate 96 deep'
    STANDARD_384 = 'plate 384 std'
    FALCON_MANUAL = 'falcon tube'

    ALL = [QUARTER_MODULAR, TUBE_24, STANDARD_96, STANDARD_384, DEEP_96,
           FALCON_MANUAL]
    PLATE_SPECS = [STANDARD_96, STANDARD_384, DEEP_96]

    _MARKER_INTERFACE = IReservoirSpecs

    @classmethod
    def is_plate_spec(cls, reservoir_spec):
        """
        Returns *True* if the passed reservoir specs is a plate spec.

        :param reservoir_specs: a reservoir spec
        :type reservoir_specs: :class:`basestring` or :class:`ReservoirSpecs`

        :return: *True*, if the spec is a plate spec

        :raise TypeError: if reservoir_specs has an unexpected class
        :raise ValueError: if the reservoir_specs is not known
        """
        if isinstance(reservoir_spec, basestring):
            rs_name = reservoir_spec
        elif isinstance(reservoir_spec, ReservoirSpecs):
            rs_name = reservoir_spec.name
        else:
            msg = 'The reservoir spec must be a basestring or a %s ' \
                  '(obtained: %s).' % (ReservoirSpecs.__name__,
                                       reservoir_spec.__class__.__name__)
            raise TypeError(msg)

        if not cls.is_known_entity(rs_name):
            msg = 'Unknown reservoir specs name: "%s".' % (rs_name)
            raise ValueError(msg)

        return rs_name in cls.PLATE_SPECS


#: An alias for :func:RESERVOIR_SPECS_NAMES.get_reservoir_spec`
get_reservoir_spec = RESERVOIR_SPECS_NAMES.from_name

#: A shortcut to get the standard 96-well reservoir specs.
def get_reservoir_specs_standard_96():
    return get_reservoir_spec(RESERVOIR_SPECS_NAMES.STANDARD_96)

#: A shortcut to get the deep well 96-well reservoir specs.
def get_reservoir_specs_deep_96():
    return get_reservoir_spec(RESERVOIR_SPECS_NAMES.DEEP_96)

#: A shortcut to get the standard 384ll reservoir specs.
def get_reservoir_specs_standard_384():
    return get_reservoir_spec(RESERVOIR_SPECS_NAMES.STANDARD_384)


class PLATE_SPECS_NAMES(SemiconstantCache):
    """
    Caching and shortcuts for :class:`thelma.models.rack.PlateSpecs` entities.
    """
    STANDARD_96 = 'BIOMEK96STD'
    STANDARD_384 = 'STD384'
    DEEP_96 = 'BIOMEK96DEEP'

    ALL = [STANDARD_96, DEEP_96, STANDARD_384]
    _MARKER_INTERFACE = IPlateSpecs

    __RESERVOIR_SPECS_MAP = {
            RESERVOIR_SPECS_NAMES.STANDARD_96 : STANDARD_96,
            RESERVOIR_SPECS_NAMES.STANDARD_384 : STANDARD_384,
            RESERVOIR_SPECS_NAMES.DEEP_96 : DEEP_96
                             }

    @classmethod
    def from_reservoir_specs(cls, reservoir_specs):
        """
        Returns the plate specs instance for the given reservoir specs
        (loads it either from the DB or from the cache).

        :param reservoir_specs: The reservoir specs whose plate specs
            you want to get.
        :type reservoir_specs: :class:`str` (name of reservoir specs) or
            :class:`thelma.models.liquidtransfer.ReservoirSpecs`

        :raises TypeError: If the type of reservoir specs is unexpected.
        :raises ValueError: If the reservoir specs is unknown.

        :return: :class:`thelma.models.rack.PlateSpecs`
        """
        if isinstance(reservoir_specs, basestring):
            rs_name = reservoir_specs
        elif isinstance(reservoir_specs, ReservoirSpecs):
            rs_name = reservoir_specs.name
        else:
            msg = 'Unsupported type for reservoir specs: %s.'\
                   % (reservoir_specs.__class__.__name__)
            raise TypeError(msg)

        if not cls.__RESERVOIR_SPECS_MAP.has_key(rs_name):
            raise ValueError('Unsupported reservoir specs "%s".' % (rs_name))

        plate_specs_name = cls.__RESERVOIR_SPECS_MAP[rs_name]
        return cls.from_name(plate_specs_name)

    @classmethod
    def to_reservoir_specs(cls, plate_specs):
        """
        Returns the reservoir specs instance that corresponds to the given
        plate specs.

        :param plate_specs: the plate specs whose reservoir specs you want
            to get.
        :type plate_specs: :class:`basestring` or
            :class:`thelma.models.rack.PlateSpecs`

        :raises TypeError: If the type of plate specs is unexpected.
        :raises ValueError: If the plate specs is unknown or there is no
            reservoir specs stored for it.

        :return: :class:`thelma.models.liquidtransfer.ReservoirSpecs`
        """
        if isinstance(plate_specs, basestring):
            ps_name = plate_specs
        elif isinstance(plate_specs, PlateSpecs):
            ps_name = plate_specs.name
        else:
            msg = 'Unsupported type for plate specs: %s.'\
                   % (plate_specs.__class__.__name__)
            raise TypeError(msg)

        if not cls.is_known_entity(plate_specs.name):
            msg = 'Unsupported plate spec "%s".' % (ps_name)
            raise ValueError(msg)

        rs = None
        for rs_name, stored_ps_name in cls.__RESERVOIR_SPECS_MAP.iteritems():
            if ps_name == stored_ps_name:
                rs = get_reservoir_spec(rs_name)
                break
        if rs is None:
            msg = 'There is no reservoir specs stored for plate spec "%s"!' \
                  % (ps_name)
            raise ValueError(msg)

        return rs
#: A short cut for :func:`PLATE_SPECS_NAMES.from_reservoir_specs`.
get_plate_specs_from_reservoir_specs = PLATE_SPECS_NAMES.from_reservoir_specs

#: A short cut for :func:`PLATE_SPECS_NAMES.to_reservoir_specs`.
get_reservoir_specs_from_plate_specs = PLATE_SPECS_NAMES.to_reservoir_specs


class RACK_POSITION_LABELS(SemiconstantCache):
    """
    Caching and shortcuts for :class:`thelma.models.rack.RackPosition` entities.
    Unlike in other caches there are no default values and the cache is not
    initialised.
    """
    _MARKER_INTERFACE = IRackPosition
    _CONVERT_TO_SLUG = False

    __coordinate_cache = dict()

    @classmethod
    def from_name(cls, label):
        """
        Returns the rack position instance for the given name (=label; loads
        it either from the DB or from the cache).

        :param label: The label of the rack position.
        :type label: :class:`basestring`

        :raises TypeError: If the label is not a basestring.
        :raises ValueError: If there is not rack position for this label in
            the DB.
        """
        if not isinstance(label, basestring):
            msg = 'The rack position label must be a basestring (obtained: ' \
                  '%s).' % (label.__class__.__name__)
            raise TypeError(msg)
        else:
            label = cls.__clean_label(label)

        if cls._cache.has_key(label):
            return cls._cache[label]

        rack_pos = cls._get_entity_from_aggregate(label.lower())
        if rack_pos is None:
            msg = 'Unknown rack position "%s".' % (label)
            raise ValueError(msg)
        else:
            cls._cache[label] = rack_pos
            coords = (rack_pos.row_index, rack_pos.column_index)
            cls._cache[coords] = rack_pos

        return rack_pos

    @classmethod
    def __clean_label(cls, label):
        """
        The read-outs of some robot might contain zeros for decadic positions
        (e.g. H09 for H9). This 0 must be removed for rack position loading.
        """
        if not label[-2] == '0':
            return label
        else:
            return label[:-2] + label[-1:]

    @classmethod
    def from_indices(cls, row_index, column_index):
        """
        Returns the rack position instance for the given row and column indices
        (loads it either from the DB or from the cache).

        Invokes :func:`get_label` and :func:`from_name`.

        :param row_index: The row index (0-based) of the rack position.
        :type row_index: :class:`int`

        :param column_index: The column index (0-based) of the rack position.
        :type column_index: :class:`int`

        :raises TypeError: If one of the indices is not an non-negative integer.
        :raises ValueError: If there is not rack position for these indices in
            the DB.
        """
        coords = (row_index, column_index)
        if cls.__coordinate_cache.has_key(coords):
            return cls.__coordinate_cache[coords]

        label = cls.get_label(row_index, column_index)
        return cls.from_name(label)

    @classmethod
    def get_label(cls, row_index, column_index):
        """
        Return the label for the given row and column indices.

        :param row_index: The row index (0-based) of the rack position.
        :type row_index: :class:`int`

        :param column_index: The column index (0-based) of the rack position.
        :type column_index: :class:`int`

        :raises TypeError: If one of the indices is not an non-negative integer.
        :raises ValueError: If there is not rack position for these indices in
            the DB.
        """
        if not cls.is_positive_integer(row_index):
            raise ValueError('The row index must be a non-negative integer ' \
                             '(obtained: %s).' % (row_index))
        if not cls.is_positive_integer(column_index):
            raise ValueError('The column index must be a non-negative ' \
                             'integer (obtained: %s).' % (column_index))

        return '%s%d' % (label_from_number(row_index + 1), column_index + 1)

    @classmethod
    def is_positive_integer(cls, value):
        """
        Checks whether a passed value is a valid positive integer.

        :param value: The value to be checked.
        :return: :class:`boolean`
        """
        try:
            value = int(value)
        except ValueError:
            return False

        return value >= 0

    @classmethod
    def is_known_entity(cls, entity_identifier):
        """
        Checks whether the given identifier is registered in :attr:`ALL`.
        """
        match = RACK_POSITION_REGEXP.match(entity_identifier)
        return not (match is None)

    @classmethod
    def initialize_cache(cls):
        """
        By default, we initialise all positions from 384-rack-shape in a
        one-step query. This is faster than fetching a potentially large
        number of positions one by one.
        """
        cls._initialize_aggregate()
        shape_384 = get_384_rack_shape()

        cls._aggregate.filter = lt(_row_index=shape_384.number_rows) \
                                & lt(_column_index=shape_384.number_columns)
        iterator = cls._aggregate.iterator()
        while True:
            try:
                rack_pos = iterator.next()
            except StopIteration:
                break
            else:
                cls._cache[rack_pos.label] = rack_pos
                coords = (rack_pos.row_index, rack_pos.column_index)
                cls.__coordinate_cache[coords] = rack_pos

        cls._aggregate.filter = None

    @classmethod
    def clear_cache(cls):
        """
        Removes all entities from the cache.
        """
        cls._aggregate = None
        cls._cache = dict()
        cls.__coordinate_cache = dict()

#: A short cut for :func:`RACK_POSITION_LABELS.from_name`
get_rack_position_from_label = RACK_POSITION_LABELS.from_name

#: A short cut for :func:`RACK_POSITION_LABELS.from_indices`
get_rack_position_from_indices = RACK_POSITION_LABELS.from_indices


__ALL_SEMICONSTANT_CLASSES = [ITEM_STATUS_NAMES,
                              RACK_SHAPE_NAMES,
                              RESERVOIR_SPECS_NAMES,
                              PLATE_SPECS_NAMES,
                              RACK_POSITION_LABELS,
                              ]

def initialize_semiconstant_caches():
    """
    Initialises the caches for all semiconstant classes registered in
    :attr:`_MARKER_INTERFACE`.
    """
    for semiconstant_cache_cls in __ALL_SEMICONSTANT_CLASSES:
        semiconstant_cache_cls.initialize_cache()

def clear_semiconstant_caches():
    """
    Clears the caches for all semiconstant classes registered in
    :attr:`_MARKER_INTERFACE`.
    """
    for semiconstant_cache_cls in __ALL_SEMICONSTANT_CLASSES:
        semiconstant_cache_cls.clear_cache()
