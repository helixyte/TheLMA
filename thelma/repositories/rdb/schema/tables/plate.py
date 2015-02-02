"""
Plate table.

Created on Jan 9, 2015
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table


def create_table(metadata, rack_tbl):
    "Table factory."
    tbl = Table('plate', metadata,
                Column('rack_id', Integer,
                       ForeignKey(rack_tbl.c.rack_id), primary_key=True)
                )
    return tbl
