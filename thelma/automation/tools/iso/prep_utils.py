"""
Utility classes for ISO preparations (steps involved in the (physical)
generation of ISO plates).

AAB, Jan 2012
"""
from thelma.automation.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.tools.semiconstants import get_96_rack_shape
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.utils.base import MOCK_POSITION_TYPE
from thelma.automation.tools.utils.base import MoleculeDesignPoolParameters
from thelma.automation.tools.utils.base import TransferLayout
from thelma.automation.tools.utils.base import TransferParameters
from thelma.automation.tools.utils.base import TransferPosition
from thelma.automation.tools.utils.base import get_converted_number
from thelma.automation.tools.utils.base import get_trimmed_string
from thelma.automation.tools.utils.base import is_valid_number
from thelma.automation.tools.utils.converters import TransferLayoutConverter
from thelma.automation.tools.utils.iso import IsoParameters
from thelma.automation.tools.utils.iso import IsoPosition
from thelma.automation.tools.utils.racksector import AssociationData
from thelma.automation.tools.utils.racksector import RackSectorAssociator
from thelma.automation.tools.utils.racksector import ValueDeterminer
from thelma.models.moleculedesign import MoleculeDesignPool
from thelma.models.organization import Organization
from thelma.models.rack import RackPosition

__docformat__ = "reStructuredText en"

__all__ = ['ISO_LABELS',
           'get_stock_takeout_volume',
           'PrepIsoParameters',
           'PrepIsoPosition',
           'PrepIsoLayout',
           'PrepIsoLayoutConverter',
           'PrepIsoValueDeterminer',
           'PrepIsoRackSectorAssociator',
           'PrepIsoAssociationData',
           'IsoControlRackParameters',
           'IsoControlRackPosition',
           'IsoControlRackLayout',
           'IsoControlRackLayoutConverter',
           'RequestedStockSample']


class ISO_LABELS(object):
    """
    Generates and parses labels for ISOs and ISO-related plates.
    """
    #: The character used in the ISO label to separate the plate set label of
    #: the ISO request from the ISO counter.
    __SEPARATING_CHAR = '_'

    #: Used to create ISO labels - the placeholder contain ticket number and
    #: ISO number.
    __ISO_LABEL_PATTERN = '%i_iso%i'
    #: The suffix to be added to the ISO label to mark the ISO as copy.
    __ISO_LABEL_COPY_MARKER = 'copy'

    #: Pattern for the labels of ISO aliquot plates. The placeholders contain
    #: the plate set label, the ISO number and the aliquot number.
    __ALIQUOT_PLATE_LABEL_PATTERN = '%s#%i'
    #: The aliquot suffix is only added if there are more than one aliquots
    #: ordered for an ISO. The placeholder is the aliquot number.
    __ALIQUOT_PLATE_LABEL_SUFFIX = '_a%i'

    @classmethod
    def create_iso_label(cls, iso_request, create_copy=False):
        """
        Creates a label for a future ISO. The number is derived from the count
        of ISOs that is already attached to the ISO request.

        :param iso_request: The ISO request the future ISO belongs to.
        :type iso_request: :class:`thelma.models.iso.IsoRequest`

        :param create_copy: Is the future ISO a copy of an existing ISO
            (if so, a marker will be added to the label).
        :type create_copy: :class:`bool`
        :default create_copy: *True*`
        """
        highest_number = cls.__get_largest_iso_number(iso_request)
        iso_number = highest_number + 1
        ticket_number = iso_request.experiment_metadata.ticket_number
        label = cls.__ISO_LABEL_PATTERN % (ticket_number, iso_number)

        if create_copy:
            label += cls.__SEPARATING_CHAR
            label += cls.__ISO_LABEL_COPY_MARKER

        return label

    @classmethod
    def __get_largest_iso_number(cls, iso_request):
        """
        Returns the number of the largest ISO existing for this ISO request.
        """
        highest_number = 0
        for iso in iso_request.isos:
            number = cls.get_iso_number(iso)
            highest_number = max(highest_number, number)

        return highest_number

    @classmethod
    def get_iso_number(cls, iso):
        """
        Parses an ISO number from the label.
        """
        number_str = iso.label.split(cls.__SEPARATING_CHAR)[-1]
        if number_str == cls.__ISO_LABEL_COPY_MARKER:
            number_str = iso.label.split(cls.__SEPARATING_CHAR)[-2]
        try:
            number = int(number_str[3:])
        except ValueError:
            number = 0

        return number

    @classmethod
    def create_aliquot_plate_label(cls, iso, aliquot_number=1):
        """
        Creates a label for a future ISO aliuot plate. The aliquot number
        is only added, if there is more than one aliquot requested for this
        ISO or if it is larger than the requested number of aliqout (for
        additional plates).

        In all cases, the label will contain the plate set label specified
        by the user during experiment metadata file upload.

        :param iso: The ISO future plate belongs to.
        :type iso: :class:`thelma.models.iso.Iso`

        :param aliquot_number: Only added if there is more than one aliquot
            requested (see :class:`thelma.models.iso.IsoRequest`) or the
            number is larger than the number of originally requested plates.
        :type aliquot_number: :class:`int`
        :default aliquot_number: *1*`
        """
        iso_number = cls.get_iso_number(iso)
        label = cls.__ALIQUOT_PLATE_LABEL_PATTERN % (
                iso.iso_request.plate_set_label, iso_number)

        req_aliquots = iso.iso_request.number_aliquots
        if req_aliquots > 1 or aliquot_number > req_aliquots:
            suffix = cls.__ALIQUOT_PLATE_LABEL_SUFFIX % (aliquot_number)
            label += suffix

        return label


def get_stock_takeout_volume(stock_concentration, required_volume,
                             concentration):
    """
    Returns the volume that needs to be taken out of the stock in
    order to set up the desired concentration (round to 1 decimal
    place).

    :param stock_concentration: The stock concentration for the given
        molecule type in nM.
    :type stock_concentration: :class:`int`
    :rtype: :class:`float`

    :param required_volume: The required volume determined for a preparation
        position in ul.
    :type required_volume: positive number

    :param concentration: The concentration for the target position in nM.
    :type concentration: positive number

    :return: The volume to be taken from the stock in ul.
    """
    dil_factor = stock_concentration / float(concentration)
    take_out_volume = required_volume / dil_factor
    take_out_volume = round(take_out_volume, 1)
    return take_out_volume


class PrepIsoParameters(TransferParameters):
    """
    This is a list of parameters involved in of the processing of ISO
    preparation plates (generation and usage of prep plates).

    A prepIsoPlate has two states: INI and READY. At this, \'INI\' refers
    to the initial state right after the transfer from the stock. In \'READY\'
    state all dilutions have been carried out and the solutions are ready
    to be passed to the ISO plate (aliquot plate).

    :Note: Unlike in a normal ISO layout, there is no position type. Empty
        positions are not stored.
    """

    DOMAIN = 'iso_preparation'
    ALLOWS_UNTREATED_POSITIONS = False


    #: The molecule design pool (tag value: molecule design pool id).
    MOLECULE_DESIGN_POOL = MoleculeDesignPoolParameters.MOLECULE_DESIGN_POOL
    #: The position type (fixed, floating or mock).
    POSITION_TYPE = MoleculeDesignPoolParameters.POS_TYPE

    #: The barcode of the preferred stock tube (as determined by the
    #: ISO generation optimization query).
    STOCK_TUBE_BARCODE = 'stock_tube_barcode'
    #: The barcode of the preferred stock rack (as determined by the
    #: ISO generation optimization query).
    STOCK_RACK_BARCODE = 'stock_rack_barcode'

    #: The concentration in the preparation plate in nM (in most cases it
    #: equal to the ISO concentration).
    PREP_CONCENTRATION = 'preparation_concentration'
    #: The volume required to supply all child wells and the volume for
    #: the transfer to the ISO plate.
    REQUIRED_VOLUME = 'required_volume'

    #: The parent well is the well the RNAi agent has derived from in the
    #: dilution series. A well withou parent well got its RNAi agent from
    #: the stock.
    PARENT_WELL = 'parent_well'

    #: The target well are the ISO position of the ISO layout.
    #: The volume is the ISO volume.
    ISO_POSITIONS = TransferParameters.TARGET_WELLS

    REQUIRED = [MOLECULE_DESIGN_POOL, PREP_CONCENTRATION, REQUIRED_VOLUME,
                POSITION_TYPE]
    ALL = [MOLECULE_DESIGN_POOL, STOCK_TUBE_BARCODE, ISO_POSITIONS, POSITION_TYPE,
           PREP_CONCENTRATION, REQUIRED_VOLUME, PARENT_WELL, STOCK_RACK_BARCODE]

    ALIAS_MAP = {MOLECULE_DESIGN_POOL : MoleculeDesignPoolParameters.ALIAS_MAP[
                                                          MOLECULE_DESIGN_POOL],
                 POSITION_TYPE : MoleculeDesignPoolParameters.ALIAS_MAP[
                                                          POSITION_TYPE],
                 STOCK_TUBE_BARCODE : [],
                 STOCK_RACK_BARCODE : [],
                 PREP_CONCENTRATION : [IsoParameters.ISO_CONCENTRATION],
                 REQUIRED_VOLUME : ['total volume'],
                 PARENT_WELL : [],
                 ISO_POSITIONS : ['iso_positions']}

    DOMAIN_MAP = {MOLECULE_DESIGN_POOL : DOMAIN,
                  POSITION_TYPE : DOMAIN,
                  STOCK_TUBE_BARCODE : DOMAIN,
                  STOCK_RACK_BARCODE : DOMAIN,
                  PREP_CONCENTRATION : DOMAIN,
                  REQUIRED_VOLUME : DOMAIN,
                  PARENT_WELL : DOMAIN,
                  ISO_POSITIONS : TransferParameters.DOMAIN}

    #: The minimum volume that can be transferred between wells
    #: (without Biomek) in ul.
    WELL_MIN_TRANSFER_VOLUME = 1

    #: The maximum dilution factor for a dilution step within the Biomek series.
    MAX_DILUTION_FACTOR_BIOMEK = 10
    #: The maximum dilution factor for a dilution step within a CyBio series.
    MAX_DILUTION_FACTOR_CYBIO = 100


class PrepIsoPosition(TransferPosition):
    """
    This class represents a position in a prepIsoPlate.
    """

    PARAMETER_SET = PrepIsoParameters

    #: The delimiter for the different ISO transfer target infos.
    POSITION_DELIMITER = '-'

    def __init__(self, rack_position, molecule_design_pool, required_volume,
                 position_type, transfer_targets, prep_concentration=None,
                 parent_well=None, stock_tube_barcode=None,
                 stock_rack_barcode=None):
        """
        Constructor:

        :param rack_position: The position within the rack.
        :type rack_position: :class:`thelma.models.rack.RackPosition`

        :param molecule_design_pool: The molecule design pool for this position.
        :type molecule_design_pool:  placeholder or
            :class:`thelma.models.moleculedesign.MoleculeDesignPool`

        :param position_type: The position type (fixed, floating or mock).
        :type position_type: :class:`str`

        :param required_volume: The volume required to supply all child wells
            and the volume for the transfer to the ISO plate.
        :type required_volume: positive number

        :param transfer_targets: The transfer targets are the ISO positions
             of the ISO layout. The transfer volume is the same as the ISO
             volume.
        type transfer_targets: List of transfer target objects.

        :param prep_concentration: The concentration in the preparation plate
            (in most cases equal to the ISO concentration).
        :type prep_concentration: positive number

        :param parent_well: The parent well from which this well has obtained
            its RNAi agent. The concentration of the parent well must
            be as least as high as this wells concentration.
        :type parent_well: :class:`thelma.models.rack.RackPosition`

        :param stock_tube_barcode: The barcode of the stock tube of the prime
            hit of the optimisation query.
        :type stock_tube_barcode: :class:`str`

        :param stock_rack_barcode: The barcode of the stock rack of the prime
            hit of the optimisation query.
        :type stock_rack_barcode: :class:`str`
        """

        TransferPosition.__init__(self, transfer_targets=transfer_targets,
                                  rack_position=rack_position,
                                  molecule_design_pool=molecule_design_pool)
        self.position_type = position_type # overwrite from base class

        if (position_type == MOCK_POSITION_TYPE and \
                            not molecule_design_pool == MOCK_POSITION_TYPE) or \
                            (molecule_design_pool == MOCK_POSITION_TYPE and \
                             not position_type == MOCK_POSITION_TYPE):
            msg = 'For mock positions both molecule design pool ID and ' \
                  'position type must be "%s".' % (MOCK_POSITION_TYPE)
            raise ValueError(msg)

        if not molecule_design_pool == MOCK_POSITION_TYPE and \
                                not is_valid_number(prep_concentration):
            msg = 'The preparation concentration must be a positive number ' \
                  '(obtained: %s).' % (prep_concentration)
            raise ValueError(msg)
        if not is_valid_number(required_volume):
            msg = 'The required volume must a positive number (obtained: %s)' \
                  % (required_volume)
            raise ValueError(msg)

        if not stock_tube_barcode is None and \
                                not isinstance(stock_tube_barcode, basestring):
            msg = 'The stock tube barcode must be a string (obtained: %s).' \
                   % (stock_tube_barcode.__class__.__name__)
            raise TypeError(msg)
        if not stock_rack_barcode is None and \
                                not isinstance(stock_rack_barcode, basestring):
            msg = 'The stock rack barcode must be a string (obtained: %s).' \
                   % (stock_rack_barcode.__class__.__name__)
            raise TypeError(msg)

        if not parent_well is None and not isinstance(parent_well, RackPosition):
            msg = 'The parent well design must be a RackPosition object ' \
                  '(obtained: %s).' % (parent_well.__class__.__name__)
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

        #: The requested preparation concentration.
        self.prep_concentration = get_converted_number(prep_concentration)

        #: The volume required to supply all child wells and the volume for
        #: the transfer to the ISO plate.
        self.required_volume = float(required_volume)

        #: The well the RNAi agent in this position originates from (or *None*
        #: if it originates from the stock).
        self.parent_well = parent_well

        #: The supplier for molecule (fixed positions only - not stored in
        #: the DB).
        self._supplier = None

        if self.is_mock:
            self.prep_concentration = None
            self.stock_rack_barcode = None
            self.stock_tube_barcode = None
            self.parent_well = None

    @property
    def hash_value(self):
        """
        The hash is comprised of molecule design pool ID and preparation
        concentration. It must be unique within a layout.
        """
        conc_str = get_trimmed_string(self.prep_concentration)
        return '%s%s' % (self.molecule_design_pool_id, conc_str)

    @property
    def is_inactivated(self):
        """
        A position is set to inactivated if the tube picker has not been
        capable to find a valid stock tube.
        """
        if self.stock_tube_barcode is None and not self.is_mock:
            return True
        else:
            return False

    @classmethod
    def create_mock_position(cls, rack_position, required_volume,
                             transfer_targets):
        """
        Returns a preparation position with mock molecule design pool.

        :param rack_position: The position within the rack.
        :type rack_position: :class:`thelma.models.rack.RackPosition`

        :param required_volume: The volume required to supply all child wells
            and the volume for the transfer to the ISO plate.
        :type required_volume: positive number

        :param transfer_targets: The transfer targets are the ISO positions
             of the ISO layout. The transfer volume is the same as the ISO
             volume.
        type transfer_targets: List of transfer target objects.
        """
        return PrepIsoPosition(rack_position=rack_position,
                       molecule_design_pool=MOCK_POSITION_TYPE,
                       position_type=MOCK_POSITION_TYPE,
                       required_volume=required_volume,
                       transfer_targets=transfer_targets)

    def get_stock_takeout_volume(self):
        """
        Returns the volume that needs to be taken out of the stock in
        order to set up the desired concentration (round to 1 decimal
        place).
        Return *None* for non-starting wells.

        :raise ValueError: if the stock concentration is *None*

        :rtype: :class:`float`
        """
        if not self.parent_well is None: return None
        if self.is_mock: return 0
        if self.stock_concentration is None:
            raise ValueError('The stock concentration must not be None!')
        take_out_volume = get_stock_takeout_volume(self.stock_concentration,
                                self.required_volume, self.prep_concentration)
        return take_out_volume

    def get_completed_copy(self, stock_tube_barcode, stock_rack_barcode,
                           molecule_design_pool=None):
        """
        Returns a copy of this PrepIsoPosition which stock tube barcode
        stock rack barcode and a defined molecule design pool ID.

        :param stock_tube_barcode: The barcode of the stock tube the optimizer
            has found as prime hit for this molecule design pool ID.
        :type stock_tube_barcode: :class:`str`

        :param stock_rack_barcode: The barcode of the stock rack the optimizer
            has found as prime hit for this molecule design pool ID.
        :type stock_rack_barcode: :class:`str`

        :param molecule_design_poo: The molecule design pool for this
            position.
        :type molecule_design_pool:
            :class:`thelma.models.moleculedesign.MoleculeDesignPool`
        :default molecule_design_pool: *None*

        :return: The PrepIsoPosition or *None* if any value is invalid.
        """
        if self.is_floating and molecule_design_pool is None:
            return None
        if self.is_mock: return None

        if not molecule_design_pool is None and \
                      not isinstance(molecule_design_pool, MoleculeDesignPool):
            return None
        if not isinstance(stock_tube_barcode, basestring): return None
        if not isinstance(stock_rack_barcode, basestring): return None

        if molecule_design_pool is None:
            molecule_design_pool = self.molecule_design_pool

        prep_pos = PrepIsoPosition(rack_position=self.rack_position,
                               molecule_design_pool=molecule_design_pool,
                               position_type=self.position_type,
                               stock_tube_barcode=stock_tube_barcode,
                               stock_rack_barcode=stock_rack_barcode,
                               prep_concentration=self.prep_concentration,
                               required_volume=self.required_volume,
                               transfer_targets=self.transfer_targets,
                               parent_well=self.parent_well)
        return prep_pos

    def set_supplier(self, supplier):
        """
        Sets the supplier for the molecule (fixed positions only, not stored in
        the DB).

        :param supplier: The supplier for the molecule.
        :type supplier: :class:`thelma.models.organization.Organization`

        :raises ValueError: If the position is a mock or a floating.
        :raises TypeError: If the supplier is not an Organisation.
        """
        if self.is_mock or self.is_floating:
            msg = 'Suppliers for mock and floating positions are not supported!'
            raise ValueError(msg)

        if not isinstance(supplier, Organization):
            msg = 'The supplier must be an Organization object ' \
                  '(obtained: %s).' % (supplier.__class__.__name__)
            raise TypeError(msg)

        self._supplier = supplier

    def get_supplier(self):
        """
        Returns the supplier.
        """
        return self._supplier

    def inactivate(self):
        """
        Inactivates the position (setting stock tube barcode and stock rack
        barcode to *None*). A position is set to inactivated if the tube
        picker has not been capable to find a valid stock tube.
        """
        self.stock_tube_barcode = None
        self.stock_rack_barcode = None

    def _get_parameter_values_map(self):
        """
        Returns a map containing the value for each parameter.
        """
        return {self.PARAMETER_SET.MOLECULE_DESIGN_POOL :
                                                self.molecule_design_pool,
                self.PARAMETER_SET.POSITION_TYPE : self.position_type,
                self.PARAMETER_SET.STOCK_TUBE_BARCODE : self.stock_tube_barcode,
                self.PARAMETER_SET.STOCK_RACK_BARCODE : self.stock_rack_barcode,
                self.PARAMETER_SET.PREP_CONCENTRATION : self.prep_concentration,
                self.PARAMETER_SET.REQUIRED_VOLUME : self.required_volume,
                self.PARAMETER_SET.PARENT_WELL : self.parent_well,
                self.PARAMETER_SET.ISO_POSITIONS : self.transfer_targets}

    def __eq__(self, other):
        if not isinstance(other, PrepIsoPosition): return False
        return self.rack_position == other.rack_position and \
             self.molecule_design_pool_id == other.molecule_design_pool_id and \
             self.prep_concentration == other.prep_concentration

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        str_format = '<%s rack position: %s, molecule design pool: %s, type: ' \
                     '%s, preparation concentration: %s, parent well: %s, ' \
                     'required volume: %s, target wells: %s>'
        if self.parent_well is None:
            pw_label = 'None'
        else:
            pw_label = self.parent_well.label
        params = (self.__class__.__name__, self.rack_position,
                  self.molecule_design_pool_id, self.position_type,
                  self.prep_concentration, pw_label, self.required_volume,
                  self.get_targets_tag_value())
        return str_format % params


class PrepIsoLayout(TransferLayout):
    """
    A working container for ISO preparation layouts.

    Within the layout, each hash (combination of molecule design pool and
    preparation concentration) must be unique. For the \'INI\' state of
    optimisation or 96-well cases, each position (starting well = position
    without parent well) must be unique.
    """
    WORKING_POSITION_CLASS = PrepIsoPosition

    def add_position(self, working_position):
        """
        Adds a :class:`Working_position` to the layout.

        :Note: 96-well preparation have stricter constraints than 384-well
            layouts.

        :param working_position: The transfer position to be added.
        :type working_position: :class:`PrepIsoPosition`
        :raises TypeError: If the added position is not a
            :class:`PrepIsoPosition` object.
        :raises ValueError: If there is already a prep position with that
            hash in the layout (96-well only).
        """
        if not isinstance(working_position, self.WORKING_POSITION_CLASS):
            msg = 'A position to be added must be a %s object (obtained ' \
                  'type: %s).' % (self.WORKING_POSITION_CLASS,
                                  working_position.__class__)
            raise TypeError(msg)

        if self.shape.name == RACK_SHAPE_NAMES.SHAPE_96:
            hash_value = working_position.hash_value
            hash_map = self.get_hash_map()
            if hash_value in hash_map:
                msg = 'Duplicate hash value %s!' % (hash_value)
                raise ValueError(msg)

        TransferLayout.add_position(self, working_position)

    def check_starting_well_uniqueness(self):
        """
        Checks whether the molecule design pools of all molecule design pools
        without parent well are unique (required for INI state of 96-well
        plates).

        :Note: 384-well layout always return *True*

        :return: :class:`bool`
        """
        if self.shape.name == RACK_SHAPE_NAMES.SHAPE_384: return True

        md_pools = []
        for prep_pos in self._position_map.values():
            if not prep_pos.parent_well is None: continue
            md_pool = prep_pos.molecule_design_pool_id
            if md_pool in md_pools: return False
            md_pools.append(md_pool)

        return True

    def get_starting_wells(self):
        """
        Returns a dictionary with starting well, that is well without
        parent well that have obtained their RNAi agent from the stock
        instead of from another well.

        :return: dictionary with rack positions as keys and PrepIsoPosition
            objects as values.
        """
        starting_positions = dict()
        for rack_pos, prep_pos in self._position_map.iteritems():
            if prep_pos.parent_well is None:
                starting_positions[rack_pos] = prep_pos
        return starting_positions

    def get_hash_map(self):
        """
        Returns a map with all hashes as key and the referring
        prepIsoPosition object as value (96-well layouts only). 384-layouts
        return None automatically.

        :raises ValueError: If there are duplicate hash.
        """
        if self.shape.name == RACK_SHAPE_NAMES.SHAPE_384: return None

        hash_map = dict()
        for prep_pos in self._position_map.values():
            hash_value = prep_pos.hash_value
            if hash_map.has_key(hash_value):
                msg = 'Duplicate hash %s!' % (hash_value)
                raise ValueError(msg)
            hash_map[hash_value] = prep_pos
        return hash_map

    def has_unconverted_floatings(self):
        """
        Returns *True* if there are still unconverted floating positions in
        this layout.
        """
        for prep_pos in self._position_map.values():
            if not prep_pos.is_floating: continue
            if prep_pos.stock_tube_barcode is None: return True

        return False

    def get_md_pool_concentration_map(self):
        """
        Returns a dictionary with all the preparation positions of the layout
        sorted by molecule design pool (map key) and concentration
        (map as value).
        """
        mdp_conc_map = dict()

        for prep_pos in self._position_map.values():
            md_pool = prep_pos.molecule_design_pool
            if not mdp_conc_map.has_key(md_pool):
                conc_map = dict()
                mdp_conc_map[md_pool] = conc_map
            else:
                conc_map = mdp_conc_map[md_pool]
            conc_map[prep_pos.prep_concentration] = prep_pos
            mdp_conc_map[md_pool] = conc_map

        return mdp_conc_map

    def get_supplier_map(self):
        """
        Returns a dictionary mapping supplier IDs onto the molecule design pool
        IDs they are meant for (no mocks and no floatings).
        """
        supplier_map = dict()

        for prep_pos in self._position_map.values():
            if prep_pos.is_mock or prep_pos.is_floating: continue
            pool_id = prep_pos.molecule_design_pool_id
            if supplier_map.has_key(pool_id): continue
            supplier = prep_pos.get_supplier()
            if supplier is None:
                supplier_id = IsoPosition.ANY_SUPPLIER_INDICATOR
            else:
                supplier_id = supplier.id
            supplier_map[pool_id] = supplier_id

        return supplier_map


class PrepIsoLayoutConverter(TransferLayoutConverter):
    """
    Converts an rack_layout into a :class:`PrepIsoLayout`.
    """

    NAME = 'ISO Preparation Layout Converter'

    PARAMETER_SET = PrepIsoParameters
    WORKING_LAYOUT_CLASS = PrepIsoLayout

    def __init__(self, rack_layout, log):
        """
        Constructor:

        :param rack_layout: The rack layout containing the preparation data.
        :type rack_layout: :class:`thelma.models.racklayout.RackLayout`

        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`
        """
        TransferLayoutConverter.__init__(self, rack_layout, log)

        # intermediate storage of invalid rack positions
        self.__missing_pool = None
        self.__invalid_pool = None
        self.__missing_type = None
        self.__missing_prep_conc = None
        self.__invalid_prep_conc = None
        self.__missing_req_vol = None
        self.__invalid_req_vol = None
        self.__invalid_parent_well = None
        self.__inconsistent_type = None

    def reset(self):
        """
        Resets all attributes except for the :attr:`rack_layout`.
        """
        TransferLayoutConverter.reset(self)
        self.__missing_pool = []
        self.__invalid_pool = []
        self.__missing_type = []
        self.__missing_prep_conc = []
        self.__invalid_prep_conc = []
        self.__missing_req_vol = []
        self.__invalid_req_vol = []
        self.__invalid_parent_well = []
        self.__inconsistent_type = []

    def _obtain_working_position(self, parameter_map):
        """
        Derives a working position from a parameter map (including validity
        checks).
        """
        rack_position = parameter_map[self._RACK_POSITION_KEY]
        pool_id = parameter_map[self.PARAMETER_SET.MOLECULE_DESIGN_POOL]
        pos_type = parameter_map[self.PARAMETER_SET.POSITION_TYPE]
        tube_barcode = parameter_map[self.PARAMETER_SET.STOCK_TUBE_BARCODE]
        rack_barcode = parameter_map[self.PARAMETER_SET.STOCK_RACK_BARCODE]
        prep_concentration = parameter_map[
                                    self.PARAMETER_SET.PREP_CONCENTRATION]
        req_volume = parameter_map[self.PARAMETER_SET.REQUIRED_VOLUME]
        parent_well = parameter_map[self.PARAMETER_SET.PARENT_WELL]
        transfer_targets = parameter_map[self.PARAMETER_SET.TARGET_WELLS]

        # Additional dilution series position do not have to have associated
        # ISO positions.
        if transfer_targets is None: transfer_targets = []

        is_valid = True
        if pool_id is None and pos_type is None:
            return None
        elif not self._are_valid_transfer_targets(transfer_targets,
                                                  rack_position):
            is_valid = False

        rack_pos_label = rack_position.label

        if pool_id is None:
            self.__missing_pool.append(rack_pos_label)
            is_valid = False
        if pos_type is None:
            self.__missing_type.append(rack_pos_label)
            is_valid = False
        else:
            mock_value = MOCK_POSITION_TYPE
            if (pos_type == mock_value and not pool_id == mock_value) or \
                        (not pos_type == mock_value and pool_id == mock_value):
                self.__inconsistent_type.append(rack_pos_label)
                is_valid = False

        if pool_id == MOCK_POSITION_TYPE:
            pool = pool_id
        else:
            pool = self._get_molecule_design_pool_for_id(pool_id,
                                                         rack_pos_label)
            if pool is None:
                is_valid = False
            elif prep_concentration is None:
                self.__missing_prep_conc.append(rack_pos_label)
                is_valid = False
        if not prep_concentration is None and \
                                not is_valid_number(prep_concentration):
            info = '%s (%s)' % (rack_pos_label, prep_concentration)
            self.__invalid_prep_conc.append(info)
            is_valid = False

        if req_volume is None:
            self.__missing_req_vol.append(rack_pos_label)
            is_valid = False
        if not is_valid_number(req_volume):
            info = '%s (%s)' % (rack_pos_label, req_volume)
            self.__invalid_req_vol.append(info)
            is_valid = False

        if not parent_well is None:
            try:
                parent_well = get_rack_position_from_label(parent_well)
            except ValueError:
                info = '%s (label: %s)' % (rack_pos_label, parent_well)
                self.__invalid_parent_well.append(info)
                is_valid = False

        if not is_valid: return None
        pp = PrepIsoPosition(rack_position=rack_position,
                               molecule_design_pool=pool,
                               position_type=pos_type,
                               prep_concentration=prep_concentration,
                               required_volume=req_volume,
                               transfer_targets=transfer_targets,
                               stock_tube_barcode=tube_barcode,
                               stock_rack_barcode=rack_barcode,
                               parent_well=parent_well)
        return pp

    def _record_additional_position_errors(self):
        """
        Records errors that have been collected for rack positions.
        """
        TransferLayoutConverter._record_additional_position_errors(self)

        if len(self.__missing_pool) > 0:
            msg = 'The molecule design pool IDs for the following rack ' \
                  'positions are missing: %s.' \
                  % (', '.join(sorted(self.__missing_pool)))
            self.add_error(msg)

        if len(self.__missing_type) > 0:
            msg = 'The position type for the following positions are ' \
                  'missing: %s.' % (', '.join(sorted(self.__missing_type)))
            self.add_error(msg)

        if len(self.__missing_prep_conc) > 0:
            msg = 'The following rack positions do not have a preparation ' \
                  'concentrations: %s.' \
                   % (', '.join(sorted(self.__missing_prep_conc)))
            self.add_error(msg)
        if len(self.__invalid_prep_conc) > 0:
            msg = 'The preparation concentration must be a positive number. ' \
                  'The following rack positions have invalid preparation ' \
                  'concentrations: %s.' \
                   % (', '.join(sorted(self.__invalid_prep_conc)))
            self.add_error(msg)

        if len(self.__missing_req_vol) > 0:
            msg = 'The following rack positions do not have a required volume ' \
                  'specification: %s.' \
                  % (', '.join(sorted(self.__missing_req_vol)))
            self.add_error(msg)
        if len(self.__invalid_req_vol) > 0:
            msg = 'The required volume must be a positive number. The ' \
                  'following rack positions have invalid required volume ' \
                  'specifications: %s.' % \
                  (', '.join(sorted(self.__invalid_req_vol)))
            self.add_error(msg)

        if len(self.__invalid_parent_well) > 0:
            msg = 'The following rack positions have invalid parent well ' \
                  'labels: %s.' \
                  % (', '.join(sorted(self.__invalid_parent_well)))
            self.add_error(msg)

        if len(self.__inconsistent_type) > 0:
            msg = 'The mock positions both molecule design pool ID and ' \
                  'position type must be "%s". The types for the following ' \
                  'positions are inconsistent: %s.' \
                   % (MOCK_POSITION_TYPE,
                      ', '.join(sorted(self.__inconsistent_type)))
            self.add_error(msg)

    def _initialize_working_layout(self, shape):
        """
        Initialises the working layout.
        """
        return PrepIsoLayout(shape=shape)

    def _perform_layout_validity_checks(self, working_layout):
        """
        Use this method to check the validity of the generated layout.
        """
        if not working_layout.check_starting_well_uniqueness():
            msg = 'The generated preparation plate layout contains duplicate ' \
                  'starting wells. This is a programming error, please ' \
                  'contact the IT department.'
            self.add_error(msg)


class PrepIsoValueDeterminer(ValueDeterminer):
    """
    This is a special rack sector determiner. It sorts preparation positions
    by preparation concentration. The molecule design pools of parent and child
    wells must be shared.

    **Return Value:** A map containing the values for the different sectors.
    """

    NAME = 'Preparation Rack Sector Value Determiner'

    def __init__(self, prep_layout, attribute_name, log, number_sectors=4):
        """
        Constructor:

        :param prep_layout: The preparation layout whose positions to check.
        :type prep_layout: :class:`PrepIsoLayout`

        :param attribute_name: The name of the attribute to be determined.
        :type attribute_name: :class:`str`

        :param number_sectors: The number of rack sectors.
        :type number_sectors: :class:`int`
        :default number_sectors: *4*
        """
        ValueDeterminer.__init__(self, working_layout=prep_layout,
                                      attribute_name=attribute_name,
                                      number_sectors=number_sectors,
                                      log=log)

    def _check_input(self):
        """
        Checks the input values.
        """
        ValueDeterminer._check_input(self)

        self._check_input_class('preparation layout', self.working_layout,
                                PrepIsoLayout)

    def _ignore_position(self, working_pos):
        """
        Use this method to add conditions under which a position is ignored.
        """
        if working_pos.is_mock:
            return True
        else:
            return False


class PrepIsoRackSectorAssociator(RackSectorAssociator):
    """
    A special rack sector associator for preparation layouts.

    **Return Value:** A list of lists (each list containing the indices of
        rack sector associated with one another).
    """

    NAME = 'Preparation rack sector associator'

    SECTOR_ATTR_NAME = 'prep_concentration'
    WORKING_LAYOUT_CLS = PrepIsoLayout

    def __init__(self, prep_layout, log, number_sectors=4):
        """
        Constructor:

        :param prep_layout: The preparation layout whose positions to check.
        :type prep_layout: :class:`PrepIsoLayout`

        :param number_sectors: The number of rack sectors.
        :type number_sectors: :class:`int`
        :default number_sectors: *4*

        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`
        """
        RackSectorAssociator.__init__(self, working_layout=prep_layout,
                                      log=log, number_sectors=number_sectors)

    def _init_value_determiner(self):
        """
        Initialises the value determiner for the preparation concentrations.
        """
        value_determiner = PrepIsoValueDeterminer(log=self.log,
                        prep_layout=self.working_layout,
                        attribute_name=self.SECTOR_ATTR_NAME,
                        number_sectors=self.number_sectors)
        return value_determiner

    def _get_molecule_design_pool(self, working_position):
        """
        Returns the molecule design pools of a working position.
        """
        prep_pos = working_position
        if prep_pos is None:
            md = PrepIsoPosition.NONE_REPLACER
        elif prep_pos.is_mock:
            md = PrepIsoPosition.NONE_REPLACER
        else:
            md = prep_pos.molecule_design_pool_id
        return md


class PrepIsoAssociationData(AssociationData):
    """
    A special association data class for preparation layouts which also stores
    the required volumes for each rack sector.

    :Note: All attributes are immutable.
    """

    def __init__(self, preparation_layout, log):
        """
        Constructor:

        :param preparation_layout: The prepartion layout whose sectors to
            associate.
        :type preparation_layout: :class:`PrepIsoLayout`

        :param log: The log to write into (not stored in the object).
        :type log: :class:`thelma.ThelmaLog`
        """
        AssociationData.__init__(self, working_layout=preparation_layout,
                                 log=log)

        #: The required volumes for each rack sector.
        self.__sector_req_volumes = None

        self.__find_required_volumes(preparation_layout, log)

    @property
    def sector_req_volumes(self):
        """
        The required volumes for each rack sector.
        """
        return self.__sector_req_volumes

    def _find_concentrations(self, iso_layout):
        """
        Finds all different concentrations in the layout.
        """
        prep_layout = iso_layout
        prep_concentrations = set()
        for prep_pos in prep_layout.working_positions():
            prep_concentrations.add(prep_pos.prep_concentration)
        return prep_concentrations

    def _init_associator(self, working_layout, log):
        """
        Initialises the associator.
        """
        associator = PrepIsoRackSectorAssociator(prep_layout=working_layout,
                                                 log=log, number_sectors=4)
        return associator

    def __find_required_volumes(self, preparation_layout, log):
        """
        Finds the required volumes for each rack sector.

        :raises TypeError: If the required volumes are inconsistent.
        """
        determiner = PrepIsoValueDeterminer(prep_layout=preparation_layout,
                                    attribute_name='required_volume',
                                    log=log, number_sectors=self.number_sectors)
        self.__sector_req_volumes = determiner.get_result()

        if self.__sector_req_volumes is None:
            msg = ', '.join(determiner.get_messages())
            raise ValueError(msg)


class IsoControlRackParameters(TransferParameters):
    """
    This is a list of parameters involved in of the processing of ISO
    controls (for 384-well cases).

    ISO controls rack provide the controls for all ISOs of an ISO job.
    """

    DOMAIN = 'iso_control_rack'
    ALLOWS_UNTREATED_POSITIONS = False


    #: The molecule design pool (tag value: molecule design pool id).
    MOLECULE_DESIGN_POOL = MoleculeDesignPoolParameters.MOLECULE_DESIGN_POOL

    #: The target well are the preparation position of the preparation layout.
    #: The volume is the stock take out volume.
    PREP_POSITIONS = TransferParameters.TARGET_WELLS

    REQUIRED = [MOLECULE_DESIGN_POOL, PREP_POSITIONS]
    ALL = [MOLECULE_DESIGN_POOL, PREP_POSITIONS]

    ALIAS_MAP = {MOLECULE_DESIGN_POOL :
                   MoleculeDesignPoolParameters.ALIAS_MAP[MOLECULE_DESIGN_POOL],
                 PREP_POSITIONS : ['preparation_positions']}

    DOMAIN_MAP = {MOLECULE_DESIGN_POOL : DOMAIN,
                  PREP_POSITIONS : TransferParameters.DOMAIN}


class IsoControlRackPosition(TransferPosition):
    """
    This class represents a position in an ISO control stock rack.
    """

    PARAMETER_SET = IsoControlRackParameters

    def __init__(self, rack_position, molecule_design_pool, transfer_targets):
        """
        Constructor:

        :param rack_position: The position within the rack.
        :type rack_position: :class:`thelma.models.rack.RackPosition`

        :param molecule_design_pool: The molecule design pool for this position.
        :type molecule_design_pool:  placeholder or
            :class:`thelma.models.moleculedesign.MoleculeDesignPool`

        :param transfer_targets: The volume required to supply all child wells
            and the volume for the transfer to the ISO plate.
        :type transfer_targets: :class:`list` of :class:`TransferTarget` objects
        """
        TransferPosition.__init__(self, rack_position=rack_position,
                                  molecule_design_pool=molecule_design_pool,
                                  transfer_targets=transfer_targets)

        if not self.is_fixed:
            msg = 'ISO control rack positions must be fixed positions!'
            raise ValueError(msg)
        self.position_type = None # we do not need position types here

        if transfer_targets is None or len(transfer_targets) < 1:
            msg = 'An ISO control rack position must have at least one ' \
                  'transfer target!'
            raise ValueError(msg)

    def _get_parameter_values_map(self):
        """
        Returns a map with key = parameter name, value = associated attribute.
        """
        return {self.PARAMETER_SET.MOLECULE_DESIGN_POOL :
                                                self.molecule_design_pool,
                self.PARAMETER_SET.PREP_POSITIONS : self.transfer_targets}

    def __eq__(self, other):
        return isinstance(other, IsoControlRackPosition) and \
            self.rack_position == other.rack_position and \
            self.molecule_design_pool == other.molecule_design_pool and \
            self.transfer_targets == other.transfer_targets

    def __repr__(self):
        str_format = '<%s rack position: %s, molecule design pool ID: %s, ' \
                     'preparation layout target: %s>'
        params = (self.__class__.__name__, self.rack_position,
                  self.molecule_design_pool_id, self.get_targets_tag_value())
        return str_format % params


class IsoControlRackLayout(TransferLayout):
    """
    A working layout for ISO control stock rack (for 384-well ISO jobs).
    """

    WORKING_POSITION_CLASS = IsoControlRackPosition

    def __init__(self): # pylint: disable=W0231
        """
        Constructor:

        :param shape: The rack shape.
        :type shape: :class:`thelma.models.rack.RackShape`
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


class IsoControlRackLayoutConverter(TransferLayoutConverter):
    """
    Converts a rack layout into a :class:`IsoControlRackLayout`
    """

    NAME = 'ISO Control Rack Layout Converter'

    PARAMETER_SET = IsoControlRackParameters
    WORKING_LAYOUT_CLASS = IsoControlRackLayout

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

    def reset(self):
        """
        Resets all attributes except for the :attr:`rack_layout`.
        """
        TransferLayoutConverter.reset(self)
        self.__missing_pool = []
        self.__missing_transfer_targets = []

    def _obtain_working_position(self, parameter_map):
        """
        Derives a working position from a parameter map (including validity
        checks).
        """
        rack_position = parameter_map[self._RACK_POSITION_KEY]
        pool_id = parameter_map[self.PARAMETER_SET.MOLECULE_DESIGN_POOL]
        transfer_targets = parameter_map[self.PARAMETER_SET.TARGET_WELLS]

        if pool_id is None and transfer_targets is None:
            return None

        is_valid = True

        if transfer_targets is None:
            self.__missing_transfer_targets.append(rack_position.label)
            is_valid = False
        elif not self._are_valid_transfer_targets(transfer_targets,
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
            control_pos = IsoControlRackPosition(rack_position=rack_position,
                                            molecule_design_pool=pool,
                                            transfer_targets=transfer_targets)
            return control_pos
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

        if len(self.__missing_transfer_targets) > 0:
            msg = 'A control rack position must have at least one transfer ' \
                  'target. The following rack position do not have a ' \
                  'transfer target: %s.' \
                   % (', '.join(sorted(self.__missing_transfer_targets)))
            self.add_error(msg)

    def _initialize_working_layout(self, shape):
        """
        Initialises the working layout.
        """
        return IsoControlRackLayout()

    def _perform_layout_validity_checks(self, working_layout):
        """
        Use this method to check the validity of the generated layout.
        """
        duplicate_pools = working_layout.get_duplicate_molecule_design_pools()
        if len(duplicate_pools) > 0:
            msg = 'There are duplicate molecule design pools in the control ' \
                  'layout. This is a programming error, please contact the ' \
                  'the IT department.'
            self.add_error(msg)


class RequestedStockSample(object):
    """
    A helper class storing the values required for a stock tube picking query.
    It is not stored in the DB.
    """

    def __init__(self, pool, stock_concentration,
                 take_out_volume, stock_tube_barcode, stock_rack_barcode,
                 target_position):
        """
        Constructor:

        :param pool: The molecule design pool we need a sample for.
        :type pool: :class:`thelma.models.moleculedesign.MoleculeDesignPool`

        :param stock_concentration: The stock concentration for the molecule
            type of the molecule design pool in nM.
        :type stock_concentration: Positive number.

        :param take_out_volume: The requested volume in ul (volume that
            needs to be taken from the stock).
        :type take_out_volume: positive number

        :param stock_tube_barcode: The barcode of the stock tube picked
            by the :class:`IsoCreator`.
        :type stock_tube_barcode: :class:`basestring`

        :param stock_rack_barcode: The barcode of the rack holding the stock
            tube as picked by the :class:`IsoCreator`.
        :type stock_rack_barcode: :class:`basestring`

        :param target_position: The target rack position of the stock tube in
            the stock rack (after tube handling).
        :type target_position: :class:`thelma.models.rack.RackPosition`

        """
        #: The molecule design pool we need a sample for.
        self.pool = pool
        #: The requested stock concentration in nM.
        self.stock_concentration = stock_concentration
        #: The requested volume in ul.
        self.take_out_volume = take_out_volume
        #: The barcode of the stock tube picked by the ISO creator.
        self.stock_tube_barcode = stock_tube_barcode
        #: The barcode of the rack holding the stock tube as picked by the
        #: ISO creator.
        self.stock_rack_barcode = stock_rack_barcode
        #: The target rack position of the stock tube in the stock rack.
        self.target_position = target_position

        #: The tube candidate that has been picked for this requested molecule.
        self.tube_candidate = None

    @classmethod
    def from_prep_pos(cls, prep_pos):
        """
        Factory method creating a :class:`RequestedStockTube` object from
        a preparation position.
        """

        take_out_volume = prep_pos.get_stock_takeout_volume()
        return RequestedStockSample(take_out_volume=take_out_volume,
                    stock_concentration=prep_pos.stock_concentration,
                    pool=prep_pos.molecule_design_pool,
                    stock_tube_barcode=prep_pos.stock_tube_barcode,
                    stock_rack_barcode=prep_pos.stock_rack_barcode,
                    target_position=prep_pos.rack_position)

    @classmethod
    def from_control_pos(cls, control_pos, prep_pos, number_isos):
        """
        Factory method creating a :class:`RequestedStockTube` object from
        a control position.
        """
        plate_volume = 0
        for tt in control_pos.transfer_targets:
            plate_volume += tt.transfer_volume
        total_volume = plate_volume * number_isos

        return RequestedStockSample(take_out_volume=total_volume,
                    pool=control_pos.molecule_design_pool,
                    stock_concentration=prep_pos.stock_concentration,
                    stock_tube_barcode=prep_pos.stock_tube_barcode,
                    stock_rack_barcode=prep_pos.stock_rack_barcode,
                    target_position=control_pos.rack_position)


    def __repr__(self):
        str_format = '<%s molecule design pool: %s, stock take ' \
                     'volume: %.1f ul, tube: %s, rack: %s, target position: %s>'
        params = (self.__class__.__name__, self.pool,
                  self.take_out_volume, self.stock_tube_barcode,
                  self.stock_rack_barcode, self.target_position)
        return str_format % params
