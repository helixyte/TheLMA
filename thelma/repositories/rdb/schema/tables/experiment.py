"""
Experiment table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, experiment_design_tbl, job_tbl):
    "Table factory."
    # FIXME: need to retire the old experiment table.
    tbl = Table('new_experiment', metadata,
                Column('experiment_id', Integer, primary_key=True),
                Column('label', String, nullable=False),
                Column('experiment_design_id', Integer,
                       ForeignKey(experiment_design_tbl.c.experiment_design_id),
                       nullable=False),
                Column('job_id', Integer,
                       ForeignKey(job_tbl.c.job_id,
                                  onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False),
                )
    return tbl
