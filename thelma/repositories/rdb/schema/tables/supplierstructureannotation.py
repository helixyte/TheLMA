"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Supplier structure annotation table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, supplier_molecule_design_tbl,
                 chemical_structure_tbl):
    "Table factory."
    tbl = Table('supplier_structure_annotation', metadata,
        Column('supplier_molecule_design_id', Integer,
               ForeignKey(
                    supplier_molecule_design_tbl.c.supplier_molecule_design_id,
                    onupdate='CASCADE', ondelete='CASCADE'),
               nullable=False, primary_key=True),
        Column('chemical_structure_id', Integer,
               ForeignKey(
                    chemical_structure_tbl.c.chemical_structure_id,
                    onupdate='CASCADE', ondelete='CASCADE'),
               nullable=False, primary_key=True),
        Column('annotation', String, nullable=False),
        )
    return tbl
