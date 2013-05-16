"""
Experiment design tagged rack position set table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata,
                 tagged_rack_position_set_tbl, experiment_design_rack_tbl):
    "Table factory."
    tbl = Table('experiment_design_tagged_rack_position_set', metadata,
                Column('tagged_rack_position_set_id', Integer,
                       ForeignKey(tagged_rack_position_set_tbl.c.tagged_id),
                       nullable=False),
                Column('experiment_design_rack_id', Integer,
                       ForeignKey(experiment_design_rack_tbl.c.experiment_design_rack_id),
                       nullable=False),
                )
    return tbl
