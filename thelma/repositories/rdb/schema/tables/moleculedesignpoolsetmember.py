"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Molecule design pool set member table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy.schema import PrimaryKeyConstraint


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, pool_tbl, molecule_design_pool_set_tbl):
    "Table factory."
    tbl = Table('molecule_design_pool_set_member', metadata,
            Column('molecule_design_pool_set_id', Integer,
                ForeignKey(molecule_design_pool_set_tbl.c.\
                           molecule_design_pool_set_id),
                nullable=False),
            Column('molecule_design_pool_id', Integer,
                   ForeignKey(pool_tbl.c.molecule_design_set_id),
                   nullable=False)
                )
    PrimaryKeyConstraint(tbl.c.molecule_design_pool_set_id,
                         tbl.c.molecule_design_pool_id)
    return tbl
