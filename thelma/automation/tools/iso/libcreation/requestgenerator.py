from math import ceil

from everest.entities.utils import get_root_aggregate
from thelma.automation.handlers.libbaselayout \
    import LibraryBaseLayoutParserHandler
from thelma.automation.handlers.poolcreationset import \
    PoolCreationSetParserHandler
from thelma.automation.semiconstants import get_pipetting_specs_biomek
from thelma.automation.semiconstants import get_pipetting_specs_cybio
from thelma.automation.tools.base import BaseTool
from thelma.automation.tools.iso.libcreation.base import LibraryBaseLayout
from thelma.automation.tools.iso.libcreation.base import NUMBER_SECTORS
from thelma.automation.tools.iso.libcreation.base import \
    DEFAULT_ALIQUOT_PLATE_CONCENTRATION
from thelma.automation.tools.iso.libcreation.base import \
    DEFAULT_ALIQUOT_PLATE_VOLUME
from thelma.automation.tools.iso.libcreation.base import \
    DEFAULT_LIBRARY_MOLECULE_TYPE_ID
from thelma.automation.tools.iso.libcreation.base import \
    DEFAULT_NUMBER_LIBRARY_PLATE_ALIQUOTS
from thelma.automation.tools.iso.libcreation.base import \
    DEFAULT_PREPARATION_PLATE_VOLUME
from thelma.automation.tools.iso.libcreation.base import \
    get_pool_buffer_volume
from thelma.automation.tools.iso.libcreation.base import \
    get_preparation_plate_transfer_volume
from thelma.automation.tools.iso.libcreation.base import \
    get_stock_transfer_volume
from thelma.automation.tools.stock.base import STOCKMANAGEMENT_USER
from thelma.automation.tools.stock.base import get_default_stock_concentration
from thelma.automation.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.utils.base import is_valid_number
from thelma.automation.utils.racksector import \
    get_sector_layouts_for_384_layout
from thelma.interfaces import IMoleculeType
from thelma.models.iso import StockSampleCreationIsoRequest
from thelma.models.library import MoleculeDesignLibrary
from thelma.models.liquidtransfer import PlannedRackSampleTransfer
from thelma.models.liquidtransfer import PlannedSampleDilution
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.liquidtransfer import WorklistSeries
from thelma.models.user import User


__docformat__ = 'reStructuredText en'

__all__ = ['LibraryCreationIsoRequestGenerator',
           'LibraryCreationWorklistGenerator']


class LibraryCreationIsoRequestGenerator(BaseTool):
    """
    This tool creates an ISO request for a library creation procedure.
    The input stream contains the base layout for the library and the
    molecule design for the pools to be created.
    The worklists for the sample transfers a created as well.

    **Return Value:** :class:`thelma.models.library.MoleculeDesignLibrary`
    """
    NAME = 'Library Generation'

    def __init__(self, library_name, stream, requester, number_designs=1,
                 number_aliquots=DEFAULT_NUMBER_LIBRARY_PLATE_ALIQUOTS,
                 preparation_plate_volume=DEFAULT_PREPARATION_PLATE_VOLUME,
                 molecule_type=DEFAULT_LIBRARY_MOLECULE_TYPE_ID,
                 create_pool_racks=None, parent=None):
        """
        Constructor.

        :param library_name: Name of the library to be created.
        :type library_name: :class:`str`
        :param stream: Excel file stream containing one sheet with the
            library base layout and one with the molecule design data.
        :param requester: This user will be owner and reporter of the ISO
            trac tickets.
        :type requester: :class:`thelma.models.user.User`
        :param str molecule_type: Molecule type to use for the library.
        :param int number_designs: Number of designs contained in the
            library pools to create.
        :params int number_aliquots: Number of aliquots to create for
            each library plate.
        :params float preparation_plate_volume: Volume to create in the
            preparation plates.
        :params bool create_pool_racks: Flag indicating whether pooled stock
            tube racks should be created. If this is set to `False`, the
            stock transfer will be assumed to have the preparation plate as
            target and buffer volumes will be calculated accordingly. By
            default, this is set to `True` unless `number_designs` is 1.
        """
        BaseTool.__init__(self, parent=parent)
        self.library_name = library_name
        self.stream = stream
        self.requester = requester
        self.number_designs = number_designs
        self.number_aliquots = number_aliquots
        self.preparation_plate_volume = preparation_plate_volume
        self.molecule_type = molecule_type
        if create_pool_racks is None:
            create_pool_racks = not number_designs == 1
        self.create_pool_racks = create_pool_racks
        #: The base layout (384-well) defining which positions contain
        #: libary samples.
        self.__base_layout = None
        #: The pool set containing the stock sample pools for the library.
        self.__pool_set = None
        #: The worklist series (generated by the
        #: :class:`LibraryCreationWorklistGenerator`).
        self.__worklist_series = None
        #: The stock concentration for the single molecule design pools.
        self.__stock_concentration = None
        #: The stock transfer volume for the single molecule design pools.
        self.__stock_transfer_volume = None
        #: The number of plates (ISOs) depends on the number of positions in the
        #: base layouts and the number of pools in the molecule design set.
        self.__number_plates = None

    def reset(self):
        BaseTool.reset(self)
        self.__base_layout = None
        self.__pool_set = None
        self.__worklist_series = None
        self.__stock_concentration = None
        self.__number_plates = None

    def run(self):
        """
        Creates the ISO request.
        """
        self.reset()
        self.add_info('Start ISO request creation ...')
        self.__check_input()
        if not self.has_errors():
            self.__stock_concentration = \
                        get_default_stock_concentration(self.molecule_type)
            # The transfer volume from a single design stock tube is
            # determined by preparation plate volume, stock concentration,
            # and number of molecule designs per pool.
            self.__stock_transfer_volume = \
                get_stock_transfer_volume(
                    preparation_plate_volume=self.preparation_plate_volume,
                    stock_concentration=self.__stock_concentration,
                    number_designs=self.number_designs)
        if not self.has_errors():
            self.__parse_base_layout()
        if not self.has_errors():
            self.__get_pool_set()
        if not self.has_errors():
            self.__create_worklist_series()
        if not self.has_errors():
            self.__determine_number_of_plates()
        if not self.has_errors():
            self.return_value = self.__create_library()
            self.add_info('ISO request generation completed.')

    def __check_input(self):
        """
        Checks the initialisation values.
        """
        self._check_input_class('library name', self.library_name, basestring)
        self._check_input_class('requester', self.requester, User)
        self._check_input_class('number designs', self.number_designs, int)
        self._check_input_class('number aliquots', self.number_aliquots, int)
        self._check_input_class('molecule type', self.molecule_type,
                                basestring)

    def __parse_base_layout(self):
        # Parse the library layout.
        self.add_debug('Obtain base layout ...')
        handler = LibraryBaseLayoutParserHandler(self.stream, parent=self)
        self.__base_layout = handler.get_result()
        if self.__base_layout is None:
            msg = 'Error when trying to obtain library base layout.'
            self.add_error(msg)

    def __get_pool_set(self):
        # Retrieves the pool set from the parsed Excel data stream.
        self.add_debug('Obtain pool set ...')
        handler = PoolCreationSetParserHandler(self.stream,
                                               parent=self)
        self.__pool_set = handler.get_result()
        parsed_num_designs = handler.get_number_designs()
        if parsed_num_designs != self.number_designs:
            msg = 'The number of designs per molecule design pool in the ' \
                  'request file (%i) differs from the requested number of ' \
                  'designs (%i).' % (parsed_num_designs, self.number_designs)
            self.add_error(msg)
        agg = get_root_aggregate(IMoleculeType)
        md_type = agg.get_by_id(self.molecule_type)
        parsed_mol_type = handler.get_molecule_type()
        if parsed_mol_type != md_type:
            msg = 'The molecule type of the pools in the request file (%s) ' \
                  'differs from the requested molecule type (%s).' \
                  % (parsed_mol_type, self.molecule_type)
            self.add_error(msg)
        if self.__pool_set is None:
            msg = 'Unable to parse library pool set!'
            self.add_error(msg)

    def __create_worklist_series(self):
        # Generates the buffer transfer worklists.
        self.add_debug('Create worklist series ...')
        if self.create_pool_racks:
            pool_buf_vol = get_pool_buffer_volume()
            prep_trf_vol = get_preparation_plate_transfer_volume(
                                preparation_plate_volume=
                                        self.preparation_plate_volume)
            prep_buf_vol = self.preparation_plate_volume - prep_trf_vol
        else:
            pool_buf_vol = None
            prep_buf_vol = \
                self.preparation_plate_volume \
                - self.__stock_transfer_volume * self.number_designs
        generator = LibraryCreationWorklistGenerator(
                                            self.__base_layout,
                                            self.__stock_concentration,
                                            self.library_name,
                                            prep_buf_vol,
                                            pool_buffer_volume=pool_buf_vol,
                                            parent=self)
        self.__worklist_series = generator.get_result()
        if self.__worklist_series is None:
            msg = 'Error when trying to generate worklist series.'
            self.add_error(msg)

    def __determine_number_of_plates(self):
        # The number of plates depends on the number of molecule design set
        # member and the number of available positions in the library layout.
        number_members = len(self.__pool_set)
        number_positions = len(self.__base_layout)
        number_plates = ceil(float(number_members) / number_positions)
        self.__number_plates = int(number_plates)

    def __create_library(self):
        # Create library creation ISO request and library.
        final_vol = DEFAULT_ALIQUOT_PLATE_VOLUME / VOLUME_CONVERSION_FACTOR
        final_conc = DEFAULT_ALIQUOT_PLATE_CONCENTRATION \
                        / CONCENTRATION_CONVERSION_FACTOR
        stock_vol = self.__stock_transfer_volume / VOLUME_CONVERSION_FACTOR
        stock_conc = self.__stock_concentration \
                        / CONCENTRATION_CONVERSION_FACTOR
        self.add_debug('Create ISO request ...')
        iso_request = StockSampleCreationIsoRequest(
                            self.library_name,
                            stock_vol,
                            stock_conc,
                            number_designs=self.number_designs,
                            expected_number_isos=self.__number_plates,
                            number_aliquots=self.number_aliquots,
                            owner=STOCKMANAGEMENT_USER,
                            molecule_design_pool_set=self.__pool_set,
                            worklist_series=self.__worklist_series,
                            preparation_plate_volume=
                                self.preparation_plate_volume)
        library = MoleculeDesignLibrary(
                            self.__pool_set,
                            self.library_name,
                            final_vol,
                            final_conc,
                            self.__number_plates,
                            self.__base_layout.create_rack_layout(),
                            creation_iso_request=iso_request)
        return library


class LibraryCreationWorklistGenerator(BaseTool):
    """
    Creates the worklist series for containing the worklists involved in
    library creation.

    Preparation route with pool stock racks (default):
     1. Buffer addition into the pool stock racks (1 for each quadrant)
     2. Buffer addition into preparation plates (1 for each quadrant)
     3. Rack transfers from normal stock racks into pool stock racks (the
        take out worklists are not stored as part of this worklist series
        but at the sample stock racks as container transfer worklist to allow
        for container tracking)
     4. Rack transfer from stock rack to preparation plate
     5. Rack transfer from preparation plates to aliquot plate.

    For the preparation route without pool stock racks, steps 1 and 3 are
    left out and the stock transfer is made directly into the preparation
    plate (with the buffer volume adjusted accordingly).

    **Return Value:**  worklist series
        (:class:`thelma.models.liquidtransfer.WorklistSeries`).
    """
    NAME = 'Library Creation Worklist Generator'
    #: Name pattern for the worklists that add annealing buffer to the pool
    #: stock racks. The placeholders will contain the library name and the
    #: quadrant sector.
    LIBRARY_STOCK_BUFFER_WORKLIST_LABEL = '%s_stock_buffer_Q%i'
    #: Name pattern for the worklists that add annealing buffer to the pool
    #: preparation plates. The placeholders will contain the library name and
    #: the quadrant sector.
    LIBRARY_PREP_BUFFER_WORKLIST_LABEL = '%s_prep_buffer_Q%i'
    #: Name pattern for the worklists that transfers the pool from the pool
    #: stock rack to the preparation plate. The placeholder will contain the
    #: library name.
    STOCK_TO_PREP_TRANSFER_WORKLIST_LABEL = '%s_stock_to_prep'
    #: Name pattern for the worklists that transfers the pool from the
    #: preparation plate to the final library aliqut plate. The placeholder will
    #: contain the library name.
    PREP_TO_ALIQUOT_TRANSFER_WORKLIST_LABEL = '%s_prep_to_aliquot'
    #: The dilution info for the dilution worklists.
    DILUTION_INFO = 'annealing buffer'


    def __init__(self, base_layout, stock_concentration,
                 library_name, preparation_buffer_volume,
                 pool_buffer_volume=None, parent=None):
        """
        Constructor.

        :param base_layout: Layout defining which positions of the layout
            are allowed to take up library samples.
        :type base_layout: :class:`LibraryBaseLayout`
        :param int stock_concentration: Concentration of the single
            source molecule designs in the stock in nM (positive number).
        :param str library_name: Name of the library to be created.
        :param float pool_buffer_volume: Buffer volume for pool
            plates. May be `None` if no pool racks are created.
        :param float preparation_buffer_volume: Buffer volume for preparation
            plates.
        """
        BaseTool.__init__(self, parent=parent)
        self.base_layout = base_layout
        self.stock_concentration = stock_concentration
        self.library_name = library_name
        self.preparation_buffer_volume = preparation_buffer_volume
        self.pool_buffer_volume = pool_buffer_volume
        #: The worklist series for the ISO request.
        self.__worklist_series = None
        #: The last used worklist index (within the series).
        self.__last_worklist_index = None
        #: The base layout for each sector.
        self.__sector_layouts = None

    def reset(self):
        BaseTool.reset(self)
        self.__worklist_series = None
        self.__last_worklist_index = 0
        self.__sector_layouts = dict()

    def run(self):
        self.reset()
        self.add_info('Start worklist generation ...')
        self.__check_input()
        if not self.has_errors():
            self.__sort_into_sectors()
        if not self.has_errors():
            self.__worklist_series = WorklistSeries()
            if not self.pool_buffer_volume is None:
                self.__create_pool_rack_buffer_worklists()
        if not self.has_errors():
            self.__create_preparation_plate_buffer_worklists()
        if not self.has_errors():
            self.__create_prep_to_aliquot_worklist()
        if not self.has_errors():
            self.return_value = self.__worklist_series
            self.add_info('Worklist generation completed.')

    def __check_input(self):
        # Checks the initialisation values.
        self.add_debug('Checking input.')
        self._check_input_class('base library layout', self.base_layout,
                                LibraryBaseLayout)
        self._check_input_class('library name', self.library_name, basestring)
        if not is_valid_number(self.stock_concentration):
            msg = 'The stock concentration for the single source molecules ' \
                  'must be a positive number (obtained: %s).' \
                  % (self.stock_concentration)
            self.add_error(msg)

    def __sort_into_sectors(self):
        # Create a rack layout for each quadrant.
        self.add_debug('Sorting positions into sectors.')
        self.__sector_layouts = \
                        get_sector_layouts_for_384_layout(self.base_layout,
                                                          LibraryBaseLayout)
        if len(self.__sector_layouts) < NUMBER_SECTORS:
            missing_sector_labels = [str(si + 1)
                                     for si in range(NUMBER_SECTORS)
                                     if not si in self.__sector_layouts]
            msg = 'Some rack sectors are empty. You do not require stock ' \
                  'racks for them: %s!' % ', '.join(missing_sector_labels)
            self.add_warning(msg)

    def __create_pool_rack_buffer_worklists(self):
        # These worklists are responsible for the addition of annealing buffer
        # to the pool rack. There is 1 worklist for each quadrant.
        self.add_debug('Creating pool buffer worklists.')
        for sector_index, sector_layout in self.__sector_layouts.iteritems():
            label = self.LIBRARY_STOCK_BUFFER_WORKLIST_LABEL \
                        % (self.library_name, sector_index + 1)
            self.__create_buffer_worklist(sector_layout,
                                          self.pool_buffer_volume, label)

    def __create_preparation_plate_buffer_worklists(self):
        # These worklists are responsible for the addition of annealing
        # buffer to the pool preparation plate. There is 1 worklist for each
        # quadrant.
        self.add_debug('Creating preparation plate buffer worklists.')
        for sector_index, sector_layout in self.__sector_layouts.iteritems():
            label = self.LIBRARY_PREP_BUFFER_WORKLIST_LABEL % (
                                        self.library_name, (sector_index + 1))
            self.__create_buffer_worklist(sector_layout,
                                          self.preparation_buffer_volume,
                                          label)

    def __create_buffer_worklist(self, sector_layout, buffer_volume, label):
        # Creates the buffer dilution worklist for a particular quadrant
        # and adds it to the worklist series.
        volume = buffer_volume / VOLUME_CONVERSION_FACTOR
        ptfs = []
        for rack_pos_96 in sector_layout.get_positions():
            planned_transfer = PlannedSampleDilution.get_entity(
                                                        volume,
                                                        self.DILUTION_INFO,
                                                        rack_pos_96)
            ptfs.append(planned_transfer)
        worklist = PlannedWorklist(label,
                                   TRANSFER_TYPES.SAMPLE_DILUTION,
                                   get_pipetting_specs_biomek(),
                                   planned_liquid_transfers=ptfs)
        self.__worklist_series.add_worklist(self.__last_worklist_index,
                                            worklist)
        self.__last_worklist_index += 1

    def __create_prep_to_aliquot_worklist(self):
        # There is one rack transfer for each sector (many-to-one transfer).
        # Each transfer is executed once per aliquot plate.
        self.add_debug('Add worklist for transfer into aliquot plates ...')
        volume = DEFAULT_ALIQUOT_PLATE_VOLUME / VOLUME_CONVERSION_FACTOR
        rack_transfers = []
        for sector_index in self.__sector_layouts.keys():
            rack_transfer = PlannedRackSampleTransfer.get_entity(
                                                            volume,
                                                            NUMBER_SECTORS,
                                                            0,
                                                            sector_index)
            rack_transfers.append(rack_transfer)
        label = self.PREP_TO_ALIQUOT_TRANSFER_WORKLIST_LABEL % (
                                                            self.library_name)
        worklist = PlannedWorklist(label,
                                   TRANSFER_TYPES.RACK_SAMPLE_TRANSFER,
                                   get_pipetting_specs_cybio(),
                                   planned_liquid_transfers=rack_transfers)
        self.__worklist_series.add_worklist(self.__last_worklist_index,
                                            worklist)
        self.__last_worklist_index += 1
