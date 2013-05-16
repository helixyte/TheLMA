"""
Release gene transcript table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, db_release_tbl, gene_tbl, transcript_tbl):
    "Table factory."
    tbl = Table('release_gene_transcript', metadata,
            Column('gene_id', Integer, nullable=False),
            Column('transcript_id', Integer, primary_key=True),
            Column('db_release_id', Integer,
                   ForeignKey(db_release_tbl.c.db_release_id),
                   primary_key=True),
            Column('species_id', Integer, nullable=False),
            ForeignKeyConstraint(['gene_id', 'species_id'],
                                 [gene_tbl.c.gene_id, gene_tbl.c.species_id],
                                 'gene_species_fkey'),
            ForeignKeyConstraint(['transcript_id', 'species_id'],
                                 [transcript_tbl.c.transcript_id,
                                  transcript_tbl.c.species_id],
                                 'transcript_species_fkey'),
            )
    return tbl
