"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Executed sample transfer table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, executed_liquid_transfer_tbl, container_tbl):
    "Table factory."
    tbl = Table('executed_sample_transfer', metadata,
                Column('executed_liquid_transfer_id', Integer,
                       ForeignKey(executed_liquid_transfer_tbl.c.\
                                  executed_liquid_transfer_id,
                                  ondelete='CASCADE'),
                       nullable=False, primary_key=True),
                Column('source_container_id', Integer,
                       ForeignKey(container_tbl.c.container_id,
                                  onupdate='CASCADE'),
                       nullable=False),
                Column('target_container_id', Integer,
                       ForeignKey(container_tbl.c.container_id,
                                  onupdate='CASCADE'),
                       nullable=False),
                )
    return tbl
