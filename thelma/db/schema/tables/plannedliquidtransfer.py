"""
Planned liquid transfer table.
"""
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from thelma.models.liquidtransfer import TRANSFER_TYPES

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata):
    "Table factory."
    tbl = Table('planned_liquid_transfer', metadata,
                Column('planned_liquid_transfer_id', Integer, primary_key=True),
                Column('volume', Float, CheckConstraint('volume>0'),
                       nullable=False),
                Column('hash_value', String(32), unique=True, nullable=False),
                Column('transfer_type', String(20),
                       CheckConstraint(
                       'transfer_type IN (\'%s\', \'%s\', \'%s\', \'%s\')'
                         % (TRANSFER_TYPES.LIQUID_TRANSFER,
                            TRANSFER_TYPES.SAMPLE_DILUTION,
                            TRANSFER_TYPES.SAMPLE_TRANSFER,
                            TRANSFER_TYPES.RACK_SAMPLE_TRANSFER)),
                       nullable=False)
                )
    return tbl
