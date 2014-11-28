"""
Worklist series experiment design table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import Table

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, experiment_design_tbl, worklist_series_tbl):
    "Table factory."
    tbl = Table('worklist_series_experiment_design', metadata,
                Column('experiment_design_id', Integer,
                       ForeignKey(experiment_design_tbl.c.experiment_design_id,
                                  ondelete='CASCADE', onupdate='CASCADE'),
                       nullable=False, unique=True),
                Column('worklist_series_id', Integer,
                       ForeignKey(worklist_series_tbl.c.worklist_series_id,
                                  ondelete='CASCADE', onupdate='CASCADE'),
                       nullable=False)
                )
    PrimaryKeyConstraint(tbl.c.experiment_design_id, tbl.c.worklist_series_id)
    return tbl
