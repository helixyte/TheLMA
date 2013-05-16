"""
This tool generates ISOs for an ISO request. This comprises calls of the
ISO Optimizer (which selects the molecule design pools for floating positions)
and the PrepLayoutFinder (generating the layout for the preparation plate).

Report generation is taken over by an external tool.

AAB
"""
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.iso.optimizer import IsoOptimizer
from thelma.automation.tools.iso.prep_utils import PrepIsoLayout
from thelma.automation.tools.iso.preplayoutfinder import PrepLayoutFinder
from thelma.automation.tools.iso.worklist import IsoWorklistSeriesGenerator
from thelma.automation.tools.semiconstants \
    import get_reservoir_specs_standard_384
from thelma.automation.tools.semiconstants \
    import get_reservoir_specs_standard_96
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import PLATE_SPECS_NAMES
from thelma.automation.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.tools.semiconstants import get_item_status_future
from thelma.automation.tools.semiconstants import get_reservoir_specs_deep_96
from thelma.automation.tools.stock.base import STOCK_CONCENTRATIONS
from thelma.automation.tools.utils.base import is_valid_number
from thelma.automation.tools.utils.iso import IsoLayoutConverter
from thelma.automation.tools.utils.iso import IsoParameters
from thelma.automation.tools.worklists.base \
    import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.worklists.base import VOLUME_CONVERSION_FACTOR
from thelma.models.iso import ISO_STATUS
from thelma.models.iso import Iso
from thelma.models.iso import IsoPreparationPlate
from thelma.models.iso import IsoRequest
from thelma.models.moleculedesign import MoleculeDesignPoolSet
from thelma.models.moleculetype import MOLECULE_TYPE_IDS
import logging

__docformat__ = 'reStructuredText en'

__all__ = ['IsoCreator',
           'IsoGenerator',
           'IsoRescheduler']


class IsoCreator(BaseAutomationTool):
    """
    An abstract base tool for the generation of ISOs. It comprises an
    optimisation step (finding stock racks so that only a minimum number has
    to be taken from the stock) and the generation of preparation plate layouts
    for the ISOs.

    Subclasses concentrate on the generation of new ISOs (:class:`IsoGenerator`)
    or the re-generation of existing ISOs (:class:`IsoRescheduler`).

    **Return Value:** The new ISOs.
    """

    #: The character used in the ISO label to separate the plate set label of
    #: the ISO request from the ISO counter.
    SEPARATING_CHAR = '_'

    #: The suffix to be added to the ISO label to mark the ISO as copy.
    COPY_MARKER = 'copy'

    def __init__(self, iso_request, number_isos,
                       excluded_racks=None, requested_tubes=None,
                       logging_level=logging.WARNING,
                       add_default_handlers=False):
        """
        Constructor:

        :param iso_request: The ISO request containing the ISO layout for the
            ISO (and experiment metadata with the molecule design pools).
        :type iso_request: :class:`thelma.models.iso.IsoRequest`

        :param number_isos: The number of ISOs ordered.
        :type number_isos: :class:`int`

        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for stock sample picking.
        :type excluded_racks: A list of rack barcodes

        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of tube barcodes.

        :param logging_level: the desired minimum log level
        :type log_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """
        BaseAutomationTool.__init__(self, logging_level=logging_level,
                                    add_default_handlers=add_default_handlers,
                                    depending=False)

        #: The ISO request defining the ISO layout
        #: (:class:`thelma.models.iso.IsoRequest`)
        self.iso_request = iso_request
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

        #: The new ISOs that have been generated.
        self.__isos = None

        #: The ISO layout for the ISO request.
        self.__iso_layout = None
        #: The preparation layout for the ISO with unconverted floatings.
        self._raw_prep_layout = None
        #: The number of distinct floating placeholders.
        self._number_floatings = None

        #: The molecule design pool IDs of the fixed positions.
        self.__fixed_pools = None
        #: The queued molecule design pools for the floating positions (mapped
        #: onto their molecule design pool IDs).
        self._floating_pools = None

        #: The stock concentration for the fixed molecule design pools.
        self.__fixed_concentrations = None
        #: The stock concentration for the floating molecule design pools.
        self.__floating_concentration = None

        #: The ISO candidates for fixed positions (in unchanged order).
        self.__fixed_candidates = None
        #: The ISO candidates for the floating positions (in unchanged order)
        #: mapped onto ISO counts.
        self.__floating_candidates = None
        #: The ISO candidates for both fixed and floating positions (in
        #: unchanged order).
        self.__all_candidates = None

        #: The picked candidated for each fixed candidate design.
        self.__fixed_selection = None
        #: The picked candidated for each floating candidate design.
        self.__floating_selection = None

        #: The ISO candidates for the floating positions mapped onto the
        #: labels of the new ISOs.
        self.__iso_selections = None

        #: The experiment type.
        self._experiment_type = None

        #: The preparation layouts for each new ISO (for report purposes).
        self.__prep_layout_map = None
        #: The plate specs for the ISO preparation plates.
        self._prep_plate_specs = None

    def reset(self):
        """
        Resets all attributes except for the initialisation values.
        """
        BaseAutomationTool.reset(self)
        self.__isos = []
        self.__iso_layout = None
        self._raw_prep_layout = None
        self._number_floatings = None
        self.__fixed_pools = set()
        self._floating_pools = dict()
        self.__fixed_concentrations = dict()
        self.__floating_concentration = None
        self.__fixed_candidates = None
        self.__floating_candidates = None
        self.__all_candidates = None
        self.__fixed_selection = dict()
        self.__floating_selection = dict()
        self.__iso_selections = dict()
        self._experiment_type = None
        self.__prep_layout_map = dict()
        self._prep_plate_specs = None

    def get_report_data(self):
        """
        Returns the fixed candidate selection and the ISO selections and
        the preparation layout map.
        """
        if self.return_value is None:
            return None
        else:
            return self.__fixed_selection, self.__iso_selections, \
                   self.__prep_layout_map

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start ISO creation ...')

        self._check_input()
        if not self.has_errors():
            self.__get_iso_layout()
            self.__get_metadata()
        if not self.has_errors(): self.__find_preparation_layout()
        if not self.has_errors():
            self.__look_for_compounds()
            self._determine_prep_plate_specs()
        if not self.has_errors(): self.__add_suppliers_and_count_floatings()
        if not self.has_errors(): self.__find_molecule_design_pools()
        if not self.has_errors(): self.__run_optimizers()
        if not self.has_errors(): self.__distribute_candidates()
        if not self.has_errors(): self.__create_isos()
        if not self.has_errors(): self.__create_worklist_series()
        if not self.has_errors():
            self.return_value = self.__isos
            self.add_info('ISO creation completed.')

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check initialisation values ...')

        self._check_input_class('ISO request', self.iso_request, IsoRequest)
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

    def __get_iso_layout(self):
        """
        Fetches the ISO layout from the ISO request.
        """
        self.add_debug('Convert ISO layout ...')

        converter = IsoLayoutConverter(rack_layout=self.iso_request.iso_layout,
                                       log=self.log)
        self.__iso_layout = converter.get_result()

        if self.__iso_layout is None:
            msg = 'Error when trying to convert ISO layout.'
            self.add_error(msg)

    def __get_metadata(self):
        """
        Sets the metadata required for the ISO creation (e.g. stock
        concentration of the molecule type, the experiment type).
        """
        self.add_debug('Get metadata ...')

        experiment_metadata = self.iso_request.experiment_metadata
        self._experiment_type = experiment_metadata.experiment_metadata_type

        pool_set = experiment_metadata.molecule_design_pool_set
        if not pool_set is None:
            # We cannot use the molecule type, because the stock
            # concentration also depends on the number of designs.
            # The stock concentration must be equal for all members of the
            # set therefore we can pick an arbitrary member.
            for pool in pool_set:
                stock_conc = pool.default_stock_concentration \
                             * CONCENTRATION_CONVERSION_FACTOR
                self.__floating_concentration = stock_conc

    def __find_preparation_layout(self):
        """
        Finds the (raw) preparation layouts for the ISO.
        """
        self.add_debug('Find preparation layout ...')

        finder = PrepLayoutFinder.create(iso_layout=self.__iso_layout,
                                         iso_request=self.iso_request,
                                         log=self.log)
        if finder is None:
            msg = 'Error when trying to create layout finder.'
            self.add_error(msg)
        else:
            self._raw_prep_layout = finder.get_result()

            if self._raw_prep_layout is None:
                msg = 'Error when trying to find preparation plate layout!'
                self.add_error(msg)
            elif self.__floating_concentration is not None:
                self._raw_prep_layout.set_floating_stock_concentration(
                                                self.__floating_concentration)

    def _determine_prep_plate_specs(self):
        """
        Determines the plate specs for the ISO preparation plates.
        """
        self.add_error('Abstract method: _determine_prep_plate_specs()')

    def __add_suppliers_and_count_floatings(self):
        """
        Adds the suppliers to the fixed positions of the preparation layout
        and counts the distinct floating placeholder.
        """
        self.add_debug('Add supplier to preparation layout ...')

        unknown_pool_ids = set()
        floating_pools = set()

        iso_suppliers = self.__iso_layout.get_supplier_map()
        for prep_pos in self._raw_prep_layout.working_positions():
            if prep_pos.is_mock: continue
            pool_id = prep_pos.molecule_design_pool_id
            if prep_pos.is_floating:
                floating_pools.add(pool_id)
                continue
            if not iso_suppliers.has_key(pool_id):
                unknown_pool_ids.add(pool_id)
                continue
            supplier = iso_suppliers[pool_id]
            if not supplier is None:
                prep_pos.set_supplier(supplier)

        self._number_floatings = len(floating_pools)
        if self._number_floatings == 0 and self.number_isos > 1:
            msg = 'You have requested %i ISOs. The system will only generate ' \
                  '1 ISO though, because there are no floating positions for ' \
                  'this ISO request.' % (self.number_isos)
            self.add_warning(msg)

    def __find_molecule_design_pools(self):
        """
        Finds the molecule design pools for the optimiser.
        """
        self.add_debug('Collect molecule design pools ...')

        self.__find_fixed_molecule_design_pools()
        if self._number_floatings > 0:
            self._find_floating_molecule_design_pools()

    def __find_fixed_molecule_design_pools(self):
        """
        Collects the fixed molecule design pools.
        """
        for iso_pos in self.__iso_layout.working_positions():
            if not iso_pos.is_fixed: continue
            pool_id = iso_pos.molecule_design_pool_id
            if not pool_id in self.__fixed_pools:
                self.__fixed_pools.add(pool_id)
                self.__fixed_concentrations[pool_id] = \
                                                iso_pos.stock_concentration

        if len(self.__fixed_pools) < 1:
            msg = 'There are no fixed molecule design pools in this ISO layout!'
            self.add_error(msg)

    def _find_floating_molecule_design_pools(self):
        """
        Collects the queued floating molecule design pools.
        """
        msg = 'Abstract method: _find_floating_molecule_design_pools()'
        self.add_error(msg)

    def __run_optimizers(self):
        """
        Runs the optimiser (fetching the ISO candidates from the DB).
        """
        self.add_debug('Run optimiser ...')

        if self.__iso_layout.shape.name == RACK_SHAPE_NAMES.SHAPE_96:
            if self._number_floatings < 1:
                self.__fixed_candidates = self.__get_candidates(
                                                self.__fixed_pools, 'fixed')
            else:
                pool_ids = set()
                for pool_id in self.__fixed_pools: pool_ids.add(pool_id)
                for pool_id in self._floating_pools.keys():
                    pool_ids.add(pool_id)
                self.__all_candidates = self.__get_candidates(pool_ids,
                                                          'fixed and floating')
        elif self.__iso_layout.shape.name == RACK_SHAPE_NAMES.SHAPE_384:
            self.__fixed_candidates = self.__get_candidates(self.__fixed_pools,
                                                            'fixed')
#            if self._experiment_type and self._number_floatings > 0:
            if self._number_floatings > 0: # TODO: reactivate or remove
                floating_designs = set(self._floating_pools.keys())
                self.__floating_candidates = self.__get_candidates(
                                        floating_designs, 'floating')

    def __get_candidates(self, molecule_design_pools, pos_type):
        """
        Runs one particular optimiser and returns the resulting candidate
        list.
        """
        optimizer = IsoOptimizer(molecule_design_pools=molecule_design_pools,
                             preparation_layout=self._raw_prep_layout,
                             log=self.log, excluded_racks=self.excluded_racks)
        candidates = optimizer.get_result()

        if candidates is None:
            msg = 'Error when trying to find ISO candidates for %s positions.' \
                  % (pos_type)
            self.add_error(msg)

        return candidates

    def __distribute_candidates(self):
        """
        Selects candidates from the optimiser results.
        """
        self.add_debug('Create ISOs ...')

        if not self.__fixed_candidates is None:
            self.__create_fixed_candidates_selection()
        if not self.__floating_candidates is None:
            self.__create_floating_candidates_selection()
        if not self.__all_candidates is None:
            self.__create_all_candidates_selection()

        self.__check_fixed_candidates_completeness()

    def __create_fixed_candidates_selection(self):
        """
        Selects the ISO candidates for the fixed positions.
        """

        for pool_id in self.__fixed_pools:
            self.__fixed_selection[pool_id] = None

        for candidate in self.__fixed_candidates:
            pool_id = candidate.pool_id
            exp_conc = self.__fixed_concentrations[pool_id]
            if not exp_conc == candidate.concentration: continue
            if self.__fixed_selection[pool_id] is None:
                self.__fixed_selection[pool_id] = candidate
            elif candidate.container_barcode in self.requested_tubes:
                self.__fixed_selection[pool_id] = candidate

    def __create_floating_candidates_selection(self):
        """
        Selects the candidates for the floating positions.
        """
        used_pools = set()
        found_pools = set()
        current_floatings = dict()
        iso_count = 0

        for candidate in self.__floating_candidates:
            if not candidate.concentration == self.__floating_concentration:
                continue
            pool_id = candidate.pool_id
            found_pools.add(pool_id)
            if pool_id in used_pools: continue

            if iso_count == self.number_isos: continue

            current_floatings[pool_id] = candidate
            used_pools.add(pool_id)
            if len(current_floatings) == self._number_floatings:
                iso_count = self.__store_current_floatings(iso_count,
                                                           current_floatings)
                current_floatings = dict()

        if iso_count < self.number_isos:
            if len(current_floatings) > 0:
                self.__store_current_floatings(iso_count, current_floatings)
            msg = 'Some positions of the last ISO will be empty because ' \
                  'there are not enough molecule design pools left in the ' \
                  'queue to fill all positions. Number of generated ISOs: %i.' \
                   % (len(self.__floating_selection))
            self.add_warning(msg)

        missing_pools = []
        for pool_id in self._floating_pools.keys():
            if not pool_id in found_pools: missing_pools.append(pool_id)
        if len(missing_pools) > 0:
            missing_pools.sort()
            msg = 'Did not find candidates for the following sample molecule ' \
                  'design pools: %s!' % (missing_pools)
            self.add_warning(msg)

    def __store_current_floatings(self, iso_count, current_floatings):
        """
        Stores the floating candidates for the current ISO in the
        :attr:`__floating_selection` map and increments the ISO count.
        """
        iso_count += 1
        self.__floating_selection[iso_count] = current_floatings
        return iso_count

    def __create_all_candidates_selection(self):
        """
        This method is a merge of :func:`__create_floating_candidates_selection`
        and :func:`__create_fixed_candidates_selection`. It does not add any
        functionality but only serves the purpose of speed (to prevent a double
        iteration over the potentially long candidate lists).
        """
        for pool_id in self.__fixed_pools:
            self.__fixed_selection[pool_id] = None

        found_pools = set()
        used_floatings = set()
        current_floatings = dict()
        iso_count = 0

        for candidate in self.__all_candidates:
            pool_id = candidate.pool_id
            if pool_id in self.__fixed_pools:
                exp_conc = self.__fixed_concentrations[pool_id]
            else:
                exp_conc = self.__floating_concentration
            if not candidate.concentration == exp_conc: continue

            if pool_id in used_floatings: continue
            found_pools.add(pool_id)

            # Fixed molecule design pool
            if pool_id in self.__fixed_pools:
                if self.__fixed_selection[pool_id] is None:
                    self.__fixed_selection[pool_id] = candidate
                elif candidate.container_barcode in self.requested_tubes:
                    self.__fixed_selection[pool_id] = candidate
                continue

            # Floating molecule design pools
            if iso_count == self.number_isos: continue

            current_floatings[pool_id] = candidate
            used_floatings.add(pool_id)
            if len(current_floatings) == self._number_floatings:
                iso_count = self.__store_current_floatings(iso_count,
                                                           current_floatings)
                current_floatings = dict()

        if iso_count < self.number_isos:
            if len(current_floatings) < 1:
                msg = 'There is not enough molecule design pools left in ' \
                      'the queue to generate the requested number of ISOs. ' \
                      'Number of generated ISOs: %i.' \
                       % (len(self.__floating_selection))
                self.add_warning(msg)
            else:
                self.__store_current_floatings(iso_count, current_floatings)
                msg = 'Some positions of the last ISO will be empty because ' \
                      'there are not enough molecule design pools left in ' \
                      'the queue to fill all positions. Number of generated ' \
                      'ISOs: %i.' % (len(self.__floating_selection))
                self.add_warning(msg)

        missing_pools = []
        for pool_id in self._floating_pools.keys():
            if not pool_id in found_pools: missing_pools.append(pool_id)
        if len(missing_pools) > 0:
            missing_pools.sort()
            msg = 'Did not find candidates for the following sample molecule ' \
                  'design pools: %s!' % (missing_pools)
            self.add_warning(msg)

    def __check_fixed_candidates_completeness(self):
        """
        Checks whether there is at least one ISO candidate for each fixed
        molecule design and whether there is a candidate for each requested
        tube.
        """
        self.add_debug('Checks candidate completeness ...')

        missing_ids = []
        tube_barcodes = []
        for pool_id, candidate in self.__fixed_selection.iteritems():
            if candidate is None:
                missing_ids.append(pool_id)
            else:
                tube_barcodes.append(candidate.container_barcode)

        if len(missing_ids) > 0:
            missing_ids.sort()
            msg = 'Could not find valid stock tubes for the following ' \
                  'fixed molecule design pool IDs: %s.' % (missing_ids)
            self.add_error(msg)

        missing_requested_tubes = []
        for tube_barcode in self.requested_tubes:
            if not tube_barcode in tube_barcodes:
                missing_requested_tubes.append(tube_barcode)

        if len(self.requested_tubes) > len(tube_barcodes):
            msg = 'There are more requested control tubes (%i) than ' \
                  'control molecule design pools (%i)!' \
                  % (len(self.requested_tubes), len(tube_barcodes))
            self.add_warning(msg)

        if len(missing_requested_tubes) > 0:
            missing_requested_tubes.sort()
            msg = 'The following tube barcodes you have requested could not ' \
                  'be found: %s.' % (missing_requested_tubes)
            self.add_warning(msg)

    def __create_isos(self):
        """
        Creates the ISOs.
        """
        latest_iso_number = self.__get_largest_iso_number()
        placeholder_maps = self.__get_placeholder_maps()

        if len(self.__floating_selection) < 1:
            self.__create_iso(latest_iso_number, 1, dict(), dict())
        else:
            for iso_count, candidate_map in \
                                        self.__floating_selection.iteritems():
                placeholder_map = placeholder_maps[iso_count]
                self.__create_iso(latest_iso_number, iso_count,
                                  placeholder_map, candidate_map)

    def __get_largest_iso_number(self):
        """
        Returns the number of the largest ISO existing for this ISO request.
        """
        highest_number = 0
        for iso in self.iso_request.isos:
            number_str = iso.label.split(self.SEPARATING_CHAR)[-1]
            if number_str == self.COPY_MARKER:
                number_str = iso.label.split(self.SEPARATING_CHAR)[-2]
            try:
                number = int(number_str)
            except ValueError:
                number = len(self.iso_request.isos)
            highest_number = max(highest_number, number)

        return highest_number

    def __get_placeholder_maps(self):
        """
        Distributes the floating molecule designs over the ISOs.
        """
        placeholder_maps = dict()

        for iso_count, candidate_map in self.__floating_selection.iteritems():
            placeholder_map = dict()
            floating_counter = 0

            for pool_id in candidate_map.keys():
                floating_counter += 1
                placeholder = '%s%03i' % (IsoParameters.FLOATING_INDICATOR,
                                          floating_counter)
                placeholder_map[placeholder] = pool_id
            placeholder_maps[iso_count] = placeholder_map

        return placeholder_maps

    def __create_iso(self, latest_iso_number, iso_count, placeholder_map,
                     candidate_map):
        """
        Creates an ISO.
        """
        prep_layout = self.__create_prep_layout_for_iso(placeholder_map,
                                                                candidate_map)
        label = self._create_iso_label(latest_iso_number, iso_count)
        self.__prep_layout_map[label] = prep_layout # for report
        self.__iso_selections[label] = candidate_map # for report
        pool_set = self.__create_pool_set(candidate_map)

        iso = Iso(label=label,
                      iso_request=self.iso_request,
                      molecule_design_pool_set=pool_set,
                      optimizer_excluded_racks=self.excluded_racks,
                      optimizer_required_racks=self.requested_tubes,
                      rack_layout=prep_layout.create_rack_layout())

        prep_label = 'p_%s' % (label)
        prep_plate = self._prep_plate_specs.create_rack(label=prep_label,
                                        status=get_item_status_future())
        IsoPreparationPlate(iso=iso, plate=prep_plate)
        self.__isos.append(iso)

    def __create_prep_layout_for_iso(self, placeholder_map,
                                     floating_candidate_map):
        """
        Creates a converted preparation layout for the given placeholder map.
        """
        prep_layout = PrepIsoLayout(shape=self._raw_prep_layout.shape)

        for prep_pos in self._raw_prep_layout.working_positions():
            if prep_pos.is_mock:
                prep_layout.add_position(prep_pos)
                continue
            elif prep_pos.is_floating:
                placeholder = prep_pos.molecule_design_pool_id
                if not placeholder_map.has_key(placeholder): continue
                pool_id = placeholder_map[placeholder]
                candidate = floating_candidate_map[pool_id]
                pool = self._floating_pools[pool_id]
            else:
                pool = prep_pos.molecule_design_pool
                candidate = self.__fixed_selection[pool.id]
            completed_pos = prep_pos.get_completed_copy(
                            stock_tube_barcode=candidate.container_barcode,
                            stock_rack_barcode=candidate.rack_barcode,
                            molecule_design_pool=pool)
            prep_layout.add_position(completed_pos)

        return prep_layout

    def _create_iso_label(self, highest_number, iso_count):
        """
        Creates a label for a new ISO.
        """
        iso_number = highest_number + iso_count
        ticket_number = self.iso_request.experiment_metadata.ticket_number
        label = '%i%siso%i' % (ticket_number, self.SEPARATING_CHAR, iso_number)
        return label

    def __create_pool_set(self, candidate_map):
        """
        Creates a molecule design pool set for an ISO.
        """
        if len(candidate_map) < 1:
            return None

        md_type = self.iso_request.experiment_metadata \
                      .molecule_design_pool_set.molecule_type
        md_pools = set()
        for pool_id in candidate_map.keys():
            md_pool = self._floating_pools[pool_id]
            md_pools.add(md_pool)

        pool_set = MoleculeDesignPoolSet(molecule_type=md_type,
                                         molecule_design_pools=md_pools)
        return pool_set

    def __create_worklist_series(self):
        """
        Generates the ISO processing worklist series if there is not any so far.
        """
        self.add_debug('Create ISO worklist series ...')

        if self.iso_request.worklist_series is None:
            series_generator = IsoWorklistSeriesGenerator(log=self.log,
                                    iso_request=self.iso_request,
                                    preparation_layout=self._raw_prep_layout)
            series = series_generator.get_result()

            if series is None:
                msg = 'Error when trying to generate worklist series for ' \
                      'ISO request.'
                self.add_error(msg)
            elif len(series) < 1 and \
                        self._experiment_type.id == EXPERIMENT_SCENARIOS.MANUAL:
                pass
            else:
                self.iso_request.worklist_series = series

        if self._experiment_type.id == EXPERIMENT_SCENARIOS.MANUAL:
            # there should be only one new ISO
            new_iso = self.__isos[0]
            self._adjust_manual_prep_plate_labels(new_iso)

    def _adjust_manual_prep_plate_labels(self, new_iso): #pylint: disable=W0613
        """
        In case of manual experiment it can be that the preparation plate
        is already the final cell plate. In this case, we want the
        plates to have to set plate set labels instead of the preparation
        plate labels.
        """
        self.add_error('Abstract method: _adjust_manual_prep_plate_labels()')

    def __look_for_compounds(self):
        """
        Compounds designs have different stock concentrations, thus it might
        be we produce incorrect ISO concentrations.
        """
        has_compounds = False
        for prep_pos in self._raw_prep_layout.working_positions():
            if not prep_pos.is_fixed: continue
            if prep_pos.molecule_design_pool.molecule_type.id \
                                            == MOLECULE_TYPE_IDS.COMPOUND:
                has_compounds = True
                break

        if has_compounds:
            msg = 'Attention! There are compound pools among the molecule ' \
                  'design pool IDs. For compounds in floating positions, we ' \
                  'assume a stock concentration of %s nM. Please make sure, ' \
                  'that this is the correct stock concentration for every ' \
                  'compound on this plate because otherwise you might ' \
                  'receive a deviating concentration.' % ('{0:,}'.format(
                  STOCK_CONCENTRATIONS.COMPOUND_STOCK_CONCENTRATION))
            self.add_warning(msg)


class IsoGenerator(IsoCreator):
    """
    This tool generates new ISOs for an ISO request.

    **Return Value:** The new ISOs.
    """

    NAME = 'ISO Generator'

    def __init__(self, iso_request, number_isos,
                       excluded_racks=None, requested_tubes=None,
                       logging_level=logging.WARNING,
                       add_default_handlers=False):
        """
        Constructor:

        :param iso_request: The ISO request containing the ISO layout for the
            ISO (and experiment plan with the molecule design pools).
        :type iso_request: :class:`thelma.models.iso.IsoRequest`

        :param number_isos: The number of ISOs ordered.
        :type number_isos: :class:`int`

        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for molecule design picking.
        :type excluded_racks: A list of rack barcodes

        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of tube barcodes.

        :param logging_level: the desired minimum log level
        :type log_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """
        IsoCreator.__init__(self, iso_request=iso_request,
                            number_isos=number_isos,
                            excluded_racks=excluded_racks,
                            requested_tubes=requested_tubes,
                            logging_level=logging_level,
                            add_default_handlers=add_default_handlers)

    def _determine_prep_plate_specs(self):
        """
        Determines the plate specs for the ISO preparation plates.
        """
        self.add_debug('Determine preparation plate specs ...')

        if self._raw_prep_layout.shape.name == RACK_SHAPE_NAMES.SHAPE_384:
            prep_rs = get_reservoir_specs_standard_384()
        elif self._experiment_type.id == EXPERIMENT_SCENARIOS.MANUAL:
            prep_rs = get_reservoir_specs_standard_96()
        else:
            prep_rs = get_reservoir_specs_standard_96()
            max_req_volume = 0
            for prep_pos in self._raw_prep_layout.working_positions():
                max_req_volume = max(max_req_volume, prep_pos.required_volume)
            max_rs_vol = prep_rs.max_volume * VOLUME_CONVERSION_FACTOR
            if max_req_volume > max_rs_vol:
                prep_rs = get_reservoir_specs_deep_96()

        self._prep_plate_specs = PLATE_SPECS_NAMES.from_reservoir_specs(prep_rs)

    def _find_floating_molecule_design_pools(self):
        """
        Collects the queued floating molecule design pools.
        """
        used_pools = set()
        for iso in self.iso_request.isos:
            if iso.status == ISO_STATUS.CANCELLED: continue
            for md_pool in iso.molecule_design_pool_set:
                used_pools.add(md_pool)

        for md_pool in \
                self.iso_request.experiment_metadata.molecule_design_pool_set:
            if not md_pool in used_pools:
                self._floating_pools[md_pool.id] = md_pool

        if self._number_floatings > 0 and len(self._floating_pools) < 1:
            msg = 'There are no unused molecule design pools left for the ' \
                  'floating positions!'
            self.add_error(msg)

    def _adjust_manual_prep_plate_labels(self, new_iso):
        new_iso.preparation_plate.label = self.iso_request.plate_set_label


class IsoRescheduler(IsoCreator):
    """
    This tool re-creates a group of existing ISOs. The optimizer is rerun,
    thus, the distribution of ISO might differ.

    **Return Value:** The new ISOs.
    """

    NAME = 'ISO Rescheduler'

    def __init__(self, iso_request, isos_to_copy,
                       excluded_racks=None, requested_tubes=None,
                       logging_level=logging.WARNING,
                       add_default_handlers=False):
        """
        Constructor:

        :param iso_request: The ISO request containing the ISO layout for the
            ISO (and experiment plan with the molecule design pools).
        :type iso_request: :class:`thelma.models.iso.IsoRequest`

        :param isos_to_copy: The ISOs to copy.
        :type isos_to_copy: :class:`list` of :class:`Iso` objects

        :param excluded_racks: A list of barcodes from stock racks that shall
            not be used for molecule design picking.
        :type excluded_racks: A list of rack barcodes

        :param requested_tubes: A list of barcodes from stock tubes that are
            supposed to be used.
        :type requested_tubes: A list of tube barcodes.

        :param logging_level: the desired minimum log level
        :type log_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *False*
        """
        if isinstance(isos_to_copy, list):
            number_isos = len(isos_to_copy)
        else:
            number_isos = 0
            # The error be recorded later.

        IsoCreator.__init__(self, iso_request=iso_request,
                                number_isos=number_isos,
                                excluded_racks=excluded_racks,
                                requested_tubes=requested_tubes,
                                logging_level=logging_level,
                                add_default_handlers=add_default_handlers)

        #: The ISOs to copy.
        self.isos_to_copy = isos_to_copy

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        IsoCreator._check_input(self)

        if self._check_input_class('ISO list', self.isos_to_copy, list):
            for iso in self.isos_to_copy:
                if not self._check_input_class('ISO', iso, Iso): break

    def _determine_prep_plate_specs(self):
        """
        Determines the plate specs for the ISO preparation plates.
        """
        self.add_debug('Determine preparation plate specs ...')

        no_prep_plate = []

        plate_specs = set()
        for iso in self.isos_to_copy:
            prep_plate = iso.preparation_plate
            if prep_plate is None:
                no_prep_plate.append(iso.label)
                continue
            plate_specs.add(prep_plate.specs)

        if len(no_prep_plate) > 0:
            msg = 'Some of the ISOs to copy to not have a preparation plate!'
            self.add_error(msg)
        elif len(plate_specs) > 1:
            msg = 'The ISOs to copy have different preparation plate ' \
                  'specs: %s!' % (list(plate_specs))
            self.add_error(msg)
        else:
            self._prep_plate_specs = list(plate_specs)[0]

    def _find_floating_molecule_design_pools(self):
        """
        Collects the queued floating molecule design pools.
        """
        for iso in self.isos_to_copy:
            for md_pool in iso.molecule_design_pool_set:
                self._floating_pools[md_pool.id] = md_pool

    def _create_iso_label(self, highest_number, iso_count):
        """
        Creates a label for a new ISO.
        """
        label = IsoCreator._create_iso_label(self, highest_number, iso_count)
        copy_label = '%s%s%s' % (label, self.SEPARATING_CHAR, self.COPY_MARKER)
        return copy_label

    def _adjust_manual_prep_plate_labels(self, new_iso):
        new_iso.preparation_plate.label = new_iso.label
