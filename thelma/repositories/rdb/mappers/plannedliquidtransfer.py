"""
Planned liquid transfer mapper.
"""
from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from thelma.entities.liquidtransfer import PlannedLiquidTransfer
from thelma.entities.liquidtransfer import TRANSFER_TYPES


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(planned_liquid_transfer_tbl):
    "Mapper factory."
    m = mapper(PlannedLiquidTransfer, planned_liquid_transfer_tbl,
               id_attribute='planned_liquid_transfer_id',
               properties=dict(
                    _transfer_type=planned_liquid_transfer_tbl.c.transfer_type,
                    _volume=planned_liquid_transfer_tbl.c.volume,
                    _hash_value=planned_liquid_transfer_tbl.c.hash_value
                    ),
               slug_expression=lambda cls: as_slug_expression(cls._hash_value), # pylint: disable=W0212
               polymorphic_on=planned_liquid_transfer_tbl.c.transfer_type,
               polymorphic_identity=TRANSFER_TYPES.LIQUID_TRANSFER
               )
    return m
