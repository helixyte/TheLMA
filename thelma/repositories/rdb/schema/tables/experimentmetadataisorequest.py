"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Experiment metadata ISO request association table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, experiment_metadata_tbl, iso_request_tbl):
    "Table factory."
    tbl = Table('experiment_metadata_iso_request', metadata,
                Column('experiment_metadata_id', Integer,
                       ForeignKey(experiment_metadata_tbl.c.\
                                  experiment_metadata_id),
                       nullable=False),
                Column('iso_request_id', Integer,
                       ForeignKey(iso_request_tbl.c.iso_request_id),
                       nullable=False),
                )
    return tbl
