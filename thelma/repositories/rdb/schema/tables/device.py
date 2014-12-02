"""
Device table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.schema import DDL


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def _setup_postgres_ddl(table):
    DDL("""
        ALTER TABLE %(table)s ALTER COLUMN "name" SET DATA TYPE name
        """,
        on='postgres'
        ).execute_at('after-create', table)


def create_table(metadata, device_type_tbl, organization_tbl):
    "Table factory."
    tbl = Table('device', metadata,
        Column('device_id', Integer, primary_key=True),
        Column('device_type_id', Integer,
               ForeignKey(device_type_tbl.c.device_type_id,
                          onupdate='CASCADE', ondelete='RESTRICT'),
               nullable=False),
        Column('label', String(32), nullable=False),
        Column('model', String(64), nullable=False),
        Column('name', String, nullable=False, unique=True),
        Column('manufacturer_id', Integer,
               ForeignKey(organization_tbl.c.organization_id,
                          onupdate='CASCADE', ondelete='RESTRICT'),
               nullable=False),
        )
    _setup_postgres_ddl(tbl)
    return tbl
