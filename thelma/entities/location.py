"""
Location entity classes.

NP
"""

from everest.entities.base import Entity
from everest.entities.utils import slug_from_string

__docformat__ = 'reStructuredText en'

__all__ = ['BarcodedLocation',
           'BarcodedLocationType'
           ]


class BarcodedLocationType(Entity):
    """
    This class represents a location type, i.e. a kind of container for
    locations such as a drawer, a robot or a freezer.

    **Equality Condition**: equal :attr:`name`
    """

    #: The name of the location type (e.g. *freezer*, *drawer*).
    name = None

    def __init__(self, name, **kw):
        Entity.__init__(self, **kw)
        self.name = name

    @property
    def slug(self):
        #: The slug for instances of this class is derived from the
        #: :attr:`name`.
        return slug_from_string(self.name)

    def __eq__(self, other):
        return (isinstance(other, BarcodedLocationType) and
                self.name == other.name)

    def __str__(self):
        return self.name

    def __repr__(self):
        str_format = '<%s name: %s>'
        params = (self.__class__.__name__, self.name)
        return str_format % params


class BarcodedLocation(Entity):
    """
    This class represents a barcoded location. A location can store a rack.

    :Note: The location represents a unique, unambiguous location, e.g.
           not a complete drawer, but a certain position within the drawer.

    **Equality Condition**: equal :attr:`id`
    """

    #: The barcode of the location.
    barcode = None
    #: The name of the location (unique).
    name = None
    #: The label of the location (human readable marker).
    label = None
    #: The type of the location
    #: (:class:`BarcodedLocationType`).
    type = None
    #: The device (:class:`thelma.entities.device.Device`), if the location
    #: is associated with one (as it might be the case for e.g. robots).
    device = None
    #: The rack (:class:`thelma.entities.rack.Rack`) stored at the location.
    rack = None
    #: An identifier for a section within a robot, drawer etc.
    index = None
    #: Indicates whether there is a rack stored at this location.
    empty = True
    #: The date a rack was last checked into this location. This is `None` if
    #: the location is empty.
    checkin_date = None

    def __init__(self, name, label, type, barcode, # redef type pylint: disable=W0622
                 device=None, index=None, rack=None, checkin_date=None, **kw):
        Entity.__init__(self, **kw)
        #FIXME: #pylint: disable=W0511
        #       this awaits proper handling of character ids on DB level
        self.name = name
        self.label = label
        self.type = type
        self.device = device
        self.rack = rack
        self.index = index
        self.barcode = barcode
        self.checkin_date = checkin_date

    @property
    def slug(self):
        #: The slug for instances of this class is derived from the
        #: :attr:`name`.
        return slug_from_string(self.name)

    def __str__(self):
        return self.name

    def __repr__(self):
        str_format = '<%s id: %s, barcode: %s, name: %s, label: %s, ' \
                     'type: %s, device: %s, index: %s, rack: %s>'
        params = (self.__class__.__name__, self.id, self.barcode, self.name,
                  self.label, self.type, self.device, self.index, self.rack)
        return str_format % params

    def checkin_rack(self, rack):
        """
        Checks in the given rack at this barcoded location.
        """
        if not self.rack is None:
            raise RuntimeError('Can not check in a rack in an occupied '
                               'location.')
        self.rack = rack
        self.rack.check_in()

    def checkout_rack(self):
        """
        Checks out the rack held at this barcoded location.
        """
        if self.rack is None:
            raise RuntimeError('Location does not have a rack to check out.')
        self.rack.check_out()
        self.rack = None
