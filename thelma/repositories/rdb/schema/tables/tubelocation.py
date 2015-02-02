"""
Tube location table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy import UniqueConstraint


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, container_tbl, rack_tbl, rack_position_tbl):
    "Table factory."
    tbl = Table('tube_location', metadata,
        Column('rack_id', Integer,
               ForeignKey(rack_tbl.c.rack_id,
                          onupdate='CASCADE', ondelete='CASCADE'),
               index=True,
               nullable=False),
        Column('container_id', Integer,
               ForeignKey(container_tbl.c.container_id,
                          onupdate='NO ACTION', ondelete='CASCADE'),
               primary_key=True),
        Column('rack_position_id',
               ForeignKey(rack_position_tbl.c.rack_position_id),
               nullable=False)
        )
    UniqueConstraint(tbl.c.rack_id, tbl.c.rack_position_id,
                     name='uq_tube_location_rack_id_rack_position_id')
    return tbl
