"""
Sample mapper.
"""
from sqlalchemy import String
from sqlalchemy.orm import column_property
from sqlalchemy.sql import cast
from sqlalchemy.sql import literal
from sqlalchemy.sql import select
from sqlalchemy.sql.expression import and_
from sqlalchemy.sql.expression import func
from sqlalchemy.sql.expression import null
from sqlalchemy.sql.functions import coalesce

from everest.repositories.rdb.utils import mapper
from thelma.entities.sample import Sample
from thelma.repositories.rdb.utils import string_agg


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(sample_mpr, sample_tbl, sample_molecule_tbl, molecule_tbl,
                  molecule_design_pool_tbl):
    "Mapper factory."
    s = sample_tbl
    sm = sample_molecule_tbl
    m = molecule_tbl
    mdp = molecule_design_pool_tbl
    s1 = sample_tbl.alias()
    # FIXME: The following construct introduces a dependency on string_agg
    #        in the SQL engine. Consider a materialized view instead.
    mds_sel = select(
        [mdp.c.molecule_design_set_id],
        mdp.c.member_hash ==
          select([func.md5(
                    string_agg(cast(m.c.molecule_design_id, String),
                               literal(';'),
                               order_by=m.c.molecule_design_id))
                  ],
                 from_obj=[s1.join(sm,
                                   and_(sm.c.sample_id == s1.c.sample_id,
                                        s1.c.sample_id == s.c.sample_id))
                           .join(m,
                                 m.c.molecule_id == sm.c.molecule_id)
                           ]) \
                .group_by(sm.c.sample_id))
    m = mapper(Sample,
            inherits=sample_mpr,
            properties=dict(
#                container=relationship(Well,
#                                       uselist=False,
#                                       back_populates='sample'),
                molecule_design_pool_id=
                    column_property(coalesce(mds_sel.as_scalar(), null()),
                                    deferred=True),
                        )
            )
    return m
