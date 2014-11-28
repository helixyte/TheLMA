"""
Container table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from thelma.entities.container import CONTAINER_TYPES
from thelma.tools.semiconstants import ITEM_STATUS_NAMES

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, container_specs_tbl, item_status_tbl):
    "Table factory."
    tbl = Table('container', metadata,
        Column('container_id', Integer, primary_key=True),
        Column('container_specs_id', Integer,
               ForeignKey(container_specs_tbl.c.container_specs_id,
               # FIXME: pylint:disable=W0511
               #        Consider changing actions to
               #        'ON UPDATE CASCADE ON DELETE RESTRICT' in DB
               # onupdate='CASCADE', ondelete='RESTRICT'
               ),
               nullable=False),
        Column('item_status', String(9),
               ForeignKey(item_status_tbl.c.item_status_id,
                          onupdate='CASCADE', ondelete='RESTRICT'),
               nullable=False),
        Column('container_type', String(9),
               nullable=False, default=CONTAINER_TYPES.CONTAINER
               )
        )
    Index('stock_container_idx', tbl.c.container_id,
          postgresql_where=tbl.c.item_status == ITEM_STATUS_NAMES.MANAGED
                            and tbl.c.container_specs_id == 8)
    return tbl
