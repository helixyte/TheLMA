"""
DB release table.
"""
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import UniqueConstraint


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, db_source_tbl):
    "Table factory."
    tbl = Table('db_release', metadata,
        Column('db_release_id', Integer, primary_key=True),
        Column('version', String(20), nullable=False, unique=True),
        Column('db_source_id', Integer,
               ForeignKey(db_source_tbl.c.db_source_id, onupdate='CASCADE'),
               nullable=False),
        Column('release_date', DateTime, nullable=False),
        Column('download_source', String(256), nullable=False),
        )
    UniqueConstraint(tbl.c.db_release_id, tbl.c.db_source_id)
    UniqueConstraint(tbl.c.db_source_id, tbl.c.version)
    return tbl
