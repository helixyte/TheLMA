"""
Sample mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy import String
from sqlalchemy import event
from sqlalchemy.orm import column_property
from sqlalchemy.orm import relationship
from sqlalchemy.orm.session import object_session
from sqlalchemy.orm.util import class_mapper
from sqlalchemy.sql import cast
from sqlalchemy.sql import literal
from sqlalchemy.sql import select
from sqlalchemy.sql.expression import and_
from sqlalchemy.sql.expression import func
from sqlalchemy.sql.expression import insert
from sqlalchemy.sql.expression import null
from sqlalchemy.sql.functions import coalesce
from thelma.repositories.rdb.utils import string_agg
from thelma.entities.container import Container
from thelma.entities.sample import SAMPLE_TYPES
from thelma.entities.sample import Sample
from thelma.entities.sample import SampleMolecule
from thelma.entities.sample import StockSample

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
                                 cascade='all,delete,delete-orphan',
                                 lazy='joined'
                                 ),
            ),
        polymorphic_on=sample_tbl.c.sample_type,
        polymorphic_identity=SAMPLE_TYPES.BASIC
        )
    # Listen to changes to the sample_type attribute.
    event.listen(Sample.sample_type, "set", check_set_sample_type) # pylint: disable=E1101
    return m


def check_set_sample_type(target, value, oldvalue, initiator): # pylint: disable=W0613
    if isinstance(target, Sample) \
       and value == SAMPLE_TYPES.STOCK \
       and oldvalue != SAMPLE_TYPES.STOCK:
        sess = object_session(target)
        if target.id is None:
            # We need a sample ID for the following execute statement to work.
            sess.flush()
        mdp = target.molecule_design_pool
        if mdp.id is None:
            sess.add(type(mdp), mdp)
            sess.flush()
        ss_tbl = class_mapper(StockSample).local_table
        sess.execute(insert(ss_tbl,
                            values=dict(sample_id=target.sample_id,
                                        molecule_design_set_id=
                                            target.molecule_design_pool.id,
                                        supplier_id=target.supplier.id,
                                        molecule_type_id=
                                            target.molecule_type.id,
                                        concentration=
                                            target.concentration)
                                  )
                           )
