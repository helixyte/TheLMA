"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Container barcode table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, container_tbl):
    "Table factory."
    tbl = Table('container_barcode', metadata,
        Column('container_id', Integer,
               ForeignKey(container_tbl.c.container_id,
                          onupdate='NO ACTION', ondelete='CASCADE'),
               primary_key=True),
        Column('barcode', String, CheckConstraint("barcode<>''"),
               nullable=False, unique=True),
        )
    return tbl
