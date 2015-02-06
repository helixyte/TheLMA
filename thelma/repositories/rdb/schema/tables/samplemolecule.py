"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Sample molecule table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, sample_tbl, molecule_tbl):
    "Table factory."
    tbl = Table('sample_molecule', metadata,
        Column('sample_id', Integer,
               ForeignKey(sample_tbl.c.sample_id,
                          onupdate='CASCADE', ondelete='CASCADE'),
               primary_key=True, index=True),
        Column('molecule_id', Integer,
               ForeignKey(molecule_tbl.c.molecule_id,
                          onupdate='CASCADE', ondelete='RESTRICT'),
               primary_key=True, index=True),
        Column('concentration', Float, CheckConstraint('concentration>=0.0')),
        Column('freeze_thaw_cycles', Integer,
               CheckConstraint('freeze_thaw_cycles IS NULL OR '
                               'freeze_thaw_cycles >= 0')),
        Column('checkout_date', DateTime(timezone=True)),
        )
    return tbl
