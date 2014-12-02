"""
Experiment design rack table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.schema import UniqueConstraint


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, experiment_design_tbl, rack_layout_tbl):
    "Table factory."
    tbl = Table('experiment_design_rack', metadata,
                Column('experiment_design_rack_id', Integer, primary_key=True),
                Column('label', String, CheckConstraint('length(label)>0'),
                       nullable=False),
                Column('experiment_design_id', Integer,
                       ForeignKey(experiment_design_tbl.c.experiment_design_id,
                                  ondelete='CASCADE', onupdate='CASCADE'),
                       nullable=False),
                Column('rack_layout_id', Integer,
                       ForeignKey(rack_layout_tbl.c.rack_layout_id),
                       nullable=False),
                )
    UniqueConstraint(tbl.c.experiment_design_id, tbl.c.label,
                     name='unique_label_per_experiment_design')
    return tbl
