"""
Planned worklist mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.liquidtransfer import ExecutedWorklist
from thelma.models.liquidtransfer import PlannedTransfer
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import WorklistSeriesMember

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(planned_worklist_tbl, planned_transfer_tbl,
                  planned_worklist_member_tbl):
    "Mapper factory."
    pw = planned_worklist_tbl
    pwm = planned_worklist_member_tbl
    pt = planned_transfer_tbl
    m = mapper(PlannedWorklist, planned_worklist_tbl,
               properties=dict(
                    id=synonym('planned_worklist_id'),
                    planned_transfers=relationship(PlannedTransfer,
                            uselist=True,
                            primaryjoin=(pw.c.planned_worklist_id == \
                                         pwm.c.planned_worklist_id),
                            secondaryjoin=(pwm.c.planned_transfer_id == \
                                           pt.c.planned_transfer_id),
                            secondary=pwm,
                            back_populates='planned_worklist'),
                    worklist_series_member=relationship(WorklistSeriesMember,
                            uselist=False, back_populates='planned_worklist'),
                    executed_worklists=relationship(ExecutedWorklist,
                            collection_class=list,
                            back_populates='planned_worklist')
                    )
               )
    if isinstance(PlannedWorklist.slug, property):
        PlannedWorklist.slug = \
            hybrid_property(PlannedWorklist.slug.fget,
                    expr=lambda cls: as_slug_expression(cls.id)
                            )
    return m