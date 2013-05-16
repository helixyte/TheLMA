"""
Planned container dilution mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from thelma.models.liquidtransfer import PlannedContainerDilution
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.rack import RackPosition

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(planned_transfer_mapper, planned_container_dilution_tbl,
                  rack_position_tbl):
    "Mapper factory."
    pcd = planned_container_dilution_tbl
    rp = rack_position_tbl
    m = mapper(PlannedContainerDilution, planned_container_dilution_tbl,
               inherits=planned_transfer_mapper,
               properties=dict(
                    target_position=relationship(RackPosition, uselist=False,
                        primaryjoin=(pcd.c.target_position_id == \
                                             rp.c.rack_position_id)),
                               ),
               polymorphic_identity=TRANSFER_TYPES.CONTAINER_DILUTION
               )
    return m
