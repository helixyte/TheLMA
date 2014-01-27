"""
Shortcuts for tools involved in experiment processing.

AAB
"""
from thelma.automation.tools.experiment.batch import ExperimentBatchExecutor
from thelma.automation.tools.experiment.batch import ExperimentBatchManualExecutor
from thelma.automation.tools.experiment.batch import ExperimentBatchWorklistWriter
from thelma.automation.tools.experiment.manual import ExperimentManualExecutor
from thelma.automation.tools.experiment.mastermix import get_experiment_executor
from thelma.automation.tools.experiment.mastermix import get_experiment_writer

__docformat__ = 'reStructuredText en'

__all__ = ['get_manual_executor',
           'get_writer',
           'get_executor',
           'get_batch_manual_executor',
           'get_batch_writer',
           'get_batch_executor']


def get_manual_executor(experiment, user, **kw):
    """
    Factory function creating an tool that performs DB executions for experiments
    without mastermix support (:class:`ExperimentManualExecutor`).

    :param experiment: The experiment for which to generate the BioMek
        worklists.
    :type experiment: :class:`thelma.models.experiment.Experiment`

    :param user: The user who has committed the update.
    :type user: :class:`thelma.models.user.User`
    """
    kw.update(dict(experiment=experiment, user=user))
    return ExperimentManualExecutor(**kw)

def get_writer(experiment, **kw):
    """
    Factory function returning the writer/executor for the passed experiment
    in printing mode.
    Invokes :func:`get_experiment_writer`.

    :param experiment: The experiment for which to generate the robot worklists.
    :type experiment: :class:`thelma.models.experiment.Experiment`
    """
    return get_experiment_writer(experiment=experiment, **kw)

def get_executor(experiment, user, **kw):
    """
    Factory function returning the writer/executor for the passed experiment
    in execution mode (this tool performs DB updates).
    Invokes :func:`get_experiment_executor`.

    :param experiment: The experiment for which to generate the robot worklists.
    :type experiment: :class:`thelma.models.experiment.Experiment`

    :param user: The user who conducts the DB update.
    :type user: :class:`thelma.models.user.User`
    """
    return get_experiment_executor(experiment=experiment, user=user, **kw)

def get_batch_manual_executor(experiments, user, **kw):
    """
    Factory function creating a batch tool that performs DB executions for
    experiments without mastermix support
    (:class:`ExperimentBatchManualExecutor`).

    :param experiments: A list of experiments that all belong to the
        same experiment design.
    :type experiments: :class:`list` of :class:`thelma.models.job.Experiment`

    :param user: The user who has committed the update.
    :type user: :class:`thelma.models.user.User`
    """
    kw.update(dict(experiments=experiments, user=user))
    return ExperimentBatchManualExecutor(**kw)

def get_batch_writer(experiments, **kw):
    """
    Factory function creating a batch tool that prints worklist for all
    experiments of the passed experiment jobs
    (:class:`ExperimentBatchWorklistWriter`).

    :param experiments: A list of experiments that all belong to the
        same experiment design.
    :type experiments: :class:`list` of :class:`thelma.models.job.Experiment`
    """
    kw.update(dict(experiments=experiments))
    return ExperimentBatchWorklistWriter(**kw)

def get_batch_executor(experiments, user, **kw):
    """
    Factory function creating a batch tool that performs DB for all
    experiments of the passed experiment jobs
    (:class:`ExperimentBatchExecutor`).

    :param experiments: A list of experiments that all belong to the
        same experiment design.
    :type experiments: :class:`list` of :class:`thelma.models.job.Experiment`

    :param user: The user who has committed the update.
    :type user: :class:`thelma.models.user.User`
    """
    kw.update(dict(experiments=experiments, user=user))
    return ExperimentBatchExecutor(**kw)
