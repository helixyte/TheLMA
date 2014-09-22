"""
ISO job preparation plate table
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = "reStructuredText en"
__all__ = ['create_table']

def create_table(metadata, rack_tbl, job_tbl, rack_layout_tbl):
    """Table Factory"""

    tbl = Table('iso_job_preparation_plate', metadata,
                Column('iso_job_preparation_plate_id', Integer,
                       primary_key=True),
                Column('rack_id', Integer,
                       ForeignKey(rack_tbl.c.rack_id),
                       nullable=False, unique=True),
                Column('rack_layout_id', Integer,
                       ForeignKey(rack_layout_tbl.c.rack_layout_id,
                                  onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False),
                Column('job_id', Integer,
                       ForeignKey(job_tbl.c.job_id,
                                  onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False)
                )

    return tbl
