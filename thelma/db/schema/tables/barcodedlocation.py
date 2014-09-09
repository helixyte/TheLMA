"""
Barcoded location table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import UniqueConstraint
from sqlalchemy.schema import DDL


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def _setup_postgres_ddl(table):
    DDL("""
        ALTER TABLE %(table)s ALTER COLUMN barcode SET DATA TYPE cenix_barcode
        """,
        on='postgres'
        ).execute_at('after-create', table)

    DDL("""
        ALTER TABLE %(table)s ALTER COLUMN barcode SET DEFAULT
            lpad((nextval('barcode_seq'::regclass))::text, 8, '0'::text)
        """,
        on='postgres'
        ).execute_at('after-create', table)

    DDL("""
        ALTER TABLE %(table)s ALTER COLUMN "name" SET DATA TYPE name
        """,
        on='postgres'
        ).execute_at('after-create', table)


def create_table(metadata, device_tbl):
    "Table factory."
    tbl = Table('barcoded_location', metadata,
        Column('barcoded_location_id', Integer, primary_key=True),
        Column('barcode', String(8), server_default='barcode', unique=True),
        Column('name', String, nullable=False, unique=True),
        Column('label', String(128), nullable=False),
        Column('type', String(12), nullable=False),
        Column('device_id', Integer,
               ForeignKey(device_tbl.c.device_id,
                          onupdate='CASCADE', ondelete='CASCADE')
               ),
        Column('index', Integer),
        )
    UniqueConstraint(tbl.c.device_id, tbl.c.index)
    UniqueConstraint(tbl.c.device_id, tbl.c.label)
    _setup_postgres_ddl(tbl)
    #_setup_sqlite_ddl(tbl)
    return tbl
