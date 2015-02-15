"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Rack entity classes.
"""
import re

from everest.entities.base import Entity
from everest.entities.utils import get_root_aggregate
from everest.entities.utils import slug_from_string
from everest.querying.specifications import eq
from everest.querying.specifications import lt
from thelma.entities.container import TubeLocation
from thelma.entities.container import Well
from thelma.entities.location import BarcodedLocationRack
from thelma.entities.utils import BinaryRunLengthEncoder
from thelma.entities.utils import number_from_label
from thelma.interfaces import IRackPosition
from thelma.interfaces import IRackPositionSet
from thelma.utils import get_utc_time


__docformat__ = 'reStructuredText en'
__all__ = ['Rack',
           'TubeRack',
           'Plate',
           'RackSpecs',
           'TubeRackSpecs',
           'PlateSpecs',
           'RackPosition',
           'RackPositionSet',
           'RACK_BARCODE_REGEXP',
           'RACK_POSITION_REGEXP',
           'RACK_TYPES',
           'rack_shape_from_rows_columns'
           ]


class RACK_TYPES(object):
    RACK = 'RACK'
    TUBE_RACK = 'TUBERACK'
    PLATE = 'PLATE'


class RACK_SPECS_TYPES(object):
    RACK_SPECS = 'RACKSPECS'
    TUBE_RACK_SPECS = 'TUBERACKSPECS'
    PLATE_SPECS = 'PLATESPECS'


RACK_POSITION_REGEXP = re.compile('^([A-Za-z]{1,2})([0-9]{1,2})$')
RACK_BARCODE_REGEXP = re.compile('0[1-9][0-9]{6}')


class Rack(Entity):
    """
    This is an abstract base class for all racks
    (:class:`TubeRack` and :class:`Plate`).
    """
    #: The (human-readable) label of this rack.
    label = None
    #: A comment made for this rack.
    comment = None
    #: The date this rack has been created in the database.
    creation_date = None
    #: The barcode (8-place-digit starting with \'0\') of the rack.
    barcode = None
    # FIXME: rack_specs should be made private/protected
    specs = None
    #: Barcoded location (:class:`thelma.entities.location.BarcodedLocation`)
    #: at which the rack is stored at the moment.
    location = None
    #: Barcoded location rack (association object between rack and location).
    location_rack = None
    #: The item status (:class:`thelma.entities.status.ItemStatus`) of the rack.
    status = None
    #: List of container (currently) present in the rack
    #: (:class:`thelma.entities.container.Container`).
    #: This is mapped automatically by SQLAlchemy ORM.
    containers = None
    #: Total number of containers in this rack.
    total_containers = None

    def __init__(self, label, specs, status, comment='',
                 creation_date=None, barcode=None, **kw):
        Entity.__init__(self, **kw)
        if self.__class__ is Rack:
            raise NotImplementedError('Abstract class')
        self.label = label
        self.specs = specs
        self.status = status
        self.comment = comment
        if creation_date is None:
            creation_date = get_utc_time()
        self.creation_date = creation_date
        self.barcode = barcode
        self.containers = []
        self._location = None

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`barcode`.
        if not self.barcode is None:
            slug = slug_from_string(self.barcode)
        else:
            slug = None
        return slug

    @property
    def rack_shape(self):
        """
        The :class:`RackShape` of the rack.
        """
        return self.specs.shape

    @classmethod
    def is_valid_barcode(cls, barcode):
        """
        Checks if the given value is a valid Cenix rack barcode.
        """
        return isinstance(barcode, basestring) \
               and RACK_BARCODE_REGEXP.match(barcode)

    @property
    def container_positions(self):
        """
        Maps container positions to containers.
        """
        raise NotImplementedError('Abstract property.')

    def check_in(self, location):
        """
        Checks this rack into the given barcoded location.

        We assume the barcoded location belongs to a freezer and check in all
        samples in this rack.
        """
        if not self.location_rack is None:
            raise RuntimeError('Trying to check in a rack that has not been '
                               'checked out (barcode: %s).' % self.barcode)
        self.location_rack = BarcodedLocationRack(location.rack, location)
        for cnt in self.containers:
#            cnt = cnt_loc.container
            # When we check in samples for the first time, they will not be
            # checked out; hence, we add an additional check here.
            if not cnt.sample is None and cnt.sample.is_checked_out:
                cnt.sample.check_in()

    def check_out(self):
        """
        Checks this rack out of its current barcoded location.

        We assume the barcoded location belongs to a freezer and check out all
        samples in this rack.
        """
        if self.location_rack is None:
            raise RuntimeError('Trying to check out a rack that has not been '
                               'checked in (barcode: %s).' % self.barcode)
        for cnt in self.containers:
            if not cnt.sample is None:
                cnt.sample.check_out()
        self.location_rack = None

    def _get_location(self):
        return self._location

    def _set_location(self, location):
        if not location is None:
            if not self.location_rack is None:
                raise ValueError()
            self.check_in(location)
        else:
            if self.location_rack is None:
                raise ValueError()
            self.check_out()

    location = property(_get_location, _set_location)

    def __str__(self):
        return self.barcode

    def __repr__(self):
        str_format = '<%s id: %s, barcode: %s, label: %s, comment: %s, ' \
                     'creation_date: %s, specs: %s, status: %s, location: %s>'
        params = (self.__class__.__name__, self.id, self.barcode, self.label,
                  self.comment, self.creation_date, self.specs, self.status,
                  self.location)
        return str_format % params


class TubeRack(Rack):
    """
    This class represents tube racks (racks harboring movable,
    barcoded tubes (:class:`thelma.entities.container.Tube`)).
    """
    #: List of tube locations (:class:`TubeLocation`).
    tube_locations = None

    def __init__(self, label, specs, status, **kw):
        Rack.__init__(self, label, specs, status, **kw)
        self.rack_type = RACK_TYPES.TUBE_RACK
        self.__containers = None
        self.__container_positions = None

    @property
    def container_positions(self):
        if self.__container_positions is None:
            cp_map = {}
            for cnt in self.containers:
                cp_map[cnt.position] = cnt
            self.__container_positions = cp_map
        return self.__container_positions

    def is_empty(self, position):
        """
        Checks if the given position is empty (i.e., does not have a tube).

        :param position: position to check
        :type position: `thelma.entities.RackPosition`
        """
        return not position in self.container_positions

    def move_tube(self, start_position, dest_position):
        """
        Moves the tube in the given start position to the given destination
        position (both on this rack).

        :param start_position: position to move from
        :type start_position: `thelma.entities.RackPosition`
        :param dest_position: position to move to
        :type dest_position: `thelma.entities.RackPosition`
        :raises ValueError: if the given start position is empty or the given
          destination position is not empty.
        """
        if  self.is_empty(start_position):
            raise ValueError('Can not move a tube starting from empty '
                             'position "%s".' % start_position.label)
        if not self.is_empty(dest_position):
            raise ValueError('Can not put a tube in occupied position "%s"'
                             % dest_position.label)
        tube = self.container_positions.pop(start_position)
        tube.location.position = dest_position
        self.container_positions[dest_position] = tube

    def add_tube(self, tube, position):
        """
        Adds the given tube to the given position on this rack.

        :param tube: tube to add
        :type tube: `thelma.entities.container.Tube`
        :param position: position to place the tube at
        :type position: `thelma.entities.RackPosition`
        :raises ValueError: If the given tube already has a location (only
          floating tubes can be added to a rack) or if the given position
          is already occupied.
        """
        if not tube.location is None:
            raise ValueError('Can only add floating tubes (i.e., tubes '
                             'without a location) to a rack.')
        if not self.is_empty(position):
            raise ValueError('Cannot put tube "%s" in occupied position "%s"'
                             % (tube.barcode, position.label))
        if position.row_index >= self.rack_shape.number_rows \
           or position.column_index >= self.rack_shape.number_columns:
            raise ValueError('Invalid position "%s" for rack with specs '
                             '"%s"' % (position.label, self.specs.label))
        new_location = TubeLocation(tube, self, position)
        self.tube_locations.append(new_location)
        self.container_positions[position] = tube

    def remove_tube(self, tube):
        """
        Removes the given tube from this rack.

        :param tube: tube to remove
        :type tube: `thelma.entities.container.Tube`
        :raises ValueError: If the given tube does not have a location or
          has a location that is not on this rack.
        """
        if tube.location is None:
            raise ValueError('Can not remove floating tube "%s" from rack.'
                             '%s".' % (tube.barcode, self.barcode))
        elif not tube.location.rack is self:
            raise ValueError('Tube "%s" can not be removed from rack "%s" as '
                             'it is currently associated with rack "%s".'
                             % (tube.barcode, self.barcode,
                                tube.location.rack.barcode))
        tube = self.container_positions.pop(tube.location.position)
        tube.location = None


class Plate(Rack):
    """
    This class represents plate racks (racks harboring immobile,
    unbarcoded wells (:class:`thelma.entities.container.Well`)).
    """
    def __init__(self, label, specs, status, **kw):
        Rack.__init__(self, label, specs, status, **kw)
        self.rack_type = RACK_TYPES.PLATE
        if self.specs != None:
            self.__container_positions = self.__init_wells()
        self.total_containers = self.rack_shape.size

    @property
    def container_positions(self):
        return self.__container_positions

    def __init_wells(self):
        c_specs = self.specs.well_specs
        containers = []
        cp_map = {}
        # We fetch all the rack positions in one query to speed up things.
        shape = self.specs.shape
        agg = get_root_aggregate(IRackPosition)
        agg.filter = lt(_row_index=shape.number_rows) \
                     & lt(_column_index=shape.number_columns)
        iterator = agg.iterator()
        while True:
            try:
                rack_pos = iterator.next()
            except StopIteration:
                break
            else:
                well = Well.create_from_rack_and_position(c_specs,
                                                          self.status,
                                                          self,
                                                          rack_pos)
                containers.append(well)
                cp_map[rack_pos] = well
        self.containers = containers
        return cp_map


class RackShape(Entity):
    """
    This class defines rack dimensions.
    RackShape instance can easily obtained by the
    :class:`RackShapeFactory`.
    """
    #: Name of the rack shape.
    name = None
    #: Equals the :attr:`name`.
    label = None
    #: The number of rows for this shape.
    number_rows = None
    #: The number of columns for this shape.
    number_columns = None
    #: A rack sort (:class:`RackSpecs`).
    specs = None

    def __init__(self, name, label, number_rows, number_columns, **kw):
        Entity.__init__(self, **kw)
        self.name = name
        self.label = label
        self.number_rows = number_rows
        self.number_columns = number_columns

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`name`.
        return slug_from_string(self.name)

    @property
    def size(self):
        """
        The number of positions.
        """
        return self.number_rows * self.number_columns

    def contains_position(self, rack_position):
        """
        Checks whether the passed rack position is within the range of the
        rack shape.

        :param rack_position: The rack position to check.
        :type rack_position: :class:`RackPosition`
        :rtype: :class:`bool`
        """
        return (rack_position.row_index < (self.number_rows) and
                rack_position.column_index < (self.number_columns))

    def __len__(self):
        """
        The number of positions for this rack shape.
        """
        return self.number_rows * self.number_columns

    def __eq__(self, other):
        """
        Equality is based on the name attribute.
        """
        return (isinstance(other, RackShape) and self.name == other.name)

    def __str__(self):
        return self.name

    def __repr__(self):
        str_format = '<%s name: %s, label: %s, number_rows: %s, ' \
                     'number_columns: %s>'
        params = (self.__class__.__name__, self.name, self.label,
                  self.number_rows, self.number_columns)
        return str_format % params


class RackShapeFactory(object):

    @classmethod
    def shape_from_rows_columns(cls, number_rows, number_columns):
        """
        Return a rack shape (:class:`RackShape`) from
        a row and column number. At this, it will first search its
        internal cache for a shape matching these both criteria.
        If there is no matching rack shape in the cache, the function
        will create one.

        There is an alias for this function called
        :func:`rack_shape_from_rows_columns`

        :param number_rows: The number of rows.
        :type number_rows: :class:`int`

        :param number_columns: THe number of columns.
        :type number columns: :class:`int`

        :return: the wanted rack shape
        :rtype: :class:`RackShape`
        """
        name = "%sx%s" % (number_rows, number_columns)
        return RackShape(name, name, number_rows, number_columns)

# Define standard rack shape access function.
#: An alias for
#: :func:`RackShapeFactory.shape_from_rows_columns`
rack_shape_from_rows_columns = RackShapeFactory.shape_from_rows_columns


class RackSpecs(Entity):
    """
    Abstract class for all rack specifications (rack types).
    """
    #: The name of the rack specification, similar to the :attr:`label`.
    name = None
    #: A more human-readable label, similar to :attr:`name`.
    label = None
    #: The dimensions of this rack (:class:`RackShape`).
    shape = None
    #: Defines whether this rack type has movable subitems (*True* for
    #: :class:`TubeRack` instances, *False* for
    #: :class:`Plate` instances).
    has_tubes = None
    #: The manufacturer of this type of racks
    #: (:class:`thelma.entities.organization.Organization`).
    manufacturer = None
    # FIXME: number_rows + number_columns are redundant # pylint:disable=W0511
    #: The number of rows of these rack specs.
    number_rows = None
    #: The number of rows of these rack specs.
    number_columns = None

    def __init__(self, label, shape,
                 name=None, manufacturer=None, has_tubes=None, **kw):
        if self.__class__ is RackSpecs:
            raise NotImplementedError('Abstract class')
        Entity.__init__(self, **kw)
        self.label = label
        self.shape = shape
        if name is None:
            # FIXME: ensure uniqueness ?! # pylint:disable=W0511
            name = label.replace(' ', '').upper()[:32]
        self.name = name
        self.manufacturer = manufacturer
        # FIXME: has_tubes should be readonly # pylint: disable=W0511
        self.has_tubes = has_tubes
        # FIXME: this is redundant - fix at DB level. # pylint: disable=W0511
        self.number_rows = shape.number_rows
        self.number_columns = shape.number_columns

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`name`.
        return slug_from_string(self.name)

    def __str__(self):
        return self.name

    def __repr__(self):
        str_format = '<%s id: %s, name: %s, label: %s, rack_shape: %s, ' \
                     'has_moveable_subitems: %s, manufacturer: %s>'
        params = (self.__class__.__name__, self.id, self.name, self.label,
                  self.shape, self.has_tubes, self.manufacturer)
        return str_format % params

    def create_rack(self, label, status, comment=''):
        raise NotImplementedError('abstract method')


class TubeRackSpecs(RackSpecs):
    """
    This class defines tube rack specifications (tube rack types).
    """
    #: List of compatible tube (container) specs for this tube rack specs.
    tube_specs = None

    def __init__(self, label, shape, tube_specs=None, **kw):
        kw['has_tubes'] = True
        RackSpecs.__init__(self, label, shape, **kw)
        if tube_specs is None:
            tube_specs = []
        self.tube_specs = tube_specs

    def create_rack(self, label, status, **kw):
        return TubeRack(label, self, status, **kw)


class PlateSpecs(RackSpecs):
    """
    This class defines plate specifications (plate types).
    """
    #: The well (container) specs for this plate specs.
    well_specs = None

    def __init__(self, label, shape, well_specs, **kw):
        kw['has_tubes'] = False
        RackSpecs.__init__(self, label, shape, **kw)
        self.well_specs = well_specs

    def create_rack(self, label, status, **kw):
        plate = Plate(label, self, status, **kw)
        return plate


class RackPosition(Entity):
    """
    This class defines position on a rack.

    It is a **value object** and row and column indices **must** remain
    immutable.
    See http://devlicio.us/blogs/casey/archive/2009/02/13/ddd-entities-and-value-objects.aspx

    RackPosition object can easily be obtained using the
    :class:`RackPositionFactory`.
    """

    #: The label of this rack position, i.e. a combination of letters
    #: (row) and numbers (column).
    _label = None
    #: The index of the row.
    _row_index = None
    #: The index of the column.
    _column_index = None

    def __init__(self, row_index, column_index, label, **kw):
        """
        This constructor should not be used. Load the rack positions from the
        DB instead by means of one of fetcher methods (:func:`from_label`,
        :func:`from_row_index_column_index` or :func:`from_row_column`).
        """
        Entity.__init__(self, **kw)
        self._label = label
        self._row_index = row_index
        self._column_index = column_index

    @property
    def slug(self):
        #: The slug of a rack position is its label.
        return self.label.lower()

    @property
    def label(self):
        """
        The label of this rack position, i.e. a combination of letters (row)
        and numbers (column).
        """
        return str(self._label)

    @property
    def row_index(self):
        """
        The index of the row.
        """
        return self._row_index

    @property
    def column_index(self):
        """
        The index of the column.
        """
        return self._column_index

    @classmethod
    def from_label(cls, label):
        """
        Returns a new RackPosition instance from the rack position label.

        :Note: Try not to use this method if you can avoid it as it takes
            as it takes a lot of time if you try to fetch a larger number
            of rack positions one by one. Use the rack position cache in the
            :mod:`semiconstants` module instead, if possible.

        :param label: a set of characters from a-z (or A-Z) which
                      signifies a row followed by an number
                      signifying the column
        :type label: :class:`string`

        :return: The wanted rack position.
        :rtype: :class:`RackPosition`
        """
        agg = get_root_aggregate(IRackPosition)
        return agg.get_by_slug(label.lower())

    @classmethod
    def from_indices(cls, row_index, column_index):
        """
        Returns a RackPosition from the row index and column index.

        :Note: Try not to use this method if you can avoid it as it takes
            as it takes a lot of time if you try to fetch a larger number
            of rack positions one by one. Use the rack position cache in the
            :mod:`semiconstants` module instead, if possible.

        :param row_index: the row of the container (this is 0 based).
        :type row_index: :class:`int`

        :param column_index: the column of the container (this 0 based).
        :type column_index: :class:`int`

        :return: The wanted rack position.
        :rtype: :class:`RackPosition`
        """
        agg = get_root_aggregate(IRackPosition)
        agg.filter = eq(_row_index=row_index) & eq(_column_index=column_index)
        return list(agg.iterator())[0]

    @classmethod
    def from_row_column(cls, row, column):
        """
        Returns a new RackPosition instance from the row name
        and column number.
        Invokes :func:`from_indices`.

        :Note: Try not to use this method if you can avoid it as it takes
            as it takes a lot of time if you try to fetch a larger number
            of rack positions one by one. Use the rack position cache in the
            :mod:`semiconstants` module instead, if possible.

        :param row: a set of characters from a-z (or A-Z) which signifies a row
        :type row: :class:`string`

        :param column: a number signifying the row
        :type column: :class:`int`

        :return: The wanted rack position.
        :rtype: :class:`RackPosition`
        """
        row_index = number_from_label(row) - 1
        column_index = column - 1
        return cls.from_indices(row_index, column_index)

    def __composite_values__(self):
        return (self._row_index, self._column_index)

    def __eq__(self, other):
        """
        Equality is based on the row_index and column_index attributes.
        """
        return isinstance(other, RackPosition) \
               and self._row_index == other.row_index \
               and self._column_index == other.column_index

    def __cmp__(self, other):
        if self._row_index < other.row_index:
            return -1
        elif self._row_index > other.row_index:
            return 1
        else:
            return cmp(self._column_index, other.column_index)

    def __hash__(self):
        return hash((self._row_index, self._column_index))

    def __str__(self):
        return self._label

    def __repr__(self):
        return '<RackPosition %s>' % self._label



class RackPositionSet(Entity):
    """
    Set of :class:`RackPosition` objects.

    A rack position set is uniquely identified by a hash value that is
    derived from the underlying (immutable) set of rack positions.

    Rack position sets are used by, for instance,
    :class:`thelma.entities.tagging.TaggedRackPositionSet`.
    """
    #: The rack positions (:class:`RackPosition`) as set - immutable.
    _positions = None
    #: The hash value is run length decoded string of the rack position
    #: pattern generated by the :func:`_encode_rack_position_set` function
    #: - immutable.
    _hash_value = None

    def __init__(self, positions, hash_value, **kw):
        """
        This construction should not be used. Use the factory method
        :func:`from_positions` to load a potential existing rack position
        set from DB instead of creating a new one.
        """
        Entity.__init__(self, **kw)
        self._positions = positions
        self._hash_value = hash_value

    @classmethod
    def from_positions(cls, positions):
        """
        Returns a RackPositionSet for the given positions. If there is
        already a set with the same hash value in the root aggregate, this
        set will be loaded and returned instead.
        """
        if not isinstance(positions, set):
            positions = set(positions)
        hash_value = cls.encode_rack_position_set(positions)
        agg = get_root_aggregate(IRackPositionSet)
        rps = agg.get_by_slug(hash_value)
        if rps is None:
            rps = cls(positions=positions, hash_value=hash_value)
            agg.add(rps)
        return rps

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: :attr:`hash_value`.
        return slug_from_string(self._hash_value)

    @property
    def positions(self):
        """
        The rack positions as set.
        """
        return self._positions

    @property
    def hash_value(self):
        """
        The hash value is run length decoded string of the rack position
        pattern generated by the :func:`encode_rack_position_set` function.
        """
        return self._hash_value

    @staticmethod
    def encode_rack_position_set(position_set):
        """
        Returns a run-length decoded string, storing the
        information of a 2D binary pattern.

        :param position_set: Set of well positions having a tag
        :type position_set: :class:`RackPosition`
        :return: run length decoded string
        """
        encoder = _PositionSetLengthEncoder(position_set)
        return encoder.encode_as_run_length_string()

    def __contains__(self, rack_position):
        """
        Checks whether the rack position set contains a certain
        rack position.

        :param rack_position: Rack position to check.
        :type rack_positions: :class:`RackPosition`
        :return: :class:`boolean`
        """
        return rack_position in self.positions

    def __eq__(self, other):
        """
        Equality is based on the hash_value attribute.
        """
        return isinstance(other, RackPositionSet) \
            and self._hash_value == other.hash_value

    def __iter__(self):
        return iter(self.positions)

    def __len__(self):
        return len(self.positions)

    def __str__(self):
        return self.hash_value

    def __repr__(self):
        str_format = '<%s hash value: %s>'
        params = (self.__class__.__name__, self._hash_value)
        return str_format % params


class _PositionSetLengthEncoder(BinaryRunLengthEncoder):
    """
    Special BinaryRunLengthEncoder dealing with sets of RackPosition objects.
    Wells present in the position set are considered "positive".
    """
    def _create_lookup(self):
        """
        For rack positions the coordinates must be derived from the entity.
        """
        for rack_pos in self._positive_positions:
            coord = (rack_pos.row_index, rack_pos.column_index)
            self._index_lookup.add(coord)

    def _get_row_index_from_input_set(self, position):
        return position.row_index

    def _get_column_index_from_input_set(self, position):
        return position.column_index
