"""
Job type mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import synonym
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.job import JobType

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(jobtype_tbl):
    "Mapper factory."
    m = mapper(JobType, jobtype_tbl,
                properties=dict(id=synonym('job_type_id'),
                                ),
               )
    if isinstance(JobType.slug, property):
        JobType.slug = \
            hybrid_property(JobType.slug.fget,
                            expr=lambda cls: as_slug_expression(cls.name))
    return m
