"""
The classes in this module provides ISOs for ISO jobs in stock sample
creation ISO requests.

:Note: The ISOs are already created externally, because they need a ticket ID.
    The tool actually populates an empty ISO (instead of creating a new one).

The following tasks need to be performed:

 * pick molecule design pools
 * creation of a preparation layout (= stock sample creation layout)

AAB
"""
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.iso.jobcreator import IsoProvider
from thelma.automation.tools.iso.jobcreator import IsoJobCreator
from thelma.automation.tools.iso.poolcreation.base \
    import StockSampleCreationLayout
from thelma.automation.tools.iso.poolcreation.base \
    import StockSampleCreationPosition
from thelma.automation.tools.iso.poolcreation.base import VolumeCalculator
from thelma.automation.tools.iso.poolcreation.optimizer \
    import StockSampleCreationTubePicker
from thelma.automation.tools.semiconstants import get_positions_for_shape
from thelma.automation.tools.stock.base import get_default_stock_concentration
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import ISO_TYPES
from thelma.models.iso import StockSampleCreationIso

__docformat__ = 'reStructuredText en'

__all__ = ['StockSampleCreationIsoJobCreator',
           'StockSampleCreationIsoPopulator',
           'StockSampleCreationIsoResetter']


class StockSampleCreationIsoJobCreator(IsoJobCreator):
    """
    ISO job creator for stock samples creation ISOs.

    **Return Value:** :class:`thelma.models.job.IsoJob` with all populated ISOs
    """

    _ISO_TYPE = ISO_TYPES.STOCK_SAMPLE_GENERATION

    def _get_isos(self):
        """
        Creates or populates the request number of ISOs (depending on the
        ISO type).
        """
        kw = self._get_iso_provider_keywords()
        provider = StockSampleCreationIsoPopulator(**kw)
        self._isos = provider.get_result()
        if self._isos is None:
            msg = 'Error when trying to fetch ISOs!'
            self.add_error(msg)


class StockSampleCreationIsoPopulator(IsoProvider):
    """
    Populates an empty pool creation ISO for a pool stock sample ISO request.
    The data is stored in the rack layout of the ISO.

    **Return Value:** The newly populated ISOs.
    """
    NAME = 'Stock Sample Creation ISO Populator'

    _ISO_TYPE = ISO_TYPES.STOCK_SAMPLE_GENERATION

    def __init__(self, log, iso_request, number_isos,
                 excluded_racks=None, requested_tubes=None):
        """
        Constructor:

        :param log: The log to record events.
        :type log: :class:`thelma.ThelmaLog`

        :param stock_sample_creation_iso_request: The stock sample creation
            ISO request for which to populate the ISO.
        :type stock_sample_creation_iso_request:
            :class:`thelma.models.iso.StockSampleCreationIsoRequest`

        :param number_isos: The number of ISOs ordered.
        :type number_isos: :class:`int`

        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for stock sample picking.
        :type excluded_racks: A list of rack barcodes

        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of tube barcodes.

        :param logging_level: the desired minimum log level
        :type log_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: None

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *None*
        """
        IsoProvider.__init__(self, log=log, iso_request=iso_request,
                             number_isos=number_isos,
                             excluded_racks=excluded_racks,
                             requested_tubes=requested_tubes)

        #: The molecule type must be the same for all pools.
        self._molecule_type = None
        #: The pools to be generated for which to pick tubes.
        self._queued_pools = None
        #: The stock concentration for the single designs the new pools will
        #: consist of (the concentration depends on the molecule type).
        self.__single_design_stock_concentration = None

        #: The pool candidates returned by the optimiser.
        self._pool_candidates = None

        #: The stock sample creation layouts mapped onto layout numbers.
        self._ssc_layouts = None

        #: The picked empty ISOs to populate.
        self.__picked_isos = None

        #: The ISOs that have been populated in this run.
        self.__populated_isos = None

    def reset(self):
        IsoProvider.reset(self)
        self._molecule_type = None
        self._queued_pools = []
        self.__single_design_stock_concentration = None
        self._pool_candidates = None
        self._ssc_layouts = []
        self.__picked_isos = []
        self.__populated_isos = []

    def _collect_iso_data(self):
        if not self.has_errors(): self._find_queued_pools()
        if not self.has_errors(): self.__pick_pool_candidates()
        if not self.has_errors(): self._distribute_candidates()
        if not self.has_errors(): self.__pick_isos()
        if not self.has_errors(): self.__populate_isos()
        if not self.has_errors(): self.return_value = self.__populated_isos

    def _find_queued_pools(self):
        """
        Finds the pools to be created that are still in the queue and
        determines stock concentration for single design pools.
        All molecule design pools from the ISO request that are not part
        of an ISO yet, are used. Cancelled ISOs are ignored.
        """
        used_pools = set()
        for iso in self.iso_request.isos:
            if iso.status == ISO_STATUS.CANCELLED:
                continue
            if iso.molecule_design_pool_set is None:
                continue
            used_pools.update(
                        iso.molecule_design_pool_set.molecule_design_pools)

        pool_set = self.iso_request.molecule_design_pool_set
        self._molecule_type = pool_set.molecule_type
        self._queued_pools = \
                pool_set.molecule_design_pools.difference(used_pools)

        if len(self._queued_pools) < 1:
            msg = 'There are no unused molecule design pools left!'
            self.add_error(msg)
        else:
            self.__single_design_stock_concentration = \
                        get_default_stock_concentration(self._molecule_type)

    def __pick_pool_candidates(self):
        """
        Runs the optimizer which finds stock tube for the single molecule
        designs. The optimizer returns a list of :class:`PoolCandidate`
        objects (in order of the optimizing completion).
        """
        volume_calculator = VolumeCalculator.from_iso_request(self.iso_request)
        self._run_and_record_error(volume_calculator.calculate,
                   base_msg='Unable to determine stock transfer volume: ',
                   error_type=ValueError)
        if not self.has_errors():
            take_out_volume = volume_calculator.\
                              get_single_design_stock_transfer_volume()
            optimizer = StockSampleCreationTubePicker(log=self.log,
                    molecule_design_pools=self._queued_pools,
                    single_design_concentration=\
                                    self.__single_design_stock_concentration,
                    take_out_volume=take_out_volume,
                    excluded_racks=self.excluded_racks,
                    requested_tubes=self.requested_tubes)
            self._pool_candidates = optimizer.get_result()

            if self._pool_candidates is None:
                msg = 'Error when trying to pick tubes.'
                self.add_error(msg)

    def _distribute_candidates(self):
        """
        Creates a :class:`StockSampleCreationLayout` for each ISO.
        Positions are populated row-wise.
        """
        self.add_info('Distribute candidates ...')

        not_enough_candidates = False
        for i in range(self.number_isos): #pylint: disable=W0612
            if len(self._pool_candidates) < 1: break
            ssc_layout = StockSampleCreationLayout()
            for rack_pos in get_positions_for_shape(ssc_layout.shape,
                                                    vertical_sorting=True):
                if len(self._pool_candidates) < 1:
                    not_enough_candidates = True
                    break
                pool_cand = self._pool_candidates.pop(0)
                ssc_pos = StockSampleCreationPosition(pool=pool_cand.pool,
                              rack_position=rack_pos,
                              stock_tube_barcodes=pool_cand.get_tube_barcodes())
                ssc_layout.add_position(ssc_pos)

            if len(ssc_layout) < 1:
                break
            else:
                self._ssc_layouts.append(ssc_layout)

        if not_enough_candidates:
            msg = 'There is not enough candidates left to populate all ' \
                  'positions for the requested number of ISOs. Number ' \
                  'of generated ISOs: %i.' % (len(self._ssc_layouts))
            self.add_warning(msg)

    def __pick_isos(self):
        """
        Only ISOs with empty rack layouts can be picked.
        """
        iso_map = dict()
        used_layout_numbers = set()
        for iso in self.iso_request.isos:
            if len(iso.rack_layout.tagged_rack_position_sets) > 0:
                used_layout_numbers.add(iso.layout_number)
            iso_map[iso.layout_number] = iso

        number_layouts = self.iso_request.expected_number_isos
        for i in range(number_layouts):
            if not (i + 1) in used_layout_numbers:
                iso = iso_map[i + 1]
                self.__picked_isos.append(iso)
            if len(self.__picked_isos) == len(self._ssc_layouts): break

    def __populate_isos(self):
        """
        Adds molecule design pool set and layout to the picked ISOs.
        """
        self.add_debug('Create ISOs ...')

        while len(self.__picked_isos) > 0:
            iso = self.__picked_isos.pop(0)
            ssc_layout = self._ssc_layouts.pop(0)
            iso.rack_layout = ssc_layout.create_rack_layout()
            iso.molecule_design_pool_set = \
                        ssc_layout.get_pool_set(self._molecule_type)
            self.__populated_isos.append(iso)


class StockSampleCreationIsoResetter(BaseAutomationTool):
    """
    Resets a list of stock sample creation ISOs so that the pools that are
    scheduled for these ISOs are put back into queue (as long as there are
    no other non-cancelled ISOs dealing with these pools). An ISO can only
    be reset as long it is not completed (or cancelled).
    Resetting might be required for instance if there is a longer period
    gone between optimization and tube picking and the actual physical
    start of the processing.

    Technically, we empty the rack layout and remove the molecule design pool
    set for the ISO.

    **Return Value:** The update ISOs.
    """
    NAME = 'Stock Sample Creation ISO Resetter'

    def __init__(self, isos,
                 logging_level=None, add_default_handlers=False):
        """
        Constructor:

        :param isos: The ISOs to be reset.
        :type isos: :class:`list` of :class:`StockSampleCreationIso`s

        :param logging_level: the desired minimum log level
        :type log_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: None

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *None*
        """
        BaseAutomationTool.__init__(self, logging_level=logging_level,
                                    add_default_handlers=add_default_handlers)

        #: The ISOs to be reset.
        self.isos = isos

    def run(self):
        self.reset()
        self.add_info('Start ISO reset ...')

        self.__check_input()
        if not self.has_errors():
            for iso in self.isos:
                iso.molecule_design_pool_set = None
                iso.rack_layout.tagged_rack_position_sets = []
            self.return_value = self.isos
            self.add_info('ISO reset completed.')

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        invalid_status = (ISO_STATUS.CANCELLED, ISO_STATUS.DONE)
        invalid_isos = []

        if self._check_input_class('ISO list', self.isos, list):
            for iso in self.isos:
                if not self._check_input_class('ISO', iso,
                                               StockSampleCreationIso): break
                if iso.status in invalid_status:
                    invalid_isos.append(iso.label)

        if len(invalid_isos) > 0:
            msg = 'The following ISOs cannot be reset because there are ' \
                  'either completed or cancelled: %s.' \
                  % (', '.join(sorted(invalid_isos)))
            self.add_error(msg)

