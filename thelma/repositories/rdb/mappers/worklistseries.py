"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Worklist series mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import mapper
from thelma.entities.liquidtransfer import WorklistSeries
from thelma.entities.liquidtransfer import WorklistSeriesMember


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(worklist_series_tbl):
    "Mapper factory."
    m = mapper(WorklistSeries, worklist_series_tbl,
               id_attribute='worklist_series_id',
               properties=dict(
                    worklist_series_members=relationship(WorklistSeriesMember,
                        uselist=True, collection_class=list,
                        back_populates='worklist_series',
                        cascade='all,delete,delete-orphan')
                               )
               )
    return m
