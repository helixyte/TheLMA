"""
Base classes and constants for library creation ticket.

AAB
"""
from everest.entities.utils import get_root_aggregate
from thelma.automation.tools.utils.base import ParameterSet
from thelma.automation.tools.utils.base import WorkingLayout
from thelma.automation.tools.utils.base import WorkingPosition
from thelma.automation.tools.utils.base import is_valid_number
from thelma.automation.tools.utils.base import round_up
from thelma.automation.tools.utils.converters import BaseLayoutConverter
from thelma.interfaces import IMoleculeDesignPool
from thelma.models.moleculedesign import MoleculeDesignPool
from thelma.models.moleculedesign import MoleculeDesignPoolSet
from thelma.models.moleculetype import MOLECULE_TYPE_IDS
from thelma.models.tagging import Tag

__docformat__ = 'reStructuredText en'

__all__ = ['NUMBER_SECTORS',
           'NUMBER_MOLECULE_DESIGNS',
           'MOLECULE_DESIGN_TRANSFER_VOLUME',
           'POOL_STOCK_RACK_CONCENTRATION',
           'PREPARATION_PLATE_CONCENTRATION',
           'ALIQUOT_PLATE_CONCENTRATION',
           'ALIQUOT_PLATE_VOLUME',
           'STARTING_NUMBER_ALIQUOTS',
           'get_stock_pool_buffer_volume',
           'get_source_plate_transfer_volume',
           'LibraryBaseLayoutParameters',
           'LibraryBaseLayoutPosition',
           'LibraryBaseLayout',
           'LibraryBaseLayoutConverter',
           'LibraryParameters',
           'LibraryPosition',
           'LibraryLayout',
           'LibraryLayoutConverter']


#: The number of rack sectors (96-to-384 plate transition).
NUMBER_SECTORS = 4
#: The molecule type ID for the library.
MOLECULE_TYPE = MOLECULE_TYPE_IDS.SIRNA

#: The number of molecule designs per pool.
NUMBER_MOLECULE_DESIGNS = 3
#: The transfer volume of each molecule design in the pool (from single
#: molecule design stock to pool) in ul.
MOLECULE_DESIGN_TRANSFER_VOLUME = 3

#: The volume of the pool stock racks in ul.
POOL_STOCK_RACK_VOLUME = 45
#: The concentration of the pool stock racks in nM.
POOL_STOCK_RACK_CONCENTRATION = 10000 # 10 uM
#: The concentration of the prepartion plate in nM.
PREPARATION_PLATE_CONCENTRATION = 1270 # 1270 nM
#: The sample volume (after dilution, before aliquot plate creation) in the
#: preparation plate in ul.
PREPARATION_PLATE_VOLUME = 43.3 # 43.3 ul
#: The concentration of the library plate in nM.
ALIQUOT_PLATE_CONCENTRATION = 1270 # 1270 nM
#: The final sample volume in the library aliquot plate in ul.
ALIQUOT_PLATE_VOLUME = 4

#: The number of aliquot plates generated for each layout.
STARTING_NUMBER_ALIQUOTS = 8

OPTIMEM_DILUTION_FACTOR = 3


def get_stock_pool_buffer_volume():
    """
    Returns the buffer volume required to generate the pool stock samples.
    """
    total_transfer_volume = NUMBER_MOLECULE_DESIGNS \
                            * MOLECULE_DESIGN_TRANSFER_VOLUME
    return POOL_STOCK_RACK_VOLUME - total_transfer_volume

def get_source_plate_transfer_volume():
    """
    Returns the volume that is transferred from a pool stock rack to a
    library source (preparation) plate in ul.
    """
    dilution_factor = float(POOL_STOCK_RACK_CONCENTRATION) \
                      / PREPARATION_PLATE_CONCENTRATION
    vol = PREPARATION_PLATE_VOLUME / dilution_factor
    return round_up(vol)


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
        :attr:`is_sample_pos`
    """
    PARAMETER_SET = LibraryBaseLayoutParameters

    def __init__(self, rack_position, is_sample_position=True):
        """
        Constructor:

        :param rack_position: The rack position.
        :type rack_position: :class:`thelma.models.rack.RackPosition`.

        :param is_sample_position: Is this position available for samples?
        :type is_sample_position: :class:`bool`
        """
        WorkingPosition.__init__(self, rack_position)

        if not isinstance(is_sample_position, bool):
            msg = 'The "sample position" flag must be a bool (obtained: %s).' \
                  % (is_sample_position.__class__.__name__)
            raise TypeError(msg)

        #: Is this position available for samples?
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
    WORKING_POSITION_CLASS = LibraryBaseLayoutPosition

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


class LibraryBaseLayoutConverter(BaseLayoutConverter):
    """
    Converts a :class:`thelma.models.racklayout.RackLayout` into a
    :class:`LibraryBaseLayout`.
    """

    NAME = 'Library Base Layout Converter'

    PARAMETER_SET = LibraryBaseLayoutParameters
    WORKING_LAYOUT_CLASS = LibraryBaseLayout

    def __init__(self, rack_layout, log):
        """
        Constructor:

        :param rack_layout: The rack layout containing the ISO data.
        :type rack_layout: :class:`thelma.models.racklayout.RackLayout`

        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`
        """

        BaseLayoutConverter.__init__(self, rack_layout, log=log)

        # intermediate storage of invalid rack positions
        self.__invalid_flag = None

    def reset(self):
        BaseLayoutConverter.reset(self)
        self.__invalid_flag = []

    def _obtain_working_position(self, parameter_map):
        """
        Derives a working position from a parameter map (including validity
        checks).
        """
        is_sample_pos_str = parameter_map[self.PARAMETER_SET.IS_SAMPLE_POS]
        rack_pos = parameter_map[self._RACK_POSITION_KEY]
        pos_label = rack_pos.label

        if is_sample_pos_str is None: return None

        values = {str(True) : True, str(False) : False}

        if not values.has_key(is_sample_pos_str):
            info = '%s (%s)' % (pos_label, is_sample_pos_str)
            self.__invalid_flag.append(info)
        else:
            return LibraryBaseLayoutPosition(rack_position=rack_pos,
                                is_sample_position=values[is_sample_pos_str])

    def _record_additional_position_errors(self):
        """
        Records specific errors that have been collection during position
        generation.
        """
        if len(self.__invalid_flag) > 0:
            msg = 'The "sample position" flag must be a boolean. The values ' \
                  'for some positions are invalid. Details: %s.' \
                  % (', '.join(sorted(self.__invalid_flag)))
            self.add_error(msg)

    def _initialize_working_layout(self, shape):
        return LibraryBaseLayout(shape=shape)

    def _perform_layout_validity_checks(self, working_layout):
        """
        We do not check anything but we close the layout.
        """
        working_layout.close()


class LibraryParameters(ParameterSet):
    """
    Stores the pool IDs and molecule design IDs for each position of the
    a particular library plate (layout).
    """

    DOMAIN = 'library'

    #: A pool ID (stock sample molecule design set ID).
    POOL = 'pool_id'
    #: A list of molecule design IDs for a particular pool.
    MOLECULE_DESIGNS = 'molecule_designs'

    #: The barcodes for the stock tubes (as determined by the
    #: ISO generation optimization query).
    STOCK_TUBE_BARCODES = 'stock_tube_barcodes'

    REQUIRED = [POOL, MOLECULE_DESIGNS, STOCK_TUBE_BARCODES]
    ALL = [POOL, MOLECULE_DESIGNS, STOCK_TUBE_BARCODES]

    ALIAS_MAP = {POOL : ['molecule design set', 'molecule design set ID',
                         'pool', 'molecule design pool',
                         'molecule design pool ID'],
                 MOLECULE_DESIGNS : ['molecule design IDs'],
                 STOCK_TUBE_BARCODES : []}

    DOMAIN_MAP = {POOL : DOMAIN,
                  MOLECULE_DESIGNS : DOMAIN,
                  STOCK_TUBE_BARCODES : DOMAIN}


class LibraryPosition(WorkingPosition):
    """
    The pool ID and molecule design IDs for a particular position in a
    library layout.

    **Equality condition**: equal :attr:`rack_position` and :attr:`pool`.
    """

    PARAMETER_SET = LibraryParameters
    DELIMITER = '-'

    def __init__(self, rack_position, pool, stock_tube_barcodes):
        """
        :param rack_position: The source rack position in the source rack.
        :type rack_position: :class:`thelma.models.rack.RackPosition`

        :param pool: A molecule design pool.
        :type pool:
            :class:`thelma.models.moleculedesign.MoleculeDesignPool`

        :param stock_tube_barcodes: The stock tube barcodes for the single
            molecule design tubes used to generate this pool.
        :type stock_tube_barcodes: :class:`list`
        """
        WorkingPosition.__init__(self, rack_position)

        if not isinstance(pool, MoleculeDesignPool):
            msg = 'The molecule design pool must be a %s (obtained: %s).' \
                  % (MoleculeDesignPool.__name__,
                     pool.__class__.__name__)
            raise TypeError(msg)
        if not isinstance(stock_tube_barcodes, list):
            msg = 'The stock tube barcodes must be a list (obtained: %s).' \
                  % (stock_tube_barcodes.__class__.__name__)
            raise TypeError(msg)

        #: The molecule design pool.
        self.pool = pool
        #: A list of molecules contained in the pool.
        self.molecule_designs = []
        for md in pool.molecule_designs: self.molecule_designs.append(md)

        #: The stock tube barcodes for the single molecule design tubes
        #: used to generate this pool
        self.stock_tube_barcodes = stock_tube_barcodes

    def get_parameter_tag(self, parameter):
        """
        The method needs to be overwritten because the value for the molecule
        designs tag is a concatenated string.
        """
        if parameter == self.PARAMETER_SET.MOLECULE_DESIGNS:
            return self.get_molecule_designs_tag()
        elif parameter == self.PARAMETER_SET.STOCK_TUBE_BARCODES:
            return self.get_stock_barcodes_tag()
        else:
            return WorkingPosition.get_parameter_tag(self, parameter)

    @classmethod
    def validate_molecule_designs(cls, md_pool, md_tag_value):
        """
        Compares the molecule design of the pool to a molecule design tag
        value. Is used by the layout converter for validation.
        """
        pool_str = cls.__get_molecule_designs_tag_value(
                                                    md_pool.molecule_designs)
        return pool_str == md_tag_value

    @classmethod
    def __get_molecule_designs_tag_value(cls, molecule_designs):
        """
        The tag values contains the molecule designs as concatenated string.
        """
        ids = []
        for md in molecule_designs: ids.append(md.id)
        return cls.DELIMITER.join(sorted([str(md_id) for md_id in ids]))

    def get_molecule_designs_tag_value(self):
        """
        This parameter requires a special method because the value for the
        molecule designs tag is a concatenated string.
        """
        return self.__get_molecule_designs_tag_value(self.molecule_designs)

    def get_molecule_designs_tag(self):
        """
        This parameter requires a special method because the value for the
        molecule designs tag is a concatenated string.
        """
        return Tag(self.PARAMETER_SET.DOMAIN,
                   self.PARAMETER_SET.MOLECULE_DESIGNS,
                   self.get_molecule_designs_tag_value())

    def get_stock_barcodes_tag_value(self):
        """
        This parameter requires a special method because the value for the
        stock barcodes tag is a concatenated string.
        """
        return self.DELIMITER.join(self.stock_tube_barcodes)

    def get_stock_barcodes_tag(self):
        """
        This parameter requires a special method because the value for the
        stock barcodes tag is a concatenated string.
        """
        return Tag(self.PARAMETER_SET.DOMAIN,
                   self.PARAMETER_SET.STOCK_TUBE_BARCODES,
                   self.get_stock_barcodes_tag_value())

    def _get_parameter_values_map(self):
        """
        Returns a map containing the value for each parameter.
        """
        return {self.PARAMETER_SET.POOL : self.pool,
                self.PARAMETER_SET.MOLECULE_DESIGNS : self.molecule_designs,
                self.PARAMETER_SET.STOCK_TUBE_BARCODES : \
                                                    self.stock_tube_barcodes}

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
                other.rack_position == self.rack_position and \
                other.pool.id == self.pool.id

    def __repr__(self):
        str_format = '<%s rack position: %s, pool ID: %s, molecule ' \
                     'designs: %s, stock tubes: %s>'
        params = (self.__class__.__name__, self.rack_position, self.pool.id,
                  self.get_molecule_designs_tag_value(),
                  self.get_stock_barcodes_tag_value())
        return str_format % params


class LibraryLayout(WorkingLayout):
    """
    Defines the molecule design pools for a library plate.
    """

    WORKING_POSITION_CLASS = LibraryPosition

    def __init__(self, shape):
        """
        Constructor:

        :param shape: The rack shape.
        :type shape: :class:`thelma.models.rack.RackShape`
        """
        WorkingLayout.__init__(self, shape)

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

    def get_pool_set(self, molecule_type):
        """
        Returns a pool set contain all pool from the layout.

        :param molecule_type: The type of the pools in the set is derived
            from the molecule type of the library.
        :type molecule_type: :class:`thelma.models.moleculetype.MoleculeType`
        """
        pools = set([lp.pool for lp in self._position_map.values()])
        return MoleculeDesignPoolSet(molecule_type=molecule_type,
                                     molecule_design_pools=pools)


class LibraryLayoutConverter(BaseLayoutConverter):
    """
    Converts a :class:`thelma.models.racklayout.RackLayout` into a
    :class:`LibraryLayout`.
    """

    NAME = 'Library Layout Converter'

    PARAMETER_SET = LibraryParameters
    WORKING_LAYOUT_CLASS = LibraryLayout

    def __init__(self, rack_layout, log):
        """
        Constructor:

        :param rack_layout: The rack layout containing the ISO data.
        :type rack_layout: :class:`thelma.models.racklayout.RackLayout`

        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`
        """
        BaseLayoutConverter.__init__(self, rack_layout, log=log)

        #: The molecule design pool aggregate
        #: (see :class:`thelma.models.aggregates.Aggregate`)
        #: used to obtain check the validity of molecule design pool IDs.
        self.__pool_aggregate = get_root_aggregate(IMoleculeDesignPool)
        #: Stores the molecule design pools for molecule design pool IDs.
        self.__pool_map = None

        # intermediate storage of invalid rack positions
        self.__missing_pool = None
        self.__unknown_pool = None
        self.__mismatching_mds = None
        self.__missing_tubes = None
        self.__mismatching_tubes = None

    def reset(self):
        BaseLayoutConverter.reset(self)
        self.__pool_map = dict()
        self.__missing_pool = []
        self.__unknown_pool = []
        self.__mismatching_mds = []
        self.__missing_tubes = []
        self.__mismatching_tubes = []

    def _obtain_working_position(self, parameter_map):
        """
        Derives an library position from a parameter map (including validity
        checks).
        """
        pool_id = parameter_map[self.PARAMETER_SET.POOL]
        md_str = parameter_map[self.PARAMETER_SET.MOLECULE_DESIGNS]
        tube_str = parameter_map[self.PARAMETER_SET.STOCK_TUBE_BARCODES]
        rack_pos = parameter_map[self._RACK_POSITION_KEY]
        pos_label = rack_pos.label

        if pool_id is None and md_str is None and tube_str is None: return None

        invalid = False
        if pool_id is None:
            self.__missing_pool.append(pos_label)
            invalid = True
        else:
            pool = self.__get_molecule_design_pool_for_id(pool_id, pos_label)
            if pool is None:
                invalid = True
            elif not LibraryPosition.validate_molecule_designs(pool, md_str):
                exp_mds = []
                for md in pool: exp_mds.append(md.id)
                info = '%s (pool %s, found: %s, expected: %s)' \
                        % (pos_label, pool_id, md_str,
                           '-'.join([str(md_id) for md_id in sorted(exp_mds)]))
                self.__mismatching_mds.append(info)
                invalid = True
            elif tube_str is None:
                self.__missing_tubes.append(pos_label)
                invalid = True
            else:
                tube_barcodes = tube_str.split(LibraryPosition.DELIMITER)
                if not len(tube_barcodes) == len(pool):
                    info = '%s (%s, number mds: %i)' % (pos_label, tube_str,
                                                        len(pool))
                    self.__mismatching_tubes.append(info)
                    invalid = True

        if invalid:
            return None
        else:
            return LibraryPosition(rack_position=rack_pos, pool=pool,
                                   stock_tube_barcodes=tube_barcodes)

    def __get_molecule_design_pool_for_id(self, pool_id, position_label):
        """
        Checks whether the molecule design pool for a fixed position is a
        valid one.
        """
        if self.__pool_map.has_key(pool_id):
            return self.__pool_map[pool_id]

        if not is_valid_number(pool_id, is_integer=True):
            info = '%s (%s)' % (pool_id, position_label)
            self.__unknown_pool.append(info)
            return None

        entity = self.__pool_aggregate.get_by_id(pool_id)
        if entity is None:
            info = '%s (%s)' % (pool_id, position_label)
            self.__unknown_pool.append(info)
            return None

        self.__pool_map[pool_id] = entity
        return entity

    def _record_additional_position_errors(self):
        """
        Launches collected position errors.
        """
        if len(self.__missing_pool) > 0:
            msg = 'Some positions do not have a pool ID: %s.' \
                  % (sorted(self.__missing_pool))
            self.add_error(msg)

        if len(self.__unknown_pool) > 0:
            msg = 'Some molecule design pool IDs could not be found in the ' \
                  'DB: %s.' % (sorted(self.__unknown_pool))
            self.add_error(msg)

        if len(self.__mismatching_mds) > 0:
            msg = 'The molecule designs IDs for some pools do not match: %s.' \
                  % (sorted(self.__mismatching_mds))
            self.add_error(msg)

        if len(self.__missing_tubes) > 0:
            msg = 'The following rack position do not contain stock tube ' \
                  'barcodes: %s.' % (', '.join(
                                     sorted(self.__missing_tubes)))
            self.add_error(msg)

        if len(self.__mismatching_tubes) > 0:
            msg = 'For some positions the number of tubes does not match ' \
                  'the number of molecule designs: %s.' \
                   % (' - '.join(self.__mismatching_tubes))
            self.add_error(msg)


    def _initialize_working_layout(self, shape):
        return LibraryLayout(shape=shape)

    def _perform_layout_validity_checks(self, working_layout):
        """
        There are no checks to be performed.
        """
        pass

