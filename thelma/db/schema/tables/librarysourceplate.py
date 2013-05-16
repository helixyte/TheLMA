"""
Library ISO source (preparation) plate table
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = "reStructuredText en"
__all__ = ['create_table']

def create_table(metadata, library_creation_iso_tbl, rack_tbl):
    "Table factory."
    tbl = Table('library_source_plate', metadata,
                Column('library_source_plate_id', Integer, primary_key=True),
                Column('rack_id', Integer, ForeignKey(rack_tbl.c.rack_id),
                       nullable=False),
                Column('iso_id', Integer,
                       ForeignKey(library_creation_iso_tbl.c.iso_id),
                       nullable=False),
                Column('sector_index', Integer, nullable=False)
                )

    return tbl
