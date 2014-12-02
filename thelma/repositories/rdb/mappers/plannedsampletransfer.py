"""
Planned sample transfer mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship

from thelma.entities.liquidtransfer import PlannedSampleTransfer
from thelma.entities.liquidtransfer import TRANSFER_TYPES
from thelma.entities.rack import RackPosition


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(planned_liquid_transfer_mapper, planned_sample_transfer_tbl,
                  rack_position_tbl):
    "Mapper factory."
    pst = planned_sample_transfer_tbl
    rp = rack_position_tbl
    m = mapper(PlannedSampleTransfer, planned_sample_transfer_tbl,
               inherits=planned_liquid_transfer_mapper,
               properties=dict(
                    _source_position=relationship(RackPosition, uselist=False,
                            primaryjoin=(pst.c.source_position_id == \
                                         rp.c.rack_position_id)),
                    _target_position=relationship(RackPosition, uselist=False,
                            primaryjoin=(pst.c.target_position_id == \
                                         rp.c.rack_position_id))
                               ),
               polymorphic_identity=TRANSFER_TYPES.SAMPLE_TRANSFER,
               )
    return m
