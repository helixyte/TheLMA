"""
Base classes, functions and constants involved in lab ISO processing tasks.

AAB
"""
from thelma.automation.tools.iso.base import IsoRackContainer
from thelma.automation.tools.iso.base import _ISO_LABELS_BASE
from thelma.automation.tools.worklists.base import TRANSFER_ROLES
from thelma.automation.tools.writers import TxtWriter
from thelma.automation.utils.base import add_list_map_element
from thelma.automation.utils.converters import TransferLayoutConverter
from thelma.automation.utils.layouts import EMPTY_POSITION_TYPE
from thelma.automation.utils.layouts import FIXED_POSITION_TYPE
from thelma.automation.utils.layouts import FLOATING_POSITION_TYPE
from thelma.automation.utils.layouts import LIBRARY_POSITION_TYPE
from thelma.automation.utils.layouts import MOCK_POSITION_TYPE
from thelma.automation.utils.layouts import TransferLayout
from thelma.automation.utils.layouts import TransferParameters
from thelma.automation.utils.layouts import TransferPosition
from thelma.automation.utils.layouts import TransferTarget
from thelma.automation.utils.layouts import get_converted_number
from thelma.automation.utils.layouts import get_trimmed_string
from thelma.automation.utils.layouts import is_valid_number
from thelma.models.iso import LabIso
from thelma.models.iso import LabIsoRequest
from thelma.models.job import IsoJob
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.moleculedesign import MoleculeDesignPool
from thelma.automation.utils.layouts import MoleculeDesignPoolParameters

__all__ = ['get_stock_takeout_volume',
           'LABELS',
           'LabIsoParameters',
           'LabIsoPosition',
           'LabIsoLayout',
           'LabIsoLayoutConverter',
           'FinalLabIsoParameters',
           'FinalLabIsoPosition',
           'FinalLabIsoLayout',
           'FinalLabIsoLayoutConverter',
           'LabIsoPrepParameters',
           'LabIsoPrepPosition',
           'LabIsoPrepLayout',
           'LabIsoPrepLayoutConverter',
           '_InstructionsWriter',
           '_LabIsoJobInstructionsWriter',
           '_LabIsoInstructionsWriter',
           'create_instructions_writer']


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


class LABELS(_ISO_LABELS_BASE):
    """
    Generates and parses worklist and rack labels involved in lab ISO
    processing.
    """

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

    #: Marker for ticket number in keyword dictionaries.
    MARKER_TICKET_NUMBER = 'ticket_number'

    #: Marker for ISO or ISO job number.
    MARKER_ENTITY_NUM = 'entity_num'

    #: For transfer worklists. Located between source and target rack.
    __FILL_WORKLIST_TRANSFER = 'to'
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
        value_parts = [ticket_number, cls.__FILL_ISO, iso_num_str]
        if create_copy: value_parts += [cls.__ISO_COPY_MARKER]
        return cls._create_label(value_parts)

    @classmethod
    def parse_iso_label(cls, label):
        """
        Parses an ISO label and returns the value parts as map. The values
        are ticket number and ISO number. Potential copy markers are ignored.
        """
        value_parts = cls._get_value_parts(label)
        ticket_num = cls._parse_int_str(value_parts[0])
        iso_num = cls._parse_int_str(value_parts[2])
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
        value_parts = cls._get_value_parts(iso.label)
        return cls._parse_int_str(value_parts[2])

    @classmethod
    def create_job_label(cls, ticket_number, job_number):
        """
        The job label contains the ticket ID and a running number as job number
        (you can get a new ISO number with :func:`get_new_job_number`).
        """
        job_num_str = '%02i' % (job_number)
        value_parts = [ticket_number, cls.__FILL_ISO_JOB, job_num_str]
        return cls._create_label(value_parts)

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
        value_parts = cls._get_value_parts(iso_job.label)
        return cls._parse_int_str(value_parts[2])

    @classmethod
    def create_rack_label(cls, rack_marker, entity_label):
        """
        The rack label contains the ISO or ISO job label and a rack marker.
        """
        value_parts = [entity_label, rack_marker]
        return cls._create_label(value_parts)

    @classmethod
    def parse_rack_label(cls, rack_label):
        """
        The rack label contains the ticket ID and ISO or ISO job number,
        and a rack marker (rack role and (optionally) rack number).
        """
        value_parts = cls._get_value_parts(rack_label)
        ticket_number = cls._parse_int_str(value_parts[0])
        entity_num = cls._parse_int_str(value_parts[2])
        rack_marker = value_parts[3]
        value_parts[-1] = rack_marker
        values = cls.parse_rack_marker(rack_marker)
        values[cls.MARKER_RACK_MARKER] = rack_marker
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
        value_parts = [ticket_number, worklist_number]
        if source_rack_marker is None:
            value_parts += [target_rack_marker, cls._FILL_WORKLIST_DILUTION]
        else:
            value_parts += [source_rack_marker, cls.__FILL_WORKLIST_TRANSFER,
                           target_rack_marker]
        return cls._create_label(value_parts)

    @classmethod
    def parse_worklist_label(cls, worklist_label):
        """
        Series worklist labels always contain the ticket number and a worklist
        number. Transfer worklists then continue with the source rack marker,
        a filler and the target rack marker (source and target marker can be
        equal) whereas dilution worklists contain the target rack marker
        and a (different) filler.
        """
        value_parts = cls._get_value_parts(worklist_label)
        ticket_number = cls._parse_int_str(value_parts[0])
        worklist_num = cls._parse_int_str(value_parts[1])
        values = {cls.MARKER_TICKET_NUMBER : ticket_number,
                  cls.MARKER_WORKLIST_NUM : worklist_num}
        if len(value_parts) == 4: # dilution
            values[cls.MARKER_WORKLIST_TARGET] = value_parts[2]
        else: # transfer
            values[cls.MARKER_WORKLIST_SOURCE] = value_parts[2]
            values[cls.MARKER_WORKLIST_TARGET] = value_parts[4]
        return values

    @classmethod
    def create_final_plate_label(cls, iso, plate_num=None):
        """
        The final plate label is replaces the working label of final (aliquot
        and library) plates once the plate generation is completed. It
        contains the ISO request label, the ISO number and (optionally) a
        plate number.
        """
        iso_request = iso.iso_request
        iso_values = cls.parse_iso_label(iso.label)
        iso_num = iso_values[cls.MARKER_ENTITY_NUM]
        value_parts = [iso_request.label, iso_num]
        if plate_num is not None: value_parts.append(plate_num)
        return cls._create_label(value_parts)


class LabIsoParameters(TransferParameters):
    """
    These parameters are involved in the preparation of lab ISOs.
    """

    DOMAIN = 'iso_plate'
    ALLOWED_POSITION_TYPES = [FIXED_POSITION_TYPE, FLOATING_POSITION_TYPE,
                              MOCK_POSITION_TYPE, LIBRARY_POSITION_TYPE,
                              EMPTY_POSITION_TYPE]

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

    REQUIRED = TransferParameters.REQUIRED
    ALL = TransferParameters.ALL + [STOCK_TUBE_BARCODE, STOCK_RACK_BARCODE,
                SECTOR_INDEX, STOCK_RACK_MARKER, CONCENTRATION, VOLUME]

    ALIAS_MAP = dict(TransferParameters.ALIAS_MAP, **{
                 CONCENTRATION : ['preparation_concentration'],
                 VOLUME : ['required_volume'],
                 STOCK_TUBE_BARCODE : [], STOCK_RACK_BARCODE : [],
                 SECTOR_INDEX : [], STOCK_RACK_MARKER : []})

    DOMAIN_MAP = dict(TransferParameters.DOMAIN_MAP, **{
                 CONCENTRATION : DOMAIN, VOLUME : DOMAIN,
                 STOCK_TUBE_BARCODE : DOMAIN, STOCK_RACK_BARCODE : DOMAIN,
                 SECTOR_INDEX : DOMAIN, STOCK_RACK_MARKER : DOMAIN})

    MOCK_NON_PARAMETERS = MoleculeDesignPoolParameters.MOCK_NON_PARAMETERS \
                          + [CONCENTRATION, STOCK_TUBE_BARCODE,
                             STOCK_RACK_BARCODE, STOCK_RACK_MARKER]

    @classmethod
    def is_valid_mock_value(cls, value, parameter):
        if not super(LabIsoParameters, cls).is_valid_mock_value(value,
                                                                parameter):
            return False
        if parameter == cls.VOLUME:
            return is_valid_number(value)
        elif parameter == cls.SECTOR_INDEX:
            return is_valid_number(value, may_be_zero=True, is_integer=True)
        return True


class LabIsoPosition(TransferPosition):
    """
    Represents a position in a plate involved in lab ISO processing.
    """
    PARAMETER_SET = LabIsoParameters

    #: Used in the ISO planning phase to mark a staring position for which
    #: there is no tube barcode yet.
    TEMP_STOCK_DATA = 'to be defined'
    #: Is used to mark floating positions for which there has been no pool
    #: anymore.
    MISSING_FLOATING = 'missing_floating'

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
        if position_type is None:
            msg = 'The position type for a %s position must not be None!' \
                  % (self.__class__.__name__)
            raise ValueError(msg)
        TransferPosition.__init__(self, rack_position=rack_position,
                                  molecule_design_pool=molecule_design_pool,
                                  transfer_targets=transfer_targets,
                                  position_type=position_type)

        if concentration is None:
            if self.is_fixed or self.is_floating or self.is_library:
                msg = 'The concentration for %s lab ISO positions must ' \
                      'not be None!' % (self.position_type)
                raise ValueError(msg)
        elif not is_valid_number(concentration):
            msg = 'The concentration must be a positive number (obtained: ' \
                  '%s).' % (concentration)
            raise ValueError(msg)

        if volume is None:
            if self.is_fixed or self.is_floating or self.is_mock or \
                                                    self.is_library:
                msg = 'The volume for %s lab ISO positions must not be None!' \
                      % (self.position_type)
                raise ValueError(msg)
        elif not is_valid_number(volume):
            msg = 'The volume must a positive number (obtained: %s)' % (volume)
            raise ValueError(msg)

        if not stock_tube_barcode is None and \
                    (not isinstance(stock_tube_barcode, basestring) or \
                     len(stock_tube_barcode) < 2):
            msg = 'The stock tube barcode must be a string of at least 2 ' \
                  'characters length (obtained: %s).' % (stock_tube_barcode)
            raise TypeError(msg)
        if not stock_rack_barcode is None and \
                    (not isinstance(stock_rack_barcode, basestring) or \
                     len(stock_rack_barcode) < 2):
            msg = 'The stock rack barcode must be a string of at least 2 ' \
                  'characters length (obtained: %s).' % (stock_rack_barcode)
            raise TypeError(msg)
        if not sector_index is None and not is_valid_number(sector_index,
                                        may_be_zero=True, is_integer=True):
            msg = 'The sector index must be a non-negative integer (obtained: ' \
                  '%s).' % (sector_index)
            raise ValueError(msg)
        if not stock_rack_marker is None and \
                                not isinstance(stock_rack_marker, basestring):
            msg = 'The stock rack marker must be a string (obtained: %s).' \
                  % (stock_rack_marker)
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
        self.volume = get_converted_number(volume)

        #: The (lowest) sector index in the final ISO plate (only for samples
        #: that are transferred via the CyBio).
        self.sector_index = sector_index
        #: The plate marker (see :class:`LABELS`) for the source stock rack
        #: (only for starting wells).
        self.stock_rack_marker = stock_rack_marker

        non_values = {'stock tube barcode' : stock_tube_barcode,
                      'stock rack barcode' : stock_rack_barcode,
                      'stock rack marker' : stock_rack_marker}
        if self.is_library:
            non_values['transfer_targets'] = transfer_targets
            self.__check_non_values(non_values)
        elif self.is_mock:
            non_values['concentration'] = concentration
            self.__check_non_values(non_values)
        elif self.is_empty:
            non_values['volume'] = volume
            non_values['sector index'] = sector_index
            non_values['concentration'] = concentration
            self.__check_non_values(non_values)

    def __check_non_values(self, value_map):
        """
        Helper method making sure that certain values are None.
        """
        for attr_name, value in value_map.iteritems():
            if attr_name == 'transfer_targets':
                if not (value is None or len(value) < 1):
                    msg = 'Lab ISO position of this type (%s) must not have ' \
                          'transfer targets!' % (self.position_type)
                    raise ValueError(msg)
            elif not value is None:
                msg = 'The %s for %s lab ISO positions must be None!' \
                      % (attr_name, self.position_type)
                raise ValueError(msg)

    def _get_position_type(self, position_type):
        """
        This method has to be overwritten because floating position are also
        allowed to have molecule design pool entities as pool (after their
        placeholders have been replaced by a picked tube pool).
        """
        if position_type == FLOATING_POSITION_TYPE:
            if self.molecule_design_pool == self.MISSING_FLOATING  or \
                   isinstance(self.molecule_design_pool, MoleculeDesignPool):
                return position_type
        return TransferPosition._get_position_type(self, position_type)

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
                   position_type=MOCK_POSITION_TYPE, volume=volume,
                   concentration=None)

    @property
    def is_missing_floating(self):
        """
        Missing floatings are positions which are empty because there has
        not been a pool left for it (they are marked by a special
        molecule design pool placeholder).
        """
        if not self.is_floating: return False
        return self.molecule_design_pool == self.MISSING_FLOATING

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
        a starting well also it will also get a defined stock tube barcode
        and stock rack barcode.
        A well is regarded as starting well if its current
        :attr:`stock_tube_barcode` is equal to the :attr:`TEMP_STOCK_DATA`.

        If the tube candidate for a floating position is *None*, the floating
        position is set as missing floating.

        :param tube_candidate: The tube candidate used to complete the position
            data (or *None* for missing floatings).
        :type tube_candidate: :class:`TubeCandidate`

        :raises ValueError: If there is already a pool for a floating
            position, if (in case of fixed positions) if the pool of tube
            candidate and position do not match, if the tube candidate for
            a fixed position is *None* or if the position type is not
            fixed or floating.
        :raises AttributeError: If there is already a non-placeholder stock
            tube barcode set.
        :return: The LabIsoPosition or *None* if any value is invalid.
        """
        if self.is_floating:
            if not isinstance(self.molecule_design_pool, basestring):
                msg = 'The pool for this floating position is already set ' \
                      '(%s)!' % (self.molecule_design_pool)
                raise AttributeError(msg)
            if tube_candidate is None:
                return self.create_missing_floating_copy()
            else:
                pool = tube_candidate.get_pool()
        elif self.is_fixed:
            pool = self.molecule_design_pool
            if tube_candidate is None:
                msg = 'The tube candidate for a fixed position must not be ' \
                      'None!'
                raise ValueError(msg)
            elif not tube_candidate.pool_id == pool.id:
                msg = 'The pools of the position (%s) and the tube candidate ' \
                      '(%i) do not match!' % (pool, tube_candidate.pool_id)
                raise ValueError(msg)
        else:
            msg = 'Completed copies can only be created for fixed and ' \
                  'floating positions. This is a %s position.' \
                   % (self.position_type)
            raise ValueError(msg)

        stock_tube_barcode, stock_rack_barcode = None, None
        if self.stock_tube_barcode == self.TEMP_STOCK_DATA:
            stock_tube_barcode = tube_candidate.tube_barcode
            stock_rack_barcode = tube_candidate.rack_barcode
        elif self.stock_tube_barcode is not None:
            msg = 'There is already a stock tube barcode set for this ' \
                  'position (%s)!' % (self.stock_tube_barcode)
            raise AttributeError(msg)

        kw = dict(molecule_design_pool=pool,
                  position_type=self.position_type,
                  stock_tube_barcode=stock_tube_barcode,
                  stock_rack_barcode=stock_rack_barcode,
                  transfer_targets=self.transfer_targets)
        return self.__create_adjusted_copy(**kw)

    def create_missing_floating_copy(self):
        """
        Creates a floating position which is empty because no pool has been
        left for it (used to find ignored positions for worklists).
        """
        kw = dict(molecule_design_pool=self.MISSING_FLOATING,
                  position_type=self.position_type)
        return self.__create_adjusted_copy(**kw)

    def __create_adjusted_copy(self, **kw):
        """
        Returns an (adjusted) copy of this position which has the same
        rack position.
        """
        self._add_class_specific_keywords(kw)
        kw['rack_position'] = self.rack_position
        kw['concentration'] = self.concentration
        kw['volume'] = self.volume
        kw['sector_index'] = self.sector_index
        return self.__class__(**kw)

    def _add_class_specific_keywords(self, kw):
        """
        Adds subclass-specific keywords to a keyword dictionary used to create
        a new position.
        """
        pass

    def as_transfer_target(self, target_plate_marker):
        """
        Returns a :class:`TransferTarget` for a :class:`StockRackPosition`.
        For starting wells only.

        :param target_plate_marker: The rack marker for the rack
            (see :func:`LABELS.create_rack_marker`) in which position is located.
        :type target_plate_marker: :class:`basestring`
        """
        return TransferTarget(rack_position=self.rack_position,
                              transfer_volume=self.get_stock_takeout_volume(),
                              target_rack_marker=target_plate_marker)

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
        if not TransferPosition.__eq__(self, other): return False
        return self.concentration == other.concentration and \
               self.volume == other.volume

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
    POSITION_CLS = LabIsoPosition

    #: Is used to indicate working position without sector indices in sector
    #: maps (see :func:`get_sector_map`).
    NO_SECTOR_MARKER = 'no sector'

    def get_sorted_floating_positions(self):
        """
        Returns the floating positions sorted by pool ID.
        Is invoked before assigning tube candidates to floating positions.
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
        tmp_value = self.POSITION_CLS.TEMP_STOCK_DATA
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
    LAYOUT_CLS = LabIsoLayout
    POSITION_CLS = LabIsoPosition

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
        self.__invalid_conc = None
        self.__invalid_vol = None
        self.__invalid_sector_index = None
        self.__invalid_tube_barcode = None
        self.__invalid_rack_barcode = None
        self.__transfer_target_not_allowed = None
        self.__invalid_floating = None
        self.__tube_data_not_allowed = None

    def reset(self):
        """
        Resets all attributes except for the :attr:`rack_layout`.
        """
        TransferLayoutConverter.reset(self)
        self.__invalid_conc = []
        self.__invalid_vol = []
        self.__invalid_sector_index = []
        self.__invalid_tube_barcode = []
        self.__invalid_rack_barcode = []
        self.__transfer_target_not_allowed = []
        self.__invalid_floating = set()
        self.__tube_data_not_allowed = []

    def _get_position_init_values(self, parameter_map, rack_pos):
        kw = TransferLayoutConverter._get_position_init_values(self,
                                                parameter_map, rack_pos)
        if kw is None: return None
        pos_label = rack_pos.label

        pos_type = kw['position_type']

        invalid = False
        concentration = parameter_map[self.PARAMETER_SET.CONCENTRATION]
        if pos_type == MOCK_POSITION_TYPE:
            if not concentration is None:
                info = '%s (%s)' % (pos_label, concentration)
                self.__invalid_conc.append(info)
                invalid = True
        elif not is_valid_number(concentration):
            info = '%s (%s)' % (pos_label, concentration)
            self.__invalid_conc.append(info)
            invalid = True

        volume = parameter_map[self.PARAMETER_SET.VOLUME]
        if not is_valid_number(volume):
            info = '%s (%s)' % (pos_label, volume)
            self.__invalid_vol.append(info)
            invalid = True

        if pos_type == LIBRARY_POSITION_TYPE:
            tts = kw['transfer_targets']
            if not (tts is None or len(tts) < 1):
                self.__transfer_target_not_allowed.append(pos_label)
                invalid = True

        sector_index = parameter_map[self.PARAMETER_SET.SECTOR_INDEX]
        if sector_index is not None and not is_valid_number(sector_index,
                                        may_be_zero=True, is_integer=True):
            info = '%s (%s)' % (pos_label, sector_index)
            self.__invalid_sector_index.append(info)
            invalid = True

        stock_tube_barcode = parameter_map[
                                        self.PARAMETER_SET.STOCK_TUBE_BARCODE]
        if stock_tube_barcode is not None and len(stock_tube_barcode) < 2:
            info = '%s (%s)' % (pos_label, stock_tube_barcode)
            self.__invalid_tube_barcode.append(info)
            invalid = True
        stock_rack_barcode = parameter_map[
                                        self.PARAMETER_SET.STOCK_RACK_BARCODE]
        if stock_rack_barcode is not None and len(stock_rack_barcode) < 2:
            info = '%s (%s)' % (pos_label, stock_rack_barcode)
            self.__invalid_rack_barcode.append(info)
            invalid = True

        stock_rack_marker = parameter_map[self.PARAMETER_SET.STOCK_RACK_MARKER]
        if pos_type == MOCK_POSITION_TYPE or pos_type == LIBRARY_POSITION_TYPE:
            for val in (stock_tube_barcode, stock_rack_barcode,
                        stock_rack_marker):
                if not val is None:
                    self.__tube_data_not_allowed.append(pos_label)
                    invalid = True
                    break

        if invalid: return None
        kw['concentration'] = concentration
        kw['volume'] = volume
        kw['sector_index'] = sector_index
        kw['stock_tube_barcode'] = stock_tube_barcode
        kw['stock_rack_barcode'] = stock_rack_barcode
        kw['stock_rack_marker'] = stock_rack_marker
        return kw

    def _check_type_validity(self, pos_type, pool_id):
        """
        Floating position must either be missing strings or pools.
        """
        if pos_type == FLOATING_POSITION_TYPE:
            if pool_id == self.POSITION_CLS.MISSING_FLOATING:
                return True
            elif is_valid_number(pool_id, is_integer=True):
                return True
            else:
                self.__invalid_floating.add(pool_id)
                return False
        return TransferLayoutConverter._check_type_validity(self, pos_type,
                                                            pool_id)

    def _record_errors(self):
        """
        Records errors that have been collected for rack positions.
        """
        TransferLayoutConverter._record_errors(self)

        if len(self.__invalid_conc) > 0:
            msg = 'The concentration must be a positive number (or *None* ' \
                  'for mock positions). The following positions in the ' \
                  'layout have invalid concentrations: %s.' \
                   % (', '.join(self.__invalid_conc))
            self.add_error(msg)

        if len(self.__invalid_vol) > 0:
            msg = 'The volume must be a positive number. The following rack ' \
                  'positions have invalid volumes: %s.' % \
                  (', '.join(self.__invalid_vol))
            self.add_error(msg)

        if len(self.__invalid_floating) > 0:
            msg = 'Pools for floating positions for lab ISO plate must ' \
                  'either be a missing placeholder ("%s") or a pool ID. The ' \
                  'following floating position pools are invalid: %s.' \
                  % (self.POSITION_CLS.MISSING_FLOATING,
                     self._get_joined_str(self.__invalid_floating))
            self.add_error(msg)

        if len(self.__invalid_rack_barcode) > 0:
            msg = 'The stock rack barcode must be at least 2 characters long ' \
                  'if it is specified. The following positions ins the ' \
                  'layout have invalid stock rack barcodes: %s.' \
                  % (self._get_joined_str(self.__invalid_rack_barcode))
            self.add_error(msg)

        if len(self.__invalid_tube_barcode) > 0:
            msg = 'The stock tube barcode must be at least 2 characters long ' \
                  'if it is specified. The following positions ins the ' \
                  'layout have invalid stock tube barcodes: %s.' \
                  % (self._get_joined_str(self.__invalid_tube_barcode))
            self.add_error(msg)

        if len(self.__invalid_sector_index) > 0:
            msg = 'The sector index must be a non-negative integer or None. ' \
                  'The following positions in the layout have invalid sector ' \
                  'indices: %s.' \
                  % (self._get_joined_str(self.__invalid_sector_index))
            self.add_error(msg)

        if len(self.__transfer_target_not_allowed) > 0:
            msg = 'Library lab ISO position must not have transfer targets. ' \
                  'The following library positions violate this rule: %s.' \
                   % (self._get_joined_str(self.__transfer_target_not_allowed))
            self.add_error(msg)

        if len(self.__tube_data_not_allowed) > 0:
            msg = 'Mock and library ISO plate positions must not have stock ' \
                  'tube or rack data. The following positions violate this ' \
                  'rule: %s.' \
                  % (self._get_joined_str(self.__tube_data_not_allowed))
            self.add_error(msg)



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

        if from_job and not self.is_fixed:
            msg = 'Only fixed final lab ISO positions can be provided from ' \
                  'a job. This one is a %s type.' % (self.position_type)
            raise ValueError(msg)

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
                      'stock_tube_barcode', 'stock_rack_barcode',
                      'stock_rack_marker')
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

    def _add_class_specific_keywords(self, kw):
        kw['from_job'] = self.from_job

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
    POSITION_CLS = FinalLabIsoPosition


class FinalLabIsoLayoutConverter(LabIsoLayoutConverter):
    """
    Converts a :class:`RackLayout` into a :class:`FinalLabIsoLayout`.
    """
    NAME = 'ISO Final Plate Layout Converter'

    PARAMETER_SET = FinalLabIsoParameters
    LAYOUT_CLS = FinalLabIsoLayout
    POSITION_CLS = FinalLabIsoPosition

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
        self.__true_not_allowed = None

    def reset(self):
        LabIsoLayoutConverter.reset(self)
        self.__invalid_from_job = []
        self.__true_not_allowed = []

    def _get_position_init_values(self, parameter_map, rack_pos):
        kw = LabIsoLayoutConverter._get_position_init_values(self, parameter_map,
                                                             rack_pos)
        if kw is None: return None

        from_job_str = parameter_map[self.PARAMETER_SET.FROM_JOB]
        from_job = self._get_boolean_value(from_job_str, rack_pos.label,
                                           self.__invalid_from_job)
        if from_job is None: return None
        if from_job and not kw['position_type'] == FIXED_POSITION_TYPE:
            self.__true_not_allowed.append(rack_pos.label)
            return None

        kw['from_job'] = from_job
        return kw

    def _record_errors(self):
        LabIsoLayoutConverter._record_errors(self)
        self._record_invalid_boolean_error('from job', self.__invalid_from_job)

        if len(self.__true_not_allowed) > 0:
            msg = 'Only fixed position might originate from a job. The ' \
                  'following non-fixed positions violate this rule: %s.' \
                  % (self._get_joined_str(self.__true_not_allowed))
            self.add_error(msg)


class LabIsoPrepParameters(LabIsoParameters):
    """
    These parameters describe ISO preparation plate. In addition to normal
    ISO plates, these plates have transfer targets on a different plate
    (the final ISO plate).
    """

    DOMAIN = 'iso_prep_plate'

    ALLOWED_POSITION_TYPES = [FIXED_POSITION_TYPE, FLOATING_POSITION_TYPE,
                              EMPTY_POSITION_TYPE]

    #: The transfer targets *on the final ISO plate*.
    EXTERNAL_TRANSFER_TARGETS = 'external_targets'
    TRANSFER_TARGET_PARAMETERS = LabIsoParameters.TRANSFER_TARGET_PARAMETERS \
                                 + [EXTERNAL_TRANSFER_TARGETS]
    MUST_HAVE_TRANSFER_TARGETS = \
                            dict(LabIsoParameters.MUST_HAVE_TRANSFER_TARGETS,
                                 **{EXTERNAL_TRANSFER_TARGETS : True})

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
                                external_targets, 'external plate target')

    def _add_class_specific_keywords(self, kw):
        kw['external_targets'] = self.external_targets

    def _get_parameter_values_map(self):
        parameters = LabIsoPosition._get_parameter_values_map(self)
        parameters[self.PARAMETER_SET.EXTERNAL_TRANSFER_TARGETS] = \
                                                        self.external_targets
        return parameters

    def _get_transfer_target_map(self):
        return {self.PARAMETER_SET.TRANSFER_TARGETS : self.transfer_targets,
                self.PARAMETER_SET.EXTERNAL_TRANSFER_TARGETS : \
                        self.external_targets}


class LabIsoPrepLayout(LabIsoLayout):
    """
    Represents a lab ISO preparation plate.
    """
    POSITION_CLS = LabIsoPrepPosition


class LabIsoPrepLayoutConverter(LabIsoLayoutConverter):
    """
    Converts a :class:`RackLayout` into a :class:`LabIsoPrepLayout`.
    """
    NAME = 'ISO Preparation Plate Layout Converter'

    PARAMETER_SET = LabIsoPrepParameters
    LAYOUT_CLS = LabIsoPrepLayout
    POSITION_CLS = LabIsoPrepPosition

    def _get_position_init_values(self, parameter_map, rack_pos):
        kw = LabIsoLayoutConverter._get_position_init_values(self,
                                                     parameter_map, rack_pos)
        if kw is None: return kw

        ext_tt_tag_value = parameter_map[
                                self.PARAMETER_SET.EXTERNAL_TRANSFER_TARGETS]
        ext_tts = self._parse_target_tag_value(ext_tt_tag_value, rack_pos,
                                self.PARAMETER_SET.EXTERNAL_TRANSFER_TARGETS)
        if ext_tts is None: return None
        kw['external_targets'] = ext_tts
        return kw


class _InstructionsWriter(TxtWriter):
    """
    Writes a file with instructions about how to prepare the ISO or ISO job.

    **Return Value:** The instructions as stream (TXT)
    """
    #: The entity class supported by this summary writer.
    _ENTITY_CLS = None

    #: The main headline of the file.
    BASE_MAIN_HEADER = 'Processing Instructions for %s "%s"'
    #: To be filled into the :attr:`BASE_MAIN_HEADER` (ISO or ISO job).
    __ENTITY_CLS_NAME = {LabIso : 'ISO', IsoJob : 'ISO job'}

    #: Is used if :attr:`process_job_first` value of the ISO request is *True*.
    ORDER_JOB_FIRST = '''
    The ISO job must be processed before you start processing ISOs the
    specific ISOs.'''
    #: Is used if :attr:`process_job_first` value of the ISO request is *False*.
    ORDER_ISO_FIRST = '''
    ATTENTION! A part of ISOs has to processed before you can add the
    fixed samples (controls). Look at the steps for further instructions.'''
    #: Is used if there are no samples added via the ISO job.
    ORDER_NO_JOB = '''
    There is no job processing required for this ISO preparation.'''
    #: Is used if the final plate is a library plate to be completed.
    ORDER_NO_ISO = '''
    There is no ISO processing required for this ISO preparation.
    All required steps are performed via the job.'''

    #: The header marking the next step.
    STEPS_HEADER = 'Step %i:'
    #: Comprises the worklist name and some isntructions.
    STEPS_DETAILS = 'Worklist %s: %s'

    #: The header for the buffer dilution section.
    BUFFER_DILUTION_HEADER = 'Buffer Additions'
    #: Is used if there are not dilution worklists for the entity in the ISO
    #: request worklist series.
    BUFFER_NO_WORKLISTS = '''
    There are no buffer dilutions for this %s.'''

    #: The header for the stock transfer section.
    STOCK_TRANSFER_HEADER = 'Transfers from the Stock'
    #: The header for the processing section.
    PROCESSING_HEADER = 'Processing Steps (Other Transfers)'
    #: Is used if there are no further processing transfers for the entity
    #: in the ISO request worklist.
    PROCESSING_NO_WORKLIST = '''
    There are no further transfers required after the sample transfer from the
    stock (for the %s).'''

    #: The placeholder for final plates.
    FINAL_PLATE_PLACEHOLDER = 'final plate(s)'
    #: The header for the final plates section.
    FINAL_PLATES_HEADER = 'Final ISO Plates'

    def __init__(self, log, entity, iso_request, rack_containers):
        """
        Constructor:

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`

        :param entity: The ISO or the ISO job for which to generate the summary.
        :type entity: :class:`LabIso` or :class:`IsoJob`
            (see :attr:`_ENTITY_CLS).

        :param iso_request: The lab ISO request the job belongs to.
        :type iso_request: :class:`thelma.models.iso.LabIsoRequest`

        :param rack_containers: The :class:`IsoRackContainer` objects for all
            racks and plates involved in the processing of the entity.
        :type rack_containers: list of :class:`IsoRackContainer`
        """
        TxtWriter.__init__(self, log=log)

        #: The ISO or the ISO job for which to generate the summary.
        self.entity = entity
        #: The lab ISO request the job belongs to.
        self.iso_request = iso_request
        #: The :class:`IsoRackContainer` objects for all racks and plates
        #: involved in the processing of the entity.
        self.rack_containers = rack_containers

        #: The worklists in the ISO request worklist series ordered by index.
        self.__sorted_worklists = None

        #: Counts the steps.
        self.__step_counter = None
        #: The rack containers mapped onto rack markers - does not contain
        #: final ISO plates.
        self.__racks_by_markers = None

    def reset(self):
        TxtWriter.reset(self)
        self.__sorted_worklists = None
        self.__step_counter = 0
        self.__racks_by_markers = dict()

    def _check_input(self):
        self._check_input_class('entity', self.entity, self._ENTITY_CLS)
        self._check_input_class('ISO request', self.iso_request, LabIsoRequest)
        self._check_input_list_classes('rack container', self.rack_containers,
                                       IsoRackContainer)

    def _write_stream_content(self):
        """
        We start with an remark about the order of ISO and ISO job. The
        following sections deal with buffer transfers, stock transfers,
        processing steps and the involved final plates.
        """
        self.add_debug('Write stream content ...')

        self.__sort_racks_by_markers()

        self.__write_main_headline()
        self.__write_order()
        self.__write_dilution_section()
        self.__write_stock_rack_section()
        self.__write_processing_section()
        self.__write_final_plates_section()

    def __sort_racks_by_markers(self):
        """
        The maps serves the geenration of rack strings.
        Final plates are not included in map. They are indicated by the
        :attr:`FINAL_PLATE_PLACEHOLDER` instead.
        """
        for rack_container in self.rack_containers:
            if rack_container.role == LABELS.ROLE_FINAL: continue
            self.__racks_by_markers[rack_container.rack_marker] = rack_container

    def __write_main_headline(self):
        """
        Writes the main head line.
        """
        cls_name = self.__ENTITY_CLS_NAME[self._ENTITY_CLS]
        main_headline = self.BASE_MAIN_HEADER % (cls_name, self.entity.label)
        self._write_headline(main_headline, underline_char='=',
                             preceding_blank_lines=0, trailing_blank_lines=1)

    def __write_order(self):
        """
        Explain whether to start with the ISO or the ISO job.
        """
        if self.iso_request.molecule_design_library is not None:
            order_line = self.ORDER_NO_ISO
        elif not self._has_job_processing():
            order_line = self.ORDER_NO_JOB
        elif self.iso_request.process_job_first:
            order_line = self.ORDER_JOB_FIRST
        else:
            order_line = self.ORDER_ISO_FIRST
        self._write_body_lines(['', order_line])

    def _has_job_processing(self):
        """
        Are there sample added via the ISO job?
        """
        raise NotImplementedError('Abstract method.')

    def __write_dilution_section(self):
        """
        Lists the buffer dilution steps.
        """
        self._write_headline(self.BUFFER_DILUTION_HEADER)

        worklist_series = self.iso_request.worklist_series
        if worklist_series is None:
            self.__sorted_worklists = []
        else:
            self.__sorted_worklists = worklist_series.get_sorted_worklists()

        base_desc = 'Adding to buffer to plate %s.'
        worklist_labels = []
        descriptions = []
        for worklist in self.__sorted_worklists:
            if not worklist.transfer_type == TRANSFER_TYPES.SAMPLE_DILUTION:
                continue
            racks = self.__get_rack_strings_for_worklist(worklist.label)
            if racks is None: continue
            desc = base_desc % (racks[TRANSFER_ROLES.TARGET])
            descriptions.append(desc)
            worklist_labels.append(worklist.label)

        self.__write_optional_section(descriptions, worklist_labels,
                                      self.BUFFER_NO_WORKLISTS)

    def __write_stock_rack_section(self):
        """
        The stock rack section lists the stock transfers ordered by stock
        rack.
        """
        stock_racks = dict()
        for stock_rack in self._get_stock_racks():
            stock_racks[stock_rack.label] = stock_racks

        self._write_headline(self.STOCK_TRANSFER_HEADER)
        base_desc = 'Transfer of sample from stock rack %s to plate %s.'

        empty_worklist_series = []
        for label in sorted(stock_racks):
            stock_rack = stock_racks[label]
            worklist_series = stock_rack.worklist_series
            if len(worklist_series) < 1:
                empty_worklist_series.append(label)
                continue
            for worklist in worklist_series.get_sorted_worklists():
                worklist_label = worklist.label
                racks = self.__get_rack_strings_for_worklist(worklist_label)
                desc = base_desc % (racks[TRANSFER_ROLES.SOURCE],
                                    racks[TRANSFER_ROLES.TARGET])
                self.__write_step_section(worklist_label, desc)

    def _get_stock_racks(self):
        """
        Returns all stock racks for the entity or an empty list. Stock racks
        cannot be retrieved via the rack container maps because we need to
        access their worklist series.
        """
        raise NotImplementedError('Abstract method.')

    def __write_processing_section(self):
        """
        Describes the remaining processing steps (if there are any).
        """
        base_desc = 'Transferring samples from %s to %s%s'
        rack_sector_addition = ' (use CyBio).'
        sector_info = ' (sector: %i)'

        worklist_labels = []
        descriptions = []
        for worklist in self.__sorted_worklists:
            transfer_type = worklist.transfer_type
            if transfer_type == TRANSFER_TYPES.SAMPLE_DILUTION: continue
            racks = self._get_processing_worklist_plates(worklist)
            if racks is None: continue
            src_rack = racks[TRANSFER_ROLES.SOURCE]
            trg_rack = racks[TRANSFER_ROLES.TARGET]

            if transfer_type == TRANSFER_TYPES.RACK_SAMPLE_TRANSFER:
                for psrt in worklist:
                    src_str = src_rack + sector_info \
                              % (psrt.source_sector_index + 1)
                    trg_str = trg_rack + sector_info \
                              % (psrt.target_sector_index + 1)
                    desc = base_desc % (src_str, trg_str)
                    desc += rack_sector_addition
                    descriptions.append(desc)
                    worklist_labels.append(worklist.label)
            else:
                desc = base_desc % (src_rack, trg_rack)
                descriptions.append(desc)
                worklist_labels.append(worklist.label)

        self.__write_optional_section(descriptions, worklist_labels,
                                      self.PROCESSING_NO_WORKLIST)

    def _get_processing_worklist_plates(self, worklist):
        """
        Invokes :func:`__get_rack_strings_for_worklist`. However, even if
        all participating plates are known the worklist might not be accepted
        for this entity.
        """
        return self.__get_rack_strings_for_worklist(worklist.label)

    def __write_final_plates_section(self):
        """
        Lists all involved final plates
        """
        self._write_headline(self.FINAL_PLATES_HEADER)

        plate_map = dict()
        for rack_container in self.rack_containers:
            if not rack_container.role == LABELS.ROLE_FINAL: continue
            plate_map[rack_container.label] = rack_container

        plate_lines = ['']
        for label in sorted(plate_map.keys()):
            rack_container = plate_map[label]
            plate_line = self.__get_rack_string(rack_container=rack_container)
            plate_lines.append(plate_line)

        self._write_body_lines(plate_lines)

    def __get_rack_strings_for_worklist(self, worklist_label):
        """
        Helper function returning the rack string for a worklist (mapped
        onto :class:`TRANSFER_ROLES` values or *None* if a rack marker
        is unknown and not a final plate (final plates are replaced
        by the attr:`FINAL_PLATE_PLACEHOLDER`).
        """
        values = LABELS.parse_worklist_label(worklist_label)
        transfer_roles = {TRANSFER_ROLES.SOURCE : LABELS.MARKER_WORKLIST_SOURCE,
                          TRANSFER_ROLES.TARGET : LABELS.MARKER_WORKLIST_TARGET}
        racks = dict()
        for transfer_role, role_marker in transfer_roles.iteritems():
            if values.has_key(role_marker):
                rack_marker = values[role_marker]
                rack_str = self.__get_rack_string(rack_marker)
                if rack_str is None: return None
                racks[transfer_role] = rack_str
        raise racks

    def __get_rack_string(self, rack_marker=None, rack_container=None):
        """
        Helper function returning a string with the rack label and barcode
        (if there has been a container pass for this rack).
        Rack markers is for an final ISO plate the rack string is
        replaced by the :attr:`FINAL_PLATE_PLACEHOLDER`.
        """
        if rack_container is None:
            if not self.__racks_by_markers.has_key(rack_marker):
                values = LABELS.parse_rack_marker(rack_marker)
                role = values[LABELS.MARKER_RACK_ROLE]
                if role == LABELS.ROLE_FINAL:
                    return self.FINAL_PLATE_PLACEHOLDER
                else:
                    return None
            else:
                rack_container = self.__racks_by_markers[rack_marker]
        return '%s (%s)' % (rack_container.rack.barcode, rack_container.label)

    def __write_step_section(self, worklist_label, description):
        """
        Helper function writing a new step section. The step number is
        determine automatically.
        """
        self.__step_counter += 1
        step_header = self.STEPS_HEADER % (self.__step_counter)
        detail_line = self.STEPS_DETAILS % (worklist_label, description)
        step_lines = ['', step_header, detail_line]
        self._write_body_lines(step_lines)

    def __write_optional_section(self, descriptions, worklist_labels,
                                 no_worklists_template):
        """
        Helper method writing either the steps for a section or a no
        worklist remark.
        """
        if len(descriptions) < 1:
            lines = ['', no_worklists_template % self._ENTITY_CLS]
            self._write_body_lines(lines)
        else:
            for i in range(descriptions):
                self.__write_step_section(worklist_labels[i], descriptions[i])


class _LabIsoJobInstructionsWriter(_InstructionsWriter):
    """
    Writes a file with instructions about how to prepare the ISO job.

    **Return Value:** The instructions as stream (TXT)
    """
    NAME = 'Lab ISO Job Instructions Writer'

    _ENTITY_CLS = IsoJob

    def _has_job_processing(self):
        return (self.entity.number_stock_racks > 0)

    def _get_stock_racks(self):
        return self.entity.iso_job_stock_racks

    def _get_processing_worklist_plates(self, worklist):
        """
        There are no rack sample transfers in the job processing. Apart from
        that we can check wether the racks are known.
        """
        if worklist.transfer_type == TRANSFER_TYPES.RACK_SAMPLE_TRANSFER:
            return None
        return _InstructionsWriter._get_processing_worklist_plates(self,
                                                                   worklist)


class _LabIsoInstructionsWriter(_InstructionsWriter):
    """
    Writes a file with instructions about how to prepare a lab ISO job.

    **Return Value:** The instructions as stream (TXT)
    """
    NAME = 'Lab ISO Instructions Writer'

    _ENTITY_CLS = LabIso

    def _has_job_processing(self):
        return self.entity.iso_job.number_stock_racks

    def _get_stock_racks(self):
        return self.entity.iso_stock_racks + self.entity.iso_sector_stock_racks


def create_instructions_writer(log, entity, iso_request, rack_containers):
    """
    Factory method returning the :class:`_InstructionsWriter` for the passed
    entity.

    :param log: The log to write into.
    :type log: :class:`thelma.ThelmaLog`

    :param entity: The ISO or the ISO job for which to generate the summary.
    :type entity: :class:`LabIso` or :class:`IsoJob`
        (see :attr:`_ENTITY_CLS).

    :param iso_request: The lab ISO request the job belongs to.
    :type iso_request: :class:`thelma.models.iso.LabIsoRequest`

    :param rack_containers: The :class:`IsoRackContainer` objects for all
        racks and plates involved in the processing of the entity.
    :type rack_containers: list of :class:`IsoRackContainer`

    :raises TypeError: if the entity has an unexpected class.
    """

    if isinstance(entity, LabIso):
        writer_cls = _LabIsoInstructionsWriter
    elif isinstance(entity, IsoJob):
        writer_cls = _LabIsoJobInstructionsWriter
    else:
        msg = 'Unexpected entity class (%s). The entity must be a %s or a %s!' \
              % (entity.__class__.__name__, LabIso.__name__, IsoJob.__name__)
        raise TypeError(msg)

    kw = dict(log=log, entity=entity, iso_request=iso_request,
              rack_containers=rack_containers)
    return writer_cls(**kw)

