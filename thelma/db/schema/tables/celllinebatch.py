"""
Cell_line_batch table.
"""
from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, VARCHAR

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, container_tbl, cell_line_tbl, subproject_tbl):
    "Table factory."
    tbl = Table('cell_line_batch', metadata,
        Column('cell_line_batch_id', Integer, primary_key=True),
        Column('container_id', Integer,
               ForeignKey(container_tbl.c.container_id),
               nullable=False),
        Column('cell_line_id', Integer,
               ForeignKey(cell_line_tbl.c.cell_line_id),
               nullable=False),
        Column('subproject_id', Integer,
               ForeignKey(subproject_tbl.c.subproject_id),
               nullable=False),
        Column('freezing_date', DateTime(timezone=False), nullable=False),
        Column('defrosting_date', DateTime(timezone=False), nullable=True),
        Column('is_master_stock', Boolean, nullable=False, default=True),
        Column('parent_cell_line_batch_id', Integer,
               ForeignKey('cell_line_batch.cell_line_batch_id'),
               nullable=False),
        Column('cell_count', BigInteger, nullable=False),
        Column('freezing_medium_dmso', DOUBLE_PRECISION, nullable=False),
        Column('freezing_medium_serum', DOUBLE_PRECISION, nullable=False),
        Column('freezing_medium_medium', DOUBLE_PRECISION, nullable=False),
        Column('comments', VARCHAR, nullable=True),
        )
    return tbl
