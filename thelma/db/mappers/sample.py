"""
Sample mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy import String
from sqlalchemy.orm import column_property
from sqlalchemy.orm import relationship
from sqlalchemy.sql import cast
from sqlalchemy.sql import literal
from sqlalchemy.sql import select
from sqlalchemy.sql.expression import and_
from sqlalchemy.sql.expression import func
from sqlalchemy.sql.expression import null
from sqlalchemy.sql.functions import coalesce
from thelma.db.utils import string_agg
from thelma.models.container import Container
from thelma.models.sample import SAMPLE_TYPES
from thelma.models.sample import Sample
from thelma.models.sample import SampleMolecule
#from sqlalchemy.schema import ForeignKey
#from thelma.models.moleculedesign import MoleculeDesignPool

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(sample_tbl, sample_molecule_tbl, molecule_tbl,
                  molecule_design_pool_tbl):
    "Mapper factory."
    s = sample_tbl
    sm = sample_molecule_tbl
    m = molecule_tbl
    mdp = molecule_design_pool_tbl
    s1 = sample_tbl.alias()
    # FIXME: The following construct introduces a dependency on string_agg
    #        in the SQL engine.
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
    m = mapper(Sample, sample_tbl,
        id_attribute='sample_id',
        properties=dict(
            molecule_design_pool_id=
                    column_property(coalesce(mds_sel.as_scalar(), null())),
            container=relationship(Container,
                                   uselist=False,
                                   back_populates='sample'),
            sample_molecules=
                    relationship(SampleMolecule,
                                 back_populates='sample',
                                 lazy='joined'
                                 ),
            ),
        polymorphic_on=sample_tbl.c.sample_type,
        polymorphic_identity=SAMPLE_TYPES.BASIC
        )
#    fkey_mds = ForeignKey(ssmds.c.molecule_design_set_id)
#    fkey_mds.parent = mds_sel.c.molecule_design_set_id
#    mds_sel.c.molecule_design_set_id.foreign_keys.add(fkey_mds)
#    fkey_s = ForeignKey(s.c.sample_id)
#    fkey_s.parent = mds_sel.c.sample_id
#    mds_sel.c.sample_id.foreign_keys.add(fkey_s)
#    m.add_property('molecule_design_set',
#                   relationship(MoleculeDesignPool,
#                                viewonly=True,
#                                uselist=False,
#                                lazy='joined',
#                                primaryjoin=
#                                    and_(s.c.sample_id == mds_sel.c.sample_id,
#                                    mds_sel.c.molecule_design_set_id ==
#                                            ssmds.c.molecule_design_set_id),
#                                foreign_keys=mds_sel.c.molecule_design_set_id
#                                )
#                   )
#                                secondary=mds_sel,
#                                primaryjoin=mds_sel.c.sample_id == s2.c.sample_id,
#                                secondaryjoin=
#                                        ssmds.c.molecule_design_set_id ==
#                                              mds_sel.c.molecule_design_set_id,
#                                foreign_keys=(mds_sel.c.sample_id,
#                                              mds_sel.c.molecule_design_set_id)
#                                )
#                   )
    return m
