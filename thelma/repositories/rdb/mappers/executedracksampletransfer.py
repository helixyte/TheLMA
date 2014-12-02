"""
Executed rack transfer mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship

from thelma.entities.liquidtransfer import ExecutedRackSampleTransfer
from thelma.entities.liquidtransfer import TRANSFER_TYPES
from thelma.entities.rack import Rack


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(executed_liquid_transfer_mapper,
                  executed_rack_sample_transfer_tbl, rack_tbl):
    "Mapper factory."
    erst = executed_rack_sample_transfer_tbl
    r = rack_tbl
    m = mapper(ExecutedRackSampleTransfer, executed_rack_sample_transfer_tbl,
               inherits=executed_liquid_transfer_mapper,
               properties=dict(
                    source_rack=relationship(Rack, uselist=False,
                            primaryjoin=(erst.c.source_rack_id == r.c.rack_id)),
                    target_rack=relationship(Rack, uselist=False,
                            primaryjoin=(erst.c.target_rack_id == r.c.rack_id)),
                    ),
               polymorphic_identity=TRANSFER_TYPES.RACK_SAMPLE_TRANSFER
               )
    return m
