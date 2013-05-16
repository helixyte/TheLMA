"""
Job mapper.
"""
from sqlalchemy import String
from sqlalchemy import cast
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
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
            properties=dict(
                id=synonym('job_id'),
                job_type=relationship(JobType, uselist=False),
                user=relationship(User, uselist=False),
                subproject=relationship(Subproject, uselist=False),
                status=synonym('status_type'),
            ),
            polymorphic_on=job_tbl.c.type,
            polymorphic_identity=JOB_TYPES.OTHER
        )
    if isinstance(Job.slug, property):
        Job.slug = hybrid_property(
                            Job.slug.fget,
                            expr=lambda cls: cast(cls.job_id, String))
    return m
