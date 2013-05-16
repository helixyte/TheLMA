"""
Experiment metadata molecule design pool set association table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, experiment_metadata_tbl,
                 molecule_design_pool_set_tbl):
    "Table factory."

    tbl = Table('experiment_metadata_pool_set', metadata,
                Column('experiment_metadata_id', Integer,
                       ForeignKey(experiment_metadata_tbl.c.\
                                  experiment_metadata_id),
                       nullable=False),
                Column('molecule_design_pool_set_id', Integer,
                       ForeignKey(molecule_design_pool_set_tbl.c.\
                                  molecule_design_pool_set_id),
                       nullable=False),
                )
    return tbl
