"""
Stock sample creation ISO request table.
"""
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy.schema import CheckConstraint
from sqlalchemy.schema import PrimaryKeyConstraint

__docformat__ = "reStructuredText en"
__all__ = ['create_table']

def create_table(metadata, iso_request_tbl):
    "Table factory"
    tbl = Table('stock_sample_creation_iso_request', metadata,
                Column('iso_request_id', Integer,
                       ForeignKey(iso_request_tbl.c.iso_request_id,
                                  onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False),
                Column('stock_volume', Float,
                       CheckConstraint('stock_volume>0'),
                       nullable=False),
                Column('stock_concentration', Float,
                       CheckConstraint('stock_concentration>0'),
                       nullable=False),
                Column('number_designs', Integer,
                       CheckConstraint('number_designs>1'),
                       nullable=False),
                Column('preparation_plate_volume', Float,
                       CheckConstraint('preparation_plate_volume>0')),
                )
    PrimaryKeyConstraint(tbl.c.iso_request_id)

    return tbl
