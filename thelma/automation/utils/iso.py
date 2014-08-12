"""
Classes related to ISO request plates.

AAB, Aug 2011
"""

from thelma.automation.utils.converters \
    import MoleculeDesignPoolLayoutConverter
from thelma.automation.utils.layouts import MOCK_POSITION_TYPE
from thelma.automation.utils.layouts import MoleculeDesignPoolLayout
from thelma.automation.utils.layouts import MoleculeDesignPoolParameters
from thelma.automation.utils.layouts import MoleculeDesignPoolPosition
from thelma.automation.utils.layouts import get_converted_number
from thelma.automation.utils.layouts import is_valid_number
from thelma.automation.utils.racksector import AssociationData
from thelma.automation.utils.racksector import RackSectorAssociator
from thelma.automation.utils.racksector import ValueDeterminer


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
    DOMAIN = 'iso_request'

    #: The molecule design pool (tag value: molecule design pool id).
    MOLECULE_DESIGN_POOL = MoleculeDesignPoolParameters.MOLECULE_DESIGN_POOL
    #: The requested volume in ul.
    ISO_VOLUME = 'iso_volume'
    #: The requested concentration in nM.
    ISO_CONCENTRATION = 'iso_concentration'
    #: The position type (fixed, floating, mock or empty).
    POS_TYPE = MoleculeDesignPoolParameters.POS_TYPE

    REQUIRED = [MOLECULE_DESIGN_POOL]
    ALL = MoleculeDesignPoolParameters.ALL + [ISO_VOLUME, ISO_CONCENTRATION]

    ALIAS_MAP = dict(MoleculeDesignPoolParameters.ALIAS_MAP, **{
                    ISO_CONCENTRATION : [], ISO_VOLUME : []})

    DOMAIN_MAP = dict(MoleculeDesignPoolParameters.DOMAIN_MAP, **{
                    ISO_CONCENTRATION : DOMAIN, ISO_VOLUME : DOMAIN})

    #: The minimum volume that can be requested by the stock management in ul.
    MINIMUM_ISO_VOLUME = 1

    MOCK_NON_PARAMETERS = MoleculeDesignPoolParameters.MOCK_NON_PARAMETERS \
                          + [ISO_CONCENTRATION]

    @classmethod
    def is_valid_mock_value(cls, value, parameter):
        if not super(IsoRequestParameters, cls).is_valid_mock_value(value,
                                                                    parameter):
            return False
        if parameter == cls.ISO_VOLUME:
            if value is None or is_valid_number(value):
                return True
            return False
        return True


class IsoRequestPosition(MoleculeDesignPoolPosition):
    """
    This class contains the data for one position in an ISO layout. The
    allowed and required values for the single parameters depend on the
    position type.

    **Equality condition**: equal :attr:`type`, :attr:`rack_position`,
                :attr:`molecule_design_pool` and :attr:`concentration`
    """
    PARAMETER_SET = IsoRequestParameters

    def __init__(self, rack_position, molecule_design_pool=None,
                 position_type=None, iso_concentration=None, iso_volume=None):
        """
        Constructor:

        :param rack_position: The rack position.
        :type rack_position: :class:`thelma.models.rack.RackPosition`.

        :param molecule_design_pool: The molecule design pool for this position
            or a valid placeholder.
        :type molecule_design_pool:
            :class:`thelma.models.moleculedesign.MoleculeDesignPool`
            or :class:`basestring`

        :param position_type: influences valid values for other parameters
        :type position_type: :class:`str

        :param iso_concentration: The concentration requested from the stock.
        :type iso_concentration: positive number

        :param iso_volume: The volume requested by the stock.
        :type iso_volume: positive number
        """
        MoleculeDesignPoolPosition.__init__(self, rack_position=rack_position,
                                    molecule_design_pool=molecule_design_pool,
                                    position_type=position_type)

        #: The concentration requested by the stock management.
        self.iso_concentration = get_converted_number(iso_concentration)
        #: The volume requested by the stock management.
        self.iso_volume = get_converted_number(iso_volume)

        self.__check_values_for_position_type()

    def __check_values_for_position_type(self):
        """
        Sets the position type and checks the validity of the values.
        """
        concentration_base_tpl = ('ISO concentration', self.iso_concentration)
        volume_base_tpl = ('ISO volume', self.iso_volume)

        if self.is_untreated_type:
            self._check_untreated_values([volume_base_tpl,
                                          concentration_base_tpl])
        elif self.is_empty:
            self._check_none_value([concentration_base_tpl, volume_base_tpl])

        elif self.is_mock:
            self._check_mock_values([concentration_base_tpl])
            self._check_numbers([volume_base_tpl], allow_none=True)

        else:
            self._check_numbers([volume_base_tpl, concentration_base_tpl], True)

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

    def _get_parameter_values_map(self):
        """
        Returns the :attr:`parameter_values_map`
        """
        parameter_map = MoleculeDesignPoolPosition._get_parameter_values_map(
                                                                        self)
        parameter_map[self.PARAMETER_SET.ISO_VOLUME] = self.iso_volume
        parameter_map[self.PARAMETER_SET.ISO_CONCENTRATION] = \
                                                    self.iso_concentration
        return parameter_map

    def __eq__(self, other):
        if not MoleculeDesignPoolPosition.__eq__(self, other): return False
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
    POSITION_CLS = IsoRequestPosition

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


class IsoRequestLayoutConverter(MoleculeDesignPoolLayoutConverter):
    """
    Converts an rack_layout into an :class:`IsoRequestLayout`.

    :Note: Untreated positions are converted to empty positions.
    """
    NAME = 'ISO Request Layout Converter'

    PARAMETER_SET = IsoRequestParameters
    LAYOUT_CLS = IsoRequestLayout
    POSITION_CLS = IsoRequestPosition

    def __init__(self, rack_layout, parent=None):
        MoleculeDesignPoolLayoutConverter.__init__(self,
                                                   rack_layout=rack_layout,
                                                   parent=parent)
        #: Do we expect ISO volumes and concentrations? If *False* these
        #: values are allowed to miss.
        self._expect_iso_values = True
        # intermediate storage of invalid rack positions
        self.__invalid_iso_volume = None
        self.__invalid_iso_concentration = None
        self.__missing_iso_volume = None
        self.__missing_iso_concentration = None

    def reset(self):
        """
        Resets all attributes except for the :attr:`rack_layout`.
        """
        MoleculeDesignPoolLayoutConverter.reset(self)
        self.__invalid_iso_volume = []
        self.__invalid_iso_concentration = []
        self.__missing_iso_volume = []
        self.__missing_iso_concentration = []

    def _get_position_init_values(self, parameter_map, rack_pos):
        kw = MoleculeDesignPoolLayoutConverter._get_position_init_values(self,
                                                     parameter_map, rack_pos)
        if kw is None: return None # includes empty and untreated type pos

        pos_type = kw['position_type']
        iso_concentration = parameter_map[self.PARAMETER_SET.ISO_CONCENTRATION]
        iso_volume = parameter_map[self.PARAMETER_SET.ISO_VOLUME]
        invalid = False

        is_mock = (pos_type == MOCK_POSITION_TYPE)
        if self._expect_iso_values and \
                    not self.__check_volume_and_concentration(iso_volume,
                             iso_concentration, rack_pos.label, is_mock):
            invalid = True

        if invalid: return None
        kw['iso_volume'] = iso_volume
        kw['iso_concentration'] = iso_concentration
        return kw

    def __check_volume_and_concentration(self, iso_volume, iso_conc,
                                        pos_label, is_mock=False):
        """
        Checks the volume and concentration for non-empty positions.
        """
        is_valid = True

        if iso_volume is None:
            self.__missing_iso_volume.append(pos_label)
            is_valid = False
        elif not is_valid_number(iso_volume):
            self.__invalid_iso_volume.append(pos_label)
            is_valid = False

        if is_mock:
            if not IsoRequestPosition.is_valid_mock_value(iso_conc,
                                  self.PARAMETER_SET.ISO_CONCENTRATION):
                info = '%s (%s, mock position)' % (iso_conc, pos_label)
                self.__invalid_iso_concentration.append(info)
                is_valid = False
        else:
            if iso_conc is None:
                self.__missing_iso_concentration.append(pos_label)
                is_valid = False
            elif not is_valid_number(iso_conc):
                self.__invalid_iso_concentration.append(pos_label)
                is_valid = False

        return is_valid

    def _record_errors(self):
        MoleculeDesignPoolLayoutConverter._record_errors(self)

        if len(self.__invalid_iso_volume) > 0:
            msg = 'Some position have invalid ISO volumes. The volume must ' \
                  'be a positive number. Details: %s.' \
                  % (self._get_joined_str(self.__invalid_iso_volume))
            self.add_error(msg)

        if len(self.__invalid_iso_concentration) > 0:
            msg = 'Some position have invalid ISO concentrations. The ' \
                  'concentration must a positive number. Details: %s.' \
                   % (self._get_joined_str(self.__invalid_iso_concentration))
            self.add_error(msg)

        if len(self.__missing_iso_volume) > 0:
            msg = 'Some position do not have an ISO volume specifications: %s.' \
                  % (self._get_joined_str(self.__missing_iso_volume))
            self.add_error(msg)

        if len(self.__missing_iso_concentration) > 0:
            msg = 'Some positions do not have an ISO concentration ' \
                  'specification: %s.' \
                  % (self._get_joined_str(self.__missing_iso_concentration))
            self.add_error(msg)


class IsoRequestValueDeterminer(ValueDeterminer):
    """
    There are two different modes: You can either regard only floating
    positions or regard both floating and control (fixed) positions.

    **Return Value:** A map containing the values for the different sectors.
    """
    NAME = 'ISO Request Value Determiner'

    LAYOUT_CLS = IsoRequestLayout

    def __init__(self, iso_request_layout, attribute_name, number_sectors,
                 regard_controls, parent=None):
        """
        Constructor.

        :param bool regard_controls: Flag indicating if control positions
            should be considered (floating positions are always considered).
        :param int number_sectors: The number of rack sectors.
        :default number_sectors: *4*
        """
        ValueDeterminer.__init__(self, iso_request_layout, attribute_name,
                                 number_sectors, parent=parent)
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
    NAME = 'ISO Request Rack Sector Associator'
    LAYOUT_CLS = IsoRequestLayout
    SECTOR_ATTR_NAME = 'iso_concentration'

    def __init__(self, layout, regard_controls, number_sectors=4,
                 parent=None):
        """
        Constructor.

        :param regard_controls: Shall controls positions be regarded (*True*)
            or be ignored (*False* - floating positions are always regarded)?
        :type regard_controls: :class:`bool`
        """
        RackSectorAssociator.__init__(self, layout,
                                      number_sectors=number_sectors,
                                      parent=parent)
        #: Flag indicating if control (Fixed) position should be considered.
        self.regard_controls = regard_controls

    def _check_input(self):
        RackSectorAssociator._check_input(self)
        self._check_input_class('"regard controls" flag', self.regard_controls,
                                bool)

    def _init_value_determiner(self):
        value_determiner = IsoRequestValueDeterminer(self.layout,
                                                     self.SECTOR_ATTR_NAME,
                                                     self.number_sectors,
                                                     self.regard_controls,
                                                     parent=self)
        return value_determiner

    def _get_molecule_design_pool_id(self, layout_pos):
        """
        In addition to the superclass method fixed positions are only regarded
        if :attr:`regard_controls` is *True*.
        """
        if not layout_pos is None and layout_pos.is_fixed and \
                                                not self.regard_controls:
            result = None
        else:
            result = \
                RackSectorAssociator._get_molecule_design_pool_id(self,
                                                                  layout_pos)
        return result


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

    def __init__(self, layout, tool, regard_controls):
        """
        Constructor.

        :param bool regard_controls: Flag indicating if controls positions
            should be considered (floating positions are always included).
        """
        self.__regard_controls = regard_controls
        AssociationData.__init__(self, layout, tool, record_errors=False)
        #: The volumes for each rack sector.
        self.__sector_volumes = None
        self.__find_volumes(layout, tool)

    @property
    def sector_volumes(self):
        """
        The volumes for each sector.
        """
        return self.__sector_volumes

    @property
    def regard_controls(self):
        """
        Do fixed positions adhere to the sector data (*True*) or do they
        have to be treated separately (*False*)?
        """
        return self.__regard_controls

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

    def _init_value_determiner(self, layout, tool):
        """
        The name of the concentration attribute is derived from the
        :attr:`ASSOCIATOR_CLS`.
        """
        value_determiner = \
            IsoRequestValueDeterminer(layout,
                                      self.ASSOCIATOR_CLS.SECTOR_ATTR_NAME,
                                      self._number_sectors,
                                      self.__regard_controls,
                                      parent=tool)
        return value_determiner

    def _init_associator(self, layout, tool):
        args = (layout, self.__regard_controls)
        kw = dict(parent=tool)
        associator = self.ASSOCIATOR_CLS(*args, **kw)
        return associator

    def __find_volumes(self, layout, tool):
        """
        Finds the volumes for each rack sector.

        :raises ValueError: If the volumes are inconsistent.
        """
        determiner = IsoRequestValueDeterminer(iso_request_layout=layout,
                                    attribute_name='iso_volume', parent=tool,
                                    regard_controls=self.__regard_controls,
                                    number_sectors=self._number_sectors)
        determiner.disable_error_and_warning_recording()
        self.__sector_volumes = determiner.get_result()
        if self.__sector_volumes is None:
            msg = 'Error when trying to determine sector volumes.'
            raise ValueError(msg)
        else:
            self._remove_none_sectors(self.__sector_volumes)

    @classmethod
    def find(cls, layout, tool):
        """
        Tries to create an :class:`IsoRequestAssociationData`. In the first
        run controls are included. If the first run fails, a second run
        ignoring controls is started. If the second run fails, too, the
        return value is *None*.

        :param tool: The calling tool recording messages.
        :param layout: The ISO request layout whose sectors to associate.
        :type layout: :class:`IsoRequestLayout`
        :returns: The association data and the controls (fixed position) mode
            or *None* if both attemps have failed.
        """
        regard_controls = True
        kw = dict(layout=layout,
                  tool=tool,
                  regard_controls=regard_controls)
        try:
            ad = cls(**kw)
        except ValueError:
            regard_controls = False
            kw['regard_controls'] = regard_controls
            try:
                ad = cls(**kw)
            except ValueError:
                return None, None
        return ad, regard_controls
