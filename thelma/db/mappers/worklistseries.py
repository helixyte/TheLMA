"""
Worklist series mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.liquidtransfer import WorklistSeries
from thelma.models.liquidtransfer import WorklistSeriesMember

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(worklist_series_tbl):
    "Mapper factory."
    m = mapper(WorklistSeries, worklist_series_tbl,
               properties=dict(
                    id=synonym('worklist_series_id'),
                    worklist_series_members=relationship(WorklistSeriesMember,
                        uselist=True, collection_class=list,
                        back_populates='worklist_series',
                        cascade='all,delete,delete-orphan')
                               )
               )
    if isinstance(WorklistSeries.slug, property):
        WorklistSeries.slug = \
            hybrid_property(WorklistSeries.slug.fget,
                            expr=lambda cls: as_slug_expression(cls.id))
    return m
