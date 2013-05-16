"""
Experiment job mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from thelma.models.experiment import Experiment
from thelma.models.job import ExperimentJob
from thelma.models.job import JOB_TYPES

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
               polymorphic_identity=JOB_TYPES.RNAI_EXPERIMENT
               )
    return m
