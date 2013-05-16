"""
Target set mapper.
"""
from sqlalchemy import String
from sqlalchemy import cast
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.models.gene import Target
from thelma.models.gene import TargetSet

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


#FIXME: no name on DB level #pylint: disable=W0511
def create_mapper(target_set_tbl, target_tbl, target_set_member_tbl):
    "Mapper factory."
    ts = target_set_tbl
    t = target_tbl
    tsm = target_set_member_tbl
    m = mapper(TargetSet, target_set_tbl,
               properties=dict(
                    id=synonym('target_set_id'),
                    targets=relationship(
                        Target, viewonly=True, collection_class=set,
                        primaryjoin=(tsm.c.target_set_id == ts.c.target_set_id),
                        secondaryjoin=(tsm.c.target_id == t.c.target_id),
                        foreign_keys=(tsm.c.target_set_id, tsm.c.target_id),
                        secondary=target_set_member_tbl)
                    )
               )
    if isinstance(TargetSet.slug, property):
        TargetSet.slug = \
            hybrid_property(TargetSet.slug.fget,
                            expr=lambda cls: cast(cls.target_set_id, String))
    return m
