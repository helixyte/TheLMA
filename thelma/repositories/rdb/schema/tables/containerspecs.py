"""
Container_specs table.
"""
from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, organization_tbl):
    "Table factory."
    tbl = Table('container_specs', metadata,
        Column('container_specs_id', Integer, primary_key=True),
        Column('manufacturer_id', Integer,
               ForeignKey(organization_tbl.c.organization_id,
                          onupdate='CASCADE', ondelete='RESTRICT')),
        Column('name', String, nullable=False, unique=True), # FIXME: validate against regexp '[_A-Za-z][_A-Za-z0-9]+'
        Column('label', String, nullable=False, unique=True),
        Column('description', String, nullable=False, default=''),
        Column('max_volume', Float, CheckConstraint('max_volume>=0.0'),
               nullable=False),
        Column('dead_volume', Float, CheckConstraint('dead_volume>=0.0'),
               nullable=False),
        Column('has_barcode', Boolean, nullable=False),
        )
    return tbl
