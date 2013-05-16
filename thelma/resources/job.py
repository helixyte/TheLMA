"""
Job resource.

AAB, Jun 2011
"""

from datetime import datetime
from everest.entities.utils import get_root_aggregate
from everest.querying.specifications import DescendingOrderSpecification
from everest.representers.dataelements import DataElementAttributeProxy
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from pyramid.httpexceptions import HTTPBadRequest
from thelma.automation.tools.experiment.executor \
    import ExperimentExecutorOptimisation
from thelma.automation.tools.experiment.executor \
    import ExperimentExecutorScreening
from thelma.automation.tools.experiment.manual import ExperimentRackFiller
from thelma.automation.tools.semiconstants import ITEM_STATUS_NAMES
from thelma.interfaces import IExperiment
from thelma.interfaces import IItemStatus
from thelma.interfaces import IJobType
from thelma.interfaces import IRack
from thelma.interfaces import ISubproject
from thelma.interfaces import IUser
from thelma.models.experiment import EXPERIMENT_METADATA_TYPES
from thelma.models.utils import get_current_user
from thelma.resources.base import RELATION_BASE_URL
import logging

__docformat__ = 'reStructuredText en'

__all__ = ['ExperimentJobCollection',
           'ExperimentJobMember',
           'IsoJobCollection',
           'IsoJobMember',
           'JobCollection',
           'JobMember',
           ]


class JobMember(Member):
    relation = '%s/job' % RELATION_BASE_URL

    label = terminal_attribute(str, 'label')
    description = terminal_attribute(str, 'description')
    job_type = member_attribute(IJobType, 'job_type')
    user = member_attribute(IUser, 'user')
    subproject = member_attribute(ISubproject, 'subproject')
    status = terminal_attribute(str, 'status')
    start_time = terminal_attribute(datetime, 'start_time')
    end_time = terminal_attribute(datetime, 'end_time')

class ExperimentJobMember(JobMember):
    experiments = collection_attribute(IExperiment, 'experiments')

    @property
    def title(self):
        entity = self.get_entity()
        return '%s: %s' % (entity.job_type, entity.label)

    def __getitem__(self, name):
        if name == 'experiments':
            return self.experiments
        else:
            raise KeyError(name)

    def update_from_data(self, data_element):
        prx = DataElementAttributeProxy(data_element)
        exp_nodes = prx.experiments
        if exp_nodes is not None:
            for exp_node in exp_nodes:
                exp_rack_nodes = exp_node.experiment_racks
                exp_id = exp_node.id
                if exp_rack_nodes is not None and len(exp_rack_nodes) > 0:
                    self.__update_experiment_racks(exp_rack_nodes, exp_id)

    def __update_experiment_racks(self, exp_rack_nodes, exp_id):
        plate_node = exp_rack_nodes[0].plate
        # FIXME: hack - we are using a non-existent status link here.
        status_title = plate_node.status.get_title()
        if status_title != ITEM_STATUS_NAMES.FUTURE:
            for experiment in self.experiments:
                exp_ent = experiment.get_entity()
                if exp_ent.id == exp_id:
                    self.__update_experiment(exp_ent, status_title)

    def __update_experiment(self, exp_ent, status_title):
        tool = None
        user = get_current_user()
        if status_title == 'manual_execution':
            tool = ExperimentRackFiller.create(exp_ent, user)
        elif status_title == 'robot_execution':
            experiment_type = exp_ent.experiment_design.experiment_type
            if experiment_type.id == EXPERIMENT_METADATA_TYPES.OPTI:
                tool = ExperimentExecutorOptimisation(exp_ent, user)
            elif experiment_type.id == EXPERIMENT_METADATA_TYPES.SCREEN:
                tool = ExperimentExecutorScreening(exp_ent, user)
            else:
                raise HTTPBadRequest('There is no robot support for ' \
                            '"%s" experiments!' % (experiment_type)).exception
        if not tool is None:
            new_experiment = tool.get_result()
            if not new_experiment is None:
                status_agg = get_root_aggregate(IItemStatus)
                status_managed = \
                    status_agg.get_by_slug(ITEM_STATUS_NAMES.MANAGED.lower())
                for new_exp_rack in new_experiment.experiment_racks:
                    new_exp_rack.rack.status = status_managed
                exp_ent.source_rack = new_experiment.source_rack
                exp_ent.experiment_racks = new_experiment.experiment_racks
            if tool.has_errors():
                exc_msg = str(tool.get_messages(logging.ERROR))
                raise HTTPBadRequest('Could not update Database: %s' % exc_msg
                                     ).exception


class IsoJobMember(JobMember):
    relation = "%s/iso_job" % RELATION_BASE_URL

    iso_control_stock_rack = member_attribute(IRack,
                                              'iso_control_stock_rack.rack')

    @property
    def title(self):
        entity = self.get_entity()
        return '%s: %s' % (entity.job_type, entity.label)


class JobCollection(Collection):
    title = 'Jobs'
    root_name = 'jobs'


class IsoJobCollection(JobCollection):
    title = 'Iso Jobs'
    root_name = 'iso-jobs'
    description = 'Manage Iso jobs'
    default_order = DescendingOrderSpecification('start_time')


class ExperimentJobCollection(JobCollection):
    title = 'Experiment Jobs'
    root_name = 'experiment-jobs'
    description = 'Manage Experiment jobs'
    default_order = DescendingOrderSpecification('start_time')
