"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

ISO molecule design pool set association table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, iso_tbl, iso_pool_set_tbl):
    "Table factory."
    tbl = Table('iso_pool_set', metadata,
                Column('iso_id', Integer,
                       ForeignKey(iso_tbl.c.iso_id),
                       nullable=False, unique=True),
                Column('molecule_design_pool_set_id', Integer,
                       ForeignKey(
                            iso_pool_set_tbl.c.molecule_design_pool_set_id),
                       nullable=False),
                )
    return tbl
