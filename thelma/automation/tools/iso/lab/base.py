"""
Base classes and constants involved in lab ISO processing tasks.

AAB
"""
from thelma.automation.tools.utils.base import LIBRARY_POSITION_TYPE
from thelma.automation.tools.utils.base import MOCK_POSITION_TYPE
from thelma.automation.tools.utils.base import TransferLayout
from thelma.automation.tools.utils.base import TransferParameters
from thelma.automation.tools.utils.base import TransferPosition
from thelma.automation.tools.utils.base import add_list_map_element
from thelma.automation.tools.utils.base import get_converted_number
from thelma.automation.tools.utils.base import get_trimmed_string
from thelma.automation.tools.utils.base import is_valid_number
from thelma.automation.tools.utils.converters import TransferLayoutConverter
from thelma.automation.tools.utils.iso import IsoRequestPosition
from thelma.automation.tools.utils.racksector import AssociationData
from thelma.automation.tools.utils.racksector import RackSectorAssociator
from thelma.automation.tools.utils.racksector import ValueDeterminer
from thelma.models.organization import Organization
from thelma.automation.tools.utils.base import TransferTarget

__all__ = ['get_stock_takeout_volume',
           'LabIsoRackContainer',
           'LabIsoParameters',
           'LabIsoPosition',
           'LabIsoLayout',
           'LabIsoLayoutConverter',
           'IsoPlateValueDeterminer',
           'IsoPlateSectorAssociator',
           'IsoPlateAssociationData',
           'FinalLabIsoParameters',
           'FinalLabIsoPosition',
           'FinalLabIsoLayout',
           'FinalLabIsoLayoutConverter',
           'LabIsoPrepParameters',
           'LabIsoPrepPosition',
           'LabIsoPrepLayout',
           'LabIsoPrepLayoutConverter']


def get_stock_takeout_volume(stock_concentration, final_volume, concentration):
    """
    Returns the volume that needs to be taken out of the stock in
    order to set up the desired concentration (*in ul* round to 1 decimal
    place).

    :param stock_concentration: The stock concentration for the given
        molecule type *in nM*.
    :type stock_concentration: :class:`int`
    :rtype: :class:`float`

    :param final_volume: The volume determined for a plate position *in ul*.
    :type final_volume: positive number

    :param concentration: The concentration for the target position *in nM*.
    :type concentration: positive number

    :return: The volume to be taken from the stock *in ul*.
    """
    dil_factor = stock_concentration / float(concentration)
    take_out_volume = final_volume / dil_factor
    take_out_volume = round(take_out_volume, 1)
    return take_out_volume


#: The diluent info for the planned container dilutions (always buffer).
DILUENT_INFO = 'annealing buffer'


class LABELS(object):
    """
    Generates and parses worklist and rack labels involved in lab ISO
    processing.
    """
    #: The character used in the labels to separate the value parts.
    __SEPARATING_CHAR = '_'
    #: This character is used seperate running numbers from value parts.
    NUMBERING_CHAR = '#'

    #: Marker for final ISO plates.
    ROLE_FINAL = 'a'
    #: Marker for plates related in preparation processing.
    ROLE_PREPARATION_ISO = 'p'
    #: Marker for plates related to job processing (occurs if there are
    #: floatings positions in a layout).
    ROLE_PREPARATION_JOB = 'jp'
    #: Marker for stock racks.
    ROLE_STOCK = 's'

    #: Marker for worklist counts (to facilitate worklist ordering and
    #: distinguish intraplate transfer worklists).
    MARKER_WORKLIST_NUM = 'worklist_number'
    #: Marker for worklist source racks in keyword dictionaries.
    MARKER_WORKLIST_SOURCE = 'source_rack_marker'
    #: Marker for worklist target racks in keyword dictionaries.
    MARKER_WORKLIST_TARGET = 'target_rack_marker'

    #: Marker for ticket number in keyword dictionaries.
    MARKER_TICKET_NUMBER = 'ticket_number'
    #: Marker for racks. The role can be :attr:`ROLE_FINAL`, :attr:`ROLE_STOCK`,
    #: :attr:`ROLE_PREPARATION` or :attr:`ROLE_JOB_PREPARATION`.
    MARKER_RACK_ROLE = 'rack_role'
    #: Used to distinguish racks having the same role.
    MARKER_RACK_NUM = 'rack_num'
    #: Marker for racks markers (see :func:`create_rack_marker`).
    MARKER_RACK_MARKER = 'rack_marker'
    #: Marker for ISO or ISO job number.
    MARKER_ENTITY_NUM = 'entity_num'

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
    def create_rack_marker(cls, rack_role, rack_number=None):
        """
        A rack marker contains a role and (optionally) a rack number.
        """
        value_parts = [rack_role]
        if rack_number is not None:
            rack_num = cls.__get_int_str(rack_number)
            value_parts += [rack_num]
            return cls.__create_label(value_parts, for_numbering=True)
        else:
            return rack_role

    @classmethod
    def parse_rack_marker(cls, rack_marker):
        """
        A rack marker contains a role and (optionally) a rack number.
        If the rack marker is a :attr:LIBRARY_PLACEHOLDER`, the role is
        final plate (without number).
        """
        value_parts = cls.__get_value_parts(rack_marker, for_numbering=True)
        values = {cls.MARKER_RACK_ROLE : value_parts[0]}
        if len(value_parts) > 1:
            rack_num = cls.__parse_int_str(value_parts[1])
            values[cls.MARKER_RACK_NUM] = rack_num
        return values

    @classmethod
    def create_rack_label(cls, rack_marker, entity_label):
        """
        The rack label contains the ISO or ISO job label and a rack marker.
        """
        value_parts = [entity_label, rack_marker]
        return cls.__create_label(value_parts)

    @classmethod
    def parse_rack_label(cls, plate_label):
        """
        The rack label contains the ticket ID and ISO or ISO job number,
        and a rack marker (rack role and (optionally) rack number).
        """
        value_parts = cls.__get_value_parts(plate_label)
        ticket_number = cls.__parse_int_str(value_parts[0])
        entity_num = cls.__parse_int_str(value_parts[2])
        rack_marker = value_parts[3]
        value_parts[cls.MARKER_RACK_MARKER] = rack_marker
        values = cls.parse_rack_marker(rack_marker)
        values[cls.MARKER_TICKET_NUMBER] = ticket_number
        values[cls.MARKER_ENTITY_NUM] = entity_num
        return values


    @classmethod
    def create_worklist_label(cls, ticket_number, worklist_number,
                              target_rack_marker, source_rack_marker=None):
        """
        Creates a label for a series worklist. The worklist label always
        contains the ticket number and a worklist number. Transfer worklists
        then continue with the source rack marker, a filler and the target
        rack marker (source and target marker can be equal) whereas dilution
        worklists contain the target rack marker and a (different) filler.
        """
        ticket_str = cls.__get_int_str(ticket_number)
        num_str = cls.__get_int_str(worklist_number)
        value_parts = [ticket_str, num_str]
        if source_rack_marker is None:
            value_parts += [target_rack_marker, cls.__FILL_WORKLIST_DILUTION]
        else:
            value_parts += [source_rack_marker, cls.__FILL_WORKLIST_TRANSFER,
                           target_rack_marker]
        return cls.__create_label(value_parts)

    @classmethod
    def parse_worklist_label(cls, worklist_label):
        """
        Series worklist labels always contain the ticket number and a worklist
        number. Transfer worklists then continue with the source rack marker,
        a filler and the target rack marker (source and target marker can be
        equal) whereas dilution worklists contain the target rack marker
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


class LabIsoRackContainer(object):
    """
    A helper class storing the role and rack marker for a rack involved
    in ISO processing.
    """
    def __init__(self, rack, label=None, rack_marker=None, role=None):
        """
        Constructor:

        :param rack: The rack or plate.
        :type rack: :class:`thelma.models.rack.Rack`

        :param label: The rack or stock rack label.
        :type label: :class:`basestring`
        :default label: *None* (is taken from the :param:`rack`).

        :param rack_marker: Contains the rack role and number
            (see :func:`LABELS.create_rack_marker`).
        :type rack_marker: :class:`basestring`
        :default rack_marker: *None* (is parsed from the :param:`label`).

        :param role: Final, preparation or stock preparation plate or stock rack
            (see :class:`LABELS`).
        :type role: *ROLE* value from :class:`LABELS`
        :default role: *None* (is parsed from the :param:`label`).
        """
        #: The rack or plate.
        self.rack = rack

        if label is None:
            label = rack.label
        #: The rack or stock rack label.
        self.label = label

        if rack_marker is None or role is None:
            values = LABELS.parse_rack_label(label)
            if rack_marker is None:
                rack_marker = values[LABELS.MARKER_RACK_MARKER]
            if role is None:
                role = values[LABELS.MARKER_RACK_ROLE]

        #: Contains the rack role and number (see
        #: :func:`LABELS.create_rack_marker`).
        self.rack_marker = rack_marker
        #: Final, preparation or stock preparation plate or stock rack
        #: (see :class:`LABELS`).
        self.role = role

    def __eq__(self, other):
        return isinstance(other, self.__class__) and other.rack == self.rack

    def __str__(self):
        return self.label

    def __repr__(self):
        str_format = '<%s rack: %s, label: %s>'
        params = (self.__class__.__name__, self.rack, self.label)
        return str_format % params



class LabIsoParameters(TransferParameters):
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

    #: The (lowest) sector index in the final ISO plate (only for samples
    #: that are transferred via the CyBio).
    SECTOR_INDEX = 'sector_index'
    #: The plate marker (see :class:`LABELS`) for the source stock rack (only
    #: for starting wells).
    STOCK_RACK_MARKER = 'stock_rack_marker'


    REQUIRED = TransferParameters + [CONCENTRATION, VOLUME]
    ALL = REQUIRED + [STOCK_TUBE_BARCODE, STOCK_RACK_BARCODE, TRANSFER_TARGETS,
                      SECTOR_INDEX, STOCK_RACK_MARKER]

    ALIAS_MAP = dict(TransferParameters.ALIAS_MAP, **{
                 CONCENTRATION : ['preparation_concentration'],
                 VOLUME : ['required_volume'],
                 STOCK_TUBE_BARCODE : [], STOCK_RACK_BARCODE : [],
                 SECTOR_INDEX : [], STOCK_RACK_MARKER : []})

    DOMAIN_MAP = dict(TransferParameters.DOMAIN_MAP, **{
                 CONCENTRATION : DOMAIN, VOLUME : DOMAIN,
                 STOCK_TUBE_BARCODE : DOMAIN, STOCK_RACK_BARCODE : DOMAIN,
                 SECTOR_INDEX : DOMAIN, STOCK_RACK_MARKER : DOMAIN})


class LabIsoPosition(TransferPosition):
    """
    Represents a position in a plate involved in lab ISO processing.
    """
    PARAMETER_SET = LabIsoParameters

    #: Used in the ISO planning phase to mark a staring position for which
    #: there is no tube barcode yet.
    TEMP_STOCK_DATA = 'to be defined'

    def __init__(self, rack_position, molecule_design_pool, position_type,
                 concentration, volume, transfer_targets=None,
                 stock_tube_barcode=None, stock_rack_barcode=None,
                 sector_index=None, stock_rack_marker=None):
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

        :param sector_index: The (lowest) sector index in the final ISO plate
            (only for samples that are transferred via the CyBio).
        :type sector_index: non-negative integer

        :param stock_rack_marker: The plate marker (see :class:`LABELS`) for
            the source stock rack (only for starting wells).
        :type stock_rack_marker: :class:`str`
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
        if not sector_index is None and not is_valid_number(sector_index,
                                        may_be_zero=True, is_integer=True):
            msg = 'The sector index must be a non-negative integer (obtained: ' \
                  '%s).' % (sector_index)
            raise ValueError(msg)
        if not stock_rack_marker is None and \
                (not isinstance(stock_rack_marker, basestring) or \
                 len(stock_rack_marker) < 2):
            msg = 'The stock rack marker must be a string of at least 2 ' \
                  'characters length (obtained: %s).' % (stock_rack_marker)
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

        #: The (lowest) sector index in the final ISO plate (only for samples
        #: that are transferred via the CyBio).
        self.sector_index = sector_index
        #: The plate marker (see :class:`LABELS`) for the source stock rack
        #: (only for starting wells).
        self.stock_rack_marker = stock_rack_marker

        if self.is_mock:
            self.concentration = None
            self.stock_rack_barcode = None
            self.stock_tube_barcode = None
            self.stock_rack_marker = None

    @classmethod
    def create_mock_position(cls, rack_position, volume):
        """
        Returns an ISO plate position with mock molecule design pool.

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
        if not (self.is_fixed or self.is_floating): return False
        return (self.stock_rack_marker is not None and \
                self.stock_tube_barcode is None)

    def inactivate(self):
        """
        Inactivates the position (setting stock tube and barcode to *None*).
        A position is set to inactivated if there is no suitable stock tube
        found. Only floating positions can be inactivated.

        :raises AttributeError: If the position is not a floating position.
        """
        if self.is_floating:
            self.stock_tube_barcode = None
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
        if not (self.is_floating or self.is_fixed): return False
        return (self.stock_rack_marker is not None)

    def get_stock_takeout_volume(self):
        """
        Returns the volume that needs to be taken out of the stock in
        order to set up the desired concentration (*in ul* rounded to 1 decimal
        place).
        Return *None* for non-starting wells (= wells without
        :attr:`stock_tube_barcode`) and *0* for mock positions.

        :raise ValueError: if the stock concentration is *None*

        :rtype: :class:`float`, unit ul
        """
        if not self.is_starting_well: return None
        if self.stock_concentration is None:
            raise ValueError('The stock concentration must not be None!')
        take_out_volume = get_stock_takeout_volume(self.stock_concentration,
                                            self.volume, self.concentration)
        return take_out_volume

    def create_completed_copy(self, tube_candidate):
        """
        Returns a copy of this LabIsoPosition that has a specific molecule
        design pool (in case of floating positions) and, if this position is
        a starting well also defined stock tube barcode and stock rack barcode.
        A well is regarded as starting well if its current
        :attr:`stock_tube_barcode` is equal to the :attr:`TEMP_STOCK_DATA`.

        :param tube_candidate: The tube candidate used to complete the position
            data.
        :type tube_candidate: :class:`TubeCandidate`

        :raises ValueError: If there is already a pool for a floating
            position, if (in case of fixed positions) if the pool of tube
            candidate and position do not match or if there is already a
            non-placeholde stock tube barcode set.
        :return: The LabIsoPosition or *None* if any value is invalid.
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

        if self.stock_tube_barcode == self.TEMP_STOCK_DATA:
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

    def as_transfer_target(self):
        """
        Returns a :class:`TransferTarget` for a :class:`StockRackPosition`.
        For starting wells only.
        """
        return TransferTarget(rack_position=self.rack_position,
                              transfer_volume=self.get_stock_takeout_volume(),
                              target_rack_marker=self.stock_rack_marker)

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
        parameters[self.PARAMETER_SET.SECTOR_INDEX] = self.sector_index
        parameters[self.PARAMETER_SET.STOCK_RACK_MARKER] = \
                                                      self.stock_rack_marker
        return parameters

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


class LabIsoLayout(TransferLayout):
    """
    Represents a plate in a lab ISO preparation process.
    """
    WORKING_POSITION_CLS = LabIsoPosition

    #: Is used to indicate working position without sector indices in sector
    #: maps (see :func:`get_sector_map`).
    NO_SECTOR_MARKER = 'no sector'

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

    def get_sector_map(self):
        """
        Sorts the plate positions by sector index. Positions without sector
        index are marked using the :attr:`NO_SECTOR_MARKER` key.
        Only floating and fixed positions are regarded.
        """
        sector_map = dict()
        for plate_pos in self._position_map.values():
            if not (plate_pos.is_floating or plate_pos.is_fixed): continue
            if plate_pos.sector_index is None:
                sector_marker = self.NO_SECTOR_MARKER
            else:
                sector_marker = plate_pos.sector_index
            add_list_map_element(sector_map, sector_marker, plate_pos)
        return sector_map

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

    def create_rack_layout(self):
        """
        Also makes sure all starting wells have non-temporary data (otherwise
        and AttributeError is raised).
        """
        self.__check_starting_wells()
        return TransferLayout.create_rack_layout(self)

    def __check_starting_wells(self):
        """
        If there is still starting wells with temporary stock data in the layout
        the layout mut not be converted into a rack layout and a error is
        raised.
        """
        tmp_value = self.WORKING_POSITION_CLS.TEMP_STOCK_DATA
        for plate_pos in self._position_map.values():
            if not plate_pos.is_starting_well: continue
            if plate_pos.stock_tube_barcode == tmp_value or \
                                plate_pos.stock_rack_marker == tmp_value:
                raise AttributeError('There are still starting wells without ' \
                                     'stock data in the layout!')


class LabIsoLayoutConverter(TransferLayoutConverter):
    """
    Converts a :class:`RackLayout` into a :class:`LabIsoLayout`.
    """
    NAME = 'ISO Plate Layout Converter'

    PARAMETER_SET = LabIsoParameters
    WORKING_LAYOUT_CLS = LabIsoLayout
    WORKING_POSITION_CLS = LabIsoPosition

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

    WORKING_LAYOUT_CLS = LabIsoLayout

    def __init__(self, iso_plate_layout, attribute_name, log, number_sectors=4):
        """
        Constructor:

        :param iso_plate_layout: The ISO plate layout whose positions to check.
        :type iso_plate_layout: :class:`LabIsoLayout`

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
    LAYOUT_CLS = LabIsoLayout


    def __init__(self, iso_plate_layout, log, number_sectors=4):
        """
        Constructor:

        :param iso_plate_layout: The ISO plate layout whose positions to check.
        :type iso_plate_layout: :class:`LabIsoLayout`

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
        :type iso_plate_layout: :class:`LabIsoLayout`

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

    def _init_value_determiner(self, layout, log):
        value_determiner = IsoPlateValueDeterminer(iso_plate_layout=layout,
                                attribute_name='concentration',
                                log=log, number_sectors=self._number_sectors)
        return value_determiner

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


class FinalLabIsoParameters(LabIsoParameters):
    """
    These parameters describe a final ISO plate (aliquot or library plate to
    be comppleted). In addition to normal ISO plates, we have mark whether
    a sample originates from an ISO job or an ISO.
    """
    DOMAIN = 'final_iso_plate'

    #: Is the pool for this position handled by the ISO job (*True*) or the
    #: ISO (*False*)?
    FROM_JOB = 'from_job'

    ALL = LabIsoParameters.ALL + [FROM_JOB]
    ALIAS_MAP = dict(LabIsoParameters.ALIAS_MAP, **{FROM_JOB : []})
    DOMAIN_MAP = dict(LabIsoParameters.DOMAIN_MAP, **{FROM_JOB : DOMAIN})


class FinalLabIsoPosition(LabIsoPosition):
    """
    This position reflects a position in an final ISO plate. In addition to
    normal ISO plates, we have mark whether an sample originates from an ISO job
    or an ISO.
    """
    PARAMETER_SET = FinalLabIsoParameters

    RECORD_FALSE_VALUES = False

    def __init__(self, rack_position, molecule_design_pool, position_type,
                 concentration, volume, from_job=False, transfer_targets=None,
                 stock_tube_barcode=None, stock_rack_barcode=None,
                 sector_index=None, stock_rack_marker=None):
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

        :param from_job: Is the pool for this position handled by the ISO job
            (*True*) or the ISO (*False*)?
        :type from_job: :class:`bool`
        :default from_job: *False*

        :param transfer_targets: The transfer targets *within the same plate*.
        type transfer_targets: List of transfer target objects.

        :param stock_tube_barcode: The barcode of the stock tube of the prime
            hit of the optimisation query.
        :type stock_tube_barcode: :class:`str`

        :param stock_rack_barcode: The barcode of the stock rack of the prime
            hit of the optimisation query.
        :type stock_rack_barcode: :class:`str`

        :param sector_index: The sector index within in the plate (only for
            samples that are transferred via the CyBio).
        :type sector_index: non-negative integer

        :param stock_rack_marker: The plate marker (see :class:`LABELS`) for
            the source stock rack (only for starting wells).
        :type stock_rack_marker: :class:`str`
        """
        LabIsoPosition.__init__(self, rack_position=rack_position,
                                  molecule_design_pool=molecule_design_pool,
                                  position_type=position_type,
                                  concentration=concentration,
                                  volume=volume,
                                  transfer_targets=transfer_targets,
                                  stock_tube_barcode=stock_tube_barcode,
                                  stock_rack_barcode=stock_rack_barcode,
                                  sector_index=sector_index,
                                  stock_rack_marker=stock_rack_marker)

        #: Is the pool for this position handled by the ISO job (*True*) or
        #: the ISO (*False*)?
        self.from_job = from_job

    @classmethod
    def from_iso_plate_position(cls, from_job, iso_plate_pos):
        """
        Factory method creating an :class:`FinalLabIsoPosition` from
        a normal :class:`LabIsoPosition`.

        :param from_job: Does the sample originate from ISO job processing
            (*True*) or the ISO processing (*False*)?
        :type from_job: :class:`bool`

        :param iso_plate_pos: The ISO plate position containing the values
            for this final ISO position.
        :type iso_plate_pos: :class:`LabIsoPosition`
        """
        attr_names = ('rack_position', 'molecule_design_pool', 'position_type',
                      'concentration', 'volume', 'transfer_targets',
                      'stock_tube_barcode', 'stock_rack_barcode')
        kw = dict()
        for attr_name in attr_names:
            value = getattr(iso_plate_pos, attr_name)
            kw[attr_name] = value
        kw['from_job'] = from_job
        return FinalLabIsoPosition(**kw)

    @classmethod
    def create_library_position(cls, rack_position, concentration, volume):
        """
        Returns a library type ISO plate position with the given values.
        The samples are already present in the plates.

        :param rack_position: The position within the rack.
        :type rack_position: :class:`thelma.models.rack.RackPosition`

        :param concentration: The pool concentration in the plate *in nM*.
        :type concentration: positive number, unit nM

        :param volume: The volume in the plate *in ul*.
        :type volume: positive number, unit ul
        """
        return cls(rack_position=rack_position,
                   molecule_design_pool=LIBRARY_POSITION_TYPE,
                   position_type=LIBRARY_POSITION_TYPE,
                   concentration=concentration,
                   volume=volume)

    def _get_parameter_values_map(self):
        parameters = LabIsoPosition._get_parameter_values_map(self)
        parameters[self.PARAMETER_SET.FROM_JOB] = self.from_job
        return parameters


class FinalLabIsoLayout(LabIsoLayout):
    """
    Represents an final ISO plate (:class:`IsoAliquotPlate`) or (for
    library screenings) a library plate (:class:`IsoLibraryPlate`)
    to be completed..
    """
    WORKING_POSITION_CLS = FinalLabIsoPosition


class FinalLabIsoLayoutConverter(LabIsoLayoutConverter):
    """
    Converts a :class:`RackLayout` into a :class:`FinalLabIsoLayout`.
    """
    NAME = 'ISO Final Plate Layout Converter'

    PARAMETER_SET = FinalLabIsoParameters
    WORKING_LAYOUT_CLS = FinalLabIsoLayout
    WORKING_POSITION_CLS = FinalLabIsoPosition

    def __init__(self, rack_layout, log):
        """
        Constructor:

        :param rack_layout: The rack layout containing the plate data.
        :type rack_layout: :class:`thelma.models.racklayout.RackLayout`

        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`
        """
        LabIsoLayoutConverter.__init__(self, rack_layout=rack_layout, log=log)

        # intermediate error storage
        self.__invalid_from_job = None

    def reset(self):
        LabIsoLayoutConverter.reset(self)
        self.__invalid_from_job = []

    def _get_position_init_values(self, parameter_map):
        rack_position = parameter_map[self._RACK_POSITION_KEY]
        from_job_str = parameter_map[self.PARAMETER_SET.FROM_JOB]

        kw = LabIsoLayoutConverter._get_position_init_values(self,
                                                               parameter_map)
        from_job = self._get_boolean_value(from_job_str, rack_position.label,
                                           self.__invalid_from_job)
        if from_job is None or kw is None: return None
        kw['from_job'] = from_job
        return kw

    def _record_additional_position_errors(self):
        LabIsoLayoutConverter._record_additional_position_errors(self)
        self._record_invalid_boolean_error('from job', self.__invalid_from_job)


class LabIsoPrepParameters(LabIsoParameters):
    """
    These parameters describe ISO preparation plate. In addition to normal
    ISO plates, these plates have transfer targets on a different plate
    (the final ISO plate).
    """

    DOMAIN = 'iso_prep_plate'

    #: The transfer targets *on the final ISO plate*.
    EXTERNAL_TRANSFER_TARGETS = 'external_transfer_targets'
    TRANSFER_TARGET_PARAMETERS = LabIsoParameters.TRANSFER_TARGET_PARAMETERS \
                                 + [EXTERNAL_TRANSFER_TARGETS]
    MUST_HAVE_TRANSFER_TARGETS = \
                            dict(LabIsoParameters.MUST_HAVE_TRANSFER_TARGETS,
                                 {EXTERNAL_TRANSFER_TARGETS : True})

    REQUIRED = LabIsoParameters.REQUIRED + [EXTERNAL_TRANSFER_TARGETS]
    ALL = LabIsoParameters.ALL + [EXTERNAL_TRANSFER_TARGETS]

    ALIAS_MAP = dict(LabIsoParameters.ALIAS_MAP, **{
                    EXTERNAL_TRANSFER_TARGETS : []})
    DOMAIN_MAP = dict(LabIsoParameters.DOMAIN_MAP, **{
                    EXTERNAL_TRANSFER_TARGETS : DOMAIN})


class LabIsoPrepPosition(LabIsoPosition):
    """
    Represents a position in an ISO preparation plate.
    """
    PARAMETER_SET = LabIsoPrepParameters

    def __init__(self, rack_position, molecule_design_pool, position_type,
                 concentration, volume, external_targets, transfer_targets=None,
                 stock_tube_barcode=None, stock_rack_barcode=None,
                 sector_index=None, stock_rack_marker=None):
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

        :param external_targets: The transfer targets on a different
            (= final ISO) plate. There must be at least one.
        :type external_targets: List of :class:`TransferTarget` objects

        :param transfer_targets: The transfer targets *within the same plate*.
        type transfer_targets: List of :class:`TransferTarget` objects

        :param stock_tube_barcode: The barcode of the stock tube of the prime
            hit of the optimisation query.
        :type stock_tube_barcode: :class:`str`

        :param stock_rack_barcode: The barcode of the stock rack of the prime
            hit of the optimisation query.
        :type stock_rack_barcode: :class:`str`

        :param sector_index: The sector index within in the plate (only for
            samples that are transferred via the CyBio).
        :type sector_index: non-negative integer

        :param stock_rack_marker: The plate marker (see :class:`LABELS`) for
            the source stock rack (only for starting wells).
        :type stock_rack_marker: :class:`str`
        """
        LabIsoPosition.__init__(self, rack_position=rack_position,
                                  molecule_design_pool=molecule_design_pool,
                                  position_type=position_type,
                                  concentration=concentration,
                                  volume=volume,
                                  transfer_targets=transfer_targets,
                                  stock_tube_barcode=stock_tube_barcode,
                                  stock_rack_barcode=stock_rack_barcode,
                                  sector_index=sector_index,
                                  stock_rack_marker=stock_rack_marker)

        #: The transfer targets on the final ISO plate. There must be at
        #: least 1.
        self.external_targets = self._check_transfer_targets(
                                self.PARAMETER_SET.EXTERNAL_TRANSFER_TARGETS,
                                external_targets, 'external plate targets')

    def _get_parameter_values_map(self):
        parameters = LabIsoPosition._get_parameter_values_map(self)
        parameters[self.PARAMETER_SET.EXTERNAL_TRANSFER_TARGETS] = \
                                                        self.external_targets
        return parameters


class LabIsoPrepLayout(LabIsoLayout):
    """
    Represents a lab ISO preparation plate.
    """
    WORKING_POSITION_CLS = LabIsoPrepPosition


class LabIsoPrepLayoutConverter(LabIsoLayoutConverter):
    """
    Converts a :class:`RackLayout` into a :class:`LabIsoPrepLayout`.
    """
    NAME = 'ISO Preparation Plate Layout Converter'

    PARAMETER_SET = LabIsoPrepParameters
    WORKING_LAYOUT_CLS = LabIsoPrepLayout
    WORKING_POSITION_CLS = LabIsoPrepPosition

    def _get_position_init_values(self, parameter_map):
        rack_position = parameter_map[self._RACK_POSITION_KEY]
        external_targets = parameter_map[
                                self.PARAMETER_SET.EXTERNAL_TRANSFER_TARGETS]

        kw = LabIsoLayoutConverter._get_position_init_values(self,
                                                               parameter_map)
        if not self._are_valid_transfer_targets(external_targets,
                   rack_position, self.PARAMETER_SET.EXTERNAL_TRANSFER_TARGETS):
            return None

        if not kw is None: kw['external_targets'] = external_targets
        return kw

