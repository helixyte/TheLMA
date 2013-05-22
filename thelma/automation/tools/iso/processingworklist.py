"""
These tools generate layouts and worklists for an ISO plate
generation (preparation processing and sample transfer to the ISO plate).

AAB, Jan 2012
"""
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.iso.prep_utils import PrepIsoAssociationData
from thelma.automation.tools.iso.prep_utils import PrepIsoLayout
from thelma.automation.tools.iso.prep_utils import get_stock_takeout_volume
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import RACK_SHAPE_NAMES
from thelma.automation.tools.semiconstants import get_rack_position_from_label
from thelma.automation.tools.stock.base import get_default_stock_concentration
from thelma.automation.tools.utils.base import get_trimmed_string
from thelma.automation.tools.utils.base import is_valid_number
from thelma.automation.tools.utils.iso import IsoLayoutConverter
from thelma.automation.tools.utils.iso import IsoValueDeterminer
from thelma.automation.tools.utils.racksector import QuadrantIterator
from thelma.automation.tools.worklists.base import MIN_BIOMEK_TRANSFER_VOLUME
from thelma.automation.tools.worklists.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.tools.worklists.generation \
            import PlannedWorklistGenerator
from thelma.models.iso import IsoRequest
from thelma.models.liquidtransfer import PlannedContainerDilution
from thelma.models.liquidtransfer import PlannedContainerTransfer
from thelma.models.liquidtransfer import PlannedRackTransfer
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import WorklistSeries
from thelma.models.liquidtransfer import WorklistSeriesMember

__docformat__ = 'reStructuredText en'
__author__ = 'Anna-Antonia Berger'

__all__ = ['IsoWorklistSeriesGenerator',
           'IsoBufferWorklistGenerator',
           'IsoBufferWorklistGeneratorOptimisation',
           'IsoBufferWorklistGeneratorScreening',
           'IsoDilutionWorklistsGenerator',
           'IsoDilutionWorklistsGeneratorOptimisation',
           'IsoDilutionWorklistsGeneratorScreening',
           'IsoTransferWorklistGenerator',
           'IsoTransferWorklistGeneratorOptimisation',
           'IsoTransferWorklistGeneratorScreening',
           'IsoAliquotBufferWorklistGenerator']


class IsoWorklistSeriesGenerator(BaseAutomationTool):
    """
    This tool generates the worklist series for the ISO processing that is
    worklists for the

        1. addition of annealing buffer (container dilution worklist),
        2. the conduction of dilutions to set up the different ISO
            concentrations (if there is more than one ISO concentration for
            a molecule design pool) and
        3. the transfer from the preparation to the aliquot plate
        (4. in some 384-well screening cases there must be buffer added to
            the aliquot plates too).

    The transfer of molecule design pool from the stock racks to the preparation
    plate is *not* covered here. Instead the worklist are stored with the
    referring stock racks.

    :Note: Manual optimisation scenarios comprise either only worklist 1 or
        are completely empty.

    **Return Value:**  worklist series
        (:class:`thelma.models.liquidtransfer.WorklistSeries`).
    """

    NAME = 'ISO Worklist Series Generator'

    def __init__(self, iso_request, preparation_layout, log):
        """
        Constructor:

        :param iso_request: The ISO request this worklist will belong to.
            Its plate set label will be a part of the worklist name.
        :type iso_request: :class:`thelma.models.iso.IsoRequest`

        :param preparation_layout: The preparation plate layout (does not
            has to be completed).
        :type preparation_layout:
            :class:`thelma.automation.tools.utils.iso.prep_utils.PreparationLayout`

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        BaseAutomationTool.__init__(self, log=log)

        #: The plate set label of the ISO request this liquid transfer plan
        # will belong to. It will be a part of the plan name.
        self.iso_request = iso_request
        #: The preparation plate layout.
        self.prep_layout = preparation_layout

        #: Do we need worklists for a 384-well screening scenario?
        self.__is_384_screening = None
        #: The rack sector association data (384-screenings only).
        self.__association_data = None

        #: The last used worklist index (within the series).
        self.__last_worklist_index = None
        #: The :class:`thelma.models.liquidtransfer.WorklistSeries` to generate.
        self.__worklist_series = None

    def reset(self):
        """
        Resets all values except for the initialization values.
        """
        BaseAutomationTool.reset(self)
        self.__is_384_screening = False
        self.__association_data = None
        self.__worklist_series = None
        self.__last_worklist_index = 0

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start worklist series generation ...')

        self.__check_input()

        if not self.has_errors():
            experiment_type_id = self.iso_request.experiment_metadata_type.id
            self.__worklist_series = WorklistSeries()
            self.__determine_scenario(experiment_type_id)

        if not self.has_errors():
            if experiment_type_id == EXPERIMENT_SCENARIOS.MANUAL:
                self.__create_worklist_for_one_plate_scenario()
            else:
                self.__create_worklist_for_usual_scenario()

        if not self.has_errors():
            self.return_value = self.__worklist_series
            self.add_info('Worklist series generation completed.')

    def __check_input(self):
        """
        Checks the input values.
        """
        self.add_debug('Check input values ...')

        self._check_input_class('ISO request', self.iso_request, IsoRequest)
        self._check_input_class('preparation plate layout', self.prep_layout,
                                PrepIsoLayout)

    def __determine_scenario(self, experiment_type_id):
        """
        Determines the scenario and obtains the association data, if required.
        """
        if self.prep_layout.shape.name == RACK_SHAPE_NAMES.SHAPE_384:
            if experiment_type_id == EXPERIMENT_SCENARIOS.SCREENING:
                self.__is_384_screening = True
                self.__determine_rack_sector_data()

    def __determine_rack_sector_data(self):
        """
        Finds the associated rack sectors (if there is more than one
        ISO concentration per floating position).
        """
        self.add_debug('Get association data ...')

        try:
            self.__association_data = PrepIsoAssociationData(log=self.log,
                                        preparation_layout=self.prep_layout)

        except ValueError:
            msg = 'Error when trying to associate rack sectors by ' \
                  'molecule design pool.'
            self.add_error(msg)

    def __create_worklist_for_one_plate_scenario(self):
        """
        Create the worklist series for one plate scenarios (order only and
        some manuals) scenario.
        """
        self.add_debug('Create worklists for manual scenario ...')

        generator = IsoBufferWorklistGeneratorManual(log=self.log,
                                            iso_request=self.iso_request,
                                            preparation_layout=self.prep_layout)
        buffer_worklist = generator.get_result()

        if buffer_worklist is None:
            msg = 'Error when trying to generate buffer worklist.'
            self.add_error(msg)
        elif len(buffer_worklist.planned_transfers) > 0:
            WorklistSeriesMember(planned_worklist=buffer_worklist,
                                 worklist_series=self.__worklist_series,
                                 index=self.__last_worklist_index)

    def __create_worklist_for_usual_scenario(self):
        """
        Create the worklist series for scenarios with a more complex
        ISO processing.
        """
        self.add_debug('Create worklists for non-manual scenario ...')

        if not self.has_errors(): self.__create_buffer_dilution_worklist()
        if not self.has_errors(): self.__create_dilution_series_worklists()
        if not self.has_errors() and self.__is_384_screening:
            self.__create_aliquot_buffer_worklists()
        if not self.has_errors(): self.__create_transfer_worklist()

    def __create_buffer_dilution_worklist(self):
        """
        Adds the first worklist (addition of annealing buffer).
        """
        self.add_debug('Add annealing buffer dilution worklist ...')

        kw = dict(iso_request=self.iso_request, log=self.log,
                  preparation_layout=self.prep_layout)
        if self.__is_384_screening:
            generator_cls = IsoBufferWorklistGeneratorScreening
            kw['association_data'] = self.__association_data
        else:
            generator_cls = IsoBufferWorklistGeneratorOptimisation

        generator = generator_cls(**kw)
        buffer_worklist = generator.get_result()

        if buffer_worklist is None:
            msg = 'Error when trying to generate preparation buffer dilution ' \
                  'worklist. Abort worklist series generation.'
            self.add_error(msg)
        else:
            WorklistSeriesMember(planned_worklist=buffer_worklist,
                                 worklist_series=self.__worklist_series,
                                 index=self.__last_worklist_index)
            self.__last_worklist_index += 1

    def __create_dilution_series_worklists(self):
        """
        Creates the transfer worklists for the dilution series.
        """
        self.add_debug('Create dilution series worklists ...')

        plate_set_label = get_trimmed_string(self.iso_request.plate_set_label)
        kw = dict(iso_request_name=plate_set_label, log=self.log,
                  preparation_layout=self.prep_layout)
        if self.__is_384_screening:
            generator_cls = IsoDilutionWorklistsGeneratorScreening
            kw['association_data'] = self.__association_data
        else:
            generator_cls = IsoDilutionWorklistsGeneratorOptimisation

        generator = generator_cls(**kw)
        worklist_map = generator.get_result()

        if worklist_map is None:
            msg = 'Error when trying to generate dilution series worklists. ' \
                  'Abort worklist series generation.'
            self.add_error(msg)
        elif len(worklist_map) > 0:
            indeces = worklist_map.keys()
            indeces.sort()
            for i in indeces:
                transfer_worklist = worklist_map[i]
                WorklistSeriesMember(planned_worklist=transfer_worklist,
                                     worklist_series=self.__worklist_series,
                                     index=self.__last_worklist_index)
                self.__last_worklist_index += 1

    def __create_aliquot_buffer_worklists(self):
        """
        Creates the worklist for the addition of buffer into aliquot plates
        (applies only for 384-well screening ISOs with a dilution step
        between preparation and aliquot plate).
        """
        self.add_debug('Add aliquot buffer worklist ...')

        buffer_volume = self.__determine_aliquot_buffer_volume()
        if not buffer_volume is None:
            generator = IsoAliquotBufferWorklistGenerator(
                    iso_request_name=self.iso_request.plate_set_label,
                    preparation_layout=self.prep_layout,
                    buffer_volume=buffer_volume, log=self.log)
            worklist = generator.get_result()
            if worklist is None:
                msg = 'Error when trying to generate aliquot buffer worklist.'
                self.add_error(msg)
            else:
                WorklistSeriesMember(planned_worklist=worklist,
                                     worklist_series=self.__worklist_series,
                                     index=self.__last_worklist_index)
                self.__last_worklist_index += 1

    def __determine_aliquot_buffer_volume(self):
        """
        Determines the buffer volume for the aliquot plates.
        """
        self.add_debug('Determine aliquot buffer volume ...')

        iso_converter = IsoLayoutConverter(log=self.log,
                                        rack_layout=self.iso_request.iso_layout)
        iso_layout = iso_converter.get_result()
        if iso_layout is None:
            msg = 'Error when trying to convert ISO layout!'
            self.add_error(msg)
            return None

        determiner = IsoValueDeterminer(iso_layout=iso_layout,
                                        attribute_name='iso_volume',
                                        log=self.log, number_sectors=1)
        volume_map = determiner.get_result()
        if volume_map is None:
            msg = 'Error when trying to determine volume for ISO layout.'
            self.add_error(msg)
            return None

        iso_volume = volume_map[0]
        buffer_volumes = set()
        for prep_pos in self.prep_layout.working_positions():
            if prep_pos.is_mock: continue
            for tt in prep_pos.transfer_targets:
                transfer_volume = tt.transfer_volume
                buffer_volume = iso_volume - transfer_volume
                buffer_volumes.add(buffer_volume)
        if len(buffer_volumes) > 1:
            msg = 'There is more than buffer volume for this aliquot ' \
                  'plate (%s)! This is a programming error. Please ' \
                  'contact the IT department.' % (list(buffer_volumes))
            self.add_error(msg)
            return None

        buffer_volume = list(buffer_volumes)[0]
        if buffer_volume == 0: return None
        return buffer_volume

    def __create_transfer_worklist(self):
        """
        Creates the worklist for the preparation plate to ISO plate transfer.
        """
        self.add_debug('Create preparation to ISO plate transfer plan ...')

        plate_set_label = get_trimmed_string(self.iso_request.plate_set_label)
        kw = dict(iso_request_name=plate_set_label, log=self.log,
                  preparation_layout=self.prep_layout)
        if self.__is_384_screening:
            generator_cls = IsoTransferWorklistGeneratorScreening
            kw['association_data'] = self.__association_data
        else:
            generator_cls = IsoTransferWorklistGeneratorOptimisation

        generator = generator_cls(**kw)
        transfer_worklist = generator.get_result()

        if transfer_worklist is None:
            msg = 'Error when trying to generate preparation to ISO plate ' \
                  'transfer worklist. Abort worklist series generation.'
            self.add_error(msg)
        else:
            WorklistSeriesMember(planned_worklist=transfer_worklist,
                                 worklist_series=self.__worklist_series,
                                 index=self.__last_worklist_index)
            self.__last_worklist_index += 1


class IsoBufferWorklistGenerator(PlannedWorklistGenerator):
    """
    This is an abstract tool generating a dilution plan for the
    ISO processing worklist series (addition of annealing buffer).
    Since the plan differ depending on the experiment type, the actual
    calculations are taken over by specialised sub classes.

    **Return Value:** :class:`PlannedWorklist` (type: CONTAINER_DILUTION)
    """

    #: The suffix for the worklist label. The first part will be derived by
    #: the ISO request the plan belong to.
    WORKLIST_SUFFIX = '_preparation_buffer'

    #: The diluent info for the planned container dilutions.
    DILUENT_INFO = 'annealing buffer'

    def __init__(self, iso_request, preparation_layout, log):
        """
        Constructor:

        :param iso_request: The ISO request this worklist will belong to.
            Its plate set label will be a part of the worklist name.
        :type iso_request: :class:`thelma.models.iso.IsoRequest`

        :param preparation_layout: The preparation plate layout (does not
            has to be completed).
        :type preparation_layout: :class:`PreparationLayout`

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        PlannedWorklistGenerator.__init__(self, log=log)

        #: The ISO request this worklist will belong to.
        self.iso_request = iso_request
        #: The preparation plate layout.
        self.prep_layout = preparation_layout

    def _check_input(self):
        """
        Checks the input values.
        """
        self.add_debug('Check input values ...')

        self._check_input_class('ISO request', self.iso_request, IsoRequest)
        self._check_input_class('preparation plate layout', self.prep_layout,
                                PrepIsoLayout)

    def _set_label(self):
        """
        Use this method to set label for the planned worklist.
        """
        self._label = '%s%s' % (self.iso_request.plate_set_label,
                                self.WORKLIST_SUFFIX)


class IsoBufferWorklistGeneratorOptimisation(IsoBufferWorklistGenerator):
    """
    This tool generate a dilution plan for the ISO processing
    worklist series (optimisation ISOs).

    At this, it deals with the first of three steps (addition of annealing
    buffer to the preparation plate). The preparation positions are the
    *target* positions.

    **Return Value:** :class:`PlannedWorklist` (type: CONTAINER_DILUTION)
    """

    NAME = 'ISO Annealing Buffer Dilution Worklist Generator Opti'

    def __init__(self, iso_request, preparation_layout, log):
        """
        Constructor:

        :param iso_request: The ISO request this worklist will belong to.
            Its plate set label will be a part of the worklist name.
        :type iso_request: :class:`thelma.models.iso.IsoRequest`

        :param preparation_layout: The preparation plate layout (does not
            has to be completed).
        :type preparation_layout: :class:`PreparationLayout`

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        IsoBufferWorklistGenerator.__init__(self, log=log,
                                        iso_request=iso_request,
                                        preparation_layout=preparation_layout)

        # Intermediate error storage.
        self.__min_buffer_volume = None

    def reset(self):
        """
        Resets all except for initialisation values.
        """
        IsoBufferWorklistGenerator.reset(self)
        self.__min_buffer_volume = []

    def _create_planned_transfers(self):
        """
        Overwrite this method to create the planned transfer belonging to
        the worklist.
        """
        pool_conc_map = self.prep_layout.get_md_pool_concentration_map()

        for prep_pos in self.prep_layout.working_positions():
            if prep_pos.parent_well is None:
                self.__store_pos_for_starting_well(prep_pos)
            else:
                self.__store_pos_for_other_well(prep_pos, pool_conc_map)

        if len(self.__min_buffer_volume) > 0:
            msg = 'The buffer volume for some wells is too small to be ' \
                  'transferred: %s. This is a programming error. Please ' \
                  'contact the IT department!' % (self.__min_buffer_volume)
            self.add_error(msg)

    def __store_pos_for_starting_well(self, prep_pos):
        """
        Generates and stores a planned container dilution for a starting well.
        """
        if prep_pos.is_floating:
            take_out_volume = get_stock_takeout_volume(
                        stock_concentration=self.prep_layout.\
                                            floating_stock_concentration,
                        required_volume=prep_pos.required_volume,
                        concentration=prep_pos.prep_concentration)
        else:
            take_out_volume = prep_pos.get_stock_takeout_volume()
        buffer_volume = prep_pos.required_volume - take_out_volume
        volume = buffer_volume / VOLUME_CONVERSION_FACTOR
        self.__check_buffer_volume(buffer_volume, prep_pos.rack_position)
        pcd = PlannedContainerDilution(volume=volume,
                        target_position=prep_pos.rack_position,
                        diluent_info=self.DILUENT_INFO)
        self._add_planned_transfer(pcd)

    def __store_pos_for_other_well(self, prep_pos, pool_conc_map):
        """
        Generates and stores a planned container dilution for a
        non-starting well.
        """
        pool = prep_pos.molecule_design_pool
        conc_map = pool_conc_map[pool]
        prep_conc = prep_pos.prep_concentration

        concentrations = conc_map.keys()
        concentrations.sort()
        concentrations.reverse()

        prep_pos_index = concentrations.index(prep_conc)
        source_conc = concentrations[prep_pos_index - 1]

        dil_factor = source_conc / prep_conc
        donation_vol = prep_pos.required_volume / dil_factor
        donation_vol = round(donation_vol, 1)
        buffer_vol = prep_pos.required_volume - donation_vol
        self.__check_buffer_volume(buffer_vol, prep_pos.rack_position)
        volume = buffer_vol / VOLUME_CONVERSION_FACTOR

        pcd = PlannedContainerDilution(volume=volume,
                    target_position=prep_pos.rack_position,
                    diluent_info=self.DILUENT_INFO)
        self._add_planned_transfer(pcd)

    def __check_buffer_volume(self, volume, rack_pos):
        """
        Checks whether the buffer volume is within the valid range.
        """
        if (volume - MIN_BIOMEK_TRANSFER_VOLUME) < -0.01:
            info = '%s (%.1f ul)' % (rack_pos.label, volume)
            self.__min_buffer_volume.append(info)


class IsoBufferWorklistGeneratorScreening(IsoBufferWorklistGenerator):
    """
    This tool generate a dilution plan for the ISO processing
    worklist series (screening ISOs).

    At this, it deals with the first of five steps (addition of annealing
    buffer to the preparation plate). The preparation positions
    are *target* positions.

    **Return Value:** :class:`PlannedWorklist` (type: CONTAINER_DILUTION)
    """

    NAME = 'ISO Annealing Buffer Dilution Worklist Generator Screen'

    def __init__(self, iso_request, preparation_layout, association_data, log):
        """
        Constructor:

        :param iso_request: The ISO request this worklist will belong to.
            Its plate set label will be a part of the worklist name.
        :type iso_request: :class:`thelma.models.iso.IsoRequest`

        :param preparation_layout: The preparation plate layout (does not
            has to be completed).
        :type preparation_layout: :class:`PrepIsoLayout`

        :param association_data: The rack sector association data (sector
            association, concentrations and parent sectors).
        :type association_data: :class:`PrepIsoAssociationData`

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        IsoBufferWorklistGenerator.__init__(self, log=log,
                                    iso_request=iso_request,
                                    preparation_layout=preparation_layout)

        #: The rack sector association data (sector association, concentrations
        #: and parent sectors).
        self.association_data = association_data

        #: The stock concentration for the molecule type used in this experiment
        self.__stock_conc = None
        #: The buffer volumes for each rack sector.
        self.__buffer_volumes = None

    def reset(self):
        """
        Resets all except for initialisation values.
        """
        IsoBufferWorklistGenerator.reset(self)
        self.__stock_conc = None
        self.__buffer_volumes = dict()

    def _check_input(self):
        """
        Checks the input values.
        """
        IsoBufferWorklistGenerator._check_input(self)
        self._check_input_class('association data', self.association_data,
                                PrepIsoAssociationData)

    def _create_planned_transfers(self):
        """
        Overwrite this method to create the planned transfer belonging to
        the worklist.
        """
        md_type = self.iso_request.experiment_metadata \
                      .molecule_design_pool_set.molecule_type
        self.__stock_conc = get_default_stock_concentration(md_type)
        self.__determine_buffer_volumes()

        number_sectors = self.association_data.number_sectors
        quadrant_iter = QuadrantIterator(number_sectors=number_sectors)
        for quandrant_pps in quadrant_iter.get_all_quadrants(self.prep_layout):

            for sector_index, prep_pos in quandrant_pps.iteritems():
                if prep_pos is None: continue
                buffer_volume = self.__buffer_volumes[sector_index]
                pcd = PlannedContainerDilution(volume=buffer_volume,
                            target_position=prep_pos.rack_position,
                            diluent_info=self.DILUENT_INFO)
                self._add_planned_transfer(pcd)

    def __determine_buffer_volumes(self):
        """
        Determines the buffer volumes for each rack sector.
        """
        self.add_debug('Determine buffer volumes for rack sectors ...')

        required_volumes = self.association_data.sector_req_volumes
        concentrations = self.association_data.sector_concentrations

        for sector_index in range(self.association_data.number_sectors):
            iso_conc = concentrations[sector_index]
            if iso_conc is None: continue
            parent_sector = self.association_data.parent_sectors[sector_index]
            req_volume = required_volumes[sector_index]

            if parent_sector is None:
                take_out_volume = get_stock_takeout_volume(
                            stock_concentration=self.__stock_conc,
                            required_volume=req_volume,
                            concentration=iso_conc)
                buffer_volume = req_volume - take_out_volume

            else:
                parent_conc = concentrations[parent_sector]
                dil_factor = parent_conc / iso_conc
                donation_vol = req_volume / dil_factor
                donation_vol = round(donation_vol, 1)
                buffer_volume = req_volume - donation_vol

            volume = buffer_volume / VOLUME_CONVERSION_FACTOR
            self.__buffer_volumes[sector_index] = volume


class IsoBufferWorklistGeneratorManual(IsoBufferWorklistGenerator):
    """
    An IsoBufferWorklistGenerator for manual optimisation experiments.
    Transfers are only created for positions that are not in stock
    concentration.

    **Return Value:** :class:`PlannedWorklist` (type: CONTAINER_DILUTION)
    """
    NAME = 'ISO Annealing Buffer Dilution Worklist Generator Manual'

    def _create_planned_transfers(self):
        """
        Overwrite this method to create the planned transfer belonging to
        the worklist.
        """
        for rack_pos, prep_pos in self.prep_layout.iterpositions():
            pp_conc = prep_pos.prep_concentration
            if pp_conc == prep_pos.stock_concentration: continue

            take_out_volume = prep_pos.get_stock_takeout_volume()
            buffer_volume = prep_pos.required_volume - take_out_volume
            volume = buffer_volume / VOLUME_CONVERSION_FACTOR
            pcd = PlannedContainerDilution(volume=volume,
                                           target_position=rack_pos,
                                           diluent_info=self.DILUENT_INFO)
            self._add_planned_transfer(pcd)


class IsoDilutionWorklistsGenerator(BaseAutomationTool):
    """
    This tool generate a list of transfer worklists for the
    ISO processing worklist series.
    Since the plan differ depending on the experiment tpe, the actual
    calculations are taken over by specialised sub classes.

    **Return Value:** depending in the subclass
    """

    #: The suffix for the worklist label. The first part will be derived by
    #: the ISO request the plan belong to. The medium part is a marker
    #: (opti or screening). The last part will be number of
    #: the plan withing the dilution series.
    BASE_PLAN_NAME = '_dilution_'

    def __init__(self, iso_request_name, preparation_layout, log):
        """
        Constructor:

        :param iso_request_name: The plate set label of the ISO request
            this liquid transfer plan will belong to. It will be a part
            of the name of the plan.
        :type iso_request_name: :class:`str`

        :param preparation_layout: The preparation plate layout (does not
            has to be completed).
        :type preparation_layout:
            :class:`thelma.automation.tools.utils.iso.prep_utils.PreparationLayout`

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        BaseAutomationTool.__init__(self, log=log)

        #: The plate set label of the ISO request this liquid transfer plan
        # will belong to. It will be a part of the plan name.
        self.iso_request_name = iso_request_name
        #: The preparation plate layout.
        self.prep_layout = preparation_layout

        #: The generated dilution worklists as dict (key: index within the
        #: series, value: sample_transfer_plan).
        self._worklist_map = None

    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        BaseAutomationTool.reset(self)
        self._worklist_map = dict()

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start dilution series worklist generation ...')

        self._check_input()
        if not self.has_errors():
            self._determine_number_of_worklists()
            self.__generate_worklists()
        if not self.has_errors():
            self.return_value = self._worklist_map
            self.add_info('Dilution series worklists generated.')

    def _check_input(self):
        """
        Checks the input values.
        """
        self.add_debug('Check input values ...')

        self._check_input_class('ISO request name', self.iso_request_name,
                                basestring)
        self._check_input_class('preparation plate layout', self.prep_layout,
                                PrepIsoLayout)

    def _determine_number_of_worklists(self):
        """
        Determines the number of worklists to be generated (and sets up the
        :attr:`_worklist_map` accordingly.
        """
        self.add_error('Abstract method: _determine_number_of_worklists()')

    def __generate_worklists(self):
        """
        Generates the worklists (only if there are different concentrations
        for the molecule design pools).
        """
        self.add_debug('Generate worklists ...')

        for worklist_index in range(len(self._worklist_map)):
            label = label = '%s%s%i' % (self.iso_request_name,
                                        self.BASE_PLAN_NAME,
                                        (worklist_index + 1))
            worklist = PlannedWorklist(label=label)
            updated_worklist = self._fill_worklist(worklist, worklist_index)
            self._worklist_map[worklist_index] = updated_worklist

    def _fill_worklist(self, worklist, worklist_index): #pylint: disable=W0613
        """
        Generates the transfers for the given worklist and worklist index.
        """
        self.add_debug('Abstract method: _fill_worklist()')


class IsoDilutionWorklistsGeneratorOptimisation(IsoDilutionWorklistsGenerator):
    """
    This tool generates a set of container transfer worklists for the
    ISO processing worklist series (optimisation ISOs).

    At this, it deals with the second(s) of three steps (dilution of molecule
    designs to the requested ISO concentrations). The preparation positions
    are the *source and target* positions.

    **Return Value:** dict with key = index, value = container transfer worklist
    """

    NAME = 'ISO Preparation Dilution Series Generator Opti'

    def __init__(self, iso_request_name, preparation_layout, log):
        """
        Constructor:

        :param iso_request_name: The plate set label of the ISO request
            this liquid transfer plan will belong to. It will be a part
            of the name of the plan.
        :type iso_request_name: :class:`str`

        :param preparation_layout: The preparation plate layout (does not
            has to be completed).
        :type preparation_layout:
            :class:`thelma.automation.tools.utils.iso.prep_utils.PreparationLayout`

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        IsoDilutionWorklistsGenerator.__init__(self, log=log,
                            iso_request_name=iso_request_name,
                            preparation_layout=preparation_layout)

        #: Maps preparation position onto molecule design pools.
        self.__mdp_conc_map = None

    def reset(self):
        """
        Resets all values except for the initialization values.
        """
        IsoDilutionWorklistsGenerator.reset(self)
        self.__mdp_conc_map = dict()

    def _determine_number_of_worklists(self):
        """
        Determines the number of worklists to be generated (and sets up the
        :attr:`_worklist_map` accordingly.
        """
        self.add_debug('Determine number of worklists ...')

        self.__mdp_conc_map = self.prep_layout.get_md_pool_concentration_map()
        max_conc_number = 0
        for conc_map in self.__mdp_conc_map.values():
            if len(conc_map) > max_conc_number:
                max_conc_number = len(conc_map)

        if not max_conc_number == 1:
            for i in range(max_conc_number - 1):
                self._worklist_map[i] = None

    def _fill_worklist(self, worklist, worklist_index):
        """
        Generates the container transfers for the given worklist and
        worklist index.
        """

        for conc_map in self.__mdp_conc_map.values():
            concentrations = conc_map.keys()
            concentrations.sort()
            concentrations.reverse()
            if len(concentrations) < worklist_index + 2: continue

            starting_conc = concentrations[worklist_index]
            target_conc = concentrations[worklist_index + 1]
            dil_factor = starting_conc / target_conc
            starting_pos = conc_map[starting_conc]
            target_pos = conc_map[target_conc]
            donation_vol = target_pos.required_volume / dil_factor
            donation_vol = round(donation_vol, 1)
            volume = donation_vol / VOLUME_CONVERSION_FACTOR

            pct = PlannedContainerTransfer(volume=volume,
                        source_position=starting_pos.rack_position,
                        target_position=target_pos.rack_position)
            worklist.planned_transfers.append(pct)

        return worklist


class IsoDilutionWorklistsGeneratorScreening(IsoDilutionWorklistsGenerator):
    """
    This tool generates a s set of rack transfer plan for the
    ISO processing worklist series (screening ISOs).

    At this, it deals with the fourth of five steps (dilution of molecule
    designs to the requested ISO concentrations). The preparation positions
    are the *source and target* positions.

    **Return Value:** :class:`PlannedWorklist` (type: RACK_TRANSFER)
    """

    NAME = 'ISO Preparation Dilution Series Generator Screen'

    def __init__(self, iso_request_name, preparation_layout, association_data,
                 log):
        """
        Constructor:

        :param iso_request_name: The plate set label of the ISO request
            this liquid transfer plan will belong to. It will be a part
            of the name of the plan.
        :type iso_request_name: :class:`str`


        :param preparation_layout: The preparation plate layout (does not
            has to be completed).
        :type preparation_layout: :class:`PreparationLayout`

        :param association_data: The rack sector association data (sector
            association, concentrations and parent sectors).
        :type association_data: :class:`PrepIsoAssociationData`

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        IsoDilutionWorklistsGenerator.__init__(self, log=log,
                                    iso_request_name=iso_request_name,
                                    preparation_layout=preparation_layout)

        #: The rack sector association data (sector association, concentrations
        #: and parent sectors).
        self.association_data = association_data

    def _check_input(self):
        """
        Checks the input values.
        """
        IsoDilutionWorklistsGenerator._check_input(self)
        self._check_input_class('association data', self.association_data,
                                PrepIsoAssociationData)

    def _determine_number_of_worklists(self):
        """
        Determines the number of worklists to be generated (and sets up the
        :attr:`_worklist_map` accordingly.
        """
        self.add_debug('Determine number of worklists ...')

        number_worklists = 0
        for sectors in self.association_data.associated_sectors:
            number_sectors = len(sectors)
            if number_sectors > number_worklists:
                number_worklists = number_sectors

        if not number_worklists == 1:
            for i in range(number_worklists - 1):
                self._worklist_map[i] = None

    def _fill_worklist(self, worklist, worklist_index):
        """
        Generates the rack transfers for the given worklist and
        worklist index.
        """
        for sectors in self.association_data.associated_sectors:
            if len(sectors) < worklist_index + 2: continue
            concentration_map = dict()
            for sector_index in sectors:
                iso_conc = self.association_data.sector_concentrations[
                                                                sector_index]
                concentration_map[iso_conc] = sector_index

            concentrations = concentration_map.keys()
            concentrations.sort()
            concentrations.reverse()

            source_conc = concentrations[worklist_index]
            source_sector = concentration_map[source_conc]
            target_conc = concentrations[worklist_index + 1]
            target_sector = concentration_map[target_conc]
            dil_factor = source_conc / target_conc

            required_volume = self.association_data.sector_req_volumes[
                                                                target_sector]
            donation_vol = required_volume / dil_factor
            donation_vol = round(donation_vol, 1)
            volume = donation_vol / VOLUME_CONVERSION_FACTOR

            prt = PlannedRackTransfer(volume=volume,
                            source_sector_index=source_sector,
                            target_sector_index=target_sector,
                            sector_number=self.association_data.number_sectors)
            worklist.planned_transfers.append(prt)

        return worklist


class IsoTransferWorklistGenerator(PlannedWorklistGenerator):
    """
    This is an abstract tool generating a transfer plan for the
    ISO processing worklist series (transfer of molecule design pools
    from preparation to aliquot plate). Since the plan differ
    depending on the experiment tpe, the actual calculations are taken
    over by specialised sub classes.

    **Return Value:** :class:`PlannedWorklist` (type depends on the subclass)
    """

    #: The suffix for the worklist label. The first part will be derived by
    #: the ISO request the plan belong to.
    WORKLIST_SUFFIX = '_aliquot_transfer'

    def __init__(self, iso_request_name, preparation_layout, log):
        """
        Constructor:

        :param iso_request_name: The plate set label of the ISO request
            this liquid transfer plan will belong to. It will be a part
            of the name of the plan.
        :type iso_request_name: :class:`str`

        :param preparation_layout: The preparation plate layout (does not
            has to be completed).
        :type preparation_layout:
            :class:`thelma.automation.tools.utils.iso.prep_utils.PreparationLayout`

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        PlannedWorklistGenerator.__init__(self, log=log)

        #: The plate set label of the ISO request this liquid transfer plan
        # will belong to. It will be a part of the plan name.
        self.iso_request_name = iso_request_name
        #: The preparation plate layout.
        self.prep_layout = preparation_layout

    def _check_input(self):
        """
        Checks the input values.
        """
        self.add_debug('Check input values ...')

        self._check_input_class('ISO request name', self.iso_request_name,
                                basestring)
        self._check_input_class('preparation plate layout', self.prep_layout,
                                PrepIsoLayout)

    def _set_label(self):
        """
        Sets label for the planned worklist.
        """
        self._label = '%s%s' % (self.iso_request_name, self.WORKLIST_SUFFIX)


class IsoTransferWorklistGeneratorOptimisation(IsoTransferWorklistGenerator):
    """
    This tool generate a container transfer worklist for the
    ISO processing worklist series (optimisation ISOs).

    At this, it deals with the third of three steps (transfer of sample from
    the preparation plate to the aliquot plate). The preparation positions
    are the *source and target* positions.

    **Return Value:** :class:`PlannedWorklist` (type: CONTAINER_TRANSFER)
    """

    NAME = 'ISO Transfer Worklist Generator Optimisation'

    def __init__(self, iso_request_name, preparation_layout, log):
        """
        Constructor:

        :param iso_request_name: The plate set label of the ISO request
            this liquid transfer plan will belong to. It will be a part
            of the name of the plan.
        :type iso_request_name: :class:`str`

        :param preparation_layout: The preparation plate layout (does not
            has to be completed).
        :type preparation_layout:
            :class:`thelma.automation.tools.utils.iso.prep_utils.PreparationLayout`

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        IsoTransferWorklistGenerator.__init__(self, log=log,
                                iso_request_name=iso_request_name,
                                preparation_layout=preparation_layout)

    def _create_planned_transfers(self):
        """
        Generates the planned container transfer positions for worklist.
        """
        self.add_debug('Generate container transfers ...')

        for prep_pos in self.prep_layout.working_positions():
            source_pos = prep_pos.rack_position
            for tt in prep_pos.transfer_targets:
                volume = tt.transfer_volume / VOLUME_CONVERSION_FACTOR
                target_pos = get_rack_position_from_label(tt.position_label)
                pct = PlannedContainerTransfer(volume=volume,
                        source_position=source_pos,
                        target_position=target_pos)
                self._add_planned_transfer(pct)


class IsoTransferWorklistGeneratorScreening(IsoTransferWorklistGenerator):
    """
    This tool generate a rack transfer plan for the ISO processing
    worklist series (screening ISOs).

    At this, it deals with the fifth of five steps (transfer of sample from
    the preparation plate to the aliquot plate). The preparation positions
    are the *source and target* positions.

    **Return Value:** :class:`PlannedWorklist` (type: RACK_TRANSFER)
    """

    NAME = 'ISO Transfer Worklist Generator Optimisation'


    def __init__(self, iso_request_name, preparation_layout, association_data,
                 log):
        """
        Constructor:

        :param iso_request_name: The plate set label of the ISO request
            this liquid transfer plan will belong to. It will be a part
            of the name of the plan.
        :type iso_request_name: :class:`str`

        :param preparation_layout: The preparation plate layout (does not
            has to be completed).
        :type preparation_layout: :class:`PreparationLayout`

        :param association_data: The rack sector association data (sector
            association, concentrations and parent sectors).
        :type association_data: :class:`PrepIsoAssociationData`

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        IsoTransferWorklistGenerator.__init__(self, log=log,
                                    iso_request_name=iso_request_name,
                                    preparation_layout=preparation_layout)

        #: The rack sector association data (sector association, concentrations
        #: and parent sectors).
        self.association_data = association_data

    def _check_input(self):
        """
        Checks the input values.
        """
        IsoTransferWorklistGenerator._check_input(self)
        self._check_input_class('association data', self.association_data,
                                PrepIsoAssociationData)

    def _create_planned_transfers(self):
        """
        Generates the planned container transfer positions for worklist.
        """
        self.add_debug('Generate container transfers ...')

        transfer_volumes = set()
        for prep_pos in self.prep_layout.working_positions():
            for tt in prep_pos.transfer_targets:
                transfer_volume = tt.transfer_volume
                transfer_volumes.add(transfer_volume)

        if len(transfer_volumes) > 1:
            msg = 'There is more than one ISO volume for this screening ' \
                  'preparation layout: %s.' % (list(transfer_volumes))
            self.add_error(msg)
        else:
            transfer_volume = list(transfer_volumes)[0]
            volume = transfer_volume / VOLUME_CONVERSION_FACTOR
            prt = PlannedRackTransfer(volume=volume,
                            source_sector_index=0,
                            target_sector_index=0,
                            sector_number=1)

            self._add_planned_transfer(prt)


class IsoAliquotBufferWorklistGenerator(PlannedWorklistGenerator):
    """
    This is an abstract tool generating a dilution plan for the
    ISO processing worklist series (addition of annealing buffer to
    the aliquot plate if there are different concentrations).
    This applies only to screening cases.

    **Return Value:** :class:`PlannedWorklist` (type: CONTAINER_DILUTION)
    """
    NAME = 'Iso Aliquot Buffer Worklist Generator'

    #: The suffix for the worklist label. The first part will be derived by
    #: the ISO request the plan belong to.
    WORKLIST_SUFFIX = '_aliquot_buffer'
    #: The diluent info for the planned container dilutions.
    DILUENT_INFO = 'buffer'

    def __init__(self, iso_request_name, preparation_layout,
                 buffer_volume, log):
        """
        Constructor:

        :param iso_request_name: The plate set label of the ISO request
            this liquid transfer plan will belong to. It will be a part
            of the name of the plan.
        :type iso_request_name: :class:`str`

        :param preparation_layout: The preparation plate layout (does not
            has to be completed).
        :type preparation_layout:
            :class:`thelma.automation.tools.utils.iso.prep_utils.PreparationLayout`

        :param buffer_volume: The buffer volume in ul.
        :type buffer_volume: positive number

        :param log: The log to write into.
        :type log: :class:`thelma.ThelmaLog`
        """
        PlannedWorklistGenerator.__init__(self, log=log)

        #: The plate set label of the ISO request this liquid transfer plan
        # will belong to. It will be a part of the plan name.
        self.iso_request_name = iso_request_name
        #: The preparation plate layout.
        self.prep_layout = preparation_layout
        #: The buffer volume to be added in ul.
        self.buffer_volume = buffer_volume

    def _check_input(self):
        """
        Checks the input values.
        """
        self.add_debug('Check input ...')

        self._check_input_class('ISO request name', self.iso_request_name,
                                basestring)
        self._check_input_class('preparation plate layout', self.prep_layout,
                                PrepIsoLayout)

        if not is_valid_number(self.buffer_volume):
            msg = 'The buffer volume must be a positive number ' \
                  '(obtained: %s).' % (self.buffer_volume)
            self.add_error(msg)

    def _set_label(self):
        """
        Sets label for the planned worklist.
        """
        self._label = '%s%s' % (self.iso_request_name, self.WORKLIST_SUFFIX)

    def _create_planned_transfers(self):
        """
        Generates the planned container dilution positions for worklist.
        """
        self.add_debug('Generate container dilutions ...')

        volume = self.buffer_volume / VOLUME_CONVERSION_FACTOR
        for rack_pos, prep_pos in self.prep_layout.iterpositions():
            if prep_pos.is_mock: continue
            pcd = PlannedContainerDilution(volume=volume,
                            target_position=rack_pos,
                            diluent_info=self.DILUENT_INFO)
            self._add_planned_transfer(pcd)
