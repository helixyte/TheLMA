"""
The classes in this module serve the creation of an ISO for a library creation
process.

:Note: The ISOs are already created externally, because they need a ticket ID.
    The tool actually populates an empty ISO (instead of creating a new one).

The following tasks need to be performed:

 * pick molecule design pools
 * create a preparation layout (= library layout)
 * create preparation plate
 * create aliquot plate
 * create ISO sample stock rack for each quadrant (barcodes are provided)

AAB
"""
from thelma.automation.semiconstants import get_item_status_future
from thelma.automation.semiconstants import get_reservoir_specs_standard_384
from thelma.automation.semiconstants import get_reservoir_specs_standard_96
from thelma.automation.tools.base import BaseTool
from thelma.automation.semiconstants import get_rack_specs_from_reservoir_specs
from thelma.automation.tools.libcreation.base \
    import ALIQUOT_PLATE_CONCENTRATION
from thelma.automation.tools.libcreation.base \
    import LibraryBaseLayoutConverter
from thelma.automation.tools.libcreation.base \
    import MOLECULE_DESIGN_TRANSFER_VOLUME
from thelma.automation.tools.libcreation.base \
    import PREPARATION_PLATE_CONCENTRATION
from thelma.automation.tools.libcreation.base import LibraryLayout
from thelma.automation.tools.libcreation.base import MOLECULE_TYPE
from thelma.automation.tools.libcreation.base import NUMBER_SECTORS
from thelma.automation.tools.libcreation.base import STARTING_NUMBER_ALIQUOTS
from thelma.automation.tools.libcreation.optimizer import LibraryCreationTubePicker
from thelma.automation.tools.stock.base import get_default_stock_concentration
from thelma.automation.tools.writers import CsvColumnParameters
from thelma.automation.tools.writers import CsvWriter
from thelma.automation.utils.base import is_valid_number
from thelma.automation.utils.racksector import QuadrantIterator
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import IsoAliquotPlate
from thelma.models.iso import IsoSectorPreparationPlate
from thelma.models.iso import StockSampleCreationIso
from thelma.models.library import MoleculeDesignLibrary


__docformat__ = 'reStructuredText en'

__all__ = ['LibraryCreationIsoPopulator',
           'LibraryCreationIsoLayoutWriter']


class LibraryCreationIsoPopulator(BaseTool):
    """
    Populates an empty library creation ISO for a library. The tools creates
    a proper rack layout, preparation plates and aliquot plates.

    **Return Value:** The newly populated ISOs.
    """
    NAME = 'Library Creation ISO Populator'

    #: The label pattern for preparation plates.
    PREP_PLATE_LABEL_PATTERN = '%s-%i-%inM-Q%i'
    #: The label pattern for aliquot plates.
    ALIQUOT_PLATE_LABEL_PATTERN = '%s-%i-%inM-%i'

    def __init__(self, molecule_design_library, number_isos,
                 excluded_racks=None, requested_tubes=None, parent=None):
        """
        Constructor:

        :param molecule_design_library: The molecule design library for which to
            populate the ISO.
        :type molecule_design_library:
            :class:`thelma.models.library.MoleculeDesignLibrary`
        :param number_isos: The number of ISOs ordered.
        :type number_isos: :class:`int`
        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for stock sample picking.
        :type excluded_racks: A list of rack barcodes
        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of tube barcodes.
        """
        BaseTool.__init__(self, parent=parent)
        #: The molecule design library for which to generate an ISO.
        self.molecule_design_library = molecule_design_library
        #: The number of ISOs ordered.
        self.number_isos = number_isos

        #: A list of barcodes from stock racks that shall not be used for
        #: stock sample (molecule design pool) picking.
        self.excluded_racks = excluded_racks
        if excluded_racks is None: self.excluded_racks = []

        if requested_tubes is None: requested_tubes = []
        #: A list of barcodes from stock tubes that are supposed to be used
        #: (for fixed positions).
        self.requested_tubes = requested_tubes

        #: The ISO request defining the ISO layout
        #: (:class:`thelma.models.iso.IsoRequest`)
        self._iso_request = None

        #: The library pools for which to pick tubes.
        self._queued_pools = None
        #: The stock concentration for the library molecule type.
        self.__stock_concentration = None
        #: The worklist series that is attached to the ISO request.
        self.__worklist_series = None

        #: The base layout defines which positions might be taken by library
        #: positions. This is the base layout for the 384-well plate.
        self.__base_layout = None
        #: The base layout positions for each quadrant.
        self._quadrant_positions = None

        #: The library candidates returned by the optimiser.
        self._library_candidates = None

        #: The library layouts mapped onto layout numbers.
        self._library_layouts = None

        #: The picked empty ISOs to populate.
        self.__picked_isos = None

        #: The newly populated ISOs.
        self.__new_isos = None

    def reset(self):
        BaseTool.reset(self)
        self._iso_request = None
        self._queued_pools = []
        self.__stock_concentration = None
        self.__worklist_series = None
        self.__base_layout = None
        self._quadrant_positions = dict()
        self._library_candidates = None
        self._library_layouts = []
        self.__picked_isos = []
        self.__new_isos = []

    def run(self):
        """
        Creates the requested number of ISO.
        """
        self.reset()
        self.add_info('Start ISO generation ...')

        self._check_input()
        if not self.has_errors(): self.__get_library_metadata()
        if not self.has_errors(): self.__get_base_layout()
        if not self.has_errors(): self.__pick_library_candidates()
        if not self.has_errors(): self._distribute_candidates()
        if not self.has_errors(): self.__pick_isos()
        if not self.has_errors(): self.__populate_isos()
        if not self.has_errors():
            self.return_value = self.__new_isos
            self.add_info('ISO generation completed.')

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check initialisation values ...')

        self._check_input_class('molecule design library',
                            self.molecule_design_library, MoleculeDesignLibrary)

        if not is_valid_number(self.number_isos, is_integer=True):
            msg = 'The number of ISOs order must be a positive integer ' \
                  '(obtained: %s).' % (self.number_isos)
            self.add_error(msg)

        if self._check_input_class('excluded racks list',
                                       self.excluded_racks, list):
            for excl_rack in self.excluded_racks:
                if not self._check_input_class('excluded rack barcode',
                                               excl_rack, basestring): break

        if self._check_input_class('requested tubes list',
                                       self.requested_tubes, list):
            for req_tube in self.requested_tubes:
                if not self._check_input_class('requested tube barcode',
                                               req_tube, basestring): break

    def __get_library_metadata(self):
        """
        Determines the ISO request, the library pools for which to pick
        source tubes, the worklist series and the stock concentration.
        """
        self._iso_request = self.molecule_design_library.iso_request
        if self._iso_request is None:
            msg = 'There is no ISO request for this library!'
            self.add_error(msg)

        else:
            self.__worklist_series = self._iso_request.worklist_series
            self._find_queued_pools()
            if not self.has_errors():
                self.__stock_concentration = \
                                get_default_stock_concentration(MOLECULE_TYPE)

    def _find_queued_pools(self):
        """
        All molecule design pools from the ISO request that are not part
        of an ISO yet, are used. Cancelled ISOs are ignored.
        """
        used_pools = set()
        for iso in self._iso_request.isos:
            if iso.status == ISO_STATUS.CANCELLED:
                continue
            if iso.molecule_design_pool_set is None:
                continue
            used_pools.update(
                        iso.molecule_design_pool_set.molecule_design_pools)
        pool_set = self.molecule_design_library.molecule_design_pool_set
        self._queued_pools = \
                pool_set.molecule_design_pools.difference(used_pools)
        if len(self._queued_pools) < 1:
            msg = 'There are no unused molecule design pools left!'
            self.add_error(msg)

    def __get_base_layout(self):
        # The base layout defines which positions might be taken by library
        # positions.
        self.add_debug('Fetch base layout ...')
        converter = LibraryBaseLayoutConverter(
                                self._iso_request.iso_layout, parent=self)
        self.__base_layout = converter.get_result()
        if self.__base_layout is None:
            msg = 'Error when trying to fetch library base layout.'
            self.add_error(msg)
        else:
            self._quadrant_positions = QuadrantIterator.sort_into_sectors(
                                            self.__base_layout,
                                            number_sectors=NUMBER_SECTORS)

    def __pick_library_candidates(self):
        # Runs the library optimizer. The optimizer returns a list of
        # :class:`LibraryCandidate` objects (in order of the optimizing
        # completion).
        optimizer = LibraryCreationTubePicker(
                            self._queued_pools,
                            self.__stock_concentration,
                            take_out_volume=MOLECULE_DESIGN_TRANSFER_VOLUME,
                            excluded_racks=self.excluded_racks,
                            requested_tubes=self.requested_tubes,
                            parent=self)
        self._library_candidates = optimizer.get_result()
        if self._library_candidates is None:
            msg = 'Error when trying to pick tubes.'
            self.add_error(msg)

    def _distribute_candidates(self):
        """
        Creates a :class:`LibraryLayout` for each ISO.

        Positions are populated sector-wise (maybe some sector will remain
        empty if there is not enough positions).
        """
        self.add_info('Distribute candidates ...')

        not_enough_candidates = False
        for i in range(self.number_isos): #pylint: disable=W0612
            if len(self._library_candidates) < 1: break
            lib_layout = LibraryLayout.from_base_layout(self.__base_layout)

            for positions in self._quadrant_positions.values():
                if len(self._library_candidates) < 1: break

                for base_pos in positions:
                    if len(self._library_candidates) < 1:
                        not_enough_candidates = True
                        break
                    lib_cand = self._library_candidates.pop(0)
                    lib_pos = LibraryPosition(pool=lib_cand.pool,
                               rack_position=base_pos.rack_position,
                               stock_tube_barcodes=lib_cand.get_tube_barcodes())
                    lib_layout.add_position(lib_pos)

            if len(lib_layout) < 1:
                break
            else:
                self._library_layouts.append(lib_layout)

        if not_enough_candidates:
            msg = 'There is not enough library candidates left to populate ' \
                  'all positions for the requested number of ISOs. Number ' \
                  'of generated ISOs: %i.' % (len(self._library_layouts))
            self.add_warning(msg)

    def __pick_isos(self):
        """
        Only ISOs with empty rack layouts can be picked.
        """
        iso_map = dict()
        used_layout_numbers = set()
        for iso in self._iso_request.isos:
            if len(iso.rack_layout.tagged_rack_position_sets) > 0:
                used_layout_numbers.add(iso.layout_number)
            iso_map[iso.layout_number] = iso

        number_layouts = self._iso_request.number_plates
        for i in range(number_layouts):
            if not (i + 1) in used_layout_numbers:
                iso = iso_map[i + 1]
                self.__picked_isos.append(iso)
            if len(self.__picked_isos) == len(self._library_layouts): break

    def __populate_isos(self):
        """
        Adds molecule design set, library layout and plates to the picked ISOs.
        """
        self.add_debug('Create ISOs ...')

        ir_specs_96 = get_reservoir_specs_standard_96()
        plate_specs_96 = get_rack_specs_from_reservoir_specs(ir_specs_96)
        ir_specs_384 = get_reservoir_specs_standard_384()
        plate_specs_384 = get_rack_specs_from_reservoir_specs(ir_specs_384)
        future_status = get_item_status_future()
        library_name = self._iso_request.plate_set_label
        md_type = \
          self.molecule_design_library.molecule_design_pool_set.molecule_type

        while len(self.__picked_isos) > 0:
            lci = self.__picked_isos.pop(0)
            library_layout = self._library_layouts.pop(0)
            lci.rack_layout = library_layout.create_rack_layout()
            lci.molecule_design_pool_set = \
                        library_layout.get_pool_set(md_type)
            layout_number = lci.layout_number

            # create source plates
            for sector_index in self._quadrant_positions.keys():
                prep_label = self.PREP_PLATE_LABEL_PATTERN % (library_name,
                                layout_number, PREPARATION_PLATE_CONCENTRATION,
                                (sector_index + 1))
                prep_plate = plate_specs_96.create_rack(label=prep_label,
                                                        status=future_status)
                LibrarySourcePlate(iso=lci, plate=prep_plate,
                                   sector_index=sector_index)

            # create aliquot plates
            for i in range(STARTING_NUMBER_ALIQUOTS):
                aliquot_label = self.ALIQUOT_PLATE_LABEL_PATTERN % (
                                library_name, layout_number,
                                ALIQUOT_PLATE_CONCENTRATION, (i + 1))
                aliquot_plate = plate_specs_384.create_rack(label=aliquot_label,
                                                        status=future_status)
                IsoAliquotPlate(iso=lci, plate=aliquot_plate)

            self.__new_isos.append(lci)


class LibraryCreationIsoLayoutWriter(CsvWriter):
    """
    Generates an overview file containing the layout data for a particular
    library creation ISO.

    **Return Value:** stream (CSV format)
    """
    NAME = 'Library Creation ISO Layout Writer'

    #: The header for the rack position column.
    POSITION_HEADER = 'Rack Position'
    #: The header for the molecule design pool column.
    POOL_HEADER = 'Pool ID'
    #: The header for the molecule design column.
    MOLECULE_DESIGN_HEADER = 'Molecule Design IDs'
    #: The header for the stock tube barcode column.
    TUBE_HEADER = 'Stock Tubes'

    #: The index for the rack position column.
    POSITION_INDEX = 0
    #: The index for the molecule design pool column.
    POOL_INDEX = 1
    #: The index for the molecule design column.
    MOLECULE_DESIGN_INDEX = 2
    #: The index for the stock tube barcode column.
    TUBE_INDEX = 3

    def __init__(self, stock_sample_creation_iso, parent=None):
        """
        Constructor:

        :param stock_sample_creation_iso: The ISO whose library layout you want
            to print.
        :type stock_sample_creation_iso:
            :class:`thelma.models.iso.StockSampleCreationIso`
        """
        CsvWriter.__init__(self, parent=parent)

        #: The ISO whose layout you want to print.
        self.stock_sample_creation_iso = stock_sample_creation_iso

        #: The values for the columns.
        self.__position_values = None
        self.__pool_values = None
        self.__md_values = None
        self.__tube_values = None

    def reset(self):
        CsvWriter.reset(self)
        self.__position_values = []
        self.__pool_values = []
        self.__md_values = []
        self.__tube_values = []

    def _init_column_map_list(self):
        if self._check_input_class('ISO', self.stock_sample_creation_iso,
                                    StockSampleCreationIso):
            self.__store_values()
            self.__generate_columns()

    def __store_values(self):
        # Fetches and stores the values for the columns.
        self.add_debug('Store column values ...')
        lib_layout = self.__get_library_layout()
        if not lib_layout is None:
            for lib_pos in lib_layout.get_sorted_working_positions():
                self.__position_values.append(lib_pos.rack_position.label)
                self.__pool_values.append(lib_pos.pool.id)
                self.__md_values.append(
                                lib_pos.get_molecule_designs_tag_value())
                self.__tube_values.append(
                                lib_pos.get_stock_barcodes_tag_value())

    def __get_library_layout(self):
        # Converts the library layout from the ISO.
        self.add_debug('Get library layout ...')

        converter = LibraryLayoutConverter(
                        self.stock_sample_creation_iso.rack_layout, parent=self)
        lib_layout = converter.get_result()
        if lib_layout is None:
            msg = 'Error when trying to convert library layout!'
            self.add_error(msg)

        return lib_layout

    def __generate_columns(self):
        # Generates the :attr:`_column_map_list`
        pos_column = CsvColumnParameters(self.POSITION_INDEX,
                                self.POSITION_HEADER, self.__position_values)
        pool_column = CsvColumnParameters(self.POOL_INDEX, self.POOL_HEADER,
                                self.__pool_values)
        md_column = CsvColumnParameters(self.MOLECULE_DESIGN_INDEX,
                                self.MOLECULE_DESIGN_HEADER, self.__md_values)
        tube_column = CsvColumnParameters(self.TUBE_INDEX, self.TUBE_HEADER,
                                self.__tube_values)
        self._column_map_list = [pos_column, pool_column, md_column,
                                 tube_column]
