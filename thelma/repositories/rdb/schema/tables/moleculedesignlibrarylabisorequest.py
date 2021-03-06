"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Molecule design library lab ISO request association table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy.schema import PrimaryKeyConstraint


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, molecule_design_library_tbl, lab_iso_request_tbl):
    "Table factory."
    tbl = Table('molecule_design_library_lab_iso_request', metadata,
                Column('molecule_design_library_id', Integer,
                       ForeignKey(molecule_design_library_tbl.c.\
                                                molecule_design_library_id),
                       nullable=False),
                Column('iso_request_id', Integer,
                       ForeignKey(lab_iso_request_tbl.c.iso_request_id),
                       nullable=False),
        )
    PrimaryKeyConstraint(tbl.c.iso_request_id)
    return tbl
