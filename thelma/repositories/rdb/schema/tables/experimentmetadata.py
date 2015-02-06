"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Experiment metadata table.
"""
from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, subproject_tbl, experiment_metadata_type_tbl):
    "Table factory."
    tbl = Table('experiment_metadata', metadata,
                Column('experiment_metadata_id', Integer, primary_key=True),
                Column('label', String, nullable=False, unique=True),
                Column('subproject_id', Integer,
                       ForeignKey(subproject_tbl.c.subproject_id),
                       nullable=False),
                Column('number_replicates', Integer, nullable=False),
                Column('creation_date', DateTime(timezone=True),
                       default=datetime.now, nullable=False),
                Column('experiment_metadata_type_id', String(10),
                       ForeignKey(experiment_metadata_type_tbl.c.
                                            experiment_metadata_type_id),
                       nullable=False),
                Column('ticket_number', Integer, nullable=False, unique=True),
                )
    return tbl
