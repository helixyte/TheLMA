"""
This module provides special :class:`ExperimentTool` classes for experiment
metadata types that provide mastermix support.

AAB
"""
from thelma.automation.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.experiment.base import ExperimentTool
from thelma.automation.tools.worklists.series import RackSampleTransferJob
from thelma.automation.tools.worklists.series import SampleTransferJob
from thelma.automation.tools.writers import merge_csv_streams


__all__ = ['ExperimentOptimisationWriterExecutor',
           'ExperimentScreeningWriterExecutor']


class ExperimentOptimisationWriterExecutor(ExperimentTool):
    """
    A special base ExperimentTool for optimisation scenarios.

    **Return Value:** a zip stream for for printing mode or executed worklists
        for execution mode
    """
    NAME = 'Experiment Robot-Optimisation Writer Executor'

    SUPPORTED_SCENARIOS = [EXPERIMENT_SCENARIOS.OPTIMISATION]
    FILE_SUFFIX_TRANSFER = '_biomek_transfer.csv'

    def _check_mastermix_compatibility(self):
        """
        Checks whether the worklist series allows for a complete
        execution (as opposed to a partial one) of the DB (requires the full
        set of worklist series).
        """
        self.add_debug('Check mastermix compatibility ...')

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

    def _create_all_transfer_jobs(self, add_cell_jobs):
        """
        Returns a list of all transfer jobs.
        """
        self._create_transfer_jobs_for_mastermix_preparation()
        if not self.has_errors():
            for design_rack_label in sorted(self._experiment_racks.keys()):
                self.__create_jobs_for_design_rack(design_rack_label,
                                                   add_cell_jobs)
                if self.has_errors() is None: break

    def _sort_experiment_racks(self):
        """
        Sorts the target experiment racks for each design rack by barcode
        (improves the readability of the generated transfer worklist file)
        -- for printing mode only.
        """
        self.add_debug('Sort experiment racks ...')

        for label, exp_rack_list in self._experiment_racks.iteritems():
            barcode_map = dict()
            for exp_rack in exp_rack_list:
                barcode_map[exp_rack.rack.barcode] = exp_rack
            sorted_list = []
            for barcode in sorted(barcode_map.keys()):
                sorted_list.append(barcode_map[barcode])
            self._experiment_racks[label] = sorted_list

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

            transfer_job = SampleTransferJob(index=counter,
                    planned_worklist=transfer_worklist,
                    target_rack=plate,
                    source_rack=self._source_plate,
                    ignored_positions=self._ignored_positions)
            self._transfer_jobs[counter] = transfer_job
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
        for pct in transfer_worklist.planned_liquid_transfers:
            source_pos = pct.source_position
            if source_pos in self._ignored_positions:
                cell_ignored_positions.append(pct.target_position)

        return cell_ignored_positions

    def _merge_streams(self, stream_map):
        """
        All transfer jobs are merged into one file. Optimem and reagent
        stream are from the merged stream map, too.
        """
        self._extract_mastermix_streams(stream_map)
        transfer_streams = dict()
        transfer_worklist = None
        for job_index, stream in stream_map.iteritems():
            transfer_streams[job_index] = stream
            if transfer_worklist is None:
                transfer_worklist = self._transfer_jobs[job_index].\
                                    planned_worklist

        transfer_stream = merge_csv_streams(transfer_streams)
        self._final_streams[self.FILE_SUFFIX_TRANSFER] = transfer_stream
        return dict()


class ExperimentScreeningWriterExecutor(ExperimentTool):
    """
    A special base ExperimentTool for screening and library scenarios.

    **Return Value:** a zip stream for for printing mode or executed worklists
        for execution mode
    """

    NAME = 'Experiment Screening Writer Executor'

    SUPPORTED_SCENARIOS = [EXPERIMENT_SCENARIOS.SCREENING,
                           EXPERIMENT_SCENARIOS.LIBRARY]
    FILE_SUFFIX_TRANSFER = '_cybio_transfers.txt'

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
        elif len(transfer_worklist.planned_liquid_transfers) > 1:
            msg = 'There is more than rack transfer in the transfer worklist!'
            self.add_error(msg)
            return None

        return transfer_worklist

    def _create_all_transfer_jobs(self, add_cell_jobs):
        """
        Returns the transfer jobs for the whole screening experiment design
        series.
        """
        transfer_worklist = self._get_rack_transfer_worklist()
        if not self.has_errors():
            self._create_transfer_jobs_for_mastermix_preparation()
            self.__create_cell_transfer_jobs(transfer_worklist, add_cell_jobs)

    def __create_cell_transfer_jobs(self, transfer_worklist, add_cell_jobs):
        """
        Returns the transfer jobs for the transfer to the experiment plates and
        the addition of cell suspension.
        """
        self.add_debug('Create cell plate transfer jobs ...')

        rack_transfer = transfer_worklist.planned_liquid_transfers[0]
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

                transfer_job = RackSampleTransferJob(index=counter,
                            planned_rack_sample_transfer=rack_transfer,
                            target_rack=plate, source_rack=self._source_plate)
                self._transfer_jobs[counter] = transfer_job
                self._rack_transfer_worklists[counter] = transfer_worklist
                counter += 1

                if add_cell_jobs and not self.has_errors():
                    counter = self._add_cell_suspension_job(cell_worklist,
                                    counter, plate, self._ignored_positions)

    def _get_rack_transfer_stream(self, stream_map):
        stream = ExperimentTool._get_rack_transfer_stream(self, stream_map)
        if not stream is None:
            self._final_streams[self.FILE_SUFFIX_TRANSFER] = stream


def get_experiment_writer(experiment, log=None, **kw):
    """
    Factory method returning the writer/executor for the passed experiment
    in printing mode.

    :param experiment: The experiment for which to generate the robot worklists.
    :type experiment: :class:`thelma.models.experiment.Experiment`

    :param log: The ThelmaLog to write into (if used as part of a batch).
    :type log: :class:`thelma.ThelmaLog`
    :default log: *None*

    :raises TypeError: if the experiment metadata type is not supported.
    """
    return __get_writer_executor(mode=ExperimentTool.MODE_PRINT_WORKLISTS,
                                 experiment=experiment, log=log, **kw)

def get_experiment_executor(experiment, user, log=None, **kw):
    """
    Factory method returning the writer/executor for the passed experiment
    in execution mode.

    :param experiment: The experiment to execute.
    :type experiment: :class:`thelma.models.experiment.Experiment`

    :param user: The user who conducts the DB update.
    :type user: :class:`thelma.models.user.User`

    :param log: The ThelmaLog to write into (if used as part of a batch).
    :type log: :class:`thelma.ThelmaLog`
    :default log: *None*

    :raises TypeError: if the experiment metadata type is not supported.
    """
    return __get_writer_executor(mode=ExperimentTool.MODE_EXECUTE, user=user,
                                 experiment=experiment, log=log, **kw)

def __get_writer_executor(mode, experiment, user=None, log=None, **kw):
    """
    Helper factory method creating an experiment writer/executor for
    for the passed experiment type in the given mode.
    """
    experiment_type = experiment.experiment_design.experiment_metadata_type
    if experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING or \
                            experiment_type.id == EXPERIMENT_SCENARIOS.LIBRARY:
        tool_cls = ExperimentScreeningWriterExecutor
    elif experiment_type.id == EXPERIMENT_SCENARIOS.OPTIMISATION:
        tool_cls = ExperimentOptimisationWriterExecutor
    else:
        msg = 'This experiment type (%s) does not support robot ' \
              'worklists!' % (experiment_type.display_name)
        if log is None:
            raise TypeError(msg)
        else:
            log.add_error(msg)
            return None

    kw.update(dict(mode=mode, experiment=experiment, user=user, log=log))
    return tool_cls(**kw)


