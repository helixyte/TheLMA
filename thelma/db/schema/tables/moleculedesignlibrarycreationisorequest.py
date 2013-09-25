"""
Molecule design library creation ISO request association table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.schema import PrimaryKeyConstraint

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, molecule_design_library_tbl,
                 stock_sample_creation_iso_request_tbl):
    "Table factory."
    tbl = Table('molecule_design_library_creation_iso_request', metadata,
                Column('molecule_design_library_id', Integer,
                       ForeignKey(molecule_design_library_tbl.c.\
                                  molecule_design_library_id),
                       nullable=False),
                Column('iso_request_id', String,
                       ForeignKey(stock_sample_creation_iso_request_tbl.c.\
                                  iso_request_id),
                       nullable=False),
        )

    PrimaryKeyConstraint(tbl.c.molecule_design_library_id)

    return tbl
