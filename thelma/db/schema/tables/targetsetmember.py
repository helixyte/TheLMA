"""
Target set member table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = "reStructuredText en"
__all__ = ['create_table']

def create_table(metadata, target_tbl, target_set_tbl):
    "Table factory."
    tbl = Table('target_set_member', metadata,
                Column('target_set_id', Integer,
                       ForeignKey(target_set_tbl.c.target_set_id),
                       nullable=False),
                Column('target_id', Integer,
                       ForeignKey(target_tbl.c.target_id), nullable=False)
                )

    return tbl
