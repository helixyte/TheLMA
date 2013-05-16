"""
Tagged rack position set table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import Table

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, rack_layout_tbl, tagged_tbl, rack_position_set_tbl):
    "Table factory."
    tbl = Table('tagged_rack_position_set', metadata,
                Column('rack_layout_id', Integer,
                       ForeignKey(rack_layout_tbl.c.rack_layout_id,
                                  ondelete='CASCADE', onupdate='CASCADE'),
                       nullable=False),
                Column('tagged_id', Integer,
                       ForeignKey(tagged_tbl.c.tagged_id),
                       nullable=False),
                Column('rack_position_set_id', Integer,
                       ForeignKey(rack_position_set_tbl.c.rack_position_set_id,
                                  onupdate='CASCADE', ondelete='RESTRICT'),
                       nullable=False),
                        )
    PrimaryKeyConstraint(tbl.c.rack_layout_id, tbl.c.tagged_id)
    return tbl
