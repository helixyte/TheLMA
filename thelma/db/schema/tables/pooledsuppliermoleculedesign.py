"""
Supplier molecule design table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, supplier_molecule_design_tbl,
                 molecule_design_set_tbl):
    "Table factory."
    tbl = Table('pooled_supplier_molecule_design', metadata,
        Column('supplier_molecule_design_id', Integer,
               ForeignKey(
                supplier_molecule_design_tbl.c.supplier_molecule_design_id),
               primary_key=True),
        Column('molecule_design_set_id', Integer,
               ForeignKey(molecule_design_set_tbl.c.molecule_design_set_id,
                          onupdate='CASCADE', ondelete='CASCADE'),
               nullable=False),
        )
    return tbl
