"""
Experiment metadata type table.
"""
from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Table


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata):
    "Table factory."
    tbl = Table('experiment_metadata_type', metadata,
                Column('experiment_metadata_type_id', String(10),
                       primary_key=True),
                Column('display_name', String, nullable=False)
                )
    return tbl
