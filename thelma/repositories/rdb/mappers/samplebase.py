"""
Sample base mapper.
"""
from sqlalchemy import event
from sqlalchemy.orm import relationship
from sqlalchemy.orm.session import object_session
from sqlalchemy.orm.util import class_mapper
from sqlalchemy.sql.expression import insert

from everest.repositories.rdb.utils import mapper
from thelma.entities.sample import SAMPLE_TYPES
from thelma.entities.sample import SampleBase
from thelma.entities.sample import SampleMolecule
from thelma.entities.sample import StockSample


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(sample_tbl):
    "Mapper factory."
    m = mapper(SampleBase, sample_tbl,
        id_attribute='sample_id',
        properties=dict(
            sample_molecules=
                    relationship(SampleMolecule,
                                 back_populates='sample',
                                 cascade='all,delete,delete-orphan',
#                                 lazy='joined'
                                 ),
            ),
        polymorphic_on=sample_tbl.c.sample_type,
        polymorphic_identity=SAMPLE_TYPES.BASIC
        )
    # Listen to changes to the sample_type attribute.
    event.listen(SampleBase.sample_type, "set", check_set_sample_type) # pylint: disable=E1101
    return m


def check_set_sample_type(target, value, oldvalue, initiator): # pylint: disable=W0613
    if isinstance(target, SampleBase) \
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
