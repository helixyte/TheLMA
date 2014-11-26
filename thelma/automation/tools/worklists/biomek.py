"""
This module deals with the creation of worklist files for the Biomek.

AAB
"""
from math import ceil

from thelma.automation.semiconstants import get_pipetting_specs_biomek
from thelma.automation.semiconstants import get_positions_for_shape
from thelma.automation.tools.worklists.base import EmptyPositionManager
from thelma.automation.tools.worklists.writers import WorklistWriter
from thelma.automation.tools.writers import CsvColumnParameters
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.utils.base import get_trimmed_string
from thelma.automation.utils.base import round_up
from thelma.automation.utils.base import sort_rack_positions
from thelma.entities.liquidtransfer import ReservoirSpecs
from thelma.entities.liquidtransfer import TRANSFER_TYPES
from thelma.entities.rack import Plate
from thelma.entities.rack import Rack


__docformat__ = 'reStructuredText en'

__all__ = ['BiomekWorklistWriter',
           'SampleTransferWorklistWriter',
           'SampleDilutionWorklistWriter']


class BiomekWorklistWriter(WorklistWriter):
    """
    A base tool to generate Biomek worklists from planned worklists
    These worklists however might also be used for manual pipetting.
    """
    #: The header for the source rack column.
    SOURCE_RACK_HEADER = 'SourcePlateBarcode'
    #: The header for the source position column.
    SOURCE_POS_HEADER = 'SourcePlateWell'
    #: The header for the target rack column.
    TARGET_RACK_HEADER = 'DestinationPlateBarcode'
    #: The header for the target position column.
    TARGET_POS_HEADER = 'DestinationPlateWell'
    #: The header for the transfer volume.
    TRANSFER_VOLUME_HEADER = 'Volume'
    #: The index for the source rack column.
    SOURCE_RACK_INDEX = 0
    #: The index for the source position column.
    SOURCE_POS_INDEX = 1
    #: The index for the target rack column.
    TARGET_RACK_INDEX = 2
    #: The index for the target position column.
    TARGET_POS_INDEX = 3
    #: The index for the transfer volume.
    TRANSFER_VOLUME_INDEX = 4

    def __init__(self, planned_worklist, target_rack,
                 pipetting_specs=None, ignored_positions=None, parent=None):
        WorklistWriter.__init__(self, planned_worklist, target_rack,
                                pipetting_specs,
                                ignored_positions=ignored_positions,
                                parent=parent)
        if self.pipetting_specs is None:
            self.pipetting_specs = get_pipetting_specs_biomek()
        # These are the CsvColumnParameters for the worklists.
        self._source_rack_values = None
        self._source_pos_values = None
        self._target_rack_values = None
        self._target_pos_values = None
        self._volume_values = None

    def reset(self):
        """
        Resets all values escept for input values.
        """
        WorklistWriter.reset(self)
        self._source_rack_values = []
        self._source_pos_values = []
        self._target_rack_values = []
        self._target_pos_values = []
        self._volume_values = []

    def _init_column_maps(self):
        """
        Initialises the CsvColumnParameters object for the
        :attr:`_column_map_list`.
        """
        source_rack_column = CsvColumnParameters.create_csv_parameter_map(
                    self.SOURCE_RACK_INDEX, self.SOURCE_RACK_HEADER,
                    self._source_rack_values)
        source_pos_column = CsvColumnParameters.create_csv_parameter_map(
                    self.SOURCE_POS_INDEX, self.SOURCE_POS_HEADER,
                    self._source_pos_values)
        target_rack_column = CsvColumnParameters.create_csv_parameter_map(
                    self.TARGET_RACK_INDEX, self.TARGET_RACK_HEADER,
                    self._target_rack_values)
        target_pos_column = CsvColumnParameters.create_csv_parameter_map(
                    self.TARGET_POS_INDEX, self.TARGET_POS_HEADER,
                    self._target_pos_values)
        volume_column = CsvColumnParameters.create_csv_parameter_map(
                    self.TRANSFER_VOLUME_INDEX, self.TRANSFER_VOLUME_HEADER,
                    self._volume_values)
        self._column_map_list = [source_rack_column, source_pos_column,
                                 target_rack_column, target_pos_column,
                                 volume_column]
        self.add_info('Column generation complete.')


class SampleTransferWorklistWriter(BiomekWorklistWriter):
    """
    An abstract base class writing worklist for sample transfer worklists.

    **Return Value:** Stream for an CSV file.
    """

    NAME = 'Biomek Transfer Worklist Writer'

    TRANSFER_TYPE = TRANSFER_TYPES.SAMPLE_TRANSFER

    def __init__(self, planned_worklist, target_rack, source_rack,
                 pipetting_specs=None, ignored_positions=None, parent=None):
        """
        Constructor.

        :param source_rack: The rack from which to take the volumes.
        :type source_rack: :class:`thelma.entities.rack.Rack`
        """
        BiomekWorklistWriter.__init__(self, planned_worklist,
                                      target_rack, pipetting_specs,
                                      ignored_positions=ignored_positions,
                                      parent=parent)
        #: The rack from which to take the volumes.
        self.source_rack = source_rack

    def _check_input(self):
        """
        Checks the input values.
        """
        BiomekWorklistWriter._check_input(self)
        self._check_input_class('source rack', self.source_rack, Rack)

    def _init_source_data(self):
        """
        Initialises the source rack related values and lookups.
        """
        for container in self.source_rack.containers:
            rack_pos = container.location.position
            self._source_containers[rack_pos] = container
            if container.sample is None:
                self._source_volumes[rack_pos] = 0.0
            else:
                volume = container.sample.volume * VOLUME_CONVERSION_FACTOR
                self._source_volumes[rack_pos] = volume
        if isinstance(self.source_rack, Plate):
            well_specs = self.source_rack.specs.well_specs
            self._source_dead_volume = well_specs.dead_volume \
                                       * VOLUME_CONVERSION_FACTOR

    def _generate_column_values(self):
        """
        This method generates the value lists for the CSV columns.
        """
        source_rack_barcode = self.source_rack.barcode
        target_rack_barcode = self.target_rack.barcode
        sorted_transfers = self.__get_sorted_transfers()
        for pt in sorted_transfers:
            if pt.source_position in self.ignored_positions:
                continue
            if not self._check_transfer_volume(pt.volume, pt.target_position,
                                               pt.source_position):
                continue
            self._source_rack_values.append(source_rack_barcode)
            self._source_pos_values.append(pt.source_position.label)
            self._target_rack_values.append(target_rack_barcode)
            self._target_pos_values.append(pt.target_position.label)
            volume = get_trimmed_string(pt.volume * VOLUME_CONVERSION_FACTOR)
            self._volume_values.append(volume)

    def __get_sorted_transfers(self):
        """
        Sorts the planned transfers of the worklist by source position.
        """
        source_positions = dict()
        for plt in self.planned_worklist:
            source_pos = plt.source_position
            if not source_positions.has_key(source_pos):
                source_positions[source_pos] = []
            source_positions[source_pos].append(plt)
        sorted_source_positions = sort_rack_positions(source_positions.keys())
        sorted_transfers = []
        for source_pos in sorted_source_positions:
            planned_transfers = source_positions[source_pos]
            if len(planned_transfers) == 1:
                sorted_transfers.append(planned_transfers[0])
            else:
                target_positions = dict()
                for plt in planned_transfers:
                    target_pos = plt.target_position
                    target_positions[target_pos] = plt
                sorted_target_positions = sort_rack_positions(
                                                        target_positions.keys())
                for target_pos in sorted_target_positions:
                    sorted_transfers.append(target_positions[target_pos])
        return sorted_transfers


class SampleDilutionWorklistWriter(BiomekWorklistWriter):
    """
    An abstract base class writing worklist for sample dilution worklists.

    **Return Value:** Stream for an CSV file.
    """
    NAME = 'Biomek Dilution Worklist Writer'
    TRANSFER_TYPE = TRANSFER_TYPES.SAMPLE_DILUTION
    #: The name of the optional diluent info column.
    DILUENT_INFO_HEADER = 'DiluentInformation'
    #: The index of the optional diluent info column.
    DILUENT_INFO_INDEX = 5

    def __init__(self, planned_worklist, target_rack, source_rack_barcode,
                 reservoir_specs, pipetting_specs=None,
                 ignored_positions=None, parent=None):
        """
        Constructor.

        :param str source_rack_barcode: The barcode for the source rack or
            reservoir.
        :type source_rack_barcode: :class:`str`
        """
        BiomekWorklistWriter.__init__(self, planned_worklist, target_rack,
                                      pipetting_specs=pipetting_specs,
                                      ignored_positions=ignored_positions,
                                      parent=parent)
        #: The barcode for the source rack or reservoir.
        self.source_rack_barcode = source_rack_barcode
        #: The specs for the source rack or reservoir.
        self.reservoir_specs = reservoir_specs
        #: The maximum volume of source rack container.
        self._source_max_volume = None
        #: Values for a column presenting diluent information.
        self._diluent_info_values = None
        #: Maps source position amounts (volumes) onto diluents.
        self._diluent_map = None
        #: Maps total diluent amounts (volumes) onto diluents.
        self._amount_map = None
        #: The last used source rack position.
        self.__last_source_rack_pos = None
        #: Stores and return empty positions in the source rack.
        self.__emtpy_pos_manager = None
        # If True, some dilution had to be split because they exceeded the
        # maximum allowed transfer volume.
        self.__has_split_volumes = False
        # If True, some source containers could not take up all liquid required
        # so that there is at least one additional source container for
        # an diluent.
        self.__split_sources = None

    def reset(self):
        """
        Resets all values except for input values.
        """
        BiomekWorklistWriter.reset(self)
        self._source_max_volume = None
        self._diluent_info_values = []
        self._amount_map = dict()
        self._diluent_map = dict()
        self.__has_split_volumes = False
        self.__split_sources = set()
        self.__emtpy_pos_manager = None
        self.__last_source_rack_pos = None

    def _check_input(self):
        """
        Checks the input values.
        """
        BiomekWorklistWriter._check_input(self)
        self._check_input_class('source rack barcode', self.source_rack_barcode,
                                basestring)
        self._check_input_class('reservoir specs', self.reservoir_specs,
                                ReservoirSpecs)

    def _init_source_data(self):
        """
        Initialises the source rack related values and lookups.
        """
        for rack_pos in get_positions_for_shape(self.reservoir_specs.rack_shape):
            self._source_volumes[rack_pos] = 0
        self._source_dead_volume = self.reservoir_specs.min_dead_volume \
                                   * VOLUME_CONVERSION_FACTOR
        self._source_max_volume = self.reservoir_specs.max_volume \
                                   * VOLUME_CONVERSION_FACTOR
        self.__emtpy_pos_manager = EmptyPositionManager(
                                    rack_shape=self.reservoir_specs.rack_shape)

    def _generate_column_values(self):
        """
        This method generates the value lists for the CSV columns.
        """
        target_rack_barcode = self.target_rack.barcode
        sorted_transfers = self.__get_sorted_transfers()
        for pt in sorted_transfers:
            if pt.target_position in self.ignored_positions:
                continue
            if not self._check_transfer_volume(pt.volume, pt.target_position):
                continue
            split_volumes = self.__split_into_transferable_amounts(pt)
            for i in range(len(split_volumes)):
                volume = round(split_volumes[i], 1)
                source_pos = self.__get_and_adjust_source_position(
                                                pt.diluent_info, volume, i)
                if self.has_errors():
                    break
                self._source_rack_values.append(self.source_rack_barcode)
                self._source_pos_values.append(source_pos.label)
                self._volume_values.append(get_trimmed_string(volume))
                self._target_rack_values.append(target_rack_barcode)
                self._target_pos_values.append(pt.target_position.label)
                self._diluent_info_values.append(pt.diluent_info)
        if self.__has_split_volumes:
            msg = 'Some dilution volumes exceed the allowed maximum transfer ' \
                  'volume of %s ul. The dilution volumes have been distributed ' \
                  'over different source wells. Have a look on the generated ' \
                  'worklist file for details, please.' \
                   % (get_trimmed_string(self._max_transfer_volume))
            self.add_warning(msg)
        if len(self.__split_sources) > 0:
            msg = 'The source for the following diluents has been split ' \
                  'and distributed over several containers because one ' \
                  'single container could not have taken up the required ' \
                  'volume (max volume of a source container: %s ul, dead ' \
                  'volume: %s ul): %s. Have a look onto the generated ' \
                  'worklist files for details, please.' \
                  % (get_trimmed_string(self.reservoir_specs.max_volume \
                                        * VOLUME_CONVERSION_FACTOR),
                     get_trimmed_string(self.reservoir_specs.max_dead_volume \
                                        * VOLUME_CONVERSION_FACTOR),
                     list(self.__split_sources))
            self.add_warning(msg)

    def __get_sorted_transfers(self):
        # Sorts the planned transfers of the worklist by source position.
        target_positions = dict()
        for plt in self.planned_worklist:
            target_pos = plt.target_position
            target_positions[target_pos] = plt

        sorted_target_positions = sort_rack_positions(target_positions.keys())
        sorted_transfers = []
        for target_pos in sorted_target_positions:
            plt = target_positions[target_pos]
            sorted_transfers.append(plt)

        return sorted_transfers

    def __split_into_transferable_amounts(self, planned_transfer):
        # Checks whether the volume is larger than the allowed maximum
        # transfer volume and splits it into transferable amounts.
        volume = round(planned_transfer.volume * VOLUME_CONVERSION_FACTOR, 1)
        if volume <= self._max_transfer_volume:
            return [volume]
        self.__has_split_volumes = True
        no_volumes = ceil(volume / self._max_transfer_volume)
        amounts = []
        partial_vol = round_up((volume / no_volumes), 1)
        while volume > 0:
            if volume < partial_vol:
                amounts.append(volume)
                volume = 0
            else:
                amounts.append(partial_vol)
                volume = volume - partial_vol
        amounts.sort()
        return amounts

    def __get_and_adjust_source_position(self, diluent_info, volume, i):
        # Returns the source position for the diluent.
        diluent_marker = '%s#%i' % (diluent_info, i)
        if not self._diluent_map.has_key(diluent_marker):
            self.__init_new_diluent_source(diluent_marker, volume)
        else:
            source_pos = self._diluent_map[diluent_marker]
            stored_amount = self._amount_map[source_pos]
            new_amount = stored_amount + volume
            if new_amount > self._source_max_volume:
                self.__split_sources.add(str(diluent_info))
                self.__init_new_diluent_source(diluent_marker, volume)
            else:
                self._amount_map[source_pos] = new_amount
        return self._diluent_map[diluent_marker]

    def __init_new_diluent_source(self, diluent_marker, volume):
        # Initialises a new source volume container in the source reservoir.
        try:
            source_pos = self.__emtpy_pos_manager.get_empty_position()
        except ValueError:
            msg = 'There is not enough space for all source containers ' \
                  'in the source rack or reservoir!'
            self.add_error(msg)
            source_pos = None
        self._diluent_map[diluent_marker] = source_pos
        if not source_pos is None:
            self._amount_map[source_pos] = volume + self._source_dead_volume

    def _init_column_maps(self):
        """
        Initialises the CsvColumnParameters object for the
        :attr:`_column_map_list`.
        """
        BiomekWorklistWriter._init_column_maps(self)
        diluent_info_column = \
            CsvColumnParameters.create_csv_parameter_map(
                        self.DILUENT_INFO_INDEX, self.DILUENT_INFO_HEADER,
                        self._diluent_info_values)
        self._column_map_list.append(diluent_info_column)

