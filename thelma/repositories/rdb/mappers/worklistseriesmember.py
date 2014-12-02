"""
Worklist series member mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship

from thelma.entities.liquidtransfer import PlannedWorklist
from thelma.entities.liquidtransfer import WorklistSeries
from thelma.entities.liquidtransfer import WorklistSeriesMember


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(worklist_series_member_tbl):
    "Mapper factory."
    m = mapper(WorklistSeriesMember, worklist_series_member_tbl,
               properties=dict(
                    worklist_series=relationship(WorklistSeries,
                        uselist=False,
                        back_populates='worklist_series_members'),
                    planned_worklist=relationship(PlannedWorklist,
                        uselist=False,
                        back_populates='worklist_series_member',
                        cascade='all,delete,delete-orphan',
                        single_parent=True),
                    )
               )
    return m
