"""
Job mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.entities.job import JOB_TYPES
from thelma.entities.job import Job
from thelma.entities.user import User

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(job_tbl):
    "Mapper factory."
    m = mapper(Job, job_tbl,
            id_attribute='job_id',
            properties=dict(
                user=relationship(User, uselist=False),
            ),
            polymorphic_on=job_tbl.c.job_type,
            polymorphic_identity=JOB_TYPES.BASE,
        )

    return m

