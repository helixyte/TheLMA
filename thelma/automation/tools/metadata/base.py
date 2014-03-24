"""
Classes related to transfection worklist generation
(robot worklist generations).

AAB, Sept 2011
"""
from thelma.automation.semiconstants import PIPETTING_SPECS_NAMES
from thelma.automation.semiconstants import get_min_transfer_volume
from thelma.automation.semiconstants import get_positions_for_shape
from thelma.automation.semiconstants import get_reservoir_specs_standard_96
from thelma.automation.tools.worklists.base import get_dynamic_dead_volume
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.utils.base import add_list_map_element
from thelma.automation.utils.base import get_converted_number
from thelma.automation.utils.base import get_trimmed_string
from thelma.automation.utils.base import is_valid_number
from thelma.automation.utils.base import round_up
from thelma.automation.utils.iso import IsoRequestAssociationData
from thelma.automation.utils.iso import IsoRequestLayout
from thelma.automation.utils.iso import IsoRequestLayoutConverter
from thelma.automation.utils.iso import IsoRequestParameters
from thelma.automation.utils.iso import IsoRequestPosition
from thelma.automation.utils.iso import IsoRequestSectorAssociator
from thelma.automation.utils.iso import IsoRequestValueDeterminer
from thelma.automation.utils.layouts import LIBRARY_POSITION_TYPE
from thelma.automation.utils.layouts import MOCK_POSITION_TYPE
from thelma.models.moleculetype import MOLECULE_TYPE_IDS
from thelma.models.moleculetype import MoleculeType
from thelma.models.racklayout import RackLayout
from thelma.models.tagging import TaggedRackPositionSet

__docformat__ = "reStructuredText en"

__all__ = ['TransfectionParameters',
           'TransfectionPosition',
           'TransfectionLayout',
           'TransfectionLayoutConverter',
           'TransfectionSectorAssociator',
           'TransfectionAssociationData']


class TransfectionParameters(IsoRequestParameters):
    """
    This a list of parameters required to generate a BioMek transfection
    worklist when translating an ISO plate into a cell plate.
    """

    #: The domain for transfer-related tags.
    DOMAIN = 'transfection'

    #: The final RNAi concentration in the assay.
    FINAL_CONCENTRATION = 'final_concentration'
    #: The molecule design pool (tag value: molecule design pool id).
    MOLECULE_DESIGN_POOL = IsoRequestParameters.MOLECULE_DESIGN_POOL
    #: The volume requested in the ISO in ul.
    ISO_VOLUME = IsoRequestParameters.ISO_VOLUME
    #: The concentration requested in the ISO in nM.
    ISO_CONCENTRATION = IsoRequestParameters.ISO_CONCENTRATION
    #: The position type (fixed, floating or empty).
    POS_TYPE = IsoRequestParameters.POS_TYPE
    #: The name of the RNAi reagent.
    REAGENT_NAME = 'reagent_name'
    #: The final dilution factor of the RNAi reagent in the cell plate.
    REAGENT_DIL_FACTOR = 'reagent_dilution_factor'
    #: The OptiMem dilution factor usually depends on the molecule type.
    #: In library screenings however the factor is variable depending on the
    #: final concentration.
    OPTIMEM_DIL_FACTOR = 'optimem_dilution_factor'

    ALL = IsoRequestParameters.ALL + [REAGENT_NAME, REAGENT_DIL_FACTOR,
                                      FINAL_CONCENTRATION, OPTIMEM_DIL_FACTOR]

    #: A map storing alias predicates for each parameter.
    ALIAS_MAP = dict(IsoRequestParameters.ALIAS_MAP, **{
                 FINAL_CONCENTRATION : [],
                 REAGENT_NAME : [],
                 REAGENT_DIL_FACTOR : ['reagent_concentration'],
                 OPTIMEM_DIL_FACTOR : []})

    #: Maps tag predicates on domains.
    DOMAIN_MAP = dict(IsoRequestParameters.DOMAIN_MAP, **{
                  FINAL_CONCENTRATION : DOMAIN,
                  REAGENT_NAME : DOMAIN,
                  REAGENT_DIL_FACTOR : DOMAIN,
                  OPTIMEM_DIL_FACTOR : DOMAIN})

    # Constants for calculations

    #: The volume transferred into each cell (experiment) plate well (in ul).
    TRANSFER_VOLUME = 5

    #: The minimum volume that can be requested by the stockmanagement.
    MINIMUM_ISO_VOLUME = IsoRequestParameters.MINIMUM_ISO_VOLUME

    #: The dilution factor for the transfection reagent dilution (mastermix
    #: step - as opposed to the final dilution factor of the reagent itself
    #: which is specified as part of the experiment metadata).
    REAGENT_MM_DILUTION_FACTOR = 2
    #: The dilution factor for the dilution with cell suspension.
    CELL_DILUTION_FACTOR = 7


    #: The optimem dilution factor for miRNA molecule types.
    MIRNA_OPTIMEM_DILUTION_FACTOR = 3
    #: The optimem dilution factor for other molecule types.
    STANDARD_OPTIMEM_DILUTION_FACTOR = 4

    #: The default molecule type for mock positions.
    DEFAULT_MOLECULE_TYPE = MOLECULE_TYPE_IDS.SIRNA

    MOCK_NON_PARAMETERS = IsoRequestParameters.MOCK_NON_PARAMETERS \
                          + [FINAL_CONCENTRATION]

    @classmethod
    def is_valid_mock_value(cls, value, parameter):
        if not super(TransfectionParameters, cls).is_valid_mock_value(value,
                                                                  parameter):
            return False
        if parameter in {cls.REAGENT_DIL_FACTOR, cls.OPTIMEM_DIL_FACTOR}:
            if value is None: return True
            return is_valid_number(value)
        elif parameter == cls.REAGENT_NAME:
            if value is None: return True
            if not isinstance(value, basestring) or not len(value) > 2:
                return False
        return True

    @classmethod
    def calculate_iso_volume(cls, number_target_wells, number_replicates,
                             iso_reservoir_spec, optimem_dil_factor,
                             pipetting_specs):
        """
        Calculates the ISO volume required to fill the given number
        of target wells (assuming the given number of interplate replicates).

        :param number_target_wells: The number of target wells in all
            design racks of an experiment design.
        :type number_target_wells: :class:`int`

        :param number_replicates: The number of replicates.
        :type number_replicates: :class:`int`

        :param optimem_dil_factor: The optimem dilution factor depends on
            molecule type or final concentration.
        :type optimem_dil_factor: positive number

        :param iso_reservoir_spec: The reservoir specs to be assumed.
        :type iso_reservoir_spec:
            :class:`thelma.models.liquidtransfer.ReservoirSpecs`
        :return: The ISO volume that should be ordered in the ISO to generate
            an sufficient amount of mastermix solution.

        :param pipetting_specs: Defines whether to use a static dead volume
            or a dynamic (represents Biomek-transfer).
        :type pipetting_specs: :class:`PipettingSpecs`
        """
        required_volume = cls.\
                calculate_mastermix_volume_from_target_well_number(
                    number_target_wells, number_replicates, iso_reservoir_spec,
                    pipetting_specs)
        iso_volume = required_volume / (cls.REAGENT_MM_DILUTION_FACTOR \
                                        * optimem_dil_factor)

        min_volume = get_min_transfer_volume(pipetting_specs)

        if iso_volume < min_volume: iso_volume = min_volume
        return round_up(iso_volume)

    @classmethod
    def get_optimem_dilution_factor_from_molecule_type(cls, molecule_type):
        """
        Returns the optimem dilution factor for a molecule type or molecule
        type name.

        :param molecule_type: The molecule types for the molecule design pool.
        :type molecule_type: :class:`thelma.models.moleculetype.MoleculeType`
            or :class:`str` (molecule type ID)
        :raises TypeError: For molecule types of the wrong class.
        :raises ValueError: If the molecule type is unknown.
        :return: The OptiMem dilution factor for this molecule type.
        """
        if isinstance(molecule_type, MoleculeType):
            mt_id = molecule_type.id
        elif isinstance(molecule_type, basestring):
            if MOLECULE_TYPE_IDS.is_known_type(molecule_type):
                mt_id = molecule_type
            else:
                msg = 'Unknown molecule type name "%s".' % (molecule_type)
                raise ValueError(msg)
        else:
            msg = 'The molecule types must be a %s object or a string ' \
                  '(obtained: %s).' % (MoleculeType.__class__.__name__,
                   molecule_type.__class__.__name__)
            raise TypeError(msg)

        if mt_id == MOLECULE_TYPE_IDS.MIRNA_INHI or \
                                    mt_id == MOLECULE_TYPE_IDS.MIRNA_MIMI:
            return cls.MIRNA_OPTIMEM_DILUTION_FACTOR
        else:
            return cls.STANDARD_OPTIMEM_DILUTION_FACTOR

    @classmethod
    def get_total_dilution_factor(cls, optimem_dilution_factor):
        """
        The total dilution factor for the transfection preparation
        (comprised of transfection reagent, OptiMem and cell suspension
        dilution).

        :param optimem_dilution_factor: The optimem dilution factor depends on
            molecule type or final concentrations.
        :type optimem_dilution_factor: positive number
        :return: The total dilution factor.
        """
        return cls.REAGENT_MM_DILUTION_FACTOR * cls.CELL_DILUTION_FACTOR \
                * optimem_dilution_factor

    @classmethod
    def calculate_mastermix_volume_from_target_well_number(cls,
                number_target_wells, number_replicates, iso_reservoir_spec,
                pipetting_specs=None):
        """
        Calculates the mastermix volume including transfection reagent.
        (assuming the given number of target wells and interplate replicates).

        :param number_target_wells: The number of target wells in all
            design racks fo an experiment design.
        :type number_target_wells: :class:`int`

        :param number_replicates: The number of replicates.
        :type number_replicates: :class:`int`

        :param iso_reservoir_spec: The reservoir specs to be assumed.
        :type iso_reservoir_spec:
            :class:`thelma.models.liquidtransfer.ReservoirSpecs`

        :param pipetting_specs: Defines whether to use a static dead volume
            or a dynamic dead volume correction (e.g. for Biomek).
        :type pipetting_specs: :class:`PipettingSpecs`
        :default pipetting_specs: *None* (with correction)

        :return: The determined volume required to fill these wells.
        """
        well_number = number_target_wells * number_replicates

        if pipetting_specs is None or pipetting_specs.has_dynamic_dead_volume:
            dead_volume = get_dynamic_dead_volume(
                                            target_well_number=well_number,
                                            reservoir_specs=iso_reservoir_spec)
        else:
            dead_volume = iso_reservoir_spec.min_dead_volume \
                          * VOLUME_CONVERSION_FACTOR

        required_volume = well_number * cls.TRANSFER_VOLUME + dead_volume
        return required_volume

    @classmethod
    def calculate_mastermix_volume_from_iso_volume(cls, iso_volume,
                                                   optimem_dil_factor):
        """
        Returns the maximum volume of a mastermix (the volume of the complete
        complex with all its ingredients).

        :param iso_volume: The ISO volume.
        :type iso_volume: positive number

        :param optimem_dil_factor: The optimem dilution factor depends on
            molecule type or final concentration.
        :type optimem_dil_factor: positive number

        :rtype: :class:`float`
        """
        reagent_dilution_volume = cls.calculate_reagent_dilution_volume(
                iso_volume=iso_volume, optimem_dil_factor=optimem_dil_factor)
        return reagent_dilution_volume * 2

    @classmethod
    def calculate_reagent_dilution_volume(cls, iso_volume, optimem_dil_factor):
        """
        Returns the reagent volume that is needed for an 1:2 dilution
        with RNAi reagent.

        :param iso_volume: An ISO volume.
        :type iso_volume: numeric, positive

        :param optimem_dil_factor: The optimem dilution factor depends on
            molecule type or final concentration.
        :type optimem_dil_factor: positive number

        :return: The required volume.
        """
        return float(iso_volume) * optimem_dil_factor

    @classmethod
    def calculate_initial_reagent_dilution(cls, reagent_dil_factor):
        """
        Returns the initial reagent dilution (the dilution that has be
        provided for the 1:2 dilution step).

        :param reagent_dil_factor: The final reagent dilution factor.
        :type reagent_dil_factor: :class:`int`
        :return: The initial dilution factor.
        """
        return reagent_dil_factor / \
               (cls.REAGENT_MM_DILUTION_FACTOR * cls.CELL_DILUTION_FACTOR)

    # TODO: review and replace
    @classmethod
    def get_critical_iso_concentration(cls, stock_concentration):
        """
        Returns the critical ISO concentration in ul.

        ISO concentrations that are larger than this value might cause slight
        inaccuracies in the concentration when using the Biomek (due to the
        transfer volume step width of 0.1 ul).

        :param stock_concentration: The stock concentration for molecule design
            pool in nM.
        :type stock_concentration: positive number
        :return: critical ISO concentration in ul.
        """
        rs = get_reservoir_specs_standard_96()
        std_96_min_dead_vol = rs.min_dead_volume * VOLUME_CONVERSION_FACTOR
        min_biomek_transfer_vol = get_min_transfer_volume(
                                                PIPETTING_SPECS_NAMES.BIOMEK)

        crit_iso_conc = stock_concentration \
                    / ((std_96_min_dead_vol + cls.MINIMUM_ISO_VOLUME) \
                    / (std_96_min_dead_vol + cls.MINIMUM_ISO_VOLUME \
                       - min_biomek_transfer_vol))

        return crit_iso_conc

    # TODO: review and replace
    @classmethod
    def get_critical_final_concentration(cls, stock_concentration,
                                         optimem_dil_factor=None):
        """
        Returns the critical final concentration in ul.

        Final concentrations that are larger than this value might cause slight
        inaccuracies in the concentration when using the Biomek (due to the
        transfer volume step width of 0.1 ul).

        If you do not provide an OptiMem dilution factor, the dilution factor
        is determined via the molecule type.

        :param stock_concentration: The stock concentration for the molecule
            design pool in nM.
        :type stock_concentration: positive number

        :param optimem_dil_factor: The optimem dilution factor depends on
            molecule type or final concentration.
        :type optimem_dil_factor: positive number

        :param optimem_dil_factor: The optimem dilution factor depends on
            molecule type or final concentration.
        :type optimem_dil_factor: positive number
        :default optimem_dil_factor: *None*

        :return: critical final concentration in ul.
        """
        crit_iso_conc = cls.get_critical_iso_concentration(stock_concentration)
        # The ODF differs only in library experiment and these do not
        # need ISO concentration checking.
        total_df = cls.get_total_dilution_factor(optimem_dil_factor)
        crit_final_conc = crit_iso_conc / total_df
        return crit_final_conc

    @classmethod
    def get_layout_mock_optimem_molecule_type(cls, working_layout):
        """
        Returns the molecule type for mock positions in a layout (to be used for
        the determination of a optimem dilution factor). If there is only
        one OptiMem factor, the optimem factor for this factor is returned.
        Otherwise the function returns the optimem dilution factor for the
        :attr:`DEFAULT_MOLECULE_TYPE`.

        Make sure, the OptiMem dilution factors of the layout are set.
        """
        fixed_optimem_dfs = set()
        for wp in working_layout.working_positions():
            if wp.is_fixed:
                optimem_df = wp.optimem_dil_factor
                fixed_optimem_dfs.add(optimem_df)
        if len(fixed_optimem_dfs) == 1:
            return list(fixed_optimem_dfs)[0]
        else:
            mock_mt = cls.DEFAULT_MOLECULE_TYPE
            optimem_df = cls.get_optimem_dilution_factor_from_molecule_type(
                                                                     mock_mt)
            return optimem_df

    @classmethod
    def get_floating_placeholder(cls, num):
        """
        Returns a value floating placeholder (suitable for recognition as
        floating via :func:`get_position_type`).

        :param num: a number for the placeholder
        :type num: :class:`int`
        """
        return '%s%03i' % (cls.FLOATING_INDICATOR, num)


class TransfectionPosition(IsoRequestPosition):
    """
    This class represents a source position in an ISO layout. The target
    positions are the target in the final cell (experiment) plate.
    """

    #: The parameter set this working position is associated with.
    PARAMETER_SET = TransfectionParameters

    #: The delimiter for the different target infos.
    POSITION_DELIMITER = '-'

    def __init__(self, rack_position, molecule_design_pool=None,
                 position_type=None, reagent_name=None, reagent_dil_factor=None,
                 iso_volume=None, iso_concentration=None,
                 final_concentration=None, optimem_dil_factor=None):
        """
        :param rack_position: The rack position.
        :type rack_position: :class:`thelma.models.rack.RackPosition`.

        :param molecule_design_pool: The molecule design pool or placeholder for
            the RNAi reagent.
        :type molecule_design_pool: :class`int` (ID), :class:`str` (placeholder)
            or :class:`thelma.models.moleculedesign.StockSampleMoleculeDesign`

        :param position_type: influences valid values for other parameters
        :type position_type: :class:`str

        :param reagent_name: The name of the transfection reagent.
        :type reagent_name: :class:`str`

        :param reagent_dil_factor: The final dilution factor of the
            transfection reagent in the cell plate.
        :type reagent_dil_factor: positive number, no unit

        :param iso_volume: The volume requested by the stock management.
        :type iso_volume: positive number, unit ul

        :param iso_concentration: The concentration requested by the stock
            management.
        :type iso_concentration: positive number, unit nM

        :param final_concentration: The final concentration of the RNAi
            reagent in the cell plate.
        :type final_concentration: positive number, unit nM

        :param optimem_dil_factor: The dilution factor for the OptiMem dilution
            (use only if you do not want to use the default factor).
        :type optimem_dil_factor: positive number
        """
        IsoRequestPosition.__init__(self, rack_position=rack_position,
                             molecule_design_pool=molecule_design_pool,
                             position_type=position_type, iso_volume=iso_volume,
                             iso_concentration=iso_concentration)

        #: Stores the position in the cell plate that are filled by this
        #: source positions (:class:`set` of
        #: :class:`thelma.models.rack.RackPosition` objects).
        self.cell_plate_positions = set()

        #: The name of the RNAi reagent.
        self.reagent_name = reagent_name
        #: The final dilution factor RNAi reagent in the cell plate.
        self.reagent_dil_factor = get_converted_number(reagent_dil_factor)

        #: The final concentration in the cell plate (experiment plate).
        self.final_concentration = get_converted_number(final_concentration)

        #: The optimem dilution factor set in library screenings (because
        #: in this case it is depending on the final concentration instead
        #: of depending on the molecule type).
        self._optimem_dil_factor = optimem_dil_factor

        tf_attrs = [('reagent name', self.reagent_name),
                    ('reagent dilution factor', self.reagent_dil_factor),
                    ('final concentration', self.final_concentration),
                    ('optimem dilution factor', self._optimem_dil_factor)]
        if self.is_untreated_type:
            self._check_untreated_values(tf_attrs)
        elif self.is_empty:
            self._check_none_value(tf_attrs)
        else:
            if self.reagent_name is not None and \
                        (not isinstance(self.reagent_name, basestring) or \
                         len(self.reagent_name) < 2):
                msg = 'The reagent name must be at least 2 characters long ' \
                      'if there is one (obtained: "%s")!' % (self.reagent_name)
                raise ValueError(msg)
            numericals = [tf_attrs[1], tf_attrs[3]]
            if self.is_mock:
                self._check_mock_values([tf_attrs[2]])
            else:
                numericals.append(tf_attrs[2])
            self._check_numbers(numericals, allow_none=True)

    @property
    def hash_full(self):
        """
        A string that can be used as hash value for comparison. This hash
        covers all four parameters (molecule design pool, reagent name, reagent
        concentration and final concentration) needed to make well
        associations.
        """
        if self.is_empty: return '%s' % (self.rack_position)

        fc = self.final_concentration
        if self.is_mock: fc = None
        return '%s%s%s%s' % (self.molecule_design_pool_id,
                             self.reagent_name,
                             get_trimmed_string(self.reagent_dil_factor),
                             get_trimmed_string(fc))

    @property
    def hash_partial(self):
        """
        A string that can be used as hash value. This hash covers only three
        three of the four parameters (molecule design pool, reagent name
        and reagent concentration). It is meant to enable comparison of
        manual ISO definitions, in which the final concentraiton is not known.
        """
        if self.is_empty: return '%s' % (self.rack_position)

        return '%s%s%s' % (self.molecule_design_pool_id,
                           self.reagent_name,
                           get_trimmed_string(self.reagent_dil_factor))

    @property
    def optimem_dil_factor(self):
        """
        The dilution factor depends on the molecule type (for most experiment
        scenarios) or on the final concentration (for library screenings).
        """
        return self._optimem_dil_factor

    def store_optimem_dilution_factor(self):
        """
        This method is meant for fixed position that can derive the OptiMem
        dilution factor from the pool.
        """
        self._optimem_dil_factor = TransfectionParameters.\
                    get_optimem_dilution_factor_from_molecule_type(
                    self.molecule_design_pool.molecule_type)

    def set_optimem_dilution_factor(self, optimem_df):
        """
        The OptiMem dilution factor must be a positive number.
        The factor might only be set ones, except for fixed positions.

        :raises AttributeError: If the factor has been set before.
        :raises ValueError: If the factor is not a positive number.
        """
        if not is_valid_number(optimem_df):
            msg = 'The OptiMem dilution factor must be a positive number ' \
                  '(obtained: %s).' % (optimem_df)
            raise ValueError(msg)
        if not self._optimem_dil_factor is None and not self.is_fixed:
            raise AttributeError('The OptiMem dilution factor has already ' \
                                 'been set!')

        self._optimem_dil_factor = optimem_df

    def get_total_dilution_factor(self):
        """
        Returns the total tranfecion dilution factor for this molecule type.
        """
        if self._optimem_dil_factor is None: return None
        return TransfectionParameters.get_total_dilution_factor(
                            optimem_dilution_factor=self._optimem_dil_factor)

    def calculate_reagent_dilution_volume(self):
        """
        Returns the reagent volume that has be added to this well.
        Make sure, the OptiMem dilution factor of the postion is set.
        """
        if self.is_empty or self.iso_volume is None: return None

        return TransfectionParameters.calculate_reagent_dilution_volume(
                                self.iso_volume, self.optimem_dil_factor)

    @classmethod
    def create_library_position(cls, rack_position):
        """
        Creates a transfection position representing a mock well.

        :return: A transfection position.
        """
        kw = dict(molecule_design_pool=LIBRARY_POSITION_TYPE,
                  rack_position=rack_position)
        return TransfectionPosition(**kw)


    @classmethod
    def create_mock_position(cls, rack_position):
        """
        Creates a transfection position representing a mock well.

        :return: A transfection position.
        """
        kw = dict(molecule_design_pool=MOCK_POSITION_TYPE,
                  rack_position=rack_position)
        return TransfectionPosition(**kw)

    @classmethod
    def create_untreated_position(cls, rack_position, position_type):
        """
        Creates a transfection position representing an untreated (empty) well.

        :return: A transfection position.
        """
        return TransfectionPosition(rack_position=rack_position,
                        molecule_design_pool=position_type,
                        reagent_name=position_type,
                        reagent_dil_factor=position_type,
                        final_concentration=position_type)

    def copy(self):
        """
        Returns a copy of this transfection position.
        """
        tf_pos = TransfectionPosition(rack_position=self.rack_position,
                      molecule_design_pool=self.molecule_design_pool,
                      position_type=self.position_type,
                      reagent_name=self.reagent_name,
                      reagent_dil_factor=self.reagent_dil_factor,
                      iso_volume=self.iso_volume,
                      iso_concentration=self.iso_concentration,
                      final_concentration=self.final_concentration,
                      optimem_dil_factor=self._optimem_dil_factor)
        return tf_pos

    def _get_parameter_values_map(self):
        """
        Returns a map containing the value for each parameter.
        """
        parameters = dict()
        parameters[self.PARAMETER_SET.MOLECULE_DESIGN_POOL] = \
                                            self.molecule_design_pool
        parameters[self.PARAMETER_SET.ISO_VOLUME] = self.iso_volume
        parameters[self.PARAMETER_SET.ISO_CONCENTRATION] = \
                                                    self.iso_concentration
        parameters[self.PARAMETER_SET.POS_TYPE] = self.position_type
        parameters[self.PARAMETER_SET.REAGENT_NAME] = self.reagent_name
        parameters[self.PARAMETER_SET.REAGENT_DIL_FACTOR] = \
                                        self.reagent_dil_factor
        parameters[self.PARAMETER_SET.FINAL_CONCENTRATION] = \
                                        self.final_concentration
        parameters[self.PARAMETER_SET.OPTIMEM_DIL_FACTOR] = \
                                        self._optimem_dil_factor
        return parameters

    def __eq__(self, other):
        if not IsoRequestPosition.__eq__(self, other): return False
        if not self.is_empty:
            if not self.reagent_name == other.reagent_name:
                return False
            if not self.reagent_dil_factor == other.reagent_dil_factor:
                return False
        if not (self.is_mock or self.is_empty):
            if not self.final_concentration == other.final_concentration:
                return False
        return True

    def __repr__(self):
        str_format = '<%s rack position: %s, molecule design pool: %s ' \
                     'ISO volume: %s, ISO concentration: %s, reagent name %s, ' \
                     'reagent dilution factor: %s>'
        params = (self.__class__.__name__, self.rack_position,
                  self.molecule_design_pool, self.iso_volume,
                  self.iso_concentration, self.reagent_name,
                  self.reagent_dil_factor)
        return str_format % params


class TransfectionLayout(IsoRequestLayout):
    """
    A working container for transfection positions. Transfection positions
    contain data about the ISO, the mastermix and transfer parameters.
    """

    WORKING_POSITION_CLASS = TransfectionPosition

    def copy(self):
        """
        Returns a copy of this layout.
        """
        copied = TransfectionLayout(shape=self.shape)
        for tf_pos in self._position_map.values():
            copied_pos = tf_pos.copy()
            copied.add_position(copied_pos)
        return copied

    def has_iso_concentrations(self):
        """
        Returns *True* if there are ISO concentrations specified in this
        transfection layout.
        """
        for working_pos in self._position_map.values():
            if working_pos.is_empty or working_pos.is_mock: continue
            if not working_pos.iso_concentration is None: return True
        return False

    def has_iso_volumes(self):
        """
        Returns *True* if there are ISO volumes specified in this
        transfection layout.
        """
        for working_position in self._position_map.values():
            if working_position.is_empty: continue
            if not working_position.iso_volume is None: return True
        return False

    def has_final_concentrations(self):
        """
        Returns *True* there are final concentrations specified in the
        this transfection layout.
        """
        for working_pos in self._position_map.values():
            if working_pos.is_empty or working_pos.is_mock: continue
            if not working_pos.final_concentration is None: return True
        return False

    def create_merged_rack_layout(self, additional_trps, user):
        """
        Returns a rack layout that contains the passed tags and all tags
        of this layout.

        :param additional_trps: non-transfection tags (as
            :class:`TaggedRackPositionSet`) mapped onto their
            rack positions set hash values
        type additional_trps: :class:`dict`

        :param user: The user creating the tag, usually the request of
            the ISO request.
        :type user: :class:`thelma.models.user.User`
        :return: the completed :class:`thelma.models.racklayout.RackLayout`
        """
        if len(additional_trps) < 1: return self.create_rack_layout()

        # get transfection layout data
        self.close()
        trp_sets = self.create_tagged_rack_position_sets()

        # get tagged rack positions sets, map tags onto hash values
        trps_map = dict()
        for trps in trp_sets:
            trps_map[trps.rack_position_set.hash_value] = trps

        # add tags
        for hash_value, trps in additional_trps.iteritems():
            if trps_map.has_key(hash_value):
                tf_trps = trps_map[hash_value]
                for tag in trps.tags:
                    tf_trps.add_tag(tag, user)
            else:
                trps_map[hash_value] = trps

        return RackLayout(shape=self.shape,
                          tagged_rack_position_sets=trps_map.values())

    @classmethod
    def complete_rack_layout_with_screening_tags(cls, exp_rack_layout,
                                                 iso_request_rack_layout, user):
        """
        Returns a rack layout with the transfection data of the layout
        added to it. This method is used to create the experiment design rack
        layouts for screening and library cases.
        ISO data (ISO volume and ISO concentration) is excluded.

        :param exp_rack_layout: The rack layout to complete.
        :type exp_rack_layout: :class:`thelma.models.racklayout.RackLayout`

        :param iso_request_rack_layout: The rack layout of the ISO request
            (which might contain customized tags).
        :type iso_request_rack_layout:
            :class:`thelma.models.racklayout.RackLayout`
        """

        trps_map = dict()

        for trps in exp_rack_layout.tagged_rack_position_sets:
            hash_value = trps.rack_position_set.hash_value
            trps_map[hash_value] = trps

        excluded_parameters = [IsoRequestParameters.ISO_VOLUME,
                               IsoRequestParameters.ISO_CONCENTRATION]

        for trps in iso_request_rack_layout.tagged_rack_position_sets:
            hash_value = trps.rack_position_set
            tags = []
            for tag in trps.tags:
                predicate = tag.predicate
                if (predicate in excluded_parameters): continue
                tags.append(tag)
            if trps_map.has_key(hash_value):
                trps = trps_map[hash_value]
                for tag in tags:
                    trps.add_tag(tag, user)
            elif len(tags) < 1:
                # might be the case if there are only ISO volume or ISO
                # concentration tags in a new tagged rack position set
                continue
            else:
                trps = TaggedRackPositionSet(set(tags), trps.rack_position_set,
                                             user)
                trps_map[hash_value] = trps

        return RackLayout(shape=exp_rack_layout.shape,
                          tagged_rack_position_sets=trps_map.values())

    @staticmethod
    def compare_ignoring_untreated_types(layout1, layout2):
        """
        Compares two transfection layouts ignoring potential untreated
        positions.
        """
        if layout1.shape != layout2.shape: return False

        for rack_pos in get_positions_for_shape(layout1.shape):
            tf1 = layout1.get_working_position(rack_pos)
            tf2 = layout2.get_working_position(rack_pos)
            if tf1 is None and tf2 is None: continue
            if tf1 is not None and (tf1.is_untreated_type or tf1.is_empty):
                tf1 = None
            if tf2 is not None and (tf2.is_untreated_type or tf2.is_empty):
                tf2 = None
            if tf1 is None and tf2 is None:
                continue
            elif not tf1 == tf2:
                return False

        return True


class TransfectionLayoutConverter(IsoRequestLayoutConverter):
    """
    Converts a rack layout into a IdQuartetLayout. These layouts types are
    only used to ensure layout uniqueness.
    """
    NAME = 'Transfection Layout Converter'

    PARAMETER_SET = TransfectionParameters
    LAYOUT_CLS = TransfectionLayout
    POSITION_CLS = TransfectionPosition

    def __init__(self, rack_layout, log, is_iso_request_layout=True,
                 is_mastermix_template=False):
        """
        Constructor:

        :param rack_layout: The rack layout containing the ISO data.
        :type rack_layout: :class:`thelma.models.racklayout.RackLayout`

        :param is_iso_request_layout: Defines if certain parameters are allowed
            to be missing (final concentration, reaagent name,
            reagent dil factor).
        :type is_iso_request_layout: :class:`boolean`
        :default is_iso_request_layout: True

        :param is_mastermix_template: Defines if certain parameters are allowed
            to be missing (ISO volume, ISO concentration, position type).
            If *True*, \'is_iso_layout\' must be false.
        :type is_mastermix_template: :class:`boolean`
        :default is_mastermix_layout: False

        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`
        """
        IsoRequestLayoutConverter.__init__(self, rack_layout=rack_layout,
                                           log=log)

        #: Defines if certain parameters are allowed to be missing (final
        #: concentration, reaagent name, reagent dil factor).
        self.__is_iso_request_layout = is_iso_request_layout
        #: Defines if certain parameters are allowed to be missing (ISO
        #: volume, ISO concentration).
        self.__is_mastermix_template = is_mastermix_template

        # intermediate storage of invalid rack positions
        self.__invalid_dil_factor = None
        self.__invalid_name = None
        self.__invalid_final_concentration = None
        self.__invalid_optimem_factor = None
        self.__missing_reagent_name = None
        self.__missing_reagent_df = None
        self.__missing_final_conc = None

    def reset(self):
        """
        Resets all attributes except for the :attr:`rack_layout`.
        """
        IsoRequestLayoutConverter.reset(self)
        self.__invalid_dil_factor = []
        self.__invalid_name = []
        self.__invalid_final_concentration = []
        self.__invalid_optimem_factor = []
        self.__missing_reagent_name = []
        self.__missing_reagent_df = []
        self.__missing_final_conc = []

    def _check_input(self):
        IsoRequestLayoutConverter._check_input(self)
        self._check_input_class('"is ISO request layout" flag',
                                self.__is_iso_request_layout, bool)
        self._check_input_class('"is mastermix template" flag',
                                self.__is_mastermix_template, bool)
        if not self.has_errors() and \
                self.__is_mastermix_template and self.__is_iso_request_layout:
            msg = 'The layout cannot be a mastermix layout and an ISO ' \
                  'request layout at the same time!'
            self.add_error(msg)

    def _initialize_parameter_validators(self):
        """
        Initializes all parameter validators for the tools
        :attr:`PARAMETER_SET`. Overwrite this method if you want to have
        other validators.
        """
        self._optional_parameters = set([self.PARAMETER_SET.OPTIMEM_DIL_FACTOR])

        params = [self.PARAMETER_SET.MOLECULE_DESIGN_POOL,
                  self.PARAMETER_SET.REAGENT_NAME,
                  self.PARAMETER_SET.REAGENT_DIL_FACTOR,
                  self.PARAMETER_SET.POS_TYPE,
                  self.PARAMETER_SET.FINAL_CONCENTRATION,
                  self.PARAMETER_SET.ISO_VOLUME,
                  self.PARAMETER_SET.ISO_CONCENTRATION,
                  self.PARAMETER_SET.OPTIMEM_DIL_FACTOR]

        if self.__is_iso_request_layout:
            self._optional_parameters.add(
                                        self.PARAMETER_SET.FINAL_CONCENTRATION)
        else:
            self._expect_iso_values = False
            self._optional_parameters.add(self.PARAMETER_SET.POS_TYPE)
            self._optional_parameters.add(self.PARAMETER_SET.ISO_VOLUME)
            self._optional_parameters.add(self.PARAMETER_SET.ISO_CONCENTRATION)

        if not self.__is_mastermix_template:
            self._optional_parameters.add(self.PARAMETER_SET.REAGENT_NAME)
            self._optional_parameters.add(
                                        self.PARAMETER_SET.REAGENT_DIL_FACTOR)

        self._parameter_validators = dict()
        for parameter in params:
            validator = self.PARAMETER_SET.create_validator_from_parameter(
                                                                    parameter)
            self._parameter_validators[parameter] = validator

    def _get_position_init_values(self, parameter_map, rack_pos):
        kw = IsoRequestLayoutConverter._get_position_init_values(self,
                                              parameter_map, rack_pos)
        if kw is None: return None # includes empty and untreated type pos

        pos_type = kw['position_type']
        pos_label = rack_pos.label
        reagent_name = parameter_map[self.PARAMETER_SET.REAGENT_NAME]
        reagent_df = parameter_map[self.PARAMETER_SET.REAGENT_DIL_FACTOR]
        final_conc = parameter_map[self.PARAMETER_SET.FINAL_CONCENTRATION]
        optimem_dil_factor = None

        invalid = False

        optimem_dil_factor = parameter_map[
                                        self.PARAMETER_SET.OPTIMEM_DIL_FACTOR]
        if optimem_dil_factor is not None and \
                                not is_valid_number(optimem_dil_factor):
            info = '%s (%s)' % (pos_label, optimem_dil_factor)
            self.__invalid_optimem_factor.append(info)
            invalid = True

        if reagent_name is None:
            if self.__is_mastermix_template:
                self.__missing_reagent_name.append(pos_label)
                invalid = True
        elif not isinstance(reagent_name, basestring) \
                            or len(reagent_name) < 2:
            self.__invalid_name.append(pos_label)
            invalid = True

        if reagent_df is None:
            if self.__is_mastermix_template:
                self.__missing_reagent_df.append(pos_label)
                invalid = True
        elif not is_valid_number(reagent_df):
            self.__invalid_dil_factor.append(pos_label)
            invalid = True

        if not self.__is_iso_request_layout and final_conc is None and \
                        not pos_type == IsoRequestParameters.MOCK_TYPE_VALUE:
            self.__missing_final_conc.append(pos_label)
            invalid = True

        if not final_conc is None:
            if pos_type == MOCK_POSITION_TYPE:
                if not TransfectionPosition.is_valid_mock_value(final_conc,
                            self.PARAMETER_SET.FINAL_CONCENTRATION):
                    info = '%s (%s)' % (pos_label, final_conc)
                    self.__invalid_final_concentration.append(info)
                    invalid = True
            elif not is_valid_number(final_conc):
                info = '%s (%s)' % (pos_label, final_conc)
                self.__invalid_final_concentration.append(info)
                invalid = True

        if invalid:
            return None
        else:
            kw['reagent_name'] = reagent_name
            kw['reagent_dil_factor'] = reagent_df
            kw['final_concentration'] = final_conc
            kw['optimem_dil_factor'] = optimem_dil_factor
            return kw

    def _record_errors(self):
        """
        Records errors that habe been collected for rack positions.
        """
        IsoRequestLayoutConverter._record_errors(self)

        if len(self.__invalid_name) > 0:
            msg = 'The following rack positions have invalid reagent names: ' \
                  '%s. A valid reagent name must be a string of at least 2 ' \
                  'characters length.' \
                   % (self._get_joined_str(self.__invalid_name))
            self.add_error(msg)

        if len(self.__invalid_dil_factor) > 0:
            msg = 'The following rack positions have invalid reagent ' \
                  'dilution factors: %s. The reagent dilution factor must be ' \
                  'a positive number.' \
                   % (self._get_joined_str(self.__invalid_dil_factor))
            self.add_error(msg)

        if len(self.__invalid_final_concentration) > 0:
            msg = 'The following rack positions have invalid final ' \
                  'concentrations: %s. The final concentration must be ' \
                  'a positive number.' \
                  % (self._get_joined_str(self.__invalid_final_concentration))
            self.add_error(msg)

        if len(self.__invalid_optimem_factor) > 0:
            msg = 'The following rack positions have invalid OptiMem ' \
                  'dilution factors: %s. The OptiMem dilution factor must be ' \
                  'a positive number.' \
                   % (self._get_joined_str(self.__invalid_optimem_factor))
            self.add_error(msg)

        if len(self.__missing_reagent_name) > 0:
            msg = 'The following rack positions do not have a reagent name: %s.' \
                  % (self._get_joined_str(self.__missing_reagent_name))
            self.add_error(msg)

        if len(self.__missing_reagent_df) > 0:
            msg = 'The following rack positions do not have a reagent ' \
                  'dilution factor: %s.' \
                  % (self._get_joined_str(self.__missing_reagent_df))
            self.add_error(msg)

        if len(self.__missing_final_conc) > 0:
            msg = 'The following rack positions do not have a final ' \
                  'concentration: %s.' \
                   % (self._get_joined_str(self.__missing_final_conc))
            self.add_error(msg)

    def _perform_layout_validity_checks(self, working_layout):
        """
        Use this method to check the validity of the generated layout.
        """
        IsoRequestLayoutConverter._perform_layout_validity_checks(self,
                                                        working_layout)
        self.__check_optimem_factor(working_layout)

    def __check_optimem_factor(self, working_layout):
        """
        If there is an OptiMem dilution factor defined for one position, it
        must be defined for all non-empty positions.
        """
        optimem_factors = set()
        for tf_pos in working_layout.working_positions():
            if tf_pos.is_empty: continue
            optimem_factors.add(tf_pos.optimem_dil_factor)
        if len(optimem_factors) > 1 and None in optimem_factors:
            msg = 'Some positions do not have an OptiMem dilution factor ' \
                  'although there are OptiMem dilution factors in this layout!'
            self.add_error(msg)


class TransfectionSectorAssociator(IsoRequestSectorAssociator):
    """
    This is a special rack sector determiner. It sorts the transfection
    positions by final concentration.
    It is assumed that the sorting of floating positions has not taken place
    yet. Hence, pools for floating positions are replaced by the an
    unspecific marker.

    **Return Value:** A map containing the values for the different sectors.
    """

    NAME = 'Transfection Rack Sector Associator'

    SECTOR_ATTR_NAME = 'final_concentration'
    LAYOUT_CLS = TransfectionLayout

    def _get_molecule_design_pool_id(self, layout_pos):
        """
        Floating pool placeholdes are replaced by an unspecific marker.
        """
        if not layout_pos is None and layout_pos.is_floating:
            return TransfectionParameters.FLOATING_TYPE_VALUE
        else:
            return IsoRequestSectorAssociator._get_molecule_design_pool_id(self,
                                                                     layout_pos)

    def _check_associated_sectors(self):
        """
        Since all floating positions are regarded as the same pool, the default
        sector association will not work if we do have controls to distinguish
        sectors.
        """
        if not self.regard_controls and self.number_sectors > 1:
            self.__find_floating_only_associations()
        else:
            IsoRequestSectorAssociator._check_associated_sectors(self)

    def __find_floating_only_associations(self):
        """
        Since all floating are treated in the same way we exclude the
        possibility of equal concentrations in a rack sectors if controls
        are not regarded as in this case we have 2 ways to interpreted
        findings (remember that the floating placeholder have not been
        assigned yet).

        Example: 4 floatings with the same contration can either be regarded
        as 4 independent pools or as 1 pool in 4-fold replicate. As the first
        case is more likely in our company we choose the this case for
        interpretation. If scientists want a different interpretation
        we have to adjust this manually.
        """
        concentrations = dict()
        present_sectors = []
        for sector_index, conc in self._sector_concentrations.iteritems():
            if conc is not None:
                add_list_map_element(concentrations, conc, sector_index)
                present_sectors.append(sector_index)
        if len(self._associated_sectors) > 1:
            msg = 'Unable to adjust floating position association ' \
                  'because basic assumptions are not met. This is ' \
                  'a programming error. Talk to IT, please.'
            raise AssertionError(msg)

        if len(present_sectors) > 1:
            current_sets = []
            if len(concentrations) == 1:
                for sector_index in present_sectors:
                    current_sets.append([sector_index])
            elif len(concentrations) > 1:
                while len(concentrations) > 0:
                    current_set = []
                    del_conc = []
                    for conc, sectors in concentrations.iteritems():
                        sectors.sort()
                        si = sectors.pop(0)
                        current_set.append(si)
                        if len(sectors) < 1: del_conc.append(conc)
                    current_sets.append(current_set)
                    for conc in del_conc: del concentrations[conc]
        else:
            current_sets = [[present_sectors[0]]]

        if self._are_valid_sets(current_sets):
            self._associated_sectors = current_sets


class TransfectionAssociationData(IsoRequestAssociationData):
    """
    A helper class determining and storing associated rack sectors, parent
    sectors and sector concentrations (ISO and final) for an transfection
    layout.

    :Note: All attributes are immutable.
    """
    ASSOCIATOR_CLS = TransfectionSectorAssociator

    def __init__(self, layout, regard_controls, log):
        """
        Constructor:

        :param layout: The ISO request layout whose sectors to associate.
        :type layout: :class:`IsoRequestLayout`

        :param regard_controls: Shall controls positions be regarded (*True*)
            or be ignored (*False* - floating positions are always regarded)?
        :type regard_controls: :class:`bool`

        :param log: The log to write into (not stored in the object).
        :type log: :class:`thelma.ThelmaLog`
        """
        IsoRequestAssociationData.__init__(self, log=log, layout=layout,
                                regard_controls=regard_controls)

        self.__iso_concentrations = None
        self.__find_iso_concentrations(layout, log, regard_controls)

    @property
    def iso_concentrations(self):
        """
        The ISO concentrations for the different rack sectors.
        """
        return self.__iso_concentrations

    def __find_iso_concentrations(self, transfection_layout, log,
                                  regard_controls):
        """
        Finds the ISO concentration for each rack sector.
        """
        determiner = IsoRequestValueDeterminer(log=log,
                                    iso_request_layout=transfection_layout,
                                    attribute_name='iso_concentration',
                                    number_sectors=self.number_sectors,
                                    regard_controls=regard_controls)
        self.__iso_concentrations = determiner.get_result()

        if self.__iso_concentrations is None:
            msg = ', '.join(determiner.get_messages())
            raise ValueError(msg)
        else:
            self._remove_none_sectors(self.__iso_concentrations)

