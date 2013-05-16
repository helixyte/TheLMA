"""
Supplier molecule design table.
"""
from datetime import datetime
from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, organization_tbl):
    "Table factory."
    tbl = Table('supplier_molecule_design', metadata,
        Column('supplier_molecule_design_id', Integer, primary_key=True),
        Column('product_id', String,
               CheckConstraint('length(product_id)>0'),
               nullable=False),
        Column('supplier_id', Integer,
               ForeignKey(organization_tbl.c.organization_id,
                          onupdate='CASCADE', ondelete='CASCADE'),
               nullable=False),
        Column('time_stamp', DateTime(timezone=True),
               default=datetime.now),
        Column('is_current', Boolean, nullable=False, default=False),
        Column('is_deleted', Boolean, nullable=False, default=False),
        # FIXME: Drop this column after the migration has been completed.
        Column('sense_strand', String, default='unknown'),
        )
    Index('current_supplier_molecule_design',
          tbl.c.product_id, tbl.c.supplier_id,
          postgreql_where=tbl.c.is_current, unique=True)
    return tbl
