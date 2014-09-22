"""
Project table.
"""
from datetime import datetime
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table

__docformat__ = "epytext"
__all__ = ['create_table']


def create_table(metadata, organization_tbl, dbuser_tbl):
    "Table factory."
    tbl = Table('project', metadata,
                Column('project_id', Integer, primary_key=True),
                Column('label', String, CheckConstraint('length(label)>0'),
                       nullable=False, unique=True
                       ),
                Column('customer_id', Integer,
                       ForeignKey(organization_tbl.c.organization_id,
                                  onupdate='CASCADE', ondelete='RESTRICT'),
                       nullable=False),
                Column('creation_date', DateTime(timezone=True),
                       nullable=False, default=datetime.now),
                Column('project_leader_id', Integer,
                       ForeignKey(dbuser_tbl.c.db_user_id),
                       nullable=False),
                )
    return tbl
