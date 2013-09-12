"""
Utility classes related to ISO-handling.

AAB, Aug 2011
"""

from everest.entities.utils import get_root_aggregate
from thelma.automation.tools.utils.layouts import EMPTY_POSITION_TYPE
from thelma.automation.tools.utils.layouts import MOCK_POSITION_TYPE
from thelma.automation.tools.utils.layouts import MoleculeDesignPoolLayout
from thelma.automation.tools.utils.layouts import MoleculeDesignPoolParameters
from thelma.automation.tools.utils.layouts import MoleculeDesignPoolPosition
from thelma.automation.tools.utils.layouts import get_converted_number
from thelma.automation.tools.utils.layouts import is_valid_number
from thelma.automation.tools.utils.layouts import LIBRARY_POSITION_TYPE
from thelma.automation.tools.utils.converters \
    import MoleculeDesignPoolLayoutConverter
from thelma.automation.tools.utils.racksector import AssociationData
from thelma.automation.tools.utils.racksector import RackSectorAssociator
from thelma.automation.tools.utils.racksector import ValueDeterminer
from thelma.interfaces import IOrganization
from thelma.models.moleculedesign import MoleculeDesignPool
from thelma.models.organization import Organization


__docformat__ = "reStructuredText en"

__all__ = ['IsoRequestParameters',
           'IsoRequestPosition',
           'IsoRequestLayout',
           'IsoRequestLayoutConverter',
           'IsoRequestValueDeterminer',
           'IsoRequestAssociationData']


class IsoRequestParameters(MoleculeDesignPoolParameters):
    """
    A list of ISO parameters.
    """

    #: The domain for all ISO-related tags.
    DOMAIN = 'iso'

    #: The molecule design pool (tag value: molecule design pool id).
    MOLECULE_DESIGN_POOL = MoleculeDesignPoolParameters.MOLECULE_DESIGN_POOL
    #: The requested volume in ul.
    ISO_VOLUME = 'iso_volume'
    #: The requested concentration in nM.
    ISO_CONCENTRATION = 'iso_concentration'
    #: The supplier for the molecule design pool (tag value: organisation name).
    SUPPLIER = 'supplier'
    #: The position type (fixed, floating, mock or empty).
    POS_TYPE = MoleculeDesignPoolParameters.POS_TYPE

    #: A list of the attributes/parameters that need to be set.
    REQUIRED = [MOLECULE_DESIGN_POOL]
    #: A list of all available attributes/parameters.
    ALL = [MOLECULE_DESIGN_POOL, ISO_CONCENTRATION, ISO_VOLUME, SUPPLIER,
           POS_TYPE]

    #: A map storing alias prediactes for each parameter.
    ALIAS_MAP = {MOLECULE_DESIGN_POOL : MoleculeDesignPoolParameters.ALIAS_MAP[
                                                          MOLECULE_DESIGN_POOL],
                ISO_CONCENTRATION : [],
                ISO_VOLUME : [],
                SUPPLIER : [],
                POS_TYPE : MoleculeDesignPoolParameters.ALIAS_MAP[POS_TYPE]}

    DOMAIN_MAP = {MOLECULE_DESIGN_POOL : DOMAIN,
                  ISO_CONCENTRATION : DOMAIN,
                  ISO_VOLUME : DOMAIN,
                  SUPPLIER : DOMAIN,
                  POS_TYPE : DOMAIN}

    #: The minimum volume that can be requested by the stock management in ul.
    MINIMUM_ISO_VOLUME = 1


class IsoRequestPosition(MoleculeDesignPoolPosition):
    """
    This class contains the data for one position in an ISO layout. The
    allowed and required values for the single parameters depend on the
    position type.

    **Equality condition**: equal :attr:`type`, :attr:`rack_position`,
                :attr:`molecule_design_pool` and :attr:`concentration`
    """
    PARAMETER_SET = IsoRequestParameters

    #: String indicating that there shall be no restriction for the supplier
    #: (required if there are restrictions for only some molecule design pool
    #: IDs in an ISO layout)
    ANY_SUPPLIER_INDICATOR = 'any'

    def __init__(self, rack_position, molecule_design_pool=None,
                 iso_concentration=None, iso_volume=None, supplier=None):
        """
        Constructor:

        :param rack_position: The rack position.
        :type rack_position: :class:`thelma.models.rack.RackPosition`.

        :param molecule_design_pool: The molecule design pool for this position
            or a valid placeholder.
        :type molecule_design_pool:
            :class:`thelma.models.moleculedesign.MoleculeDesignPool`
            or :class:`basestring`

        :param iso_concentration: The concentration requested from the stock.
        :type iso_concentration: positive number

        :param iso_volume: The volume requested by the stock.
        :type iso_volume: positive number

        :param supplier: The supplier for the molecule design pool ID
            (fixed positions only).
        :type supplier: :class:thelma.models.organization.Organization`
        """
        MoleculeDesignPoolPosition.__init__(self, rack_position=rack_position,
                                    molecule_design_pool=molecule_design_pool)

        #: The concentration requested by the stock management.
        self.iso_concentration = get_converted_number(iso_concentration)
        #: The volume requested by the stock management.
        self.iso_volume = get_converted_number(iso_volume)

        #: The supplier the molecule should be supplied by (fixed positions
        #: only).
        self.supplier = supplier

        #: The type of the ISO position.
        self.__check_values_for_position_type()

    def __check_values_for_position_type(self):
        """
        Sets the position type and checks the validity of the values.
        """
        concentration_base_tpl = ('ISO concentration', self.iso_concentration)
        volume_base_tpl = ('ISO volume', self.iso_volume)
        supplier_base_tpl = ('supplier', self.supplier)

        if self.is_untreated_type:
            self._check_none_value([supplier_base_tpl])
            self._check_untreated_values([volume_base_tpl,
                                          concentration_base_tpl])
        elif self.is_empty:
            self._check_none_value([concentration_base_tpl, volume_base_tpl,
                                    supplier_base_tpl])

        elif self.is_mock:
            self._check_none_value([supplier_base_tpl])
            self._check_mock_values([concentration_base_tpl])
            self._check_numbers([volume_base_tpl], allow_none=True)

        else:
            self._check_numbers([volume_base_tpl, concentration_base_tpl], True)
            if self.is_fixed:
                pool_tuple = ('molecule design pool', self.molecule_design_pool)
                self.__check_classes([pool_tuple], (MoleculeDesignPool, int))
                if not self.supplier is None:
                    self.__check_classes([supplier_base_tpl], Organization)
            else:
                self._check_none_value([supplier_base_tpl])

    def _check_none_value(self, value_list):
        """
        Checks whether all passed values are *None*.

        The values must be passed as tuple with the value name (for error
        messages) as first element and the values as second element.
        """
        for value_tuple in value_list:
            value_name, value = value_tuple[0], value_tuple[1]
            if not value is None:
                msg = 'The %s must be None for %s positions (obtained: %s)!' \
                       % (value_name, self.position_type, value)
                raise ValueError(msg)

    def _check_numbers(self, value_list, allow_none):
        """
        Checks whether all passed values are a positive number (or *None*,
        if *None* is allowed).

        The values must be passed as list of tuples with the value name (for
        error messages) as first element and the values as second element.
        """
        for value_tuple in value_list:
            value_name, value = value_tuple[0], value_tuple[1]
            if value is None and allow_none:
                pass
            else:
                if not is_valid_number(value=value):
                    msg = 'The %s must be a positive number (obtained: %s).' \
                          % (value_name, value)
                    raise ValueError(msg)

    def __check_specific_value(self, value_list, allowed_values):
        """
        Checks whether all passed values have one of the allowed values.

        The values must be passed as list of tuples with the value name (for
        error messages) as first element and the values as second element.
        """
        for value_tuple in value_list:
            value_name, value = value_tuple[0], value_tuple[1]
            value_upper = value
            if isinstance(value, basestring): value_upper = value.upper()
            if not value_upper in allowed_values:
                msg = 'The value "%s" is invalid for the %s of %s positions. ' \
                      'Allowed values are: %s' % (value, value_name,
                       self.position_type, allowed_values)
                raise ValueError(msg)

    def _check_untreated_values(self, value_list):
        """
        Valid values for these attributes are *None*, \'None\' and
        \'untreated\'. The values must be passed as tuple with
        the value name (for error messages) as first element and the
        values as second element.

        :raises ValueError: if a value is invalid
        """
        self.__check_specific_value(value_list,
                          self.PARAMETER_SET.VALID_UNTREATED_NONE_REPLACERS)

    def _check_mock_values(self, value_list):
        """
        Valid values for these attributes are *None*, \'None\' and
        \'mock\'. The values must be passed as tuple with
        the value name (for error messages) as first element and the
        values as second element.
        """
        self.__check_specific_value(value_list,
                            self.PARAMETER_SET.VALID_MOCK_NONE_REPLACERS)

    def __check_classes(self, value_list, allowed_classes):
        """
        Checks whether all passed values are members of one of the passed
        classes.

        The values must be passed as list of tuples with the value name (for
        error messages) as first element and the values as second element.
        """
        for value_tuple in value_list:
            value_name, value = value_tuple[0], value_tuple[1]
            if not isinstance(value, allowed_classes):
                msg = 'The %s must be a an object of one of the ' \
                      'following types: %s (obtained: %s).' \
                      % (value_name, allowed_classes, value.__class__.__name__)
                raise TypeError(msg)

    @classmethod
    def create_library_position(cls, rack_position, **kw):
        """
        Creates a library ISO position.

        :param rack_position: The rack position.
        :type rack_position: :class:`thelma.models.rack.RackPosition`.

        :return: library type IsoPosition
        """
        return cls(rack_position=rack_position,
                   molecule_design_pool=LIBRARY_POSITION_TYPE, **kw)

    @classmethod
    def create_mock_position(cls, rack_position, iso_volume, **kw):
        """
        Creates a mock ISO position.

        :param rack_position: The rack position.
        :type rack_position: :class:`thelma.models.rack.RackPosition`.

        :param iso_volume: The volume requested from the stock management.
        :type iso_volume: positive number, unit ul

        :return: mock type IsoPosition
        """
        return cls(rack_position=rack_position,
                   molecule_design_pool=cls.PARAMETER_SET.MOCK_TYPE_VALUE,
                   iso_volume=iso_volume, **kw)

    def _get_parameter_values_map(self):
        """
        Returns the :attr:`parameter_values_map`
        """
        parameter_map = MoleculeDesignPoolPosition._get_parameter_values_map(
                                                                        self)
        parameter_map[self.PARAMETER_SET.ISO_VOLUME] = self.iso_volume
        parameter_map[self.PARAMETER_SET.ISO_CONCENTRATION] = \
                                                    self.iso_concentration
        parameter_map[self.PARAMETER_SET.SUPPLIER] = self.supplier
        return parameter_map

    def __eq__(self, other):
        if not (isinstance(other, self.__class__)): return None
        if not self.rack_position == other.rack_position: return False
        if not self.molecule_design_pool_id == other.molecule_design_pool_id:
            return False
        if not self.is_empty and not self.iso_volume == other.iso_volume:
            return False
        if not (self.is_empty or self.is_mock) and \
                not self.iso_concentration == other.iso_concentration:
            return False
        return True

    def __repr__(self):
        str_format = '<%s type: %s, rack position: %s, molecule design ' \
                     'pool: %s, volume: %s, concentration: %s>'
        params = (self.__class__.__name__, self.position_type,
                  self.rack_position, self.molecule_design_pool, self.iso_volume,
                  self.iso_concentration)
        return str_format % params


class IsoRequestLayout(MoleculeDesignPoolLayout):
    """
    A working container for ISO layouts.
    """

    #: The working position class this layout is associated with.
    WORKING_POSITION_CLASS = IsoRequestPosition

    def has_consistent_volumes_and_concentrations(self):
        """
        Checks whether the volumes and concentration of the layout
        (non-empty position) are either all *None* or all set.

        :return: :class:`boolean`
        """
        volumes = set()
        concentrations = set()
        for iso_pos in self._position_map.values():
            if iso_pos.is_empty: continue
            if not iso_pos.iso_volume is None: volumes.add(iso_pos.iso_volume)
            if iso_pos.is_mock: continue
            if not iso_pos.iso_concentration is None:
                concentrations.add(iso_pos.iso_concentration)

        if len(volumes) > 0:
            for iso_pos in self._position_map.values():
                if iso_pos.is_empty: continue
                if iso_pos.iso_volume is None: return False
        if len(concentrations) > 0:
            for iso_pos in self._position_map.values():
                if iso_pos.is_mock or iso_pos.is_empty: continue
                if iso_pos.iso_concentration is None: return False

        return True

    def get_supplier_map(self):
        """
        Returns a dictionary mapping supplier IDs onto the molecule design pool
        IDs they are meant for (fixed positions only).
        """
        supplier_map = dict()

        for iso_pos in self._position_map.values():
            if not iso_pos.is_fixed: continue
            pool_id = iso_pos.molecule_design_pool_id
            if supplier_map.has_key(pool_id): continue
            supplier = iso_pos.supplier
            supplier_map[pool_id] = supplier

        return supplier_map


class IsoRequestLayoutConverter(MoleculeDesignPoolLayoutConverter):
    """
    Converts an rack_layout into an :class:`IsoRequestLayout`.

    :Note: Untreated positions are converted to empty positions.
    """

    NAME = 'ISO Layout Converter'

    PARAMETER_SET = IsoRequestParameters
    WORKING_LAYOUT_CLASS = IsoRequestLayout

    def __init__(self, rack_layout, log):
        """
        Constructor:

        :param rack_layout: The rack layout containing the ISO data.
        :type rack_layout: :class:`thelma.models.racklayout.RackLayout`

        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`
        """
        MoleculeDesignPoolLayoutConverter.__init__(self, log=log,
                                                   rack_layout=rack_layout)

        #: The organisation aggregate
        #: (see :class:`thelma.models.aggregates.Aggregate`)
        #: used to obtain suppliers from organisation names.
        self._organization_agg = get_root_aggregate(IOrganization)
        #: Stores the suppliers for the different supplier names.
        self._supplier_map = None

        # intermediate storage of invalid rack positions
        self._invalid_iso_volume = None
        self._invalid_iso_concentration = None
        self._missing_iso_volume = None
        self._missing_iso_concentration = None
        self._unknown_supplier = None
        self._invalid_supplier = None
        self._empty_and_volume = None
        self._empty_and_concentration = None

    def reset(self):
        """
        Resets all attributes except for the :attr:`rack_layout`.
        """
        MoleculeDesignPoolLayoutConverter.reset(self)
        self._supplier_map = dict()
        self._invalid_iso_volume = []
        self._invalid_iso_concentration = []
        self._missing_iso_volume = []
        self._missing_iso_concentration = []
        self._unknown_supplier = []
        self._invalid_supplier = []
        self._empty_and_volume = []
        self._empty_and_concentration = []

    def _get_position_init_values(self, parameter_map):
        md_pool = parameter_map[self.PARAMETER_SET.MOLECULE_DESIGN_POOL]
        volume = parameter_map[self.PARAMETER_SET.ISO_VOLUME]
        concentration = parameter_map[self.PARAMETER_SET.ISO_CONCENTRATION]
        supplier = parameter_map[self.PARAMETER_SET.SUPPLIER]
        pos_type = parameter_map[self.PARAMETER_SET.POS_TYPE]
        rack_pos = parameter_map[self._RACK_POSITION_KEY]
        pos_label = rack_pos.label

        if pos_type is None:
            pos_type = self.PARAMETER_SET.get_position_type(md_pool)
        if pos_type == IsoRequestParameters.MOCK_TYPE_VALUE:
            md_pool = IsoRequestParameters.MOCK_TYPE_VALUE

        # check values
        invalid = False

        if pos_type == EMPTY_POSITION_TYPE or \
                                self.PARAMETER_SET.is_untreated_type(pos_type):
            if self.PARAMETER_SET.is_untreated_type(pos_type):
                pos_type = EMPTY_POSITION_TYPE
                volume, concentration = None, None
            if not volume is None:
                self._empty_and_volume.append(pos_label)
                invalid = True
            if not concentration is None:
                self._empty_and_concentration.append(pos_label)
                invalid = True
        else:
            is_mock = False
            if md_pool == MOCK_POSITION_TYPE:
                is_mock = True
            invalid = self._check_volume_and_concentration(volume,
                                        concentration, pos_label, is_mock)

        if pos_type == self.PARAMETER_SET.FIXED_TYPE_VALUE:
            md_pool = self._get_molecule_design_pool_for_id(md_pool, pos_label)
            if md_pool is None: invalid = True
            if not supplier is None:
                supplier = self._get_supplier_for_name(supplier)
                if supplier is None: invalid = True
        else:
            if not supplier is None:
                self._invalid_supplier.append(pos_label)
                invalid = True

        if invalid or pos_type == EMPTY_POSITION_TYPE: # incl untreated
            return None
        else:
            return dict(rack_position=rack_pos,
                        molecule_design_pool=md_pool,
                        iso_concentration=concentration,
                        iso_volume=volume, supplier=supplier)

    def _get_supplier_for_name(self, supplier_name):
        """
        Checks and returns the supplier for a supplier name.
        """
        if not supplier_name is None:

            if self._supplier_map.has_key(supplier_name):
                return self._supplier_map[supplier_name]

            supplier = self._organization_agg.get_by_slug(supplier_name.lower())
            if supplier is None:
                if not supplier_name in self._unknown_supplier:
                    self._unknown_supplier.append(supplier_name)
                return None
            else:
                self._supplier_map[supplier_name] = supplier
                return supplier

    def _check_volume_and_concentration(self, iso_volume, iso_conc,
                                        pos_label, is_mock=False):
        """
        Checks the volume and concentration for non-empty positions.
        """
        invalid = False

        if iso_volume is None:
            self._missing_iso_volume.append(pos_label)
            invalid = True
        elif not is_valid_number(iso_volume):
            self._invalid_iso_volume.append(pos_label)
            invalid = True

        if is_mock:
            if not IsoRequestPosition.is_valid_mock_value(iso_conc):
                info = '%s (%s, mock position)' % (iso_conc, pos_label)
                self._invalid_iso_concentration.append(info)
                invalid = True
        else:
            if iso_conc is None:
                self._missing_iso_concentration.append(pos_label)
                invalid = True
            elif not is_valid_number(iso_conc):
                self._invalid_iso_concentration.append(pos_label)
                invalid = True

        return invalid

    def _record_additional_position_errors(self):
        """
        Launches collected position errors.
        """
        MoleculeDesignPoolLayoutConverter._record_additional_position_errors(
                                                                        self)

        if len(self._invalid_iso_volume) > 0:
            self._invalid_iso_volume.sort()
            msg = 'Some position have invalid ISO volumes. The volume must ' \
                  'either be None or a positive number. Details: %s.' \
                  % (', '.join(sorted(self._invalid_iso_volume)))
            self.add_error(msg)

        if len(self._invalid_iso_concentration) > 0:
            self._invalid_iso_concentration.sort()
            msg = 'Some position have invalid ISO concentrations. The ' \
                  'concentration must either be None or a positive number. ' \
                  'Details: %s.' % (', '.join(sorted(
                                         self._invalid_iso_concentration)))
            self.add_error(msg)

        if len(self._missing_iso_volume) > 0:
            self._missing_iso_volume.sort()
            msg = 'Some position do not have an ISO volume specifications: %s.' \
                  % (', '.join(sorted(self._missing_iso_volume)))
            self.add_error(msg)

        if len(self._missing_iso_concentration) > 0:
            self._missing_iso_concentration.sort()
            msg = 'Some positions do not have an ISO concentration ' \
                  'specification: %s.' % (', '.join(sorted(
                                          self._missing_iso_concentration)))
            self.add_error(msg)

        if len(self._unknown_supplier) > 0:
            self._unknown_supplier.sort()
            msg = 'Some suppliers could not be found in the DB: %s. Please ' \
                  'check the spelling.' % (', '.join(sorted(
                                                     self._unknown_supplier)))
            self.add_error(msg)

        if len(self._invalid_supplier) > 0:
            self._invalid_supplier.sort()
            msg = 'There are supplier specified for the following non-fixed ' \
                  'positions: %s.' % (', '.join(sorted(self._invalid_supplier)))
            self.add_error(msg)

        if len(self._empty_and_volume) > 0:
            self._empty_and_volume.sort()
            msg = 'Some wells have ISO volume specifications although they ' \
                  'are empty: %s.' % (', '.join(sorted(self._empty_and_volume)))
            self.add_error(msg)

        if len(self._empty_and_concentration) > 0:
            self._empty_and_concentration.sort()
            msg = 'Some wells have ISO concentration specifications although ' \
                  'they are empty: %s.' % (', '.join(sorted(
                                                self._empty_and_concentration)))
            self.add_error(msg)

    def _initialize_working_layout(self, shape):
        """
        Initialises the working layout.
        """
        return IsoRequestLayout(shape=shape)


class IsoRequestValueDeterminer(ValueDeterminer):
    """
    There are two different modes: You can either regard only floating
    positions or regard both floating and control (fixed) positions.

    **Return Value:** A map containing the values for the different sectors.
    """

    def __init__(self, log, iso_request_layout, regard_controls, attribute_name,
                 number_sectors):
        """
        Constructor:

        :param iso_request_layout: The ISO layout whose positions to check.
        :type iso_request_layout: :class:`IsoRequestLayout`

        :param attribute_name: The name of the attribute to be determined.
        :type attribute_name: :class:`str`

        :param regard_controls: Shall controls positions be regarded (*True*)
            or be ignored (*False* - floating positions are always regarded)?
        :type regard_controls: :class:`bool`

        :param number_sectors: The number of rack sectors.
        :type number_sectors: :class:`int`
        :default number_sectors: *4*

        :param log: The ThelmaLog you want to write in.
        :type log: :class:`thelma.ThelmaLog`
        """
        ValueDeterminer.__init__(self, working_layout=iso_request_layout,
                                 attribute_name=attribute_name, log=log,
                                 number_sectors=number_sectors)

        #: Shall controls (Fixed) position be regarded?
        self.regard_controls = regard_controls

    def _check_input(self):
        ValueDeterminer._check_input(self)
        self._check_input_class('"regard controls" flag', self.regard_controls,
                                bool)

    def _ignore_position(self, layout_pos):
        """
        Floating positions are always accepted. Fixed positions are accepted,
        if :attr:`regard_controls` is *True*. Other position types are always
        ignored.
        """
        if layout_pos.is_floating:
            return False
        elif layout_pos.is_fixed and self.regard_controls:
            return False
        else:
            return True


class IsoRequestSectorAssociator(RackSectorAssociator):
    """
    A special rack sector associator for ISO request layouts.
    There are two different modes: You can either regard only floating
    positions or regard both floating and control (fixed) positions.

    **Return Value:** A list of lists (each list containing the indices of
        rack sector associated with one another).
    """
    LAYOUT_CLS = IsoRequestLayout

    __ATTR_NAME = 'iso_concentration'

    def __init__(self, layout, regard_controls, log, number_sectors=4):
        """
        Constructor:

        :param iso_request_layout: The ISO request layout whose sectors to
            associate.
        :type iso_request_layout: :class:`IsoRequestLayout`

        :param regard_controls: Shall controls positions be regarded (*True*)
            or be ignored (*False* - floating positions are always regarded)?
        :type regard_controls: :class:`bool`

        :param log: The ThelmaLog you want to write in.
        :type log: :class:`thelma.ThelmaLog`

        :param number_sectors: The number of rack sectors.
        :type number_sectors: :class:`int`
        :default number_sectors: *4*
        """
        RackSectorAssociator.__init__(self, layout=layout,
                                      number_sectors=number_sectors, log=log)

        #: Shall controls (Fixed) position be regarded?
        self.regard_controls = regard_controls

    def _check_input(self):
        RackSectorAssociator._check_input(self)
        self._check_input_class('"regard controls" flag', self.regard_controls,
                                bool)

    def _init_value_determiner(self):
        value_determiner = IsoRequestValueDeterminer(log=self.log,
                                    iso_request_layout=self.layout,
                                    attribute_name=self.__ATTR_NAME,
                                    regard_controls=self.regard_controls,
                                    number_sectors=self.number_sectors)
        return value_determiner


class IsoRequestAssociationData(AssociationData):
    """
    A special association data class for ISO request layouts which also stores
    the volume for each rack sector. There are two different modes:
    You can either regard only floating positions or regard both floating and
    control (fixed) positions.

    :Note: All attributes are immutable.
    :Note: Error and warning recording is disabled.
    """

    #: The class of the :class:`RackSectorAssociator` to be used (default:
    #: :class:`IsoRequestSectorAssociator`).
    ASSOCIATOR_CLS = IsoRequestSectorAssociator

    def __init__(self, iso_request_layout, regard_controls, log):
        """
        Constructor:

        :param iso_request_layout: The ISO request layout whose sectors to
            associate.
        :type iso_request_layout: :class:`IsoRequestLayout`

        :param regard_controls: Shall controls positions be regarded (*True*)
            or be ignored (*False* - floating positions are always regarded)?
        :type regard_controls: :class:`bool`

        :param log: The ThelmaLog you want to write in.
        :type log: :class:`thelma.ThelmaLog`
        """
        self.__regard_controls = regard_controls
        AssociationData.__init__(self, layout=iso_request_layout, log=log,
                                 record_errors=False)

        #: The volumes for each rack sector.
        self.__sector_volumes = None

        self.__find_volumes(iso_request_layout, log)

    @property
    def sector_volumes(self):
        """
        The volumes for each sector.
        """
        return self.__sector_volumes

    def _find_concentrations(self, layout):
        """
        The name of the concentration attribute is derived from the
        :attr:`ASSOCIATOR_CLS`.
        """
        attr_name = self.ASSOCIATOR_CLS.SECTOR_ATTR_NAME
        concentrations = set()
        for ir_pos in layout.working_positions():
            if ir_pos.is_floating or \
                                    (ir_pos.is_fixed and self.__regard_controls):
                conc = getattr(ir_pos, attr_name)
                concentrations.add(conc)
        return concentrations

    def _init_value_determiner(self, layout, log):
        """
        The name of the concentration attribute is derived from the
        :attr:`ASSOCIATOR_CLS`.
        """
        value_determiner = IsoRequestValueDeterminer(iso_request_layout=layout,
                         regard_controls=self.__regard_controls,
                         attribute_name=self.ASSOCIATOR_CLS.SECTOR_ATTR_NAME,
                         log=log, number_sectors=self._number_sectors)
        return value_determiner

    def _init_associator(self, layout, log):
        kw = dict(layout=layout, log=log,
                  regard_controls=self.__regard_controls)
        associator = self.ASSOCIATOR_CLS(**kw)
        return associator

    def __find_volumes(self, layout, log):
        """
        Finds the volumes for each rack sector.

        :raises ValueError: If the volumes are inconsistent.
        """
        determiner = IsoRequestValueDeterminer(iso_request_layout=layout,
                                    attribute_name='iso_volume', log=log,
                                    regard_controls=self.__regard_controls)
        determiner.disable_error_and_warning_recording()
        self.__sector_volumes = determiner.get_result()

        if self.__sector_volumes is None:
            msg = ', '.join(determiner.get_messages())
            raise ValueError(msg)

    @classmethod
    def find(cls, log, iso_request_layout):
        """
        Tries to create an :class:`IsoRequestAssociationData`. In the first
        run controls are included. If the first run fails, a second run
        ignoring controls is started. If the second run fails, too, the
        return value is *None*.

        :param log: The ThelmaLog you want to write in.
        :type log: :class:`thelma.ThelmaLog`

        :param iso_request_layout: The ISO request layout whose sectors to
            associate.
        :type iso_request_layout: :class:`IsoRequestLayout`

        :returns: The association data and the controls (fixed position) mode
            or *None* if both attemps have failed.
        """
        regard_controls = True
        kw = dict(iso_request_layout=iso_request_layout,
                  log=log, regard_controls=regard_controls,
                  number_sectors=4)

        try:
            ad = IsoRequestAssociationData(**kw)
        except ValueError:
            regard_controls = False
            kw['regard_controls'] = regard_controls
            try:
                ad = IsoRequestAssociationData(**kw)
            except ValueError:
                return None

        return ad, regard_controls

