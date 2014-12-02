"""
Molecule design structure table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, molecule_design_tbl, chemical_structure_tbl):
    "Table factory."
    tbl = Table('molecule_design_structure', metadata,
        Column('molecule_design_id', Integer,
               ForeignKey(molecule_design_tbl.c.molecule_design_id,
                          onupdate='CASCADE', ondelete='CASCADE'),
               nullable=False, primary_key=True, index=True),
        Column('chemical_structure_id', Integer,
               ForeignKey(chemical_structure_tbl.c.chemical_structure_id,
                          onupdate='CASCADE', ondelete='CASCADE'),
               nullable=False, primary_key=True, index=True),
        )
    return tbl
