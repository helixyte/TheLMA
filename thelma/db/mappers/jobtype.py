"""
Job type mapper.
"""
from everest.repositories.rdb.utils import mapper
from everest.repositories.rdb.utils import as_slug_expression
from thelma.models.job import JobType

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(jobtype_tbl):
    "Mapper factory."
    m = mapper(JobType, jobtype_tbl,
               id_attribute='job_type_id',
               slug_expression=lambda cls: as_slug_expression(cls.name))
    return m
