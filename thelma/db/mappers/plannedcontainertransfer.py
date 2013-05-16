"""
Planned container transfer mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from thelma.models.liquidtransfer import PlannedContainerTransfer
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.rack import RackPosition

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(planned_transfer_mapper, planned_container_transfer_tbl,
                  rack_position_tbl):
    "Mapper factory."
    pct = planned_container_transfer_tbl
    rp = rack_position_tbl
    m = mapper(PlannedContainerTransfer, planned_container_transfer_tbl,
               inherits=planned_transfer_mapper,
               properties=dict(
                    source_position=relationship(RackPosition, uselist=False,
                            primaryjoin=(pct.c.source_position_id == \
                                         rp.c.rack_position_id)),
                    target_position=relationship(RackPosition, uselist=False,
                            primaryjoin=(pct.c.target_position_id == \
                                         rp.c.rack_position_id))
                               ),
               polymorphic_identity=TRANSFER_TYPES.CONTAINER_TRANSFER,
               )
    return m
