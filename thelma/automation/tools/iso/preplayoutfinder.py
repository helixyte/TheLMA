"""
This tool in this module creates a ISO Preparation Plate from a
ISO layout.
"""
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.iso.prep_utils import PrepIsoLayout
from thelma.automation.tools.iso.prep_utils import PrepIsoParameters
from thelma.automation.tools.iso.prep_utils import PrepIsoPosition
from thelma.automation.tools.utils.base import is_larger_than
from thelma.automation.tools.semiconstants \
        import get_reservoir_specs_standard_384
from thelma.automation.tools.semiconstants \
        import get_reservoir_specs_standard_96
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import PIPETTING_SPECS_NAMES
from thelma.automation.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.tools.semiconstants import get_min_transfer_volume
from thelma.automation.tools.semiconstants import get_positions_for_shape
from thelma.automation.tools.stock.base import STOCK_MIN_TRANSFER_VOLUME
from thelma.automation.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import MOCK_POSITION_TYPE
from thelma.automation.tools.utils.base import TransferTarget
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import add_list_map_element
from thelma.automation.tools.utils.base import get_trimmed_string
from thelma.automation.tools.utils.base import round_up
from thelma.automation.tools.utils.base import sort_rack_positions
from thelma.automation.tools.utils.iso import IsoRequestAssociationData
from thelma.automation.tools.utils.iso import IsoRequestLayout
from thelma.automation.tools.utils.iso import IsoRequestValueDeterminer
from thelma.automation.tools.utils.racksector import QuadrantIterator
from thelma.automation.tools.worklists.base import EmptyPositionManager
from thelma.automation.tools.worklists.base import get_dynamic_dead_volume
from thelma.models.iso import IsoRequest
from thelma.models.moleculedesign import MoleculeDesignPool


__docformat__ = 'reStructuredText en'
__all__ = ['_get_finder_class',
           'PrepLayoutFinder',
           'PreparationEmptyPositionManager',
           'PrepLayoutFinder96',
           'PrepLayoutFinder348',
           'PrepLayoutFinder384Optimisation',
           'PrepLayoutFinder384Screening',
           'PrepLayoutFinderManual',
           'PrepLayoutFinderOrderOnly']


def _get_finder_class(rack_shape_name, experiment_type):
    """
    A lookup function returning the finder class for the given parameters.

    :param rack_shape_name: The name of the ISO layout format.
    :type rack_shape_name:
        value of :class:`thelma.automation.tools.semiconstants.RACK_SHAPE_NAMES`

    :param experiment_type: The experiment metadata type.
    :type experiment_type:
        :class:`thelma.models.experiment.ExperimentMetadataType`

    :raises ValueError: If experiment type or rack shape name are unknown.
    """

    if not RACK_SHAPE_NAMES.is_known_entity(rack_shape_name):
        raise ValueError('Unknown rack shape name "%s"' % (rack_shape_name))
    if not experiment_type.id in _SUPPORTED_EXPERIMENT_TYPES:
        raise ValueError('Unsupported experiment type "%s"' % (experiment_type))

    if experiment_type.id == EXPERIMENT_SCENARIOS.MANUAL:
        return PrepLayoutFinderManual
    elif experiment_type.id == EXPERIMENT_SCENARIOS.ORDER_ONLY:
        return PrepLayoutFinderOrderOnly
    elif rack_shape_name == RACK_SHAPE_NAMES.SHAPE_96:
        return PrepLayoutFinder96
    elif experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
        return PrepLayoutFinder384Screening
    else:
        return PrepLayoutFinder384Optimisation


class PrepLayoutFinder(BaseAutomationTool):
    """
    This tool generates a ISO preparation layout (:class:`PrepIsoLayout`)
    from an ISO layout.
    """
    NAME = 'Preparation ISO Layout Finder'

    #: Name of the rack shape that is supported by this preparation layout
    #: finder.
    RACK_SHAPE_NAME = None

    def __init__(self, iso_layout, iso_request, log):
        """
        Constructor:

        :param iso_layout: The layout for the ISO.
        :type iso_layout: :class:`thelma.automation.tools.utils.iso.IsoLayout`

        :param iso_request: The ISO request for which the layout is created.
        :type iso_request: :class:`thelma.models.iso.IsoRequest`

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        BaseAutomationTool.__init__(self, log=log)

        #: The layout for the ISO
        #: (:class:`thelma.automation.tools.utils.iso.IsoLayout`).
        self.iso_layout = iso_layout
        #: The ISO request for which the layout is created.
        self.iso_request = iso_request

        #: Maps ISO positions on molecule design pools.
        self._pool_map = None
        #: The reservoir specs of the preparation plate.
        self._reservoir_specs = None

        #: The ISO preparation layout to fill.
        self._prep_layout = None

        #: The number of aliquots that has been ordered for this ISO request.
        self._number_aliquots = None

        #: The empty position manager (required for additional positions in
        #: case of great dilution factors). The manager is initialised lazy.
        self.__empty_pos_manager = None

    def reset(self):
        """
        Resets all attributes except for the initialisation values.
        """
        BaseAutomationTool.reset(self)
        self._pool_map = dict()
        self._reservoir_specs = None
        self._prep_layout = None
        self._number_aliquots = None
        self.__empty_pos_manager = None

    @classmethod
    def create(cls, iso_layout, iso_request, log):
        """
        Creates a preparation layout finder for the given experiment type
        and ISO layout format.
        """
        try:
            finder_cls = _get_finder_class(
                rack_shape_name=iso_layout.shape.name,
                experiment_type=iso_request.experiment_metadata_type)
        except ValueError as e:
            log.add_error(e)
            result = None
        except AttributeError as e:
            log.add_error(e)
            result = None
        else:
            kw = dict(iso_layout=iso_layout, iso_request=iso_request, log=log)
            result = finder_cls(**kw)
        return result

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start preparation layout generation ...')

        self.__check_input()
        if not self.has_errors(): self.__check_rack_shape()
        if not self.has_errors():
            self._set_reservoir_specs()
            self._set_other_metadata()
            self.__initialize_layout()
            self.__init_pool_map()
        if not self.has_errors(): self._fill_layout()
        if not self.has_errors(): self._check_layout_consistency()
        if not self.has_errors(): self._adjust_starting_well_volumes()
        if not self.has_errors():
            self.return_value = self._prep_layout
            self.add_info('Preparation layout generation completed.')

    def __check_input(self):
        """
        Checks the input values.
        """
        self.add_debug('Check input values ...')

        self._check_input_class('ISO layout', self.iso_layout, IsoRequestLayout)
        self._check_input_class('ISO request', self.iso_request, IsoRequest)

    def __check_rack_shape(self):
        """
        Checks whether the ISO layout has the expected rack shape.
        """
        self.add_debug('Check rack shape ...')

        if not self.iso_layout.shape.name == self.RACK_SHAPE_NAME:
            msg = 'Unsupported rack shape "%s".' % (self.iso_layout.shape)
            self.add_error(msg)

    def _set_reservoir_specs(self):
        """
        Sets the reservoir specs.
        """
        self.add_error('Abstract method: set_reservoir_specs()')

    def _set_other_metadata(self):
        """
        Sets other rack-shape-independent ISO request metadata (stock
        concentration for floating positions and number of aliquots).
        """
        if self.iso_layout.has_floatings():
            pool_set = \
                self.iso_request.experiment_metadata.molecule_design_pool_set
            if pool_set is None or len(pool_set) < 1:
                msg = 'There are no molecule design pools in the molecule ' \
                      'design pool set although there are floating positions!'
                self.add_error(msg)
            else:
                # We cannot use the molecule type, because the stock
                # concentration also depends on the number of designs.
                # The stock concentration must be equal for all members of the
                # set therefore we can pick an arbitrary member.
                for pool in pool_set:
                    stock_conc = pool.default_stock_concentration \
                                 * CONCENTRATION_CONVERSION_FACTOR
                    self.iso_layout.set_floating_stock_concentration(stock_conc)
                    break

        self._number_aliquots = self.iso_request.number_aliquots

    def __initialize_layout(self):
        """
        Initialises the preparation layout.
        """
        self._prep_layout = PrepIsoLayout(shape=self.iso_layout.shape)
        floating_stock_conc = self.iso_layout.floating_stock_concentration
        if floating_stock_conc is not None:
            self._prep_layout.set_floating_stock_concentration(
                                                        floating_stock_conc)

    def __init_pool_map(self):
        """
        The pool map stores the ISO positions for each pool.
        """
        self.add_debug('Initialise molecule design map ...')

        for iso_pos in self.iso_layout.working_positions():
            if iso_pos.is_empty: continue

            pool = iso_pos.molecule_design_pool
            if not isinstance(pool, (basestring, MoleculeDesignPool)):
                msg = 'Unexpected molecule design type: %s (type: %s)!' \
                       % (pool, pool.__class__.__name__)
                self.add_error(msg)
                break
            add_list_map_element(self._pool_map, pool, iso_pos)

    def _fill_layout(self):
        """
        Fills the layout
        """
        self.add_debug('Fill preparation layout ...')

        all_conc_maps = dict()
        # In order to create prep position we must have all concentration
        # maps (because we must know, whether there are position to be added).
        for pool, iso_pos_list in self._pool_map.iteritems():
            conc_map = self._get_concentration_map(iso_pos_list)
            if conc_map is None: break
            all_conc_maps[pool] = conc_map

        self._create_preparation_positions(all_conc_maps)

    #pylint: disable=W0613
    def _create_preparation_positions(self, all_concentration_maps):
        """
        Overwrite this method to create the preparation positions for the
        layout.
        """
        self.add_error('Abstract method: _create_preparation_positions()')
    #pylint: enable=W0613

    def _get_concentration_map(self, iso_pos_list):
        """
        Fetches the concentration map (ISO positions mapped on concentrations)
        for the ISO positions of *one* molecule design pool.
        If the dilutions factors between two dilutions are too large,
        the method will insert an position.
        """
        concentration_too_high = []
        stock_conc = None

        # Record ISO positions
        conc_map = dict()
        for iso_pos in iso_pos_list:
            if stock_conc is None:
                stock_conc = self._get_stock_concentration(iso_pos)
            iso_concentration = iso_pos.iso_concentration
            if not iso_pos.is_mock:
                if is_larger_than(iso_concentration, stock_conc):
                    info = '%s (%s nM, stock: %s nM) ' \
                            % (iso_pos.rack_position.label,
                               get_trimmed_string(iso_concentration),
                               get_trimmed_string(stock_conc))
                    concentration_too_high.append(info)
                    continue
            add_list_map_element(conc_map, iso_concentration, iso_pos)

        if len(concentration_too_high) > 0:
            concentration_too_high.sort()
            msg = 'Some ISO concentrations exceed the stock concentration ' \
                  'for the referring molecule type: %s.' \
                  % (concentration_too_high)
            self.add_error(msg)
            return None

        conc_map = self.__check_dilution_factors(conc_map, stock_conc)
        return conc_map

    def _get_stock_concentration(self, pool_pos):
        """
        Returns the stock concentration for the passed molecule design
        pool position.
        """
        if pool_pos.is_mock: return None
        if pool_pos.is_floating:
            return self.iso_layout.floating_stock_concentration

        return pool_pos.stock_concentration

    def __check_dilution_factors(self, conc_map, stock_conc):
        """
        Checks the dilution factor in a concentration map and inserts
        additional positions, if necessary.
        """
        if conc_map is None: return None

        last_conc = stock_conc
        for prep_conc in sorted(conc_map, reverse=True):
            if PrepIsoParameters.is_valid_mock_value(prep_conc): break
            dil_factor = last_conc / prep_conc
            # TODO: replace with pipetting specs
            max_dil_factor = PrepIsoParameters.MAX_DILUTION_FACTOR_BIOMEK
            if dil_factor > max_dil_factor:
                intermediate_conc = last_conc / max_dil_factor
                conc_map[intermediate_conc] = None
                if self.__empty_pos_manager is None:
                    self.__empty_pos_manager = \
                            PreparationEmptyPositionManager(self.iso_layout)
            last_conc = prep_conc

        return conc_map

    def _create_prep_positions_for_pool(self, pool, iso_conc_map,
                                        min_transfer_volume):
        """
        Determines required volumes and child positions for control positions
        and optimisation floating positions sharing a molecule design.
        """
        concentrations = iso_conc_map.keys()
        concentrations.sort()

        last_prep_pos = None

        for conc in concentrations:
            iso_positions = iso_conc_map[conc]

            if iso_positions is None:
                number_target_wells = 0
            else:
                number_target_wells = len(iso_positions)
            original_dead_volume = get_dynamic_dead_volume(
                                target_well_number=number_target_wells,
                                reservoir_specs=self._reservoir_specs)
            required_volume = original_dead_volume

            # get the volume required for this concentration
            if iso_positions is None:
                # auxiliary position
                transfer_targets = []
                # pass str(pool) to get the ID for pools and do not cause
                # errors for strings
                rack_pos = self.__get_auxiliary_rack_position(str(pool))
                if rack_pos is None: break
            else:
                transfer_targets = []
                rack_positions = dict()
                for iso_pos in iso_positions:
                    rack_pos = iso_pos.rack_position
                    rack_positions[rack_pos.label] = rack_pos
                    add_volume = iso_pos.iso_volume * self._number_aliquots
                    required_volume += add_volume
                    tt = TransferTarget(rack_position=rack_pos,
                                        transfer_volume=iso_pos.iso_volume)
                    transfer_targets.append(tt)
                # get one rack position for preparation position
                labels = rack_positions.keys()
                labels.sort()
                rack_pos = rack_positions[labels.pop(0)]
                # Add unused positions as empty.
                if not self.__empty_pos_manager is None:
                    for label in labels:
                        self.__empty_pos_manager.add_empty_position(
                                                        rack_positions[label])

            pos_type = PrepIsoParameters.get_position_type(pool)
            # we can determine the position type this way because floatings
            # have not been converted yet
            prep_pos = PrepIsoPosition(rack_position=rack_pos,
                        molecule_design_pool=pool,
                        position_type=pos_type,
                        prep_concentration=conc,
                        required_volume=required_volume,
                        transfer_targets=transfer_targets)

            # if there is a child well, adjust volume and link
            if not last_prep_pos is None:

                # increase dead volume if necessary
                number_target_wells += 1
                new_dead_volume = get_dynamic_dead_volume(
                                    target_well_number=number_target_wells,
                                    reservoir_specs=self._reservoir_specs)
                if not new_dead_volume == original_dead_volume:
                    required_volume = required_volume - original_dead_volume \
                                      + new_dead_volume
                    prep_pos.required_volume = required_volume

                # check and adjust donation volume
                dil_factor = conc / last_prep_pos.prep_concentration
                donation_volume = last_prep_pos.required_volume / dil_factor
                if donation_volume < min_transfer_volume:
                    donation_volume = min_transfer_volume
                donation_volume = round_up(donation_volume, decimal_places=1)
                last_prep_pos.required_volume = round_up(
                                                donation_volume * dil_factor)
                prep_pos.required_volume += donation_volume

                # set parent well
                last_prep_pos.parent_well = prep_pos.rack_position

            # store positions
            last_prep_pos = prep_pos
            self._prep_layout.add_position(prep_pos)

    def __get_auxiliary_rack_position(self, pool_id):
        """
        Creates an additional preparation position and adjusts the
        parent wells and volumes of the
        """
        rack_pos = self.__empty_pos_manager.get_position_for_pool(pool_id)
        if rack_pos is None:
            msg = 'Error when trying to generate additional position ' \
                  'for pool %s. ' % (pool_id)
            if not self.__empty_pos_manager.has_empty_positions():
                msg += 'There are no empty positions left in the preparation ' \
                       'layout!'
            self.add_error(msg)

        return rack_pos

    def _create_prep_pos_for_mock(self, iso_conc_map):
        """
        Create a preparation position for the mock molecule design.
        """
        transfer_targets = []

        all_iso_positions = []
        for iso_pos_list in iso_conc_map.values():
            for iso_pos in iso_pos_list: all_iso_positions.append(iso_pos)

        required_volume = get_dynamic_dead_volume(len(all_iso_positions),
                                                  self._reservoir_specs)
        rack_positions = dict()

        for iso_pos in all_iso_positions:
            add_volume = iso_pos.iso_volume * self._number_aliquots
            required_volume += add_volume
            rack_pos = iso_pos.rack_position
            tt = TransferTarget(rack_position=rack_pos,
                                transfer_volume=iso_pos.iso_volume)
            transfer_targets.append(tt)
            rack_positions[rack_pos.label] = rack_pos

        # get one rack position for preparation position
        labels = rack_positions.keys()
        labels.sort()
        rack_pos = rack_positions[labels.pop(0)]
        # Add unused positions as empty.
        if not self.__empty_pos_manager is None:
            for label in labels:
                self.__empty_pos_manager.add_empty_position(
                                                        rack_positions[label])

        # Store position
        prep_pos = PrepIsoPosition.create_mock_position(
                                            rack_position=rack_pos,
                                            required_volume=required_volume,
                                            transfer_targets=transfer_targets)
        self._prep_layout.add_position(prep_pos)

    def _check_layout_consistency(self):
        """
        Performs some layout consistency checks.
        """
        starting_wells = self._prep_layout.get_starting_wells()
        starting_pool_ids = set()
        for prep_pos in starting_wells.values():
            starting_pool_ids.add(prep_pos.molecule_design_pool_id)
        exp_ids = set()
        for prep_pos in self._prep_layout.working_positions():
            if not prep_pos.molecule_design_pool_id in exp_ids:
                exp_ids.add(prep_pos.molecule_design_pool_id)
        missing_pool_ids = []
        for pool_id in exp_ids:
            if not pool_id in starting_pool_ids:
                missing_pool_ids.append(pool_id)
        if len(missing_pool_ids) > 0:
            msg = 'The following molecule design pools do not have a starting ' \
                  'well %s. This is a programming error. Please contact ' \
                  'the IT department!'
            self.add_error(msg)

    def _adjust_starting_well_volumes(self):
        """
        Adjusts the required volumes of the starting wells regarding the
        minimum volume that can be taken out of stock.
        """
        self.add_error('Abstract method: _adjust_starting_well_volumes()')

    def _adjust_volume_for_starting_well(self, prep_pos, min_starting_volume):
        """
        Adjusts the required volumes of the given starting wells regarding the
        minimum volume that can be taken out of stock.
        """
        stock_conc = self._get_stock_concentration(prep_pos)

        dil_factor = stock_conc / prep_pos.prep_concentration
        take_out_volume = prep_pos.required_volume / dil_factor
        take_out_volume = round_up(take_out_volume)
        if take_out_volume < min_starting_volume:
            take_out_volume = min_starting_volume
        adj_req_volume = take_out_volume * dil_factor
        adj_req_volume = round(adj_req_volume, 1)
        prep_pos.required_volume = adj_req_volume


class PreparationEmptyPositionManager(EmptyPositionManager):
    """
    Stores the empty positions of an ISO layout and returns and removes
    them on request (depending on molecule design and/or preferred column).
    """

    def __init__(self, iso_layout):
        """
        Constructor:

        :param iso_layout: The ISO layout whose empty positions
            shall be managed.
        :type iso_layout:
            :class:`thelma.automation.tools.utils.iso.IsoLayout`
        """
        EmptyPositionManager.__init__(self, rack_shape=iso_layout.shape)

        #: Stores the column indices a molecule design occurs in.
        self.__pool_col_map = dict()
        #: Stores the empty rack positions for a column index.
        self.__col_map = dict()
        #: Contains all columns that are completely empty.
        self.__empty_columns = []

        self.__init_maps(iso_layout)

    def _init_empty_positions(self):
        """
        Initialises the maps.
        """
        pass

    def get_position_for_pool(self, pool_id):
        """
        Returns a empty position (or None, if there is none left). Positions
        in the same column as the other non-empty positions with the
        same molecule design pool ID are preferred.

        :param pool_id: The molecule design pool ID the of the preparation
            position to be.
        :raises ValueError: If you pass a molecule design pool that does not
            occur in the ISO layout.
        :rtype: :class:`thelma.models.rack.RackPosition`
        """
        if not self.has_empty_positions(): return None
        if not self.__pool_col_map.has_key(str(pool_id)):
            raise ValueError('Unknown molecule design pool ID %s.' % (pool_id))

        rack_pos = self.__pick_position(str(pool_id))
        self.__remove_position_from_pool(rack_pos)

        return rack_pos

    def get_empty_position(self):
        """
        Returns the position with the lowest column and row index.
        """
        raise NotImplementedError('Use get_position_for_pool_id() instead.')

    def add_empty_position(self, rack_pos):
        """
        Adds an empty position (corresponds to an unused ISO position).

        :param rack_pos: The new empty rack pos.
        :type rack_pos: :class:`thelma.models.rack.RackPosition`
        """
        self._all_empty_positions.add(rack_pos)
        col_index = rack_pos.column_index

        if not self.__col_map.has_key(col_index):
            self.__col_map[col_index] = []
        self.__col_map[col_index].append(rack_pos)

    def __init_maps(self, iso_layout):
        """
        Initialises the maps.
        """
        non_empty_columns = set()

        for rack_pos in get_positions_for_shape(iso_layout.shape):
            iso_pos = iso_layout.get_working_position(rack_pos)
            col_index = rack_pos.column_index

            if iso_pos is None or iso_pos.is_empty: # empty position
                self._all_empty_positions.add(rack_pos)
                if not self.__col_map.has_key(col_index):
                    self.__col_map[col_index] = []
                self.__col_map[col_index].append(rack_pos)

            else:
                non_empty_columns.add(col_index)
                pool_id = str(iso_pos.molecule_design_pool_id)
                if not self.__pool_col_map.has_key(pool_id):
                    self.__pool_col_map[pool_id] = []
                if not col_index in self.__pool_col_map[pool_id]:
                    self.__pool_col_map[pool_id].append(col_index)

        for col_index in range(iso_layout.shape.number_columns):
            if not col_index in non_empty_columns:
                self.__empty_columns.append(col_index)

    def __pick_position(self, pool_id):
        """
        Picks and returns a position for a molecule design pool ID.
        """
        col_indices = self.__pool_col_map[pool_id]
        for col_index in col_indices:
            if self.__col_map.has_key(col_index):
                col_pos_list = sort_rack_positions(self.__col_map[col_index])
                return col_pos_list[-1]

        for col_index in self.__empty_columns:
            if self.__col_map.has_key(col_index):
                col_pos_list = sort_rack_positions(self.__col_map[col_index])
                return col_pos_list[-1]

        return list(self._all_empty_positions)[-1]

    def __remove_position_from_pool(self, rack_pos):
        """
        Removes all references from a picked from the pool of
        available position.
        """
        col_index = rack_pos.column_index

        self._all_empty_positions.discard(rack_pos)

        col_pos_list = self.__col_map[col_index]
        col_list_index = col_pos_list.index(rack_pos)
        del col_pos_list[col_list_index]
        if len(col_pos_list) < 1:
            del self.__col_map[col_index]
            if col_index in self.__empty_columns:
                empty_col_index = self.__empty_columns.index(col_index)
                del self.__empty_columns[empty_col_index]


class PrepLayoutFinder96(PrepLayoutFinder):
    """
    This tool generates a ISO preparation layout (:class:`PrepIsoLayout`)
    from a 96-well ISO layout.

    The tool will generate an layout in \'INI\' state that meaning each
    molecule design has to be unique in the final layout. The ISO concentration,
    ISO volumes and required volumes of the remaining well will be stored in
    the child wells.
    """

    RACK_SHAPE_NAME = '8x12'

    def __init__(self, iso_layout, iso_request, log):
        """
        Constructor:

        :param iso_layout: The layout for the ISO.
        :type iso_layout: :class:`thelma.automation.tools.utils.iso.IsoLayout`

        :param iso_request: The ISO request for which the layout is created.
        :type iso_request: :class:`thelma.models.iso.IsoRequest`

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        PrepLayoutFinder.__init__(self, log=log, iso_layout=iso_layout,
                                  iso_request=iso_request)

    def _set_reservoir_specs(self):
        """
        Sets the reservoir specs.
        """
        self._reservoir_specs = get_reservoir_specs_standard_96()

    def _create_preparation_positions(self, all_concentration_maps):
        """
        Overwrite this method to create the preparation positions for the
        layout.
        """
        min_vol = get_min_transfer_volume(PIPETTING_SPECS_NAMES.BIOMEK)

        for pool, conc_map in all_concentration_maps.iteritems():
            if pool == MOCK_POSITION_TYPE:
                self._create_prep_pos_for_mock(conc_map)
            else:
                self._create_prep_positions_for_pool(pool, conc_map, min_vol)
            if self.has_errors(): break

        self.__adjust_buffer_volumes()

    def __adjust_buffer_volumes(self):
        """
        Adjusts the required volumes of all wells regarding the buffer volume
        (minimum volume that can be transferred by the BioMek).
        """
        self.add_debug('Adjust buffer volumes ...')

        min_vol = get_min_transfer_volume(PIPETTING_SPECS_NAMES.BIOMEK)

        md_conc_map = self._prep_layout.get_md_pool_concentration_map()
        for conc_map in md_conc_map.values():

            concentrations = conc_map.keys()
            concentrations.sort()
            for i in range(len(concentrations)):
                conc = concentrations[i]
                prep_pos = conc_map[conc]
                if prep_pos.is_mock: continue
                parent_pos = None
                # the vol for mocks is always over the the min because all
                # liquid is buffer and the total volume includes the dead vol
                if prep_pos.parent_well is None:
                    parent_conc = self._get_stock_concentration(prep_pos)
                else:
                    parent_conc = concentrations[i + 1]
                    parent_pos = conc_map[parent_conc]

                dil_factor = parent_conc / conc
                old_donation_vol = prep_pos.required_volume / dil_factor
                buffer_vol = prep_pos.required_volume - old_donation_vol
                if buffer_vol < min_vol and not buffer_vol == 0:
                    corr_factor = min_vol / buffer_vol
                    new_donation_vol = old_donation_vol * corr_factor
                    new_donation_vol = round_up(new_donation_vol, 1)
                    adj_req_vol = new_donation_vol * dil_factor
                    adj_req_vol = round(adj_req_vol, 1)
                    prep_pos.required_volume = adj_req_vol
                    if not parent_pos is None:
                        parent_req_vol = parent_pos.required_volume
                        parent_req_vol -= old_donation_vol
                        parent_req_vol += new_donation_vol
                        parent_req_vol = round_up(parent_req_vol, 1)
                        parent_pos.required_volume = parent_req_vol

    def _check_layout_consistency(self):
        """
        Performs some layout consistency checks.
        """
        PrepLayoutFinder._check_layout_consistency(self)

        if not self._prep_layout.check_starting_well_uniqueness():
            msg = 'Some starting positions in the preparation layout have ' \
                  'duplicate molecule design IDs. This is programming error. ' \
                  'Contact the IT department, please.'
            self.add_error(msg)

    def _adjust_starting_well_volumes(self):
        """
        Adjusts the required volumes of the starting wells regarding the
        minimum volume that can be taken out of stock.
        """
        self.add_debug('Adjust starting well volumes ...')

        min_starting_volume = STOCK_MIN_TRANSFER_VOLUME

        for prep_pos in self._prep_layout.get_starting_wells().values():
            if prep_pos.is_mock: continue
            self._adjust_volume_for_starting_well(prep_pos, min_starting_volume)


class PrepLayoutFinder348(PrepLayoutFinder):
    """
    An abstract preparation layout finder for 384 well ISO layouts.
    """

    RACK_SHAPE_NAME = '16x24'

    def _set_reservoir_specs(self):
        """
        Sets the reservoir specs.
        """
        self._reservoir_specs = get_reservoir_specs_standard_384()


class PrepLayoutFinder384Optimisation(PrepLayoutFinder348):
    """
    A preparation layout finder for 384-well ISOs in optimisation scenarios.
    Only fixed positions are allowed.
    """

    NAME = 'Preparation ISO Layout Finder 384-well Opti'

    def _create_preparation_positions(self, all_concentration_maps):
        """
        Overwrite this method to create the preparation positions for the
        layout.
        """
        min_vol = get_min_transfer_volume(PIPETTING_SPECS_NAMES.BIOMEK)

        for pool, conc_map in all_concentration_maps.iteritems():
            if pool == MOCK_POSITION_TYPE:
                self._create_prep_pos_for_mock(conc_map)
            else:
                self._create_prep_positions_for_pool(pool, conc_map, min_vol)

    def _adjust_starting_well_volumes(self):
        """
        Adjusts the required volumes of the starting wells regarding the
        minimum volume that can be taken out of stock.
        """
        min_starting_vol = STOCK_MIN_TRANSFER_VOLUME

        for prep_pos in self._prep_layout.get_starting_wells().values():
            if prep_pos.is_mock: continue # no adjustment required
            self._adjust_volume_for_starting_well(prep_pos, min_starting_vol)


class PrepLayoutFinder384Screening(PrepLayoutFinder348):
    """
    A preparation layout finder for 384-well ISO layouts and screening
    scenarios.
    """

    NAME = 'Preparation ISO Layout Finder 384-well Screening'

    def __init__(self, iso_request, iso_layout, log):
        """
        Constructor:

        :param iso_layout: The layout for the ISO.
        :type iso_layout: :class:`thelma.automation.tools.utils.iso.IsoLayout`

        :param iso_request: The ISO request for which the layout is created.
        :type iso_request: :class:`thelma.models.iso.IsoRequest`

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        PrepLayoutFinder348.__init__(self, log=log, iso_layout=iso_layout,
                                     iso_request=iso_request)

        #: The layout for the ISO
        #: (:class:`thelma.automation.tools.utils.iso.IsoLayout`).
        self.iso_layout = iso_layout
        #: The ISO request for which the layout is created.
        self.iso_request = iso_request

        #: The rack sectors sharing the same molecule design ID within a
        #: quadrant (multiple ISO concentrations only).
        self.__associated_sectors = None
        #: The ISO concentration for each rack sector.
        self.__sector_concentrations = None

        #: The stock concentration for 384-well screening scenarios must
        #: be the same for all molecule design pool and thus, also for the
        # controls and floatings (its equal to
        #: :attr:`floating_stock_concentration` of the :attr:`iso_layout`).
        self.__stock_conc = None
        #: The ISO volume for the samples.
        self.__iso_volume = None
        #: Maps required volumes onto rack sectors.
        self.__sector_req_volumes = None
        #: Stores the parent sector for each sector.
        self.__parent_sectors = None

        #: The dilution factor between preparation plate and aliquot plate.
        self.__aliquot_dil_factor = None

    def reset(self):
        """
        Resets the initialisation values.
        """
        PrepLayoutFinder348.reset(self)
        self.__associated_sectors = None
        self.__sector_concentrations = None
        self.__sector_req_volumes = dict()
        self.__parent_sectors = dict()
        self.__stock_conc = None
        self.__iso_volume = None
        self.__aliquot_dil_factor = 1

    def _set_other_metadata(self):
        """
        Since in screening scenarios many values must be equal for the whole
        layout or all positions of a sector we check them and set for later
        use. Also we need to determine the association of quadrants.
        """
        PrepLayoutFinder348._set_other_metadata(self)
        self.__determine_screening_iso_volume()
        self.__associate_rack_sectors()
        if not self.has_errors():
            self.__stock_conc = self.iso_layout.floating_stock_concentration
            self.__check_iso_concentrations()
        if not self.has_errors(): self.__determine_required_volumes()

    def __determine_screening_iso_volume(self):
        """
        Determines the ISO volume for controls and samples in screening cases.
        """
        volume_determiner = IsoRequestValueDeterminer(iso_layout=self.iso_layout,
                            attribute_name='iso_volume', log=self.log,
                            number_sectors=1, ignore_mock=True)
        sector_values = volume_determiner.get_result()

        if sector_values is None:
            msg = 'There is more than one ISO volume in this layout!'
            self.add_error(msg)
        else:
            self.__iso_volume = sector_values[0]

    def __associate_rack_sectors(self):
        """
        Finds the associated rack sectors (if there is more than one
        ISO concentration per floating position).
        """
        self.add_debug('Get association data ...')

        try:
            association_data = IsoRequestAssociationData(log=self.log,
                                                  iso_layout=self.iso_layout)
        except ValueError:
            msg = 'Error when trying to associate rack sectors by ' \
                  'molecule design pool.'
            self.add_error(msg)
        else:
            self.__associated_sectors = association_data.associated_sectors
            self.__sector_concentrations = \
                                        association_data.sector_concentrations
            self.__parent_sectors = association_data.parent_sectors

    def __check_iso_concentrations(self):
        """
        Checks whether the validity of the ISO concentrations (smaller than
        stock concentration) and the dilution factors.
        """
        self.add_debug('Check ISO concentrations ...')

        too_high = []
        parent_concentrations = set()
        # TODO: replace with pipetting specs
        max_dil_factor = PrepIsoParameters.MAX_DILUTION_FACTOR_CYBIO

        for sector_index, iso_conc in self.__sector_concentrations.iteritems():
            if iso_conc is None: continue
            # is it smaller than stock concentration?
            if iso_conc > self.__stock_conc:
                info = '%s nM (sector %s)' % (get_trimmed_string(iso_conc),
                                              sector_index + 1)
                too_high.append(info)
            # check dilution factor (compared to stock)
            parent_sector = self.__parent_sectors[sector_index]
            if not parent_sector is None: continue
            parent_concentrations.add(iso_conc)

        if len(too_high) > 0:
            msg = 'Some ISO concentrations exceed the stock concentration ' \
                  'for this experiment (%s nM): %s.' \
                  % (get_trimmed_string(self.__stock_conc), too_high)
            self.add_error(msg)
        else:
            while self.__aliquot_dil_factor < max_dil_factor:
                increment = False
                for iso_conc in parent_concentrations:
                    dil_factor = self.__stock_conc \
                                 / (iso_conc * self.__aliquot_dil_factor)
                    if dil_factor > max_dil_factor:
                        increment = True
                if increment:
                    self.__aliquot_dil_factor += 1
                    continue
                break

        if self.__aliquot_dil_factor == max_dil_factor:
            msg = 'The ISO concentration is to low to be reached in 2 steps! ' \
                  'The allowed maximum dilution factor per step (for Cybio) ' \
                  'is %i. Assumed stock concentration: %s nM. Preparation ' \
                  'source concentrations in nM: %s.' \
                   % (PrepIsoParameters.MAX_DILUTION_FACTOR_CYBIO,
                      self.__stock_conc, list(parent_concentrations))
            self.add_error(msg)

    def __determine_required_volumes(self):
        """
        Determines the required volume for each ISO concentration
        (= each sector).
        """
        aliquot_volume = self.__iso_volume / self.__aliquot_dil_factor
        dead_volume = self._reservoir_specs.min_dead_volume \
                      * VOLUME_CONVERSION_FACTOR
        base_volume = dead_volume + (aliquot_volume * self._number_aliquots)

        for sectors in self.__associated_sectors:

            # concentrations for associated sectors
            concentrations_map = dict()
            for sector_index in sectors:
                iso_conc = self.__sector_concentrations[sector_index]
                concentrations_map[iso_conc] = sector_index

            # several concentrations
            concentrations = concentrations_map.keys()
            concentrations.sort()
            last_sector = None

            for iso_conc in concentrations:
                sector_index = concentrations_map[iso_conc]
                if last_sector is None:
                    self.__sector_req_volumes[sector_index] = base_volume
                else:
                    last_iso_conc = self.__sector_concentrations[last_sector]
                    last_req_vol = self.__sector_req_volumes[last_sector]
                    dil_factor = iso_conc / last_iso_conc
                    don_vol = last_req_vol / dil_factor
                    if don_vol < PrepIsoParameters.WELL_MIN_TRANSFER_VOLUME:
                        don_vol = PrepIsoParameters.WELL_MIN_TRANSFER_VOLUME
                    don_vol = round_up(don_vol, decimal_places=1)
                    self.__sector_req_volumes[last_sector] = \
                                            round_up(don_vol * dil_factor)
                    req_vol = base_volume + don_vol
                    self.__sector_req_volumes[sector_index] = req_vol
                last_sector = sector_index

    def _fill_layout(self):
        """
        Fills the layout.
        """
        self.add_debug('Create preparation positions for screening case ...')

        number_sectors = len(self.__sector_concentrations)
        quadrant_iter = QuadrantIterator(number_sectors=number_sectors)

        for quadrant_ips in quadrant_iter.get_all_quadrants(self.iso_layout):
            for sectors in self.__associated_sectors:
                pool = None
                for sector_index in sectors:
                    iso_pos = quadrant_ips[sector_index]
                    if iso_pos is None: continue
                    if iso_pos.is_empty or iso_pos.is_mock: continue
                    pool = iso_pos.molecule_design_pool
                    break
                if pool is None: continue
                self.__create_prep_pos_for_associated_sectors(quadrant_ips,
                                                              sectors, pool)

    def __create_prep_pos_for_associated_sectors(self, quadrant_ips, sectors,
                                                 pool):
        """
        Creates the preparation positions for the a positions
        sharing the same molecule design.
        """
        aliquot_volume = self.__iso_volume / self.__aliquot_dil_factor

        for sector_index in sectors:
            iso_pos = quadrant_ips[sector_index]

            parent_sector = self.__parent_sectors[sector_index]
            if parent_sector is None:
                parent_well = None
            else:
                parent_well = quadrant_ips[parent_sector].rack_position

            iso_concentration = self.__sector_concentrations[sector_index]
            req_volume = self.__sector_req_volumes[sector_index]
            tt = TransferTarget(rack_position=iso_pos.rack_position,
                                transfer_volume=aliquot_volume)

            prep_concentration = iso_concentration * self.__aliquot_dil_factor
            pos_type = PrepIsoParameters.get_position_type(pool)
            # we can determine the position type this way because floatings
            # have not been converted yet
            prep_pos = PrepIsoPosition(rack_position=iso_pos.rack_position,
                                       molecule_design_pool=pool,
                                       position_type=pos_type,
                                       required_volume=req_volume,
                                       transfer_targets=[tt],
                                       prep_concentration=prep_concentration,
                                       parent_well=parent_well)
            self._prep_layout.add_position(prep_pos)

    def _adjust_starting_well_volumes(self):
        """
        Adjusts the required volumes of the starting wells regarding the
        minimum volume that can be taken out of stock.
        """
        self.add_debug('Adjust starting well volumes ...')

        sample_starting_vol = STOCK_MIN_TRANSFER_VOLUME
        control_starting_volume = STOCK_MIN_TRANSFER_VOLUME

        for prep_pos in self._prep_layout.get_starting_wells().values():
            if prep_pos.is_floating:
                min_starting_vol = sample_starting_vol
            else:
                min_starting_vol = control_starting_volume
            self._adjust_volume_for_starting_well(prep_pos, min_starting_vol)


class PrepLayoutFinderManual(PrepLayoutFinder):
    """
    A preparation layout finder for manual optimisation cases. This layout
    finder is a special case, since ISO layout and preparation layout
    are the same (we just have to convert the type).
    """
    NAME = 'Preparation ISO Layout Finder Manual'

    def run(self):
        """
        Runs the tool.
        """
        if self._check_input_class('ISO layout', self.iso_layout,
                                   IsoRequestLayout):

            prep_layout = PrepIsoLayout(shape=self.iso_layout.shape)
            for rack_pos, iso_pos in self.iso_layout.iterpositions():
                prep_pos = PrepIsoPosition(rack_position=rack_pos,
                        molecule_design_pool=iso_pos.molecule_design_pool,
                        position_type=iso_pos.position_type,
                        required_volume=iso_pos.iso_volume,
                        prep_concentration=iso_pos.iso_concentration,
                        transfer_targets=[], parent_well=None)
                prep_layout.add_position(prep_pos)
            self.return_value = prep_layout


class PrepLayoutFinderOrderOnly(PrepLayoutFinder):
    """
    A preparation layout finder for order only cases. This layout
    finder is a special case, since ISO layout and preparation layout
    are the same (we just have to convert the type).

    Each pool may occur only once and it must be in stock concentration.
    """

    def run(self):
        """
        We only need to convert the layout, that's why we can use a
        simplfied :func:`run` method.
        """

        if self._check_input_class('ISO layout', self.iso_layout,
                                   IsoRequestLayout):

            invalid_concentration = []

            prep_layout = PrepIsoLayout(shape=self.iso_layout.shape)
            for rack_pos, iso_pos in self.iso_layout.iterpositions():
                if not iso_pos.iso_concentration == iso_pos.stock_concentration:
                    info = '%s (%s, expected: %s, found: %s)' \
                        % (iso_pos.molecule_design_pool_id, rack_pos.label,
                           get_trimmed_string(iso_pos.iso_concentration),
                           get_trimmed_string(iso_pos.stock_concentration))
                    invalid_concentration.append(info)
                    continue

                prep_pos = PrepIsoPosition(rack_position=rack_pos,
                        molecule_design_pool=iso_pos.molecule_design_pool,
                        position_type=iso_pos.position_type,
                        required_volume=iso_pos.iso_volume,
                        prep_concentration=iso_pos.iso_concentration,
                        transfer_targets=[], parent_well=None)
                prep_layout.add_position(prep_pos)

            if len(invalid_concentration) > 0:
                msg = 'For order only scenarios, molecule design pools can ' \
                      'only be ordered in stock concentration. Some ordered ' \
                      'concentrations in this layout are different: %s.' \
                      % (', '.join(sorted(invalid_concentration)))
                self.add_error(msg)
            else:
                self.return_value = prep_layout


_SUPPORTED_EXPERIMENT_TYPES = [
                EXPERIMENT_SCENARIOS.OPTIMISATION,
                EXPERIMENT_SCENARIOS.SCREENING,
                EXPERIMENT_SCENARIOS.MANUAL,
                EXPERIMENT_SCENARIOS.ORDER_ONLY]
