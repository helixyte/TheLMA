"""
This module provides class to deal with experiment batch operations.

AAB
"""
from StringIO import StringIO
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.experiment.executor \
    import ExperimentExecutorOptimisation
from thelma.automation.tools.experiment.executor \
    import ExperimentExecutorScreening
from thelma.automation.tools.experiment.manual import ExperimentRackFiller
from thelma.automation.tools.experiment.writer \
    import ExperimentWorklistWriterOptimisation
from thelma.automation.tools.experiment.writer \
    import ExperimentWorklistWriterScreening
from thelma.automation.tools.semiconstants import EXPERIMENT_SCENARIOS
from thelma.automation.tools.semiconstants import ITEM_STATUS_NAMES
from thelma.automation.tools.writers import create_zip_archive
from thelma.automation.tools.writers import read_zip_archive
from thelma.models.job import ExperimentJob
from thelma.models.user import User
import logging

__docformat__ = 'reStructuredText en'

__all__ = ['ExperimentBatchTool',
           'ExperimentBatchRackFiller',
           'ExperimentBatchWorklistWriter',
           'ExperimentBatchExecutor']


class ExperimentBatchTool(BaseAutomationTool):
    """
    An abstract base tool for experiment batch operations.

    **Return Value:** None (depending on the subclass).
    """

    def __init__(self, experiment_jobs, logging_level=logging.WARNING,
                add_default_handlers=False):
        """
        Constructor:

        :param experiment_jobs: A list of experiment jobs that all belong
            to the same experiment design.
        :type experiment_jobs: :class:`list` of
            :class:`thelma.models.job.ExperimentJob`

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *True*
        """
        BaseAutomationTool.__init__(self, log=None,
                                    logging_level=logging_level,
                                    add_default_handlers=add_default_handlers,
                                    depending=False)

        #: A list of experiment jobs.
        self.experiment_jobs = experiment_jobs

        #: The experiment for which to conduct the operations (only one
        #: that have not been updated so far).
        self._experiments = None
        #: The experiment type of the experiment metadata.
        self._experiment_type = None

    def reset(self):
        BaseAutomationTool.reset(self)
        self._experiments = []
        self._experiment_type = None

    def run(self):
        """
        Runs the tool.
        """
        self.reset()
        self.add_info('Start batch operation ...')

        self._check_input()
        if not self.has_errors(): self.__fetch_experiments()
        if not self.has_errors(): self._execute_task()

    def _check_input(self):
        """
        Checks whether all initialisation values are valid.
        """
        self.add_debug('Check input ...')

        if self._check_input_class('experiment job list', self.experiment_jobs,
                                   list):
            for ej in self.experiment_jobs:
                if not self._check_input_class('experiment job', ej,
                                               ExperimentJob): break

    def __fetch_experiments(self):
        """
        All experiments must belong to the same experiment metadata. Experiments
        that have already been updated are ignored.
        """
        self.add_debug('Fetch experiments ...')

        already_updated = []
        experiment_design = None

        for ej in self.experiment_jobs:
            for experiment in ej.experiments:

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
                else:
                    self._experiments.append(experiment)

        if not self.has_errors():

            if len(self._experiments) < 1:
                msg = 'There are no experiments awaiting update in your ' \
                      'selection!'
                self.add_error(msg)
            else:
                self._experiment_type = experiment_design.\
                                        experiment_metadata_type

            if len(already_updated) > 0:
                already_updated.sort()
                msg = 'Some experiments in your selection have already been ' \
                      'updated in the DB: %s.' % (', '.join(already_updated))
                self.add_warning(msg)

    def _execute_task(self):
        """
        Overwrite this method to perform the tasks the tool is design
        for.
        """
        self.add_error('Abstract method: _execute_task()')


class ExperimentBatchRackFiller(ExperimentBatchTool):
    """
    Runs the :class:`ExperimentRackFiller` for all experiments that have
    not been updated so far.

    Return Value: list of updated experiments
    """

    NAME = 'Experiment Batch Manual Updater'

    def __init__(self, experiment_jobs, user,
                 logging_level=logging.WARNING, add_default_handlers=False):
        """
        Constructor:

        :param experiment_jobs: A list of experiment jobs that all belong
            to the same experiment design.
        :type experiment_jobs: :class:`list` of
            :class:`thelma.models.job.ExperimentJob`

        :param user: The user who has committed the update.
        :type user: :class:`thelma.models.user.User`

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *True*
        """
        ExperimentBatchTool.__init__(self, experiment_jobs=experiment_jobs,
                                     logging_level=logging_level,
                                     add_default_handlers=add_default_handlers)

        #: The user who has committed the update.
        self.user = user

    def _check_input(self):
        ExperimentBatchTool._check_input(self)
        self._check_input_class('user', self.user, User)

    def _execute_task(self):
        """
        Runs the :class:`ExperimentRackFiller` for :attr:`_experiments`.
        """
        self.add_debug('Run manual updaters ...')

        updated_experiments = []
        for experiment in self._experiments:
            filler = ExperimentRackFiller.create(experiment=experiment,
                                          user=self.user, log=self.log)
            updated_experiment = filler.get_result()
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

    def __init__(self, experiment_jobs,
                 logging_level=logging.WARNING, add_default_handlers=False):
        """
        Constructor:

        :param experiment_jobs: A list of experiment jobs that all belong
            to the same experiment design.
        :type experiment_jobs: :class:`list` of
            :class:`thelma.models.job.ExperimentJob`

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *True*
        """
        ExperimentBatchTool.__init__(self, experiment_jobs=experiment_jobs,
                                     logging_level=logging_level,
                                     add_default_handlers=add_default_handlers)

        #: The class for the writer (depends on :attr:`_experiment_type`).
        self.__writer_cls = None
        #: Collects the zip streams for the experiments.
        self.__zip_streams = None

    def reset(self):
        ExperimentBatchTool.reset(self)
        self.__zip_streams = []

    def _execute_task(self):
        """
        Runs worklist writers for all experiments and merges the files
        into one zip file.
        """
        self.add_debug('Start batch worklist writing ...')

        self.__get_writer_cls()
        if not self.has_errors(): self.__write_streams()
        if not self.has_errors():
            self.return_value = self.__summarize_streams()
            self.add_info('Worklists writing completed.')

    def __get_writer_cls(self):
        """
        The writer class depends on the experiment type.
        """
        if self._experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
            self.__writer_cls = ExperimentWorklistWriterScreening
        elif self._experiment_type.id == EXPERIMENT_SCENARIOS.OPTIMISATION:
            self.__writer_cls = ExperimentWorklistWriterOptimisation
        else:
            msg = 'This experiment type (%s) does not support robot ' \
                  'worklists!' % (self._experiment_type.display_name)
            self.add_error(msg)

    def __write_streams(self):
        """
        Writes the zip streams for the :attr:`_experiments`.
        """
        self.add_debug('Write streams ...')

        for experiment in self._experiments:
            kw = dict(experiment=experiment, log=self.log)
            writer = self.__writer_cls(**kw)
            zip_stream = writer.get_result()
            if zip_stream is None:
                msg = 'Error when trying to generate worklists for ' \
                      'experiment "%s".' % (experiment.label)
                self.add_error(msg)
                break
            else:
                self.__zip_streams.append(zip_stream)

    def __summarize_streams(self):
        """
        Reads the zip streams and generates a new common archive.
        """
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

    def __init__(self, experiment_jobs, user,
                 logging_level=logging.WARNING, add_default_handlers=False):
        """
        Constructor:

        :param experiment_jobs: A list of experiment jobs that all belong
            to the same experiment design.
        :type experiment_jobs: :class:`list` of
            :class:`thelma.models.job.ExperimentJob`

        :param user: The user who has committed the update.
        :type user: :class:`thelma.models.user.User`

        :param logging_level: the desired minimum log level
        :type logging_level: :class:`int` (or logging_level as
                         imported from :mod:`logging`)
        :default logging_level: logging.WARNING

        :param add_default_handlers: If *True* the log will automatically add
            the default handler upon instantiation.
        :type add_default_handlers: :class:`boolean`
        :default add_default_handlers: *True*
        """
        ExperimentBatchTool.__init__(self, experiment_jobs=experiment_jobs,
                                     logging_level=logging_level,
                                     add_default_handlers=add_default_handlers)

        #: The user who has committed the update.
        self.user = user

    def _check_input(self):
        ExperimentBatchTool._check_input(self)
        self._check_input_class('user', self.user, User)

    def _execute_task(self):
        """
        Runs the executors for the :attr:`_experiments`.
        """
        self.add_debug('Run executors ...')

        executor_cls = self.__get_executor_cls()
        updated_experiments = []

        if not self.has_errors():

            for experiment in self._experiments:
                kw = dict(experiment=experiment, user=self.user, log=self.log)
                executor = executor_cls(**kw)
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

    def __get_executor_cls(self):
        """
        The executor class depends on the experiment type.
        """
        if self._experiment_type.id == EXPERIMENT_SCENARIOS.SCREENING:
            return ExperimentExecutorScreening
        elif self._experiment_type.id == EXPERIMENT_SCENARIOS.OPTIMISATION:
            return ExperimentExecutorOptimisation
        else:
            msg = 'This experiment type (%s) does not support robot ' \
                  'database updates. Use the "manual" option, please!' \
                  % (self._experiment_type.display_name)
            self.add_error(msg)
