"""
Base classes and constants involved in lab ISO processing tasks.

AAB
"""
from thelma.automation.tools.utils.base import MOCK_POSITION_TYPE
from thelma.automation.tools.utils.base import TransferLayout
from thelma.automation.tools.utils.base import TransferParameters
from thelma.automation.tools.utils.base import TransferPosition
from thelma.automation.tools.utils.base import get_converted_number
from thelma.automation.tools.utils.base import get_trimmed_string
from thelma.automation.tools.utils.base import is_valid_number
from thelma.automation.tools.utils.converters import TransferLayoutConverter
from thelma.automation.tools.utils.iso import IsoRequestPosition
from thelma.automation.tools.utils.racksector import AssociationData
from thelma.automation.tools.utils.racksector import RackSectorAssociator
from thelma.automation.tools.utils.racksector import ValueDeterminer
from thelma.models.organization import Organization
from thelma.automation.tools.utils.base import add_list_map_element

__all__ = ['get_stock_takeout_volume',
           'IsoPlateParameters',
           'IsoPlatePosition',
           'IsoPlateLayout',
           'IsoPlateLayoutConverter',
           'IsoPlateValueDeterminer',
           'IsoPlateSectorAssociator',
           'IsoPlateAssociationData',
           'IsoPrepPlateParameters',
           'IsoPrepPlatePosition',
           'IsoPrepPlateLayout',
           'IsoPrepPlateLayoutConverter']


def get_stock_takeout_volume(stock_concentration, final_volume, concentration):
    """
    Returns the volume that needs to be taken out of the stock in
    order to set up the desired concentration (round to 1 decimal
    place).

    :param stock_concentration: The stock concentration for the given
        molecule type *in nM*.
    :type stock_concentration: :class:`int`
    :rtype: :class:`float`

    :param final_volume: The volume determined for a plate position *in ul*.
    :type final_volume: positive number

    :param concentration: The concentration for the target position *in nM*.
    :type concentration: positive number

    :return: The volume to be taken from the stock in ul.
    """
    dil_factor = stock_concentration / float(concentration)
    take_out_volume = final_volume / dil_factor
    take_out_volume = round(take_out_volume, 1)
    return take_out_volume


#: The diluent info for the planned container dilutions (always buffer).
DILUENT_INFO = 'annealing buffer'


class LABELS(object):
    """
    Generates and parses worklist and plate labels involved in lab ISO
    processing.
    """
    #: The character used in the labels to separate the value parts.
    __SEPARATING_CHAR = '_'
    #: This character is used seperate running numbers from value parts.
    NUMBERING_CHAR = '#'


    #: Marker for ticket number in keyword dictionaries.
    MARKER_TICKET_NUMBER = 'ticket_number'
    #: Marker for things related in aliquot processing.
    ROLE_ALIQUOT = 'a'
    #: Marker for things related in preparation processing.
    ROLE_PREPARATION_ISO = 'p'
    #: Marker for things related to job processing (occurs if there are
    #: flaotings positions in a layout).
    ROLE_PREPARATION_JOB = 'jp'

    #: Marker for worklist counts (to facilitate worklist ordering and
    #: distinguish intraplate transfer worklists).
    MARKER_WORKLIST_NUM = 'worklist_number'
    #: Marker for worklist source racks in keyword dictionaries.
    MARKER_WORKLIST_SOURCE = 'source_rack_marker'
    #: Marker for worklist target racks in keyword dictionaries.
    MARKER_WORKLIST_TARGET = 'target_rack_marker'

    #: Marker for plates. The role can be :attr:`ROLE_ALIQUOT`,
    #: :attr:`ROLE_PREPARATION`, or :att:`ROLE_JOB_PREPARATION`.
    MARKER_PLATE_ROLE = 'plate_role'
    #: Used to distinguish plates having the same role.
    MARKER_PLATE_NUM = 'plate_num'
    #: Marker for plate marker (see :func:`create_plate_marker`).
    MARKER_PLATE_MARKER = 'plate_marker'
    #: Marker for ISO or ISO job number.
    MARKER_ENTITY_NUM = 'entity_num'
    #: Marker for ISO or ISO job labels.
    MARKER_ENTITY_LABEL = 'entity_label'

    #: For transfer worklists. Located between source and target rack.
    __FILL_WORKLIST_TRANSFER = 'to'
    #: For dilution worklists. Located after the target rack. In lab ISOs
    #: the diluent is always buffer.
    __FILL_WORKLIST_DILUTION = 'buffer'
    #: For ISOs. Located between ticket and ISO number.
    __FILL_ISO = 'iso'
    #: Is attached to ISOs that are copies of other ISOs.
    __ISO_COPY_MARKER = 'copy'
    #: For ISOs. Located between ticket and job number.
    __FILL_ISO_JOB = 'job'

    @classmethod
    def create_iso_label(cls, ticket_number, iso_number, create_copy=False):
        """
        Creates a label for a future ISO. The label contains the ticket
        number and the ISO number (you can get a new ISO number with
        :func:`get_new_iso_number`).

        :param create_copy: Is the future ISO a copy of an existing ISO
            (if so, a marker will be added to the label).
        :type create_copy: :class:`bool`
        :default create_copy: *True*`
        """
        iso_num_str = '%02i' % (iso_number)
        ticket_str = cls.__get_int_str(ticket_number)
        value_parts = [ticket_str, cls.__FILL_ISO, iso_num_str]
        if create_copy: value_parts += [cls.__ISO_COPY_MARKER]
        return cls.__create_label(value_parts)

    @classmethod
    def parse_iso_label(cls, label):
        """
        Parses an ISO label and returns the value parts as map. The values
        are ticket number and ISO number. Potential copy markers are ignored.
        """
        value_parts = cls.__get_value_parts(label)
        ticket_num = cls.__parse_int_str(value_parts[0])
        iso_num = cls.__parse_int_str(value_parts[2])
        return {cls.MARKER_TICKET_NUMBER : ticket_num,
                cls.MARKER_ENTITY_NUM : iso_num}

    @classmethod
    def get_new_iso_number(cls, iso_request):
        """
        Returns the number for a new ISO. The number is one larger than the
        largest ISO existing for this ISO request.
        """
        highest_number = 0
        for iso in iso_request.isos:
            number = cls.__get_iso_number(iso)
            highest_number = max(highest_number, number)

        return highest_number + 1

    @classmethod
    def __get_iso_number(cls, iso):
        value_parts = cls.__get_value_parts(iso.label)
        return cls.__parse_int_str(value_parts[2])

    @classmethod
    def create_job_label(cls, ticket_number, job_number):
        """
        The job label contains the ticket ID and a running number as job number
        (you can get a new ISO number with :func:`get_new_job_number`).
        """
        ticket_str = cls.__get_int_str(ticket_number)
        job_str = cls.__get_int_str(job_number)
        value_parts = [ticket_str, cls.__FILL_ISO_JOB, job_str]
        return cls.__create_label(value_parts)

    @classmethod
    def get_new_job_number(cls, iso_request):
        """
        Returns the number for a new ISO job. The number is one larger than the
        largest ISO Job number existing for this ISO request.
        """
        highest_number = 0
        for iso_job in iso_request.iso_jobs:
            number = cls.__get_job_number(iso_job)
            highest_number = max(highest_number, number)

        return highest_number + 1

    @classmethod
    def __get_job_number(cls, iso_job):
        value_parts = cls.__get_value_parts(iso_job.label)
        return cls.__parse_int_str(value_parts[2])

    @classmethod
    def create_plate_marker(cls, plate_role, plate_number=None):
        """
        A plate marker contains a role and (optionally) a plate number.
        """
        value_parts = [plate_role]
        if plate_number is not None:
            plate_num = cls.__get_int_str(plate_number)
            value_parts += [plate_num]
            return cls.__create_label(value_parts, for_numbering=True)
        else:
            return plate_role

    @classmethod
    def parse_plate_marker(cls, plate_marker):
        """
        A plate marker contains a role and (optionally) a plate number.
        """
        value_parts = cls.__get_value_parts(plate_marker, for_numbering=True)
        values = {cls.MARKER_PLATE_ROLE : value_parts[0]}
        if len(value_parts) > 1:
            plate_num = cls.__parse_int_str(value_parts[1])
            values[cls.MARKER_PLATE_NUM] = plate_num
        return values

    @classmethod
    def create_plate_label(cls, plate_marker, entity_label):
        """
        The plate label contains the ISO or ISO job label and a plate marker.
        """
        value_parts = [entity_label, plate_marker]
        return cls.__create_label(value_parts)

    @classmethod
    def parse_plate_label(cls, plate_label):
        """
        The plate label contains the ticket ID and ISO or ISO job number,
        and a plate marker (plate role and (optionally) plate number).
        """
        value_parts = cls.__get_value_parts(plate_label)
        ticket_number = cls.__parse_int_str(value_parts[0])
        entity_num = cls.__parse_int_str(value_parts[2])
        plate_marker = value_parts[3]
        values = cls.parse_plate_marker(plate_marker)
        values[cls.MARKER_TICKET_NUMBER] = ticket_number
        values[cls.MARKER_ENTITY_NUM] = entity_num
        return values


    @classmethod
    def create_worklist_label(cls, ticket_number, worklist_number,
                              target_plate_marker, source_plate_marker=None):
        """
        Creates a label for a series worklist. The worklist label always
        contains the ticket number and a worklist number. Transfer worklists
        then continue with the source plate marker, a filler and the target
        plate marker (source and target marker can be equal) whereas dilution
        worklists contain the target plate marker and a (different) filler.
        """
        ticket_str = cls.__get_int_str(ticket_number)
        num_str = cls.__get_int_str(worklist_number)
        value_parts = [ticket_str, num_str]
        if source_plate_marker is None:
            value_parts += [target_plate_marker, cls.__FILL_WORKLIST_DILUTION]
        else:
            value_parts += [source_plate_marker, cls.__FILL_WORKLIST_TRANSFER,
                           target_plate_marker]
        return cls.__create_label(value_parts)

    @classmethod
    def parse_worklist_label(cls, worklist_label):
        """
        Series worklist labels always contain the ticket number and a worklist
        number. Transfer worklists then continue with the source plate marker,
        a filler and the target plate marker (source and target marker can be
        equal) whereas dilution worklists contain the target plate marker
        and a (different) filler.
        """
        value_parts = cls.__get_value_parts(worklist_label)
        ticket_number = cls.__parse_int_str(value_parts[0])
        worklist_num = cls.__parse_int_str(value_parts[1])
        values = {cls.MARKER_TICKET_NUMBER : ticket_number,
                  cls.MARKER_WORKLIST_NUM : worklist_num}
        if len(value_parts) == 4: # dilution
            values[cls.MARKER_WORKLIST_TARGET] = value_parts[2]
        else: # transfer
            values[cls.MARKER_WORKLIST_SOURCE] = value_parts[2]
            values[cls.MARKER_WORKLIST_TARGET] = value_parts[4]
        return values

    @classmethod
    def __create_label(cls, value_parts, for_numbering=False):
        """
        Reverse of :func:`__get_value_parts`.
        """
        sep = cls.__SEPARATING_CHAR
        if for_numbering: sep = cls.NUMBERING_CHAR
        return sep.join(value_parts)

    @classmethod
    def __get_value_parts(cls, label, for_numbering=False):
        """
        Reverse of :func:`__create_label`.
        """
        sep = cls.__SEPARATING_CHAR
        if for_numbering: sep = cls.NUMBERING_CHAR
        return label.split(sep)

    @classmethod
    def __get_int_str(cls, value):
        """
        Reverse of :func:`__parse_int_str`.
        """
        return '%i' % (value)

    @classmethod
    def __parse_int_str(cls, value_str):
        """
        Reverse of :func:`__get_int_str`.
        """
        return int(value_str)


class IsoPlateParameters(TransferParameters):
    """
    These parameters are involved in the preparation of lab ISOs.
    """

    DOMAIN = 'iso_plate'
    ALLOWS_UNTREATED_POSITIONS = False

    #: The target concentration in the plate *in nM*.
    CONCENTRATION = 'concentration'
    #: The target volume in the plate in *in nM*.
    VOLUME = 'volume'

    #: The barcode of the preferred stock tube (as determined by the
    #: optimisation query - only for well parent wells).
    STOCK_TUBE_BARCODE = 'stock_tube_barcode'
    #: The barcode of the preferred stock rack (as determined by the
    #: optimisation query - only for well parent wells).
    STOCK_RACK_BARCODE = 'stock_rack_barcode'

    #: The transfer target *within the same plate*.
    TRANSFER_TARGETS = TransferParameters.TRANSFER_TARGETS

    REQUIRED = TransferParameters + [CONCENTRATION, VOLUME]
    ALL = REQUIRED + [STOCK_TUBE_BARCODE, STOCK_RACK_BARCODE, TRANSFER_TARGETS]

    ALIAS_MAP = TransferParameters.ALIAS_MAP + {
                 CONCENTRATION : ['preparation_concentration'],
                 VOLUME : ['required_volume'],
                 STOCK_TUBE_BARCODE : [],
                 STOCK_RACK_BARCODE : []}

    DOMAIN_MAP = TransferParameters.DOMAIN_MAP + {
                 CONCENTRATION : DOMAIN,
                 VOLUME : DOMAIN,
                 STOCK_TUBE_BARCODE : DOMAIN,
                 STOCK_RACK_BARCODE : DOMAIN}


class IsoPlatePosition(TransferPosition):
    """
    Represents a position in a plate involved in lab ISO processing.
    """
    PARAMETER_SET = IsoPlateParameters

    #: Used in the ISO planning phase to mark a staring position for which
    #: there is no tube barcode yet.
    TEMP_TUBE_BARCODE = 'to be defined'

    def __init__(self, rack_position, molecule_design_pool, position_type,
                 concentration, volume, transfer_targets=None,
                 stock_tube_barcode=None, stock_rack_barcode=None):
        """
        Constructor:

        :param rack_position: The position within the rack.
        :type rack_position: :class:`thelma.models.rack.RackPosition`

        :param molecule_design_pool: The molecule design pool for this position.
        :type molecule_design_pool:  placeholder or
            :class:`thelma.models.moleculedesign.MoleculeDesignPool`

        :param position_type: The position type (fixed, floating or mock).
        :type position_type: :class:`str`

        :param concentration: The target concentration in the plate after
            all additions and dilutions.
        :type concentration: positive number, unit nM

        :param volume: The maximum volume in the plate (after all dilutions
            but before usage as source well).
        :type volume: positive number, unit ul

        :param transfer_targets: The transfer targets *within the same plate*.
        type transfer_targets: List of transfer target objects.

        :param stock_tube_barcode: The barcode of the stock tube of the prime
            hit of the optimisation query.
        :type stock_tube_barcode: :class:`str`

        :param stock_rack_barcode: The barcode of the stock rack of the prime
            hit of the optimisation query.
        :type stock_rack_barcode: :class:`str`
        """
        TransferPosition.__init__(self, rack_position=rack_position,
                                  molecule_design_pool=molecule_design_pool,
                                  transfer_targets=transfer_targets)

        if (position_type == MOCK_POSITION_TYPE and \
                            not molecule_design_pool == MOCK_POSITION_TYPE) or \
                            (molecule_design_pool == MOCK_POSITION_TYPE and \
                             not position_type == MOCK_POSITION_TYPE):
            msg = 'For mock positions both molecule design pool ID and ' \
                  'position type must be "%s".' % (MOCK_POSITION_TYPE)
            raise ValueError(msg)

        if not molecule_design_pool == MOCK_POSITION_TYPE and \
                                            not is_valid_number(concentration):
            msg = 'The concentration must be a positive number (obtained: ' \
                  '%s).' % (concentration)
            raise ValueError(msg)
        if not is_valid_number(volume):
            msg = 'The volume must a positive number (obtained: %s)' % (volume)
            raise ValueError(msg)

        if not stock_tube_barcode is None and \
                                not isinstance(stock_tube_barcode, basestring):
            msg = 'The stock tube barcode must be a string (obtained: %s).' \
                   % (stock_tube_barcode.__class__.__name__)
            raise TypeError(msg)
        if not stock_rack_barcode is None and \
                                not isinstance(stock_rack_barcode, basestring):
            msg = 'The stock rack barcode must be a string (obtained: %s).' \
                   % (stock_rack_barcode.__class__.__name__)
            raise TypeError(msg)

        if not stock_tube_barcode is None:
            stock_tube_barcode = str(stock_tube_barcode)
        #: The barcode of the stock tube of the prime hit of the optimization
        #: query.
        self.stock_tube_barcode = stock_tube_barcode

        if not stock_rack_barcode is None:
            stock_rack_barcode = str(stock_rack_barcode)
        #: The barcode of the stock tube of the prime hit of the optimization
        #: query.
        self.stock_rack_barcode = stock_rack_barcode

        #: The target concentration in the plate after all additions and
        #: dilutions.
        self.concentration = get_converted_number(concentration)

        #: The maximum volume in the plate (after all dilutions but before
        #: usage as source well).
        self.volume = float(volume)

        #: The supplier for molecule (fixed positions only - not stored in
        #: the DB).
        self._supplier = None

        if self.is_mock:
            self.prep_concentration = None
            self.stock_rack_barcode = None
            self.stock_tube_barcode = None
            self.parent_well = None

    @classmethod
    def create_mock_position(cls, rack_position, volume):
        """
        Returns a preparation position with mock molecule design pool.

        :param rack_position: The position within the rack.
        :type rack_position: :class:`thelma.models.rack.RackPosition`

        :param volume: The maximum volume in the plate (after all dilutions
            but before usage as source well).
        :type volume: positive number, unit ul
        """
        return cls(rack_position=rack_position,
                   molecule_design_pool=MOCK_POSITION_TYPE,
                   position_type=MOCK_POSITION_TYPE, volume=volume)

    @property
    def is_inactivated(self):
        """
        A position is set to inactivated if the tube picker has not been
        capable to find a valid stock tube.
        """
        if self.stock_tube_barcode is None and not self.is_mock:
            return True
        else:
            return False

    def inactivate(self):
        """
        Inactivates the position (setting stock rack barcode to *None*).
        A position is set to inactivated if there is no suitable stock tube
        found. Only floating positions can be inactivated.

        :raises AttributeError: If the position is not a floating position.
        """
        if self.is_floating:
            self.stock_rack_barcode = None
        else:
            raise AttributeError('%s positions must not be inactivated!' \
                                 % (self.position_type))

    @property
    def is_starting_well(self):
        """
        Starting wells are wells that get their pool directly from stock tubes
        (instead as from other wells). Thus, a starting position must have
        a stock tube barcode set.
        """
        if self.is_mock: return False
        return (self.stock_tube_barcode is not None)

    def get_stock_takeout_volume(self):
        """
        Returns the volume that needs to be taken out of the stock in
        order to set up the desired concentration (round to 1 decimal
        place).
        Return *None* for non-starting wells (= wells without
        :attr:`stock_tube_barcode`) and *0* for mock positions.

        :raise ValueError: if the stock concentration is *None*

        :rtype: :class:`float`
        """
        if not self.is_starting_well: return None
        if self.stock_concentration is None:
            raise ValueError('The stock concentration must not be None!')
        take_out_volume = get_stock_takeout_volume(self.stock_concentration,
                                            self.volume, self.concentration)
        return take_out_volume

    def create_completed_copy(self, tube_candidate):
        """
        Returns a copy of this IsoPlatePosition that has a specific molecule
        design pool (in case of floating positions) and, if this position is
        a starting well also defined stock tube barcode and stock rack barcode.
        A well is regarded as starting well if its current
        :attr:`stock_tube_barcode` is equal to the :attr:`TEMP_TUBE_BARCODE`.

        :param tube_candidate: The tube candidate used to complete the position
            data.
        :type tube_candidate: :class:`TubeCandidate`

        :raises ValueError: If there is already a pool for a floating
            position, if (in case of fixed positions) if the pool of tube
            candidate and position do not match or if there is already a
            non-placeholde stock tube barcode set.
        :return: The IsoPlatePosition or *None* if any value is invalid.
        """
        if self.is_floating:
            if not isinstance(self.molecule_design_pool, basestring):
                msg = 'The pool for this floating position is already set ' \
                      '(%s!)' % (self.molecule_design_pool)
                raise ValueError(msg)
            pool = tube_candidate.pool
        elif self.is_fixed:
            pool = self.molecule_design_pool
            if not tube_candidate.pool == pool:
                msg = 'The pools of the position (%s) and the tube candidate ' \
                      '(%s) do not match!' % (pool, tube_candidate.pool)
                raise ValueError(msg)

        if self.stock_tube_barcode == self.TEMP_TUBE_BARCODE:
            stock_tube_barcode = tube_candidate.tube_barcode
            stock_rack_barcode = tube_candidate.rack_barcode
        elif self.stock_tube_barcode is not None:
            msg = 'There is already a stock tube barcode set for this ' \
                  'position (%s)!' % (self.stock_tube_barcode)
            raise ValueError(msg)
        else:
            stock_tube_barcode, stock_rack_barcode = None, None

        plate_pos = self.__class__(rack_position=self.rack_position,
                         molecule_design_pool=pool,
                         position_type=self.position_type,
                         stock_tube_barcode=stock_tube_barcode,
                         stock_rack_barcode=stock_rack_barcode,
                         concentration=self.concentration,
                         volume=self.volume,
                         transfer_targets=self.transfer_targets)
        return plate_pos

    def set_supplier(self, supplier):
        """
        Sets the supplier for the molecule (fixed positions only, not stored in
        the DB).

        :param supplier: The supplier for the molecule.
        :type supplier: :class:`thelma.models.organization.Organization`

        :raises ValueError: If the position is a mock or a floating type.
        :raises TypeError: If the supplier is not an Organisation.
        """
        if self.is_mock or self.is_floating:
            msg = 'Suppliers for mock and floating positions are not supported!'
            raise ValueError(msg)

        if not isinstance(supplier, Organization):
            msg = 'The supplier must be an Organization object ' \
                  '(obtained: %s).' % (supplier.__class__.__name__)
            raise TypeError(msg)

        self._supplier = supplier

    def get_supplier(self):
        """
        Returns the supplier.
        """
        return self._supplier

    def _get_parameter_values_map(self):
        parameters = TransferPosition._get_parameter_values_map(self)
        parameters[self.PARAMETER_SET.CONCENTRATION] = self.concentration
        parameters[self.PARAMETER_SET.VOLUME] = self.volume
        parameters[self.PARAMETER_SET.STOCK_TUBE_BARCODE] = \
                                                        self.stock_tube_barcode
        parameters[self.PARAMETER_SET.STOCK_RACK_BARCODE] = \
                                                        self.stock_rack_barcode

    def __eq__(self, other):
        return isinstance(other, self.__class__) \
                and self.rack_position == other.rack_position \
                and self.molecule_design_pool == other.molecule_design_pool \
                and self.concentration == other.concentration

    def __repr__(self):
        str_format = '<%s %s, pool: %s, concentration: %s, volume: %s, ' \
                     'type: %s, stock tube: %s>'
        params = (self.__class__.__name__, self.rack_position,
                  self.molecule_design_pool,
                  get_trimmed_string(self.concentration),
                  get_trimmed_string(self.volume),
                  self.position_type, self.stock_tube_barcode)
        return str_format % params


class IsoPlateLayout(TransferLayout):
    """
    Represents a plate in a lab ISO preparation process.
    """
    WORKING_POSITION_CLS = IsoPlatePosition

    def get_sorted_floating_positions(self):
        """
        Returns the floating positions sorted by pool ID.
        """
        floating_map = dict()
        for plate_pos in self.get_sorted_working_positions():
            if not plate_pos.is_floating: continue
            add_list_map_element(floating_map, plate_pos.molecule_design_pool,
                                 plate_pos)

        floating_positions = []
        for pool in sorted(floating_map.keys()):
            positions = floating_map[pool]
            floating_positions.extend(positions)

        return floating_positions

    def get_starting_wells(self):
        """
        Starting wells are wells that get their pool directly from stock tubes
        (instead as from other wells). Thus, a starting position must have
        a stock tube barcode set.

        The starting wells are mapped onto their rack positions.
        """
        starting_wells = dict()
        for rack_pos, plate_pos in self._position_map.iteritems():
            if plate_pos.is_starting_well:
                starting_wells[rack_pos] = plate_pos

        return starting_wells

    def get_supplier_map(self):
        """
        Returns a dictionary mapping supplier IDs onto the molecule design pool
        IDs they are meant for (no mocks and no floatings).
        """
        supplier_map = dict()

        for plate_pos in self._position_map.values():
            if plate_pos.is_mock or plate_pos.is_floating: continue
            pool_id = plate_pos.molecule_design_pool_id
            if supplier_map.has_key(pool_id): continue
            supplier = plate_pos.get_supplier()
            if supplier is None:
                supplier_id = IsoRequestPosition.ANY_SUPPLIER_INDICATOR
            else:
                supplier_id = supplier.id
            supplier_map[pool_id] = supplier_id

        return supplier_map


class IsoPlateLayoutConverter(TransferLayoutConverter):
    """
    Converts a :class:`RackLayout` into a :class:`IsoPlateLayout`.
    """
    NAME = 'ISO Plate Layout Converter'

    PARAMETER_SET = IsoPlateParameters
    WORKING_LAYOUT_CLS = IsoPlateLayout
    WORKING_POSITION_CLS = IsoPlatePosition

    def __init__(self, rack_layout, log):
        """
        Constructor:

        :param rack_layout: The rack layout containing the plate data.
        :type rack_layout: :class:`thelma.models.racklayout.RackLayout`

        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`
        """
        TransferLayoutConverter.__init__(self, rack_layout=rack_layout, log=log)

        # intermediate storage of invalid rack positions
        self.__missing_pool = None
        self.__invalid_pool = None
        self.__missing_type = None
        self.__missing_conc = None
        self.__invalid_conc = None
        self.__missing_vol = None
        self.__invalid_vol = None
        self.__inconsistent_type = None

    def reset(self):
        """
        Resets all attributes except for the :attr:`rack_layout`.
        """
        TransferLayoutConverter.reset(self)
        self.__missing_pool = []
        self.__invalid_pool = []
        self.__missing_type = []
        self.__missing_conc = []
        self.__invalid_conc = []
        self.__missing_vol = []
        self.__invalid_vol = []
        self.__inconsistent_type = []

    def _get_position_init_values(self, parameter_map):
        rack_position = parameter_map[self._RACK_POSITION_KEY]
        pool_id = parameter_map[self.PARAMETER_SET.MOLECULE_DESIGN_POOL]
        pos_type = parameter_map[self.PARAMETER_SET.POS_TYPE]
        tube_barcode = parameter_map[self.PARAMETER_SET.STOCK_TUBE_BARCODE]
        rack_barcode = parameter_map[self.PARAMETER_SET.STOCK_RACK_BARCODE]
        concentration = parameter_map[self.PARAMETER_SET.CONCENTRATION]
        volume = parameter_map[self.PARAMETER_SET.VOLUME]
        transfer_targets = parameter_map[self.PARAMETER_SET.TRANSFER_TARGETS]

        is_valid = True
        if pool_id is None and pos_type is None:
            return None
        elif not self._are_valid_transfer_targets(transfer_targets,
                                                  rack_position):
            is_valid = False

        rack_pos_label = rack_position.label

        if pool_id is None:
            self.__missing_pool.append(rack_pos_label)
            is_valid = False
        if pos_type is None:
            self.__missing_type.append(rack_pos_label)
            is_valid = False
        else:
            mock_value = MOCK_POSITION_TYPE
            if (pos_type == mock_value and not pool_id == mock_value) or \
                        (not pos_type == mock_value and pool_id == mock_value):
                self.__inconsistent_type.append(rack_pos_label)
                is_valid = False

        if pool_id == MOCK_POSITION_TYPE:
            pool = pool_id
        else:
            pool = self._get_molecule_design_pool_for_id(pool_id,
                                                         rack_pos_label)
            if pool is None:
                is_valid = False
            elif concentration is None:
                self.__missing_conc.append(rack_pos_label)
                is_valid = False
        if not concentration is None and not is_valid_number(concentration):
            info = '%s (%s)' % (rack_pos_label, concentration)
            self.__invalid_conc.append(info)
            is_valid = False

        if volume is None:
            self.__missing_vol.append(rack_pos_label)
            is_valid = False
        if not is_valid_number(volume):
            info = '%s (%s)' % (rack_pos_label, volume)
            self.__invalid_vol.append(info)
            is_valid = False

        if not is_valid:
            return None
        else:
            kw = dict(rack_position=rack_position,
                      molecule_design_pool=pool,
                      position_type=pos_type,
                      concentration=concentration,
                      volume=volume,
                      transfer_targets=transfer_targets,
                      stock_tube_barcode=tube_barcode,
                      stock_rack_barcode=rack_barcode)
            return kw

    def _record_additional_position_errors(self):
        """
        Records errors that have been collected for rack positions.
        """
        TransferLayoutConverter._record_additional_position_errors(self)

        if len(self.__missing_pool) > 0:
            msg = 'The molecule design pool IDs for the following rack ' \
                  'positions are missing: %s.' \
                   % (', '.join(self.__missing_pool))
            self.add_error(msg)

        if len(self.__missing_type) > 0:
            msg = 'The position type for the following positions are ' \
                  'missing: %s.' % (', '.join(self.__missing_type))
            self.add_error(msg)

        if len(self.__missing_conc) > 0:
            msg = 'The following rack positions do not have a concentration: ' \
                  '%s.' % (', '.join(self.__missing_conc))
            self.add_error(msg)
        if len(self.__invalid_conc) > 0:
            msg = 'The concentration must be a positive number. The ' \
                  'following rack positions have invalid concentrations: %s.' \
                   % (', '.join(self.__invalid_conc))
            self.add_error(msg)

        if len(self.__missing_vol) > 0:
            msg = 'The following rack positions do not have a volume: %s.' \
                  % (', '.join(self.__missing_vol))
            self.add_error(msg)
        if len(self.__invalid_vol) > 0:
            msg = 'The volume must be a positive number. The following rack ' \
                  'positions have invalid volume: %s.' % \
                  (', '.join(self.__invalid_vol))
            self.add_error(msg)

        if len(self.__inconsistent_type) > 0:
            msg = 'The mock positions both molecule design pool ID and ' \
                  'position type must be "%s". The types for the following ' \
                  'positions are inconsistent: %s.' \
                   % (MOCK_POSITION_TYPE, ', '.join(self.__inconsistent_type))
            self.add_error(msg)


class IsoPlateValueDeterminer(ValueDeterminer):
    """
    This is a special rack sector determiner. It sorts ISO plate positions
    by concentration.

    **Return Value:** A map containing the values for the different sectors.
    """

    NAME = 'Preparation Rack Sector Value Determiner'

    WORKING_LAYOUT_CLS = IsoPlateLayout

    def __init__(self, iso_plate_layout, attribute_name, log, number_sectors=4):
        """
        Constructor:

        :param iso_plate_layout: The ISO plate layout whose positions to check.
        :type iso_plate_layout: :class:`IsoPlateLayout`

        :param attribute_name: The name of the attribute to be determined.
        :type attribute_name: :class:`str`

        :param number_sectors: The number of rack sectors.
        :type number_sectors: :class:`int`
        :default number_sectors: *4*
        """
        ValueDeterminer.__init__(self, layout=iso_plate_layout,
                                      attribute_name=attribute_name,
                                      number_sectors=number_sectors,
                                      log=log)

    def _ignore_position(self, layout_pos):
        if layout_pos.is_mock:
            return True
        else:
            return False


class IsoPlateSectorAssociator(RackSectorAssociator):
    """
    A special rack sector associator for ISO plate layouts.

    **Return Value:** A list of lists (each list containing the indices of
        rack sector associated with one another).
    """

    NAME = 'ISO plate sector associator'

    _SECTOR_ATTR_NAME = 'concentration'
    LAYOUT_CLS = IsoPlateLayout


    def __init__(self, iso_plate_layout, log, number_sectors=4):
        """
        Constructor:

        :param iso_plate_layout: The ISO plate layout whose positions to check.
        :type iso_plate_layout: :class:`IsoPlateLayout`

        :param number_sectors: The number of rack sectors.
        :type number_sectors: :class:`int`
        :default number_sectors: *4*

        :param log: The ThelmaLog you want to write in.
        :type log: :class:`thelma.ThelmaLog`
        """
        RackSectorAssociator.__init__(self, layout=iso_plate_layout,
                                      log=log, number_sectors=number_sectors)

    def _init_value_determiner(self):
        value_determiner = IsoPlateValueDeterminer(log=self.log,
                                    iso_plate_layout=self.layout,
                                    attribute_name=self._SECTOR_ATTR_NAME,
                                    number_sectors=self.number_sectors)
        return value_determiner


class IsoPlateAssociationData(AssociationData):
    """
    A special association data class for ISO plate layouts which also stores
    the volume for each rack sector.

    :Note: All attributes are immutable.
    :Note: Error and warning recording is disabled.
    """

    def __init__(self, iso_plate_layout, log):
        """
        Constructor:

        :param iso_plate_layout: The ISO plate layout whose sectors to
            associate.
        :type iso_plate_layout: :class:`IsoPlateLayout`

        :param log: The ThelmaLog you want to write in.
        :type log: :class:`thelma.ThelmaLog`
        """
        AssociationData.__init__(self, layout=iso_plate_layout, log=log,
                                 record_errors=False)

        #: The volumes for each rack sector.
        self.__sector_volumes = None

        self.__find_volumes(iso_plate_layout, log)

    @property
    def sector_volumes(self):
        """
        The volumes for each sector.
        """
        return self.__sector_volumes

    def _find_concentrations(self, iso_plate_layout):
        concentrations = set()
        for plate_pos in iso_plate_layout.working_positions():
            concentrations.add(plate_pos.concentration)
        return concentrations

    def _init_associator(self, layout, log):
        """
        Initialises the associator.
        """
        associator = IsoPlateSectorAssociator(iso_plate_layout=layout,
                                              log=log, number_sectors=4)
        return associator


    def __find_volumes(self, iso_plate_layout, log):
        """
        Finds the volumes for each rack sector.

        :raises TypeError: If the volumes are inconsistent.
        """
        determiner = IsoPlateValueDeterminer(iso_plate_layout=iso_plate_layout,
                                    attribute_name='volume',
                                    log=log, number_sectors=self.number_sectors)
        determiner.disable_error_and_warning_recording()
        self.__sector_volumes = determiner.get_result()

        if self.__sector_volumes is None:
            msg = ', '.join(determiner.get_messages())
            raise ValueError(msg)


class IsoPrepPlateParameters(IsoPlateParameters):
    """
    These parameters describe ISO preparation plate. In addition to normal
    ISO plates, these plates have transfer targets on a different plate
    (the ISO aliquot plate).
    """

    DOMAIN = 'iso_prep_plate'

    #: The transfer targets *on the ISO aliquot plate*.
    ALIQUOT_TRANSFER_TARGETS = 'aliquot_transfer_targets'
    TRANSFER_TARGET_PARAMETERS = IsoPlateParameters.TRANSFER_TARGET_PARAMETERS \
                                 + [ALIQUOT_TRANSFER_TARGETS]
    MUST_HAVE_TRANSFER_TARGETS = IsoPlateParameters.MUST_HAVE_TRANSFER_TARGETS \
                                 + {ALIQUOT_TRANSFER_TARGETS : True}

    REQUIRED = IsoPlateParameters.REQUIRED + [ALIQUOT_TRANSFER_TARGETS]
    ALL = IsoPlateParameters.ALL + [ALIQUOT_TRANSFER_TARGETS]

    ALIAS_MAP = IsoPlateParameters.ALIAS_MAP + {
                    ALIQUOT_TRANSFER_TARGETS : []}
    DOMAIN_MAP = IsoPlateParameters.DOMAIN_MAP + {
                    ALIQUOT_TRANSFER_TARGETS : DOMAIN}


class IsoPrepPlatePosition(IsoPlatePosition):
    """
    Represents a position in an ISO preparation plate.
    """
    PARAMETER_SET = IsoPrepPlateParameters

    def __init__(self, rack_position, molecule_design_pool, position_type,
                 concentration, volume, aliquot_targets, transfer_targets=None,
                 stock_tube_barcode=None, stock_rack_barcode=None):
        """
        Constructor:

        :param rack_position: The position within the rack.
        :type rack_position: :class:`thelma.models.rack.RackPosition`

        :param molecule_design_pool: The molecule design pool for this position.
        :type molecule_design_pool:  placeholder or
            :class:`thelma.models.moleculedesign.MoleculeDesignPool`

        :param position_type: The position type (fixed, floating or mock).
        :type position_type: :class:`str`

        :param concentration: The target concentration in the plate after
            all additions and dilutions.
        :type concentration: positive number, unit nM

        :param volume: The maximum volume in the plate (after all dilutions
            but before usage as source well).
        :type volume: positive number, unit ul

        :param aliquot_targets: The transfer targets on a different (=aliquot)
            plate. There must be at least one.
        :type aliquot_targets: List of :class:`TransferTarget` objects

        :param transfer_targets: The transfer targets *within the same plate*.
        type transfer_targets: List of :class:`TransferTarget` objects

        :param stock_tube_barcode: The barcode of the stock tube of the prime
            hit of the optimisation query.
        :type stock_tube_barcode: :class:`str`

        :param stock_rack_barcode: The barcode of the stock rack of the prime
            hit of the optimisation query.
        :type stock_rack_barcode: :class:`str`
        """
        IsoPlatePosition.__init__(self, rack_position=rack_position,
                                  molecule_design_pool=molecule_design_pool,
                                  position_type=position_type,
                                  concentration=concentration,
                                  volume=volume,
                                  transfer_targets=transfer_targets,
                                  stock_tube_barcode=stock_tube_barcode,
                                  stock_rack_barcode=stock_rack_barcode)

        #: The transfer targets on the aliquot plate. There must be at least 1.
        self.aliquot_targets = self._check_transfer_targets(
                                    self.PARAMETER_SET.ALIQUOT_TRANSFER_TARGETS,
                                    aliquot_targets, 'aliquot plate targets')

    def _get_parameter_values_map(self):
        parameters = IsoPlatePosition._get_parameter_values_map(self)
        parameters[self.PARAMETER_SET.ALIQUOT_TRANSFER_TARGETS] = \
                                                        self.aliquot_targets
        return parameters


class IsoPrepPlateLayout(IsoPlateLayout):
    """
    Represents a lab ISO preparation plate.
    """
    WORKING_POSITION_CLS = IsoPrepPlatePosition


class IsoPrepPlateLayoutConverter(IsoPlateLayoutConverter):
    """
    Converts a :class:`RackLayout` into a :class:`IsoPrepPlateLayout`.
    """
    NAME = 'ISO Preparation Plate Layout Converter'

    PARAMETER_SET = IsoPrepPlateParameters
    WORKING_LAYOUT_CLS = IsoPrepPlateLayout
    WORKING_POSITION_CLS = IsoPrepPlatePosition

    def _get_position_init_values(self, parameter_map):
        rack_position = parameter_map[self._RACK_POSITION_KEY]
        aliquot_targets = parameter_map[
                                self.PARAMETER_SET.ALIQUOT_TRANSFER_TARGETS]
        if not self._are_valid_transfer_targets(aliquot_targets,
                    rack_position, self.PARAMETER_SET.ALIQUOT_TRANSFER_TARGETS):
            return None

        kw = IsoPlateLayoutConverter._get_position_init_values(self,
                                                               parameter_map)
        kw['aliquot_targets'] = aliquot_targets
        return aliquot_targets
