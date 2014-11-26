"""
Job table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from thelma.entities.job import JOB_TYPES

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, user_tbl):
    "Table factory."
    tbl = Table('new_job', metadata,
                Column('job_id', Integer, primary_key=True),
                Column('job_type', String(10), nullable=False),
                Column('label', String(40), nullable=False),
                Column('user_id', Integer,
                       ForeignKey(user_tbl.c.db_user_id,
                                  onupdate='RESTRICT', ondelete='RESTRICT'),
                                  nullable=False),
                Column('creation_time', DateTime(timezone=True),
                       nullable=False),
                CheckConstraint('job_type IN (\'%s\', \'%s\', \'%s\')' \
                        % (JOB_TYPES.BASE, JOB_TYPES.EXPERIMENT, JOB_TYPES.ISO))
                )
    return tbl
