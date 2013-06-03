"""
Executed transfer mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.liquidtransfer import ExecutedTransfer
from thelma.models.liquidtransfer import PlannedTransfer
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.user import User

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(executed_transfer_tbl):
    "Mapper factory."
    m = mapper(ExecutedTransfer, executed_transfer_tbl,
               id_attribute='executed_transfer_id',
               properties=dict(
                    user=relationship(User, uselist=False),
                    planned_transfer=relationship(PlannedTransfer,
                            uselist=False, back_populates='executed_transfers'),
                    ),
               polymorphic_on=executed_transfer_tbl.c.type,
               polymorphic_identity=TRANSFER_TYPES.LIQUID_TRANSFER
               )
    return m
