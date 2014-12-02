"""
Experiment rack table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, experiment_design_rack_tbl, experiment_tbl, rack_tbl):
    "Table factory."
    # FIXME: Need to remove the deprecated current experiment_rack table so
    #        this can be renamed.
    tbl = \
      Table(
        'new_experiment_rack', metadata,
        Column('experiment_rack_id', Integer, primary_key=True),
        Column('experiment_design_rack_id', Integer,
          ForeignKey(experiment_design_rack_tbl.c.experiment_design_rack_id),
          nullable=False),
        Column('experiment_id', Integer,
               ForeignKey(experiment_tbl.c.experiment_id,
                          onupdate='CASCADE', ondelete='CASCADE'),
               nullable=False),
        Column('rack_id', Integer,
               ForeignKey(rack_tbl.c.rack_id),
               nullable=False)
        )
    return tbl
