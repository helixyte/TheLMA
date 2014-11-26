"""
This module provides class to deal with experiment batch operations.

AAB
"""
from StringIO import StringIO
from thelma.automation.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.tools.base import BaseTool
from thelma.automation.tools.experiment.manual import ExperimentManualExecutor
from thelma.automation.tools.experiment.mastermix import get_experiment_executor
from thelma.automation.tools.experiment.mastermix import get_experiment_writer
from thelma.automation.tools.writers import create_zip_archive
from thelma.automation.tools.writers import read_zip_archive
from thelma.entities.experiment import Experiment
from thelma.entities.user import User

__docformat__ = 'reStructuredText en'

__all__ = ['ExperimentBatchTool',
           'ExperimentBatchManualExecutor',
           'ExperimentBatchWorklistWriter',
           'ExperimentBatchExecutor']


class ExperimentBatchTool(BaseTool):
    """
    An abstract base tool for experiment batch operations.

    **Return Value:** None (depending on the subclass).
    """
    def __init__(self, experiments, parent=None):
        """
        Constructor.

        :param experiments: A list of experiments that all belong
            to the same experiment design.
        :type experiments: :class:`list` of
            :class:`thelma.entities.experiment.Experiment`
        """
        BaseTool.__init__(self, parent=parent)
        #: A list of experiments that all belong to the same experiment design.
        self.experiments = experiments
        #: The experiment type of the experiment metadata.
        self._experiment_type = None

    def reset(self):
        BaseTool.reset(self)
        self._experiment_type = None

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start batch operation ...')
        self._check_input()
        if not self.has_errors():
            self.__fetch_experiments()
        if not self.has_errors():
            self._execute_experiment_task()

    def _check_input(self):
        """
        Checks whether all initialisation values are valid.
        """
        self.add_debug('Check input ...')
        self._check_input_list_classes('experiment', self.experiments,
                                       Experiment)

    def __fetch_experiments(self):
        """
        All experiments must belong to the same experiment metadata. Experiments
        that have already been updated are ignored.
        """
        self.add_debug('Fetch experiments ...')
        already_updated = []
        experiment_design = None
        for experiment in self.experiments:
            if experiment_design is None:
                experiment_design = experiment.experiment_design
            elif not experiment.experiment_design == experiment_design:
                msg = 'The experiments belong to different experiment ' \
                      'designs!' # there is no technical reason against
                self.add_error(msg)
                break
            has_been_updated = False
            for exp_rack in experiment.experiment_racks:
                if exp_rack.rack.status.name == ITEM_STATUS_NAMES.MANAGED:
                    has_been_updated = True
                    break
            if has_been_updated:
                already_updated.append(experiment.label)
        if not self.has_errors():
            self._experiment_type = experiment_design.experiment_metadata.\
                                    experiment_metadata_type

            if len(already_updated) > 0:
                already_updated.sort()
                msg = 'Some experiments in your selection have already been ' \
                      'updated in the DB: %s.' % (', '.join(already_updated))
                self.add_warning(msg)

    def _execute_experiment_task(self):
        """
        Overwrite this method to perform the tasks the tool is design
        for.
        """
        raise NotImplementedError('Abstract method.')


class ExperimentBatchManualExecutor(ExperimentBatchTool):
    """
    Runs the :class:`ExperimentManualExecutor` for all experiments that have
    not been updated so far.

    Return Value: list of updated experiments
    """
    NAME = 'Experiment Batch Manual Updater'

    def __init__(self, experiments, user, parent=None):
        """
        Constructor.

        :param user: The user who has committed the update.
        :type user: :class:`thelma.entities.user.User`
        """
        ExperimentBatchTool.__init__(self, experiments, parent=parent)
        #: The user who has committed the update.
        self.user = user

    def _check_input(self):
        ExperimentBatchTool._check_input(self)
        self._check_input_class('user', self.user, User)

    def _execute_experiment_task(self):
        """
        Runs the :class:`ExperimentManualExecutor` for :attr:`experiments`.
        """
        self.add_debug('Run manual updaters ...')
        updated_experiments = []
        for experiment in self.experiments:
            executor = ExperimentManualExecutor(experiment, self.user,
                                                parent=self)
            updated_experiment = executor.get_result()
            if updated_experiment is None:
                msg = 'Error when trying to update experiment "%s".' \
                      % (experiment.label)
                self.add_error(msg)
                break
            else:
                updated_experiments.append(updated_experiment)
        if not self.has_errors():
            self.return_value = updated_experiments
            self.add_info('Update runs completed.')


class ExperimentBatchWorklistWriter(ExperimentBatchTool):
    """
    Writes robot worklists for all experiments that have not been updated
    so far.

    Return Value: zip stream
    """
    NAME = 'Experiment Batch Worklist Writer'

    def __init__(self, experiments, parent=None):
        ExperimentBatchTool.__init__(self, experiments, parent=parent)
        #: Collects the zip streams for the experiments.
        self.__zip_streams = None

    def reset(self):
        ExperimentBatchTool.reset(self)
        self.__zip_streams = []

    def _execute_experiment_task(self):
        """
        Runs worklist writers for all experiments and merges the files
        into one zip file.
        """
        self.add_debug('Start batch worklist writing ...')

        if not self.has_errors(): self.__write_streams()
        if not self.has_errors():
            self.return_value = self.__summarize_streams()
            self.add_info('Worklists writing completed.')

    def __write_streams(self):
        # Writes the zip streams for the :attr:`experiments`.
        self.add_debug('Write streams ...')
        for experiment in self.experiments:
            kw = dict(experiment=experiment, parent=self)
            writer = self._run_and_record_error(get_experiment_writer,
                    base_msg='Error when trying to fetch writer for ' \
                             'experiment "%s": ' % (experiment.label),
                    error_types=TypeError, **kw)
            if writer is None:
                continue
            zip_stream = writer.get_result()
            if zip_stream is None:
                msg = 'Error when trying to generate worklists for ' \
                      'experiment "%s".' % (experiment.label)
                self.add_error(msg)
                break
            else:
                self.__zip_streams.append(zip_stream)

    def __summarize_streams(self):
        # Reads the zip streams and generates a new common archive.
        self.add_debug('Summarize zip archives ...')

        zip_map = dict()
        for zip_stream in self.__zip_streams:
            file_map = read_zip_archive(zip_stream)
            for fn, stream in file_map.iteritems(): zip_map[fn] = stream

        final_stream = StringIO()
        create_zip_archive(final_stream, zip_map)
        return final_stream


class ExperimentBatchExecutor(ExperimentBatchTool):
    """
    Runs the executor for all experiments that have not been updated so far.

    Return Value: list of updated experiments
    """
    NAME = 'Experiment Batch Executor'

    def __init__(self, experiments, user, parent=None):
        """
        Constructor.

        :param user: The user who has committed the update.
        :type user: :class:`thelma.entities.user.User`
        """
        ExperimentBatchTool.__init__(self, experiments, parent=parent)
        #: The user who has committed the update.
        self.user = user

    def _check_input(self):
        ExperimentBatchTool._check_input(self)
        self._check_input_class('user', self.user, User)

    def _execute_experiment_task(self):
        """
        Runs the executors for the :attr:`experiments`.
        """
        self.add_debug('Run executors ...')
        updated_experiments = []
        if not self.has_errors():
            for experiment in self.experiments:
                kw = dict(experiment=experiment, user=self.user, parent=self)
                executor = self._run_and_record_error(get_experiment_executor,
                        base_msg='Error when trying to fetch executor for ' \
                        'experiment "%s": ' % (experiment.label),
                        error_types=TypeError, **kw)
                if executor is None:
                    continue
                updated_experiment = executor.get_result()
                if updated_experiment is None:
                    msg = 'Error when trying to update experiment "%s".' \
                          % (experiment.label)
                    self.add_error(msg)
                    break
                else:
                    updated_experiments.append(experiment)
        if not self.has_errors():
            self.return_value = updated_experiments
            self.add_info('Execution runs completed.')
