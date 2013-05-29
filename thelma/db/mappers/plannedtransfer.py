"""
Planned transfer mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.liquidtransfer import ExecutedTransfer
from thelma.models.liquidtransfer import PlannedTransfer
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import TRANSFER_TYPES

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(planned_transfer_tbl, planned_worklist_tbl,
                  planned_worklist_member_tbl):
    "Mapper factory."
    pt = planned_transfer_tbl
    pw = planned_worklist_tbl
    pwm = planned_worklist_member_tbl
    m = mapper(PlannedTransfer, planned_transfer_tbl,
               id_attribute='planned_transfer_id',
               properties=dict(
                    executed_transfers=relationship(ExecutedTransfer,
                                back_populates='planned_transfer'),
                    planned_worklist=relationship(PlannedWorklist,
                                primaryjoin=(pt.c.planned_transfer_id == \
                                             pwm.c.planned_transfer_id),
                                secondaryjoin=(pwm.c.planned_worklist_id == \
                                               pw.c.planned_worklist_id),
                                secondary=pwm,
                                back_populates='planned_transfers',
                                uselist=False)
                    ),
               polymorphic_on=planned_transfer_tbl.c.type,
               polymorphic_identity=TRANSFER_TYPES.LIQUID_TRANSFER
               )
    return m
