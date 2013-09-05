"""
Base classes, functions and constants for ISO processing (type-independent).

AAB
"""
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.utils.base import TransferLayout
from thelma.automation.tools.utils.base import TransferParameters
from thelma.automation.tools.utils.base import TransferPosition
from thelma.automation.tools.utils.converters import TransferLayoutConverter
from thelma.models.liquidtransfer import PlannedSampleTransfer
from thelma.automation.tools.stock.base import STOCK_DEAD_VOLUME

__docformat__ = 'reStructuredText en'

__all__ = ['StockRackParameters',
           'StockRackPosition',
           'StockRackLayout',
           'StockRackLayoutConverter']


class StockRackParameters(TransferParameters):
    """
    Stores pool, tube and transfer target data for stock racks.
    """
    DOMAIN = 'stock_rack'
    ALLOWS_UNTREATED_POSITIONS = False

    #: The molecule design pool (tag value: molecule design pool id).
    MOLECULE_DESIGN_POOL = TransferParameters.MOLECULE_DESIGN_POOL
    #: The barcode of the tube that is the source for a stock transfer.
    TUBE_BARCODE = 'tube_barcode'
    #: The target positions including transfer volumes (list of
    # :class:`TransferTarget` objects).
    TRANSFER_TARGETS = TransferParameters.TRANSFER_TARGETS
    MUST_HAVE_TRANSFER_TARGETS = True

    REQUIRED = [MOLECULE_DESIGN_POOL, TUBE_BARCODE, TRANSFER_TARGETS]
    ALL = REQUIRED

    ALIAS_MAP = {MOLECULE_DESIGN_POOL : TransferParameters.ALIAS_MAP[
                                                        MOLECULE_DESIGN_POOL],
                 TUBE_BARCODE : ['container_barcode'],
                 TRANSFER_TARGETS : TransferParameters.ALIAS_MAP[
                                                        TRANSFER_TARGETS]}

    DOMAIN_MAP = {MOLECULE_DESIGN_POOL : TransferParameters.DOMAIN_MAP[
                                                        MOLECULE_DESIGN_POOL],
                  TUBE_BARCODE : DOMAIN,
                  TRANSFER_TARGETS : TransferParameters.DOMAIN_MAP[
                                                            TRANSFER_TARGETS]}


class StockRackPosition(TransferPosition):
    """
    Represents a position in a stock rack that is used for ISO processing.
    """
    PARAMETER_SET = StockRackParameters

    def __init__(self, rack_position, molecule_design_pool, tube_barcode,
                 transfer_targets):
        """
        Constructor:

        :param rack_position: The position within the rack.
        :type rack_position: :class:`thelma.models.rack.RackPosition`

        :param molecule_design_pool: The molecule design pool for this position.
        :type molecule_design_pool:  placeholder or
            :class:`thelma.models.moleculedesign.MoleculeDesignPool`

        :param tube_barcode: The tube expected at the given position.
        :type tube_barcode: :class:`basestring`

        :param transfer_targets: The volume required to supply all child wells
            and the volume for the transfer to the ISO plate.
        :type transfer_targets: :class:`list` of :class:`TransferTarget` objects
        """
        TransferPosition.__init__(self, rack_position=rack_position,
                                  molecule_design_pool=molecule_design_pool,
                                  transfer_targets=transfer_targets)

        if not self.is_fixed:
            msg = 'ISO stock rack positions must be fixed positions!'
            raise ValueError(msg)
        self.position_type = None # we do not need position types here

        if not isinstance(tube_barcode, basestring):
            msg = 'The tube barcode must be a string (obtained: %s).' \
                   % (tube_barcode.__class__.__name__)
            raise TypeError(msg)
        #: The tube expected at the given position.
        self.tube_barcode = tube_barcode

    def get_planned_sample_transfers(self, plate_marker):
        """
        Converts the all transfer target for the given target plate into
        :class:`PlannedSampleTransfer` objects.
        """
        psts = []
        for tt in self.transfer_targets:
            if not tt.target_rack_marker == plate_marker: continue
            trg_pos = get_rack_position_from_label(tt.position_label)
            pst = PlannedSampleTransfer.get_entity(volume=tt.transfer_volume,
                                source_position=self.rack_position,
                                target_position=trg_pos)
            psts.append(pst)
        return psts

    def get_required_stock_volume(self):
        """
        Returns the sum of the transfer volumes for all target positions
        plus the stock dead volume.
        """
        vol = STOCK_DEAD_VOLUME
        for tt in self.transfer_targets:
            vol += tt.transfer_volume
        return vol

    def _get_parameter_values_map(self):
        parameter_map = TransferPosition._get_parameter_values_map(self)
        parameter_map[self.PARAMETER_SET.TUBE_BARCODE] = self.tube_barcode
        return parameter_map

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
            self.rack_position == other.rack_position and \
            self.molecule_design_pool == other.molecule_design_pool and \
            self.tube_barcode == other.tube_barcode

    def __repr__(self):
        str_format = '<%s rack position: %s, molecule design pool ID: %s, ' \
                     'tubebarocde: %s, transfer targets: %s>'
        params = (self.__class__.__name__, self.rack_position,
                  self.molecule_design_pool_id, self.tube_barcode,
                  self.get_targets_tag_value())
        return str_format % params


class StockRackLayout(TransferLayout):
    """
    The layout for a stock rack that is used in ISO processing. The rack
    shape is always 8x12.
    """
    WORKING_POSITION_CLS = StockRackPosition

    def __init__(self):
        """
        Constructor
        """
        TransferLayout.__init__(self, shape=get_96_rack_shape())

    def get_duplicate_molecule_design_pools(self):
        """
        Returns a list of molecule design pools occurring more than once.
        """
        md_pools = set()
        duplicate_pools = set()
        for control_pos in self._position_map.values():
            pool = control_pos.molecule_design_pool
            if pool.id in md_pools:
                duplicate_pools.add(pool)
            else:
                md_pools.add(pool.id)

        return list(duplicate_pools)


class StockRackLayoutConverter(TransferLayoutConverter):
    """
    Converts a rack layout into a :class:`StockRackLayout`
    """

    NAME = 'Stock Rack Layout Converter'
    PARAMETER_SET = StockRackParameters
    WORKING_LAYOUT_CLASS = StockRackLayout

    def __init__(self, rack_layout, log):
        """
        Constructor:

        :param rack_layout: The rack layout containing the transfer data.
        :type rack_layout: :class:`thelma.models.racklayout.RackLayout`

        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`
        """
        TransferLayoutConverter.__init__(self, rack_layout=rack_layout, log=log)

        # Intermediate error storage
        self.__missing_pool = None
        self.__missing_transfer_targets = None
        self.__missing_tube_barcode = None

    def reset(self):
        TransferLayoutConverter.reset(self)
        self.__missing_pool = []
        self.__missing_transfer_targets = []
        self.__missing_tube_barcode = []

    def _get_position_init_values(self, parameter_map):
        rack_position = parameter_map[self._RACK_POSITION_KEY]
        pool_id = parameter_map[self.PARAMETER_SET.MOLECULE_DESIGN_POOL]
        tube_barcode = parameter_map[self.PARAMETER_SET.TUBE_BARCODE]
        transfer_targets = parameter_map[self.PARAMETER_SET.TRANSFER_TARGETS]

        if pool_id is None and tube_barcode is None \
                                            and transfer_targets is None:
            return None

        is_valid = True

        if tube_barcode is None or len(tube_barcode) < 1:
            self.__missing_tube_barcode.append(rack_position.label)
            is_valid = False

        if not self._are_valid_transfer_targets(transfer_targets,
                                                rack_position):
            is_valid = False

        if pool_id is None:
            self.__missing_pool.append(rack_position.label)
            is_valid = False
        else:
            pool = self._get_molecule_design_pool_for_id(pool_id,
                                                         rack_position.label)
            if pool is None: is_valid = False

        if is_valid:
            kw = dict(rack_position=rack_position, molecule_design_pool=pool,
                      tube_barcode=tube_barcode,
                      transfer_targets=transfer_targets)
            return kw
        else:
            return None

    def _record_additional_position_errors(self):
        """
        Records errors that have been collected for rack positions.
        """
        TransferLayoutConverter._record_additional_position_errors(self)

        if len(self.__missing_pool) > 0:
            msg = 'The following positions to not have a molecule design ' \
                  'pool ID: %s.' % (', '.join(sorted(self.__missing_pool)))
            self.add_error(msg)

        if len(self.__missing_tube_barcode) > 0:
            msg = 'The following positions to not have tube barcode: %s.' \
                  % (', '.join(sorted(self.__missing_tube_barcode)))
            self.add_error(msg)

        if len(self.__missing_transfer_targets) > 0:
            msg = 'A control rack position must have at least one transfer ' \
                  'target. The following rack position do not have a ' \
                  'transfer target: %s.' \
                   % (', '.join(sorted(self.__missing_transfer_targets)))
            self.add_error(msg)

    def _initialize_working_layout(self, shape):
        return self.WORKING_LAYOUT_CLS()

    def _perform_layout_validity_checks(self, working_layout):
        """
        Use this method to check the validity of the generated layout.
        """
        duplicate_pools = working_layout.get_duplicate_molecule_design_pools()
        if len(duplicate_pools) > 0:
            msg = 'There are duplicate molecule design pools in the stock ' \
                  'rack layout. This is a programming error, please contact ' \
                  'the IT department.'
            self.add_error(msg)
