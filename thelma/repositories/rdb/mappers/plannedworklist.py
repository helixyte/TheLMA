"""
Planned worklist mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.entities.liquidtransfer import ExecutedWorklist
from thelma.entities.liquidtransfer import PipettingSpecs
from thelma.entities.liquidtransfer import PlannedLiquidTransfer
from thelma.entities.liquidtransfer import PlannedWorklist
from thelma.entities.liquidtransfer import WorklistSeriesMember

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(planned_worklist_tbl, planned_liquid_transfer_tbl,
                  planned_worklist_member_tbl):
    "Mapper factory."
    pw = planned_worklist_tbl
    pwm = planned_worklist_member_tbl
    plt = planned_liquid_transfer_tbl
    m = mapper(PlannedWorklist, planned_worklist_tbl,
               id_attribute='planned_worklist_id',
               properties=dict(
                    pipetting_specs=relationship(PipettingSpecs, uselist=False),
                    planned_liquid_transfers=relationship(PlannedLiquidTransfer,
                            primaryjoin=(pw.c.planned_worklist_id == \
                                         pwm.c.planned_worklist_id),
                            secondaryjoin=(pwm.c.planned_liquid_transfer_id == \
                                           plt.c.planned_liquid_transfer_id),
                            secondary=pwm),
                    worklist_series_member=relationship(WorklistSeriesMember,
                            uselist=False, back_populates='planned_worklist'),
                    executed_worklists=relationship(ExecutedWorklist,
                            collection_class=list,
                            back_populates='planned_worklist')
                    )
               )
    return m
