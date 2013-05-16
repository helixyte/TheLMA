"""
Planned rack transfer mapper.
"""
from sqlalchemy.orm import mapper
from thelma.models.liquidtransfer import PlannedRackTransfer
from thelma.models.liquidtransfer import TRANSFER_TYPES

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(planned_transfer_mapper, planned_rack_transfer_tbl):
    "Mapper factory."
    m = mapper(PlannedRackTransfer, planned_rack_transfer_tbl,
               inherits=planned_transfer_mapper,
               polymorphic_identity=TRANSFER_TYPES.RACK_TRANSFER,
               )
    return m
