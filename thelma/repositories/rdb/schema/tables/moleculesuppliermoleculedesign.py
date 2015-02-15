"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Molecule supplier molecule design table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, molecule_tbl, supplier_molecule_design_tbl):
    "Table factory."
    tbl = Table('molecule_supplier_molecule_design', metadata,
        Column('molecule_id', Integer,
               ForeignKey(molecule_tbl.c.molecule_id),
               primary_key=True),
        Column('supplier_molecule_design_id', Integer,
               ForeignKey(
                supplier_molecule_design_tbl.c.supplier_molecule_design_id,
                onupdate='CASCADE', ondelete='RESTRICT'),
               nullable=False),
        )
    return tbl
