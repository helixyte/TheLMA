"""
Utility classes related to transfection worklist generation
(robot worklist generations).

AAB, Sept 2011
"""
from thelma.automation.tools.semiconstants \
    import get_reservoir_specs_standard_96
from thelma.automation.tools.semiconstants import get_positions_for_shape
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.utils.base import EMPTY_POSITION_TYPE
from thelma.automation.tools.utils.base import MOCK_POSITION_TYPE
from thelma.automation.tools.utils.base import UNTREATED_POSITION_TYPE
from thelma.automation.tools.utils.base import get_converted_number
from thelma.automation.tools.utils.base import get_trimmed_string
from thelma.automation.tools.utils.base import is_valid_number
from thelma.automation.tools.utils.base import round_up
from thelma.automation.tools.utils.iso import IsoAssociationData
from thelma.automation.tools.utils.iso import IsoLayout
from thelma.automation.tools.utils.iso import IsoLayoutConverter
from thelma.automation.tools.utils.iso import IsoParameters
from thelma.automation.tools.utils.iso import IsoPosition
from thelma.automation.tools.utils.iso import IsoRackSectorAssociator
from thelma.automation.tools.utils.iso import IsoValueDeterminer
from thelma.automation.tools.worklists.base import MIN_BIOMEK_TRANSFER_VOLUME
from thelma.automation.tools.worklists.base import MIN_CYBIO_TRANSFER_VOLUME
from thelma.automation.tools.worklists.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.worklists.base import get_biomek_dead_volume
from thelma.models.moleculetype import MOLECULE_TYPE_IDS
from thelma.models.moleculetype import MoleculeType
from thelma.models.rack import RackPosition
from thelma.models.racklayout import RackLayout
from thelma.models.tagging import Tag
from thelma.models.tagging import TaggedRackPositionSet
import copy

__docformat__ = "reStructuredText en"

__all__ = ['TransfectionParameters',
           'TransfectionPosition',
           'TransfectionLayout',
           'TransfectionLayoutConverter',
           'TransfectionRackSectorAssociator',
           'TransfectionAssociationData']


class TransfectionParameters(IsoParameters):
    """
    This a list of parameters required to generate a BioMek transfection
    worklist when translating an ISO plate into a cell plate.
    """

    #: The domain for transfer-related tags.
    DOMAIN = 'transfection'

    #: The final RNAi concentration in the assay.
    FINAL_CONCENTRATION = 'final_concentration'
    #: The molecule design pool (tag value: molecule design pool id).
    MOLECULE_DESIGN_POOL = IsoParameters.MOLECULE_DESIGN_POOL
    #: The volume requested in the ISO in ul.
    ISO_VOLUME = IsoParameters.ISO_VOLUME
    #: The concentration requested in the ISO in nM.
    ISO_CONCENTRATION = IsoParameters.ISO_CONCENTRATION
    #: The position type (fixed, floating or empty).
    POS_TYPE = IsoParameters.POS_TYPE
    #: The supplier for the molecule design pool (tag value: organization name).
    SUPPLIER = IsoParameters.SUPPLIER
    #: The name of the RNAi reagent.
    REAGENT_NAME = 'reagent_name'
    #: The final dilution factor of the RNAi reagent in the cell plate.
    REAGENT_DIL_FACTOR = 'reagent_dilution_factor'
    #: The OptiMem dilution factor usually depends on the molecule type.
    #: In library screenings however the factor is variable depending on the
    #: final concentration.
    OPTIMEM_DIL_FACTOR = 'optimem_dilution_factor'

    #: A list of the attributes/parameters that need to be set.
    REQUIRED = [MOLECULE_DESIGN_POOL]
    #: A list of all available attributes/parameters.
    ALL = [FINAL_CONCENTRATION, MOLECULE_DESIGN_POOL, ISO_VOLUME,
           ISO_CONCENTRATION, POS_TYPE, SUPPLIER, REAGENT_NAME,
           REAGENT_DIL_FACTOR, OPTIMEM_DIL_FACTOR]

    #: A map storing alias predicates for each parameter.
    ALIAS_MAP = {FINAL_CONCENTRATION : [],
                 MOLECULE_DESIGN_POOL :
                                  IsoParameters.ALIAS_MAP[MOLECULE_DESIGN_POOL],
                 ISO_VOLUME : IsoParameters.ALIAS_MAP[ISO_VOLUME],
                 ISO_CONCENTRATION : IsoParameters.ALIAS_MAP[ISO_CONCENTRATION],
                 SUPPLIER : IsoParameters.ALIAS_MAP[SUPPLIER],
                 POS_TYPE : IsoParameters.ALIAS_MAP[POS_TYPE],
                 REAGENT_NAME : [],
                 REAGENT_DIL_FACTOR : ['reagent_concentration'],
                 OPTIMEM_DIL_FACTOR : []}

    #: Maps tag predicates on domains.
    DOMAIN_MAP = {FINAL_CONCENTRATION : DOMAIN,
                  MOLECULE_DESIGN_POOL : IsoParameters.DOMAIN,
                  ISO_VOLUME : IsoParameters.DOMAIN,
                  ISO_CONCENTRATION : IsoParameters.DOMAIN,
                  POS_TYPE : IsoParameters.DOMAIN,
                  SUPPLIER : IsoParameters.DOMAIN,
                  REAGENT_NAME : DOMAIN,
                  REAGENT_DIL_FACTOR : DOMAIN,
                  OPTIMEM_DIL_FACTOR : DOMAIN}

    # Constants for calculations

    #: The volume transferred into each cell (experiment) plate well (in ul).
    TRANSFER_VOLUME = 5

    #: The minimum volume that can be requested by the stockmanagement.
    MINIMUM_ISO_VOLUME = IsoParameters.MINIMUM_ISO_VOLUME

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

    @classmethod
    def calculate_iso_volume(cls, number_target_wells, number_replicates,
                             iso_reservoir_spec, optimem_dil_factor,
                             use_cybio=False):
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

        :param use_cybio: Defines whether to use a static dead volume (*True*)
            or a dynamic (represents Biomek-transfer, *False*).
        :type use_cybio: :class:`bool`
        :default use_cybio: *False*
        """
        required_volume = cls.calculate_mastermix_volume(number_target_wells,
                                                        number_replicates,
                                                        iso_reservoir_spec,
                                                        use_cybio)
        iso_volume = required_volume / (cls.REAGENT_MM_DILUTION_FACTOR \
                                        * optimem_dil_factor)

        if use_cybio:
            min_volume = MIN_CYBIO_TRANSFER_VOLUME
        else:
            min_volume = MIN_BIOMEK_TRANSFER_VOLUME

        if iso_volume < min_volume: iso_volume = min_volume
        return round_up(iso_volume)

    @classmethod
    def get_optimem_dilution_factor(cls, molecule_type):
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
    def requires_deepwell(cls, number_target_wells, number_replicates):
        """
        Determines the reservoir specs for an ISO plate
        (depending on the maximum volume of a mastermix).

        :param number_target_wells: The number of target wells in all
            design racks fo an experiment design.
        :type number_target_wells: :class:`int`
        :param number_replicates: The number of replicates.
        :type number_replicates: :class:`int`
        :return: :class:`bool` (*True* for deep well, *False* for standard).
        """
        rs = get_reservoir_specs_standard_96()
        req_volume = cls.calculate_mastermix_volume(
                        number_target_wells=number_target_wells,
                        number_replicates=number_replicates,
                        iso_reservoir_spec=rs)

        max_volume = rs.max_volume * VOLUME_CONVERSION_FACTOR
        return req_volume > max_volume

    @classmethod
    def calculate_mastermix_volume(cls, number_target_wells,
                                        number_replicates,
                                        iso_reservoir_spec,
                                        use_cybio=False):
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

        :param use_cybio: Defines whether to use a static dead volume (*True*)
            or a dynamic (represents Biomek-transfer, *False*).
        :type use_cybio: :class:`bool`
        :default use_cybio: *False*

        :return: The determined volume required to fill these wells.
        """
        well_number = number_target_wells * number_replicates

        if use_cybio:
            dead_volume = iso_reservoir_spec.min_dead_volume \
                          * VOLUME_CONVERSION_FACTOR
        else:
            dead_volume = get_biomek_dead_volume(target_well_number=well_number,
                                            reservoir_specs=iso_reservoir_spec)

        required_volume = well_number * cls.TRANSFER_VOLUME + dead_volume
        return required_volume

    @classmethod
    def calculate_complete_volume(cls, iso_volume, optimem_dil_factor):
        """
        Retuns the maximum volume of a mastermix (the volume of the complete
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

        crit_iso_conc = stock_concentration \
                    / ((std_96_min_dead_vol + cls.MINIMUM_ISO_VOLUME) \
                    / (std_96_min_dead_vol + cls.MINIMUM_ISO_VOLUME \
                       - MIN_BIOMEK_TRANSFER_VOLUME))

        return crit_iso_conc

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
            optimem_df = cls.get_optimem_dilution_factor(mock_mt)
            return optimem_df


class TransfectionPosition(IsoPosition):
    """
    This class represents a source position in an ISO layout. The target
    positions are the target in the final cell (experiment) plate.
    """

    #: The parameter set this working position is associated with.
    PARAMETER_SET = TransfectionParameters

    #: The delimiter for the different target infos.
    POSITION_DELIMITER = '-'

    def __init__(self, rack_position, molecule_design_pool=None,
                 reagent_name=None, reagent_dil_factor=None, iso_volume=None,
                 iso_concentration=None, supplier=None,
                 final_concentration=None):
        """
        :param rack_position: The rack position.
        :type rack_position: :class:`thelma.models.rack.RackPosition`.

        :param molecule_design_pool: The molecule design pool or placeholder for
            the RNAi reagent.
        :type molecule_design_pool: :class`int` (ID), :class:`str` (placeholder)
            or :class:`thelma.models.moleculedesign.StockSampleMoleculeDesign`

        :param reagent_name: The name of the transfection reagent.
        :type reagent_name: :class:`str`

        :param reagent_dil_factor: The final dilution factor of the
            transfection reagent in the cell plate.
        :type reagent_dil_factor: positive number

        :param iso_volume: The volume requested by the stock management.
        :type iso_volume: positive number

        :param iso_concentration: The concentration requested by the stock
            management.
        :type iso_concentration: positive number

        :param supplier: The supplier for the molecule design pool (fixed
            positions only).
        :type supplier: :class:`thelma.models.organization.Organization`

        :param final_concentration: The final concentration of the RNAi
            reagent in the cell plate.
        :type final_concentration: positive number
        """
        IsoPosition.__init__(self, rack_position=rack_position,
                             molecule_design_pool=molecule_design_pool,
                             iso_volume=iso_volume,
                             iso_concentration=iso_concentration,
                             supplier=supplier)

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
        self._optimem_dil_factor = None

        tf_attrs = [('reagent name', self.reagent_name),
                    ('reagent dilution factor', self.reagent_dil_factor),
                    ('final concentration', self.final_concentration)]
        if self.is_untreated:
            self._check_untreated_values(tf_attrs)
        elif self.is_empty:
            self._check_none_value(tf_attrs)
        else:
            if self.reagent_name is not None and len(self.reagent_name) < 2:
                msg = 'The reagent name must be at least 2 characters long ' \
                      'if there is one (obtained: %s)!' % (self.reagent_name)
                raise ValueError(msg)
            numericals = [tf_attrs[1]]
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

    def add_cell_plate_position(self, rack_position):
        """
        Adds a target cell plate (experiment plate) position.

        :param rack_position: The rack position to add.
        :type: :class:`thelma.models.rack.RackPosition`

        :raises AttributeError: If the transfection positis in an empty
            or untreated one
        :raises ValueError: If the position is already present.
        :raises TypeError: If the rack position has the wrong type.
        """
        if self.is_empty:
            msg = 'Adding a target cell plate position to an empty or ' \
                  'untreated position is not allowed!'
            raise AttributeError(msg)
        elif not isinstance(rack_position, RackPosition):
            msg = 'The rack position must be a %s object (obtained: %s).' \
                  % (RackPosition.__class__.__name__,
                     rack_position.__class__.__name__)
            raise TypeError(msg)
        elif rack_position in self.cell_plate_positions:
            msg = 'Duplicate cell plate position: %s' % (rack_position.label)
            raise ValueError(msg)

        self.cell_plate_positions.add(rack_position)

    @classmethod
    def parse_cell_plate_position_tag_value(cls, tag_value):
        """
        Converts the tag value of a cell position tag into a set of rack
        positions.

        :param tag_value: The value to be parsed.
        :type tag_value: :class:`basestring`
        :return: :class:`set` of :class:`RackPosition` objects
        """
        labels = tag_value.split(cls.POSITION_DELIMITER)
        rack_positions = set()
        for label in labels:
            rack_position = get_rack_position_from_label(label)
            rack_positions.add(rack_position)
        return rack_positions

    def get_tag_set(self):
        """
        Returns the tag set for this working position.
        """
        if self.is_empty and not self.is_untreated:
            return set([self.get_parameter_tag(self.PARAMETER_SET.POS_TYPE)])

        tag_set = set()
        for parameter in self.PARAMETER_SET.REQUIRED:
            tag = self.get_parameter_tag(parameter)
            tag_set.add(tag)
        tag_set.add(self.get_parameter_tag(self.PARAMETER_SET.POS_TYPE))

        optional_parameters = [self.PARAMETER_SET.FINAL_CONCENTRATION,
                               self.PARAMETER_SET.SUPPLIER,
                               self.PARAMETER_SET.ISO_VOLUME,
                               self.PARAMETER_SET.ISO_CONCENTRATION,
                               self.PARAMETER_SET.REAGENT_NAME,
                               self.PARAMETER_SET.REAGENT_DIL_FACTOR,
                               self.PARAMETER_SET.OPTIMEM_DIL_FACTOR]
        for parameter in optional_parameters:
            if not self.get_parameter_value(parameter) is None:
                tag = self.get_parameter_tag(parameter)
                tag_set.add(tag)

        return tag_set

    def has_tag(self, tag):
        """
        Checks whether a working position complies to a given tag.

        :param tag: The tag to be compared.
        :type tag: :class:`thelma.models.tagging.Tag`

        :return: :class:`boolean`
        """
        tag_set = self.get_tag_set()
        return tag in tag_set

    def get_parameter_tag(self, parameter):
        """
        Returns the value for the requested parameter.

        :param parameter: A parameter from the :attr:`ParameterSet` associated
            to this working position type.
        :type parameter: :class:`string`
        :return: the attribute mapped onto that parameter
        """
        if not parameter in self.PARAMETER_SET.ALL: return None

        domain = self.PARAMETER_SET.DOMAIN_MAP[parameter]
        value = self.get_parameter_value(parameter)
        value = get_trimmed_string(value)
        return Tag(domain, parameter, value)

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
            get_optimem_dilution_factor(self.molecule_design_pool.molecule_type)

    def set_optimem_dilution_factor(self, optimem_df):
        """
        The OptiMem dilution factor must be a positive number.

        :raises AttributeError: If the factor has been set before.
        :raises ValueError: If the factor is not a positive number.
        """
        if not is_valid_number(optimem_df):
            msg = 'The OptiMem dilution factor must be a positive number ' \
                  '(obtained: %s).' % (optimem_df)
            raise ValueError(msg)
        if not self._optimem_dil_factor is None:
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

    def supports_mastermix_preparation(self):
        """
        Checks whether the concentrations of the position support
        mastermix preparation. For floating position you have to pass a
        molecule type.
        """
        if self.is_mock or self.is_empty: return True
        if self.final_concentration is None: return None
        if self.iso_concentration is None: return None

        total_df = self.get_total_dilution_factor()
        expected_ic = self.final_concentration * total_df
        if expected_ic == self.iso_concentration:
            return True
        else:
            return False

    def calculate_reagent_dilution_volume(self):
        """
        Returns the reagent volume that has be added to this well.
        Make sure, the OptiMem dilution factor of the postion is set.
        """
        if self.is_empty or self.iso_volume is None: return None

        return TransfectionParameters.calculate_reagent_dilution_volume(
                                self.iso_volume, self.optimem_dil_factor)

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
        parameters[self.PARAMETER_SET.SUPPLIER] = self.supplier
        parameters[self.PARAMETER_SET.REAGENT_NAME] = self.reagent_name
        parameters[self.PARAMETER_SET.REAGENT_DIL_FACTOR] = \
                                        self.reagent_dil_factor
        parameters[self.PARAMETER_SET.FINAL_CONCENTRATION] = \
                                        self.final_concentration
        parameters[self.PARAMETER_SET.OPTIMEM_DIL_FACTOR] = \
                                        self._optimem_dil_factor
        return parameters

    # different number arguments #pylint: disable=W0221
    @classmethod
    def create_mock_position(cls, rack_position, iso_volume=None,
                     reagent_name=None, reagent_dil_factor=None,
                     final_concentration=IsoPosition.NONE_REPLACER):
        """
        Creates a transfection position representing a mock well.

        :return: A transfection position.
        """
        return TransfectionPosition(rack_position=rack_position,
                        molecule_design_pool=cls.PARAMETER_SET.MOCK_TYPE_VALUE,
                        reagent_name=reagent_name,
                        reagent_dil_factor=reagent_dil_factor,
                        iso_volume=iso_volume,
                        final_concentration=final_concentration)
    #pylint: enable=W0221

    # different number arguments #pylint: disable=W0221
    @classmethod
    def create_untreated_position(cls, rack_position,
                        reagent_name=IsoPosition.NONE_REPLACER,
                        reagent_dil_factor=IsoPosition.NONE_REPLACER,
                        final_concentration=IsoPosition.NONE_REPLACER):
        """
        Creates a transfection position representing an untreated (empty) well.

        :return: A transfection position.
        """
        return TransfectionPosition(rack_position=rack_position,
                        molecule_design_pool=UNTREATED_POSITION_TYPE,
                        reagent_name=reagent_name,
                        reagent_dil_factor=reagent_dil_factor,
                        final_concentration=final_concentration)
        #pylint: enable=W0221

    def copy(self):
        """
        Returns a copy of this transfection position.
        """
        return copy.deepcopy(self)

    def __eq__(self, other):
        if not isinstance(other, TransfectionPosition): return False
        if not self.molecule_design_pool_id == other.molecule_design_pool_id:
            return False
        if not self.is_empty:
            if not self.reagent_name == other.reagent_name:
                return False
            if not self.reagent_dil_factor == other.reagent_dil_factor:
                return False
        if not (self.is_mock or self.is_empty):
            if not self.final_concentration == other.final_concentration:
                return False
            if not self.iso_concentration == other.iso_concentration:
                return False
        return self.iso_volume == other.iso_volume


    def __repr__(self):
        str_format = '<%s rack position: %s, molecule design pool: %s ' \
                     'ISO volume: %s, ISO concentration: %s, reagent name %s, ' \
                     'reagent dilution factor: %s>'
        params = (self.__class__.__name__, self.rack_position,
                  self.molecule_design_pool, self.iso_volume,
                  self.iso_concentration, self.reagent_name,
                  self.reagent_dil_factor)
        return str_format % params


class TransfectionLayout(IsoLayout):
    """
    A working container for transfection positions. Transfection positions
    contain data about the ISO, the mastermix and transfer parameters.
    """

    WORKING_POSITION_CLASS = TransfectionPosition

    def get_ambiguous_wells(self):
        """
        Returns a list of tuples containing wells with duplicate identification
        quartets.

        :return: A list of duplicate well tuples (wells specified as
            transfection positions (:class:`TransfectionPosition`)).
        """
        duplicate_wells = []
        quartets = dict()
        for transfection_pos in self._position_map.values():
            if transfection_pos.is_empty: continue
            hash_value = transfection_pos.hash_full
            if hash_value in quartets:
                tup = (quartets[hash_value].rack_position.label,
                        transfection_pos.rack_position.label)
                duplicate_wells.append(tup)
            quartets[hash_value] = transfection_pos
        return duplicate_wells

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

    def get_iso_layout(self):
        """
        Returns the ISO layout for this transfection layout.

        :rtype: :class:`thelma.automation.tools.utils.iso.IsoLayout`
        """
        iso_layout = IsoLayout(shape=self.shape)
        for rack_pos, tf_pos in self._position_map.iteritems():
            iso_pos = IsoPosition(rack_position=rack_pos,
                            molecule_design_pool=tf_pos.molecule_design_pool,
                            iso_concentration=tf_pos.iso_concentration,
                            iso_volume=tf_pos.iso_volume)
            iso_layout.add_position(iso_pos)

        if self._floating_stock_concentration is not None:
            iso_layout.set_floating_stock_concentration(
                                            self._floating_stock_concentration)
        return iso_layout

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
                                                 iso_rack_layout, user):
        """
        Returns a list of tagged rack position set wit the molecule design set,
        transfection reagent data and final concentration tags of the layout
        added to it.

        :param exp_rack_layout: The rack layout to complete.
        :type exp_rack_layout: :class:`thelma.models.racklayout.RackLayout`

        :param iso_rack_layout: The rack layout of the ISO request
            (which might contain customized tags).
        :type iso_rack_layout: :class:`thelma.models.racklayout.RackLayout`
        """

        trps_map = dict()

        for trps in exp_rack_layout.tagged_rack_position_sets:
            hash_value = trps.rack_position_set.hash_value
            trps_map[hash_value] = trps

        for trps in iso_rack_layout.tagged_rack_position_sets:
            hash_value = trps.rack_position_set
            tags = []
            for tag in trps.tags:
                if tag.predicate in \
                    cls.WORKING_POSITION_CLASS.PARAMETER_SET.ALL: continue
                tags.append(tag)
            if trps_map.has_key(hash_value):
                trps = trps_map[hash_value]
                for tag in tags:
                    trps.add_tag(tag, user)
            else:
                trps = TaggedRackPositionSet(set(tags), trps.rack_position_set,
                                             user)
                trps_map[hash_value] = trps

        return RackLayout(shape=exp_rack_layout.shape,
                          tagged_rack_position_sets=trps_map.values())

#        # Get tags for existing layout
#        rps_map = dict()
#        tag_map = dict()
#
#        for trps in exp_rack_layout.tagged_rack_position_sets:
#            rps = trps.rack_position_set
#            hash_value = rps.hash_value
#            if not rps_map.has_key(hash_value):
#                rps_map[hash_value] = rps
#                tag_map[hash_value] = set()
#            for tag in trps.tags:
#                tag_map[hash_value].add(tag)
#
#        # Get customized tags in ISO layout.
#        for trps in iso_rack_layout.tagged_rack_position_sets:
#            rps = trps.rack_position_set
#            hash_value = rps.hash_value
#            for tag in trps.tags:
#                if tag.predicate in TransfectionParameters.ALL: continue
#                if not rps_map.has_key(hash_value):
#                    rps_map[hash_value] = rps
#                    tag_map[hash_value] = set()
#                tag_map[hash_value].add(tag)
#
#        # Get position sets for transfection layout
#        screen_map = dict()
#        for rack_position, tf_pos in self._position_map.iteritems():
#            pool_tag = tf_pos.get_parameter_tag(
#                                    IsoParameters.MOLECULE_DESIGN_POOL)
#            fc_tag = tf_pos.get_parameter_tag(
#                                    TransfectionParameters.FINAL_CONCENTRATION)
#            name_tag = tf_pos.get_parameter_tag(
#                                        TransfectionParameters.REAGENT_NAME)
#            df_tag = tf_pos.get_parameter_tag(
#                                    TransfectionParameters.REAGENT_DIL_FACTOR)
#            tags = [pool_tag, fc_tag, name_tag, df_tag]
#            for tag in tags:
#                if not screen_map.has_key(tag): screen_map[tag] = set()
#                screen_map[tag].add(rack_position)
#
#        # Merge rack position sets
#        for tag, pos_set in screen_map.iteritems():
#            rps = RackPositionSet.from_positions(positions=pos_set)
#            hash_value = rps.hash_value
#            if not rps_map.has_key(hash_value):
#                rps_map[hash_value] = rps
#                tag_map[hash_value] = set()
#            tag_map[hash_value].add(tag)
#
#        # Create rack layout
#        tagged_rack_position_sets = []
#        for hash_value in rps_map.keys():
#            rack_pos_set = rps_map[hash_value]
#            tags = tag_map[hash_value]
#            trps = TaggedRackPositionSet(tags=tags,
#                                         rack_position_set=rack_pos_set,
#                                         user=self._user)
#            tagged_rack_position_sets.append(trps)
#
#        rack_layout = RackLayout(shape=exp_rack_layout.shape,
#                        tagged_rack_position_sets=tagged_rack_position_sets)
#
#        return rack_layout

    @staticmethod
    def compare_ignoring_untreated(layout1, layout2):
        """
        Compares two transfection layouts ignoring potential untreated
        positions.
        """
        if layout1.shape != layout2.shape: return False

        for rack_pos in get_positions_for_shape(layout1.shape):
            tf1 = layout1.get_working_position(rack_pos)
            tf2 = layout2.get_working_position(rack_pos)
            if tf1 is None and tf2 is None: continue
            if tf1 is not None and (tf1.is_untreated or tf1.is_empty):
                tf1 = None
            if tf2 is not None and (tf2.is_untreated or tf2.is_empty):
                tf2 = None
            if tf1 is None and tf2 is None:
                continue
            elif not tf1 == tf2:
                return False

        return True


class TransfectionLayoutConverter(IsoLayoutConverter):
    """
    Converts a rack layout into a IdQuartetLayout. These layouts types are
    only used to ensure layout uniqueness.
    """
    NAME = 'Transfection Layout Converter'

    PARAMETER_SET = TransfectionParameters
    WORKING_LAYOUT_CLASS = TransfectionLayout


    def __init__(self, rack_layout, log, is_iso_layout=True,
                 is_mastermix_template=False, check_well_uniqueness=None):
        """
        Constructor:

        :param rack_layout: The rack layout containing the ISO data.
        :type rack_layout: :class:`thelma.models.racklayout.RackLayout`

        :param is_iso_layout: Defines if certain parameters are allowed to be
            missing (final concentration, reaagent name, reagent dil factor).
        :type is_iso_layout: :class:`boolean`
        :default is_iso_layout: True

        :param is_mastermix_template: Defines if certain parameters are allowed
            to be missing (ISO volume, ISO concentration, position type).
            If *True*, \'is_iso_layout\' must be false.
        :type is_mastermix_template: :class:`boolean`
        :default is_mastermix_layout: False

        :param check_well_uniqueness: Shall the uniqueness of the layout
            hash values be checked? Select *True* for optimisation ISO layouts,
            mastermix layout are always *False*.
        :type check_well_uniqueness: :class:`boolean`
        :default check_well_uniqueness: None (False)

        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`
        """
        IsoLayoutConverter.__init__(self, rack_layout=rack_layout, log=log)

        #: Defines if certain parameters are allowed to be missing (final
        #: concentration, reaagent name, reagent dil factor).
        self.__is_iso_layout = is_iso_layout
        #: Defines if certain parameters are allowed to be missing (ISO
        #: volume, ISO concentration, position type).
        self.__is_mastermix_template = is_mastermix_template
        #: Shall the uniqueness of the layout hash values be checked?
        self.__check_well_uniqueness = check_well_uniqueness

        #: The molecule type of the molecule design pools
        #: (:class:`thelma.models.moleculetype.MoleculeType`).
        self.__molecule_type = None

        # intermediate storage of invalid rack positions
        self.__invalid_dil_factor = None
        self.__invalid_name = None
        self.__invalid_final_concentration = None
        self.__invalid_optimem_factor = None
        self.__missing_reagent_name = None
        self.__missing_reagent_conc = None
        self.__missing_final_conc = None
        self.__empty_and_values = None
        self.__untreated_and_values = None

    def reset(self):
        """
        Resets all attributes except for the :attr:`rack_layout`.
        """
        IsoLayoutConverter.reset(self)
        self.__invalid_dil_factor = []
        self.__invalid_name = []
        self.__invalid_final_concentration = []
        self.__invalid_optimem_factor = []
        self.__missing_reagent_name = []
        self.__missing_reagent_conc = []
        self.__missing_final_conc = []
        self.__empty_and_values = []
        self.__untreated_and_values = []

    def _initialize_parameter_validators(self):
        """
        Initializes all parameter validators for the tools
        :attr:`PARAMETER_SET`. Overwrite this method if you want to have
        other validators.
        """
        self.optional_parameters = [self.PARAMETER_SET.SUPPLIER,
                                    self.PARAMETER_SET.OPTIMEM_DIL_FACTOR]

        params = [self.PARAMETER_SET.MOLECULE_DESIGN_POOL,
                  self.PARAMETER_SET.REAGENT_NAME,
                  self.PARAMETER_SET.REAGENT_DIL_FACTOR,
                  self.PARAMETER_SET.SUPPLIER,
                  self.PARAMETER_SET.POS_TYPE,
                  self.PARAMETER_SET.FINAL_CONCENTRATION,
                  self.PARAMETER_SET.ISO_VOLUME,
                  self.PARAMETER_SET.ISO_CONCENTRATION,
                  self.PARAMETER_SET.OPTIMEM_DIL_FACTOR]

        if self.__is_iso_layout:
            self.optional_parameters.append(
                                        self.PARAMETER_SET.FINAL_CONCENTRATION)
        else:
            self.optional_parameters.append(self.PARAMETER_SET.POS_TYPE)
            self.optional_parameters.append(self.PARAMETER_SET.ISO_VOLUME)
            self.optional_parameters.append(
                                        self.PARAMETER_SET.ISO_CONCENTRATION)

        if not self.__is_mastermix_template:
            self.optional_parameters.append(self.PARAMETER_SET.REAGENT_NAME)
            self.optional_parameters.append(
                                        self.PARAMETER_SET.REAGENT_DIL_FACTOR)

        self.parameter_validators = dict()
        for parameter in params:
            validator = self.PARAMETER_SET.create_validator_from_parameter(
                                                                    parameter)
            self.parameter_validators[parameter] = validator

    def _initialize_other_attributes(self):
        """
        There are no other values to be initialized here.
        """
        if self.__is_mastermix_template and self.__is_iso_layout:
            msg = 'The layout cannot be a mastermix layout and an ISO ' \
                  'layout at the same time!'
            self.add_error(msg)

        if self.__is_iso_layout and self.__check_well_uniqueness is None:
            msg = 'In case of ISO layouts you need to specify whether you ' \
                  'want to check the well uniqueness!'
            self.add_error(msg)
        elif self.__is_mastermix_template:
            self.__check_well_uniqueness = False

    def _obtain_working_position(self, parameter_map): #pylint: disable=W0613
        """
        Derives a working position from a parameter map (including validity
        checks).
        """
        self.add_debug('Convert parameter map into mastermix position ...')

        rack_position = parameter_map[self._RACK_POSITION_KEY]
        pos_label = rack_position.label

        md_pool = parameter_map[self.PARAMETER_SET.MOLECULE_DESIGN_POOL]
        reagent_name = parameter_map[self.PARAMETER_SET.REAGENT_NAME]
        reagent_dil_factor = parameter_map[
                                    self.PARAMETER_SET.REAGENT_DIL_FACTOR]
        supplier = parameter_map[self.PARAMETER_SET.SUPPLIER]
        pos_type = parameter_map[self.PARAMETER_SET.POS_TYPE]
        final_conc = parameter_map[self.PARAMETER_SET.FINAL_CONCENTRATION]

        if pos_type is None:
            pos_type = self._determine_position_type(md_pool)
            if pos_type is None: return None

        iso_vol, iso_conc, optimem_dil_factor = None, None, None
        if self.__is_iso_layout:
            iso_conc = parameter_map[self.PARAMETER_SET.ISO_CONCENTRATION]
            iso_vol = parameter_map[self.PARAMETER_SET.ISO_VOLUME]
            optimem_dil_factor = parameter_map[
                                    self.PARAMETER_SET.OPTIMEM_DIL_FACTOR]

        # Empty positions
        empty_values = {'ISO volume' : iso_vol,
                       'ISO concentration' : iso_conc,
                       'final concentration' : final_conc,
                       'reagent name' : reagent_name,
                       'reagent dilution factor' : reagent_dil_factor,
                       'supplier' : supplier,
                       'OptiMem dilution factor' : optimem_dil_factor}
        invalid_values = []
        if pos_type == EMPTY_POSITION_TYPE:
            error_list = self.__empty_and_values
            for value_name, value in empty_values.iteritems():
                if not value is None: invalid_values.append(value_name)
        elif pos_type == UNTREATED_POSITION_TYPE:
            error_list = self.__untreated_and_values
            for value_name, value in empty_values.iteritems():
                if not TransfectionPosition.is_valid_untreated_value(value):
                    invalid_values.append(value_name)
            pos_type = EMPTY_POSITION_TYPE
        if len(invalid_values) > 0:
            info = '%s (%s)' % (pos_label, ', '.join(invalid_values))
            error_list.append(info)
            return None
        if pos_type == EMPTY_POSITION_TYPE: return None

        # Non-empty positions
        invalid = False
        if self.__is_iso_layout:
            is_mock = False
            if md_pool == IsoParameters.MOCK_TYPE_VALUE: is_mock = True
            invalid = self._check_volume_and_concentration(iso_vol, iso_conc,
                                                           pos_label, is_mock)
            if optimem_dil_factor is not None and \
                                    not is_valid_number(optimem_dil_factor):
                info = '%s (%s)' % (rack_position.label, optimem_dil_factor)
                self.__invalid_optimem_factor.append(info)
                invalid = True

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

        if self.__is_mastermix_template and reagent_name is None:
            self.__missing_reagent_name.append(rack_position.label)
            invalid = True
        if not reagent_name is None and \
        (not isinstance(reagent_name, basestring) or len(reagent_name) < 2):
            self.__invalid_name.append(rack_position.label)
            invalid = True

        if self.__is_mastermix_template and reagent_dil_factor is None:
            self.__missing_reagent_conc.append(rack_position.label)
            invalid = True
        if not reagent_dil_factor is None and \
                                    not is_valid_number(reagent_dil_factor):
            self.__invalid_dil_factor.append(rack_position.label)
            invalid = True

        if self.__is_mastermix_template and final_conc is None and \
                                not pos_type == IsoParameters.MOCK_TYPE_VALUE:
            self.__missing_final_conc.append(rack_position.label)
            invalid = True
        if not final_conc is None:
            if pos_type == MOCK_POSITION_TYPE:
                if not TransfectionPosition.is_valid_mock_value(final_conc):
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
            tf_pos = TransfectionPosition(rack_position=rack_position,
                            molecule_design_pool=md_pool,
                            reagent_name=reagent_name,
                            reagent_dil_factor=reagent_dil_factor,
                            iso_concentration=iso_conc,
                            iso_volume=iso_vol,
                            supplier=supplier,
                            final_concentration=final_conc)
            if optimem_dil_factor is not None:
                tf_pos.set_optimem_dilution_factor(optimem_dil_factor)
            return tf_pos

    def _record_additional_position_errors(self):
        """
        Records errors that habe been collected for rack positions.
        """
        IsoLayoutConverter._record_additional_position_errors(self)

        if len(self.__invalid_name) > 0:
            msg = 'The following rack positions have invalid reagent names: ' \
                  '%s. A valid reagent name must be a string of at least 2 ' \
                  'characters length.' \
                   % (', '.join(sorted(self.__invalid_name)))
            self.add_error(msg)

        if len(self.__invalid_dil_factor) > 0:
            msg = 'The following rack positions have invalid reagent ' \
                  'dilution factors: %s. The reagent dilution factor must be ' \
                  'a positive number.' \
                   % (', '.join(sorted(self.__invalid_dil_factor)))
            self.add_error(msg)

        if len(self.__invalid_final_concentration) > 0:
            msg = 'The following rack positions have invalid final ' \
                  'concentrations: %s. The final concentration must be ' \
                  'a positive number.' \
                  % (', '.join(sorted(self.__invalid_final_concentration)))
            self.add_error(msg)

        if len(self.__invalid_optimem_factor) > 0:
            msg = 'The following rack positions have invalid OptiMem ' \
                  'dilution factors: %s. The OptiMem dilution factor must be ' \
                  'a positive number.' \
                   % (', '.join(sorted(self.__invalid_optimem_factor)))
            self.add_error(msg)

        if len(self.__missing_reagent_name) > 0:
            msg = 'The following rack positions do not have a reagent name: %s.' \
                  % (', '.join(sorted(self.__missing_reagent_name)))
            self.add_error(msg)

        if len(self.__missing_reagent_conc) > 0:
            msg = 'The following rack positions do not have a reagent ' \
                  'dilution factor: %s.' \
                  % (', '.join(sorted(self.__missing_reagent_conc)))
            self.add_error(msg)

        if len(self.__missing_final_conc) > 0:
            msg = 'The following rack positions do not have a final ' \
                  'concentration: %s.' \
                   % (', '.join(sorted(self.__missing_final_conc)))
            self.add_error(msg)

        if len(self.__empty_and_values) > 0:
            msg = 'There are parameter specifications for some empty ' \
                  'positions: %s.' \
                   % (', '.join(sorted(self.__empty_and_values)))
            self.add_error(msg)

        if len(self.__untreated_and_values) > 0:
            msg = 'There are invalid parameter specifications for some ' \
                  'untreated positions: %s.' \
                   % (', '.join(sorted(self.__untreated_and_values)))
            self.add_error(msg)

    def _initialize_working_layout(self, shape):
        """
        Initialises the working layout.
        """
        return TransfectionLayout(shape=shape)

    def _perform_layout_validity_checks(self, working_layout):
        """
        Use this method to check the validity of the generated layout.
        """
        working_layout.close()
        if self.__check_well_uniqueness:
            self.__check_duplicate_quartets(working_layout)
        self.__check_optimem_factor(working_layout)

    def __check_duplicate_quartets(self, working_layout):
        """
        Checks whether there are duplicate positions (ID quartets).
        """
        duplicate_positons = working_layout.get_ambiguous_wells()
        if not len(duplicate_positons) < 1:
            labels = []
            for tup in duplicate_positons: labels.append(tup)
            msg = 'The following wells cannot be identified uniquely: %s. ' \
                  'Each combination of molecule design pool ID, reagent name ' \
                  'and reagent dilution factor may occur only once!' \
                   % (labels)
            self.add_error(msg)

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


class TransfectionRackSectorAssociator(IsoRackSectorAssociator):
    """
    This is a special rack sector determiner. It sorts the transfection
    positions by final concentration. The molecule design pools of parent and
    child wells must be shared.

    **Return Value:** A map containing the values for the different sectors.
    """

    NAME = 'Transfection rack sector associator'

    SECTOR_ATTR_NAME = 'final_concentration'
    WORKING_LAYOUT_CLS = TransfectionLayout

    def __init__(self, transfection_layout, log, number_sectors=4):
        """
        Constructor:

        :param transfection_layout: The ISO layout whose positions to check.
        :type transfection_layout: :class:`TransfectionLayout`

        :param number_sectors: The number of rack sectors.
        :type number_sectors: :class:`int`
        :default number_sectors: *4*

        :param log: The ThelmaLog you want to write in. If the
            log is None, the object will create a new log.
        :type log: :class:`thelma.ThelmaLog`
        """
        IsoRackSectorAssociator.__init__(self, iso_layout=transfection_layout,
                                         log=log, ignore_mock=True,
                                         number_sectors=number_sectors,
                                         has_distinct_floatings=False)


class TransfectionAssociationData(IsoAssociationData):
    """
    A helper class determining and storing associated rack sectors, parent
    sectors and sector concentrations (ISO and final) for an transfection
    layout.

    :Note: All attributes are immutable.
    """
    def __init__(self, transfection_layout, log):
        """
        Constructor:

        :param iso_layout: The ISO layout whose sectors to associate.
        :type iso_layout: :class:`IsoLayout`

        :param log: The log to write into (not stored in the object).
        :type log: :class:`thelma.ThelmaLog`
        """
        IsoAssociationData.__init__(self, iso_layout=transfection_layout,
                                    log=log, has_distinct_floatings=False)

        self.__iso_concentrations = None
        self.__find_iso_concentrations(transfection_layout, log)

    @property
    def iso_concentrations(self):
        """
        The ISO concentrations for the different rack sectors.
        """
        return self.__iso_concentrations

    def _init_associator(self, working_layout, log):
        """
        Initialises the associator.
        """
        associator = TransfectionRackSectorAssociator(number_sectors=4, log=log,
                                            transfection_layout=working_layout)
        return associator

    def __find_iso_concentrations(self, transfection_layout, log):
        """
        Finds the ISO concentration for each rack sector.
        """
        determiner = IsoValueDeterminer(iso_layout=transfection_layout,
                                    attribute_name='iso_concentration',
                                    log=log, number_sectors=self.number_sectors)
        self.__iso_concentrations = determiner.get_result()

        if self.__iso_concentrations is None:
            msg = ', '.join(determiner.get_messages())
            raise ValueError(msg)
