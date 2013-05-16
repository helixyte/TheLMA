"""
Versioned transcript table.
"""
from sqlalchemy import Column
from sqlalchemy import DDL
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import UniqueConstraint

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def _setup_postgres_ddl(table):
    """
    ...explain..
    """
    DDL("""
        CREATE INDEX %(table)s_sequence_md5 ON %(table)s
          USING btree md5(sequence);
        """,
        on='postgres',
        ).execute_at('after-create', table)


def _setup_sqlite_ddl(table):
    """
    ...explain..
    """
    DDL("""
        CREATE INDEX %(table)s_sequence ON %(table)s
          (sequence);
        """,
        on='sqlite',
        ).execute_at('after-create', table)


def create_table(metadata, transcript_tbl):
    "Table factory."
    tbl = Table('versioned_transcript', metadata,
        Column('versioned_transcript_id', Integer, primary_key=True),
        Column('transcript_id', Integer,
               ForeignKey(transcript_tbl.c.transcript_id,
                          onupdate='CASCADE', ondelete='CASCADE'),
               nullable=False, index=True),
        Column('version', Integer, nullable=False),
        Column('sequence', String, nullable=False), # TODO: validate against regexp '[^A|T|G|C|N|M|R|W|S|Y|K|V|H|D|B|X]'
        )
    UniqueConstraint(tbl.c.transcript_id, tbl.c.version)
    _setup_postgres_ddl(tbl)
    _setup_sqlite_ddl(tbl)
    return tbl
