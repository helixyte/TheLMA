"""
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
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.automation.handlers.poolcreationset \
    import PoolCreationSetParserHandler
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.iso.poolcreation.base import VolumeCalculator
from thelma.automation.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_pipetting_specs_cybio
from thelma.automation.tools.semiconstants import get_positions_for_shape
from thelma.automation.tools.stock.base import STOCKMANAGEMENT_USER
from thelma.automation.tools.stock.base import get_default_stock_concentration
from thelma.automation.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import get_trimmed_string
from thelma.automation.tools.utils.base import is_valid_number
from thelma.models.iso import StockSampleCreationIsoRequest
from thelma.models.liquidtransfer import PlannedSampleDilution
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import WorklistSeries
from thelma.models.user import User

__docformat__ = 'reStructuredText en'

__all__ = ['StockSampleCreationIsoRequestGenerator',
           'StockSampleCreationWorklistGenerator']


class StockSampleCreationIsoRequestGenerator(BaseAutomationTool):
    """
    This tool creates an ISO request for a pool stock sample creation task
    (:class:`StockSampleCreationIsoRequest`).
    The input stream contains the molecule design data for the pools to be
    created. Furthermore the used needs to specify the volume and
    concentration for the stock samples and a label for the ISO request.

    The buffer worklist is created here as well.

    **Return Value:** :class:`thelma.models.iso.StockSampleCreationIsoRequest`
    """
    NAME = 'Stock Sample Creation ISO Request Generator'

    def __init__(self, iso_request_label, stream, requester, target_volume,
                 target_concentration, logging_level=None,
                 add_default_handlers=None):
        """
        Constructor:

        :param iso_request_label: Will be used as label of the
            ISO request and be part of worklist name.
        :type iso_request_label: :class:`str`

        :param stream: Excel file stream containing a sheet with the
            molecule design data.

        :param requester: This user will be the reporter and owner of the ISO
            trac tickets and requester for the ISO request. The owner of the
            request however, will be the stock management.
        :type requester: :class:`thelma.models.user.User`

        :param target_volume: The final volume for the new pool stock tubes
            in ul.
        :type target_volume: positive integer

        :param target_concentration: The final pool concentration for the new
            pool stock tubes in nM.
        :type target_concentration: positive integer

        :param logging_level: the desired minimum log level
        :type log_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: None

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """
        BaseAutomationTool.__init__(self, logging_level=logging_level,
                                    add_default_handlers=add_default_handlers,
                                    depending=False)

        #: The label for the ISO request and be part of buffer worklist name.
        self.iso_request_label = iso_request_label
        #: Excel file stream containing one sheet with the molecule design data.
        self.stream = stream
        #: This user will be owner and reporter of the ISO trac tickets.
        self.requester = requester
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
        BaseAutomationTool.reset(self)
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
        if not self.has_errors(): self.__get_pool_set()
        if not self.has_errors(): self._create_worklist_series()
        if not self.has_errors(): self.__determine_number_of_isos()
        if not self.has_errors():
            self.return_value = self.__create_iso_request()
            self.add_info('ISO request generation completed.')

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self._check_input_class('ISO request label', self.iso_request_label,
                                basestring)
        self._check_input_class('requester', self.requester, User)
        numbers = {self.target_volume : 'target volume for the pool tubes',
                   self.target_concentration :
                        'target concentration for the pool tubes'}
        for value, name in numbers.iteritems():
            if not is_valid_number(value=value, is_integer=True):
                msg = 'The %s must be a positive number (obtained: %s).' \
                      % (name, value)
                self.add_error(msg)

    def __get_pool_set(self):
        """
        Also sets the stock concentration.
        """
        self.add_debug('Obtain pool set ...')

        handler = PoolCreationSetParserHandler(log=self.log,
                                               stream=self.stream)
        self.__pool_set = handler.get_result()

        if self.__pool_set is None:
            msg = 'Unable to parse pool set!'
            self.add_error(msg)
        else:
            self.__number_designs = handler.get_number_designs()
            mt = handler.get_molecule_type()
            # In theory we could check the default stock concentrations for
            # of the single molecule designs. However, for this we would have to
            # fetch the corresponding pools first. Since the handler already
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

        volume_calculator = VolumeCalculator(target_volume=self.target_volume,
                             target_concentration=self.target_concentration,
                             number_designs=self.__number_designs,
                             stock_concentration=self.__stock_concentration)


        generator = StockSampleCreationWorklistGenerator(log=self.log,
                          volume_calculator=volume_calculator,
                          iso_request_label=self.iso_request_label)
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
                      'step size: 0.1 ul). The target volume will be increased ' \
                      'from %s ul to %s ul. Do you want to proceed?' \
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

        stock_vol = self.target_volume / VOLUME_CONVERSION_FACTOR
        stock_conc = self.target_concentration / CONCENTRATION_CONVERSION_FACTOR

        iso_request = StockSampleCreationIsoRequest(
                    label=self.iso_request_label,
                    stock_volume=stock_vol,
                    stock_concentration=stock_conc,
                    number_designs=self.__number_designs,
                    requester=self.requester,
                    owner=STOCKMANAGEMENT_USER,
                    expected_number_isos=self.__expected_number_isos,
                    number_aliquots=0,
                    molecule_design_pool_set=self.__pool_set,
                    worklist_series=self.__worklist_series)

        return iso_request


class StockSampleCreationWorklistGenerator(BaseAutomationTool):
    """
    Creates the worklist series containing the worklists involved in pool
    stock sample creation. This comprises only one worklist which deals with
    the addition of buffer to the future pool stock tubes. The tool will
    create planned sample dilutions for all positions of a 8x12 rack shape.

    **Return Value:**  worklist series
        (:class:`thelma.models.liquidtransfer.WorklistSeries`).
    """

    NAME = 'Pool Creation Worklist Generator'

    #: Name pattern for the worklists that adds annealing buffer to the pool
    #: stock racks. The placeholders will contain the plate set label of
    #: the ISO request.
    BUFFER_WORKLIST_LABEL = '%s_stock_buffer'

    #: The index for the buffer worklist within the series.
    BUFFER_WORKLIST_INDEX = 0

    #: The dilution info for the buffer worklists.
    DILUENT_INFO = 'annealing buffer'

    def __init__(self, log, volume_calculator, iso_request_label):
        """
        Constructor:

        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`

        :param volume_calculator: Determines transfer and dilution volumes
            for pool stock sample ISO requests.
        :type volume_calculator: :class:`VolumeCalculator`

        :param number_designs: The number of single molecule designs for
            each pool.
        :type number_designs: positive integer

        :param target_volume: The final volume for the new pool stock tubes
            in ul.
        :type target_volume: positive integer

        :param target_concentration: The final pool concentration for the new
            pool stock tubes in nM.
        :type target_concentration: positive integer

        :param iso_request_label: The plate set label of the ISO request to be
            created - will be used as part of the worklist name.
        :type iso_request_label: :class:`str`
        """
        BaseAutomationTool.__init__(self, log=log)

        #: The plate set label of the ISO request to be created - will be used
        #: as part of the worklist name.
        self.iso_request_label = iso_request_label
        #: The :class:`VolumeCalculator` determines transfer and buffer volumes
        #: and might also adjust the target volume for the ISO request.
        self.volume_calculator = volume_calculator

        #: The worklist series for the ISO request.
        self.__worklist_series = None

    def reset(self):
        BaseAutomationTool.reset(self)
        self.__worklist_series = WorklistSeries()

    def run(self):
        self.reset()
        self.add_info('Start worklist series generation ...')
        self.__check_input()
        if not self.has_errors(): self.__create_transfers()
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
        """
        Creates a :class:`PlannedContainerDilution` for each rack position
        in a 8x12 rack shape.
        """
        self.add_debug('Create transfers ...')

        self._run_and_record_error(self.volume_calculator.calculate,
                            'Error when trying to determine buffer volume: ',
                            ValueError)
        buffer_volume = self.volume_calculator.get_buffer_volume()
        if buffer_volume is not None:
            volume = buffer_volume / VOLUME_CONVERSION_FACTOR
            wl_label = self.BUFFER_WORKLIST_LABEL % (self.iso_request_label)
            wl = PlannedWorklist(label=wl_label,
                                 transfer_type=TRANSFER_TYPES.SAMPLE_DILUTION)
            for rack_pos in get_positions_for_shape(RACK_SHAPE_NAMES.SHAPE_96):
                psd = PlannedSampleDilution(volume=volume,
                      target_position=rack_pos, diluent_info=self.DILUENT_INFO)
                wl.planned_liquid_transfers.append(psd)
            self.__worklist_series.add_worklist(self.BUFFER_WORKLIST_INDEX, wl)
