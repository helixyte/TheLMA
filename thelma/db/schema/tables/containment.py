"""
Containment table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy import UniqueConstraint

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, container_tbl, rack_tbl):
    "Table factory."
    tbl = Table('containment', metadata,
        Column('holder_id', Integer,
               ForeignKey(rack_tbl.c.rack_id,
                          onupdate='CASCADE', ondelete='CASCADE'),
               nullable=False),
        Column('held_id', Integer,
               ForeignKey(container_tbl.c.container_id,
                          onupdate='NO ACTION', ondelete='CASCADE'),
               primary_key=True),
        Column('col', Integer, CheckConstraint('col>=0'), nullable=False),
        Column('row', Integer, CheckConstraint('row>=0'), nullable=False),
        )
    UniqueConstraint(tbl.c.holder_id, tbl.c.row, tbl.c.col)
    return tbl
