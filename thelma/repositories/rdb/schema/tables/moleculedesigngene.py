"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Molecule design gene table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, molecule_design_tbl, gene_tbl):
    "Table factory."
    tbl = Table('molecule_design_gene', metadata,
        Column('molecule_design_id', Integer,
               ForeignKey(molecule_design_tbl.c.molecule_design_id,
                          onupdate='CASCADE', ondelete='CASCADE'),
               primary_key=True, index=True),
        Column('gene_id', Integer,
               ForeignKey(gene_tbl.c.gene_id,
                          onupdate='CASCADE', ondelete='CASCADE'),
               primary_key=True, index=True),
        )
    return tbl
