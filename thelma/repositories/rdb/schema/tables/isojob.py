"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

ISO job table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import Table
from sqlalchemy.schema import CheckConstraint


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, job_tbl):
    "Table factory."
    tbl = Table('iso_job', metadata,
                Column('job_id', Integer,
                       ForeignKey(job_tbl.c.job_id,
                                  onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False),
                Column('number_stock_racks', Integer,
                       CheckConstraint('number_stock_racks >= 0'),
                       nullable=False)
                )

    PrimaryKeyConstraint(tbl.c.job_id)
    return tbl
