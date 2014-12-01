"""
Location entity classes.
"""
import datetime

from everest.entities.base import Entity
from everest.entities.utils import slug_from_string


__docformat__ = 'reStructuredText en'
__all__ = ['BarcodedLocation',
           'BarcodedLocationType',
           'BarcodedLocationRack',
           ]


class BarcodedLocationType(Entity):
    """
    Location type.

    A location type denotes the kind of container for locations such as a
    drawer, a robot or a freezer.
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
        """
        Equality depends on the name attribute.
        """
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
    Barcoded location.

    A barcoded location may hold a rack.

    :Note: The location represents a unique, unambiguous location, e.g.
           not a complete drawer, but a certain position within the drawer.
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
    #: An identifier for a section within a robot, drawer etc.
    index = None
    #: Associated rack checked in at this barcoded location.
    location_rack = None

    def __init__(self, name, label, type, barcode, location_rack=None, # redef type pylint: disable=W0622
                 device=None, index=None, **kw):
        Entity.__init__(self, **kw)
        #FIXME: #pylint: disable=W0511
        #       this awaits proper handling of character ids on DB level
        self.name = name
        self.label = label
        self.type = type
        self.device = device
        self.index = index
        self.barcode = barcode
        self.location_rack = location_rack

    @property
    def slug(self):
        #: The slug for instances of this class is derived from the
        #: :attr:`name`.
        return slug_from_string(self.name)

    def __str__(self):
        return self.name

    def __repr__(self):
        str_format = '<%s barcode: %s, name: %s, label: %s, ' \
                     'type: %s, device: %s, index: %s>'
        params = (self.__class__.__name__, self.barcode, self.name,
                  self.label, self.type, self.device, self.index)
        if not self.location_rack is None:
            str_format += ', rack barcode: %s'
            params += (self.location_rack.rack.barcode,)
        else:
            str_format += ', empty: True'
        return str_format % params

    def checkin_rack(self, rack):
        """
        Checks in the given rack at this barcoded location.
        """
        if not self.location_rack is None:
            raise RuntimeError('Can not check in a rack in an occupied '
                               'location.')
        self.location_rack = BarcodedLocationRack(rack, self)
        rack.check_in()

    def checkout_rack(self):
        """
        Checks out the rack held at this barcoded location.
        """
        if self.location_rack is None:
            raise RuntimeError('Location does not have a rack to check out.')
        self.location_rack.rack.check_out()
        self.location_rack = None

    @property
    def empty(self):
        return self.location_rack is None

    @property
    def rack(self):
        if self.location_rack is None:
            result = None
        else:
            result = self.location_rack.rack
        return result

    @property
    def rack_checkin_date(self):
        if self.location_rack is None:
            result = None
        else:
            result = self.location_rack.checkin_date
        return result


class BarcodedLocationRack(Entity):
    """
    Information about a rack held in a barcoded location.
    """
    #: Rrack (:class:`thelma.entities.rack.Rack`) stored at the location.
    rack = None
    #: Barcoded location holding the rack.
    location = None
    #: Date a rack was last checked into this location. This is `None` if
    #: the location is empty.
    checkin_date = None

    def __init__(self, rack, location, checkin_date=None, **kw):
        Entity.__init__(self, **kw)
        self.rack = rack
        self.location = location
        if checkin_date is None:
            checkin_date = datetime.datetime.now()
        self.checkin_date = checkin_date
