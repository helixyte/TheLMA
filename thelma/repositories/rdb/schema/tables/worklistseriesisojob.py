"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Worklist series (lab) ISO job rack table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import Table


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, iso_job_tbl, worklist_series_tbl):
    "Table factory."
    tbl = Table('worklist_series_iso_job', metadata,
                Column('job_id', Integer,
                       ForeignKey(iso_job_tbl.c.job_id,
                                  ondelete='CASCADE', onupdate='CASCADE'),
                       nullable=False),
                Column('worklist_series_id', Integer,
                       ForeignKey(worklist_series_tbl.c.worklist_series_id,
                                  ondelete='CASCADE', onupdate='CASCADE'),
                       nullable=False)
                )
    PrimaryKeyConstraint(tbl.c.job_id)
    return tbl
