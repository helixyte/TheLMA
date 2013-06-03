"""
Job mapper.
"""
from everest.repositories.rdb.utils import mapper
from everest.repositories.rdb.utils import synonym
from sqlalchemy.orm import relationship
from thelma.models.job import JOB_TYPES
from thelma.models.job import Job
from thelma.models.job import JobType
from thelma.models.subproject import Subproject
from thelma.models.user import User

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(job_tbl):
    "Mapper factory."
    # TODO: remove job type
    m = mapper(Job, job_tbl,
            id_attribute='job_id',
            properties=dict(
                job_type=relationship(JobType, uselist=False),
                user=relationship(User, uselist=False),
                subproject=relationship(Subproject, uselist=False),
            ),
            polymorphic_on=job_tbl.c.type,
            polymorphic_identity=JOB_TYPES.OTHER
        )
    Job.status = synonym('status_type')
    return m
