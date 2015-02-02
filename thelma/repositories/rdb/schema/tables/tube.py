"""
Container table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table


__docformat__ = "reStructuredText en"
__all__ = ['create_table']


def create_table(metadata, container_tbl):
    "Table factory."
    tbl = Table('tube', metadata,
                Column('container_id', Integer,
                       ForeignKey(container_tbl.c.container_id),
                       primary_key=True),
                Column('barcode', String, nullable=False))
    return tbl
