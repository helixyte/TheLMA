"""
Tissue table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, VARCHAR

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, organization_tbl):
    "Table factory."
    tbl = Table('cell_culture_ware', metadata,
        Column('cell_culture_ware_id', Integer, primary_key=True),
        Column('label', String(128), nullable=False, unique=True),
        Column('molecule_design_set_id', Integer,
               ForeignKey(organization_tbl.c.organization_id),
               nullable=False),
        Column('size', DOUBLE_PRECISION, nullable=False),
        Column('coating', VARCHAR, nullable=False),
        )
    return tbl
