"""
Molecule design set library table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, molecule_design_pool_set_tbl):
    "Table factory."
    tbl = Table('molecule_design_library', metadata,
                Column('molecule_design_library_id', Integer, primary_key=True),
                Column('molecule_design_pool_set_id', Integer,
                       ForeignKey(molecule_design_pool_set_tbl.c.\
                                  molecule_design_pool_set_id),
                       nullable=False),
                Column('label', String, nullable=False, unique=True),
                Column('final_volume', Float,
                       CheckConstraint('final_volume > 0'),
                       nullable=False),
                Column('final_concentration', Float,
                       CheckConstraint('final_concentration > 0'),
                       nullable=False)
        )
    return tbl
