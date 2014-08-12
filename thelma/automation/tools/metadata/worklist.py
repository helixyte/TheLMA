"""
These tools generate the planned worklists for the
translation of ISO plates into experiment plates.

October 2011, AAB
"""

from thelma.automation.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.semiconstants import PIPETTING_SPECS_NAMES
from thelma.automation.semiconstants import get_experiment_metadata_type
from thelma.automation.tools.base import BaseTool
from thelma.automation.tools.metadata.base import TransfectionLayout
from thelma.automation.tools.metadata.base import TransfectionParameters
from thelma.automation.utils.base import add_list_map_element
from thelma.automation.tools.worklists.generation \
                import PlannedWorklistGenerator
from thelma.automation.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.automation.utils.base import get_trimmed_string
from thelma.models.experiment import ExperimentDesign
from thelma.models.experiment import ExperimentMetadataType
from thelma.models.liquidtransfer import PlannedRackSampleTransfer
from thelma.models.liquidtransfer import PlannedSampleDilution
from thelma.models.liquidtransfer import PlannedSampleTransfer
from thelma.models.liquidtransfer import WorklistSeries
from thelma.models.liquidtransfer import WorklistSeriesMember

__docformat__ = 'reStructuredText en'

__all__ = ['_SUPPORTED_SCENARIOS',
           'EXPERIMENT_WORKLIST_PARAMETERS',
           'ExperimentWorklistGenerator',
           '_OptimemWorklistGenerator',
           '_ReagentWorklistGenerator',
           '_BiomekTransferWorklistGenerator',
           '_CybioTransferWorklistGenerator',
           '_CellSuspensionWorklistGenerator',
           ]


class _SUPPORTED_SCENARIOS(object):
    """
    Scenarios supported by the experiment worklist generator.
    """
    #: A list of all supported scenarios.
    ALL = [EXPERIMENT_SCENARIOS.SCREENING, EXPERIMENT_SCENARIOS.OPTIMISATION,
           EXPERIMENT_SCENARIOS.LIBRARY]

    @classmethod
    def get_all_displaynames(cls):
        """
        Returns the display names of all supported scenarios as list.
        """
        display_names = []
        for scenario_name in cls.ALL:
            entity = get_experiment_metadata_type(scenario_name)
            display_names.append(entity.display_name)

        return display_names


class EXPERIMENT_WORKLIST_PARAMETERS(object):
    """
    Defines the storage entity for the cell plate preparation worklists
    and thus, the indices of he worklists.
    """
    #: Marks the experiment design as storage location.
    EXPERIMENT_DESIGN = 'experiment_design'
    #: Marks the experiment design rack as storage location.
    EXPERIMENT_DESIGN_RACK = 'experiment_design_rack'

    #: The entity at which to store the cell plate preparation worklist series.
    STORAGE_LOCATIONS = {
                EXPERIMENT_SCENARIOS.SCREENING : EXPERIMENT_DESIGN,
                EXPERIMENT_SCENARIOS.LIBRARY : EXPERIMENT_DESIGN,
                EXPERIMENT_SCENARIOS.OPTIMISATION : EXPERIMENT_DESIGN_RACK,
                         }

    #: The index of the worklist for the ISO to cell plate transfer.
    TRANSFER_WORKLIST_INDICES = {
                EXPERIMENT_DESIGN : 2,
                EXPERIMENT_DESIGN_RACK : 0
                                 }
    #: The index of the worklist for the addition of cell suspension.
    CELL_WORKLIST_INDICES = {
                EXPERIMENT_DESIGN : 3,
                EXPERIMENT_DESIGN_RACK : 1,
                                 }


class ExperimentWorklistGenerator(BaseTool):
    """
    Generates the worklist series for the preparation of an experiment.
    This may include up to four worklists that can be split into 2 groups:

        I. Mastermix preparation
            1. addition of OptiMem
            2. addition of transfection reagent
        II. Cell plate preparation
            3. transfer from source to cell plate
            4. addition of cell suspension (for execution only, no worklist
               file support).

    Mastermix preparation worklists are always stored at the experiment
    design. The storage location for the cell plate preparation worklists
    differs.

    **Return Value:** updated experiment design (incl. all applicable
        worklist series)
    """
    NAME = 'Experiment Worklist Series Generator'
    #: The index for the optimem worklist within the experiment design series.
    OPTIMEM_WORKLIST_INDEX = 0
    #: The index for the reagent worklist within the experiment design series.
    REAGENT_WORKLIST_INDEX = 1

    def __init__(self, experiment_design, label, source_layout, scenario,
                 supports_mastermix, design_rack_associations=None,
                 parent=None):
        """
        Constructor.

        :param experiment_design: The experiment design for which to generate
            the worklist series.
        :type experiment_design:
            :class:`thelma.models.experiment.ExperimentDesign`
        :param str label: A label as prefix for the worklists.
        :param source_layout: The source plate layout.
        :type source_layout: :class:`TransfectionLayout`
        :param scenario: the experiment metadata type - it defines the
            storage location for the cell plate preparation worklists.
        :type scenario: :class:`thelma.models.experiment.ExperimentMetadataType`
        :param bool supports_mastermix: Flag indicating if the tool should
            create worklists for OptiMem and reagent dilution.
        :param design_rack_associations: Maps design rack labels to well
            association maps (created by the :class:`WellAssociator`).
        """
        BaseTool.__init__(self, parent=parent)
        #: The experiment design for which to generate the worklist series.
        self.experiment_design = experiment_design
        #: A label as prefix for the worklist name.
        self.label = label
        #: The transfection layout for the source plate (ISO plate).
        self.source_layout = source_layout
        #: The scenario defines the storage location for the cell plate
        #: preparation worklists.
        self.scenario = scenario
        #: Shall the tool create worklists for OptiMem and reagent dilution?
        self.supports_mastermix = supports_mastermix
        #: Maps well association maps onto design rack labels.
        self.design_rack_associations = design_rack_associations
        #: The worklist series for the experiment design (if applicable).
        self.__design_series = None
        #: The worklist series for each experiment design rack.
        self.__rack_worklists = None

    def reset(self):
        """
        Resets all values except for the initialisation values.
        """
        BaseTool.reset(self)
        self.__design_series = None
        self.__rack_worklists = None

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start generation of experiment worklists ...')

        self.__check_input()
        if not self.has_errors() and self.supports_mastermix:
            self.__create_mastermix_series()
        if not self.has_errors():
            self.__create_cell_plate_worklists()
        if not self.has_errors():
            self.experiment_design.worklist_series = self.__design_series
            self.return_value = self.experiment_design
            self.add_info('Worklist series generations completed.')

    def __check_input(self):
        # Checks the input values.
        self._check_input_class('experiment design', self.experiment_design,
                                ExperimentDesign)
        self._check_input_class('label', self.label, basestring)
        self._check_input_class('source layout', self.source_layout,
                                TransfectionLayout)
        self._check_input_class('"support mastermix" flag',
                                self.supports_mastermix, bool)
        storage_location = None
        if self._check_input_class('experiment scenario', self.scenario,
                                   ExperimentMetadataType):
            if not self.scenario.id in _SUPPORTED_SCENARIOS.ALL:
                d_names = _SUPPORTED_SCENARIOS.get_all_displaynames()
                msg = 'Unexpected scenario: "%s". Allowed scenarios: %s.' \
                      % (self.scenario, ', '.join(d_names))
                self.add_error(msg)
            else:
                storage_location = EXPERIMENT_WORKLIST_PARAMETERS.\
                                   STORAGE_LOCATIONS[self.scenario.id]

        if storage_location == EXPERIMENT_WORKLIST_PARAMETERS.\
                               EXPERIMENT_DESIGN_RACK:
            self._check_input_map_classes(self.design_rack_associations,
                            'design rack maps', 'design rack label', basestring,
                            'design rack layout', TransfectionLayout)

    def __create_mastermix_series(self):
        # Creates the worklist series for the mastermix preparation.
        self.add_debug('Create mastermix preparation worklist series ...')
        self.__design_series = WorklistSeries()
        self.__generate_optimem_worklist()
        self.__generate_reagent_worklist()

    def __generate_optimem_worklist(self):
        # Generates the optimem dilution worklist.
        generator = _OptimemWorklistGenerator(
                                    experiment_metadata_label=self.label,
                                    transfection_layout=self.source_layout)
        worklist = generator.get_result()

        if worklist is None:
            msg = 'Error when trying to generate optimem worklist.'
            self.add_error(msg)
        else:
            WorklistSeriesMember(planned_worklist=worklist,
                                 worklist_series=self.__design_series,
                                 index=self.OPTIMEM_WORKLIST_INDEX)

    def __generate_reagent_worklist(self):
        """
        Generates the transfection reagent worklist.
        """
        generator = _ReagentWorklistGenerator(self.label, self.source_layout,
                                              parent=self)
        worklist = generator.get_result()
        if worklist is None:
            msg = 'Error when trying to generate transfection reagent ' \
                  'worklist.'
            self.add_error(msg)
        else:
            # FIXME: Using instantiation for side effect.
            WorklistSeriesMember(planned_worklist=worklist,
                                 worklist_series=self.__design_series,
                                 index=self.REAGENT_WORKLIST_INDEX)

    def __create_cell_plate_worklists(self):
        # Creates the worklists for the cell suspension preparations.
        storage_location = EXPERIMENT_WORKLIST_PARAMETERS.STORAGE_LOCATIONS[
                                                            self.scenario.id]
        transfer_index = EXPERIMENT_WORKLIST_PARAMETERS.\
                            TRANSFER_WORKLIST_INDICES[storage_location]
        cell_index = EXPERIMENT_WORKLIST_PARAMETERS.\
                            CELL_WORKLIST_INDICES[storage_location]
        if storage_location == EXPERIMENT_WORKLIST_PARAMETERS.EXPERIMENT_DESIGN:
            self.__generate_cell_plate_worklist_for_experiment_design(
                                                    transfer_index, cell_index)
        else:
            self.__generate_cell_plate_worklist_for_racks(transfer_index,
                                                          cell_index)

    def __generate_cell_plate_worklist_for_experiment_design(self,
                                                    transfer_index, cell_index):
        # Generates the cell plate worklists for the experiment design as
        # storage location.
        self.add_debug('Create cell plate worklists for experiment design ...')
        if self.__design_series is None:
            self.__design_series = WorklistSeries()
        transfer_generator = _CybioTransferWorklistGenerator(self.label,
                                                             parent=self)
        self.__generate_transfer_worklist(transfer_generator, transfer_index,
                                          self.__design_series)
        for rack_pos, tf_pos in self.source_layout.iterpositions():
            tf_pos.cell_plate_positions = [rack_pos]
        cell_generator = _CellSuspensionWorklistGenerator(self.label,
                                                          self.source_layout,
                                                          parent=self)
        self.__generate_cell_worklist(cell_generator, cell_index,
                                      self.__design_series)

    def __generate_cell_plate_worklist_for_racks(self, transfer_index,
                                                 cell_index):
        # Generates the cell plate worklists for the experiment design racks
        # as storage locations.
        self.add_debug('Create cell plate worklists for design racks ...')
        for design_rack in self.experiment_design.experiment_design_racks:
            worklist_series = WorklistSeries()
            completed_layout = self.design_rack_associations[design_rack.label]
            label = '%s-%s' % (self.label, design_rack.label)
            transfer_generator = \
                    _BiomekTransferWorklistGenerator(label, completed_layout,
                                                     parent=self)
            self.__generate_transfer_worklist(transfer_generator,
                                              transfer_index, worklist_series)
            cell_generator = _CellSuspensionWorklistGenerator(label,
                                                              completed_layout,
                                                              parent=self)
            self.__generate_cell_worklist(cell_generator, cell_index,
                                          worklist_series)
            design_rack.worklist_series = worklist_series

    def __generate_transfer_worklist(self, generator, worklist_index,
                                     worklist_series):
        # Generates the transfer worklist.
        worklist = generator.get_result()
        if worklist is None:
            msg = 'Error when trying to generate transfer worklist for ' \
                  'screening scenario.'
            self.add_error(msg)
        else:
            # FIXME: Using instantiation for side effect.
            WorklistSeriesMember(planned_worklist=worklist,
                                 worklist_series=worklist_series,
                                 index=worklist_index)

    def __generate_cell_worklist(self, generator, worklist_index,
                                 worklist_series):
        # Generates the cell suspension worklist.
        worklist = generator.get_result()
        if worklist is None:
            msg = 'Error when trying to generate cell suspension worklist.'
            self.add_error(msg)
        else:
            # FIXME: Using instantiation for side effect.
            WorklistSeriesMember(planned_worklist=worklist,
                                 worklist_series=worklist_series,
                                 index=worklist_index)


class _OptimemWorklistGenerator(PlannedWorklistGenerator):
    """
    This tool generates a container dilution worklist for the
    ISO-to-Experiment-Plate worklist series.

    At this, it generates the first of four worklist (providing Optimem diluent
    to the wells of the source plate). The transfection positions here
    represent *target* positions.
    The worklist is only used for Biomek series.

    **Return Value:** :class:`PlannedWorklist` (type: SAMPLE_DILUTION)
    """
    NAME = 'Transfection OptiMem Worklist Generator'
    PIPETTING_SPECS_NAME = PIPETTING_SPECS_NAMES.BIOMEK
    #: The suffix for the worklist label.
    WORKLIST_SUFFIX = '_optimem'
    #: The name of the diluent.
    DILUENT_INFO = 'optimem'

    def __init__(self, experiment_metadata_label, transfection_layout,
                 parent=None):
        """
        Constructor.

        :param str experiment_metadata_label: The label for the experiment
            metadata the liquid transfer plan is generated for.
        :param transfection_layout: The source plate layout.
        :type transfection_layout: :class:`TransfectionLayout`
        """
        PlannedWorklistGenerator.__init__(self, parent=parent)
        #: The experiment metadata for which to generate the liquid transfer
        #: plan is generated.
        self.experiment_metadata_label = experiment_metadata_label

        #: The transfection (target well are mnot required).
        self.transfection_layout = transfection_layout

    def _check_input(self):
        """
        Checks the input values.
        """
        self._check_input_class('experiment metadata label',
                                self.experiment_metadata_label, basestring)
        self._check_input_class('transfection layout',
                                self.transfection_layout,
                                TransfectionLayout)

    def _set_label(self):
        """
        Sets label for the worklist.
        """
        self._label = '%s%s' % (self.experiment_metadata_label,
                                self.WORKLIST_SUFFIX)

    def _create_planned_liquid_transfers(self):
        """
        Generates the planned container dilution for the worklist.
        """
        self.add_debug('Generate planned container dilutions ...')

        for rack_pos, tf_pos in self.transfection_layout.iterpositions():
            if tf_pos.is_empty: continue
            volume = self.__determine_volume(tf_pos) / VOLUME_CONVERSION_FACTOR
            target_position = rack_pos
            psd = PlannedSampleDilution.get_entity(volume=volume,
                                           target_position=target_position,
                                           diluent_info=self.DILUENT_INFO)
            self._add_planned_transfer(psd)

    def __determine_volume(self, transfection_pos):
        # Determines the volume of the diluent.
        dil_factor = transfection_pos.optimem_dil_factor
        return float(transfection_pos.iso_volume) * (dil_factor - 1)


class _ReagentWorklistGenerator(PlannedWorklistGenerator):
    """
    This tool generates a container dilution worklist for the
    ISO-to-Experiment-Plate worklist series.

    At this, it generates the second of four worklists (adding transfection
    reagent to the molecule designs in the intermediate plate). The transfection
    positions here represent *target* positions.
    The worklist is only used for Biomek series.

    **Return Value:** planned worklist (type: SAMPLE_TRANSFER).
    """
    NAME = 'Transfection Reagent Worklist Generator'
    PIPETTING_SPECS_NAME = PIPETTING_SPECS_NAMES.BIOMEK
    #: The suffix for the worklist label.
    WORKLIST_SUFFIX = '_reagent'

    def __init__(self, experiment_metadata_label, transfection_layout,
                 parent=None):
        """
        Constructor.

        :param str experiment_metadata_label: The label for the experiment
            metadata the liquid transfer plan is generated for.
        :param transfection_layout: The source plate layout.
        :type transfection_layout: :class:`TransfectionLayout`
        """
        PlannedWorklistGenerator.__init__(self, parent=parent)
        #: The experiment metadata for which to generate the liquid transfer
        #: plan is generated.
        self.experiment_metadata_label = experiment_metadata_label
        #: The transfection (trget well are mnot required).
        self.transfection_layout = transfection_layout

    def _check_input(self):
        """
        Checks the input values.
        """
        self._check_input_class('experiment metadata label',
                                self.experiment_metadata_label, basestring)
        self._check_input_class('transfection layout',
                                self.transfection_layout,
                                TransfectionLayout)

    def _set_label(self):
        """
        Sets the label for the worklist.
        """
        self._label = '%s%s' % (self.experiment_metadata_label,
                                self.WORKLIST_SUFFIX)

    def _create_planned_liquid_transfers(self):
        """
        Generates the planned container dilutions for the worklist.
        """
        self.add_debug('Generate planned container dilutions ...')
        invalid_dil_factor = dict()
        for rack_pos, tf_pos in self.transfection_layout.iterpositions():
            if tf_pos.is_empty:
                continue
            dil_volume = tf_pos.calculate_reagent_dilution_volume() \
                         / VOLUME_CONVERSION_FACTOR
            ini_dil_factor = TransfectionParameters.\
                                calculate_initial_reagent_dilution(
                                float(tf_pos.reagent_dil_factor))
            if ini_dil_factor <= 1:
                add_list_map_element(invalid_dil_factor,
                                     tf_pos.reagent_dil_factor, rack_pos.label)
                continue
            rdf_str = get_trimmed_string(tf_pos.reagent_dil_factor)
            diluent_info = '%s (%s)' % (tf_pos.reagent_name, rdf_str)
            psd = PlannedSampleDilution.get_entity(volume=dil_volume,
                                           target_position=rack_pos,
                                           diluent_info=diluent_info)
            self._add_planned_transfer(psd)
        if len(invalid_dil_factor) > 0:
            msg = 'Invalid dilution reagent factor for rack positions: %s. ' \
                  'The factor would result in an initial dilution factor of ' \
                  'less then 1!' % (self._get_joined_map_str(invalid_dil_factor))
            self.add_error(msg)


class _BiomekTransferWorklistGenerator(PlannedWorklistGenerator):
    """
    This tool generates a container transfer worklist for the
    ISO-to-Experiment-Plate worklist series.

    At this, it generates the third of four worklist (transferring mastermix
    solution from the intermediate plate to the experiment plate). The
    transfection positions here represent *source* positions.
    The worklist is only used for Biomek series.

    **Return Value:** PlannedWorklist (type: SAMPLE_TRANSFER)
    """
    NAME = 'Transfection BioMek Transfer Worklist Generator'
    PIPETTING_SPECS_NAME = PIPETTING_SPECS_NAMES.BIOMEK
    #: The suffix for the worklist label.
    WORKLIST_SUFFIX = '_biomek_transfer'

    def __init__(self, label, transfection_layout, parent=None):
        """
        Constructor.

        :param str label: The label to put in front of the
            :attr:`WORKLIST_SUFFIX`.
        :param transfection_layout: The layout (including target positions)
            for the corresponding design rack.
        :type transfection_layout: :class:`TransfectionLayout`
        """
        PlannedWorklistGenerator.__init__(self, parent=parent)
        #: The label to put in front of the :attr:`WORKLIST_SUFFIX`.
        self.label = label
        #: Contains the transfection layout for the design rack (that is:
        #: *with* target wells).
        self.transfection_layout = transfection_layout

    def _check_input(self):
        """
        Checks whether the incoming layouts are transfection layouts.
        """
        self._check_input_class('label', self.label, basestring)
        self._check_input_class('transfection layout',
                                self.transfection_layout,
                                TransfectionLayout)

    def _set_label(self):
        """
        Sets label for the worklist.
        """
        self._label = '%s%s' % (self.label, self.WORKLIST_SUFFIX)

    def _create_planned_liquid_transfers(self):
        """
        Generates the planned container transfers for the worklist.
        """
        self.add_debug('Generate planned container transfer ...')
        volume = TransfectionParameters.TRANSFER_VOLUME \
                 / VOLUME_CONVERSION_FACTOR
        for rack_pos, tf_pos in self.transfection_layout.iterpositions():
            if tf_pos.is_empty:
                continue
            for target_pos in tf_pos.cell_plate_positions:
                pst = PlannedSampleTransfer.get_entity(volume=volume,
                            source_position=rack_pos,
                            target_position=target_pos)
                self._add_planned_transfer(pst)


class _CybioTransferWorklistGenerator(PlannedWorklistGenerator):
    """
    This tool creates a rack transfer worklist for the ISO-to-Experiment-Plate
    worklist series.

    At this, it generates the transfer worklist for screening cases
    (in which ISO and cell plate layout are equal).
    The worklist is *not* used for Biomek series.

    **Return Value:** PlannedWorklist (type: RACK_TRANSFER)
    """
    NAME = 'Transfection CyBio Transfer Worklist Generator'
    PIPETTING_SPECS_NAME = PIPETTING_SPECS_NAMES.CYBIO
    #: The suffix for the worklist label.
    WORKLIST_SUFFIX = '_cybio_transfer'
    #: The source sector index for the rack transfer.
    SOURCE_SECTOR_INDEX = 0
    #: The target sector index for the rack transfer.
    TARGET_SECTOR_INDEX = 0
    #: The number of sectors for the rack transfer.
    SECTOR_NUMBER = 1

    def __init__(self, experiment_metadata_label, parent=None):
        """
        Constructor.

        :param str experiment_metadata_label: The label for the experiment
            metadata the liquid transfer plan is generated for.
        """
        PlannedWorklistGenerator.__init__(self, parent=parent)
        #: The experiment metadata for which to generate the liquid transfer
        #: plan is generated.
        self.experiment_metadata_label = experiment_metadata_label

    def _check_input(self):
        """
        Checks the input values.
        """
        self._check_input_class('experiment metadata label',
                                self.experiment_metadata_label, basestring)

    def _set_label(self):
        """
        Sets label for the worklist.
        """
        self._label = '%s%s' % (self.experiment_metadata_label,
                                self.WORKLIST_SUFFIX)

    def _create_planned_liquid_transfers(self):
        """
        Generates the planned rack transfer for the worklist.
        """
        volume = TransfectionParameters.TRANSFER_VOLUME \
                 / VOLUME_CONVERSION_FACTOR
        try:
            prst = PlannedRackSampleTransfer.get_entity(
                                                    volume,
                                                    self.SECTOR_NUMBER,
                                                    self.SOURCE_SECTOR_INDEX,
                                                    self.TARGET_SECTOR_INDEX)
        except ValueError as err:
            msg = 'Invalid planned rack sample transfer (%d->%d, total %d).' \
                  'Details: %s.' \
                  % (self.SOURCE_SECTOR_INDEX, self.TARGET_SECTOR_INDEX,
                     self.SECTOR_NUMBER, err)
            self.add_error(msg)
        else:
            self._add_planned_transfer(prst)


class _CellSuspensionWorklistGenerator(PlannedWorklistGenerator):
    """
    This tool generates a container transfer worklist for the
    ISO-to-Experiment-Plate worklist series.

    At this, it generates the fourth of four worklists for the Biomek
    (adding cell suspension to the cell (experiment) plate. The ISO rack is
    not part of the plan.
    Instead, the cell (experiment) plate are target racks.

    **Return Value:** PlannedWorklist (type: CONTAINER_DILUTION)
    """
    NAME = 'Transfection Cell Suspension Worklist Generator'
    PIPETTING_SPECS_NAME = PIPETTING_SPECS_NAMES.BIOMEK
    #: The suffix for the worklist label.
    WORKLIST_SUFFIX = '_cellsuspension'
    #: #: The name of the diluent.
    DILUENT_INFO = 'cellsuspension'

    def __init__(self, label, transfection_layout, parent=None):
        """
        Constructor.

        ::param str label: The label to put in front of the
            :attr:`WORKLIST_SUFFIX`.
        :param transfection_layout: The layout (including target positions)
            for the corresponding design rack.
        :type transfection_layout: :class:`TransfectionLayout`
        """
        PlannedWorklistGenerator.__init__(self, parent=parent)
        #: The label to put in front of the :attr:`WORKLIST_SUFFIX`.
        self.label = label
        #: Contains the transfection layout for the design rack (that is:
        #: *with* target wells).
        self.transfection_layout = transfection_layout

    def _check_input(self):
        """
        Checks whether the incoming layouts are transfection layouts.
        """
        self._check_input_class('label', self.label, basestring)
        self._check_input_class('transfection layout',
                                self.transfection_layout,
                                TransfectionLayout)

    def _set_label(self):
        """
        Sets the label for the worklist.
        """
        self._label = '%s%s' % (self.label, self.WORKLIST_SUFFIX)

    def _create_planned_liquid_transfers(self):
        """
        Generates the planned container dilutions for the worklist.
        """
        self.add_debug('Generate planned container dilutions ...')
        volume = TransfectionParameters.TRANSFER_VOLUME * \
                 (TransfectionParameters.CELL_DILUTION_FACTOR - 1) \
                 / VOLUME_CONVERSION_FACTOR
        for tf_pos in self.transfection_layout.working_positions():
            if tf_pos.is_empty:
                continue
            for target_pos in tf_pos.cell_plate_positions:
                psd = PlannedSampleDilution.get_entity(volume=volume,
                                    target_position=target_pos,
                                    diluent_info=self.DILUENT_INFO)
                self._add_planned_transfer(psd)
