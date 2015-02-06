"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Pipetting specs table.
"""
from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata):
    "Table factory."
    tbl = Table('pipetting_specs', metadata,
                Column('pipetting_specs_id', Integer, primary_key=True),
                Column('name', String(8), nullable=False, unique=True),
                Column('min_transfer_volume', Float,
                       CheckConstraint('min_transfer_volume>0'),
                       nullable=False),
                Column('max_transfer_volume', Float,
                       CheckConstraint('max_transfer_volume>0'),
                       nullable=False),
                Column('max_dilution_factor', Integer,
                       CheckConstraint('max_dilution_factor>0'),
                       nullable=False),
                Column('has_dynamic_dead_volume', Boolean, nullable=False),
                Column('is_sector_bound', Boolean, nullable=False)
                )
    return tbl
