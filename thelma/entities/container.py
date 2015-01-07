"""
Container entity classes.
"""

from everest.entities.base import Entity
from everest.entities.utils import slug_from_string
from thelma.entities.sample import Sample


__docformat__ = 'reStructuredText en'
__all__ = ['CONTAINER_TYPES',
           'CONTAINER_SPECS_TYPES',
           'ContainerLocation',
           'Container',
           'Tube',
           'Well',
           'ContainerSpecs',
           'TubeSpecs',
           'WellSpecs',
           ]


class CONTAINER_TYPES(object):
    CONTAINER = 'CONTAINER'
    WELL = 'WELL'
    TUBE = 'TUBE'


class CONTAINER_SPECS_TYPES(object):
    CONTAINER = 'CONTAINER_SPECS'
    WELL = 'WELL_SPECS'
    TUBE = 'TUBE_SPECS'


class ContainerLocation(Entity):
    """
    A container's location in a rack.
    """
    #: A rack or plate (:class:`thelma.entities.rack.Rack`).
    rack = None
    #: The position on the rack or plate
    #: (:class:`thelma.entities.rack.RackPosition`).
    position = None
    #: back referenced by SQLAlchemy ORM.
    container = None

    def __init__(self, container, rack, position, **kw):
        Entity.__init__(self, **kw)
        self.position = position
        self.container = container
        self.rack = rack
        # FIXME: This is CeLMA legacy.
        self.row = position.row_index
        self.col = position.column_index

    def __eq__(self, other):
        """
        Equality is based on the rack and position attributes.
        """
        return (isinstance(other, ContainerLocation) and
                self.rack == other.rack and
                self.position == other.position)

    def __str__(self):
        return '%s:%s' % (self.rack, self.position)

    def __repr__(self):
        str_format = '<%s rack: %s, position: %s>'
        params = (self.__class__.__name__, self.rack, self.position)
        return str_format % params


class Container(Entity):
    """
    Abstract base class for all containers (incl. :class:`Tube` and
    :class:`Well`).
    """
    #: Defines the container specs (:class:`ContainerSpecs`).
    specs = None
    #: The item status (:class:`thelma.entities.status.ItemStatus`) of the
    #: container.
    status = None
     # FIXME: pylint:disable=W0511
     #        location should be readonly and only editable for tubes
    #: The associated container location; may be *None* for movable containers.
    #: Container locations are a combination of rack, container, and position
    #: (:class:`ContainerLocation`).
    location = None
    #: The sample (:class:`thelma.entities.sample.Sample`) associated with this
    #: container; may be *None*.
    sample = None

    def __init__(self, specs, status, location, sample=None, **kw):
        Entity.__init__(self, **kw)
        if self.__class__ is Container:
            raise NotImplementedError('Abstract class')
        self.specs = specs
        self.status = status
        if not location is None:
            # Do not set this to a None value to avoid inserting a container
            # location with a None value into the rack's container locations.
            self.location = location
        self.sample = sample

    @classmethod
    def create_from_rack_and_position(cls, specs, status, rack, position,
                                      **kw):
        """
        Creates a new container with a :class:`ContainerLocation` properly
        set up from the given rack and position parameters.

        This is solving the "chicken and egg problem" posed by the location
        constructor requiring not-NULL container and rack arguments and the
        container constructor requiring a location instance.
        """
        raise NotImplementedError('Abstract method.')

    @property
    def rack_position(self):
        """
        The position of a container in the rack
        (:class:`thelma.entities.rack.RackPosition`).
        """
        return self.location.position

    @property
    def rack(self):
        """
        The :class:`thelma.entities.rack.Rack` the container is located in.
        """
        return self.location.rack

    def make_sample(self, volume, **kw):
        """
        Creates a new sample for this container.

        :returns: :class:`thelma.entities.sample.Sample`
        """
        return Sample(volume, self, **kw)

    def __get_position(self):
        if self.location is None:
            pos = None
        else:
            pos = self.location.position
        return pos

    def __set_position(self, pos):
        if self.location is None:
            raise ValueError('Can not set position for a container '
                             'which is not in a rack.')
        new_location = ContainerLocation(self, self.location.rack, pos)
        self.location = new_location

    position = property(__get_position, __set_position)

    def __str__(self):
        return str(self.id)

    def __repr__(self):
        str_format = '<%s id: %s, specs: %s, location: %s, status: %s>'
        params = (self.__class__.__name__, self.id, self.specs,
                  self.location, self.status)
        return str_format % params


class Tube(Container):
    """
    Barcoded tube.
    """
    def __init__(self, specs, status, barcode, location=None, **kw):
        Container.__init__(self, specs, status, location, **kw)
        self._tube_barcode = barcode
        self.container_type = CONTAINER_TYPES.TUBE

    @classmethod
    def create_from_rack_and_position(cls, specs, status, barcode,
                                      rack, position, **kw):
        tube = cls(specs, status, barcode, None, **kw)
        rack.add_tube(tube, position)
        return tube

    @property
    def barcode(self):
        return self._tube_barcode.barcode

    def __repr__(self):
        str_format = '<%s id: %s, container_specs: %s, location: %s, ' \
                     'status: %s, barcode: %s>'
        params = (self.__class__.__name__, self.id, self.specs,
                  self.location, self.status, self.barcode)
        return str_format % params

    @property
    def slug(self):
        if self.barcode is None:
            slug = "no-barcode-%s" % self.id
        else:
            slug = self.barcode
        return slug


class Well(Container):
    """
    A plate well.
    """
    def __init__(self, specs, status, location, **kw):
        Container.__init__(self, specs, status, location, **kw)
        self.container_type = CONTAINER_TYPES.WELL

    @classmethod
    def create_from_rack_and_position(cls, specs, status, rack, position,
                                      **kw):
        container = cls(specs, status, None, **kw)
        container.location = ContainerLocation(container, rack, position)
        return container

    @property
    def slug(self):
        #: For instances of this class, the slug is derived from the
        #: position label of the location.
        return self.location.position.label

    def __str__(self):
        return str(self.location.position.label)


class ContainerSpecs(Entity):
    """
    This is an abstract class for container specifications.
    It defines the properties of a certain containers type.
    """
    #: The name of the container specification.
    name = None
    #: The (human-readable) label.
    label = None
    #: More verbose description of the container specification.
    description = None
    #: The maximum volume that can be stored in that kind of container.
    max_volume = None
    #: The dead volume that cannot be remove from that kind of container.
    dead_volume = None
    #: The manufacturer (:class:`thelma.entities.organization.Organization`).
    manufacturer = None
    #: Specifies whether containers of these type have barcodes.
    has_barcode = None

    def __init__(self, label, max_volume, dead_volume,
                 name=None, manufacturer=None, description='', **kw):
        Entity.__init__(self, **kw)
        if self.__class__ is ContainerSpecs:
            raise NotImplementedError('Abstract class')
        self.label = label
        self.max_volume = max_volume
        self.dead_volume = dead_volume
        if name is None:
            # FIXME: ensure uniqueness ?! # pylint:disable=W0511
            name = label.replace(' ', '').upper()[:32]
        self.name = name
        if not manufacturer is None:
            self.manufacturer = manufacturer
        self.description = description
        self.has_barcode = False

    @property
    def slug(self):
        #: The slug for instances of this class is derived from the
        #: :attr:`name`.
        return slug_from_string(self.name)

    def __str__(self):
        return self.name

    def __repr__(self):
        str_format = '<%s id: %s, name: %s, label: %s, max_volume: %s, ' \
                     'dead_volume: %s, manufacturer: %s, description: %s>'
        params = (self.__class__.__name__, self.id, self.name, self.label,
                  self.max_volume, self.dead_volume, self.manufacturer,
                  self.description)
        return str_format % params


class TubeSpecs(ContainerSpecs):
    """
    This class defines a properties of a certain kind of barcoded tubes.

    :note: Tubes need to have barcodes.
    """
    #: A list of tube racks sorts
    #: (:class:`thelma.entities.rack.TubeRackSpecs`)
    #: this tube can be stored in.
    tube_rack_specs = None

    def __init__(self, label, max_volume, dead_volume,
                 tube_rack_specs=None, **kw):
        ContainerSpecs.__init__(self, label, max_volume, dead_volume, **kw)
        if tube_rack_specs is None:
            tube_rack_specs = []
        if not tube_rack_specs is None:
            self.tube_rack_specs = tube_rack_specs
        # FIXME: has_barcode should be readonly. # pylint:disable=W0511
        self.has_barcode = True

    def create_tube(self, item_status, barcode, location=None):
        """
        Creates a tube with these tube specifications.

        :param item_status: the item status.
        :param barcode: The tube's barcode.
        :param location: The tube's location on the rack
            (:class:`ContainerLocation`)
        """
        return Tube(self, item_status, barcode, location)


class WellSpecs(ContainerSpecs):
    """
    This class defines the properties of a certain sort of a plate wells.

    :Note: Wells must not have barcodes.
    """
    #: Specifies which kind of plate this well belongs to.
    plate_specs = None

    def __init__(self, label, max_volume, dead_volume, plate_specs, **kw):
        ContainerSpecs.__init__(self, label, max_volume, dead_volume, **kw)
        if not plate_specs is None:
            self.plate_specs = plate_specs
