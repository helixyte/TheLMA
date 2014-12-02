"""
Molecule Design pool set table.
"""
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.schema import ForeignKey


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, molecule_type_tbl):
    "Table factory."
    tbl = Table('molecule_design_pool_set', metadata,
                Column('molecule_design_pool_set_id', Integer,
                        primary_key=True),
                Column('molecule_type_id', String(20),
                       ForeignKey(molecule_type_tbl.c.molecule_type_id),
                       nullable=False)
        )
    return tbl
