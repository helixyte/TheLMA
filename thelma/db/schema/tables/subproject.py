"""
Subproject table.
"""
from datetime import datetime
from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table

__docformat__ = "epytext"
__all__ = ['create_table']


def create_table(metadata, project_tbl):
    "Table factory."
    tbl = Table('subproject', metadata,
                Column('subproject_id', Integer, primary_key=True),
                Column('label', String, CheckConstraint('length(label)>0'),
                       nullable=False, unique=True
                       ),
                Column('project_id', Integer,
                       ForeignKey(project_tbl.c.project_id,
                                  onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False),
                Column('creation_date', DateTime(timezone=True),
                       default=datetime.now),
                Column('active', Boolean),

                )
    return tbl
