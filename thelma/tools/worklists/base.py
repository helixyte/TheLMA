"""
Base constants, functions and classes for liquid transfers.

AAB
"""
from thelma.tools.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.tools.semiconstants import get_positions_for_shape
from thelma.tools.semiconstants import get_reservoir_spec
from thelma.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.entities.liquidtransfer import ReservoirSpecs

__docformat__ = 'reStructuredText en'

__all__ = ['TRANSFER_ROLES',
           'LIMIT_TARGET_WELLS',
           'DEAD_VOLUME_COEFFICIENT',
           'get_dynamic_dead_volume',
           'EmptyPositionManager',
           ]


#: This refers to the dynamic dead volume calculation for the Biomek.
#: It is the maximum number of targets well a source might have before its
#: dead is corrected.
LIMIT_TARGET_WELLS = 3
#: This refers to the dynamic dead volume calculation for the Biomek.
#: It is the volume [in ul] that is added to the source volume for each new
#: new target well (if LIMIT_TARGET_WELLS is exceeded).
DEAD_VOLUME_COEFFICIENT = 1


class TRANSFER_ROLES(object):
    """
    Roles of racks or reservoirs in sample transfers
    """
    #: A source provides volumes.
    SOURCE = 'source'
    #: A target takes up volume.
    TARGET = 'target'


def get_dynamic_dead_volume(target_well_number,
                            reservoir_specs=RESERVOIR_SPECS_NAMES.STANDARD_96):
    """
    Calculate a dynamic dead volume (for pipetting specs that require dynamic
    dead volumes, such as Biomek).

    :param target_well_number: The number of target wells for the given
        source well.
    :type target_well_number: :class:` int`

    :param reservoir_specs: The reservoir specs you are assuming.
    :type reservoir_specs: a :class:`RESERVOIR_SPECS_NAMES` element or
        a :class:`thelma.entities.liquidtransfer.ReservoirSpecs` object
    :default reservoir_specs: RESERVOIR_SPECS_NAMES.STANDARD_96

    :Note: At the moment corrections are only applied to plates.

    :raises TypeError: if resrevoir_specs is not a string or ReservoirSpecs
    :return: The adjusted dead volume in ul.
    """

    if isinstance(reservoir_specs, ReservoirSpecs):
        rs = reservoir_specs
    elif isinstance(reservoir_specs, basestring):
        rs = get_reservoir_spec(reservoir_specs)
    else:
        msg = 'Unsupported type for reservoir specs: %s. Expectes string ' \
              'or ReservoirSpecs object.' % (reservoir_specs.__class__.__name__)
        raise TypeError(msg)

    # pylint: disable=E1103
    min_dead_volume_ul = rs.min_dead_volume * VOLUME_CONVERSION_FACTOR
    max_dead_volume_ul = rs.max_dead_volume * VOLUME_CONVERSION_FACTOR
    # pylint: enable=E1103

    if min_dead_volume_ul == max_dead_volume_ul:
        return min_dead_volume_ul

    if target_well_number <= LIMIT_TARGET_WELLS:
        return min_dead_volume_ul

    exceeding_well_count = target_well_number - LIMIT_TARGET_WELLS
    additional_volume = exceeding_well_count * DEAD_VOLUME_COEFFICIENT
    adjusted_dead_volume = min_dead_volume_ul + additional_volume
    if adjusted_dead_volume > max_dead_volume_ul:
        adjusted_dead_volume = max_dead_volume_ul
    return adjusted_dead_volume




class EmptyPositionManager(object):
    """
    Stores the empty positions of a layout and returns and removes
    them on request.
    """

    def __init__(self, rack_shape):
        """
        Constructor:

        :param rack_shape: The rack shape of the managed layout.
        :type rack_shape: :class:`thelma.entities.rack.RackShape`
        """
        #: The rack shape of the managed layout.
        self.rack_shape = rack_shape

        #: Contains all empty ISO positions.
        self._all_empty_positions = set()

        self._init_empty_positions()

    def _init_empty_positions(self):
        """
        Initialises the maps.
        """
        for rack_pos in get_positions_for_shape(self.rack_shape):
            self._all_empty_positions.add(rack_pos)

    def has_empty_positions(self):
        """
        Returns *True*, if there are still empty positions left.
        """
        if len(self._all_empty_positions) > 0:
            return True
        else:
            return False

    def add_empty_position(self, rack_pos):
        """
        Adds an empty position.

        :param rack_pos: The new empty rack pos.
        :type rack_pos: :class:`thelma.entities.rack.RackPosition`
        """
        self._all_empty_positions.add(rack_pos)

    def get_empty_position(self):
        """
        Returns the position with the lowest column and row index
        (and removes it from the pool).

        :raises ValueError: If there is no empty position left.
        """
        picked_position = None

        for rack_pos in get_positions_for_shape(self.rack_shape):
            if rack_pos in self._all_empty_positions:
                picked_position = rack_pos
                break

        if picked_position is None:
            raise ValueError('No empty position left!')

        self._all_empty_positions.discard(picked_position)
        return picked_position
