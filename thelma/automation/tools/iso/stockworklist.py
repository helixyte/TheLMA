"""
Worklists generators for stock transfers (transfer of liquids from
a stock tube to a plate).

AAB
"""
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.iso.prep_utils import IsoControlRackLayout
from thelma.automation.tools.iso.prep_utils import PrepIsoAssociationData
from thelma.automation.tools.iso.prep_utils import PrepIsoLayout
from thelma.automation.tools.iso.prep_utils import PrepIsoPosition
from thelma.automation.tools.iso.prep_utils import RequestedStockSample
from thelma.automation.tools.iso.prep_utils import get_stock_takeout_volume
from thelma.automation.tools.semiconstants import get_384_rack_shape
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import add_list_map_element
from thelma.automation.tools.utils.base import is_valid_number
from thelma.automation.tools.utils.racksector import QuadrantIterator
from thelma.automation.tools.utils.racksector import RackSectorTranslator
from thelma.automation.tools.worklists.generation \
    import PlannedWorklistGenerator
from thelma.automation.tools.worklists.optimiser import BiomekLayoutOptimizer
from thelma.automation.tools.worklists.optimiser import TransferItemData
from thelma.models.liquidtransfer import PlannedContainerTransfer
from thelma.models.liquidtransfer import PlannedWorklist

__docformat__ = 'reStructuredText en'

__all__ = ['StockTransferWorklistGenerator',
           'StockTransferWorklistGenerator96',
           'StockTransferWorklistGenerator384Samples',
           'StockTransferWorklistGenerator384Single',
           'PrepIsoTransferItem',
           'SingleStockRackLayoutOptimiser',
           'StockTransferWorklistGenerator384Controls',
           ]



class StockTransferWorklistGenerator(PlannedWorklistGenerator):
    """
    Creates a container transfer worklist for the transfer of molecule design
    sample from stock rack to a control or preparation plate.

    **Return Value:** :class:`PlannedWorklist` (type: CONTAINER_TRANSFER)
    """

    NAME = 'Stock Taking Worklist Generator'

    #: The worklist suffix added to the provided label.
    WORKLIST_SUFFIX = '_stock_transfer'
    #: Indicates the participation of a Biomek.
    BIOMEK_MARKER = '_biomek'

    #: The assumed of the working layout class.
    WORKING_LAYOUT_CLASS = None

    def __init__(self, working_layout, label, log):
        """
        Constructor:

        :param working_layout: The working layout containing the volume and
            concentration data.
        :type working_layout: depending on the subclass

        :param label: The label of ISO or ISO job for which the worklist
            is created.
        :type label: :class:`basestring`

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        PlannedWorklistGenerator.__init__(self, log=log)

        #: The layout containing the volume and concentration data.
        self.working_layout = working_layout
        #: The label of ISO or ISO job for which the worklist is created.
        self.label = label

    def _check_input(self):
        """
        Checks the input values.
        """
        self.add_debug('Check input ...')
        self._check_input_class('label', self.label, basestring)
        self._check_input_class('working layout', self.working_layout,
                                self.WORKING_LAYOUT_CLASS)

    def _set_label(self):
        """
        Use this method to set label for the planned worklist.
        """
        self._label = '%s%s' % (self.label, self.WORKLIST_SUFFIX)

    def _create_planned_transfers(self):
        """
        Overwrite this method to create the planned transfer belonging to
        the worklist.
        """
        self.add_debug('Create planned transfers ...')

        for working_pos in self.working_layout.working_positions():
            take_out_volume = self._get_take_out_volume(working_pos)
            if take_out_volume is None: continue
            volume = take_out_volume / VOLUME_CONVERSION_FACTOR
            pct = PlannedContainerTransfer(volume=volume,
                            source_position=working_pos.rack_position,
                            target_position=working_pos.rack_position)
            self._add_planned_transfer(pct)

    def _get_take_out_volume(self, working_pos): #pylint: disable=W0613
        """
        Retrieves the take out volume from the given working position.
        """
        self.add_error('Abstract method: _get_take_out_volume()')


class StockTransferWorklistGenerator96(StockTransferWorklistGenerator):
    """
    A stock taking worklist generator for 96-well ISOs.

    **Return Value:** :class:`PlannedWorklist` (type: CONTAINER_TRANSFER)
    """

    WORKING_LAYOUT_CLASS = PrepIsoLayout

    WORKLIST_SUFFIX = StockTransferWorklistGenerator.WORKLIST_SUFFIX + \
                      StockTransferWorklistGenerator.BIOMEK_MARKER

    def _get_take_out_volume(self, working_pos):
        """
        Retrieves the take out volume from the given working position.
        """
        prep_pos = working_pos

        if not prep_pos.parent_well is None: return None
        if prep_pos.is_mock or prep_pos.is_inactivated: return None
        return prep_pos.get_stock_takeout_volume()


class StockTransferWorklistGenerator384Samples(BaseAutomationTool):
    """
    A stock taking worklist generator for 384-well samples.
    In theory this could be a rack transfer. But since we are dealing with
    stock tube that may change their racks, logging (which is crucial here)
    might become difficult. Thus, the transfers are stored as container
    transfers.

    :Note: The tool will generate worklists for four different quadrants
        even if there are no rack sectors.

    **Return Value:** the :class:`PlannedWorklist` (type: CONTAINER_TRANSFER)
        mapped onto rack sectors
    """

    NAME = 'Stock Taking Sample Worklist Generator'

    def __init__(self, preparation_layout, iso_label, sector_stock_samples,
                 floating_stock_concentration, association_data, log):
        """
        Constructor:

        :param preparation_layout: The working layout containing the volume and
            concentration data.
        :type preparation_layout: :class:`PrepIsoLayout`

        :param iso_label: The label of ISO for which the worklists.
        :type iso_label: :class:`basestring`

        :param sector_stock_samples: Requested stock samples sorted by sector.
        :type sector_stock_samples: :class:`dict`

        :param association_data: The rack sector association data (sector
            association, concentrations and parent sectors).
        :type association_data: :class:`PrepIsoAssociationData`

        :param floating_stock_concentration: The concentration for the molecule
            type of the sample positions in the stock (in nM).
        :type floating_stock_concentration: positive number

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        BaseAutomationTool.__init__(self, log=log)

        #: The working layout containing the volume and concentration data.
        self.preparation_layout = preparation_layout
        #: The label of ISO for which the worklists.
        self.iso_label = iso_label
        #: Lists the sector indices for which to generate worklists.
        self.sector_stock_samples = sector_stock_samples
        #: Concentration for the requested molecule type in the stock (in nM).
        self.stock_concentration = floating_stock_concentration
        #: The rack sector association data (sector association,
        #: concentrations and parent sectors).
        self.association_data = association_data

        #: The determined take out volumes mapped onto sector indices.
        self.__transfer_volumes = None
        #: The planned worklists mapped onto sector indices.
        self.__planned_worklists = None

    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        BaseAutomationTool.reset(self)
        self.__transfer_volumes = dict()
        self.__planned_worklists = dict()

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start worklist generation ...')

        self.__check_input()
        if not self.has_errors(): self.__determine_transfer_volumes()
        if not self.has_errors(): self.__create_worklists()
        if not self.has_errors():
            self.return_value = self.__planned_worklists
            self.add_info('Worklist generation completed.')

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')

        self._check_input_class('preparation plate layout',
                                self.preparation_layout, PrepIsoLayout)
        self._check_input_class('ISO label', self.iso_label, basestring)
        self._check_input_class('association data', self.association_data,
                                PrepIsoAssociationData)

        if self._check_input_class('sector stock samples map',
                                   self.sector_stock_samples, dict):
            for sector_index, req_stock_samples \
                                in self.sector_stock_samples.iteritems():
                if not self._check_input_class('sector index', sector_index,
                                               int): break
                if not self._check_input_class('requested stock samples list',
                                               req_stock_samples, list): break

        if not is_valid_number(self.stock_concentration, is_integer=True):
            msg = 'The stock concentration must be a positive integer ' \
                  '(obtained: %s).' % (self.stock_concentration)
            self.add_error(msg)

    def __determine_transfer_volumes(self):
        """
        Determines the donation (transfer) volumes for each rack sector.
        """
        self.add_debug('Determine transfer volumes for rack sectors ...')

        required_volumes = self.association_data.sector_req_volumes
        concentrations = self.association_data.sector_concentrations
        parent_sectors = self.association_data.parent_sectors

        for sector_index in self.sector_stock_samples.keys():
            if concentrations.has_key(sector_index):
                use_index = sector_index
            else:
                use_index = 0
            parent_sector = parent_sectors[use_index]
            req_volume = required_volumes[use_index]
            prep_conc = concentrations[use_index]

            if not parent_sector is None: continue

            take_out_volume = get_stock_takeout_volume(
                        stock_concentration=self.stock_concentration,
                        required_volume=req_volume,
                        concentration=prep_conc)

            transfer_volume = take_out_volume / VOLUME_CONVERSION_FACTOR
            self.__transfer_volumes[sector_index] = transfer_volume

        return self.__transfer_volumes

    def __create_worklists(self):
        """
        Creates the planned worklists.
        """
        self.add_debug('Create worklists ...')

        self.__init_worklists()
        translators = self.__init_translators()

        quadrant_iter = QuadrantIterator(number_sectors=4)
        for quadrant_pps in quadrant_iter.get_all_quadrants(
                        working_layout=self.preparation_layout):

            for sector_index, prep_pos in quadrant_pps.iteritems():
                if not self.__transfer_volumes.has_key(sector_index): continue
                if prep_pos is None: continue
                if not prep_pos.is_floating or prep_pos.is_inactivated: continue

                translator = translators[sector_index]
                src_pos = translator.translate(prep_pos.rack_position)
                volume = self.__transfer_volumes[sector_index]

                pct = PlannedContainerTransfer(volume=volume,
                                source_position=src_pos,
                                target_position=prep_pos.rack_position)
                worklist = self.__planned_worklists[sector_index]
                worklist.planned_transfers.append(pct)

    def __init_worklists(self):
        """
        Initialises the worklists for each sector (assuming
        four sectors regardless of the association data).
        """

        for sector_index in self.__transfer_volumes.keys():
            worklist_label = '%s_Q%i' % (self.iso_label, sector_index + 1)
            worklist = PlannedWorklist(label=worklist_label)
            self.__planned_worklists[sector_index] = worklist

    def __init_translators(self):
        """
        Initialises a rack sector translator for each sector (assuming
        four sectors regardless of the association data).
        """
        translators = dict()
        for sector_index in self.sector_stock_samples.keys():
            translator = RackSectorTranslator(number_sectors=4,
                            source_sector_index=0,
                            target_sector_index=sector_index,
                            enforce_type=RackSectorTranslator.ONE_TO_MANY)
            translators[sector_index] = translator

        return translators


class StockTransferWorklistGenerator384Single(StockTransferWorklistGenerator):
    """
    A stock taking worklist generator for 384-well samples that still
    fit into one source rack.

    **Return Value:** the :class:`PlannedWorklist` (type: CONTAINER_TRANSFER)
        mapped onto rack sectors
    """

    WORKING_LAYOUT_CLASS = type(None)

    WORKLIST_SUFFIX = StockTransferWorklistGenerator.WORKLIST_SUFFIX + \
                      StockTransferWorklistGenerator.BIOMEK_MARKER

    def __init__(self, iso_label, requested_stock_samples, log):
        """
        Constructor:

        :param iso_label: The label of ISO for which the worklist is created.
        :type iso_label: :class:`basestring`

        :param requested_stock_samples: The requested stock samples.
        :type requested_stock_samples: :class:`list` of
            :class:`RequestedStockSample` objects

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        StockTransferWorklistGenerator.__init__(self, working_layout=None,
                                              label=iso_label, log=log)

        #: The requested stock samples.
        self.requested_stock_samples = requested_stock_samples

    def _check_input(self):
        """
        Checks the input values.
        """
        self.add_debug('Check input ...')

        self._check_input_class('label', self.label, basestring)
        if self._check_input_class('requested stock samples list',
                                   self.requested_stock_samples, list):
            for req_stock_sample in self.requested_stock_samples:
                if not self._check_input_class('requested stock sample',
                                req_stock_sample, RequestedStockSample): break

    def _create_planned_transfers(self):
        """
        Overwrite this method to create the planned transfer belonging to
        the worklist.
        """
        self.add_debug('Create planned transfers ...')

        optimiser = SingleStockRackLayoutOptimiser(log=self.log,
                        requested_stock_samples=self.requested_stock_samples)
        optimised_layout = optimiser.get_result()

        if optimised_layout is None:
            msg = 'Error when trying to optimised stock rack layout.'
            self.add_error(msg)
        else:

            src_positions = dict()
            for src_pos, prep_pos in optimised_layout.iterpositions():
                src_positions[prep_pos.molecule_design_pool_id] = src_pos

            for req_stock_sample in self.requested_stock_samples:
                src_pos = src_positions[req_stock_sample.pool.id]
                volume = req_stock_sample.take_out_volume \
                         / VOLUME_CONVERSION_FACTOR
                pct = PlannedContainerTransfer(volume=volume,
                            source_position=src_pos,
                            target_position=req_stock_sample.target_position)
                req_stock_sample.target_position = src_pos
                self._add_planned_transfer(pct)


class PrepIsoTransferItem(TransferItemData):
    """
    A special :class:`TransferItemData` for :class:`ParentIsoPosition` objects.
    """
    HASH_NAME = 'molecule_design_pool_id'


class SingleStockRackLayoutOptimiser(BiomekLayoutOptimizer):
    """
    A Biomek layout optimiser for single stock racks that are used to fill
    a 384-well preparation plate. The tool tries to optimise the stock
    rack layout in a way allows the Biomek to work as fast as possible.

    **Return Value:** The optimised preparation layout.
    """

    NAME = 'Single Stock Rack Layout Optimiser'

    SOURCE_LAYOUT_CLS = PrepIsoLayout
    TRANSFER_ITEM_CLASS = PrepIsoTransferItem

    def __init__(self, log, requested_stock_samples):
        """
        Constructor:
        :param requested_stock_samples: The required molecule design pooldata.
        :type requested_stock_samples: :class:`list` of
            :class:`RequestedStockSample` objects

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        BiomekLayoutOptimizer.__init__(self, log=log)

        #: The required molecule design data as :class:`RequestedStockSample`.
        self.requested_stock_samples = requested_stock_samples

    def _check_input(self):
        """
        Checks the input values.
        """
        self.add_debug('Check input ...')

        if self._check_input_class('requested stock sample list',
                                   self.requested_stock_samples, list):
            for req_stock_sample in self.requested_stock_samples:
                if not self._check_input_class('requested stock sample',
                                req_stock_sample, RequestedStockSample): break
            if len(self.requested_stock_samples) < 1:
                msg = 'There are no requested stock samples in the list!'
                self.add_error(msg)

    def _find_hash_values(self):
        """
        Initialises ::attr:`__hash_values` and :attr:`__column_maps`.
        The requested stock samples are converted back into preparation
        positions.

        Since the only relevant attributes here are molecule design and rack
        position the other values obtain default values.
        """
        self.add_debug('Collect molecule designs ... ')

        column_map = dict()

        for req_stock_sample in self.requested_stock_samples:
            self._hash_values.add(req_stock_sample.pool.id)
            pp = PrepIsoPosition(rack_position=req_stock_sample.target_position,
                            molecule_design_pool=req_stock_sample.pool,
                            required_volume=1, position_type=None,
                            prep_concentration=1,
                            transfer_targets=None)
            add_list_map_element(column_map, pp.rack_position.column_index, pp)

        self._column_maps[1] = column_map

    def _get_target_layout_shape(self):
        """
        This particular optimiser is only used for 96-to-384-well transfers.
        """
        return get_384_rack_shape()

    def _create_one_to_one_map(self):
        """
        We do not support that here because this particular optimiser is made
        for 96-to-384-well transfers
        """
        self.add_error('One-to-one sorting is not supported. There must not ' \
                       'be more than 96 molecule design pools.')

    def _add_source_position(self, rack_pos, working_pos):
        """
        Creates a new source position and places it onto the given
        position of the source layout.

        The new position is a copy of the given one, but with a different
        rack position. Since the only relevant attributes here are molecule
        design pool and rack position the other parameters obtain default
        values.
        """
        prep_pos = PrepIsoPosition(rack_position=rack_pos,
                    molecule_design_pool=working_pos.molecule_design_pool,
                    required_volume=1, prep_concentration=1,
                    position_type=None, transfer_targets=None)
        self._source_layout.add_position(prep_pos)


class StockTransferWorklistGenerator384Controls(StockTransferWorklistGenerator):
    """
    A stock taking worklist generator for 384-well ISOs controls.

    **Return Value:** :class:`PlannedWorklist` (type: CONTAINER_TRANSFER)
    """

    WORKING_LAYOUT_CLASS = IsoControlRackLayout


    def __init__(self, control_layout, job_label, log):
        """
        Constructor:

        :param working_layout: The working layout containing the volume and
            concentration data.
        :type working_layout: depending on the subclass

        :param job_label: The label of the ISO job for which the worklist
            is created.
        :type job_label: :class:`basestring`

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        StockTransferWorklistGenerator.__init__(self, log=log,
                                working_layout=control_layout,
                                label=job_label)

    def _create_planned_transfers(self):
        """
        Overwrite this method to create the planned transfer belonging to
        the worklist.
        """
        self.add_debug('Create planned transfers ...')

        for control_pos in self.working_layout.working_positions():
            source_pos = control_pos.rack_position
            for tt in control_pos.transfer_targets:
                volume = tt.transfer_volume / VOLUME_CONVERSION_FACTOR
                target_pos = get_rack_position_from_label(tt.position_label)
                pct = PlannedContainerTransfer(volume=volume,
                                    source_position=source_pos,
                                    target_position=target_pos)
                self._add_planned_transfer(pct)
