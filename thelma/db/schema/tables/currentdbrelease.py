"""
Current DB release table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, db_source_tbl, db_release_tbl):
    "Table factory."
    tbl = Table('current_db_release', metadata,
        Column('db_release_id', Integer, nullable=False, index=True),
        Column('db_source_id', Integer, nullable=False, primary_key=True),
        ForeignKeyConstraint(['db_release_id', 'db_source_id'],
                             [db_release_tbl.c.db_release_id,
                              db_source_tbl.c.db_source_id],
                             onupdate='CASCADE', ondelete='CASCADE')
        )
    return tbl
