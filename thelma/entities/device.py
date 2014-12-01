"""
Device entity classes.
"""
from everest.entities.base import Entity
from everest.entities.utils import slug_from_string


__docformat__ = 'reStructuredText en'
__all__ = ['Device',
           'DeviceType']


class DeviceType(Entity):
    """
    This class defines the general application area of a device.
    Manufacturer and model of a device are not defined here but in the
    class :class:`Device`.
    """
    #: The name of the device type (unique).
    name = None
    #: The name of that device type (human readable marker).
    label = None
    #: list of devices (:class:`Device`) having that type.
    devices = None

    def __init__(self, name, label, devices=None, **kw):
        Entity.__init__(self, **kw)
        self.name = name
        self.label = label
        if devices is None:
            devices = []
        self.devices = devices

    @property
    def slug(self):
        #: The slug for instances of this class is derived from the
        #: :attr:`name`.
        return slug_from_string(self.name)

    def __str__(self):
        return self.name

    def __repr__(self):
        str_format = '<%s id: %s, name: %s, label: %s>'
        params = (self.__class__.__name__, self.id, self.name, self.label)
        return str_format % params


class Device(Entity):
    """
    Represents an external device.
    """
    #: The name of the device (unique).
    name = None
    #: The label of the device (human readable marker).
    label = None
    #: The device type (:class:`DeviceType`).
    type = None
    #: The manufacturer of this device
    #: (:class:`thelma.entities.organization.Organization`).
    manufacturer = None
    #: Model of the device.
    model = None
    #: list of device locations
#    locations = None

    def __init__(self, name, label, type, manufacturer, model, # pylint:disable=W0622
                 locations=None, **kw):
        Entity.__init__(self, **kw)
        #FIXME: #pylint: disable=W0511
        #       this awaits proper handling of character ids on DB level
        self.name = name
        self.label = label
        self.type = type
        self.manufacturer = manufacturer
        self.model = model
        if locations is None:
            locations = []
        self.locations = locations

    @property
    def slug(self):
        #: The slug for instances of this class is derived from the
        #: :attr:`name`.
        return slug_from_string(self.name)

    def __str__(self):
        return self.name

    def __repr__(self):
        str_format = '<%s id: %s, name: %s, label: %s, type: %s, ' \
                 'manufacturer: %s>'
        params = (self.__class__.__name__, self.id, self.name, self.label,
                  self.type, self.manufacturer)
        return str_format % params
