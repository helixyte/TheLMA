"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Worklist series experiment design rack table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import Table


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, experiment_design_rack_tbl, worklist_series_tbl):
    "Table factory."
    tbl = Table('worklist_series_experiment_design_rack', metadata,
                Column('experiment_design_rack_id', Integer,
                       ForeignKey(experiment_design_rack_tbl.c.\
                                  experiment_design_rack_id,
                                  ondelete='CASCADE', onupdate='CASCADE'),
                       nullable=False, unique=True),
                Column('worklist_series_id', Integer,
                       ForeignKey(worklist_series_tbl.c.worklist_series_id,
                                  ondelete='CASCADE', onupdate='CASCADE'),
                       nullable=False)
                )
    PrimaryKeyConstraint(tbl.c.experiment_design_rack_id,
                         tbl.c.worklist_series_id)
    return tbl
