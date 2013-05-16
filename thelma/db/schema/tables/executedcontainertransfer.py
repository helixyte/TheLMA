"""
Executed container transfer table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_table(metadata, executed_transfer_tbl, container_tbl):
    "Table factory."
    tbl = Table('executed_container_transfer', metadata,
                Column('executed_transfer_id', Integer,
                       ForeignKey(executed_transfer_tbl.c.executed_transfer_id),
                       nullable=False, primary_key=True),
                Column('source_container_id', Integer,
                       ForeignKey(container_tbl.c.container_id),
                       nullable=False),
                Column('target_container_id', Integer,
                       ForeignKey(container_tbl.c.container_id),
                       nullable=False),
                )
    return tbl
