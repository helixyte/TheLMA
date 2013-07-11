#"""
#The classes in this module serve the creation of an ISO request for a
#pool creation process.
#
#The ISO request requires a base layout (all position of a 8x12 rack shape) and
#a number of molecule design pools to be included. Furthermore the user needs
#to specify the desired volume and concentration for the new stock tubes.
#
#
#The worklists for the samples
#transfers a created here as well.
#
#
#AAB
#"""
#from math import ceil
#from thelma.automation.handlers.poolcreationset \
#    import PoolCreationSetParserHandler
#from thelma.automation.tools.base import BaseAutomationTool
#from thelma.automation.tools.libcreation.base import LibraryBaseLayout
#from thelma.automation.tools.libcreation.base import LibraryBaseLayoutPosition
#from thelma.automation.tools.poolcreation.base \
#    import calculate_single_design_stock_transfer_volume
#from thelma.automation.tools.semiconstants import PIPETTING_SPECS_NAMES
#from thelma.automation.tools.semiconstants import RACK_SHAPE_NAMES
#from thelma.automation.tools.semiconstants import get_96_rack_shape
#from thelma.automation.tools.semiconstants import get_min_transfer_volume
#from thelma.automation.tools.semiconstants import get_positions_for_shape
#from thelma.automation.tools.stock.base import STOCKMANAGEMENT_USER
#from thelma.automation.tools.stock.base import get_default_stock_concentration
#from thelma.automation.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
#from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
#from thelma.automation.tools.utils.base import get_trimmed_string
#from thelma.automation.tools.utils.base import is_valid_number
#from thelma.automation.tools.utils.base import round_up
#from thelma.models.iso import ISO_TYPES
#from thelma.models.iso import IsoRequest
#from thelma.models.library import MoleculeDesignLibrary
#from thelma.models.liquidtransfer import PlannedContainerDilution
#from thelma.models.liquidtransfer import PlannedWorklist
#from thelma.models.liquidtransfer import WorklistSeries
#from thelma.models.user import User
#
##: TODO: find more appropriate names (library, pool creation ...)
##: at the moment this is fast implementation due to lack of time
#
#__docformat__ = 'reStructuredText en'
#
#__all__ = ['PoolCreationLibraryGenerator',
#           'PoolCreationWorklistGenerator']
#
#
#class PoolCreationLibraryGenerator(BaseAutomationTool):
#    """
#    This tool creates an ISO request for a pool stock sample creation task.
#    The input stream contains the molecule design data for the pools to be
#    created. Furthermore the used needs to specify the volume and
#    concentration for the stock samples and a label for the ISO request.
#
#    The buffer worklist is created here as well.
#
#    **Return Value:** :class:`thelma.models.library.MoleculeDesignLibrary`
#    """
#    NAME = 'Pool Creation ISO Request Generator'
#
#    def __init__(self, iso_request_label, stream, requester, target_volume,
#                 target_concentration, logging_level=None,
#                 add_default_handlers=None):
#        """
#        Constructor:
#
#        :param iso_request_label: Will be used as plate set label of the
#            ISO request (regard that there are no plates involved!) and be
#            part of worklist name.
#        :type iso_request_label: :class:`str`
#
#        :param stream: Excel file stream containing a sheet with the
#            molecule design data.
#
#        :param requester: This user will be owner and reporter of the ISO
#            trac tickets.
#        :type requester: :class:`thelma.models.user.User`
#
#        :param target_volume: The final volume for the new pool stock tubes
#            in ul.
#        :type target_volume: positive integer
#
#        :param target_concentration: The final pool concentration for the new
#            pool stock tubes in nM.
#        :type target_concentration: positive integer
#
#        :param logging_level: the desired minimum log level
#        :type log_level: :class:`int` (or logging_level as
#                         imported from :mod:`logging`)
#        :default logging_level: None
#
#        :param add_default_handlers: If *True* the log will automatically add
#            the default handler upon instantiation.
#        :type add_default_handlers: :class:`boolean`
#        :default add_default_handlers: *False*
#        """
#        BaseAutomationTool.__init__(self, logging_level=logging_level,
#                                    add_default_handlers=add_default_handlers,
#                                    depending=False)
#
#        #: Will be used as plate set label of the ISO request and be part of
#        #: buffer worklist name.
#        self.iso_request_label = iso_request_label
#        #: Excel file stream containing one sheet with the molecule design data.
#        self.stream = stream
#        #: This user will be owner and reporter of the ISO trac tickets.
#        self.requester = requester
#        #: The final volume for the new pool stock tubes in ul.
#        self.target_volume = target_volume
#        #: The final pool concentration for the new pool stock tubes in nM.
#        self.target_concentration = target_concentration
#
#        #: The pool set containing the stock sample pools for the ISO request.
#        self.__pool_set = None
#        #: The number of single designs in a pool must be the same for all
#        #: pools.
#        self.__number_designs = None
#        #: The default stock concentration for the single molecule designs.
#        self.__stock_concentration = None
#
#        #: The base layout for the ISO request contains all positions of a
#        #: 8x12 rack shape.
#        self.__base_layout = None
#
#        #: The worklist series (generated by the
#        #: :class:`PoolCreationWorklistGenerator`).
#        self.__worklist_series = None
#        #: The number of plates (ISOs) depends on the number of pools in the
#        #: molecule design set.
#        self.__number_plates = None
#
#    def reset(self):
#        BaseAutomationTool.reset(self)
#        self.__pool_set = None
#        self.__number_designs = None
#        self.__stock_concentration = None
#        self.__base_layout = None
#        self.__worklist_series = None
#        self.__number_plates = None
#
#    def run(self):
#        self.reset()
#        self.add_info('Start pool creation ISO request generation ...')
#
#        self.__check_input()
#        if not self.has_errors():
#            self.__get_pool_set()
#            self.__create_base_layout()
#        if not self.has_errors(): self.__create_worklist_series()
#        if not self.has_errors(): self.__determine_number_of_plates()
#        if not self.has_errors():
#            self.return_value = self.__create_pool_creation_library()
#            self.add_info('ISO request generation completed.')
#
#    def __check_input(self):
#        """
#        Checks the initialisation values.
#        """
#        self._check_input_class('ISO request label', self.iso_request_label,
#                                basestring)
#        self._check_input_class('requester', self.requester, User)
#        numbers = {self.target_volume : 'target volume for the pool tubes',
#                   self.target_concentration :
#                        'target concentration for the pool tubes'}
#        for value, name in numbers.iteritems():
#            if not is_valid_number(value=value, is_integer=True):
#                msg = 'The %s must be a positive number (obtained: %s).' \
#                      % (name, value)
#                self.add_error(msg)
#
#    def __get_pool_set(self):
#        """
#        Also sets the stock concentration.
#        """
#        self.add_debug('Obtain pool set ...')
#
#        handler = PoolCreationSetParserHandler(log=self.log,
#                                               stream=self.stream)
#        self.__pool_set = handler.get_result()
#
#        if self.__pool_set is None:
#            msg = 'Unable to parse pool set!'
#            self.add_error(msg)
#        else:
#            self.__number_designs = handler.get_number_designs()
#            mt = handler.get_molecule_type()
#            # In theory we could check the default stock concentrations for
#            # of the single molecule designs. However, for this we would have to
#            # fetch the corresponding pools first. Since the handler already
#            # made sure that we have equal molecule types and also the number
#            # of designs (1) is always equal it is very unlikely to stumble
#            # across a different concentration. Even so, the optimizer would
#            # not find proper stock samples for these designs.
#            self.__stock_concentration = get_default_stock_concentration(mt)
#
#    def __create_base_layout(self):
#        """
#        The base layout for the ISO request contains all positions of a
#        8x12 rack shape.
#        """
#        shape = get_96_rack_shape()
#        self.__base_layout = LibraryBaseLayout(shape=shape)
#        for rack_pos in get_positions_for_shape(shape):
#            base_pos = LibraryBaseLayoutPosition(rack_position=rack_pos)
#            self.__base_layout.add_position(base_pos)
#
#    def __create_worklist_series(self):
#        """
#        Generates all the buffer dilution worklists (as series).
#        The worklists for the transfer from 1-molecule-design stock rack to
#        pool stock rack. These worklists will be stored at the ISO sample
#        stock racks to enable quadrant tracking.
#        """
#        self.add_debug('Create worklist series ...')
#
#        generator = PoolCreationWorklistGenerator(log=self.log,
#                          stock_concentration=self.__stock_concentration,
#                          number_designs=self.__number_designs,
#                          target_volume=self.target_volume,
#                          target_concentration=self.target_concentration,
#                          iso_request_label=self.iso_request_label)
#        self.__worklist_series = generator.get_result()
#
#        if self.__worklist_series is None:
#            msg = 'Error when trying to generate worklist series.'
#            self.add_error(msg)
#
#    def __determine_number_of_plates(self):
#        """
#        The number of plates depends on the number of pools.
#        """
#        number_members = len(self.__pool_set)
#        number_positions = 96
#        number_plates = ceil(float(number_members) / number_positions)
#        self.__number_plates = int(number_plates)
#
#    def __create_pool_creation_library(self):
#        """
#        The actual ISO request is created here.
#        """
#        self.add_debug('Create ISO request ...')
#
#        iso_request = IsoRequest(
#                    iso_layout=self.__base_layout.create_rack_layout(),
#                    requester=self.requester,
#                    owner=STOCKMANAGEMENT_USER,
#                    number_plates=self.__number_plates,
#                    number_aliquots=1, # TODO:should be 0 but requires DB change
#                    plate_set_label=self.iso_request_label,
#                    worklist_series=self.__worklist_series,
#                    iso_type=ISO_TYPES.LIBRARY_CREATION)
#
#        library = MoleculeDesignLibrary(label=self.iso_request_label,
#                    molecule_design_pool_set=self.__pool_set,
#                    iso_request=iso_request,
#                    final_volume=self.target_volume / VOLUME_CONVERSION_FACTOR,
#                    final_concentration=self.target_concentration \
#                                        / CONCENTRATION_CONVERSION_FACTOR)
#
#        return library
#
#
#class PoolCreationWorklistGenerator(BaseAutomationTool):
#    """
#    Creates the worklist series containing the worklists involved in pool
#    creation. This comprises only one worklist which deals with the addition
#    of buffer to the future pool stock tubes. The tool will create planned
#    transfers for all positions of a 8x12 rack shape.
#
#    **Return Value:**  worklist series
#        (:class:`thelma.models.liquidtransfer.WorklistSeries`).
#    """
#
#    NAME = 'Pool Creation Worklist Generator'
#
#    #: Name pattern for the worklists that adds annealing buffer to the pool
#    #: stock racks. The placeholders will contain the plate set label of
#    #: the ISO request.
#    BUFFER_WORKLIST_LABEL = '%s_stock_buffer'
#
#    #: The index for the buffer worklist within the series.
#    BUFFER_WORKLIST_INDEX = 0
#
#    #: The dilution info for the buffer worklists.
#    DILUENT_INFO = 'annealing buffer'
#
#    def __init__(self, log, stock_concentration, number_designs, target_volume,
#                 target_concentration, iso_request_label):
#        """
#        Constructor:
#
#        :param log: The ThelmaLog you want to write in. If the
#            log is None, the object will create a new log.
#        :type log: :class:`thelma.ThelmaLog`
#
#        :param stock_concentration: The concentration of the single source
#            molecule designs in the stock in nM.
#        :type stock_concentration: positive number
#
#        :param number_designs: The number of single molecule designs for
#            each pool.
#        :type number_designs: positive integer
#
#        :param target_volume: The final volume for the new pool stock tubes
#            in ul.
#        :type target_volume: positive integer
#
#        :param target_concentration: The final pool concentration for the new
#            pool stock tubes in nM.
#        :type target_concentration: positive integer
#
#        :param iso_request_label: The plate set label of the ISO request to be
#            created - will be used as part of the worklist name.
#        :type iso_request_label: :class:`str`
#        """
#        BaseAutomationTool.__init__(self, log=log)
#
#        #: The concentration of the single source molecule designs in the
#        #: stock in nM.
#        self.stock_concentration = stock_concentration
#        #: The number of single molecule designs for each pool.
#        self.number_designs = number_designs
#        #: The final volume for the new pool stock tubes in ul.
#        self.target_volume = target_volume
#        #: The final pool concentration for the new pool stock tubes in nM.
#        self.target_concentration = target_concentration
#        #: The plate set label of the ISO request to be created - will be used
#        #: as part of the worklist name.
#        self.iso_request_label = iso_request_label
#
#        #: The worklist series for the ISO request.
#        self.__worklist_series = None
#
#    def reset(self):
#        BaseAutomationTool.reset(self)
#        self.__worklist_series = WorklistSeries()
#
#    def run(self):
#        self.reset()
#        self.add_info('Start worklist series generation ...')
#        self.__check_input()
#        if not self.has_errors(): self.__create_transfers()
#        if not self.has_errors():
#            self.return_value = self.__worklist_series
#            self.add_info('Worklist series generation completed.')
#
#    def __check_input(self):
#        """
#        Checks the initialisation values.
#        """
#        self.add_debug('Check input ...')
#
#        self._check_input_class('ISO request label', self.iso_request_label,
#                                basestring)
#        numbers = {self.stock_concentration :
#                        'stock concentration for the single source molecules',
#                   self.number_designs : 'number of designs per pool',
#                   self.target_volume : 'target volume for the pool tubes',
#                   self.target_concentration :
#                        'target concentration for the pool tubes'}
#        for value, name in numbers.iteritems():
#            if not is_valid_number(value=value, is_integer=True):
#                msg = 'The %s must be a positive number (obtained: %s).' \
#                      % (name, value)
#                self.add_error(msg)
#
#    def __create_transfers(self):
#        """
#        Creates a :class:`PlannedContainerDilution` for each rack position
#        in a 8x12 rack shape.
#        """
#        self.add_debug('Create transfers ...')
#
#        buffer_volume = self.__determine_buffer_volume()
#        if buffer_volume is not None:
#            volume = buffer_volume / VOLUME_CONVERSION_FACTOR
#            wl_label = self.BUFFER_WORKLIST_LABEL % (self.iso_request_label)
#            wl = PlannedWorklist(label=wl_label)
#            for rack_pos in get_positions_for_shape(RACK_SHAPE_NAMES.SHAPE_96):
#                pcd = PlannedContainerDilution(volume=volume,
#                                               target_position=rack_pos,
#                                               diluent_info=self.DILUENT_INFO)
#                wl.planned_transfers.append(pcd)
#            self.__worklist_series.add_worklist(self.BUFFER_WORKLIST_INDEX, wl)
#
#    def __determine_buffer_volume(self):
#        """
#        The buffer volume depends on the number of designs, the stock
#        concentration for single designs and the target volume and
#        concentration. Each volume to be transfer must meet the minimum
#        transfer volume requirements of the CyBio.
#        """
#        try:
#            stock_transfer_volume = \
#                      calculate_single_design_stock_transfer_volume(
#                      target_volume=self.target_volume,
#                      target_concentration=self.target_concentration,
#                      number_designs=self.number_designs,
#                      stock_concentration=self.stock_concentration)
#        except ValueError as e:
#            self.add_error(e)
#            return None
#
#        min_cybio_transfer_vol = get_min_transfer_volume(
#                                                    PIPETTING_SPECS_NAMES.CYBIO)
#        total_transfer_volume = stock_transfer_volume * self.number_designs
#        buffer_volume = self.target_volume - total_transfer_volume
#        if (buffer_volume < 0.01 and buffer_volume > 0):
#            return None
#        elif buffer_volume < min_cybio_transfer_vol:
#            corr_factor = min_cybio_transfer_vol / buffer_volume
#            target_single_conc = float(self.target_concentration) \
#                                 / self.number_designs
#            dil_factor = self.stock_concentration / target_single_conc
#            adj_transfer_vol = stock_transfer_volume * corr_factor
#            adj_target_volume = (self.number_designs * adj_transfer_vol) \
#                                * dil_factor
#            msg = 'The target volume you have requested (%i ul) is too low ' \
#                  'for the required dilution since the CyBio cannot pipet ' \
#                  'less than %.1f ul per transfer (with the current values ' \
#                  'it would need to pipet %s ul buffer). Please increase the ' \
#                  'target volume to %i ul or lower the target concentration.' \
#                  % (self.target_volume, min_cybio_transfer_vol,
#                     get_trimmed_string(buffer_volume),
#                     round_up(adj_target_volume, 0))
#            self.add_error(msg)
#            return None
#
#        return buffer_volume
