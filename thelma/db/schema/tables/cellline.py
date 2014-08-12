"""
Cell_line table.
"""
from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import SmallInteger
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, VARCHAR

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, species_tbl, tissue_tbl, organization_tbl, cell_culture_ware_tbl):
    "Table factory."
    tbl = Table('cell_line', metadata,
        Column('cell_line_id', Integer, primary_key=True),
        Column('label', String(128), nullable=False, unique=True),
        Column('species_id', Integer,
               ForeignKey(species_tbl.c.species_id),
               nullable=False),
        Column('origin', Text, nullable=False),
        Column('tissue_id', Integer,
               ForeignKey(tissue_tbl.c.tissue_id),
               nullable=False),
        Column('supplier_id', Integer,
               ForeignKey(organization_tbl.c.organization_id),
               nullable=False),
        Column('image', Text, nullable=False),
        Column('is_type_immortal', Boolean, nullable=False),
        Column('is_type_adherent', Boolean, nullable=False),
        Column('safety_level', SmallInteger, nullable=False),
        Column('protocol_splitting', VARCHAR, nullable=False),
        Column('protocol_media', VARCHAR, nullable=False),
        Column('protocol_thawing', VARCHAR, nullable=False),
        Column('cell_culture_ware_id', Integer,
               ForeignKey(cell_culture_ware_tbl.c.cell_culture_ware_id),
               nullable=False),
        Column('maximum_passage', Integer, nullable=False),
        Column('culture_conditions_temperature', DOUBLE_PRECISION, nullable=False),
        Column('culture_conditions_humidity', DOUBLE_PRECISION, nullable=False),
        Column('culture_conditions_co2', DOUBLE_PRECISION, nullable=False),
        Column('comment', VARCHAR, nullable=True),
        CheckConstraint('safety_level IN (1, 2, 3, 4)', name='valid_safety_level'),
        )
    return tbl