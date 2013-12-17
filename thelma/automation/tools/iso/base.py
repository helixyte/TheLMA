"""
Base classes, functions and constants for ISO processing (type-independent).

AAB
"""
from thelma.automation.semiconstants import get_rack_position_from_label
from thelma.automation.tools.stock.base import STOCK_DEAD_VOLUME
from thelma.automation.tools.stock.base import get_stock_rack_shape
from thelma.automation.tools.worklists.series import SerialWriterExecutorTool
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.utils.converters import TransferLayoutConverter
from thelma.automation.utils.layouts import BaseRackVerifier
from thelma.automation.utils.layouts import EMPTY_POSITION_TYPE
from thelma.automation.utils.layouts import FIXED_POSITION_TYPE
from thelma.automation.utils.layouts import TransferLayout
from thelma.automation.utils.layouts import TransferParameters
from thelma.automation.utils.layouts import TransferPosition
from thelma.models.iso import StockRack
from thelma.models.liquidtransfer import PlannedSampleTransfer
from thelma.models.rack import TubeRack

__docformat__ = 'reStructuredText en'

__all__ = ['IsoRackContainer',
           'StockRackParameters',
           'StockRackPosition',
           'StockRackLayout',
           'StockRackLayoutConverter',
           'StockRackVerifier',
           'StockTransferWriterExecutor']

class _ISO_LABELS_BASE(object):
    """
    Generates and parses worklist and rack labels involved in lab ISO
    processing.
    """
    #: The character used in the labels to separate the value parts.
    SEPARATING_CHAR = '_'
    #: This character is used seperate running numbers from value parts.
    NUMBERING_CHAR = '#'

    #: Marker for worklist source racks in keyword dictionaries.
    MARKER_WORKLIST_SOURCE = 'source_rack_marker'
    #: Marker for worklist target racks in keyword dictionaries.
    MARKER_WORKLIST_TARGET = 'target_rack_marker'

    #: Marks the roles of a rack (e.g. stock rack, final plate). Is part
    #: of rack labels.
    MARKER_RACK_ROLE = 'rack_role'
    #: Marker for racks markers (see :func:`create_rack_marker`).
    MARKER_RACK_MARKER = 'rack_marker'
    #: Used to distinguish racks having the same role.
    MARKER_RACK_NUM = 'rack_num'

    #: For dilution worklists. Located after the target rack. In ISOs
    #: the diluent is always buffer.
    _FILL_WORKLIST_DILUTION = 'buffer'

    @classmethod
    def _create_label(cls, value_parts, for_numbering=False):
        """
        Reverse of :func:`_get_value_parts`.
        """
        for i in range(len(value_parts)):
            value = value_parts[i]
            if isinstance(value, int):
                value_str = cls._get_int_str(value)
                value_parts[i] = value_str

        sep = cls.SEPARATING_CHAR
        if for_numbering: sep = cls.NUMBERING_CHAR
        return sep.join(value_parts)

    @classmethod
    def create_rack_marker(cls, rack_role, rack_number=None):
        """
        A rack marker contains a role and (optionally) a rack number.
        """
        value_parts = [rack_role]
        if rack_number is not None:
            value_parts += [rack_number]
            return cls._create_label(value_parts, for_numbering=True)
        else:
            return rack_role

    @classmethod
    def parse_rack_marker(cls, rack_marker):
        """
        A rack marker contains a role and (optionally) a rack number.
        If the rack marker is a :attr:LIBRARY_PLACEHOLDER`, the role is
        final plate (without number).
        """
        value_parts = cls._get_value_parts(rack_marker, for_numbering=True)
        values = {cls.MARKER_RACK_ROLE : value_parts[0]}
        if len(value_parts) > 1:
            rack_num = cls._parse_int_str(value_parts[1])
            values[cls.MARKER_RACK_NUM] = rack_num
        return values

    @classmethod
    def _get_value_parts(cls, label, for_numbering=False):
        """
        Reverse of :func:`_create_label`.
        """
        sep = cls.SEPARATING_CHAR
        if for_numbering: sep = cls.NUMBERING_CHAR
        return label.split(sep)

    @classmethod
    def _get_int_str(cls, value):
        """
        Reverse of :func:`_parse_int_str`.
        """
        return '%i' % (value)

    @classmethod
    def _parse_int_str(cls, value_str):
        """
        Reverse of :func:`_get_int_str`.
        """
        return int(value_str)


class IsoRackContainer(object):
    """
    A helper class storing the role and rack marker for a rack involved
    in ISO processing.
    """
    def __init__(self, rack, rack_marker, label=None, role=None):
        """
        Constructor:

        :param rack: The rack or plate.
        :type rack: :class:`thelma.models.rack.Rack`

        :param rack_marker: Contains the rack role and number
            (see :func:`LABELS.create_rack_marker`).
        :type rack_marker: :class:`basestring`
        :default rack_marker: *None* (is parsed from the :param:`label`).

        :param label: The rack or stock rack label.
        :type label: :class:`basestring`
        :default label: *None* (is taken from the :param:`rack`).

        :param role: Final, preparation or stock preparation plate or stock rack
            (see :class:`LABELS`).
        :type role: *ROLE* value from :class:`LABELS`
        :default role: *None* (is parsed from the :param:`label`).
        """
        #: The rack or plate.
        self.rack = rack

        #: Contains the rack role and number (see
        #: :func:`LABELS.create_rack_marker`).
        self.rack_marker = rack_marker

        if label is None:
            label = rack.label
        #: The rack or stock rack label.
        self.label = label

        if role is None:
            values = _ISO_LABELS_BASE.parse_rack_marker(rack_marker)
            role = values[_ISO_LABELS_BASE.MARKER_RACK_ROLE]
        #: Final, preparation or stock preparation plate or stock rack
        #: (see :class:`LABELS`).
        self.role = role

    def __eq__(self, other):
        return isinstance(other, self.__class__) and other.rack == self.rack

    def __cmp__(self, other):
        return cmp(self.label, other.label)

    def __str__(self):
        return self.label

    def __repr__(self):
        str_format = '<%s rack: %s, label: %s>'
        params = (self.__class__.__name__, self.rack, self.label)
        return str_format % params


class StockRackParameters(TransferParameters):
    """
    Stores pool, tube and transfer target data for stock racks.
    """
    DOMAIN = 'stock_rack'
    ALLOWED_POSITION_TYPES = [FIXED_POSITION_TYPE, EMPTY_POSITION_TYPE]

    #: The molecule design pool (tag value: molecule design pool id).
    MOLECULE_DESIGN_POOL = TransferParameters.MOLECULE_DESIGN_POOL
    #: The barcode of the tube that is the source for a stock transfer.
    TUBE_BARCODE = 'tube_barcode'
    #: The target positions including transfer volumes (list of
    # :class:`TransferTarget` objects).
    TRANSFER_TARGETS = TransferParameters.TRANSFER_TARGETS
    MUST_HAVE_TRANSFER_TARGETS = {TRANSFER_TARGETS : True}

    REQUIRED = [MOLECULE_DESIGN_POOL, TUBE_BARCODE, TRANSFER_TARGETS]
    ALL = REQUIRED

    ALIAS_MAP = dict(TransferParameters.ALIAS_MAP, **{
                                TUBE_BARCODE : ['container_barcode']})
    DOMAIN_MAP = dict(TransferParameters.DOMAIN_MAP, **{TUBE_BARCODE : DOMAIN})


class StockRackPosition(TransferPosition):
    """
    Represents a position in a stock rack that is used for ISO processing.
    """
    PARAMETER_SET = StockRackParameters
    EXPOSE_POSITION_TYPE = False

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
            pst = PlannedSampleTransfer.get_entity(
                        volume=tt.transfer_volume / VOLUME_CONVERSION_FACTOR,
                        source_position=self.rack_position,
                        target_position=trg_pos)
            psts.append(pst)
        return psts

    def get_required_stock_volume(self):
        """
        Returns the sum of the transfer volumes for all target positions
        plus the stock dead volume *in ul*.
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
        if not TransferPosition.__eq__(self, other): return False
        return self.tube_barcode == other.tube_barcode

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
    POSITION_CLS = StockRackPosition

    def __init__(self):
        """
        Constructor
        """
        TransferLayout.__init__(self, shape=get_stock_rack_shape())

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
    LAYOUT_CLS = StockRackLayout
    POSITION_CLS = StockRackPosition

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
        self.__missing_tube_barcode = None

    def reset(self):
        TransferLayoutConverter.reset(self)
        self.__missing_tube_barcode = []

    def _get_position_init_values(self, parameter_map, rack_pos):
        kw = TransferLayoutConverter._get_position_init_values(self,
                                            parameter_map, rack_pos)
        if kw is None: return None

        tube_barcode = parameter_map[self.PARAMETER_SET.TUBE_BARCODE]
        if tube_barcode is None or len(tube_barcode) < 2:
            self.__missing_tube_barcode.append(rack_pos.label)
            return None

        kw['tube_barcode'] = tube_barcode
        return kw

    def _record_errors(self):
        TransferLayoutConverter._record_errors(self)
        if len(self.__missing_tube_barcode) > 0:
            msg = 'The following positions to not have tube barcode: %s.' \
                  % (', '.join(sorted(self.__missing_tube_barcode)))
            self.add_error(msg)

    def _initialize_working_layout(self, shape):
        return self.LAYOUT_CLS()

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


class StockRackVerifier(BaseRackVerifier):
    """
    Compares stock racks for ISOs and ISO jobs with stock racks layouts.
    """
    NAME = 'Lab ISO Stock Rack Verifier'

    _RACK_CLS = TubeRack
    _LAYOUT_CLS = StockRackLayout
    _CHECK_VOLUMES = True

    def __init__(self, log, stock_rack, stock_rack_layout=None):
        """
        Constructor:

        :param log: The log the write in.
        :type log: :class:`thelma.ThelmaLog`

        :param stock_rack: The stock rack to be checked.
        :type stock_rack: :class:`thelma.models.iso.StockRack`

        :param stock_rack_layout: The layout containing the molecule design
            and volume data. Can be set here or derived during the run.
        :type stock_rack_layout:  :class:`StockRackLayout`
        """
        BaseRackVerifier.__init__(self, log=log,
                                  reference_layout=stock_rack_layout)

        #: The stock rack to be checked.
        self.stock_rack = stock_rack

    def _check_input(self):
        BaseRackVerifier._check_input(self)
        self._check_input_class('stock rack', self.stock_rack, StockRack)

    def _set_rack(self):
        self._rack = self.stock_rack.rack

    def _fetch_expected_layout(self):
        converter = StockRackLayoutConverter(log=self.log,
                                     rack_layout=self.stock_rack.rack_layout)
        self._expected_layout = converter.get_result()
        if self._expected_layout is None:
            msg = 'Error when trying to convert stock rack layout!'
            self.add_error(msg)

    def _get_minimum_volume(self, pool_pos):
        """
        Returns the sum of the transfer volumes for all target positions
        plus the stock dead volume.
        """
        return pool_pos.get_required_stock_volume()


class StockTransferWriterExecutor(SerialWriterExecutorTool):
    """
    An abstract series writer/executor for series that include stock transfers
    in ISO generation processed. It comprises additional checks and provides
    additional access functions for reporters.

    **Return Value:** a zip stream for for printing mode or the entity
        for execution mode (can be overwritten)
    """

    #: The entity treated by the subclass.
    ENTITY_CLS = None

    def __init__(self, entity, mode, user=None, **kw):
        """
        Constructor:

        :param entity: The ISO job or ISO to process.
        :type entity: :class:`thelma.models.job.IsoJob` or
            :class:`thelma.models.iso.LabIso`.

        :param mode: :attr:`MODE_EXECUTE` or :attr:`MODE_PRINT_WORKLISTS`
        :type mode: str

        :param user: The user who conducts the DB update (required for
            execution mode).
        :type user: :class:`thelma.models.user.User`
        :default user: *None*
        """
        SerialWriterExecutorTool.__init__(self, mode=mode, user=user, **kw)
        #: The entity the transfer will be attached to (ISO or ISO job).
        self.entity = entity

        #: The executed stock transfer worklists (for reporting).
        self._executed_stock_worklists = None

    def reset(self):
        """
        Checks the initialisation values.
        """
        SerialWriterExecutorTool.reset(self)
        self._executed_stock_worklists = []

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        SerialWriterExecutorTool._check_input(self)
        self._check_input_class('entity', self.entity, self.ENTITY_CLS)

    def get_executed_stock_worklists(self):
        """
        Returns the executed worklists that have been generated (for reporting).
        If the length of executed worklists is below 1 the submission to
        the trac is cancelled without error message.
        """
        return self._get_additional_value(self._executed_stock_worklists)

    def _verify_stock_racks(self):
        """
        Makes sure the tubes is the stock are placed correctly and that the
        volumes are still sufficient.
        """
        raise NotImplementedError('Abstract method.')

    def _execute_worklists(self):
        """
        Executes the created transfer jobs (as series).
        """
        self.add_debug('Prepare worklist execution ...')

        self._verify_stock_racks()
        if not self.has_errors(): self._check_for_previous_execution()
        if not self.has_errors():
            executed_worklists = self._get_executed_worklists()
        if not self.has_errors():
            self._extract_executed_stock_worklists(executed_worklists)
        if not self.has_errors():
            self._update_iso_status()
            self.return_value = self.entity
            self.add_info('Worklist execution completed.')

    def _check_for_previous_execution(self):
        """
        Makes sure the worklists have not been executed before.
        """
        raise NotImplementedError('Abstract method.')

    def _extract_executed_stock_worklists(self, executed_worklists):
        """
        Extracts the executed stock transfer worklists and stores them
        in the :attr:`_executed_stock_worklists` list.
        """
        raise NotImplementedError('Abstract method.')

    def _update_iso_status(self):
        """
        Sets the status of the ISO(s).
        """
        raise NotImplementedError('Abstract method.')
