"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

The classes in this module serve the creation of an ISO request for a
pool stock sample generation process.

The ISO request requires a set of molecule design pools to be included and
the stock volume and concentration to be generated.
The worklist for preparation of the new stock tube (buffer dilutions) are
generated here as well. These worklist do not include transfers from existing
stock tubes. These worklists are kept with the stock racks for the single
molecule designs (:class:`IsoSectorStockRack`s of the resulting ISOs).

AAB
"""
from math import ceil
from tractor import create_wrapper_for_ticket_creation
from tractor.ticket import SEVERITY_ATTRIBUTE_VALUES
from tractor.ticket import TYPE_ATTRIBUTE_VALUES
from xmlrpclib import Fault
from xmlrpclib import ProtocolError

from thelma.tools.handlers.poolcreationset \
    import PoolCreationSetParserHandler
from thelma.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.tools.semiconstants import get_96_rack_shape
from thelma.tools.semiconstants import get_pipetting_specs_cybio
from thelma.tools.semiconstants import get_positions_for_shape
from thelma.tools.base import BaseTool
from thelma.tools.iso.poolcreation.base import \
    DEFAULT_PREPARATION_PLATE_VOLUME
from thelma.tools.iso.poolcreation.base import DILUENT_INFO
from thelma.tools.iso.poolcreation.base import LABELS
from thelma.tools.iso.poolcreation.base import VolumeCalculator
from thelma.tools.stock.base import STOCKMANAGEMENT_USER
from thelma.tools.stock.base import get_default_stock_concentration
from thelma.tools.tracbase import BaseTracTool
from thelma.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.tools.utils.base import get_trimmed_string
from thelma.tools.utils.base import is_valid_number
from thelma.entities.iso import StockSampleCreationIso
from thelma.entities.iso import StockSampleCreationIsoRequest
from thelma.entities.liquidtransfer import PlannedSampleDilution
from thelma.entities.liquidtransfer import PlannedWorklist
from thelma.entities.liquidtransfer import TRANSFER_TYPES
from thelma.entities.liquidtransfer import WorklistSeries
from thelma.entities.racklayout import RackLayout
from thelma.entities.user import User


__docformat__ = 'reStructuredText en'
__all__ = ['StockSampleCreationIsoRequestGenerator',
           'StockSampleCreationWorklistGenerator',
           'StockSampleCreationTicketGenerator',
           'StockSampleCreationIsoGenerator'
           ]


class StockSampleCreationIsoRequestGenerator(BaseTool):
    """
    This tool creates an ISO request for a pool stock sample creation task
    (:class:`StockSampleCreationIsoRequest`).
    The input stream contains the molecule design data for the pools to be
    created. Furthermore the used needs to specify the volume and
    concentration for the stock samples and a label for the ISO request.

    The buffer worklist is created here as well.

    **Return Value:** :class:`thelma.entities.iso.StockSampleCreationIsoRequest`
    """
    NAME = 'Stock Sample Creation ISO Request Generator'

    def __init__(self, iso_request_label, stream, target_volume,
                 target_concentration, parent=None):
        """
        Constructor.

        :param str iso_request_label: Will be used as label of the
            ISO request and be part of worklist name.
        :param stream: Excel file stream containing a sheet with the
            molecule design data.
        :param int target_volume: The final volume for the new pool stock
            tubes in ul (positive number).
        :param int target_concentration: The final pool concentration for
            the new pool stock tubes in nM (positive number).
        """
        BaseTool.__init__(self, parent=parent)
        #: The label for the ISO request and be part of buffer worklist name.
        self.iso_request_label = iso_request_label
        #: Excel file stream containing one sheet with the molecule design data.
        self.stream = stream
        #: The final volume for the new pool stock tubes in ul.
        self.target_volume = target_volume
        #: The final pool concentration for the new pool stock tubes in nM.
        self.target_concentration = target_concentration
        #: The pool set containing the stock sample pools for the ISO request.
        self.__pool_set = None
        #: The number of single designs in a pool must be the same for all
        #: pools.
        self.__number_designs = None
        #: The default stock concentration for the single molecule designs.
        self.__stock_concentration = None
        #: The target volume might need to be adjusted due to pipetting
        #: constraints to maintain the target concentration.
        self.__adj_target_volume = None
        #: The worklist series (generated by the
        #: :class:`PoolCreationWorklistGenerator`).
        self.__worklist_series = None
        #: The number of ISOs depends on the number of pools to be generated
        #: and the number of available positions.
        self.__expected_number_isos = None

    def reset(self):
        BaseTool.reset(self)
        self.__pool_set = None
        self.__number_designs = None
        self.__stock_concentration = None
        self.__adj_target_volume = None
        self.__worklist_series = None
        self.__expected_number_isos = None

    def run(self):
        self.reset()
        self.add_info('Start pool creation ISO request generation ...')

        self.__check_input()
        if not self.has_errors():
            self.__get_pool_set()
        if not self.has_errors():
            self._create_worklist_series()
        if not self.has_errors():
            self.__determine_number_of_isos()
        if not self.has_errors():
            self.return_value = self.__create_iso_request()
            self.add_info('ISO request generation completed.')

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self._check_input_class('ISO request label', self.iso_request_label,
                                basestring)
        numbers = {self.target_volume : 'target volume for the pool tubes',
                   self.target_concentration :
                        'target concentration for the pool tubes'}
        for value, name in numbers.iteritems():
            if not is_valid_number(value=value, is_integer=True):
                msg = 'The %s must be a positive number (obtained: %s).' \
                      % (name, value)
                self.add_error(msg)

    def __get_pool_set(self):
        # Also sets the stock concentration.
        self.add_debug('Obtain pool set ...')
        handler = PoolCreationSetParserHandler(self.stream, parent=self)
        self.__pool_set = handler.get_result()
        if self.__pool_set is None:
            msg = 'Unable to parse pool set!'
            self.add_error(msg)
        else:
            self.__number_designs = handler.get_number_designs()
            mt = handler.get_molecule_type()
            # In theory we could check the default stock concentrations for
            # all the single molecule designs. However, for this we would have
            # to get the corresponding pools first. Since the handler already
            # made sure that we have equal molecule types and also the number
            # of designs (1) is always equal it is very unlikely to stumble
            # across a different concentration. Even so, the optimizer would
            # not find proper stock samples for these designs.
            self.__stock_concentration = get_default_stock_concentration(mt)

    def _create_worklist_series(self):
        """
        Generates all the buffer dilution worklists (as series).
        The worklists for the transfer from 1-molecule-design stock rack to
        pool stock rack are not included but stored at the ISO sample
        stock racks to enable quadrant tracking.
        """
        self.add_debug('Create worklist series ...')

        volume_calculator = \
          VolumeCalculator(self.target_volume, self.target_concentration,
                           self.__number_designs, self.__stock_concentration)
        generator = StockSampleCreationWorklistGenerator(
                                    volume_calculator, self.iso_request_label,
                                    parent=self)
        self.__worklist_series = generator.get_result()
        if self.__worklist_series is None:
            msg = 'Error when trying to generate worklist series.'
            self.add_error(msg)
        else:
            self.__adj_target_volume = \
                                volume_calculator.get_adjusted_target_volume()
            if not self.__adj_target_volume is None:
                robot_specs = get_pipetting_specs_cybio()
                msg = 'The target volume you have requested needs to be ' \
                      'increased slightly because of the constraints of the ' \
                      'pipetting robot (%s, min. transfer volume: %s ul, ' \
                      'step size: 0.1 ul). The target volume will be ' \
                      'increased from %s ul to %s ul.' \
                      % (robot_specs.name,
                         get_trimmed_string(robot_specs.min_transfer_volume \
                                            * VOLUME_CONVERSION_FACTOR),
                         get_trimmed_string(self.target_volume),
                         get_trimmed_string(self.__adj_target_volume))
                self.add_warning(msg)

    def __determine_number_of_isos(self):
        """
        The number of plates depends on the number of pools to be generated
        and the number of available positions in a plates.
        """
        number_members = len(self.__pool_set)
        number_positions = self._get_number_of_avaible_positions()
        expected_number_isos = ceil(float(number_members) / number_positions)
        self.__expected_number_isos = int(expected_number_isos)

    def _get_number_of_avaible_positions(self):
        """
        Returns the number of positions available for the new pools in the
        final stock rack or plate.
        """
        return len(get_96_rack_shape())

    def __create_iso_request(self):
        """
        The actual ISO request is created here.
        """
        self.add_debug('Create ISO request ...')
        vol = self.target_volume
        if self.__adj_target_volume is not None:
            vol = self.__adj_target_volume
        stock_vol = vol / VOLUME_CONVERSION_FACTOR
        stock_conc = self.target_concentration \
                        / CONCENTRATION_CONVERSION_FACTOR
        iso_request = StockSampleCreationIsoRequest(
                            self.iso_request_label,
                            stock_vol,
                            stock_conc,
                            DEFAULT_PREPARATION_PLATE_VOLUME,
                            self.__number_designs,
                            owner=STOCKMANAGEMENT_USER,
                            expected_number_isos=self.__expected_number_isos,
                            number_aliquots=0,
                            molecule_design_pool_set=self.__pool_set,
                            worklist_series=self.__worklist_series)
        return iso_request


class StockSampleCreationWorklistGenerator(BaseTool):
    """
    Creates the worklist series containing the worklists involved in pool
    stock sample creation. This comprises only one worklist which deals with
    the addition of buffer to the future pool stock tubes. The tool will
    create planned sample dilutions for all positions of a 8x12 rack shape.

    **Return Value:**  worklist series
        (:class:`thelma.entities.liquidtransfer.WorklistSeries`).
    """
    NAME = 'Pool Creation Worklist Generator'
    #: The index for the buffer worklist within the series.
    BUFFER_WORKLIST_INDEX = 0

    def __init__(self, volume_calculator, iso_request_label, parent=None):
        """
        Constructor.

        :param volume_calculator: Determines transfer and dilution volumes
            for pool stock sample ISO requests.
        :type volume_calculator: :class:`VolumeCalculator`
        :param int number_designs: The number of single molecule designs for
            each pool (positive number).
        :param int target_volume: The final volume for the new pool stock
            tubes in ul (positive number).
        :param int target_concentration: The final pool concentration for the
            new pool stock tubes in nM (positive number).
        :param str iso_request_label: The plate set label of the ISO request
            to be created - will be used as part of the worklist name.
        """
        BaseTool.__init__(self, parent=parent)
        #: The plate set label of the ISO request to be created - will be used
        #: as part of the worklist name.
        self.iso_request_label = iso_request_label
        #: The :class:`VolumeCalculator` determines transfer and buffer volumes
        #: and might also adjust the target volume for the ISO request.
        self.volume_calculator = volume_calculator
        #: The worklist series for the ISO request.
        self.__worklist_series = None

    def reset(self):
        BaseTool.reset(self)
        self.__worklist_series = WorklistSeries()

    def run(self):
        self.reset()
        self.add_info('Start worklist series generation ...')
        self.__check_input()
        if not self.has_errors():
            self.__create_transfers()
        if not self.has_errors():
            self.return_value = self.__worklist_series
            self.add_info('Worklist series generation completed.')

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input ...')

        self._check_input_class('volume calculator', self.volume_calculator,
                                VolumeCalculator)
        self._check_input_class('ISO request label', self.iso_request_label,
                                basestring)

    def __create_transfers(self):
        # Creates a :class:`PlannedSampleDilution` for each rack position
        # in a 8x12 rack shape.
        self.add_debug('Create transfers ...')
        self._run_and_record_error(self.volume_calculator.calculate,
                            'Error when trying to determine buffer volume: ',
                            ValueError)
        buffer_volume = self.volume_calculator.get_buffer_volume()
        if buffer_volume is not None:
            volume = buffer_volume / VOLUME_CONVERSION_FACTOR
            wl_label = LABELS.create_buffer_worklist_label(
                                                    self.iso_request_label)
            wl = PlannedWorklist(wl_label,
                                 TRANSFER_TYPES.SAMPLE_DILUTION,
                                 get_pipetting_specs_cybio())
            for rack_pos in get_positions_for_shape(RACK_SHAPE_NAMES.SHAPE_96):
                psd = PlannedSampleDilution.get_entity(volume=volume,
                      target_position=rack_pos, diluent_info=DILUENT_INFO)
                wl.planned_liquid_transfers.append(psd)
            self.__worklist_series.add_worklist(self.BUFFER_WORKLIST_INDEX, wl)


class StockSampleCreationTicketGenerator(BaseTracTool):
    """
    Creates a pool stock sample creation trac ticket for a new ISO.

    **Return Value:** ticket ID
    """
    NAME = 'Pool Creation Ticket Creator'
    #: The value for the ticket summary (title). The placeholder will contain
    #: the ISO label.
    SUMMARY = 'Pool Stock Sample Creation ISO (%s)'
    #: The description for the empty ticket.
    DESCRIPTION_TEMPLATE = "Autogenerated ticket for pool creation ISO " \
                           "'''%s'''.\n\nLayout number: %i\n\n"
    #: The value for ticket type.
    TYPE = TYPE_ATTRIBUTE_VALUES.TASK
    #: The value for the ticket's severity.
    SEVERITY = SEVERITY_ATTRIBUTE_VALUES.NORMAL
    #: The value for the ticket cc.
    CC = STOCKMANAGEMENT_USER
    #: The value for the ticket's component.
    COMPONENT = 'Logistics'

    def __init__(self, requester, iso_label, layout_number, parent=None):
        """
        Constructor.

        :param requester: The user who will be owner and reporter of the ticket.
        :type requester: :class:`thelma.entities.user.User`
        :param str iso_label: The label of the ISO this ticket belongs to.
        :param int layout_number: References the serial number ID of the ISO
            (within the ISO request space).
        """
        BaseTracTool.__init__(self, parent=parent)
        #: The user who will be owner and reporter of the ticket (corresponds
        #: the requester of the ISO request).
        self.requester = requester
        #: The label of the ISO this ticket belongs to.
        self.iso_label = iso_label
        #: References the library layout the ISO is created for.
        self.layout_number = layout_number
        #: The ticket wrapper storing the value applied to the ticket.
        self._ticket = None

    def reset(self):
        BaseTracTool.reset(self)
        self._ticket = None

    def get_ticket_id(self):
        """
        Sends a request and returns the ticket ID generated by the trac.
        """
        self.run()
        return self.return_value

    def run(self):
        self.reset()
        self.add_info('Create ISO request ticket ...')
        self.__check_input()
        if not self.has_errors():
            self.__create_ticket_wrapper()
        if not self.has_errors():
            self.__submit_request()

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input ...')
        self._check_input_class('requester', self.requester, User)
        self._check_input_class('ISO label', self.iso_label, basestring)
        self._check_input_class('layout number', self.layout_number, int)

    def __create_ticket_wrapper(self):
        """
        Creates the ticket wrapper to be sent.
        """
        self.add_debug('Create ticket wrapper ...')
        description = self.DESCRIPTION_TEMPLATE % (self.iso_label,
                                                   self.layout_number)
        summary = self.SUMMARY % self.iso_label
        self._ticket = create_wrapper_for_ticket_creation(
                                summary=summary,
                                description=description,
                                reporter=self.requester.directory_user_id,
                                owner=self.requester.directory_user_id,
                                component=self.COMPONENT,
                                cc=self.CC,
                                type=self.TYPE,
                                severity=self.SEVERITY)

    def __submit_request(self):
        # Submits the request to the trac.
        self.add_debug('Send request ...')
        try:
            ticket_id = self.tractor_api.create_ticket(notify=self.NOTIFY,
                                                ticket_wrapper=self._ticket)
        except ProtocolError, err:
            self.add_error(err.errmsg)
        except Fault, fault:
            msg = 'Fault %s: %s' % (fault.faultCode, fault.faultString)
            self.add_error(msg)
        else:
            self.return_value = ticket_id
            self.add_info('Ticket created (ID: %i).' % (ticket_id))
            self.was_successful = True


class StockSampleCreationIsoGenerator(BaseTool):
    """
    Creates ticket and ISOs for a pool stock sample creation ISO request.
    This step is not involved in ISO request generation because ISO generation
    might involve the generation of Trac tickets.

    Before running the tool will check whether there are already ISOs for
    this ISO request. The tool will create the remaining ISOs (using the
    number of plates in the ISO request as target number).

    IMPORTANT: This tool must not launch warnings or be interrupted, otherwise
        some or all tickets will be created multiple times.

    **Return Value:** The updated ISO request (incl. ISOs).
    """
    NAME = 'Stock Sample Generation ISO Creator'
    TICKET_GENERATOR_CLASS = StockSampleCreationTicketGenerator

    def __init__(self, iso_request, ticket_numbers=None, reporter=None,
                 parent=None):
        """
        Constructor.

        :param iso_request: The ISO request for which to generate the ISOs.
        :type iso_request:
            :class:`thelma.entities.iso.StockSampleGenerationIsoRequest`
        :param ticket_numbers: The user might specify ticket numbers for the
            ISO tickets. The number of ticket number must either be 1 (in
            which case all ISOs get the same ticket number) or equal to the
            number of ISOs. If there is no ticket number specified, the
            tool will generate new tickets for each ISO.
            Attention: It is not checked whether these given tickets exist!
        :type ticket_numbers: :class:`list` of `int`
        :default ticket_numbers: *None*
        :param reporter: This user will become reporter of the tickets (if
            new tickets are created). If you do not want to create tickets,
            the user might be *None*.
        :type reporter: :class:`thelma.entities.user.User`
        :default reporter: *None*
        """
        BaseTool.__init__(self, parent=parent)
        self.iso_request = iso_request
        self.ticket_numbers = ticket_numbers
        self.reporter = reporter
        #: The number of ISOs created (for checking reasons).
        self.__new_iso_counter = None

    def reset(self):
        BaseTool.reset(self)
        self.__new_iso_counter = 0

    def run(self):
        """
        Creates tickets and ISOs.
        """
        self.reset()
        self.add_info('Start ISO generation ...')
        self.__check_input()
        if not self.has_errors():
            self.__check_counts_and_numbers()
        if not self.has_errors():
            self.__create_isos()
        if not self.has_errors():
            self.return_value = self.iso_request
            self.add_info('%i ISOs have been created.' \
                           % (self.__new_iso_counter))

    def __check_input(self):
        self._check_input_class('ISO request', self.iso_request,
                                StockSampleCreationIsoRequest)
        if self.ticket_numbers is None:
            if not isinstance(self.reporter, User):
                msg = 'If you do not specify ticket numbers, you have to ' \
                      'provide a reporter for the ISO tickets! The reporter ' \
                      'must be %s object!' % (User.__name__)
                self.add_error(msg)
        else:
            if self._check_input_list_classes('ticket number',
                               self.ticket_numbers, int, may_be_empty=True):
                if len(self.ticket_numbers) == 0:
                    self.ticket_numbers = None

    def __check_counts_and_numbers(self):
        # The number of specified ticket IDs (if there are any) must either
        # be one or equal to the number of remaining ISOs. Usually the number
        # of remaining ISOs should be equal to the number of ISOs in total.
        # It only differs if for some reason, ISOs have been created before
        # externally.
        exp_num_isos = self.iso_request.expected_number_isos
        iso_count = len(self.iso_request.isos)
        if iso_count >= exp_num_isos:
            msg = 'The ISOs have already been created.'
            self.add_error(msg)
        remaining_isos = exp_num_isos - iso_count
        if not self.has_errors() and not self.ticket_numbers is None:
            if not len(self.ticket_numbers) in (1, remaining_isos):
                msg = 'You must specify either 1 ticket number (in which ' \
                      'case all ISOs will get the same ticket number) or ' \
                      'one for each ISO to generate (%i). You specified ' \
                      '%i numbers: %s.' \
                       % (remaining_isos, len(self.ticket_numbers),
                          ' ,'.join((str(nr) for nr in self.ticket_numbers)))
                self.add_error(msg)

    def __create_isos(self):
        # Creates the ISOs. At this the tool checks whether there are already
        # ISOs at the ISO request. The tool add ISOs until the number of plates
        # (ISO request attribute) is reached.
        self.add_debug('Create ISOs ...')
        current_iso_count = len(self.iso_request.isos)
        new_iso_count = self.iso_request.expected_number_isos
        for i in range(current_iso_count, new_iso_count):
            layout_number = i + 1
            iso_label = LABELS.create_iso_label(self.iso_request.label,
                                                layout_number)
            ticket_number = self.__get_ticket_number(iso_label, layout_number)
            if ticket_number is None:
                break
            # FIXME: Using side effect of instantiation.
            StockSampleCreationIso(iso_label,
                                   self.iso_request.number_designs,
                                   RackLayout(shape=get_96_rack_shape()),
                                   ticket_number,
                                   layout_number,
                                   iso_request=self.iso_request)
            self.__new_iso_counter += 1

    def __get_ticket_number(self, iso_label, layout_number):
        # If there are ticket numbers specified by the user, one of these
        # numbers is returned. Otherwise a new ticket will be created.
        if self.ticket_numbers is None:
            ticket_creator = self.TICKET_GENERATOR_CLASS(
                                self.reporter, iso_label, layout_number,
                                parent=self)
            ticket_number = ticket_creator.get_ticket_id()
            if ticket_number is None:
                msg = 'Error when trying to generate ISO "%s".' % (iso_label)
                self.add_error(msg)
                result = None
            else:
                result = ticket_number
        elif len(self.ticket_numbers) == 1:
            result = self.ticket_numbers[0]
        else:
            result = self.ticket_numbers.pop(0)
        return result
