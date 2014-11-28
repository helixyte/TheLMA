"""
"""
from thelma.tools.iso.poolcreation.base import \
    LABELS as _POOL_CREATION_LABELS
from thelma.tools.iso.poolcreation.base import \
    StockSampleCreationLayout
from thelma.tools.iso.poolcreation.base import \
    StockSampleCreationLayoutConverter
from thelma.tools.stock.base import get_default_stock_concentration
from thelma.tools.utils.converters import BaseLayoutConverter
from thelma.tools.utils.layouts import ParameterSet
from thelma.tools.utils.layouts import WorkingLayout
from thelma.tools.utils.layouts import WorkingPosition
from thelma.entities.moleculetype import MOLECULE_TYPE_IDS


__docformat__ = 'reStructuredText en'
__all__ = []

#: Number of rack sectors (96-to-384 plate transition).
NUMBER_SECTORS = 4
#: The molecule type ID for the library.
DEFAULT_LIBRARY_MOLECULE_TYPE_ID = MOLECULE_TYPE_IDS.SIRNA
#: Default concentration of the pool stock racks in nM.
DEFAULT_POOL_STOCK_RACK_CONCENTRATION = 10000 # 10 uM
#: Default volume of the pool stock racks in ul.
DEFAULT_POOL_STOCK_RACK_VOLUME = 45
#: Default preparation plate concentration in nM.
DEFAULT_PREPARATION_PLATE_CONCENTRATION = 1270 # 1270 nM
#: Default preparation plate volume in ul.
DEFAULT_PREPARATION_PLATE_VOLUME = 43.3 # 43.3 ul
#: Default library aliquot plate concentration in nM.
DEFAULT_ALIQUOT_PLATE_CONCENTRATION = 1270 # 1270 nM
#: Default library aliquot plate volume in ul.
DEFAULT_ALIQUOT_PLATE_VOLUME = 4 # 4 ul
#: Default number of aliquots to create for each library plate.
DEFAULT_NUMBER_LIBRARY_PLATE_ALIQUOTS = 8
#: Default number of molecule designs per library pool.
DEFAULT_NUMBER_MOLECULE_DESIGNS = 3


def get_pool_buffer_volume():
    """
    Returns the volume of buffer to transfer to a library pool rack.
    """
    # The total transfer volume is equal to the transfer needed for "pools"
    # consisting of one single design.
    total_transfer_volume = get_pool_transfer_volume(number_designs=1)
    return round(DEFAULT_POOL_STOCK_RACK_VOLUME - total_transfer_volume, 1)


def get_pool_transfer_volume(number_designs=DEFAULT_NUMBER_MOLECULE_DESIGNS,
                             stock_concentration=None):
    """
    Returns the volume to transfer from a (single design) stock rack in ul to
    a library pool rack.

    :param int number_designs: Number of single molecule designs per library
        pool.
    :param str molecule_type_id: ID of the molecule design in the pool.
    """
    if stock_concentration is None:
        stock_concentration = \
            get_default_stock_concentration(DEFAULT_LIBRARY_MOLECULE_TYPE_ID)
    dilution_factor = float(stock_concentration) \
                      / DEFAULT_POOL_STOCK_RACK_CONCENTRATION
    total_vol = DEFAULT_POOL_STOCK_RACK_VOLUME / dilution_factor
    return round(total_vol / number_designs, 1)


def get_preparation_plate_transfer_volume(
                source_concentration=DEFAULT_POOL_STOCK_RACK_CONCENTRATION,
                preparation_plate_volume=DEFAULT_PREPARATION_PLATE_VOLUME):
    """
    Returns the volume to transfer to a preparation plate in ul for the given
    source concentration, preparation plate volume, and number of molecule
    designs.

    :param float source_concentration: Concentration of the source plate in
        nM. This is either the pool rack concentration or the single stock
        concentration, depending on the library creation process.
    :param float preparation_plate_volume: Volume of the preparation plate
        in ul.
    """
    dilution_factor = float(source_concentration) \
                      / DEFAULT_PREPARATION_PLATE_CONCENTRATION
    vol = preparation_plate_volume / dilution_factor
    return round(vol, 1)


def get_stock_transfer_volume(preparation_plate_volume=
                                            DEFAULT_PREPARATION_PLATE_VOLUME,
                              stock_concentration=None,
                              number_designs=DEFAULT_NUMBER_MOLECULE_DESIGNS):
    """
    Returns the (single) stock transfer volume for the given preparation
    plate volume, stock concentration and number of molecule designs per pool.
    """
    if stock_concentration is None:
        stock_concentration = \
            get_default_stock_concentration(DEFAULT_LIBRARY_MOLECULE_TYPE_ID)
    prep_vol = get_preparation_plate_transfer_volume(
                                    source_concentration=stock_concentration,
                                    preparation_plate_volume=
                                                preparation_plate_volume)
    return round(prep_vol / number_designs, 1)


class LibraryBaseLayoutParameters(ParameterSet):
    """
    This layout defines which positions in a library will contain samples.
    """
    DOMAIN = 'library_base_layout'

    #: If *True* the position in a library plate will contain a library sample.
    IS_SAMPLE_POS = 'is_sample_position'

    REQUIRED = [IS_SAMPLE_POS]
    ALL = [IS_SAMPLE_POS]

    ALIAS_MAP = {IS_SAMPLE_POS : []}
    DOMAIN_MAP = {IS_SAMPLE_POS : DOMAIN}


class LibraryBaseLayoutPosition(WorkingPosition):
    """
    There is actually only one value for a position in a library base layout
    and this is the availability for library samples.

    **Equality condition**: equal :attr:`rack_position` and
        :attr:`is_sample_position`
    """
    PARAMETER_SET = LibraryBaseLayoutParameters

    def __init__(self, rack_position, is_sample_position=True):
        """
        Constructor.

        :param rack_position: The rack position.
        :type rack_position: :class:`thelma.entities.rack.RackPosition`.
        :param bool is_sample_position: Is this position available for samples?
        """
        WorkingPosition.__init__(self, rack_position)
        if not isinstance(is_sample_position, bool):
            msg = 'The "sample position" flag must be a bool (obtained: %s).' \
                  % (is_sample_position.__class__.__name__)
            raise TypeError(msg)
        self.is_sample_position = is_sample_position

    def _get_parameter_values_map(self):
        """
        Returns a map with key = parameter name, value = associated attribute.
        """
        return {self.PARAMETER_SET.IS_SAMPLE_POS : self.is_sample_position}

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
                other.rack_position == self.rack_position and \
                other.is_sample_position == self.is_sample_position

    def __repr__(self):
        str_format = '<%s rack position: %s, is sample position: %s>'
        params = (self.__class__.__name__, self.rack_position,
                  self.is_sample_position)
        return str_format % params


class LibraryBaseLayout(WorkingLayout):
    """
    Defines which position in a library may contain library samples.
    """
    POSITION_CLS = LibraryBaseLayoutPosition

    def __init__(self, shape):
        """
        Constructor:

        :param shape: The rack shape.
        :type shape: :class:`thelma.entities.rack.RackShape`
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
            :attr:`POSITION_CLS` object.
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


class LibraryBaseLayoutConverter(BaseLayoutConverter):
    """
    Converts a :class:`thelma.entities.racklayout.RackLayout` into a
    :class:`LibraryBaseLayout`.
    """

    NAME = 'Library Base Layout Converter'

    PARAMETER_SET = LibraryBaseLayoutParameters
    LAYOUT_CLS = LibraryBaseLayout
    POSITION_CLS = LibraryBaseLayoutPosition

    def __init__(self, rack_layout, parent=None):
        BaseLayoutConverter.__init__(self, rack_layout, parent=parent)
        # intermediate storage of invalid rack positions
        self.__invalid_flag = None

    def reset(self):
        BaseLayoutConverter.reset(self)
        self.__invalid_flag = []

    def _get_position_init_values(self, parameter_map, rack_pos):
        """
        Derives a working position from a parameter map (including validity
        checks).
        """
        is_sample_pos_str = parameter_map[self.PARAMETER_SET.IS_SAMPLE_POS]
        pos_label = rack_pos.label

        if is_sample_pos_str is None: return None

        values = {str(True) : True, str(False) : False}

        if not values.has_key(is_sample_pos_str):
            info = '%s (%s)' % (pos_label, is_sample_pos_str)
            self.__invalid_flag.append(info)
        else:
            return dict(is_sample_position=values[is_sample_pos_str])

    def _record_errors(self):
        BaseLayoutConverter._record_errors(self)
        if len(self.__invalid_flag) > 0:
            msg = 'The "sample position" flag must be a boolean. The values ' \
                  'for some positions are invalid. Details: %s.' \
                  % (', '.join(sorted(self.__invalid_flag)))
            self.add_error(msg)

    def _perform_layout_validity_checks(self, working_layout):
        """
        We do not check anything but we close the layout.
        """
        working_layout.close()


class LibraryLayout(StockSampleCreationLayout):
    """
    A special :class:`StockSampleCreationLayout` for a plate involved
    in library generation (either :class:`IsoAliquotPlate` (rack shape 16x24)
    or :class:`IsoSectorPreparationPlate` (rack shape 8x12)).
    """
    def __init__(self, shape):
        """
        Constructor.

        :param shape: The rack shape.
        :type shape: :class:`thelma.entities.rack.RackShape`
        """
        StockSampleCreationLayout.__init__(self, shape)

        #: Allows validation of new position (is only set, if the layout is
        #: initialised via :func:`from_base_layout`.
        self.base_layout_positions = None

    @classmethod
    def from_base_layout(cls, base_layout):
        """
        Creates a new library layout which will only accept positions that
        are part of the base layout.
        """
        base_layout.close()
        layout = LibraryLayout(shape=base_layout.shape)
        layout.base_layout_positions = base_layout.get_positions()
        return layout

    def add_position(self, working_position):
        """
        Adds a :class:`Working_position` to the layout.

        :param working_position: The transfer position to be added.
        :type working_position: :class:`LibraryPosition`

        :raise ValueError: If the rack position is not allowed by the
            base layout.
        :raises TypeError: If the added position is not a
            :class:`TransferPosition` object.
        """
        rack_pos = working_position.rack_position
        if not self.base_layout_positions is None and \
                    not rack_pos in self.base_layout_positions:
            msg = 'Position %s is not part of the base layout. It must not ' \
                  'take up samples.' % (rack_pos)
            raise ValueError(msg)
        WorkingLayout.add_position(self, working_position)


class LibraryLayoutConverter(StockSampleCreationLayoutConverter):

    NAME = 'Library Layout Converter'
    LAYOUT_CLS = LibraryLayout


class LABELS(_POOL_CREATION_LABELS):
    MARKER_SECTOR_INDEX = 'sector_index'

    @classmethod
    def create_sector_stock_transfer_worklist_label(cls, iso_label, role,
                                                    sector_index):
        value_parts = [cls._FILL_WORKLIST_STOCK_TRANSFER, iso_label, role,
                       sector_index]
        return cls._create_label(value_parts)

    @classmethod
    def create_sector_stock_rack_label(cls, iso_label, role,
                                       sector_index, design_number=None):
        # The rack marker for sector stock racks consists of the rack role,
        # the sector index and optionally the design number.
        # Example: psrQ1#1
        if design_number is None:
            rack_marker = '%sQ%i' % (role, sector_index)
        else:
            rack_marker = '%sQ%i#%i' % (role, sector_index, design_number)
        value_parts = [iso_label, rack_marker]
        return cls._create_label(value_parts)

    @classmethod
    def parse_sector_stock_rack_label(cls, label):
        values = _POOL_CREATION_LABELS.parse_stock_rack_label(label)
        # The base class does not parse out the sector index from the rack
        # role string.
        rack_role, sector_idx_str = values[cls.MARKER_RACK_ROLE].split('Q')
        values[cls.MARKER_RACK_ROLE] = rack_role
        values[cls.MARKER_SECTOR_INDEX] = int(sector_idx_str)
        return values
