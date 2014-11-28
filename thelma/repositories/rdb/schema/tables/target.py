"""
Target table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, transcript_tbl, molecule_design_tbl):
    "Table factory."
    tbl = Table('target', metadata,
            Column('target_id', Integer, primary_key=True),
            Column('molecule_design_id', Integer,
                   ForeignKey(molecule_design_tbl.c.molecule_design_id),
                   nullable=False),
            Column('transcript_id', Integer,
                   ForeignKey(transcript_tbl.c.transcript_id), nullable=False)
            )
    return tbl
