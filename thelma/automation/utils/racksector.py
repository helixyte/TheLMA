"""
Rack sectors classes.

AAB
"""

from math import sqrt
from thelma.automation.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.semiconstants import get_positions_for_shape
from thelma.automation.semiconstants import get_rack_position_from_indices
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.utils.base import add_list_map_element
from thelma.automation.utils.layouts import MoleculeDesignPoolLayout


__docformat__ = 'reStructuredText en'

__all__ = ['RackSectorTranslator',
           'get_sector_positions',
           'check_rack_shape_match',
           'QuadrantIterator',
           'ValueDeterminer']


class RackSectorTranslator(object):
    """
    This is a helper class that helps converting rack positions in rack
    transfers when there is more than one sector involved.
    For all cases, we assume Z-configuration

    Example::

        0  1
        2  3

    :Note: All attributes are immutable.
    """

    #: Marker to enforce many to many translation.
    MANY_TO_MANY = 'many_to_many'
    #: Marker to enforce one to many translation.
    ONE_TO_MANY = 'one_to_many'
    #: Marker to enforce many to one translation.
    MANY_TO_ONE = 'many_to_one'
    #: Marker to enforce one to one behaviour.
    ONE_TO_ONE = 'one_to_one'

    __TYPES = [MANY_TO_MANY, MANY_TO_ONE, ONE_TO_MANY, ONE_TO_ONE]

    def __init__(self, number_sectors, source_sector_index, target_sector_index,
                 row_count=None, col_count=None, behaviour=None):
        """
        Constructor:

        :param number_sectors: The total number of sectors.
        :type number_sectors: :class:`int`

        :param source_sector_index: Sector index of the source rack
            assuming Z-configuration.
        :type source_sector_index: :class:`int`

        :param target_sector_index: Sector index of the target rack
            assuming Z-configuration.
        :type target_sector_index: :class:`int`

        :param row_count: The number of sector rows - if you do not provide
            a number the row number is calculated assuming a square setup.
        :type row_count: :class:`int`

        :param col_count: The number of sector columns - if you do not provide
            a number the row number is calculated assuming a square setup.
        :type col_count: :class:`int`

        :param behaviour: Enforces a certain translation behaviour (applies
            only if there is more than one sector).
        :type behaviour: :class:`string` (class variable)
        :default behaviour: *None*
        """
        #: The translation behaviour (applies only if there is more than one
        #: sector).
        self.behaviour = behaviour

        #: The total number of sectors.
        self.__number_sectors = int(number_sectors)

        if row_count is None and col_count is None:
            sqrt_root = sqrt(self.__number_sectors)
            if not sqrt_root.is_integer():
                msg = 'Unable to determine number of row sectors and ' \
                      'column sectors for total sector count %i. Provide ' \
                      'the numbers manually, please.' \
                       % (self.__number_sectors)
                raise ValueError(msg)
            row_count = sqrt_root
            col_count = sqrt_root
        elif row_count is None:
            row_count = (float(self.__number_sectors) / col_count)
            if not row_count.is_integer():
                msg = 'Unable to determine row sector number for total ' \
                      'sector count %i and column count %i.' \
                      % (self.__number_sectors, col_count)
                raise ValueError(msg)
        elif col_count is None:
            col_count = (float(number_sectors) / row_count)
            if not col_count.is_integer():
                msg = 'Unable to determine row sector number for total ' \
                      'sector count %i and row count %i.' \
                      % (self.__number_sectors, row_count)
                raise ValueError(msg)

        #: The number of sector rows.
        self.__row_count = int(row_count)
        #: The number of sector columns.
        self.__col_count = int(col_count)

        #: Sector index of the source rack.
        self.__source_sector_index = source_sector_index
        #: Sector index of the target rack.
        self.__target_sector_index = target_sector_index

        #: The row modifier used for rack position translation.
        self.__row_modifier = None
        #: The column modifier used for rack position translation.
        self.__col_modifier = None

        #: The translation method of the sector translator (
        #: :func:`__convert_one_to_ many`, :func:`__convert_many_to_one`,
        #: :func:`__convert_one_to_one` or :func:`__convert_many_to_many`).
        self.__translation_method = None

        self.__init_modifiers()

    def __init_modifiers(self):
        """
        Initialises the row and the column modifier and sets the translation
        method.
        """
        if self.__number_sectors == 1 or self.behaviour == self.ONE_TO_ONE:
            self.__row_modifier = 0
            self.__col_modifier = 0
            self.__translation_method = self.__convert_one_to_one

        elif self.behaviour == self.MANY_TO_MANY:
            self.__init_many_to_many()
        elif self.behaviour == self.ONE_TO_MANY:
            self.__init_one_to_many()
        elif self.behaviour == self.MANY_TO_ONE:
            self.__init_many_to_one()
        elif (self.__source_sector_index == 0 \
              and self.__target_sector_index == 0):
            self.__init_many_to_many()
        elif (self.__source_sector_index == 0 \
                or self.__target_sector_index == 0):
            if self.__source_sector_index > self.__target_sector_index:
                self.__init_one_to_many()
            else:
                self.__init_many_to_one()
        else:
            self.__init_many_to_many()

    def __set_one_and_many_modifiers(self):
        """
        Sets the modifiers for one to many and many to one cases.
        """
        sector_index = max(self.__source_sector_index,
                           self.__target_sector_index)
        self.__row_modifier = self.__get_row_modifier(sector_index)
        self.__col_modifier = self.__get_col_modifier(sector_index)

    def __init_many_to_one(self):
        """
        Initialises the one to many translation type.
        """
        self.__set_one_and_many_modifiers()
        self.__translation_method = self.__convert_many_to_one

    def __init_one_to_many(self):
        """
        Initialises the one to many translation type.
        """
        self.__set_one_and_many_modifiers()
        self.__translation_method = self.__convert_one_to_many

    def __init_many_to_many(self):
        """
        Initialises the many to many translation type.
        """
        src_row_mod = self.__get_row_modifier(self.__source_sector_index)
        src_col_mod = self.__get_col_modifier(self.__source_sector_index)
        trg_row_mod = self.__get_row_modifier(self.__target_sector_index)
        trg_col_mod = self.__get_col_modifier(self.__target_sector_index)
        self.__row_modifier = (src_row_mod, trg_row_mod)
        self.__col_modifier = (src_col_mod, trg_col_mod)
        self.__translation_method = self.__convert_many_to_many

    def __get_row_modifier(self, sector_index):
        """
        Helper function returning the row modifier for a given sector index.
        """
        return int(sector_index / self.__col_count)

    def __get_col_modifier(self, sector_index):
        """
        Helper function returning the column modifier for a given sector index.
        """
        return (sector_index % self.__col_count)

    @property
    def number_sectors(self):
        """
        The total number of sectors.
        """
        return self.__number_sectors

    @property
    def source_sector_index(self):
        """
        Sector index of the source rack.
        """
        return self.__source_sector_index

    @property
    def target_sector_index(self):
        """
        Sector index of the target rack.
        """
        return self.__target_sector_index

    @property
    def row_count(self):
        """
        The number of sector rows.
        """
        return self.__row_count

    @property
    def col_count(self):
        """
        The number of sector columns.
        """
        return self.__col_count

    @property
    def row_modifier(self):
        """
        The row modifier used for rack position translation.
        """
        return self.__row_modifier

    @property
    def col_modifier(self):
        """
        The column modifier used for rack position translation.
        """
        return self.__col_modifier

    @classmethod
    def get_translation_behaviour(cls, source_shape, target_shape,
                                  number_sectors):
        """
        Return the translation behaviour for the given racks shapes.

        :param number_sectors: The number of sectors.
        :type number_sectors: :class:`int`

        :param source_shape: The rack shape of the source rack.
        :type source_shape: :class:`thelma.models.rack.RackShape`

        :param target_shape: The rack shape of the target rack.
        :type target_shape: :class:`thelma.models.rack.RackShape`
        """

        if number_sectors == 1: return cls.ONE_TO_ONE

        num_src_wells = source_shape.number_rows * source_shape.number_columns
        num_trg_wells = target_shape.number_rows * target_shape.number_columns

        if num_src_wells == num_trg_wells:
            return cls.MANY_TO_MANY
        elif num_src_wells > num_trg_wells:
            return cls.ONE_TO_MANY
        else:
            return cls.MANY_TO_ONE

    @classmethod
    def from_planned_rack_sample_transfer(cls, planned_rack_sample_transfer,
                      row_count=None, col_count=None, behaviour=None):
        """
        Initialises a RackSectorTranslator using the data of a planned rack
        sample transfer.

        :param planned_rack_sample_transfer: The planned rack transfer for which
            to initialise the translator.
        :type planned_rack_transfer:
            :class:`thelma.models.liquidtransfer.PlannedRackSampleTransfer`

        :param row_count: The number of sector rows - if you do not provide
            a number the row number is calculated assuming a square setup.
        :type row_count: :class:`int`

        :param col_count: The number of sector columns - if you do not provide
            a number the row number is calculated assuming a square setup.
        :type col_count: :class:`int`

        :param behaviour: Enforces a certain translation behaviour for
            0 to 0 sector cases (ignored in all other cases).
        :type behaviour: :class:`string` (class variable)
        :default behaviour: *None*

        :raises ValueError: If the algorithm fails to determine row count or
            column count (note that these two values can also be passed).
        :return: The translator (:class:`RackSectorTranslator`).
        """
        prst = planned_rack_sample_transfer
        return RackSectorTranslator(
                number_sectors=prst.number_sectors,
                source_sector_index=prst.source_sector_index,
                target_sector_index=prst.target_sector_index,
                behaviour=behaviour,
                row_count=row_count, col_count=col_count)

    def translate(self, rack_position):
        """
        Converts the given rack position of rack into to a rack position
        (the translation method has been determined during initialisation).

        :param rack_position: The rack position in the source rack.
        :type rack_position: :class:`thelma.models.rack.RackPosition`
        :raises ValueError: If the rack position cannot be translated.
        :return: associated rack position in the target rack
        """
        return self.__translation_method(rack_position)

    def __convert_one_to_one(self, rack_position):
        """
        Converts the given rack position of rack into to a rack position in a
        equally sized rack.

        :param rack_position: The rack position in the source rack.
        :type rack_position: :class:`thelma.models.rack.RackPosition`
        :return: associated rack position in the target rack
        """
        return rack_position

    def __convert_many_to_one(self, rack_position, row_modifier=None,
                              col_modifier=None):
        """
        Converts the given rack position of rack into to a rack position in a
        larger (or equally sized) rack.

        :Note: Row and column modifier can be provided by the
            :func:`convert_many_to_many` method.

        :param rack_position: The rack position in the source rack.
        :type rack_position: :class:`thelma.models.rack.RackPosition`
        :return: associated rack position in the target rack
        """
        if row_modifier is None: row_modifier = self.__row_modifier
        if col_modifier is None: col_modifier = self.__col_modifier

        row_index = (rack_position.row_index * self.__row_count) \
                    + row_modifier
        col_index = (rack_position.column_index * self.__col_count) \
                    + col_modifier
        return get_rack_position_from_indices(row_index, col_index)

    def __convert_one_to_many(self, rack_position, row_modifier=None,
                              col_modifier=None):
        """
        Converts the given rack position of rack into to a rack position in a
        smaller (or equally sized) rack.

        :Note: Row and column modifier can be provided by the
            :func:`convert_many_to_many` method.

        :param rack_position: The rack position in the source rack.
        :type rack_position: :class:`thelma.models.rack.RackPosition`
        :raises ValueError: If the rack position cannot be translated.
        :return: associated rack position in the target rack
        """
        if row_modifier is None: row_modifier = self.__row_modifier
        if col_modifier is None: col_modifier = self.__col_modifier

        row_index = (float(rack_position.row_index - row_modifier) \
                          / self.__row_count)

        col_index = (float(rack_position.column_index - col_modifier) \
                          / self.__col_count)

        if not row_index.is_integer() or not col_index.is_integer():
            msg = 'Invalid rack position for translation. Given rack ' \
                  'position: %s, resulting row index: %.1f, resulting column ' \
                  'index: %.1f, sector number: %i, row number: %i, column ' \
                  'number: %i, row modifier: %i, column modifier: %i, ' \
                  'translation type: %s.' \
                  % (rack_position, row_index, col_index, self.__number_sectors,
                     self.__row_count, self.__col_count, row_modifier,
                     col_modifier, self.behaviour)
            raise ValueError(msg)

        return get_rack_position_from_indices(int(row_index), int(col_index))

    def __convert_many_to_many(self, rack_position):
        """
        Converts the given rack position of rack into to a rack position in a
        larger (or equally sized) rack.

        :Note: Invokes :func:`convert_many_to_one` and
            :func:`convert_one_to_many`.

        :param rack_position: The rack position in the source rack.
        :type rack_position: :class:`thelma.models.rack.RackPosition`
        :raises ValueError: If the rack position is an invalid source
            position.
        :return: associated rack position in the target rack
        """
        src_pos = self.__convert_one_to_many(rack_position,
                            row_modifier=self.__row_modifier[0],
                            col_modifier=self.__col_modifier[0])
        trg_pos = self.__convert_many_to_one(src_pos,
                            row_modifier=self.__row_modifier[1],
                            col_modifier=self.__col_modifier[1])
        return trg_pos

    def __repr__(self):
        str_format = '<%s number sectors: %i, source sector index: %i, ' \
                     'target sector index: %i, row count: %i, column ' \
                     'count: %i>'
        params = (self.__class__.__name__, self.__number_sectors,
                  self.__source_sector_index, self.__target_sector_index,
                  self.__row_count, self.__col_count)
        return str_format % params


def check_rack_shape_match(source_shape, target_shape,
                           row_count, col_count,
                           translation_behaviour=None):
    """
    Checks whether two rack shape match the given rack transfer or translation
    behaviour.

    :Note: One-to-one translations can not be discovered automatically.

    :param source_shape: The rack shape of the source rack.
    :type source_shape: :class:`thelma.models.rack.RackShape`

    :param target_shape: The rack shape of the target rack.
    :type target_shape: :class:`thelma.models.rack.RackShape`

    :param row_count: The number of sector rows.
    :type row_count: :class:`int`

    :param col_count: The number of sector columns.
    :type col_count: :class:`int`

    :param translation_behaviour: The translation behaviour if known
        (one to many, many to one, many to many or one-to-one).
    :type translation_behaviour: :class:`RackSectorTranslator` class
        variable

    :raise ValueError: If the translation behaviour is None.
    """
    if translation_behaviour is None:
        msg = 'The translation behaviour must not be None!'
        raise ValueError(msg)

    if translation_behaviour == RackSectorTranslator.MANY_TO_MANY \
            or translation_behaviour == RackSectorTranslator.ONE_TO_ONE:
        return source_shape == target_shape

    else:
        src_row_number = source_shape.number_rows
        src_col_number = source_shape.number_columns
        trg_row_number = target_shape.number_rows
        trg_col_number = target_shape.number_columns

        if translation_behaviour == RackSectorTranslator.MANY_TO_ONE:
            trg_row_number = trg_row_number / row_count
            trg_col_number = trg_col_number / col_count
        else:
            src_row_number = src_row_number / row_count
            src_col_number = src_col_number / col_count

        return (src_row_number == trg_row_number and \
                src_col_number == trg_col_number)


def get_sector_positions(sector_index, rack_shape, number_sectors,
                         row_count=None, col_count=None):
    """
    A helper function return the positions of the given sector.

    :param sector_index: Sector index assuming Z-configuration.
    :type sector_index: :class:`int`

    :param number_sectors: The total number of sectors.
    :type number_sectors: :class:`int`

    :param rack_shape: The rack shape to be considered.
    :type rack_shape: :class:`thelma.models.rack.RackShape

    :param row_count: The number of sector rows - if you do not provide
        a number the row number is calculated assuming a square setup.
    :type row_count: :class:`int`

    :param col_count: The number of sector columns - if you do not provide
        a number the row number is calculated assuming a square setup.
    :type col_count: :class:`int`
    """

    translator = RackSectorTranslator(number_sectors=number_sectors,
                source_sector_index=sector_index,
                target_sector_index=0,
                row_count=row_count, col_count=col_count,
                behaviour=RackSectorTranslator.MANY_TO_MANY)

    positions = []

    for rack_pos in get_positions_for_shape(rack_shape):
        # Filter for positions
        try:
            translator.translate(rack_pos)
        except ValueError:
            continue
        else:
            positions.append(rack_pos)

    return positions


class QuadrantIterator(object):
    """
    A rack quadrant is an part of the rack containing one position for each
    rack sector. All positions of a quadrant are derived from the same source
    rack.

    The number of positions in a quadrant is equal to the number of sectors.
    (min. 1). If not stated differently, the shape of the rack quadrant is
    assumed to be a square.
    """

    def __init__(self, number_sectors, row_count=None, col_count=None):
        """
        Constructor:

        :param number_sectors: The total number of sectors.
        :type number_sectors: :class:`int`

        :param row_count: The number of sector rows - if you do not provide
            a number the row number is calculated assuming a square setup.
        :type row_count: :class:`int`

        :param col_count: The number of sector columns - if you do not provide
            a number the row number is calculated assuming a square setup.
        :type col_count: :class:`int`
        """

        #: The translators for each rack sector.
        self.__translators = dict()

        for i in range(number_sectors):
            translator = RackSectorTranslator(number_sectors=number_sectors,
                        source_sector_index=0, target_sector_index=i,
                        row_count=row_count, col_count=col_count,
                        behaviour=RackSectorTranslator.MANY_TO_MANY)
            self.__translators[i] = translator

    def get_quadrant_positions(self, sector_zero_position):
        """
        Returns the positions of the requested quadrant as map.

        :param sector_zero_position: The rack position of sector zero.
        :type sector_zero_position: :class:`thelma.models.rack.RackPosition`
        :return: A map with the rack positions mapped onto sector indices.
        """
        quadrant_positions = dict()

        for sector_index, translator in self.__translators.iteritems():
            target_pos = translator.translate(sector_zero_position)
            quadrant_positions[sector_index] = target_pos

        return quadrant_positions

    def get_quadrant_working_positions(self, sector_zero_position,
                                       working_layout):
        """
        Returns the working positions of the requested quadrant as map.

        :Note: Invokes :func:`get_quadrant_positions`

        :param sector_zero_position: The rack position of sector zero.
        :type sector_zero_position: :class:`thelma.models.rack.RackPosition`

        :param working_layout: The working layout whose positions to fetch.
        :type working_layout: :class:`WorkingLayout`

        :return: A map with the working positions mapped onto sector indices.
        """
        quadrant_positions = self.get_quadrant_positions(sector_zero_position)

        quadrant_wps = dict()
        for sector_index, rack_pos in quadrant_positions.iteritems():
            quadrant_wp = working_layout.get_working_position(rack_pos)
            quadrant_wps[sector_index] = quadrant_wp

        return quadrant_wps

    def get_all_quadrants(self, working_layout=None, rack_shape=None):
        """
        Returns a list with all (working) position quadrant of a working layout.
        If the working layout is None, the function will return rack positions
        instead. In the latter case, you have to provide a rack shape.

        :Note: Invokes :func:`get_quadrant_working_positions` or
            :func:`get_quadrant_positions`

        :param working_layout: The working layout whose positions to fetch.
        :type working_layout: :class:`WorkingLayout`

        :param rack_shape: The rack shape to iterate over - gets overwritten
            by the working_layout shape if there is any, thus, it needs
            only to be specified if there is no working layout.
        :type rack_shape: :class:`thelma.models.rack.RackShape`

        :return: A list of quadrant maps
            (see :func:`get_quadrant_working_positions`).
        """
        quadrants = []

        if not working_layout is None: rack_shape = working_layout.shape

        translator_0 = self.__translators[0]
        positions_0 = get_sector_positions(sector_index=0,
                        rack_shape=rack_shape,
                        number_sectors=len(self.__translators),
                        row_count=translator_0.row_count,
                        col_count=translator_0.col_count)

        for pos_0 in positions_0:
            if working_layout is None:
                quadrant_rps = self.get_quadrant_positions(pos_0)
            else:
                quadrant_rps = self.get_quadrant_working_positions(pos_0,
                                                                working_layout)
            quadrants.append(quadrant_rps)

        return quadrants

    @classmethod
    def sort_into_sectors(cls, working_layout, number_sectors):
        """
        Sorts the working positions of the given working layout into
        sectors. Rack positions without a working position are ignored.

        :return: the working positions (without *None*) positions sorted
            into rack sectors.
        """
        quadrant_positions = dict()

        for sector_index in range(number_sectors):
            positions = get_sector_positions(sector_index,
                                    working_layout.shape, number_sectors)
            quadrant_positions[sector_index] = []
            for rack_pos in positions:
                working_pos = working_layout.get_working_position(rack_pos)
                if not working_pos is None:
                    quadrant_positions[sector_index].append(working_pos)

        return quadrant_positions

    def __repr__(self):
        str_format = '<%s number of sectors: %i>'
        params = (self.__class__.__name__, len(self.__translators))
        return str_format % params


class ValueDeterminer(BaseAutomationTool):
    """
    This is a helper class determining the rack sector indices of layout
    positions depending on a particular attribute.

    For all cases, we assume Z-configuration

    Example::

        0  1
        2  3

    **Return Value:** A map containing the values for the different sectors.
    """
    #: The expected :class:`MoleculeDesignPoolLayout` subclass.
    LAYOUT_CLS = MoleculeDesignPoolLayout


    def __init__(self, working_layout, attribute_name, log, number_sectors=4):
        """
        Constructor:

        :param working_layout: The working layout whose positions to check.
        :type working_layout: :class:`WorkingLayout`

        :param attribute_name: The name of the attribute to be determined.
        :type attribute_name: :class:`str`

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param number_sectors: The number of rack sectors.
        :type number_sectors: :class:`int`
        :default number_sectors: *4*
        """
        BaseAutomationTool.__init__(self, log=log)
        #: The working layout whose positions to checks.
        self.working_layout = working_layout
        #: The name of the attribute to be determined.
        self.attribute_name = attribute_name
        #: The number of rack sectors.
        self.number_sectors = number_sectors

        #: The attribute value for each sector.
        self.__sectors = None

    def reset(self):
        """
        Resets the initialisation values.
        """
        BaseAutomationTool.reset(self)
        self.__sectors = dict()

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start rack sector determination ...')

        self._check_input()
        if not self.has_errors(): self.__determine_sector_values()
        if not self.has_errors():
            self.return_value = self.__sectors
            self.add_info('Sector determination completed.')

    def _check_input(self):
        """
        Checks the input values.
        """
        self.add_debug('Check input values ...')

        self._check_input_class('layout', self.working_layout, self.LAYOUT_CLS)
        self._check_input_class('attribute name', self.attribute_name, str)
        self._check_input_class('number of sectors', self.number_sectors, int)

    def __determine_sector_values(self):
        """
        Determines the value for each sector.
        """
        self.add_debug('Determine sector values ...')

        for sector_index in range(self.number_sectors):
            positions = get_sector_positions(sector_index=sector_index,
                                          rack_shape=self.working_layout.shape,
                                          number_sectors=self.number_sectors)

            values = set()

            for rack_pos in positions:
                working_pos = self.working_layout.get_working_position(rack_pos)
                if working_pos is None: continue
                if self._ignore_position(working_pos): continue
                try:
                    attr_value = getattr(working_pos, self.attribute_name)
                except AttributeError:
                    msg = 'Unknown attribute "%s".' % (self.attribute_name)
                    self.add_error(msg)
                    return

                if attr_value is None: continue
                values.add(attr_value)

            if len(values) > 1:
                msg = 'There is more than one value for sector %i! ' \
                      'Attribute: %s. Values: %s.' \
                       % (sector_index + 1, self.attribute_name,
                          self._get_joined_str(values, is_strs=False))
                self.add_error(msg)
            else:
                if len(values) < 1:
                    value = None
                else:
                    value = list(values)[0]
                self.__sectors[sector_index] = value

    def _ignore_position(self, layout_pos): #pylint: disable=W0613
        """
        Use this method to add conditions under which a position is ignored.
        By default, all positions are accepted.
        """
        return False


class RackSectorAssociator(BaseAutomationTool):
    """
    A abstract tool associating the sectors of a working layout (based on
    molecule design sets; assuming a screening scenario).

    **Return Value:** A list of lists (each list containing the indices of
        rack sector associated with one another).

    TODO: find a way to deal with floatings without distinct placeholder
    """
    #: The attribute by which to sort the ISO positions into sectors.
    SECTOR_ATTR_NAME = None
    #: The working layout class supported by this associator (subclass of
    #: :class:`MoleculeDesignPoolLayout`.
    LAYOUT_CLS = MoleculeDesignPoolLayout

    def __init__(self, layout, log, number_sectors=4):
        """
        Constructor:

        :param layout: The layout whose positions to check.
        :type layout: :class:`MoleculeDesignPoolLayout`

        :param number_sectors: The number of rack sectors.
        :type number_sectors: :class:`int`
        :default number_sectors: *4*

        :param log: The ThelmaLog you want to write in.
        :type log: :class:`thelma.ThelmaLog`
        """
        BaseAutomationTool.__init__(self, log=log)

        #: The layout whose positions to check.
        self.layout = layout
        #: The number of rack sectors.
        self.number_sectors = number_sectors

        #: The concentration for each rack sector.
        self._sector_concentrations = None

        #: Stores the set for each sector set hash.
        self.__sector_set_hashes = None
        #: Stores the pos label sets for each sector set hash.
        self.__sector_set_positions = None

        #: The rack sectors sharing the same molecule design sets within a
        #: quadrant.
        self._associated_sectors = None

    def reset(self):
        """
        Resets all values except the initialisation values.
        """
        BaseAutomationTool.reset(self)
        self._sector_concentrations = None
        self._associated_sectors = []
        self.__sector_set_hashes = dict()
        self.__sector_set_positions = dict()

    def get_sector_concentrations(self):
        """
        Returns the sector concentration map.
        """
        return self._get_additional_value(self._sector_concentrations)

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start sector association ...')

        self._check_input()
        if not self.has_errors(): self.__get_concentrations_for_sectors()
        if not self.has_errors(): self.__determine_association()
        if not self.has_errors():
            self.return_value = self._associated_sectors
            self.add_info('Association completed.')

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        self._check_input_class('layout', self.layout, self.LAYOUT_CLS)
        self._check_input_class('number of sectors', self.number_sectors, int)

    def __get_concentrations_for_sectors(self):
        """
        Determines the concentration for each rack sector.
        """
        self.add_debug('Determine concentrations for sectors ...')

        value_determiner = self._init_value_determiner()
        if self._disable_err_warn_rec:
            value_determiner.disable_error_and_warning_recording()
        self._sector_concentrations = value_determiner.get_result()

        if self._sector_concentrations is None:
            msg = 'Error when trying to determine rack sector concentrations.'
            self.add_error(msg)

    def _init_value_determiner(self):
        """
        Initialises the value determiner for the concentrations.
        """
        raise NotImplementedError('Abstract method.')

    def __determine_association(self):
        """
        Determines and checks the association for each quadrant.
        """
        quadrant_iterator = QuadrantIterator(number_sectors=self.number_sectors)
        for quadrant_wps in quadrant_iterator.get_all_quadrants(self.layout):
            self.__find_sector_sets(quadrant_wps)
        self._check_associated_sectors()

    def __find_sector_sets(self, quadrant_wps):
        """
        Sectors sharing the same pool ID or pool ID placeholder are regarded
        as one set.
        Pool IDs with a value of *None* are not regarded.
        """
        pools = dict()
        pos_labels = dict()

        for sector_index, pool_pos in quadrant_wps.iteritems():
            pool = self._get_molecule_design_pool_id(pool_pos)
            if not pool is None:
                add_list_map_element(pools, pool, sector_index)
                add_list_map_element(pos_labels, pool,
                                     pool_pos.rack_position.label)

        for pool, sectors in pools.iteritems():
            sector_hash = self._get_joined_str(sectors, is_strs=False,
                                               separator='.')
            if not self.__sector_set_hashes.has_key(sector_hash):
                self.__sector_set_hashes[sector_hash] = sectors
            add_list_map_element(self.__sector_set_positions, sector_hash,
                                 pos_labels[pool])

    def _get_molecule_design_pool_id(self, layout_pos):
        """
        Returns the molecule design pool ID (or placeholder) of a layout
        position. By default, untreated and mock positions are converted into
        None replacers.
        """
        if layout_pos is None:
            pool_id = None
        elif layout_pos.is_mock or layout_pos.is_empty:
            pool_id = None
        else:
            pool_id = layout_pos.molecule_design_pool_id
        return pool_id

    def _check_associated_sectors(self):
        """
        Sectors sets are sorted by size first. Larger sets must incorporate all
        known smaller sets sharing these sector indices.
        All final sets must have the same length to insure all potential
        floating positions are treated in the same manner.
        """
        length_map = dict()
        for sectors in self.__sector_set_hashes.values():
            add_list_map_element(length_map, len(sectors), sectors)

        current_sets = []
        used_sectors = dict()
        invalid = False

        for length in sorted(length_map.keys()):
            if invalid: break
            sector_sets = length_map[length]
            for sector_set in sector_sets:
                all_new = True
                all_present = True
                for si in sector_set:
                    if not used_sectors.has_key(si):
                        all_present = False
                        used_sectors[si] = sector_set
                    else:
                        all_new = False
                if all_new:
                    current_sets.append(sector_set)
                    continue
                elif not all_present:
                    invalid = True
                    break
                for si in sector_set:
                    smaller_set = used_sectors[si]
                    for smaller_set_index in smaller_set:
                        if not smaller_set_index in sector_set:
                            invalid = True
                            break

        if invalid:
            msg = 'The molecule design pools in the different quadrants are ' \
                  'not consistent. Found associated pools: %s.' \
                   % (self._get_joined_map_str(self.__sector_set_positions,
                      all_strs=False))
            self.add_error(msg)
        elif self._are_valid_sets(current_sets):
            self._associated_sectors = current_sets

    def _are_valid_sets(self, current_sets):
        """
        Makes sure the current sector sets have equal size and concentration
        combinations. Otherwise we could not make sure that all samples
        are treated in the same way.
        """
        set_lengths = set()
        set_concentrations = set()
        for sector_set in current_sets:
            set_length = len(sector_set)
            set_lengths.add(set_length)
            concentrations = []
            for sector_index in sector_set:
                concentrations.append(self._sector_concentrations[sector_index])
            conc_tup = tuple(sorted(concentrations))
            set_concentrations.add(conc_tup)

        if len(set_lengths) > 1:
            msg = 'The sets of molecule design pools in a quadrant have ' \
                  'different lengths: %s.' \
                  % (self._get_joined_map_str(self.__sector_set_positions,
                     all_strs=False))
            self.add_error(msg)
            return False
        elif len(set_concentrations) > 1:
            msg = 'All sector set must have the same combination of ' \
                  'concentrations to ensure all samples are treated equally. ' \
                  'This rule is not met. Talk to IT, please. Associated ' \
                  'sectors: %s, concentrations: %s.' \
                   % (current_sets, self._get_joined_map_str(
                                self._sector_concentrations, all_strs=False))
            self.add_error(msg)
            return False

        return True


class AssociationData(object):
    """
    A abstract helper class determining and storing associated rack sectors,
    parent sectors and sector concentration for an working layout (screening
    case assumed).

    :Note: All attributes are immutable.
    """

    __SECTOR_NUMBER_384 = 4

    def __init__(self, layout, log, record_errors=True):
        """
        Constructor:

        :param layout: The working layout whose sectors to associate.
        :type layout: :class:`MoleculeDesignPoolLayout` subclass

        :param log: The log to write into (not stored in the object).
        :type log: :class:`thelma.ThelmaLog`

        :param record_errors: If set to *False* the error and warning recording
            of the used tools will be disabled.
        :type record_errors: :class:`bool`
        :default record_errors: *True*
        """
        #: The rack sectors sharing the same molecule design set ID within a
        #: quadrant.
        self._associated_sectors = None
        #: The concentration for each rack sector.
        self._sector_concentrations = dict()
        #: The parent sector for each sector.
        self._parent_sectors = dict()

        number_sectors = 1
        if layout.shape.name == RACK_SHAPE_NAMES.SHAPE_384:
            number_sectors = self.__SECTOR_NUMBER_384
        #: The number of sectors depends on the rack shape.
        self._number_sectors = number_sectors

        self.__associate(layout, log, record_errors)

    @property
    def associated_sectors(self):
        """
        The rack sectors sharing the same molecule design set ID within a
        quadrant (does not contain sectors without regarded pools).
        """
        return self._associated_sectors

    @property
    def sector_concentrations(self):
        """
        The concentration for each rack sector (does not contain sectors
        without regarded pools).
        """
        return self._sector_concentrations

    @property
    def parent_sectors(self):
        """
        The parent sector for each sector (does not contain sectors
        without regarded pools).
        """
        return self._parent_sectors

    @property
    def number_sectors(self):
        """
        The number of sectors depends on the rack shape.
        """
        return self._number_sectors

    def __associate(self, layout, log, record_errors):
        """
        Checks whether there are different rack sectors and set ups the
        the attributes.
        """
        if self._number_sectors == 1:
            concentrations = self._find_concentrations(layout)
            if len(concentrations) == 1:
                conc = list(concentrations)[0]
                self._sector_concentrations = {0 : conc}
                self._associated_sectors = [[0]]
                self._parent_sectors = {0 : None}
            else:
                msg = 'Association failure: There is more than 1 ' \
                      'concentration although there is is only one rack ' \
                      'sector!'
                if record_errors: log.add_error(msg)
                raise ValueError(msg)

        else: # number sectors = 4
            self.__find_relationships(layout, log, record_errors)

    def _find_concentrations(self, layout):
        """
        Finds all different concentrations in the layout.
        """
        raise NotImplementedError('Abstract method.')

    def _init_value_determiner(self, layout, log):
        """
        Initialises a value determiner. It is used to find the sectors that
        are present in 384-position layout with independent sectors.
        """
        raise NotImplementedError('Abstract method.')

    def __find_relationships(self, layout, log, record_errors):
        """
        Sets up the association data (if there is more than one
        concentration).

        :raises ValueError: If the association fails.
        """
        associator = self._init_associator(layout, log)
        if not record_errors: associator.disable_error_and_warning_recording()
        self._associated_sectors = associator.get_result()

        if self._associated_sectors is None:
            if record_errors:
                msg = '-- '.join(associator.get_messages())
            else:
                msg = 'Error when trying to find rack sector association.'
            raise ValueError(msg)

        self._sector_concentrations = associator.get_sector_concentrations()
        del_sectors = []
        for sector_index, conc in self._sector_concentrations.iteritems():
            if conc is None: del_sectors.append(sector_index)
        for sector_index in del_sectors:
            del self._sector_concentrations[sector_index]

        for sectors in self._associated_sectors:
            # concentrations for associated sectors
            concentrations_map = dict()
            for sector_index in sectors:
                conc = self._sector_concentrations[sector_index]
                add_list_map_element(concentrations_map, conc, sector_index)
            concentrations = sorted(concentrations_map.keys())

            last_sector = None
            for conc in concentrations:
                sectors = concentrations_map[conc]
                for sector_index in sorted(sectors, reverse=True):
                    if not last_sector is None:
                        self._parent_sectors[last_sector] = sector_index
                    last_sector = sector_index
                    self._parent_sectors[sector_index] = None

    def _init_associator(self, layout, log):
        """
        Initialises the associator.
        """
        raise NotImplementedError('Abstract method.')

    def _remove_none_sectors(self, sector_map):
        """
        Helper functions removing sectors with None values from value maps.
        """
        del_indices = []
        for sector_index in sector_map.keys():
            if not self._sector_concentrations.has_key(sector_index):
                del_indices.append(sector_index)
        for sector_index in del_indices:
            del sector_map[sector_index]

    def __str__(self):
        return self.__class__.__name__
