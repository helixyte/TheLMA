"""
Executed liquid transfer mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.liquidtransfer import ExecutedLiquidTransfer
from thelma.models.liquidtransfer import PlannedLiquidTransfer
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.user import User

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(executed_liquid_transfer_tbl):
    "Mapper factory."
    m = mapper(ExecutedLiquidTransfer, executed_liquid_transfer_tbl,
               id_attribute='executed_liquid_transfer_id',
               properties=dict(
                    user=relationship(User, uselist=False),
                    planned_liquid_transfer=relationship(PlannedLiquidTransfer,
                                                         uselist=False),
                    ),
               polymorphic_on=executed_liquid_transfer_tbl.c.transfer_type,
               polymorphic_identity=TRANSFER_TYPES.LIQUID_TRANSFER
               )
    return m
