"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Job resource.

Created Jun 2011
"""
from datetime import datetime
import logging

from pyramid.httpexceptions import HTTPBadRequest

from everest.entities.utils import get_root_aggregate
from everest.querying.specifications import DescendingOrderSpecification
from everest.representers.dataelements import DataElementAttributeProxy
from everest.representers.interfaces import IDataElement
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.entities.utils import get_current_user
from thelma.interfaces import IExperiment
from thelma.interfaces import IIso
from thelma.interfaces import IItemStatus
from thelma.interfaces import IPlate
from thelma.interfaces import IStockRack
from thelma.interfaces import IUser
from thelma.resources.base import RELATION_BASE_URL
from thelma.tools.experiment import get_batch_writer
from thelma.tools.experiment import get_executor
from thelma.tools.experiment import get_manual_executor
from thelma.tools.semiconstants import ITEM_STATUS_NAMES


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
    job_type = terminal_attribute(str, 'job_type')
    label = terminal_attribute(str, 'label')
    user = member_attribute(IUser, 'user')
    creation_time = terminal_attribute(datetime, 'creation_time')

    @property
    def title(self):
        entity = self.get_entity()
        return '%s: %s' % (entity.job_type, entity.label)


class ExperimentJobMember(JobMember):
    experiments = collection_attribute(IExperiment, 'experiments')

    def update(self, data):
        if IDataElement.providedBy(data): # pylint: disable=E1101
            prx = DataElementAttributeProxy(data)
            try:
                exp_nodes = prx.experiments
            except AttributeError:
                pass
            else:
                for exp_node in exp_nodes:
                    exp_id = exp_node.id
                    try:
                        exp_rack_nodes = exp_node.experiment_racks
                    except AttributeError:
                        pass
                    else:
                        if len(exp_rack_nodes) > 0:
                            self.__update_experiment_racks(exp_rack_nodes,
                                                           exp_id)
        else:
            JobMember.update(self, data)

    def get_writer(self):
        return get_batch_writer(experiments=self.get_entity().experiments)

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
            tool = get_manual_executor(experiment=exp_ent, user=user)
        elif status_title == 'robot_execution':
            try:
                tool = get_executor(experiment=exp_ent, user=user)
            except TypeError as te:
                raise HTTPBadRequest(str(te)).exception
        if not tool is None:
            # FIXME: We don't care about the result here; still we must call
            #        get_result for its side effects.
            dummy = tool.get_result()
            if tool.has_errors():
                exc_msg = str(tool.get_messages(logging_level=logging.ERROR))
                raise HTTPBadRequest('Could not update Database: %s' % exc_msg
                                     ).exception
            else:
                status_agg = get_root_aggregate(IItemStatus)
                status_managed = \
                    status_agg.get_by_slug(ITEM_STATUS_NAMES.MANAGED.lower())
                for exp_rack in exp_ent.experiment_racks:
                    exp_rack.rack.status = status_managed


class IsoJobMember(JobMember):
    relation = "%s/iso_job" % RELATION_BASE_URL

    isos = collection_attribute(IIso, 'isos')
    number_stock_racks = terminal_attribute(int, 'number_stock_racks')
    stock_racks = collection_attribute(IStockRack, 'iso_job_stock_racks')
    preparation_plates = collection_attribute(IPlate, 'preparation_plates')
    status = terminal_attribute(str, 'status')


class JobCollection(Collection):
    title = 'Jobs'
    root_name = 'jobs'


class IsoJobCollection(JobCollection):
    title = 'Iso Jobs'
    root_name = 'iso-jobs'
    description = 'Manage ISO jobs'
    default_order = DescendingOrderSpecification('creation_time')


class ExperimentJobCollection(JobCollection):
    title = 'Experiment Jobs'
    root_name = 'experiment-jobs'
    description = 'Manage Experiment jobs'
    default_order = DescendingOrderSpecification('creation_time')
