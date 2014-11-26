"""
Rack table.
"""
from datetime import datetime

from sqlalchemy import CHAR
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.schema import DDL

from thelma.db.utils import BarcodeSequence
from thelma.entities.rack import RACK_TYPES


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def _setup_postgres_ddl(table):
    """
    Barcode default for PostgreSQL and a sequence to support the legacy DB
    """
    DDL("""
        ALTER TABLE %(table)s ALTER COLUMN barcode SET DATA TYPE cenix_barcode
        """,
        on='postgres'
        ).execute_at('after-create', table)


def _setup_sqlite_ddl(table):
    """
    Barcode default for SQLite using a trigger and the ROWID as the sequence

    It does not conform to how the legacy DB is setup but testing on sqlite
    should not fail. Since we do not plan to use SQLite as the production
    database the DDL below serves only to support development/testing.
    """
    DDL("""
    CREATE TRIGGER set_rack_barcode AFTER INSERT ON rack
    BEGIN
      UPDATE rack
        SET barcode =
          SUBSTR("00000000", length(new.rowid), 8-length(new.rowid)) ||
          new.rowid
        WHERE rowid = new.rowid;
    END;
    """,
    on='sqlite'
    ).execute_at('after-create', table)


def create_table(metadata, item_status_tbl, rack_specs_tbl):
    "Table factory."
    tbl = Table('rack', metadata,
        Column('rack_id', Integer, primary_key=True),
        Column('barcode', CHAR, BarcodeSequence('barcode_seq',
                                                start=2400000),
               nullable=False, unique=True, index=True),
        Column('creation_date', DateTime(timezone=True), nullable=False,
               default=datetime.now),
        Column('label', String, nullable=False, default=''),
        Column('comment', String, nullable=False, default=''),
        Column('item_status', String,
               ForeignKey(item_status_tbl.c.item_status_id,
                          onupdate='CASCADE', ondelete='RESTRICT'),
               nullable=False),
        Column('rack_specs_id', Integer,
               ForeignKey(rack_specs_tbl.c.rack_specs_id,
                          onupdate='CASCADE', ondelete='RESTRICT'),
               nullable=False),
        Column('rack_type', String(9), nullable=False,
               default=RACK_TYPES.RACK),
        )
    _setup_postgres_ddl(tbl)
    _setup_sqlite_ddl(tbl)
    return tbl
