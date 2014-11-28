"""
Tagging table.
"""
from datetime import datetime
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy.schema import PrimaryKeyConstraint

__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, tagged_tbl, tag_tbl, dbuser_tbl):
    "Table factory."
    tbl = Table('tagging', metadata,
                Column('tagged_id', Integer,
                       ForeignKey(tagged_tbl.c.tagged_id,
                                  ondelete='CASCADE', onupdate='CASCADE'),
                       nullable=False),
                Column('tag_id', Integer,
                       ForeignKey(tag_tbl.c.tag_id), nullable=False,
                       ),
                Column('time_stamp', DateTime(timezone=True),
                       nullable=False, default=datetime.now
                       ),
                Column('user_id', Integer,
                       ForeignKey(dbuser_tbl.c.db_user_id),
                       nullable=False),
                )
    PrimaryKeyConstraint(tbl.c.tagged_id, tbl.c.tag_id)
    return tbl
