"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Base classes and constants involved in pool stock samples creation tasks.

AAB
"""
from thelma.tools.semiconstants import PIPETTING_SPECS_NAMES
from thelma.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.tools.semiconstants import get_min_transfer_volume
from thelma.tools.iso.base import StockRackLayout
from thelma.tools.iso.base import StockRackLayoutConverter
from thelma.tools.iso.base import StockRackParameters
from thelma.tools.iso.base import StockRackPosition
from thelma.tools.iso.base import _ISO_LABELS_BASE
from thelma.tools.stock.base import \
    get_default_stock_concentration
from thelma.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.tools.utils.base import get_trimmed_string
from thelma.tools.utils.base import is_larger_than
from thelma.tools.utils.base import round_up
from thelma.tools.utils.converters import \
    MoleculeDesignPoolLayoutConverter
from thelma.tools.utils.layouts import FIXED_POSITION_TYPE
from thelma.tools.utils.layouts import MoleculeDesignPoolLayout
from thelma.tools.utils.layouts import MoleculeDesignPoolParameters
from thelma.tools.utils.layouts import MoleculeDesignPoolPosition
from thelma.entities.moleculedesign import MoleculeDesignPoolSet
from thelma.entities.tagging import Tag


__docformat__ = 'reStructuredText en'

__all__ = ['LABELS',
           'DILUENT_INFO',
           'VolumeCalculator',
           'StockSampleCreationParameters',
           'StockSampleCreationPosition',
           'StockSampleCreationLayout',
           'StockSampleCreationLayoutConverter',
           'PoolCreationParameters',
           'PoolCreationStockRackPosition',
           'PoolCreationStockRackLayoutConverter',
           'SingleDesignStockRackLayout',
           'SingleDesignStockRackLayoutConverter']

#: Default preparation plate volume in ul.
DEFAULT_PREPARATION_PLATE_VOLUME = 43.3


class LABELS(_ISO_LABELS_BASE):
    """
    Generates and parses worklist and rack labels involved in lab ISO
    processing.
    """
    #: Marker for stock racks that will contain the new pools.
    ROLE_POOL_STOCK = 'ps'
    #: Marker for stock racks that contain single designs that will be used
    #: to generate the new pools.
    ROLE_SINGLE_DESIGN_STOCK = 'sds'
    #: Marker for ISO labels.
    MARKER_ISO_LABEL = 'iso_label'
    #: Marker for ISO request labels.
    MARKER_ISO_REQUEST_LABEL = 'iso_request_label'
    #: Marker for the layout number.
    MARKER_LAYOUT_NUMBER = 'layout_number'
    #: Is part of stock transfer worklist labels.
    _FILL_WORKLIST_STOCK_TRANSFER = 'stock_transfer'

    @classmethod
    def create_iso_label(cls, iso_request_label, layout_number):
        """
        Creates a label for a future ISO. The label contains the ISO request
        label and the layout number.
        """
        layout_num_str = '%02i' % (layout_number)
        value_parts = [iso_request_label, layout_num_str]
        return cls._create_label(value_parts)

    @classmethod
    def create_job_label(cls, iso_request_label, job_number):
        """
        The job label contains the ISO request label and a running number
        as job number (you can get a new ISO number with
        :func:`get_new_job_number`).
        """
        job_num_str = '%02i' % (job_number)
        value_parts = [iso_request_label, cls._FILL_ISO_JOB, job_num_str]
        return cls._create_label(value_parts)

    @classmethod
    def create_stock_transfer_worklist_label(cls, iso_label):
        """
        The stock transfer worklist label contains the ISO label and a
        filler.
        """
        value_parts = [cls._FILL_WORKLIST_STOCK_TRANSFER, iso_label]
        return cls._create_label(value_parts)

    @classmethod
    def create_buffer_worklist_label(cls, iso_request_label):
        """
        The buffer dilution worklist contains the ISO request label and a
        filler.
        """
        value_parts = [iso_request_label, cls._FILL_WORKLIST_DILUTION]
        return cls._create_label(value_parts)

    @classmethod
    def create_stock_rack_label(cls, iso_label, rack_marker):
        """
        The stock rack label contains the ISO label and the rack marker
        (rack role and (optionally) rack_number).
        """
        value_parts = [iso_label, rack_marker]
        return cls._create_label(value_parts)

    @classmethod
    def parse_stock_rack_label(cls, stock_rack_label):
        """
        The stock rack label contains the ISO label and the rack marker
        (rack role and (optionally) rack_number).

        e.g. ssgen_test_01_sds#3 --> rack marker: sds#3
                                 --> layout number: 1
                                 --> ISO request label = ssgen_test
                                 --> ISO label = ssgen_test_01
        """
        value_parts = cls._get_value_parts(stock_rack_label)
        rack_marker = value_parts[-1]
        values = cls.parse_rack_marker(rack_marker)
        values[cls.MARKER_RACK_MARKER] = rack_marker
        ir_label = cls.SEPARATING_CHAR.join(value_parts[:-2])
        layout_num = cls._parse_int_str(value_parts[-2])
        values[cls.MARKER_ISO_REQUEST_LABEL] = ir_label
        values[cls.MARKER_LAYOUT_NUMBER] = layout_num
        iso_label = cls.create_iso_label(ir_label, layout_num)
        values[cls.MARKER_ISO_LABEL] = iso_label
        return values


#: The diluent info for the planned container dilutions (always buffer).
DILUENT_INFO = 'annealing buffer'


class VolumeCalculator(object):
    """
    Calculates the volume that has to be transferred from a single design
    stock tube to a future pool stock tube (for the given volume, concentration,
    and number of designs).
    """

    def __init__(self, target_volume, target_concentration, number_designs,
                 stock_concentration):
        """
        Constructor:

        :param target_volume: The requested volume for the new pool stock sample
            *in ul*.
        :type target_volume: positive number, unit ul

        :param target_concentration: The requested pool concentration for the
            new pool stock sample *in nM*.
        :type target_concentration: positive number

        :param number_designs: The number of designs per pool must be the same
            for all pools to be created.
        :type number_designs: positive integer

        :param stock_concentration: The stock concentration for single designs
            *in nM*.
        :type stock_concentration: positive number, unit nM
        """
        self.__target_volume = target_volume
        self.__target_concentration = target_concentration
        self.__number_designs = number_designs
        self.__stock_concentration = stock_concentration

        self.__adjusted_target_vol = None
        self.__stock_transfer_vol = None
        self.__buffer_volume = None

        self.__min_cybio_transfer_vol = get_min_transfer_volume(
                                                PIPETTING_SPECS_NAMES.CYBIO)

    @classmethod
    def from_iso_request(cls, iso_request):
        """
        Factory method generating a :class:`VolumeCalculator` for pool
        :class:`StockSampleIsoRequest` objects.
        The calculator determines the stock transfer volume for each single
        molecule design, the buffer volume and checks whether the target
        volume of the ISO request needs to be adjusted.

        :param iso_request: Contains all required numbers.
        :type iso_request:
            :class:`thelma.entities.iso.StockSampleCreationIsoRequest`
        """
        pool_set = iso_request.molecule_design_pool_set
        single_design_stock_concentration = \
            get_default_stock_concentration(pool_set.molecule_type,
                                            number_designs=1)
        kw = dict(
            target_volume=iso_request.stock_volume * VOLUME_CONVERSION_FACTOR,
            target_concentration=iso_request.stock_concentration \
                                   * CONCENTRATION_CONVERSION_FACTOR,
            number_designs=iso_request.number_designs,
            stock_concentration=single_design_stock_concentration)
        return cls(**kw)

    def calculate(self):
        """
        Determines the volumes for the annealing buffer and also the
        single design stock transfers and adjusts the target volume, if
        necessary.

        :raises ValueErrors: if something the values are not compatible
        """
        self.__calculate_single_stock_transfer_volume()
        self.__calculate_buffer_volume()

    def __calculate_single_stock_transfer_volume(self):
        # Determines the volume that has to be transferred from a single design
        # stock tube to a future pool stock tube (for the given volume,
        # concentration, and number of designs). The target volume might
        # be increased if the resulting single design transfer volume has
        # more than 1 decimal place.
        # :raises ValueErrors: if something the values are not compatible
        target_single_conc = float(self.__target_concentration) \
                             / self.__number_designs
        if target_single_conc > self.__stock_concentration:
            msg = 'The requested target concentration (%i nM) cannot be ' \
                  'achieved since it would require a concentration of %s nM ' \
                  'for each single design in the pool. However, the stock ' \
                  'concentration for this design type is only %s nM.' \
                  % (self.__target_concentration,
                     get_trimmed_string(target_single_conc),
                     get_trimmed_string(self.__stock_concentration))
            raise ValueError(msg)
        dil_factor = self.__stock_concentration / target_single_conc
        min_target_volume = round_up(dil_factor * self.__min_cybio_transfer_vol)
        if (min_target_volume > self.__target_volume):
            msg = 'The target volume you have requested (%i ul) is too low ' \
                  'for the required dilution (1:%s) since the CyBio cannot ' \
                  'pipet less than %.1f ul per transfer. The volume that has ' \
                  'to be taken from the stock for each single molecule ' \
                  'design would be lower that that. Increase the target ' \
                  'volume to %.1f ul or increase the target concentration.' \
                  % (self.__target_volume, get_trimmed_string(dil_factor),
                     self.__min_cybio_transfer_vol,
                     round_up(min_target_volume, 0))
            raise ValueError(msg)
        self.__stock_transfer_vol = round_up(self.__target_volume / dil_factor)
        self.__adjusted_target_vol = round(
                                     self.__stock_transfer_vol * dil_factor, 1)

        # must be at least 1 ul according to the last check
        total_transfer_vol = self.__stock_transfer_vol * self.__number_designs
        if total_transfer_vol > self.__target_volume:
            msg = 'The target volume you have requested (%i ul) is too low ' \
                  'for the concentration you have ordered (%i uM) since it ' \
                  'would require already %s ul per molecule design (%s ul in ' \
                  'total) to achieve the requested concentration. Increase ' \
                  'the volume or lower the concentration, please.' \
                  % (self.__target_volume, self.__target_concentration,
                     get_trimmed_string(self.__stock_transfer_vol),
                     get_trimmed_string(total_transfer_vol))
            raise ValueError(msg)

    def __calculate_buffer_volume(self):
        # Calculates the volume of the annealing buffer (*in ul*) required to
        # generate the desired concentration and volume. Also adjusts the
        # target volume if the necessary (e.g.
        buffer_volume = self.__adjusted_target_vol \
                        - (self.__stock_transfer_vol * self.__number_designs)
        if (buffer_volume < 0.01 and buffer_volume >= 0):
            buffer_volume = None
        elif buffer_volume < self.__min_cybio_transfer_vol:
            corr_factor = self.__min_cybio_transfer_vol / buffer_volume
            target_single_conc = \
                float(self.__target_concentration) / self.__number_designs
            dil_factor = self.__stock_concentration / target_single_conc
            self.__stock_transfer_vol = \
                self.__stock_transfer_vol * corr_factor
            self.__adjusted_target_vol = \
                self.__number_designs * self.__stock_transfer_vol * dil_factor
        self.__buffer_volume = buffer_volume

    def get_single_design_stock_transfer_volume(self):
        """
        Returns the volume that has to be transferred from a single design
        stock tube to a future pool stock tube (for the given volume,
        concentration, and number of designs)
        """
        return self.__stock_transfer_vol

    def get_adjusted_target_volume(self):
        """
        The target volume for the ISO request might need to be increased
        in order to maintain a accurate target concentration since the
        minimum step size for all pipetting methods is 0.1 ul.
        An increase of the target volume can be triggered by both odd
        single design stock transfer volumes and the buffer volume.

        Example:
        Thus, if a volume and concentration combination would result in a stock
        transfer volume of e.g. 1.333 ul the volume for the single transfer
        is increased to 1.4 ul and the target volume adjusted accordingly.

        The adjusted target concentration is determined in the
        :func:get_single_stock_transfer_volume` method. If no adjustment has
        taken place, the method returns *None*.
        """
        if is_larger_than(self.__adjusted_target_vol, self.__target_volume):
            return self.__adjusted_target_vol
        else:
            return None

    def get_buffer_volume(self):
        """
        Returns the volume of the annealing buffer required to generate
        the desired concentration and volume *in ul*.

        :raises
        """
        return self.__buffer_volume

    def __str__(self):
        return self.__class__.__name__


class StockSampleCreationParameters(MoleculeDesignPoolParameters):
    """
    Deals with the pools to be generated and the involved tubes.
    """
    DOMAIN = 'stock_sample_generation'

    ALLOWED_POSITION_TYPES = [FIXED_POSITION_TYPE]

    #: A molecule design pool ID.
    MOLECULE_DESIGN_POOL = MoleculeDesignPoolParameters.MOLECULE_DESIGN_POOL
    #: A shortcut for :attr:`MOLECULE_DESIGN_POOL`.
    POOL = MOLECULE_DESIGN_POOL
    #: The molecule design IDs the pool consists of.
    MOLECULE_DESIGNS = 'molecule_designs'
    #: The barcodes for the single design stock tubes to be used (determined
    #: via an optimizer).
    STOCK_TUBE_BARCODES = 'stock_tube_barcodes'

    REQUIRED = [POOL, MOLECULE_DESIGNS, STOCK_TUBE_BARCODES]
    ALL = [POOL, MOLECULE_DESIGNS, STOCK_TUBE_BARCODES]

    ALIAS_MAP = dict(MoleculeDesignPoolParameters.ALIAS_MAP,
                     **{MOLECULE_DESIGNS : ['molecule design IDs'],
                        STOCK_TUBE_BARCODES : []})

    DOMAIN_MAP = dict(MoleculeDesignPoolParameters.DOMAIN_MAP, **{
                  MOLECULE_DESIGNS : DOMAIN, STOCK_TUBE_BARCODES : DOMAIN})


class StockSampleCreationPosition(MoleculeDesignPoolPosition):
    """
    The pool ID, single molecule design IDs and stock tubes for a particular
    position.

    **Equality condition**: equal :attr:`rack_position` and :attr:`pool`.
    """
    PARAMETER_SET = StockSampleCreationParameters
    DELIMITER = '-'
    EXPOSE_POSITION_TYPE = False

    def __init__(self, rack_position, molecule_design_pool,
                 stock_tube_barcodes):
        """
        :param rack_position: The source rack position in the source rack.
        :type rack_position: :class:`thelma.entities.rack.RackPosition`

        :param molecule_design_pool: A molecule design pool to generate.
        :type molecule_design_pool:
            :class:`thelma.entities.moleculedesign.MoleculeDesignPool`

        :param stock_tube_barcodes: The stock tube barcodes for the single
            molecule design tubes used to generate this pool.
        :type stock_tube_barcodes: :class:`list`
        """
        MoleculeDesignPoolPosition.__init__(self, rack_position=rack_position,
                                    molecule_design_pool=molecule_design_pool,
                                    position_type=FIXED_POSITION_TYPE)

        if not isinstance(stock_tube_barcodes, list):
            msg = 'The stock tube barcodes must be a list (obtained: %s).' \
                  % (stock_tube_barcodes.__class__.__name__)
            raise TypeError(msg)

        #: A list of molecules contained in the pool (ordered by ID).
        self.molecule_designs = []
        for md in molecule_design_pool.molecule_designs:
            self.molecule_designs.append(md)
            self.molecule_designs.sort()

        #: The stock tube barcodes for the single molecule design tubes
        #: used to generate this pool
        self.stock_tube_barcodes = sorted(stock_tube_barcodes)

    @property
    def pool(self):
        """
        Shortcut to the :attr:`molecule_design_pool`.
        """
        return self.molecule_design_pool

    def get_parameter_tag(self, parameter):
        """
        The method needs to be overwritten because the value for the molecule
        designs tag is a concatenated string. Position types are not important
        """
        if parameter == self.PARAMETER_SET.MOLECULE_DESIGNS:
            return self.__get_molecule_designs_tag()
        elif parameter == self.PARAMETER_SET.STOCK_TUBE_BARCODES:
            return self.__get_stock_barcodes_tag()
        else:
            return MoleculeDesignPoolPosition.get_parameter_tag(self, parameter)

    @classmethod
    def __get_molecule_designs_tag_value(cls, molecule_designs):
        """
        The tag values contains the molecule designs as concatenated string.
        """
        return cls.DELIMITER.join([str(md.id) for md in molecule_designs])

    def get_molecule_designs_tag_value(self):
        """
        This parameter requires a special method because the value for the
        molecule designs tag is a concatenated string.
        """
        return self.__get_molecule_designs_tag_value(self.molecule_designs)

    def __get_molecule_designs_tag(self):
        """
        This parameter requires a special method because the value for the
        molecule designs tag is a concatenated string.
        """
        return Tag(self.PARAMETER_SET.DOMAIN,
                   self.PARAMETER_SET.MOLECULE_DESIGNS,
                   self.get_molecule_designs_tag_value())

    @classmethod
    def validate_molecule_designs(cls, pool, md_tag_value):
        """
        Compares the molecule design of the pool to a molecule design tag
        value. Is used by the layout converter for validation.
        """
        pool_str = cls.__get_molecule_designs_tag_value(
                                            sorted(pool.molecule_designs))
        return pool_str == md_tag_value

    def get_stock_barcodes_tag_value(self):
        """
        This parameter requires a special method because the value for the
        stock barcodes tag is a concatenated string.

        Reverse method: :func:`get_tube_barcodes_from_tag_value`.
        """
        return self.DELIMITER.join(self.stock_tube_barcodes)

    def __get_stock_barcodes_tag(self):
        """
        This parameter requires a special method because the value for the
        stock barcodes tag is a concatenated string.
        """
        return Tag(self.PARAMETER_SET.DOMAIN,
                   self.PARAMETER_SET.STOCK_TUBE_BARCODES,
                   self.get_stock_barcodes_tag_value())

    @classmethod
    def get_tube_barcodes_from_tag_value(cls, tube_barcode_tag_value):
        """
        Converts a tag value for the stock tubes into a list of stock tube
        barcodes (reverse method: :func:`get_stock_barcodes_tag_value`).
        """
        return tube_barcode_tag_value.split(cls.DELIMITER)

    def _get_parameter_values_map(self):
        """
        The position type is not included.
        """
        return {self.PARAMETER_SET.POOL : self.pool,
                self.PARAMETER_SET.MOLECULE_DESIGNS : self.molecule_designs,
                self.PARAMETER_SET.STOCK_TUBE_BARCODES : \
                                                    self.stock_tube_barcodes}

    def __eq__(self, other):
        if not MoleculeDesignPoolPosition.__eq__(self, other):
            result = False
        else:
            result = self.stock_tube_barcodes == other.stock_tube_barcodes
        return result

    def __repr__(self):
        str_format = '<%s rack position: %s, pool ID: %s, molecule ' \
                     'designs: %s, stock tubes: %s>'
        params = (self.__class__.__name__, self.rack_position, self.pool.id,
                  self.get_molecule_designs_tag_value(),
                  self.get_stock_barcodes_tag_value())
        return str_format % params


class StockSampleCreationLayout(MoleculeDesignPoolLayout):
    """
    Defines the molecule design pool data for a stock tube rack or a
    library plate.
    """
    POSITION_CLS = StockSampleCreationPosition

    __DEFAULT_SHAPE_NAME = RACK_SHAPE_NAMES.SHAPE_96

    def __init__(self, shape=None):
        """
        Constructor:

        :param shape: The rack shape - usually a 96-well plate, but you can
            overwrite that.
        :type shape: :class:`thelma.entities.rack.RackShape`
        :default shape: *None* (96-well)
        """
        if shape is None:
            shape = RACK_SHAPE_NAMES.from_name(self.__DEFAULT_SHAPE_NAME)
        MoleculeDesignPoolLayout.__init__(self, shape)

    def get_pool_set(self, molecule_type):
        """
        Returns a pool set containing all pools from the layout.

        :param molecule_type: The type of the pools in the set is derived
            from the molecule type of the stock sample creation ISO request.
        :type molecule_type: :class:`thelma.entities.moleculetype.MoleculeType`
        """
        pools = set([lp.pool for lp in self._position_map.values()])
        return MoleculeDesignPoolSet(molecule_type=molecule_type,
                                     molecule_design_pools=pools)


class StockSampleCreationLayoutConverter(MoleculeDesignPoolLayoutConverter):
    """
    Converts a :class:`thelma.entities.racklayout.RackLayout` into a
    :class:`StockSampleCreationLayout`.
    """
    NAME = 'Stock Sample Creation Layout Converter'

    PARAMETER_SET = StockSampleCreationParameters
    LAYOUT_CLS = StockSampleCreationLayout
    POSITION_CLS = StockSampleCreationPosition

    def __init__(self, rack_layout, parent=None):
        MoleculeDesignPoolLayoutConverter.__init__(self, rack_layout,
                                                   parent=parent)
        # intermediate storage of invalid rack positions
        self.__mismatching_mds = None
        self.__missing_tubes = None
        self.__mismatching_tube_num = None

    def reset(self):
        MoleculeDesignPoolLayoutConverter.reset(self)
        self.__mismatching_mds = []
        self.__missing_tubes = []
        self.__mismatching_tube_num = []

    def _get_position_init_values(self, parameter_map, rack_pos):
        kw = MoleculeDesignPoolLayoutConverter._get_position_init_values(
                                                    self,
                                                    parameter_map, rack_pos)
        result = None
        if not kw is None:
            invalid = False
            pos_label = rack_pos.label
            pool = kw['molecule_design_pool']
            md_str = parameter_map[self.PARAMETER_SET.MOLECULE_DESIGNS]
            if not self.POSITION_CLS.validate_molecule_designs(pool, md_str):
                exp_mds = [md.id for md in pool]
                info = '%s (pool %s, found: %s, expected: %s)' \
                        % (pos_label, pool.id, md_str,
                           self._get_joined_str(
                                    exp_mds, is_strs=False, separator='-'))
                self.__mismatching_mds.append(info)
                invalid = True
            tube_str = parameter_map[self.PARAMETER_SET.STOCK_TUBE_BARCODES]
            if tube_str is None:
                self.__missing_tubes.append(pos_label)
                result = None
            else:
                tubes = self.POSITION_CLS.get_tube_barcodes_from_tag_value(
                                                                    tube_str)
                if not len(tubes) == len(pool):
                    info = '%s (%s, number mds: %i)' \
                           % (pos_label, tube_str, len(pool))
                    self.__mismatching_tube_num.append(info)
                    invalid = True
                if invalid:
                    result = None
                else:
                    kw['stock_tube_barcodes'] = tubes
                    # Success!
                    result = kw
        return result

    def _record_errors(self):
        MoleculeDesignPoolLayoutConverter._record_errors(self)
        if len(self.__mismatching_mds) > 0:
            msg = 'The molecule designs IDs for some pools do not match: %s.' \
                  % (self._get_joined_str(self.__mismatching_mds))
            self.add_error(msg)
        if len(self.__missing_tubes) > 0:
            msg = 'The following rack positions do not contain stock tube ' \
                  'barcodes: %s.' % (self._get_joined_str(self.__missing_tubes))
            self.add_error(msg)
        if len(self.__mismatching_tube_num) > 0:
            msg = 'For some positions the number of tubes does not match ' \
                  'the number of molecule designs: %s.' \
                   % (self._get_joined_str(self.__mismatching_tube_num))
            self.add_error(msg)


class PoolCreationParameters(StockRackParameters):
    """
    Deals with the pools to be generated in pure pool generation ISOs that
    do not involve further processing after the pools have been
    generated. Unlike normal :class:`StockRackParameters` the
    positions do not need to have transfer targets.
    """
    MUST_HAVE_TRANSFER_TARGETS = \
        {StockRackParameters.TRANSFER_TARGETS : False}


class PoolCreationStockRackPosition(StockRackPosition):
    """
    Represents a position in a ISO stock rack for a stock sample creation
    ISO that does not involve further processing after the pools have been
    generated. Unlike normal :class:`StockRackPosition` objects they
    do not need to have transfer targets.
    """
    PARAMETER_SET = PoolCreationParameters

    def __init__(self, rack_position, molecule_design_pool, tube_barcode,
                 transfer_targets=None):
        StockRackPosition.__init__(self, rack_position, molecule_design_pool,
                                   tube_barcode, transfer_targets)

class PoolCreationStockRackLayoutConverter(StockRackLayoutConverter):
    """
    Converts a rack layout into a :class:`StockRackLayout`.
    Unlike normal with normal stock racks these positions do not need to have
    transfer targets.
    """
    NAME = 'Pool Creation Stock Rack Layout Converter'
    PARAMETER_SET = PoolCreationParameters
    POSITION_CLS = PoolCreationStockRackPosition


class SingleDesignStockRackLayout(StockRackLayout):
    """
    Represent an ISO single design stock rack for stock sample creation.
    Unlike normal :class:`StockRackPosition` objects the positions within
    the layout might have the same transfer targets.
    """
    ALLOW_DUPLICATE_TARGET_WELLS = \
        {StockRackLayout.POSITION_CLS.PARAMETER_SET.TRANSFER_TARGETS : True}


class SingleDesignStockRackLayoutConverter(StockRackLayoutConverter):
    """
    Converts a rack layout into a :class:`SingleDesignStockRackLayout`.
    Unlike normal with normal stock racks there might be several transfers
    targets with the same target.
    """
    NAME = 'Single Design Stock Rack Layout Converter'
    LAYOUT_CLS = SingleDesignStockRackLayout
