"""
:Date: 2011 December
:Author: AAB, berger at cenix-bioscience dot com

This module executes worklist series for an experiment (full execution
including mastermix preparation, if applicable).
"""

from thelma.automation.tools.experiment.base import ExperimentOptimisationTool
from thelma.automation.tools.experiment.base import ExperimentScreeningTool
from thelma.automation.tools.worklists.series import SeriesExecutor
from thelma.models.liquidtransfer import ExecutedRackTransfer
from thelma.models.liquidtransfer import ExecutedWorklist
from thelma.models.user import User
from thelma.utils import get_utc_time
import logging


__docformat__ = 'reStructuredText en'

__all__ = ['ExperimentExecutorOptimisation',
           'ExperimentExecutorScreening']


class ExperimentExecutorOptimisation(ExperimentOptimisationTool):
    """
    This executor executes the full set of worklist for an experiment
    (mastermix and cell plate preparation). It assumes an optimisation
    scenario and the use of a Biomek.

    **Return Value:** updated experiment
    """

    NAME = 'Experiment Biomek Executor'

    def __init__(self, experiment, user, logging_level=logging.WARNING,
                 add_default_handlers=False, log=None):
        """
        Constructor:

        :param experiment: The experiment for which to generate the BioMek
                worklists.
        :type experiment: :class:`thelma.models.experiment.Experiment`

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

        :param log: The ThelmaLog to write into (if used as part of a batch).
        :type log: :class:`thelma.ThelmaLog`
        """
        ExperimentOptimisationTool.__init__(self, experiment=experiment,
                                    logging_level=logging_level,
                                    add_default_handlers=add_default_handlers,
                                    log=log)

        #: The timestamp for the execution.
        self.now = get_utc_time()

        #: The user who has committed the update.
        self.user = user

    def _check_input(self):
        """
        Checks whether all initialisation values are valid.
        """
        ExperimentOptimisationTool._check_input(self)
        self._check_input_class('user', self.user, User)

    def _execute_task(self):
        """
        Runs the tool-specific tasks.
        """
        self.add_info('Start worklist execution ...')

        if not self.has_errors(): self._check_mastermix_compatibility()
        if not self.has_errors(): self.__execute_jobs()
        if not self.has_errors():
            self.return_value = self.experiment
            self.add_info('Worklist execution completed.')

    def __execute_jobs(self):
        """
        Creates and executes the transfer jobs.
        """
        self._create_all_transfer_jobs(add_cell_worklists=True)

        if not self.has_errors():
            executor = SeriesExecutor(transfer_jobs=self._transfer_jobs,
                                      user=self.user, log=self.log)
            execution_map = executor.get_result()
            if execution_map is None:
                msg = 'Error during serial worklist execution.'
                self.add_error(msg)


class ExperimentExecutorScreening(ExperimentScreeningTool):
    """
    This executor executes the worklists for an experiment (cell plate
    preparation). It assumes an screening scenario.

    **Return Value:** updated experiment
    """

    NAME = 'Experiment Cybio Executor'

    def __init__(self, experiment, user, logging_level=logging.WARNING,
                 add_default_handlers=False, log=None):
        """
        Constructor:

        :param experiment: The experiment for which to generate the BioMek
                worklists.
        :type experiment: :class:`thelma.models.experiment.Experiment`

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

        :param log: The ThelmaLog to write into (if used as part of a batch).
        :type log: :class:`thelma.ThelmaLog`
        """
        ExperimentScreeningTool.__init__(self, experiment=experiment,
                                     logging_level=logging_level,
                                     add_default_handlers=add_default_handlers,
                                     log=None)

        #: The timestamp for the execution.
        self.now = get_utc_time()

        #: The user who has committed the update.
        self.user = user

    def _check_input(self):
        """
        Checks whether all initialisation values are valid.
        """
        ExperimentScreeningTool._check_input(self)
        self._check_input_class('user', self.user, User)

    def _execute_task(self):
        """
        Runs the tool-specific tasks.
        """
        self.add_info('Start worklist execution ...')

        transfer_worklist = self._get_rack_transfer_worklist()
        self._check_mastermix_compatibility()
        if not self.has_errors():
            self._create_all_transfer_jobs(transfer_worklist, True)
        if not self.has_errors(): self.__execute_transfers(transfer_worklist)
        if not self.has_errors():
            self.return_value = self.experiment
            self.add_info('Worklist execution completed.')

    def __execute_transfers(self, transfer_worklist):
        """
        Executes the transfers. Also creates the executed worklist for
        the rack transfer.
        """
        self.add_debug('Execute transfers ...')

        executor = SeriesExecutor(transfer_jobs=self._transfer_jobs,
                                  user=self.user, log=self.log)
        execution_map = executor.get_result()

        if execution_map is None:
            msg = 'Error when trying to execute worklist series!'
            self.add_error(msg)
        else:
            for executed_item in execution_map.values():
                if not isinstance(executed_item, ExecutedRackTransfer): continue
                ExecutedWorklist(planned_worklist=transfer_worklist,
                                 executed_transfers=[executed_item])
