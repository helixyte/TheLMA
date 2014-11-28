"""
Executed liquid transfer table.
"""
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.schema import CheckConstraint
from thelma.entities.liquidtransfer import TRANSFER_TYPES

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, planned_liquid_transfer_tbl, user_tbl):
    "Table function."
    tbl = Table('executed_liquid_transfer', metadata,
                Column('executed_liquid_transfer_id', Integer,
                       primary_key=True),
                Column('planned_liquid_transfer_id', Integer,
                       ForeignKey(planned_liquid_transfer_tbl.c.\
                                  planned_liquid_transfer_id,
                                  onupdate='CASCADE'),
                       nullable=False),
                Column('db_user_id', Integer, ForeignKey(user_tbl.c.db_user_id),
                       nullable=False),
                Column('timestamp', DateTime(timezone=True), nullable=False),
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
