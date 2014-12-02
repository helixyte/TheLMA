"""
Stock sample table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, sample_tbl, organization_tbl,
                 molecule_design_set_tbl, molecule_type_tbl):
    "Table factory."
    tbl = Table('stock_sample', metadata,
            Column('sample_id', Integer, ForeignKey(sample_tbl.c.sample_id),
                   primary_key=True),
            Column('molecule_design_set_id', Integer,
                   ForeignKey(
                        molecule_design_set_tbl.c.molecule_design_set_id),
                   nullable=False),
            Column('supplier_id', Integer,
                   ForeignKey(organization_tbl.c.organization_id),
                   nullable=False),
            Column('molecule_type', String(10),
                   ForeignKey(molecule_type_tbl.c.molecule_type_id),
                   key='molecule_type_id', nullable=False, index=True),
            Column('concentration', Float,
                   CheckConstraint('concentration>0.0'), nullable=False),
            )
    return tbl
