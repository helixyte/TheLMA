"""
Rack specs container specs table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, rack_specs_tbl, container_specs_tbl):
    "Table factory."
    tbl = Table('rack_specs_container_specs', metadata,
        Column('rack_specs_id', Integer,
               ForeignKey(rack_specs_tbl.c.rack_specs_id),
               primary_key=True),
        Column('container_specs_id', Integer,
               ForeignKey(container_specs_tbl.c.container_specs_id),
               primary_key=True),
        )
    return tbl
