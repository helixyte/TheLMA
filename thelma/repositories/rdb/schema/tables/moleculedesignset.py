"""
Molecule design set table.
"""
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata):
    "Table factory."
    tbl = Table('molecule_design_set', metadata,
                Column('molecule_design_set_id', Integer, primary_key=True),
                Column('set_type', String, nullable=False)
        )
    return tbl
