"""
Executed rack transfer mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from thelma.models.liquidtransfer import ExecutedRackTransfer
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.rack import Rack

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(executed_transfer_mapper, executed_rack_transfer_tbl,
                  rack_tbl):
    "Mapper factory."
    ect = executed_rack_transfer_tbl
    r = rack_tbl
    m = mapper(ExecutedRackTransfer, executed_rack_transfer_tbl,
               inherits=executed_transfer_mapper,
               properties=dict(
                    source_rack=relationship(Rack, uselist=False,
                            primaryjoin=(ect.c.source_rack_id == r.c.rack_id)),
                    target_rack=relationship(Rack, uselist=False,
                            primaryjoin=(ect.c.target_rack_id == r.c.rack_id)),
                    ),
               polymorphic_identity=TRANSFER_TYPES.RACK_TRANSFER
               )
    return m
