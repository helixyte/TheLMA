"""
This module provides base classes for tools dealing with experiments.
The :class:`ExperimentTool` fetches experiment data such as the source rack,
the experiment racks and the worklist series.

:class:`ExperimentOptimisationTool` and :class:`ExperimentScreeningTool`
(inheriting from :class:`ExperimentTool`) provides lists of transfer jobs for
the mastermix preparation and the cell plate preparation. These lists can be
used be series tools.

AAB
"""
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionLayoutConverter
from thelma.automation.tools.metadata.transfection_utils \
    import TransfectionParameters
from thelma.automation.tools.metadata.worklist \
    import EXPERIMENT_WORKLIST_PARAMETERS
from thelma.automation.tools.metadata.worklist \
    import ExperimentWorklistGenerator
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.tools.semiconstants import PIPETTING_SPECS_NAMES
from thelma.automation.tools.semiconstants import RESERVOIR_SPECS_NAMES
from thelma.automation.tools.semiconstants import get_reservoir_spec
from thelma.automation.tools.utils.iso import IsoLayoutConverter
from thelma.automation.tools.worklists.series import ContainerDilutionJob
from thelma.automation.tools.worklists.series import ContainerTransferJob
from thelma.automation.tools.worklists.series import RackTransferJob
from thelma.models.experiment import Experiment
import logging

__docformat__ = 'reStructuredText en'

__all__ = ['ExperimentTool',
           'ExperimentOptimisationTool',
           'ExperimentScreeningTool']


class ExperimentTool(BaseAutomationTool):
    """
    An abstract base class for tools dealing with experiment (fetching
    experiment data).

    **Return Value:** None
    """

    #: The experiment types supported by this tool.
    SUPPORTED_EXPERIMENT_SCENARIOS = []

    #: The default volume of a sample in an experiment plate (in ul).
    DEFAULT_SAMPLE_VOLUME = TransfectionParameters.TRANSFER_VOLUME * \
                            TransfectionParameters.CELL_DILUTION_FACTOR
    #: May mock positions be empty in the ISO rack?
    MOCKS_MAY_BE_EMPTY = False

    #: The index of the optimem worklist in the experiment design series.
    OPTIMEM_WORKLIST_INDEX = ExperimentWorklistGenerator.OPTIMEM_WORKLIST_INDEX
    #: The index of the optimem worklist in the experiment design series.
    REAGENT_WORKLIST_INDEX = ExperimentWorklistGenerator.REAGENT_WORKLIST_INDEX

    #: The barcode of the reservoir providing the optimem medium.
    OPTIMEM_PLATE_BARCODE = 'optimem_plate'
    #: The barcode of the reservoir providing the transfection reagent.
    REAGENT_PLATE_BARCODE = 'complexes'

    def __init__(self, experiment, logging_level=logging.WARNING,
                 add_default_handlers=False, log=None):
        """
        Constructor:

        :param experiment: The experiment for which to generate the BioMek
                worklists.
        :type experiment: :class:`thelma.models.experiment.Experiment`

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *True*

        :param log: The ThelmaLog to write into (if used as part of a batch).
        :type log: :class:`thelma.ThelmaLog`

        """
        depending = not log is None
        BaseAutomationTool.__init__(self, log=log,
                                    logging_level=logging_level,
                                    add_default_handlers=add_default_handlers,
                                    depending=depending)

        #: The experiment for which to generate the rack.
        self.experiment = experiment

        #: The experiment metadata type
        #: (:class:`thelma.models.experiment.ExperimentMetadataType`).
        self._scenario = None
        #: The worklist series of the experiment design
        #: (:class:`thelma.models.liquidtransfer.WorklistSeries`).
        self._design_series = None
        #: The worklist series for the design racks mapped onto design
        #: racks labels (if there are any).
        #: (:class:`thelma.models.liquidtransfer.WorklistSeries`).
        self._design_rack_series_map = None
        #: The index of the transfer worklist within a valid design rack series.
        self._transfer_worklist_index = None
        #: The index of the cell worklist within a valid design rack series.
        self._cell_worklist_index = None

        #: Maps experiment racks onto the design rack they belong to.
        self._experiment_racks = None
        #: The source plate (ISO plate) for this experiment.
        self._iso_plate = None

        #: The ISO layout for this experiment.
        self._iso_tf_layout = None
        #: A list of rack position to be ignore during execution or worklist
        #: generation. The rack position are floating position for which
        #: there were no molecule design pools left anymore.
        self._ignored_positions = None

        #: The complete series of transfer jobs (ready-to-use).
        self._transfer_jobs = None

    def reset(self):
        """
        Resets all attributes except for the initialisation values.
        """
        BaseAutomationTool.reset(self)
        self._scenario = None
        self._design_series = None
        self._design_rack_series_map = dict()
        self._transfer_worklist_index = None
        self._cell_worklist_index = None
        self._experiment_racks = dict()
        self._iso_plate = None
        self._iso_tf_layout = None
        self._ignored_positions = None
        self._transfer_jobs = []

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self._check_input()
        if not self.has_errors(): self._check_experiment_type()
        if not self.has_errors():
            self.__fetch_experiment_data()
            self.__check_for_previous_execution()
        if not self.has_errors() and \
                    not self._scenario.id == EXPERIMENT_SCENARIOS.ISO_LESS:
            if not self.has_errors():self.__fetch_iso_layout()
            if not self.has_errors():
                self._ignored_positions = self.__find_ignored_positions()

        if not self.has_errors(): self._execute_task()

    def _check_input(self):
        """
        Checks whether all initialisation values are valid.
        """
        self.add_debug('Check input ...')
        self._check_input_class('experiment', self.experiment, Experiment)

    def _check_experiment_type(self):
        """
        Ensures that the tool is supporting the given experiment type.
        """
        self.add_debug('Check experiment type ...')

        self._scenario = self.experiment.experiment_design.\
                         experiment_metadata_type

        if not self._scenario.id in self.SUPPORTED_EXPERIMENT_SCENARIOS:
            msg = 'The type of this experiment is not supported by this tool ' \
                  '(given: %s, supported: %s).' % (self._scenario.display_name,
                   ', '.join(EXPERIMENT_SCENARIOS.get_displaynames(
                                        self.SUPPORTED_EXPERIMENT_SCENARIOS)))
            self.add_error(msg)
        elif self._scenario.id == EXPERIMENT_SCENARIOS.ISO_LESS:
            pass # there are no worklists for ISO-less experiments
        else:
            storage_location = EXPERIMENT_WORKLIST_PARAMETERS.STORAGE_LOCATIONS[
                                                            self._scenario.id]
            self._transfer_worklist_index = EXPERIMENT_WORKLIST_PARAMETERS.\
                                    TRANSFER_WORKLIST_INDICES[storage_location]
            self._cell_worklist_index = EXPERIMENT_WORKLIST_PARAMETERS.\
                                    CELL_WORKLIST_INDICES[storage_location]

    def __fetch_experiment_data(self):
        """
        Sets the transfer plans and experiment racks for the different
        design racks.
        """
        self.add_debug('Set transfer plans and experiment racks ...')

        experiment_design = self.experiment.experiment_design
        self._iso_plate = self.experiment.source_rack
        self._design_series = experiment_design.worklist_series

        design_racks = self.experiment.experiment_design.design_racks
        for design_rack in design_racks:
            self._experiment_racks[design_rack.label] = []
            worklist_series = design_rack.worklist_series
            if worklist_series is None: continue
            self._design_rack_series_map[design_rack.label] = worklist_series

        for experiment_rack in self.experiment.experiment_racks:
            design_rack_label = experiment_rack.design_rack.label
            if not self._experiment_racks.has_key(design_rack_label):
                msg = 'Unknown design rack "%s" for experiment rack "%s"!' \
                      % (design_rack_label, experiment_rack.rack.barcode)
                self.add_error(msg)
            self._experiment_racks[design_rack_label].append(experiment_rack)

    def __check_for_previous_execution(self):
        """
        Makes sure the experiment has not been executed before.
        """
        self.add_debug('Check for previous execution ...')

        has_been_executed = False

        for exp_rack_list in self._experiment_racks.values():
            for exp_rack in exp_rack_list:
                if exp_rack.rack.status.name == ITEM_STATUS_NAMES.MANAGED:
                    has_been_executed = True
                    break

        if has_been_executed:
            if self._scenario.id == EXPERIMENT_SCENARIOS.ISO_LESS:
                exp_detail = 'experiment "%s"' % (self.experiment.label)
            else:
                exp_detail = 'source plate %s' % (self._iso_plate.barcode)
            msg = 'The database update for %s has already been made before!' \
                  % (exp_detail)
            self.add_error(msg)

    def __fetch_iso_layout(self):
        """
        Fetches the ISO layout for the source rack (needed to determine
        floating positions (which might in contrast to fixed positions be
        empty).
        """
        self.add_debug('Fetch ISO layout ...')

        exp_metadata = self.experiment.experiment_design.experiment_metadata
        iso_request = exp_metadata.iso_request

        if self._scenario.id == EXPERIMENT_SCENARIOS.MANUAL:
            converter = IsoLayoutConverter(log=self.log,
                                        rack_layout=iso_request.iso_layout)
        else:
            converter = TransfectionLayoutConverter(log=self.log,
                                        rack_layout=iso_request.iso_layout,
                                        is_iso_layout=False)
        self._iso_tf_layout = converter.get_result()

        if self._iso_tf_layout is None:
            msg = 'Could not convert ISO transfection layout!'
            self.add_error(msg)
        else:
            layout_shape = self._iso_tf_layout.shape
            rack_shape = self._iso_plate.specs.shape
            if not layout_shape == rack_shape:
                msg = 'The rack shape of ISO layout (%s) and ISO rack (%s) ' \
                      'do not match!' % (layout_shape, rack_shape)
                self.add_error(msg)

    def __find_ignored_positions(self):
        """
        Determines positions that can be ignored (caused by floating positions
        for which there was no molecule design pool left anymore).
        """
        if not self._iso_tf_layout.has_floatings(): return []

        ignored_positions = []
        missing_fixed_positions = []

        for container in self._iso_plate.containers:
            rack_pos = container.location.position
            sample = container.sample
            if not (sample is None or sample.volume is None or \
                    sample.volume == 0):
                continue
            iso_pos = self._iso_tf_layout.get_working_position(rack_pos)
            if iso_pos is None or iso_pos.is_empty or iso_pos.is_mock: continue
            if iso_pos.is_floating:
                ignored_positions.append(rack_pos)
            else:
                missing_fixed_positions.append(rack_pos.label)

        if len(missing_fixed_positions) > 0:
            msg = 'Some wells of the ISO rack which should contain controls ' \
                  'are empty: %s!' % (missing_fixed_positions)
            self.add_error(msg)

        return ignored_positions

    def _execute_task(self):
        """
        Overwrite this method to perform the tasks the tool is design
        for.
        """
        self.add_error('Abstract method: _execute_task()')

    def _get_optimem_worklist(self):
        """
        A helper function returning the worklist for the transfer to the
        experiment plates.
        """
        return self.__get_worklist_by_index(self._design_series,
                                            self.OPTIMEM_WORKLIST_INDEX)

    def _get_reagent_worklist(self):
        """
        A helper function returning the worklist for the transfer to the
        experiment plates.
        """
        return self.__get_worklist_by_index(self._design_series,
                                            self.REAGENT_WORKLIST_INDEX)

    def _create_optimem_job(self, optimem_worklist):
        """
        Helper function creating an optimem dilution job.
        """
        quarter_rs = get_reservoir_spec(RESERVOIR_SPECS_NAMES.QUARTER_MODULAR)

        optimem_job = ContainerDilutionJob(index=0,
                       planned_worklist=optimem_worklist,
                       target_rack=self._iso_plate,
                       reservoir_specs=quarter_rs,
                       source_rack_barcode=self.OPTIMEM_PLATE_BARCODE,
                       ignored_positions=self._ignored_positions,
                       pipetting_specs=PIPETTING_SPECS_NAMES.BIOMEK)
        return optimem_job

    def _create_reagent_job(self, reagent_worklist):
        """
        Helper function creating an transfection reagent dilution job.
        """
        tube_24_rs = get_reservoir_spec(RESERVOIR_SPECS_NAMES.TUBE_24)

        optimem_job = ContainerDilutionJob(index=1,
                       planned_worklist=reagent_worklist,
                       target_rack=self._iso_plate,
                       reservoir_specs=tube_24_rs,
                       source_rack_barcode=self.REAGENT_PLATE_BARCODE,
                       ignored_positions=self._ignored_positions,
                       pipetting_specs=PIPETTING_SPECS_NAMES.BIOMEK)
        return optimem_job

    def _create_transfer_jobs_for_mastermix_preparation(self):
        """
        Return the transfer jobs for the mastermix preparation.
        """
        self.add_debug('Create mastermix transfer jobs ...')

        optimem_worklist = self._get_optimem_worklist()
        if optimem_worklist is None:
            msg = 'Could not get worklist for Optimem dilution.'
            self.add_error(msg)

        reagent_worklist = self._get_reagent_worklist()
        if reagent_worklist is None:
            msg = 'Could not get worklist for addition of transfection ' \
                  'reagent.'
            self.add_error(msg)

        if self.has_errors(): return None

        optimem_job = self._create_optimem_job(optimem_worklist)
        reagent_job = self._create_reagent_job(reagent_worklist)

        self._transfer_jobs = [optimem_job, reagent_job]

    def _get_transfer_worklist(self, worklist_series):
        """
        A helper function returning the worklist for the transfer to the
        experiment plates.
        """
        return self.__get_worklist_by_index(worklist_series,
                                            self._transfer_worklist_index)

    def _get_cell_suspension_worklist(self, worklist_series):
        """
        A helper function returning the worklist for the addition of cell
        suspension to the experiment plates.
        """
        return self.__get_worklist_by_index(worklist_series,
                                            self._cell_worklist_index)

    def __get_worklist_by_index(self, worklist_series, worklist_index):
        """
        Helper function return worklist for a certain index within a
        worklist series.
        """
        for worklist in worklist_series:
            if worklist.index == worklist_index:
                return worklist

        return None

    def _add_cell_suspension_job(self, cell_worklist, job_index, plate,
                                 cell_ignored_positions):
        """
        Helper function registering a container dilution job for the given
        worklist, plate and job index. In addition, in increments the
        job index.
        """
        falcon_reservoir = get_reservoir_spec(
                                            RESERVOIR_SPECS_NAMES.FALCON_MANUAL)
        cell_job = ContainerDilutionJob(index=job_index,
                    planned_worklist=cell_worklist,
                    target_rack=plate,
                    reservoir_specs=falcon_reservoir,
                    ignored_positions=cell_ignored_positions,
                    pipetting_specs=PIPETTING_SPECS_NAMES.MANUAL)
        self._transfer_jobs.append(cell_job)
        job_index += 1
        return job_index


class ExperimentOptimisationTool(ExperimentTool):
    """
    A special base ExperimentTool for optimisation scenarios.
    """

    SUPPORTED_EXPERIMENT_SCENARIOS = [EXPERIMENT_SCENARIOS.OPTIMISATION]

    def _check_mastermix_compatibility(self):
        """
        Checks whether the worklist series allows for a complete
        execution (as opposed to a partial one) of the DB (requires the full
        set of worklist series).
        """
        self.add_debug('Check compatibility.')

        invalid = False

        if self._design_series is None:
            invalid = True
        else:
            for worklist_series in self._design_rack_series_map.values():
                if not len(worklist_series) == 2:
                    invalid = True
                    break

        if invalid:
            msg = 'This experiment is not Biomek-compatible. The system ' \
                  'cannot provide Biomek worklists for it. If you have ' \
                  'attempted to update the DB, use the "manual" option ' \
                  'instead, please.'
            self.add_error(msg)

    def _create_all_transfer_jobs(self, add_cell_worklists=False):
        """
        Returns a list of all transfer jobs.
        """
        self._create_transfer_jobs_for_mastermix_preparation()
        if not self._transfer_jobs is None:
            design_rack_labels = self._experiment_racks.keys()
            design_rack_labels.sort()

            for design_rack_label in design_rack_labels:

                self.__create_jobs_for_design_rack(design_rack_label,
                                                   add_cell_worklists)
                if self.has_errors() is None: break

    def __create_jobs_for_design_rack(self, design_rack_label,
                                      add_cell_worklists=True):
        """
        Returns a list of transfer jobs preparing the cell plates for a
        particular design rack.
        """
        self.add_debug('Create design rack transfer jobs ...')

        worklist_series = self._design_rack_series_map[design_rack_label]

        transfer_worklist = self._get_transfer_worklist(worklist_series)
        if transfer_worklist is None:
            msg = 'Could not get worklist for plate transfer to experiment ' \
                  'rack for design rack "%s".' % (design_rack_label)
            self.add_error(msg)

        cell_worklist = self._get_cell_suspension_worklist(worklist_series)
        if cell_worklist is None:
            msg = 'Could not get worklist for addition of cell ' \
                  'suspension for design rack "%s".' % (design_rack_label)
            self.add_error(msg)

        if self.has_errors(): return None

        cell_ignored_positions = None
        if add_cell_worklists:
            cell_ignored_positions = self.__find_cell_ignored_positions(
                                                              transfer_worklist)
        counter = len(self._transfer_jobs)
        for experiment_rack in self._experiment_racks[design_rack_label]:
            plate = experiment_rack.rack

            transfer_job = ContainerTransferJob(index=counter,
                    planned_worklist=transfer_worklist,
                    target_rack=plate,
                    source_rack=self._iso_plate,
                    ignored_positions=self._ignored_positions,
                    pipetting_specs=PIPETTING_SPECS_NAMES.BIOMEK)
            self._transfer_jobs.append(transfer_job)
            counter += 1

            if not add_cell_worklists: continue
            counter = self._add_cell_suspension_job(cell_worklist, counter,
                                             plate, cell_ignored_positions)

    def __find_cell_ignored_positions(self, transfer_worklist):
        """
        Helper function determining the ignored position for a cell suspension
        worklist.
        """
        cell_ignored_positions = []
        for pct in transfer_worklist.planned_transfers:
            source_pos = pct.source_position
            if source_pos in self._ignored_positions:
                cell_ignored_positions.append(pct.target_position)

        return cell_ignored_positions


class ExperimentScreeningTool(ExperimentTool):
    """
    A special base ExperimentTool for screening scenarios.
    """

    SUPPORTED_EXPERIMENT_SCENARIOS = [EXPERIMENT_SCENARIOS.SCREENING]

    MOCKS_MAY_BE_EMPTY = True

    def _check_mastermix_compatibility(self):
        """
        Checks whether the experiment design worklist contains worklist
        for the optimem and the reagent dilution.
        """
        if not len(self._design_series) == 4:
            msg = 'The system cannot provide Biomek worklists for the ' \
                  'mastermix preparation of this experiment. If you have ' \
                  'attempted to update the DB, use the "manual" option ' \
                  'instead, please.'
            self.add_error(msg)

    def _get_rack_transfer_worklist(self):
        """
        Returns the planned rack transfer from the ISO to experiment plate
        transfer.
        """
        transfer_worklist = self._get_transfer_worklist(self._design_series)
        if transfer_worklist is None:
            msg = 'Could not get worklist for transfer from ISO to ' \
                  'experiment plate.'
            self.add_error(msg)
            return None
        elif len(transfer_worklist.planned_transfers) > 1:
            msg = 'There is more than rack transfer in the transfer worklist!'
            self.add_error(msg)
            return None

        return transfer_worklist

    def _create_all_transfer_jobs(self, transfer_worklist,
                                  add_cell_jobs=False):
        """
        Returns the transfer jobs for the whole screening experiment design
        series.
        """
        self.add_debug('Create transfer jobs ...')

        self._create_transfer_jobs_for_mastermix_preparation()
        self.__create_cell_transfer_jobs(transfer_worklist, add_cell_jobs)

    def __create_cell_transfer_jobs(self, transfer_worklist, add_cell_jobs):
        """
        Returns the transfer jobs for the transfer to the experiment plates and
        the addition of cell suspension.
        """
        self.add_debug('Create cell plate transfer jobs ...')

        rack_transfer = transfer_worklist.planned_transfers[0]
        cell_worklist = self._get_cell_suspension_worklist(self._design_series)
        if cell_worklist is None:
            msg = 'Could not get worklist for transfer for the addition ' \
                  'of cell suspension.'
            self.add_error(msg)

        counter = 2

        design_rack_labels = self._experiment_racks.keys()
        design_rack_labels.sort()
        for design_rack_label in design_rack_labels:

            experiment_plates = self._experiment_racks[design_rack_label]
            for experiment_plate in experiment_plates:
                plate = experiment_plate.rack

                transfer_job = RackTransferJob(index=counter,
                                planned_rack_transfer=rack_transfer,
                                target_rack=plate,
                                source_rack=self._iso_plate)
                self._transfer_jobs.append(transfer_job)
                counter += 1

                if add_cell_jobs and not self.has_errors():
                    counter = self._add_cell_suspension_job(cell_worklist,
                                    counter, plate, self._ignored_positions)
