"""
ISO request molecule design pool set association table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy.schema import PrimaryKeyConstraint

__docformat__ = "reStructuredText en"
__all__ = ['create_table']

def create_table(metadata, iso_request_tbl, molecule_design_pool_set_tbl):
    "Table factory"
    tbl = Table('iso_request_pool_set', metadata,
                Column('iso_request_id', Integer,
                       ForeignKey(iso_request_tbl.c.iso_request_id,
                                  ondelete='CASCADE', onupdate='CASCADE'),
                       nullable=False),
                Column('molecule_design_pool_set_id', Integer,
                       ForeignKey(molecule_design_pool_set_tbl.\
                                  c.molecule_design_pool_set_id),
                       nullable=False),
                )
    PrimaryKeyConstraint(tbl.c.iso_request_id)
    return tbl
