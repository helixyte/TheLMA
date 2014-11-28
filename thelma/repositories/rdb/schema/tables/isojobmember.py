"""
ISO job member table
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy.schema import PrimaryKeyConstraint

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, job_tbl, iso_tbl):
    "Table factory."
    tbl = Table('iso_job_member', metadata,
                Column('job_id', Integer,
                       ForeignKey(job_tbl.c.job_id), nullable=False),
                Column('iso_id', Integer,
                       ForeignKey(iso_tbl.c.iso_id),
                       nullable=False, unique=True)
                )
    PrimaryKeyConstraint(tbl.c.job_id, tbl.c.iso_id)
    return tbl
