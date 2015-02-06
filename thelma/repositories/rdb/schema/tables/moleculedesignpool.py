"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Molecule design pool table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.schema import ForeignKey


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, molecule_design_set_tbl, molecule_type_tbl):
    "Table factory."
    tbl = Table('molecule_design_pool', metadata,
                Column('molecule_design_set_id', Integer,
                       ForeignKey(
                            molecule_design_set_tbl.c.molecule_design_set_id),
                       primary_key=True),
                Column('molecule_type', String(10),
                       ForeignKey(
                            molecule_type_tbl.c.molecule_type_id),
                       key='molecule_type_id', nullable=False),
                Column('member_hash', String, nullable=False, unique=True),
                Column('number_designs', Integer, nullable=False),
                Column('default_stock_concentration', Float,
                       CheckConstraint('default_stock_concentration' > 0),
                       nullable=False)
        )
    return tbl
