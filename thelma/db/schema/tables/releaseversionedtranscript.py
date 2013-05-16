"""
Release versioned transcript table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, db_release_tbl, versioned_transcript_tbl):
    "Table factory."
    tbl = Table('release_versioned_transcript', metadata,
        Column('db_release_id', Integer,
               ForeignKey(db_release_tbl.c.db_release_id,
                          onupdate='CASCADE', ondelete='CASCADE'),
               primary_key=True),
        Column('versioned_transcript_id', Integer,
               ForeignKey(versioned_transcript_tbl.c.versioned_transcript_id,
                          onupdate='CASCADE', ondelete='CASCADE'),
               primary_key=True),
        )
    return tbl
