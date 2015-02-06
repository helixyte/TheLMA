"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Experiment source rack association table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, experiment_tbl, rack_tbl):
    """
    Table factory.
    """
    tbl = Table('experiment_source_rack', metadata,
                Column('experiment_id', Integer,
                       ForeignKey(experiment_tbl.c.experiment_id,
                                  onupdate='CASCADE', ondelete='NO ACTION'),
                       primary_key=True),
                Column('rack_id', Integer,
                       ForeignKey(rack_tbl.c.rack_id,
                                  onupdate='CASCADE', ondelete='NO ACTION'),
                       nullable=False)
                )
    return tbl
