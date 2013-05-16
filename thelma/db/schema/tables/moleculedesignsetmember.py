"""
Molecule design set member table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy.schema import PrimaryKeyConstraint

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, molecule_design_tbl, molecule_design_set_tbl):
    "Table factory."
    tbl = Table('molecule_design_set_member', metadata,
            Column('molecule_design_set_id', Integer,
                ForeignKey(molecule_design_set_tbl.c.molecule_design_set_id),
                nullable=False),
            Column('molecule_design_id', Integer,
                   ForeignKey(molecule_design_tbl.c.molecule_design_id),
                   nullable=False)
                )
    PrimaryKeyConstraint(tbl.c.molecule_design_set_id,
                         tbl.c.molecule_design_id)
    return tbl
