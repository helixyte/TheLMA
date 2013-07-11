#"""
#The classes in this module serve the creation of an ISO for a library creation
#process.
#
#:Note: The ISOs are already created externally, because they need a ticket ID.
#    The tool actually populates an empty ISO (instead of creating a new one).
#
#The following tasks need to be performed:
#
# * pick molecule design pools
# * create a preparation layout (= library layout)
# * create preparation plate
# * create aliquot plate
# * create ISO sample stock rack for each quadrant (barcodes are provided)
#
#IMPORTANT: Instead of calculating the stock take out volume from known numbers
#    we pass it as argument due to the current state of the DB (which we do not
#    want to change anymore for the plinius milestone). Remove the
#    argument in future milestones!
#
#AAB
#"""
#from thelma.automation.tools.base import BaseAutomationTool
#from thelma.automation.tools.semiconstants import get_positions_for_shape
#from thelma.automation.tools.libcreation.base \
#    import LibraryBaseLayoutConverter
#from thelma.automation.tools.libcreation.base import LibraryLayout
#from thelma.automation.tools.libcreation.base import LibraryPosition
#from thelma.automation.tools.libcreation.optimizer \
#    import LibraryCreationTubePicker
#from thelma.automation.tools.poolcreation.base \
#    import calculate_single_design_stock_transfer_volume_for_library
#from thelma.automation.tools.stock.base import get_default_stock_concentration
#from thelma.automation.tools.utils.base import is_valid_number
#from thelma.models.iso import ISO_STATUS
#from thelma.models.library import MoleculeDesignLibrary
#import logging
#
#__docformat__ = 'reStructuredText en'
#
#__all__ = ['PoolCreationIsoPopulator']
#
#
#class PoolCreationIsoPopulator(BaseAutomationTool):
#    """
#    Populates an empty pool creation ISO for a pool stock sample ISO request.
#    The data is stored in the rack layout of the ISO.
#
#    **Return Value:** The newly populated ISOs.
#    """
#    NAME = 'Pool Creation ISO Populator'
#
#    def __init__(self, pool_creation_library, number_isos,
#                 excluded_racks=None, requested_tubes=None,
#                 logging_level=logging.WARNING, add_default_handlers=False):
#        """
#        Constructor:
#
#        :param pool_creation_library: The pool creation library for which to
#            populate the ISO.
#        :type pool_creation_library:
#            :class:`thelma.models.library.MoleculeDesignLibrary`
#
#        :param number_isos: The number of ISOs ordered.
#        :type number_isos: :class:`int`
#
#        :param excluded_racks: A list of barcodes from stock racks that shall
#            not be used for stock sample picking.
#        :type excluded_racks: A list of rack barcodes
#
#        :param requested_tubes: A list of barcodes from stock tubes that are
#            supposed to be used.
#        :type requested_tubes: A list of tube barcodes.
#
#        :param logging_level: the desired minimum log level
#        :type log_level: :class:`int` (or logging_level as
#                         imported from :mod:`logging`)
#        :default logging_level: logging.WARNING
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
#        #: The pool creation library for which to populate the ISO.
#        self.pool_creation_library = pool_creation_library
#        #: The number of ISOs ordered.
#        self.number_isos = number_isos
#
#        #: A list of barcodes from stock racks that shall not be used for
#        #: stock sample (molecule design pool) picking.
#        self.excluded_racks = excluded_racks
#        if excluded_racks is None: self.excluded_racks = []
#
#        if requested_tubes is None: requested_tubes = []
#        #: A list of barcodes from stock tubes that are supposed to be used
#        #: (for fixed positions).
#        self.requested_tubes = requested_tubes
#
#        #: The ISO request defines the ISO layout
#        #: (:class:`thelma.models.iso.IsoRequest`)
#        self._iso_request = None
#        #: The molecule type must be the same for all pools.
#        self._molecule_type = None
#        #: The library pools for which to pick tubes.
#        self._queued_pools = None
#        #: The stock concentration for the single designs the new pools will
#        #: consist of (the concentration depends on the molecule type).
#        self.__single_design_stock_concentration = None
#
#        #: The base layout defines which positions might be taken by library
#        #: positions. This is the base layout for the 384-well plate.
#        self.__base_layout = None
#
#        #: The library candidates returned by the optimiser.
#        self._library_candidates = None
#
#        #: The library layouts mapped onto layout numbers.
#        self._library_layouts = None
#
#        #: The picked empty ISOs to populate.
#        self.__picked_isos = None
#
#        #: The newly populated ISOs.
#        self.__new_isos = None
#
#    def reset(self):
#        BaseAutomationTool.reset(self)
#        self._molecule_type = None
#        self._queued_pools = []
#        self.__single_design_stock_concentration = None
#        self.__base_layout = None
#        self._library_candidates = None
#        self._library_layouts = []
#        self.__picked_isos = []
#        self.__new_isos = []
#
#    def run(self):
#        """
#        Creates the requested number of ISO.
#        """
#        self.reset()
#        self.add_info('Start ISO generation ...')
#
#        self._check_input()
#        if not self.has_errors(): self.__get_library_metadata()
#        if not self.has_errors(): self.__get_base_layout()
#        if not self.has_errors(): self.__pick_library_candidates()
#        if not self.has_errors(): self._distribute_candidates()
#        if not self.has_errors(): self.__pick_isos()
#        if not self.has_errors(): self.__populate_isos()
#        if not self.has_errors():
#            self.return_value = self.__new_isos
#            self.add_info('ISO generation completed.')
#
#    def _check_input(self):
#        """
#        Checks the initialisation values.
#        """
#        self.add_debug('Check initialisation values ...')
#
#        self._check_input_class('pool creation library',
#                            self.pool_creation_library, MoleculeDesignLibrary)
#
#        if not is_valid_number(self.number_isos, is_integer=True):
#            msg = 'The number of ISOs order must be a positive integer ' \
#                  '(obtained: %s).' % (self.number_isos)
#            self.add_error(msg)
#
#        if self._check_input_class('excluded racks list',
#                                       self.excluded_racks, list):
#            for excl_rack in self.excluded_racks:
#                if not self._check_input_class('excluded rack barcode',
#                                               excl_rack, basestring): break
#
#        if self._check_input_class('requested tubes list',
#                                       self.requested_tubes, list):
#            for req_tube in self.requested_tubes:
#                if not self._check_input_class('requested tube barcode',
#                                               req_tube, basestring): break
#
#    def __get_library_metadata(self):
#        """
#        Determines the ISO request, the library pools for which to pick
#        source tubes, the worklist series and the stock concentration.
#        """
#        self._iso_request = self.pool_creation_library.iso_request
#        if self._iso_request is None:
#            msg = 'There is no ISO request for this library!'
#            self.add_error(msg)
#
#        else:
#            self._find_queued_pools()
#            if not self.has_errors():
#                self.__single_design_stock_concentration = \
#                            get_default_stock_concentration(self._molecule_type)
#
#    def _find_queued_pools(self):
#        """
#        All molecule design pools from the ISO request that are not part
#        of an ISO yet, are used. Cancelled ISOs are ignored.
#        """
#        used_pools = set()
#        for iso in self._iso_request.isos:
#            if iso.status == ISO_STATUS.CANCELLED:
#                continue
#            if iso.molecule_design_pool_set is None:
#                continue
#            used_pools.update(
#                        iso.molecule_design_pool_set.molecule_design_pools)
#
#        pool_set = self.pool_creation_library.molecule_design_pool_set
#        self._molecule_type = pool_set.molecule_type
#        self._queued_pools = \
#                pool_set.molecule_design_pools.difference(used_pools)
#        if len(self._queued_pools) < 1:
#            msg = 'There are no unused molecule design pools left!'
#            self.add_error(msg)
#
#    def __get_base_layout(self):
#        """
#        The base layout defines which positions might be taken by library
#        positions.
#        """
#        self.add_debug('Fetch base layout ...')
#
#        converter = LibraryBaseLayoutConverter(log=self.log,
#                                    rack_layout=self._iso_request.iso_layout)
#        self.__base_layout = converter.get_result()
#
#        if self.__base_layout is None:
#            msg = 'Error when trying to fetch library base layout.'
#            self.add_error(msg)
#
#    def __pick_library_candidates(self):
#        """
#        Runs the library optimizer. The optimizer returns a list of
#        :class:`LibraryCandidate` objects (in order of the optimizing
#        completion).
#        """
#        take_out_volume = self.__calculate_take_out_volume()
#
#        if not take_out_volume is None:
#            optimizer = LibraryCreationTubePicker(log=self.log,
#                molecule_design_pools=self._queued_pools,
#                stock_concentration=self.__single_design_stock_concentration,
#                take_out_volume=take_out_volume,
#                excluded_racks=self.excluded_racks,
#                requested_tubes=self.requested_tubes)
#            self._library_candidates = optimizer.get_result()
#
#            if self._library_candidates is None:
#                msg = 'Error when trying to pick tubes.'
#                self.add_error(msg)
#
#    def __calculate_take_out_volume(self):
#        """
#        Determines the volume to be taken from the stock for each single
#        molecule design.
#        """
#        try:
#            volume = calculate_single_design_stock_transfer_volume_for_library(
#                    pool_creation_library=self.pool_creation_library,
#                    single_design_stock_concentration=\
#                                self.__single_design_stock_concentration)
#        except ValueError as e:
#            msg = 'Unable to determine stock transfer volume: %s' % (e)
#            self.add_error(msg)
#            return None
#        else:
#            return volume
#
#    def _distribute_candidates(self):
#        """
#        Creates a :class:`LibraryLayout` for each ISO.
#        Positions are populated row-wise.
#        """
#        self.add_info('Distribute candidates ...')
#
#        not_enough_candidates = False
#        for i in range(self.number_isos): #pylint: disable=W0612
#            if len(self._library_candidates) < 1: break
#            lib_layout = LibraryLayout.from_base_layout(self.__base_layout)
#
#            for rack_pos in get_positions_for_shape(lib_layout.shape,
#                                                    vertical_sorting=True):
#                if len(self._library_candidates) < 1:
#                    not_enough_candidates = True
#                    break
#                lib_cand = self._library_candidates.pop(0)
#                lib_pos = LibraryPosition(pool=lib_cand.pool,
#                              rack_position=rack_pos,
#                              stock_tube_barcodes=lib_cand.get_tube_barcodes())
#                lib_layout.add_position(lib_pos)
#
#            if len(lib_layout) < 1:
#                break
#            else:
#                self._library_layouts.append(lib_layout)
#
#        if not_enough_candidates:
#            msg = 'There is not enough candidates left to populate all ' \
#                  'positions for the requested number of ISOs. Number ' \
#                  'of generated ISOs: %i.' % (len(self._library_layouts))
#            self.add_warning(msg)
#
#    def __pick_isos(self):
#        """
#        Only ISOs with empty rack layouts can be picked.
#        """
#        iso_map = dict()
#        used_layout_numbers = set()
#        for iso in self._iso_request.isos:
#            if len(iso.rack_layout.tagged_rack_position_sets) > 0:
#                used_layout_numbers.add(iso.layout_number)
#            iso_map[iso.layout_number] = iso
#
#        number_layouts = self._iso_request.number_plates
#        for i in range(number_layouts):
#            if not (i + 1) in used_layout_numbers:
#                iso = iso_map[i + 1]
#                self.__picked_isos.append(iso)
#            if len(self.__picked_isos) == len(self._library_layouts): break
#
#    def __populate_isos(self):
#        """
#        Adds molecule design set, library layout and plates to the picked ISOs.
#        """
#        self.add_debug('Create ISOs ...')
#
#        while len(self.__picked_isos) > 0:
#            lci = self.__picked_isos.pop(0)
#            library_layout = self._library_layouts.pop(0)
#            lci.rack_layout = library_layout.create_rack_layout()
#            lci.molecule_design_pool_set = \
#                        library_layout.get_pool_set(self._molecule_type)
#            self.__new_isos.append(lci)
