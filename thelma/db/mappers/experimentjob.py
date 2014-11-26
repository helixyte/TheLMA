"""
Experiment job mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.entities.experiment import Experiment
from thelma.entities.job import ExperimentJob
from thelma.entities.job import JOB_TYPES

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(job_mapper, job_tbl, experiment_tbl):
    "Mapper factory."
    m = mapper(ExperimentJob, job_tbl,
               inherits=job_mapper,
               properties=dict(
                  experiments=relationship(Experiment,
                                order_by=experiment_tbl.c.experiment_id,
                                back_populates='job',
                                cascade='save-update, merge, delete'
                                )
                               ),
               polymorphic_identity=JOB_TYPES.EXPERIMENT
               )
    return m
