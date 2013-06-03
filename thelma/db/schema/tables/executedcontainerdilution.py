"""
Executed container dilution table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, executed_transfer_tbl, container_tbl,
                 reservoir_specs_tbl):
    "Table factory."
    tbl = Table('executed_container_dilution', metadata,
                Column('executed_transfer_id', Integer,
                       ForeignKey(executed_transfer_tbl.c.executed_transfer_id),
                       nullable=False, primary_key=True),
                Column('target_container_id', Integer,
                       ForeignKey(container_tbl.c.container_id),
                       nullable=False),
                Column('reservoir_specs_id', Integer,
                       ForeignKey(reservoir_specs_tbl.c.reservoir_specs_id),
                       nullable=False)
                )
    return tbl
