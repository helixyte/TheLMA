"""
Experiment design table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, rack_shape_tbl, experiment_metadata_tbl):
    "Table factory."
    tbl = Table('experiment_design', metadata,
                Column('experiment_design_id', Integer, primary_key=True),
                Column('rack_shape_name', String,
                       ForeignKey(rack_shape_tbl.c.rack_shape_name,
                                  onupdate='CASCADE', ondelete='RESTRICT'),
                       nullable=False),
                Column('experiment_metadata_id', Integer,
                       ForeignKey(experiment_metadata_tbl.c.\
                                  experiment_metadata_id,
                                  onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False)
                )
    return tbl
