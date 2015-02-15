"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Pipetting entity classes (liquid transfers).

Created Oct 2011
"""
from md5 import md5

from everest.entities.base import Entity
from everest.entities.utils import get_root_aggregate
from everest.entities.utils import slug_from_integer
from everest.entities.utils import slug_from_string
from thelma.interfaces import IPlannedLiquidTransfer
from thelma.interfaces import IPlannedRackSampleTransfer
from thelma.interfaces import IPlannedSampleDilution
from thelma.interfaces import IPlannedSampleTransfer
from thelma.utils import get_utc_time


__docformat__ = 'reStructuredText en'
__all__ = ['TRANSFER_TYPES',
           'PlannedLiquidTransfer',
           'PlannedSampleDilution',
           'PlannedSampleTransfer',
           'PlannedRackSampleTransfer',
           'PlannedWorklist',
           'WorklistSeries',
           'WorklistSeriesMember',
           'ExecutedLiquidTransfer',
           'ExecutedSampleDilution',
           'ExecutedSampleTransfer',
           'ExecutedRackSampleTransfer',
           'ExecutedWorklist',
           'PipettingSpecs',
           'ReservoirSpecs']


### New Entities

class TRANSFER_TYPES(object):
    LIQUID_TRANSFER = 'TRANSFER_TYPE'
    SAMPLE_DILUTION = 'SAMPLE_DILUTION'
    SAMPLE_TRANSFER = 'SAMPLE_TRANSFER'
    RACK_SAMPLE_TRANSFER = 'RACK_SAMPLE_TRANSFER'


class PlannedLiquidTransfer(Entity):
    """
    This is an abstract base class for planned liquid transfers. A planned
    transfer represents a single (atomic) aspire-dispense operation. Planned
    liquid transfers are always part of a planned worklist.
    \'Planned\' here indicates that the entities hold only general data
    (volume, rack position, etc.). The transfer is not specific for a rack
    or container.

    :Note: Do not create directly but use the :func:`get_entity` method.
    """
    #: The volume to be transferred (float) *in liters*.
    _volume = None
    #: The type of the transfer (element of :class:`TRANSFER_TYPES`).
    _transfer_type = None
    #: An md5 encoded string derived from the attributes of a planned liquid
    #: transfer. The way the hash value is generated depends on the subclass.
    _hash_value = None

    #: The marker interface used to search the DB for existing planned liquid
    #: transfer entities.
    _MARKER_INTERFACE = IPlannedLiquidTransfer

    #: Separates the values in hash value generation.
    __HASH_SEPARATOR = ';'

    def __init__(self, volume, hash_value=None, transfer_type=None, **kw):
        """
        Constructor
        """
        Entity.__init__(self, **kw)
        if self.__class__ is PlannedLiquidTransfer:
            raise NotImplementedError('Abstract class')
        self._volume = volume
        self._hash_value = hash_value
        if transfer_type is None:
            transfer_type = TRANSFER_TYPES.LIQUID_TRANSFER
        self._transfer_type = transfer_type

    @property
    def slug(self):
        """
        The slug is derived from the :attr:`hash_value`.
        """
        return slug_from_string(self._hash_value)

    @property
    def hash_value(self):
        """
        An md5 encoded string derived from the attributes of a planned liquid
        transfer.
        """
        return self._hash_value

    @property
    def volume(self):
        """
        The volume to be transferred (float) *in liters*.
        """
        return self._volume

    @property
    def transfer_type(self):
        """
        The type of the transfer (element of :class:`TRANSFER_TYPES`).
        """
        return self._transfer_type

    @classmethod
    def create_from_data(cls, data):
        # We reuse existing transfers with the same hash value.
        volume = data.pop('volume')
        hash_value = cls.get_hash_value(volume, **data)
        agg = get_root_aggregate(cls._MARKER_INTERFACE)
        pt = agg.get_by_slug(hash_value)
        if pt is None:
            pt = cls(volume=volume, hash_value=hash_value, **data)
            agg.add(pt)
        return pt

    @classmethod
    def get_hash_value(cls, volume, **kw):
        """
        Returns the hash value for the passed values.

        :param volume: The volume. The unit will be regarded as litre, if the
            value is smaller 1, otherwise the unit will be assumed to be *ul*.
        :type volume: positive number
        """
        raise NotImplementedError('Abstract method.')

    @classmethod
    def _create_hash_value(cls, value_list):
        """
        Helper method concatenating the values in the list (using the
        :attr:`__HASH_SEPARATOR` ) and creating a md5 encoded string from it.
        """
        value_str = cls.__HASH_SEPARATOR.join(value_list)
        return md5(value_str).hexdigest()

    @classmethod
    def _get_volume_str_in_ul(cls, volume):
        """
        If the value is smaller 1, otherwise the unit will be assumed to
        be *ul*. Conversion is required because hash values use the volume
        *in ul* to decrease the number of rendering variations.
        """
        if volume > 1:
            vol = volume
        else:
            vol = volume * 1e6
        vol_str = '%.1f' % (vol)
        if vol_str.endswith('.0'):
            vol_str = vol_str[:-2]
        return vol_str

    def __eq__(self, other):
        """
        Equality is based on the hash_value attribute.
        """
        return isinstance(other, self.__class__) and \
                self._hash_value == other.hash_value

    def __hash__(self):
        return hash(self._hash_value)


class PlannedSampleDilution(PlannedLiquidTransfer):
    """
    A sample dilution is a planned liquid transfer in which a volume
    is added to a source well. The origin of the volume is not regarded -
    source wells are assigned on the fly during worklist file creation.

    :Note: Do not create directly but use the :func:`get_entity` method.
    """

    #: The rack position (:class:`thelma.entities.rack.RackPosition`) to which
    #: the volume is added.
    _target_position = None
    #: Further information (e.g. name and concentration) of the diluent as
    #: :class:`str`. This becomes applicable to distinguish
    #: different diluent (and thus sources) within a worklist.
    _diluent_info = None

    _MARKER_INTERFACE = IPlannedSampleDilution

    def __init__(self, volume, hash_value, target_position, diluent_info,
                 **kw):
        PlannedLiquidTransfer.__init__(self, volume=volume,
                                transfer_type=TRANSFER_TYPES.SAMPLE_DILUTION,
                                hash_value=hash_value, **kw)
        self._target_position = target_position
        self._diluent_info = diluent_info

    @classmethod
    def get_entity(cls, volume, diluent_info, target_position):
        """
        Factory method returning the planned sample transfer for the given
        values. If there is already an entity with this values in the DB,
        the entity will be loaded, otherwise a new entity is generated.

        :param float volume: The volume *in l* (greater than zero).
        :param str diluent_info: Further information (e.g. name and
            concentration) of the diluent.
        :param target_position: The rack position to which the volume is added.
        :type target_position: :class:`thelma.entities.rack.RackPosition`
        :returns: :class:`PlannedSampleDilution`
        """
        data = dict(diluent_info=diluent_info,
                    target_position=target_position)
        data['volume'] = volume
        return cls.create_from_data(data)

    #pylint: disable=W0221
    @classmethod
    def get_hash_value(cls, volume, diluent_info, target_position):
        """
        The hash value for sample dilutions is comprised of the volume (in ul),
        diluent info and target position ID.

        :param float volume: The volume (greater than zero). Assuming litre
            as unit if volume is smaller than 1, *ul* otherwise.
        :param str diluent_info: Further information (e.g. name and
            concentration) of the diluent.
        :param target_position: The rack position to which the volume is added.
        :type target_position: :class:`thelma.entities.rack.RackPosition`

        :return: The sample dilution hash value for the passed values.
        """
        volume_in_ul = cls._get_volume_str_in_ul(volume)
        values = [volume_in_ul, diluent_info, str(target_position.id)]
        return cls._create_hash_value(values)
    #pylint: enable=W0221

    @property
    def target_position(self):
        """
        The rack position (:class:`thelma.entities.rack.RackPosition`) to which
        the volume is added.
        """
        return self._target_position

    @property
    def diluent_info(self):
        """
        Further information (e.g. name and concentration) of the diluent.
        """
        return self._diluent_info

    def __repr__(self):
        str_format = '<%s id: %s, volume: %s, target position: %s, ' \
                     'diluent info: %s>'
        params = (self.__class__.__name__, self.id, self._volume,
                  self._target_position, self._diluent_info)
        return str_format % params


class PlannedSampleTransfer(PlannedLiquidTransfer):
    """
    A sample transfer is a planned liquid transfer in which a volume
    is transfer from one sample (in the source rack) to another sample
    (in the target rack - target rack and source rack can be identical).

    :Note: Do not create directly but use the :func:`get_entity` method.
    """
    #: The rack position (:class:`thelma.entities.rack.RackPosition`) from which
    #: the volume is taken.
    _source_position = None
    #: The rack position (:class:`thelma.entities.rack.RackPosition`) to which
    #: the volume is added.
    _target_position = None

    _MARKER_INTERFACE = IPlannedSampleTransfer

    def __init__(self, volume, hash_value, source_position, target_position,
                 **kw):
        PlannedLiquidTransfer.__init__(self, volume,
                               transfer_type=TRANSFER_TYPES.SAMPLE_TRANSFER,
                               hash_value=hash_value, **kw)
        self._source_position = source_position
        self._target_position = target_position

    @property
    def source_position(self):
        """
        The rack position (:class:`thelma.entities.rack.RackPosition`) from which
        the volume is taken.
        """
        return self._source_position

    @property
    def target_position(self):
        """
        The rack position (:class:`thelma.entities.rack.RackPosition`) to which
        the volume is added.
        """
        return self._target_position

    @classmethod
    def get_entity(cls, volume, source_position, target_position):
        """
        Factory method returning the planned sample transfer for the given
        values. If there is already an entity with this values in the DB,
        the entity will be loaded, otherwise a new entity is generated.

        :param volume: The volume *in l*.
        :type volume: positive number

        :param source_position: The rack position from which the volume is
            taken.
        :type source_position: :class:`thelma.entities.rack.RackPosition`

        :param target_position: The rack position to which the volume is added.
        :type target_position: :class:`thelma.entities.rack.RackPosition`

        :return: :class:`PlannedSampleTransfer`
        """
        data = dict(source_position=source_position,
                    target_position=target_position)
        data['volume'] = volume
        return cls.create_from_data(data)

    #pylint: disable=W0221
    @classmethod
    def get_hash_value(cls, volume, source_position, target_position):
        """
        The hash value for sample transfers is comprised of the volume (in ul),
        source position ID and target position ID.

        :param volume: The volume. The unit will be regarded as litre, if the
            value is smaller 1, otherwise the unit will be assumed to be *ul*.
        :type volume: positive number

        :param source_position: The rack position from which the volume is
            taken.
        :type source_position: :class:`thelma.entities.rack.RackPosition`

        :param target_position: The rack position to which the volume is added.
        :type target_position: :class:`thelma.entities.rack.RackPosition`

        :return: The sample dilution hash value for the passed values.
        """
        volume_in_ul = cls._get_volume_str_in_ul(volume)
        values = [volume_in_ul, str(source_position.id),
                  str(target_position.id)]
        return cls._create_hash_value(values)
    #pylint: enable=W0221

    def __repr__(self):
        str_format = '<%s id: %s, volume: %s, source position: %s, ' \
                     'target position: %s>'
        params = (self.__class__.__name__, self.id, self._volume,
                  self._source_position, self._target_position)
        return str_format % params


class PlannedRackSampleTransfer(PlannedLiquidTransfer):
    """
    A rack sample transfer is a planned transfer in which the content of a rack
    (sector) is transfer to another rack (sector) in a one-to-one fashion.
    Single samples cannot be added or omitted. Furthermore, the transferred
    volume must be the same for all samples.
    A rack sample transfer represents a part of a CyBio run.

    :Note: Do not create directly but use the :func:`get_entity` method.
    """
    #: The sector of the source plate the volume is taken from (:class:`int`).
    _source_sector_index = None
    #: The sector of the target plate the volume is dispensed into
    #: (:class:`int`).
    _target_sector_index = None
    #: The total number of sectors (:class:`int`).
    _number_sectors = None

    _MARKER_INTERFACE = IPlannedRackSampleTransfer

    def __init__(self, volume, hash_value, number_sectors, source_sector_index,
                 target_sector_index, **kw):
        PlannedLiquidTransfer.__init__(self, volume,
                                       hash_value=hash_value,
                                       transfer_type=
                                        TRANSFER_TYPES.RACK_SAMPLE_TRANSFER,
                                        **kw)
        self._number_sectors = number_sectors
        self._source_sector_index = source_sector_index
        self._target_sector_index = target_sector_index

    @property
    def number_sectors(self):
        """
        The total number of sectors (:class:`int`).
        """
        return self._number_sectors

    @property
    def source_sector_index(self):
        """
        The sector of the source plate the volume is taken from.
        """
        return self._source_sector_index

    @property
    def target_sector_index(self):
        """
        The sector of the target plate the volume is dispensed into.
        """
        return self._target_sector_index

    @classmethod
    def get_entity(cls, volume, number_sectors, source_sector_index,
                   target_sector_index):
        """
        Factory method returning the planned sample transfer for the given
        values. If there is already an entity with this values in the DB,
        the entity will be loaded, otherwise a new entity is generated.

        :param float volume: The volume *in l* (positive number).
        :param int number_sectors: The total number of sectors (:class:`int`).
        :param int source_sector_index: The sector of the source plate the
            volume is taken from.
        :param int target_sector_index: The sector of the target plate the
            volume is dispensed into.
        :returns: :class:`PlannedRackSampleTransfer` instance.
        """
        data = dict(number_sectors=number_sectors,
                    source_sector_index=source_sector_index,
                    target_sector_index=target_sector_index)
        data['volume'] = volume
        return cls.create_from_data(data)

    @classmethod
    def get_hash_value(cls, volume, number_sectors, source_sector_index, #pylint: disable=W0221
                       target_sector_index):
        """
        The hash value for rack sample transfers is comprised of the volume
        (in ul), sector number, source sector index and target sector index.

        :param volume: The volume. The unit will be regarded as litre, if the
            value is smaller 1, otherwise the unit will be assumed to be *ul*.
        :type volume: positive number

        :param number_sectors: The total number of sectors (:class:`int`).
        :type number_sectors: :class:`int`

        :param source_sector_index: The sector of the source plate the volume
            is taken from.
        :type source_sector_index: :class:`int`

        :param target_sector_index: The sector of the target plate the volume
            is dispensed into.
        :type target_sector_index: :class:`int`

        :return: The sample dilution hash value for the passed values.
        """
        volume_in_ul = cls._get_volume_str_in_ul(volume)
        values = [volume_in_ul, str(number_sectors), str(source_sector_index),
                  str(target_sector_index)]
        return cls._create_hash_value(values)

    def __repr__(self):
        str_format = '<%s id: %s, volume: %s, source sector: %s, ' \
                     'target sector: %s, number of sectors: %s>'
        params = (self.__class__.__name__, self.id, self._volume,
                  self._source_sector_index, self._target_sector_index,
                  self._number_sectors)
        return str_format % params


class PlannedWorklist(Entity):
    """
    A planned worklist represents an (abstract unordered) series of liquid
    transfer steps. It allows the generation of a robot worklist file.
    """
    #: A label for the worklist.
    label = None
    #: The particular steps forming this worklist (list of
    #: :class:`PlannedLiquidTransfer` entities (all of the same type)).
    planned_liquid_transfers = None
    #: The type of the planned liquid transfers in the worklist
    #: (element of :class:`TRANSFER_TYPES`).
    transfer_type = None
    #: The :class:`PipettingSpecs` assumed for this worklist.
    pipetting_specs = None

    #: The :class:`WorklistSeriesMember` entity linking this worklist to
    #: a particular worklist series.
    worklist_series_member = None
    #: A list of executed worklists (:class:`ExecutedWorklist`) for this
    #: planned worklist.
    executed_worklists = None

    def __init__(self, label, transfer_type, pipetting_specs,
                 planned_liquid_transfers=None, worklist_series_member=None,
                 executed_worklists=None, **kw):
        Entity.__init__(self, **kw)
        self.label = label
        self.transfer_type = transfer_type
        self.pipetting_specs = pipetting_specs
        if planned_liquid_transfers is None:
            planned_liquid_transfers = []
        self.planned_liquid_transfers = planned_liquid_transfers
        self.worklist_series_member = worklist_series_member
        if executed_worklists is None:
            executed_worklists = []
        self.executed_worklists = []

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

    def __iter__(self):
        return iter(self.planned_liquid_transfers)

    def __repr__(self):
        str_format = '<%s id: %s, label: %s, type: %s, pipetting specs: %s, ' \
                     'number of executions: %i>'
        params = (self.__class__.__name__, self.id, self.label,
                  self.transfer_type, self.pipetting_specs,
                  len(self.executed_worklists))
        return str_format % params


class WorklistSeries(Entity):
    """
    This class represents an ordered series of :class:`PlannedWorklist`
    objects.
    """

    #: The :class:`WorklistSeriesMember` entity linking this worklist series to
    #: the particular worklists belonging to it.
    worklist_series_members = None

    def __init__(self, **kw):
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
        # FIXME: Using instantiation for its side effect.
        WorklistSeriesMember(worklist, self, index)

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

    def get_sorted_worklists(self):
        """
        Returns the worklists of this series sorted by index.
        """
        worklist_map = dict()
        for wsm in self.worklist_series_members:
            worklist_map[wsm.index] = wsm.planned_worklist
        sorted_worklists = []
        for i in sorted(worklist_map.keys()):
            sorted_worklists.append(worklist_map[i])
        return sorted_worklists

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
        """
        Equality is based on the planned_worklists and worklist_series
        attributes.
        """
        return (isinstance(other, WorklistSeriesMember) and \
                self.planned_worklist == other.planned_worklist and \
                self.worklist_series == other.worklist_series)

    def __str__(self):
        return '%s:%s' % (self.worklist_series, self.planned_worklist)

    def __repr__(self):
        str_format = '<%s planned worklist: %s, index: %s, worklist ' \
                     'series: %s>'
        params = (self.__class__.__name__, self.planned_worklist,
                  self.index, self.worklist_series)
        return str_format % params



class ExecutedLiquidTransfer(Entity):
    """
    Abstract base class for executed liquid transfer.

    An executed liquid transfer represents a planned transfer that has
    actually been carried out. Thus, there are specific racks or containers
    involved.
    """
    #: The planned liquid transfer that has been executed
    #: (:class:`PlannedLiquidTransfer`).
    planned_liquid_transfer = None
    #: The user who has carried out the transfer
    #: (:class:thelma.entities.user.User`).
    user = None
    #: The time stamp is set upon entity creation. It represents the time
    #: the transfer has been executed on DB level.
    timestamp = None
    #: The type of the transfer (element of :class:`TRANSFER_TYPES`) depends
    #: on the type of the associated :attr:`planned_liquid_transfer`.
    transfer_type = None

    def __init__(self, planned_liquid_transfer, user, timestamp=None,
                 transfer_type=None, **kw): # pylint: disable=W0622
        if self.__class__ is ExecutedLiquidTransfer:
            raise NotImplementedError('Abstract class')
        Entity.__init__(self, **kw)
        if transfer_type is None:
            transfer_type = TRANSFER_TYPES.LIQUID_TRANSFER
        self.transfer_type = transfer_type
        if not planned_liquid_transfer.transfer_type == transfer_type:
            msg = 'Invalid planned liquid transfer type "%s" for executed ' \
                  'transfer class %s.' \
                    % (planned_liquid_transfer.transfer_type,
                       self.__class__.__name__)
            raise ValueError(msg)
        self.planned_liquid_transfer = planned_liquid_transfer
        self.user = user
        if timestamp is None:
            timestamp = get_utc_time()
        self.timestamp = timestamp

    def __str__(self):
        return self.id


class ExecutedSampleDilution(ExecutedLiquidTransfer):
    """
    Executed sample dilution.

    Sample dilution means that there is a target container but not source
    container. The source container is not specified since it exists only
    temporary. Instead the specs of the source rack are logged.
    """
    #: The container the volume has been dispensed into
    #: (:class:`thelma.entities.container.Container`).
    target_container = None
    #: The specs of the source reservoir (:class:`ReservoirSpecs`).
    reservoir_specs = None

    def __init__(self, target_container, reservoir_specs,
                 planned_sample_dilution, user, timestamp=None, **kw):
        ExecutedLiquidTransfer.__init__(self, planned_sample_dilution, user,
                                        timestamp=timestamp,
                                        transfer_type=
                                            TRANSFER_TYPES.SAMPLE_DILUTION,
                                        **kw)
        self.target_container = target_container
        self.reservoir_specs = reservoir_specs

    @property
    def planned_sample_dilution(self):
        """
        The planned sample dilution that has been executed
        (:class:`PlannedSampleDilution`).
        """
        return self.planned_liquid_transfer

    @property
    def target_rack(self):
        """
        The rack of the target container.
        """
        return self.target_container.rack

    def __repr__(self):
        str_format = '<%s id: %s, target container: %s, reservoir specs: %s, ' \
                     'user: %s>'
        params = (self.__class__.__name__, self.id, self.target_container,
                  self.reservoir_specs, self.user)
        return str_format % params


class ExecutedSampleTransfer(ExecutedLiquidTransfer):
    """
    Executed sample transfer.

    Sample transfer represent transfers from one source container to a target
    container. The container can be situated in different racks.
    """
    #: The container the volume has been taken from
    #: (:class:`thelma.entities.container.Container`).
    source_container = None
    #: The container the volume has been dispensed into
    #: (:class:`thelma.entities.container.Container`).
    target_container = None

    def __init__(self, source_container, target_container,
                 planned_sample_transfer, user, timestamp=None, **kw):
        ExecutedLiquidTransfer.__init__(self, planned_sample_transfer, user,
                                        timestamp=timestamp,
                                        transfer_type=
                                            TRANSFER_TYPES.SAMPLE_TRANSFER,
                                        **kw)
        self.source_container = source_container
        self.target_container = target_container

    @property
    def planned_sample_transfer(self):
        """
        The planned container transfer that has been executed
        (:class:`PlannedSampleransfer`).
        """
        return self.planned_liquid_transfer

    @property
    def target_rack(self):
        """
        The rack of the target container.
        """
        return self.target_container.rack

    @property
    def source_rack(self):
        """
        The rack of the source container.
        """
        return self.source_container.rack

    def __repr__(self):
        str_format = '<%s id: %s, source container: %s, target ' \
                     'container: %s, user: %s>'
        params = (self.__class__.__name__, self.id, self.source_container,
                  self.target_container, self.user)
        return str_format % params


class ExecutedRackSampleTransfer(ExecutedLiquidTransfer):
    """
    Executed rack transfer.

    In the rack transfer the contents of all containers of a rack (sector) is
    transferred to another rack (sector). The volumes must be the same for all
    containers.
    """
    #: The rack the volumes are taken from (:class:`thelma.entities.rack.Rack`).
    source_rack = None
    #: The rack the volumes are dispensed into
    #: (:class:`thelma.entities.rack.Rack`).
    target_rack = None

    def __init__(self, source_rack, target_rack, planned_rack_sample_transfer,
                 user, timestamp=None, **kw):
        ExecutedLiquidTransfer.__init__(self, planned_rack_sample_transfer,
                                        user, timestamp,
                                        transfer_type=
                                          TRANSFER_TYPES.RACK_SAMPLE_TRANSFER,
                                        **kw)
        self.source_rack = source_rack
        self.target_rack = target_rack

    @property
    def planned_rack_sample_transfer(self):
        """
        The planned rack sample transfer that has been executed
        (:class:`PlannedRackSampleTransfer`).
        """
        return self.planned_liquid_transfer

    def __repr__(self):
        str_format = '<%s id: %s, source rack: %s, target rack: %s, user: %s>'
        params = (self.__class__.__name__, self.id, self.source_rack,
                  self.target_rack, self.user)
        return str_format % params


class ExecutedWorklist(Entity):
    """
    Executed planned worklist.
    """
    #: The planned worklist that has been executed (:class:`PlannedWorklist`).
    planned_worklist = None
    #: The executed transfer steps belonging to this worklist
    #: (list of :class:`ExecutedLiquidTransfer` objects).
    executed_liquid_transfers = None

    def __init__(self, planned_worklist, executed_liquid_transfers=None, **kw):
        Entity.__init__(self, **kw)
        self.planned_worklist = planned_worklist
        if executed_liquid_transfers is None:
            executed_liquid_transfers = []
        self.executed_liquid_transfers = executed_liquid_transfers

    @property
    def worklist_series(self):
        """
        The worklist series the planned worklist belongs to.
        """
        return self.planned_worklist.worklist_series

    def __iter__(self):
        return iter(self.executed_liquid_transfers)

    def __repr__(self):
        str_format = '<%s id: %s, planned worklist: %s>'
        params = (self.__class__.__name__, self.id, self.planned_worklist.label)
        return str_format % params


class PipettingSpecs(Entity):
    """
    Contains the properties for a pipetting method or robot.
    """
    #: The name of the robot or method.
    _name = None
    #: The minimum volume that can be pipetted with this method in l.
    _min_transfer_volume = None
    #: The maximum volume that can be pipetted with this method in l.
    _max_transfer_volume = None
    #: The maximum dilution that can achieved with a one-step transfer.
    _max_dilution_factor = None
    #: For some robots the dead volume depends on the number of transfers
    #: taken from a source well. The minimum and maximum dead volume depend
    #: on the :class:`ReservoirSpecs`.
    _has_dynamic_dead_volume = None
    #: Some robots have limitation regarding the possible target positions for
    #: a source position.
    _is_sector_bound = None

    def __init__(self, name, min_transfer_volume, max_transfer_volume,
                 max_dilution_factor, has_dynamic_dead_volume, is_sector_bound,
                 **kw):
        Entity.__init__(self, **kw)
        self._name = name
        self._min_transfer_volume = min_transfer_volume
        self._max_transfer_volume = max_transfer_volume
        self._max_dilution_factor = max_dilution_factor
        self._has_dynamic_dead_volume = has_dynamic_dead_volume
        self._is_sector_bound = is_sector_bound

    @property
    def slug(self):
        """
        The slug of a planned transfer is its :attr:`name`.
        """
        return slug_from_string(self._name)

    @property
    def name(self):
        """
        The name of the robot or method.
        """
        return self._name

    @property
    def min_transfer_volume(self):
        """
        The minimum volume that can be pipetted with this method in l.
        """
        return self._min_transfer_volume

    @property
    def max_transfer_volume(self):
        """
        The maximum volume that can be pipetted with this method in l.
        """
        return self._max_transfer_volume

    @property
    def max_dilution_factor(self):
        """
        The maximum dilution that can achieved with a one-step transfer.
        """
        return self._max_dilution_factor

    @property
    def has_dynamic_dead_volume(self):
        """
        For some robots the dead volume depends on the number of transfers
        taken from a source well. The minimum and maximum dead volume depend
        on the :class:`ReservoirSpecs`.
        """
        return self._has_dynamic_dead_volume

    @property
    def is_sector_bound(self):
        """
        Some robots have limitation regarding the possible target positions for
        a source position.
        """
        return self._is_sector_bound

    def __eq__(self, other):
        return isinstance(other, PipettingSpecs) and \
                    other.name == self._name

    def __str__(self):
        return self._name

    def __repr__(self):
        str_format = '<%s name: %s>'
        params = (self.__class__.__name__, self._name)
        return str_format % params


class ReservoirSpecs(Entity):
    """
    Specs for a reservoir.

    A reservoir represents an anonymous source rack. Reservoirs
    exist only temporary (in the physical world) and are not stored in the DB.
    They constitute the source for container dilutions where the origin of a
    volume is not specified.
    """
    #: This attribute is used as slug.
    _name = None
    #: Contains a little more information than the :attr:`name`.
    _description = None
    #: The rack shape of the reservoir
    #: (:class:`thelma.entities.Rack.RackShape`).
    _rack_shape = None
    #: The maximum volume of a rack container *in liters*.
    _max_volume = None
    #: The minimum dead volume of a rack container *in liters*.
    _min_dead_volume = None
    #: The maximum dead volume of a rack container *in liters*.
    _max_dead_volume = None

    def __init__(self, name, description, rack_shape, max_volume,
                 min_dead_volume, max_dead_volume, **kw):
        Entity.__init__(self, **kw)
        self._name = name
        self._description = description
        self._rack_shape = rack_shape
        self._max_volume = max_volume
        self._min_dead_volume = min_dead_volume
        self._max_dead_volume = max_dead_volume

    @property
    def slug(self):
        """
        The slug of a reservoir spec is its :class:`name`.
        """
        return slug_from_string(self._name)

    @property
    def name(self):
        """
        This attribute is used as slug.
        """
        return self._name

    @property
    def description(self):
        """
        Contains a little more information than the :attr:`name`.
        """
        return self._description

    @property
    def rack_shape(self):
        """
        The rack shape of the reservoir
        (:class:`thelma.entities.Rack.RackShape`).
        """
        return self._rack_shape

    @property
    def max_volume(self):
        """
        The maximum volume of a rack container in liters.
        """
        return self._max_volume

    @property
    def min_dead_volume(self):
        """
        The minimum dead volume of a rack container.
        """
        return self._min_dead_volume

    @property
    def max_dead_volume(self):
        """
        The maximum dead volume of a rack container *in liters*.
        """
        return self._max_dead_volume

    def __eq__(self, other):
        """
        Equality depends on the rack_hspae, max_volume, min_dead_volume, and
        max_dead_volume attributes.
        """
        return isinstance(other, ReservoirSpecs) and \
                self._rack_shape == other.rack_shape and \
                self._max_volume == other.max_volume and \
                self._min_dead_volume == other.min_dead_volume and \
                self._max_dead_volume == other.max_dead_volume

    def __str__(self):
        return self._name

    def __repr__(self):
        str_format = '<%s id: %s, name: %s, rack shape: %s, maximum ' \
                     'volume: %s, min dead volume: %s, max dead volume: %s>'
        params = (self.__class__.__name__, self.id, self._name,
                  self._rack_shape, self._max_volume, self._min_dead_volume,
                  self._max_dead_volume)
        return str_format % params
