"""
Other job mapper.
"""
from sqlalchemy.orm import mapper
from thelma.models.job import OtherJob
from thelma.models.job import JOB_TYPES

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(job_mapper, job_tbl):
    "Mapper factory."
    m = mapper(OtherJob, job_tbl,
               inherits=job_mapper,
               polymorphic_identity=JOB_TYPES.OTHER
               )
    return m
