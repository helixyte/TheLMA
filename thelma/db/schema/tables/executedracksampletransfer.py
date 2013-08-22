"""
Executed rack sample transfer table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, executed_liquid_transfer_tbl, rack_tbl):
    "Table factory."
    tbl = Table('executed_rack_sample_transfer', metadata,
                Column('executed_transfer_id', Integer,
                       ForeignKey(executed_liquid_transfer_tbl.c.\
                                  executed_liquid_transfer_id,
                                  ondelete='CASCADE'),
                       nullable=False, primary_key=True),
                Column('source_rack_id', Integer,
                       ForeignKey(rack_tbl.c.rack_id,
                                  onupdate='CASCADE'),
                       nullable=False),
                Column('target_rack_id', Integer,
                       ForeignKey(rack_tbl.c.rack_id,
                                  onupdate='CASCADE'),
                       nullable=False),
                )

    return tbl
