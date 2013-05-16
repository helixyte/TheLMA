"""
Gene table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import UniqueConstraint

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, species_tbl):
    "Table factory."
    tbl = Table('gene', metadata,
        Column('gene_id', Integer, primary_key=True),
        Column('accession', String(32), nullable=False, unique=True),
        Column('locus_name', String(40), nullable=False, index=True),
        Column('species_id', Integer,
               ForeignKey(species_tbl.c.species_id,
                          onupdate='CASCADE', ondelete='CASCADE'),
               nullable=False),
        )
    UniqueConstraint(tbl.c.gene_id, tbl.c.species_id)
    return tbl
