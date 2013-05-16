"""
ISO job table
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, job_tbl):
    "Table factory."
    tbl = Table('iso_job', metadata,
                Column('job_id', Integer,
                       ForeignKey(job_tbl.c.job_id), nullable=False,
                       primary_key=True),
                )
    return tbl
