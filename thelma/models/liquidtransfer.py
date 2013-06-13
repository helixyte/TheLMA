"""
Pipetting models (liquid transfers)

Oct 2011, AAB
"""
from everest.entities.base import Entity
from everest.entities.utils import slug_from_integer
from everest.entities.utils import slug_from_string
from thelma.utils import get_utc_time

__docformat__ = 'reStructuredText en'

__author__ = 'Anna-Antonia Berger'

__all__ = ['TRANSFER_TYPES',
           'PlannedTransfer',
           'PlannedContainerDilution',
           'PlannedContainerTransfer',
           'PlannedRackTransfer',
           'PlannedWorklist',
           'WorklistSeries',
           'WorklistSeriesMember',
           'ExecutedTransfer',
           'ExecutedContainerDilution',
           'ExecutedContainerTransfer',
           'ExecutedRackTransfer',
           'ExecutedWorklist',
           'PipettingSpecs',
           'ReservoirSpecs']


### New Entities

class TRANSFER_TYPES(object):
    LIQUID_TRANSFER = 'TRANSFER_TYPE'
    CONTAINER_DILUTION = 'CONTAINER_DILUTION'
    CONTAINER_TRANSFER = 'CONTAINER_TRANSFER'
    RACK_TRANSFER = 'RACK_TRANSFER'


class PlannedTransfer(Entity):
    """
    This is an abstract base class for planned transfers. A planned transfer
    represents a single (atomic) aspire-dispense operation. Planned transfers
    are always part of a planned worklist. \'Planned\' here indicates that
    the entities hold only general data (volume, rack position, etc.).
    The transfer is not specific for a rack or container.

    **Equality Condition**: equal :attr:`id`
    """

    #: The volume to be transferred (float) in liters.
    volume = None
    #: The type of the transfer (element of :class:`TRANSFER_TYPES`).
    type = None
    #: The executions for this planned transfer (:class:`ExecutedTransfer`).
    executed_transfers = None
    #: The worklist this transfer belongs to.
    planned_worklist = None

    def __init__(self, volume, **kw):
        """
        Constructor
        """
        Entity.__init__(self, **kw)
        if self.__class__ is PlannedTransfer:
            raise NotImplementedError('Abstract class')
        self.volume = volume

    @property
    def slug(self):
        """
        The slug of a planned transfer is its :attr:`id`.
        """
        if self.id is None:
            slug = None
        else:
            slug = slug_from_integer(self.id)
        return slug

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and self.id == other.id)

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __str__(self):
        return self.id


class PlannedContainerDilution(PlannedTransfer):
    """
    A container dilution is a planned transfer in which a volume
    is added to a source well. The origin of the volume is not regarded -
    source wells are assigned on the fly during worklist file creation.

    **Equality Condition**: equal :attr:`id`
    """

    #: The rack position (:class:`thelma.models.rack.RackPosition`) to which
    #: the volume is added.
    target_position = None
    #: Furhter information (e.g. name and concentration) of the diluent as
    #: :class:`str` (optional). This becomes applicable to distinguish
    #: different diluent (and thus sources) within a worklist.
    diluent_info = None

    def __init__(self, volume, target_position, diluent_info, **kw):
        """
        Constructor
        """
        PlannedTransfer.__init__(self, volume, **kw)
        self.type = TRANSFER_TYPES.CONTAINER_DILUTION
        self.target_position = target_position
        self.diluent_info = diluent_info

    def __repr__(self):
        str_format = '<%s id: %s, volume: %s, target position: %s, ' \
                     'diluent info: %s>'
        params = (self.__class__.__name__, self.id, self.volume,
                  self.target_position, self.diluent_info)
        return str_format % params


class PlannedContainerTransfer(PlannedTransfer):
    """
    A container transfer is a planned transfer in which a volume
    is transfer from one container (in the source rack) to another container
    (in the target rack - target rack and source rack can be identical).

    **Equality Condition**: equal :attr:`id`
    """

    #: The rack position (:class:`thelma.models.rack.RackPosition`) from which
    #: the volume is taken.
    source_position = None
    #: The rack position (:class:`thelma.models.rack.RackPosition`) to which
    #: the volume is added.
    target_position = None

    def __init__(self, volume, source_position, target_position, **kw):
        """
        Constructor
        """
        PlannedTransfer.__init__(self, volume, **kw)
        self.type = TRANSFER_TYPES.CONTAINER_TRANSFER
        self.source_position = source_position
        self.target_position = target_position

    def __repr__(self):
        str_format = '<%s id: %s, volume: %s, source position: %s, ' \
                     'target position: %s>'
        params = (self.__class__.__name__, self.id, self.volume,
                  self.source_position, self.target_position)
        return str_format % params


class PlannedRackTransfer(PlannedTransfer):
    """
    A rack transfer is a planned transfer in which the content of a rack
    (sector) is transfer to another rack (sector) in a one-to-one fashion.
    Single containers cannot be added or omitted. Furthermore, the transferred
    volume must be the same for all containers.
    A rack transfer represents a part of a CyBio run.

    **Equality Condition**: equal :attr:`id`
    """

    #: The sector of the source plate the volume is taken from (:class:`int`).
    source_sector_index = None
    #: The sector of the target plate the volume is dispensed into
    #: (:class:`int`).
    target_sector_index = None
    #: The total number of sectors (:class:`int`).
    sector_number = None

    def __init__(self, volume, source_sector_index, target_sector_index,
                 sector_number, **kw):
        """
        Constructor
        """
        PlannedTransfer.__init__(self, volume, **kw)
        self.type = TRANSFER_TYPES.RACK_TRANSFER
        self.source_sector_index = source_sector_index
        self.target_sector_index = target_sector_index
        self.sector_number = sector_number

    @classmethod
    def create_one_to_one(cls, volume):
        """
        Creates a one-to-one (replicating) transfer.
        """
        return PlannedRackTransfer(volume=volume,
                                   source_sector_index=0,
                                   target_sector_index=0,
                                   sector_number=1)

    def __repr__(self):
        str_format = '<%s id: %s, volume: %s, source sector: %s, ' \
                     'target sector: %s, number of sectors: %s>'
        params = (self.__class__.__name__, self.id, self.volume,
                  self.source_sector_index, self.target_sector_index,
                  self.sector_number)
        return str_format % params


class PlannedWorklist(Entity):
    """
    A planned worklist represents an (abstract unordered) series of liquid
    transfer steps. It allows the generation of a robot worklist file.

    **Equality Condition**: equal :attr:`id`
    """

    #: A label for the worklist.
    label = None
    #: The particular steps forming this worklist (list of
    #: :class:`PlannedTransfer` entities (all of the same type)).
    planned_transfers = None
    #: The :class:`WorklistSeriesMember` entity linking this worklist to
    #: a particular worklist series.
    worklist_series_member = None
    #: A list of executed worklists (:class:`ExecutedWorklist`) for this
    #: planned worklist.
    executed_worklists = None

    def __init__(self, label, planned_transfers=None,
                 worklist_series_member=None, executed_worklists=None, **kw):
        """
        Constructor
        """
        Entity.__init__(self, **kw)
        self.label = label
        if planned_transfers is None:
            planned_transfers = []
        self.planned_transfers = planned_transfers
        self.worklist_series_member = worklist_series_member
        if executed_worklists is None:
            executed_worklists = []
        self.executed_worklists = []

    @property
    def slug(self):
        """
        The slug of a planned worklist is its :class:`id`.
        """
        if self.id is None:
            slug = None
        else:
            slug = slug_from_integer(self.id)
        return slug

    def __eq__(self, other):
        return (isinstance(other, PlannedWorklist) and self.id == other.id)

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __str__(self):
        return self.id

    def __repr__(self):
        str_format = '<%s id: %s, label: %s, number of executions: %i>'
        params = (self.__class__.__name__, self.id, self.label,
                  len(self.executed_worklists))
        return str_format % params

    def __get_index(self):
        if self.worklist_series_member is None:
            return None
        else:
            return self.worklist_series_member.index

    def __get_worklist_series(self):
        if self.worklist_series_member is None:
            return None
        else:
            return self.worklist_series_member.worklist_series

    def __set_index(self, index):
        if self.worklist_series_member is None:
            raise ValueError('Can not set index for a planned worklist '
                             'which is not part of a worklist series.')
        self.worklist_series_member.index = index

    def __set_worklist_series(self, worklist_series):
        if self.worklist_series_member is None:
            raise ValueError('Can not set worklist series for a planned ' \
                             'worklist without an index.')
        self.worklist_series_member.worklist_series = worklist_series

    index = property(__get_index, __set_index)
    worklist_series = property(__get_worklist_series, __set_worklist_series)


class WorklistSeries(Entity):
    """
    This class represents an ordered series of :class:`PlannedWorklist` objects.

    **Equality Condition**: equal :attr:`id`
    """

    #: The :class:`WorklistSeriesMember` entity linking this worklist series to
    #: the particular worklists belonging to it.
    worklist_series_members = None

    def __init__(self, **kw):
        """
        Constructor
        """
        Entity.__init__(self, **kw)
        self.worklist_series_members = []

    @property
    def slug(self):
        """
        The slug of a worklist series is its :class:`id`.
        """
        if self.id is None:
            slug = None
        else:
            slug = slug_from_integer(self.id)
        return slug

    def add_worklist(self, index, worklist):
        """
        Adds the worklists using the index provided.
        """
        WorklistSeriesMember(planned_worklist=worklist, worklist_series=self,
                             index=index)

    def get_worklist_for_index(self, wl_index):
        """
        Returns the :class:`PlannedWorklist` for the given index.

        :param wl_index: Index of the worklist within the series.
        :type wl_index: positive number
        :return: The :class:`PlannedWorklist` for the given index.
        :raises ValueError: If there is no worklist for the given index.
        """
        for wsm in self.worklist_series_members:
            if wsm.index == wl_index: return wsm.planned_worklist

        raise ValueError('There is no worklist for index %i!' % (wl_index))

    def __eq__(self, other):
        return (isinstance(other, WorklistSeries) and self.id == other.id)

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __str__(self):
        return self.id

    def __repr__(self):
        str_format = '<%s id: %s, number of worklists: %i>'
        params = (self.__class__.__name__, self.id,
                  len(self.worklist_series_members))
        return str_format % params

    def __len__(self):
        return len(self.worklist_series_members)

    def __iter__(self):
        return iter(self.__get_planned_worklists())

    def __get_planned_worklists(self):
        worklists = []
        for series_member in self.worklist_series_members:
            worklists.append(series_member.planned_worklist)
        return worklists

    planned_worklists = property(__get_planned_worklists)


class WorklistSeriesMember(Entity):
    """
    The class links :class:`PlannedWorklists` to a :class:`WorklistSeries`.

    **Equality Condition**: equal :attr:`planned_worklists` and
        :attr:`worklist_series`
    """

    #: The planned worklist being the series member.
    planned_worklist = None
    #: The worklist series the plan belongs to.
    worklist_series = None
    #: The index of the worklist within the series.
    index = None

    def __init__(self, planned_worklist, worklist_series, index, **kw):
        Entity.__init__(self, **kw)
        self.planned_worklist = planned_worklist
        self.worklist_series = worklist_series
        self.index = index

    def __eq__(self, other):
        return (isinstance(other, WorklistSeriesMember) and \
                self.planned_worklist == other.planned_worklist and \
                self.worklist_series == other.worklist_series)

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __str__(self):
        return '%s:%s' % (self.planned_worklist, self.worklist_series)

    def __repr__(self):
        str_format = '<%s planned worklist: %s, index: %s, worklist ' \
                     'series: %s>'
        params = (self.__class__.__name__, self.planned_worklist,
                  self.index, self.worklist_series)
        return str_format % params



class ExecutedTransfer(Entity):
    """
    This is an abstract base class for executed transfer. An executed transfer
    represents a planned transfer that has actually been carried out. Thus,
    there are specific racks or containers involved.

    **Equality Condition**: equal :attr:`id`
    """

    #: The planned transfer that has been executed (:class:`PlannedTransfer`).
    planned_transfer = None
    #: The user who has carried out the transfer
    #: (:class:thelma.models.user.User`).
    user = None
    #: The time stamp is set upon entity creation. It represents the time
    #: the transfer has been executed on DB level.
    timestamp = None
    #: The type of the transfer (element of :class:`TRANSFER_TYPES`) depends
    #: on the type of the associated :attr:`planned_transfer`.
    transfer_type = None

    def __init__(self, planned_transfer, user, timestamp=None,
                 type=None, **kw): # pylint: disable=W0622
        """
        Constructor
        """
        Entity.__init__(self, **kw)
        if type is None:
            type = self.__class__.transfer_type
        self.type = type
        if self.__class__ is ExecutedTransfer:
            raise NotImplementedError('Abstract class')
        if not planned_transfer.type == self.type:
            raise ValueError('Invalid planned transfer type "%s" for ' \
                             'executed transfer class %s.' % \
                             (planned_transfer.type, self.__class__.__name__))
        self.planned_transfer = planned_transfer
        self.user = user
        if timestamp is None:
            timestamp = get_utc_time()
        self.timestamp = timestamp

    @property
    def slug(self):
        """
        The slug of an executed transfer is its :class:`id`.
        """
        if self.id is None:
            slug = None
        else:
            slug = slug_from_integer(self.id)
        return slug

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and self.id == other.id)

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __str__(self):
        return self.id


class ExecutedContainerDilution(ExecutedTransfer):
    """
    An executed container dilution. Container dilution means that there
    source well. The source well is not specified since it exists only
    temporary. Instead the specs of the source rack are logged.

    **Equality Condition**: equal :attr:`id`
    """

    #: The container the volume has been dispensed into
    #: (:class:`thelma.models.container.Container`).
    target_container = None
    #: The specs of the source reservoir (:class:`ReservoirSpecs`).
    reservoir_specs = None
    #: The type of the transfer (element of :class:`TRANSFER_TYPES`) depends
    #: on the type of the associated :attr:`planned_transfer`.
    transfer_type = TRANSFER_TYPES.CONTAINER_DILUTION

    def __init__(self, target_container, reservoir_specs,
                 planned_container_dilution, user, timestamp=None, **kw):
        """
        Constructor
        """
        ExecutedTransfer.__init__(self, user=user, timestamp=timestamp,
                                  planned_transfer=planned_container_dilution,
                                  **kw)
        self.target_container = target_container
        self.reservoir_specs = reservoir_specs

    @property
    def planned_container_dilution(self):
        """
        The planned container dilution that has been executed
        (:class:`PlannedContainerDilution`).
        """
        return self.planned_transfer

    @property
    def target_rack(self):
        """
        The rack of the target container.
        """
        return self.target_container.location.rack

    def __repr__(self):
        str_format = '<%s id: %s, target container: %s, reservoir specs: %s, ' \
                     'user: %s>'
        params = (self.__class__.__name__, self.id, self.target_container,
                  self.reservoir_specs, self.user)
        return str_format % params


class ExecutedContainerTransfer(ExecutedTransfer):
    """
    An executed container transfer. Container transfer represent transfer
    from one source container to a target container. The container can
    be situated in different racks.

    **Equality Condition**: equal :attr:`id`
    """

    #: The container the volume has been taken from
    #: (:class:`thelma.models.container.Container`).
    source_container = None
    #: The container the volume has been dispensed into
    #: (:class:`thelma.models.container.Container`).
    target_container = None
    #: The type of the transfer (element of :class:`TRANSFER_TYPES`) depends
    #: on the type of the associated :attr:`planned_transfer`.
    transfer_type = TRANSFER_TYPES.CONTAINER_TRANSFER

    def __init__(self, source_container, target_container,
                 planned_container_transfer, user, timestamp=None, **kw):
        """
        Constructor
        """
        ExecutedTransfer.__init__(self, user=user, timestamp=timestamp,
                                  planned_transfer=planned_container_transfer,
                                  **kw)
        self.source_container = source_container
        self.target_container = target_container

    @property
    def planned_container_transfer(self):
        """
        The planned container transfer that has been executed
        (:class:`PlannedContainerTransfer`).
        """
        return self.planned_transfer

    @property
    def target_rack(self):
        """
        The rack of the target container.
        """
        return self.target_container.location.rack

    @property
    def source_rack(self):
        """
        The rack of the source container.
        """
        return self.source_container.location.rack

    def __repr__(self):
        str_format = '<%s id: %s, source container: %s, target ' \
                     'container: %s, user: %s>'
        params = (self.__class__.__name__, self.id, self.source_container,
                  self.target_container, self.user)
        return str_format % params


class ExecutedRackTransfer(ExecutedTransfer):
    """
    An executed rack transfer. In the rack transfer the contents of all
    containers of a rack (sector) is transferred to another rack (sector).
    The volumes must be the same for all containers.

    **Equality Condition**: equal :attr:`id`
    """

    #: The rack the volumes are taken from (:class:`thelma.models.rack.Rack`).
    source_rack = None
    #: The rack the volumes are dispensed into
    #: (:class:`thelma.models.rack.Rack`).
    target_rack = None
    #: The type of the transfer (element of :class:`TRANSFER_TYPES`) depends
    #: on the type of the associated :attr:`planned_transfer`.
    transfer_type = TRANSFER_TYPES.RACK_TRANSFER

    def __init__(self, source_rack, target_rack, planned_rack_transfer,
                 user, timestamp=None, **kw):
        """
        Constructor
        """
        ExecutedTransfer.__init__(self, planned_transfer=planned_rack_transfer,
                                  user=user, timestamp=timestamp, **kw)
        self.source_rack = source_rack
        self.target_rack = target_rack

    @property
    def planned_rack_transfer(self):
        """
        The planned rack transfer that has been executed
        (:class:`PlannedRackTransfer`).
        """
        return self.planned_transfer

    def __repr__(self):
        str_format = '<%s id: %s, source rack: %s, target rack: %s, user: %s>'
        params = (self.__class__.__name__, self.id, self.source_rack,
                  self.target_rack, self.user)
        return str_format % params


class ExecutedWorklist(Entity):
    """
    This class represents a planned worklist that has actually been carried out.

    **Equality Condition**: equal :attr:`id`
    """

    #: The planned worklist that has been executed (:class:`PlannedWorklist`).
    planned_worklist = None
    #: The executed transfer steps belonging to this worklist
    #: (list of :class:`ExecutedTransfer` objects).
    executed_transfers = None

    def __init__(self, planned_worklist, executed_transfers=None, **kw):
        """
        Constructor
        """
        Entity.__init__(self, **kw)
        self.planned_worklist = planned_worklist
        if executed_transfers is None:
            executed_transfers = []
        self.executed_transfers = executed_transfers

    @property
    def worklist_series(self):
        """
        The worklist series the planned worklist belongs to.
        """
        return self.planned_worklist.worklist_series

    @property
    def slug(self):
        """
        The slug of a planned transfer is its :attr:`id`.
        """
        if self.id is None:
            slug = None
        else:
            slug = slug_from_integer(self.id)
        return slug

    def __eq__(self, other):
        return isinstance(other, ExecutedWorklist) and self.id == other.id

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __str__(self):
        return self.id

    def __repr__(self):
        str_format = '<%s id: %s, planned worklist: %s>'
        params = (self.__class__.__name__, self.id, self.planned_worklist.label)
        return str_format % params


class PipettingSpecs(Entity):
    """
    Contains the properties for a pipetting method or robot.

    **Equality Condition**: equal :attr:`name`
    """
    #: The name of the robot or method.
    name = None
    #: The minimum volume that can be pipetted with this method in l.
    min_transfer_volume = None
    #: The maximum volume that can be pipetted with this method in l.
    max_transfer_volume = None
    #: The maximum dilution that can achieved with a one-step transfer.
    max_dilution_factor = None
    #: For some robots the dead volume depends on the number of transfers
    #: taken from a source well. The minimum and maximum dead volume depend
    #: on the :class:`ReservoirSpecs`.
    has_dynamic_dead_volume = None
    #: Some robots have limitation regarding the possible target positions for
    #: a source position.
    is_sector_bound = None

    def __init__(self, name, min_transfer_volume, max_transfer_volume,
                 max_dilution_factor, has_dynamic_dead_volume, is_sector_bound,
                 **kw):
        """
        Constructor
        """
        Entity.__init__(self, **kw)
        self.name = name
        self.min_transfer_volume = min_transfer_volume
        self.max_transfer_volume = max_transfer_volume
        self.max_dilution_factor = max_dilution_factor
        self.has_dynamic_dead_volume = has_dynamic_dead_volume
        self.is_sector_bound = is_sector_bound

    @property
    def slug(self):
        """
        The slug of a planned transfer is its :attr:`name`.
        """
        return slug_from_string(self.name)

    def __eq__(self, other):
        return isinstance(other, PipettingSpecs) and \
                    other.name == self.name

    def __str__(self):
        return self.name

    def __repr__(self):
        str_format = '<%s name: %s>'
        params = (self.__class__.__name__, self.name)
        return str_format % params


class ReservoirSpecs(Entity):
    """
    A reservoir represents an anonymous source rack. Reservoirs
    exist only temporary (in the physical world) and are not stored in the DB.
    They constitute the source for container dilutions where the origin of a
    volume is not specified.

    **Equality condition:** equal :attr:`rack_shape`, :attr:`max_volume`,
        :attr:`min_dead_volume` and attr:`max_dead_volume`
    """

    #: This attribute is used as slug.
    name = None
    #: Container a little more information than the :attr:`name`.
    description = None
    #: The rack shape of the reservoir (:class:`thelma.model.Rack.RackShape`).
    rack_shape = None
    #: The maximum volume of a rack container in liters.
    max_volume = None
    #: The minimum dead volume of a rack container.
    min_dead_volume = None
    #: The maximum dead volume of a rack container.
    max_dead_volume = None


    def __init__(self, name, description, rack_shape, max_volume,
                 min_dead_volume, max_dead_volume, **kw):
        """
        Constructor
        """
        Entity.__init__(self, **kw)
        self.name = name
        self.description = description
        self.rack_shape = rack_shape
        self.max_volume = max_volume
        self.min_dead_volume = min_dead_volume
        self.max_dead_volume = max_dead_volume

    @property
    def slug(self):
        """
        The slug of a reservoir spec is its :class:`name`.
        """
        return slug_from_string(self.name)

    def __eq__(self, other):
        return isinstance(other, ReservoirSpecs) and \
                self.rack_shape == other.rack_shape and \
                self.max_volume == other.max_volume and \
                self.min_dead_volume == other.min_dead_volume and \
                self.max_dead_volume == other.max_dead_volume

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __str__(self):
        return self.name

    def __repr__(self):
        str_format = '<%s id: %s, name: %s, rack shape: %s, maximum ' \
                     'volume: %s, min dead volume: %s, max dead volume: %s>'
        params = (self.__class__.__name__, self.id, self.name,
                  self.rack_shape, self.max_volume, self.min_dead_volume,
                  self.max_dead_volume)
        return str_format % params
