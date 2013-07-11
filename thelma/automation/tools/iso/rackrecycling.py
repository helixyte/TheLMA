"""
Tools that allow recycling of stock racks for tube picking.

AAB
"""
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.iso.stocktransfer \
    import IsoControlStockRackVerifier
from thelma.automation.tools.iso.stockworklist \
    import StockTransferWorklistGenerator384Controls
from thelma.automation.tools.iso.tubehandler import IsoControlLayoutFinder
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.tools.semiconstants import get_experiment_type_screening
from thelma.automation.tools.stock.base import STOCK_DEAD_VOLUME
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.models.iso import IsoJobStockRack
from thelma.models.job import IsoJob
from thelma.models.rack import TubeRack
import logging

__docformat__ = 'reStructuredText en'

__all__ = ['IsoControlRackRecycler']


class IsoControlRackRecycler(BaseAutomationTool):
    """
    Checks whether the passed stock rack can be used as ISO control stock
    rack for an ISO job and assigns the rack, if possible.

    **Return Value:** The updated ISO job.
    """

    NAME = 'ISO Control Stock Rack Recycler'

    def __init__(self, iso_job, stock_rack, logging_level=logging.WARNING,
                 add_default_handlers=False):
        """
        Constructor:

        :param iso_job: The ISO job the rack shall be used for.
        :type iso_job: :class:`thelma.models.job.IsoJob`

        :param stock_rack: The stock rack to be used as controlc sotck rack.
        :type stock_rack: :class:`thelma.models.rack.TubeRack`

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """
        BaseAutomationTool.__init__(self, logging_level=logging_level,
                                    add_default_handlers=add_default_handlers,
                                    depending=False)

        #: The ISO job the rack shall be used for.
        self.iso_job = iso_job
        #: The stock rack to be used as control stock rack.
        self.stock_rack = stock_rack

        #: The control layout for the ISO control stock rack.
        self.__control_layout = None
        #: The worklist for the transfer of sample from the stock tube to the
        #: preparation plates.
        self.__planned_worklist = None

    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        BaseAutomationTool.reset(self)
        self.__control_layout = None
        self.__planned_worklist = None

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start control stock rack recycler ...')

        self.__check_input()
        if not self.has_errors(): self.__check_scenario()
        if not self.has_errors(): self.__create_control_layout()
        if not self.has_errors(): self.__verify_stock_rack()
        if not self.has_errors(): self.__check_rack_volumes()
        if not self.has_errors(): self.__create_transfer_worklist()
        if not self.has_errors(): self.__assign_stock_rack()
        if not self.has_errors():
            self.return_value = self.iso_job
            self.add_info('Control rack confirmed and assigned.')

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')
        self._check_input_class('stock rack', self.stock_rack, TubeRack)

        if self._check_input_class('ISO job', self.iso_job, IsoJob):
            if len(self.iso_job.isos) < 1:
                msg = 'There are no ISOs in this ISO job!'
                self.add_error(msg)

    def __check_scenario(self):
        """
        Only 384-well screening scenarios are supported.
        """
        iso_request = self.iso_job.iso_request
        em_type = iso_request.experiment_metadata_type
        iso_shape = iso_request.iso_layout.shape.name
        if not iso_shape == RACK_SHAPE_NAMES.SHAPE_384 or \
                not em_type.id == EXPERIMENT_SCENARIOS.SCREENING:
            msg = 'Control stock racks are only available for %s cases with ' \
                  'a %s-well format! This is a %s scenario (%s-well format).' \
                   % (get_experiment_type_screening().display_name,
                      RACK_SHAPE_NAMES.SHAPE_384, em_type.display_name,
                      iso_shape)
            self.add_error(msg)

    def __create_control_layout(self):
        """
        Creates the control layout for the potential control stock rack.
        """
        self.add_debug('Create control layout ...')

        finder = IsoControlLayoutFinder(iso_job=self.iso_job, log=self.log)
        self.__control_layout = finder.get_result()

        if self.__control_layout is None:
            msg = 'Error when trying to find layout for ISO control rack.'
            self.add_error(msg)

    def __verify_stock_rack(self):
        """
        Verifies the :attr:`stock_rack` in its current state.
        """
        verifier = IsoControlStockRackVerifier(stock_rack=self.stock_rack,
                                    control_layout=self.__control_layout,
                                    log=self.log)
        compatible = verifier.get_result()
        if compatible is None:
            msg = 'Error in the verifier!'
            self.add_error(msg)
        elif not compatible:
            msg = 'The stock rack is not compatible with the ISO job!'
            self.add_error(msg)

    def __check_rack_volumes(self):
        """
        Checks volumes of the stock rack.
        """
        self.add_debug('Check rack volumes ...')

        not_enough_volume = []

        for tube in self.stock_rack.containers:
            rack_pos = tube.location.position
            control_pos = self.__control_layout.get_working_position(rack_pos)
            # Cannot not be None (the verifier would have detected that)
            required_volume = STOCK_DEAD_VOLUME
            for tt in control_pos.transfer_targets:
                required_volume += (tt.transfer_volume * len(self.iso_job.isos))
            sample_volume = tube.sample.volume * VOLUME_CONVERSION_FACTOR
            if not sample_volume - required_volume > -0.01:
                info = '%s (%.1f ul, required: %s)' % (tube.barcode,
                                       sample_volume, required_volume)
                not_enough_volume.append(info)

        if len(not_enough_volume) > 0:
            msg = 'Some tubes do not contain enough volume (required volumes ' \
                  'included %i ul dead volume): %s.' \
                  % (STOCK_DEAD_VOLUME, not_enough_volume)
            self.add_error(msg)

    def __create_transfer_worklist(self):
        """
        Creates the planned worklist for the transfer from stock rack to
        preparation plates.
        """
        generator = StockTransferWorklistGenerator384Controls(log=self.log,
                                        control_layout=self.__control_layout,
                                        job_label=self.iso_job.label)
        self.__planned_worklist = generator.get_result()

        if self.__planned_worklist is None:
            msg = 'Error when trying to generate control stock transfer ' \
                  'worklist.'
            self.add_error(msg)

    def __assign_stock_rack(self):
        """
        Assigns the stock rack to the ISO job.
        """
        self.add_debug('Assign stock rack ...')

        self.iso_job.iso_control_stock_rack = None
        IsoControlStockRack(iso_job=self.iso_job,
                    rack=self.stock_rack,
                    rack_layout=self.__control_layout.create_rack_layout(),
                    planned_worklist=self.__planned_worklist)
