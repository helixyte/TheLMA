"""
.. currentmodule:: thelma.models.liquidtransfer

Handler for the :class:`GenericSampleTransferPlanParser`.
Converts the data into a :class:`WorklistSeries`

AAB
"""
from everest.entities.utils import get_root_aggregate
from thelma.automation.handlers.base import LayoutParserHandler
from thelma.automation.parsers.sampletransfer \
    import GenericSampleTransferPlanParser
from thelma.automation.tools.semiconstants \
    import get_reservoir_specs_from_plate_specs
from thelma.automation.tools.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.tools.semiconstants import get_reservoir_spec
from thelma.automation.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import add_list_map_element
from thelma.automation.tools.worklists.base import TRANSFER_ROLES
from thelma.interfaces import IPlate
from thelma.interfaces import IRackShape
from thelma.models.liquidtransfer import PlannedContainerDilution
from thelma.models.liquidtransfer import PlannedContainerTransfer
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import WorklistSeries

__docformat__ = 'reStructuredText en'

__all__ = ['GenericSampleTransferPlanParserHandler',
           'RackOrReservoirItem']

#: TODO: think about how to add rack sample transfers

class GenericSampleTransferPlanParserHandler(LayoutParserHandler):
    """
    Converts the data from the :class:`GenericSampleTransferPlanParser`
    into a :class:`WorklistSeries`.

    **Return Value:** :class:`WorklistSeries`

    """
    NAME = 'Generic Sample Transfer Plan Parser Handler'

    _PARSER_CLS = GenericSampleTransferPlanParser

    def __init__(self, stream, log):
        """
        Constructor:

        :param stream: stream of the file to be parsed

        :param log: The ThelmaLog you want to write in.
        :type log: :class:`thelma.ThelmaLog`
        """
        LayoutParserHandler.__init__(self, log=log, stream=stream)

        #: The :class:`WorklistSeries` to be generated.
        self.__worklist_series = None

        #: The :class:`RackOrReservoirItem` objects mapped onto rack identifiers.
        self.__ror_map = dict()

        #: The aggregate used to fetch plates.
        self.__plate_agg = None

        #: Intermediate error storage.
        self.__missing_rack_barcodes = None

    def reset(self):
        LayoutParserHandler.reset(self)
        self.__worklist_series = WorklistSeries()
        self.__plate_agg = get_root_aggregate(IPlate)
        self.__missing_rack_barcodes = []

    def get_racks_and_reservoir_items(self):
        """
        Returns the :class:`RackOrReservoirItem` objects found in the sheet.
        """
        return self._get_additional_value(self.__ror_map.values())

    def _initialize_parser_keys(self):
        """
        We need to set the allowed rack shapes (that is all available rack
        shapes) and the transfer role markers.
        """
        self.parser.source_role_marker = TRANSFER_ROLES.SOURCE
        self.parser.target_role_marker = TRANSFER_ROLES.TARGET

        allowed_rack_dimensions = []

        rack_shape_agg = get_root_aggregate(IRackShape)
        rack_shape_agg.filter = None
        rs_iter = rack_shape_agg.iterator()
        while True:
            try:
                rack_shape = rs_iter.next()
            except StopIteration:
                break
            else:
                dimensions = (rack_shape.number_rows,
                              rack_shape.number_columns)
                allowed_rack_dimensions.append(dimensions)

        self.parser.allowed_rack_dimensions = allowed_rack_dimensions

    def _convert_results_to_model_entity(self):
        """
        Assembles a worklist series from the parsed sheet.
        """
        self.add_info('Start conversion into worklist series ...')

        self.__get_or_generate_racks()
        if not self.has_errors(): self.__create_worklists()
        if not self.has_errors():
            self.add_info('Conversion completed.')
            self.return_value = self.__worklist_series

    def __get_or_generate_racks(self):
        """
        Plates (recognized by specs) are fetched from the DB.
        Reservoirs are generated.
        """
        self.add_debug('Fetch or generate racks ...')

        for rack_container in self.parser.rack_containers.values():
            data_item = self.__create_rack_or_reservoir_data(rack_container)
            if data_item is None: break
            self.__ror_map[data_item.identifier] = data_item

    def __create_rack_or_reservoir_data(self, rack_container):
        """
        Determines whether the specified items is plate or a reservoirs.
        Fetches plates for which there are barcodes or generates plates
        without barcode.
        """
        if rack_container.specs is None:
            plate = self.__get_plate_for_barcode(rack_container.barcode)
            if plate is None:
                return None
            else:
                if not rack_container.specs is None:
                    rs = self.__get_reservoir_specs(rack_container)
                else:
                    rs = self.__get_reservoir_specs_for_plate(plate)
                if rs is None: return None
                data_item = RackOrReservoirItem(is_plate=True,
                                        reservoir_specs=rs,
                                        identifier=rack_container.rack_label)
                data_item.set_plate(plate)
                return data_item

        else:
            rs = self.__get_reservoir_specs(rack_container)
            if rs is None: return None
            is_plate = RESERVOIR_SPECS_NAMES.is_plate_spec(rs)
            data_item = RackOrReservoirItem(is_plate=is_plate,
                       reservoir_specs=rs, identifier=rack_container.rack_label)

            barcode = rack_container.barcode
            if is_plate:
                if barcode is None:
                    msg = 'There is no barcode for rack "%s"!' \
                           % (data_item.identifier)
                    self.add_error(msg)
                    return None
                plate = self.__get_plate_for_barcode(barcode)
                if plate is None: return None
                rs = self.__get_reservoir_specs_for_plate(plate, rs)
                if rs is None: return None
                data_item.reservoir_specs = rs
                data_item.set_plate(plate)

            else:
                if barcode is None:
                    barcode = data_item.identifier
                data_item.barcode = barcode

            return data_item

    def __get_reservoir_specs(self, rack_container):
        """
        Also records an error message if the spec has not been found.
        """
        try:
            rs = get_reservoir_spec(rack_container.specs.lower())
        except ValueError as ve:
            msg = 'Error when trying to fetch specs for rack "%s": %s' \
                   % (rack_container.identifier, ve)
            self.add_error(msg)
            return None
        else:
            return rs

    def __get_plate_for_barcode(self, barcode):
        """
        Also records error message if the aggregate did not return a plate.
        """
        plate = self.__plate_agg.get_by_slug(barcode)

        if plate is None:
            msg = 'Could not find plate "%s" in the DB!' % (barcode)
            self.add_error(msg)

        return plate

    def __get_reservoir_specs_for_plate(self, plate, reservoir_specs=None):
        """
        Fetches the reservoir specs for a plate. If there is already a specs
        in the file, the specs are compared.
        """
        try:
            rs = get_reservoir_specs_from_plate_specs(plate.specs)
        except ValueError as ve:
            msg = 'Error when trying to determine reservoir specs for ' \
                  'plate "%s" (plate specs "%s"): %s' \
                   % (plate.barcode, plate.specs.name, ve)
            self.add_error(msg)
            return None
        else:
            if reservoir_specs is not None and not rs == reservoir_specs:
                msg = 'You specified a wrong reservoir spec for plate "%s" ' \
                      '("%s" instead of "%s"). Will use spec "%s".' \
                      % (plate.barcode, reservoir_specs.name, rs.name, rs.name)
                self.add_warning(msg)
            return rs

    def __create_worklists(self):
        """
        Creates :class:`PlannedWorklist`s and adds them to the
        :attr:`__worklist_series`
        """
        self.add_debug('Create worklists ...')

        for step_number in sorted(self.parser.step_containers.keys()):
            step_container = self.parser.step_containers[step_number]
            if not self.__has_consistent_rack_shapes(step_container): break

            is_dilution = self.__is_dilution(step_container)
            if is_dilution is None: break
            if not self.__has_only_plates_as_target(step_container): break

            planned_transfers = self.__get_planned_transfers(step_container,
                                                             is_dilution)
            if planned_transfers is None: break

            wl_label = '%s_%i' % (self.parser.worklist_prefix, step_number)
            worklist = PlannedWorklist(label=wl_label,
                                       planned_transfers=planned_transfers)
            self.__worklist_series.add_worklist(step_number, worklist)

            for role, rack_ids in step_container.rack_containers.iteritems():
                for rack_id in rack_ids:
                    data_item = self.__ror_map[rack_id]
                    data_item.add_worklist(role, worklist)

    def __has_consistent_rack_shapes(self, step_container):
        """
        Makes sure the rack items assigned to the source and target layouts
        of a step have the requested rack shape.
        """
        for role, layout_container in step_container.layouts.iteritems():
            rack_shape = self._convert_to_rack_shape(layout_container.shape)
            if rack_shape is None: return False

            for rack_id in step_container.rack_containers[role]:
                data_item = self.__ror_map[rack_id]
                if not data_item.rack_shape == rack_shape:
                    msg = 'The rack shape for layout at %s (%s) does not ' \
                          'match the rack shape for rack "%s" (%s).' \
                           % (layout_container.get_starting_cell_name(),
                              layout_container.shape.name,
                              data_item.identifier, data_item.rack_shape.name)
                    self.add_error(msg)
                    return False

        return True

    def __is_dilution(self, step_container):
        """
        Returns *True* for sample dilutions and *False* for sample transfers.
        """
        is_dilution = False

        for rack_id in step_container.rack_containers[TRANSFER_ROLES.SOURCE]:
            data_item = self.__ror_map[rack_id]
            if not data_item.is_plate:
                is_dilution = True
            elif is_dilution:
                # this should not happen because reservoirs have other rack
                # shapes (consistency has already been tested at this point).
                # However, there might be other reservoirs in the future.
                msg = 'The source types for step %i are inconsistent. There ' \
                      'must be either all plate or all reservoirs!' \
                       % (step_container.number)
                self.add_error(msg)
                return None

        return is_dilution

    def __has_only_plates_as_target(self, step_container):
        """
        Reservoirs must not be targets.
        """
        for rack_id in step_container.rack_containers[TRANSFER_ROLES.TARGET]:
            data_item = self.__ror_map[rack_id]
            if not data_item.is_plate:
                msg = 'The target for step %i is a reservoirs. Reservoirs ' \
                      'may only serve as sources!' % (step_container.number)
                self.add_error(msg)
                return False

        return True

    def __get_planned_transfers(self, step_container, is_dilution):
        """
        Create :class:`PlannedContainerDilution`s for dilution (requires
        valid diluent), otherwise it creates
        :class:`PlannedContainerTransfer`s.
        """
        planned_transfers = []
        for transfer_container in step_container.get_transfer_containers():
            src_positions = transfer_container.get_source_positions()
            trg_positions = transfer_container.get_target_positions()
            volume = float(transfer_container.volume) \
                     / VOLUME_CONVERSION_FACTOR

            if is_dilution:
                diluent = transfer_container.diluent
                if diluent is None or not len(str(diluent)) > 1:
                    msg = 'A diluent must be at least 2 characters long! ' \
                          'Change the diluent for step %i code %s, ' \
                          'please.' \
                          % (step_container.number, transfer_container.code)
                    self.add_error(msg)
                    return None

            for trg_pos_container in trg_positions:
                trg_pos = self._convert_to_rack_position(trg_pos_container)
                if is_dilution:
                    pcd = PlannedContainerDilution(volume=volume,
                                target_position=trg_pos,
                                diluent_info=str(transfer_container.diluent))
                    planned_transfers.append(pcd)
                else:
                    for src_pos_container in src_positions:
                        src_pos = self._convert_to_rack_position(
                                                            src_pos_container)
                        pct = PlannedContainerTransfer(volume=volume,
                                                source_position=src_pos,
                                                target_position=trg_pos)
                        planned_transfers.append(pct)

        return planned_transfers


class RackOrReservoirItem(object):
    """
    Helper class storing all data required to run worklist tool using the
    rack or reservoir presented here.
    """
    def __init__(self, is_plate, reservoir_specs, identifier):
        """
        Constructor:

        :param is_plate: Does the object represent a plate (*True*) or
            a reservoir (*False*)?
        :type is_plate: :class:`bool`

        :param reservoir_specs: contains rack shape, maximum and dead volumes
            for the object (it easier to use unified specs)
        :type reservoir_specs:
            :class:`thelma.models.liquidtransfer.ReservoirSpecs`

        :param identifier: The identifier used in the excel sheet.
        :type identifier: :class:`str`
        """
        #: Does the object represent a plate (*True*) or a reservoir (*False*)?
        self.is_plate = is_plate
        #: contains rack shape, maximum and dead volumes for the object
        #: (it easier to use unified specs)
        self.reservoir_specs = reservoir_specs
        #: The identifier used in the excel sheet.
        self.identifier = identifier
        #: The barcode (if there is one specified).
        self.barcode = None
        #: The :class:`thelma.models.rack.Plate` entity (if :attr:`is_plate`
        #; is *True*).
        self.plate = None
        #: List of :class:`PlannedWorklist`s for which this item is a source
        #: or target (mapped onto roles).
        self.__worklists = dict()

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
                 self.barcode == other.barcode

    @property
    def rack_shape(self):
        """
        The rack shape for this rack or reservoir.
        """
        return self.reservoir_specs.rack_shape

    def set_plate(self, plate):
        """
        Sets a plate and a barcode.
        """
        self.plate = plate
        self.barcode = plate.barcode

    def add_worklist(self, role, worklist):
        """
        Registers a worklist in which this object takes over the specified role.

        :param role: source or target
            (see :class:`thelma.automation.tools.worklists.TRANSFER_ROLES`)
        :type role: :class:`str`

        :param worklist: a worklist in which this rack or reservoir occurs
        :type worklist: :class:`thelma.models.liquidtransfer.PlannedWorklist`
        """
        add_list_map_element(self.__worklists, role, worklist)

    def get_worklists_for_source(self):
        """
        Returns the :class:`PlannedWorklist`s for which this items is
        scheduled as source (or an empty list if there are no such worklists).
        """
        return self.__get_worklists_for_role(TRANSFER_ROLES.SOURCE)

    def get_worklists_for_target(self):
        """
        Returns the :class:`PlannedWorklist`s for which this items is
        scheduled as target (or an empty list if there are no such worklists).
        """
        return self.__get_worklists_for_role(TRANSFER_ROLES.TARGET)

    def __get_worklists_for_role(self, role):
        """
        Helper method return a list of worklists in which this items plays
        the specified role.
        """
        if not self.__worklists.has_key(role): return []
        return self.__worklists[role]

    def __cmp__(self, other):
        return cmp(self.identifier, other.identifier)

    def __str__(self):
        if self.is_plate:
            return 'Plate %s' % (self.identifier)
        else:
            return 'Reservoir %s' % (self.identifier)

    def __repr__(self):
        str_format = '<%s is plate: %s, ID: %s, reservoir spec: %s>'
        params = (self.__class__.__name__, self.is_plate, self.identifier,
                  self.reservoir_specs)
        return str_format % params

