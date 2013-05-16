"""
Executed worklist mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.liquidtransfer import ExecutedTransfer
from thelma.models.liquidtransfer import ExecutedWorklist
from thelma.models.liquidtransfer import PlannedWorklist

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(executed_worklist_tbl, executed_transfer_tbl,
                  executed_worklist_member_tbl):
    "Mapper factory."
    ew = executed_worklist_tbl
    ewm = executed_worklist_member_tbl
    et = executed_transfer_tbl
    m = mapper(ExecutedWorklist, executed_worklist_tbl,
               properties=dict(
                    id=synonym('executed_worklist_id'),
                    planned_worklist=relationship(PlannedWorklist,
                            uselist=False,
                            back_populates='executed_worklists'),
                    executed_transfers=relationship(ExecutedTransfer,
                            uselist=True,
                            primaryjoin=(ew.c.executed_worklist_id == \
                                         ewm.c.executed_worklist_id),
                            secondaryjoin=(ewm.c.executed_transfer_id == \
                                           et.c.executed_transfer_id),
                            secondary=ewm),
                    )
            )
    if isinstance(ExecutedWorklist.slug, property):
        ExecutedWorklist.slug = \
            hybrid_property(ExecutedWorklist.slug.fget,
                    expr=lambda cls: as_slug_expression(cls.id)
                            )
    return m
