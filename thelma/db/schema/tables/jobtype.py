"""
Job type table.
"""
from sqlalchemy import Table
from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Integer

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata):
    "Table factory."
    tbl = Table('job_type', metadata,
                Column('job_type_id', Integer, primary_key=True),
                Column('name', String(32), nullable=False, unique=True),
                Column('label', String(64), nullable=False),
                Column('xml', String, nullable=False)
                )
    return tbl
