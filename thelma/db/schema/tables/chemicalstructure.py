"""
Chemical structure table.
"""
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import UniqueConstraint

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata):
    "Table factory."
    tbl = Table('chemical_structure', metadata,
                Column('chemical_structure_id', Integer, primary_key=True),
                Column('structure_type', String, nullable=False,
                       key='structure_type_id'),
                Column('representation', String, nullable=False),
                )
    UniqueConstraint(tbl.c.structure_type_id, tbl.c.representation)
    return tbl
