"""
Job table.
"""
from datetime import datetime
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import Text

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, job_type_tbl, user_tbl, subproject_tbl):
    "Table factory."
    # TODO: remove job type
    tbl = Table('job', metadata,
                Column('job_id', Integer, primary_key=True),
                Column('job_type_id', Integer,
                       ForeignKey(job_type_tbl.c.job_type_id),
#                       nullable=False
                       ),
                Column('start_time', DateTime(timezone=True),
                       default=datetime.now()),
                Column('end_time', DateTime(timezone=True)),
                Column('label', String(64), nullable=False, unique=True),
                Column('description', Text),
                Column('db_user_id', Integer,
                       ForeignKey(user_tbl.c.db_user_id), nullable=False),
                Column('subproject_id', Integer,
                       ForeignKey(subproject_tbl.c.subproject_id), nullable=False),
                Column('status_type', String(12), nullable=False),
                Column('type', String(20), nullable=False)
                )
    return tbl
