"""
Executed transfer mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.liquidtransfer import ExecutedTransfer
from thelma.models.liquidtransfer import PlannedTransfer
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.user import User

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(executed_transfer_tbl):
    "Mapper factory."
    m = mapper(ExecutedTransfer, executed_transfer_tbl,
               properties=dict(
                    id=synonym('executed_transfer_id'),
                    user=relationship(User, uselist=False),
                    planned_transfer=relationship(PlannedTransfer,
                            uselist=False, back_populates='executed_transfers'),
                    ),
               polymorphic_on=executed_transfer_tbl.c.type,
               polymorphic_identity=TRANSFER_TYPES.LIQUID_TRANSFER
               )
    if isinstance(ExecutedTransfer.slug, property):
        ExecutedTransfer.slug = \
            hybrid_property(ExecutedTransfer.slug.fget,
                    expr=lambda cls: as_slug_expression(cls.id)
                            )
    return m
