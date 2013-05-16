"""
Molecule design versioned transcript target table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, molecule_design_tbl, versioned_transcript_tbl):
    "Table factory."
    tbl = Table('molecule_design_versioned_transcript_target', metadata,
        Column('molecule_design_id', Integer,
               ForeignKey(molecule_design_tbl.c.molecule_design_id),
               primary_key=True),
        Column('versioned_transcript_id', Integer,
               ForeignKey(versioned_transcript_tbl.c.versioned_transcript_id),
               primary_key=True),
        )
    return tbl
