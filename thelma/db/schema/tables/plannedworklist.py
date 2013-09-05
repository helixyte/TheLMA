"""
Planned worklist table.
"""
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.schema import CheckConstraint
from thelma.models.liquidtransfer import TRANSFER_TYPES
from sqlalchemy.schema import ForeignKey

__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, pipetting_specs_tbl):
    "Table factory."
    tbl = Table('planned_worklist', metadata,
                Column('planned_worklist_id', Integer, primary_key=True),
                Column('label', String, nullable=False),
                Column('transfer_type', String(20),
                       CheckConstraint(
                       'transfer_type IN (\'%s\', \'%s\', \'%s\', \'%s\')'
                         % (TRANSFER_TYPES.LIQUID_TRANSFER,
                            TRANSFER_TYPES.SAMPLE_DILUTION,
                            TRANSFER_TYPES.SAMPLE_TRANSFER,
                            TRANSFER_TYPES.RACK_SAMPLE_TRANSFER)),
                       nullable=False),
                Column('pipetting_specs_id', Integer,
                       ForeignKey(pipetting_specs_tbl.c.pipetting_specs_id,
                                  onupdate='CASCADE'),
                       nullable=False)
                )
    return tbl
