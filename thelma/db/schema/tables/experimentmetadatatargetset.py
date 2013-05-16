"""
Experiment metadata target set association table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, experiment_metadata_tbl, target_set_tbl):
    "Table factory."

    tbl = Table('experiment_metadata_target_set', metadata,
                Column('experiment_metadata_id', Integer,
                       ForeignKey(experiment_metadata_tbl.c.\
                                  experiment_metadata_id),
                       nullable=False),
                Column('target_set_id', Integer,
                       ForeignKey(target_set_tbl.c.target_set_id),
                       nullable=False),
                )
    return tbl
