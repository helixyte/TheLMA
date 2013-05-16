"""
Tube transfer worklist mapper

AAB
"""
from sqlalchemy import String
from sqlalchemy import cast
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.models.tubetransfer import TubeTransfer
from thelma.models.tubetransfer import TubeTransferWorklist
from thelma.models.user import User

__docformat__ = 'reStructuredText en'

__all__ = ['create_mapper']


def create_mapper(tube_transfer_worklist_tbl, tube_transfer_tbl,
                  tube_transfer_worklist_member_tbl, user_tbl):
    """
    Planned container transfer class mapper factory
    """

    ttw = tube_transfer_worklist_tbl
    tt = tube_transfer_tbl
    ttwm = tube_transfer_worklist_member_tbl
    u = user_tbl

    m = mapper(TubeTransferWorklist, tube_transfer_worklist_tbl,
               properties=dict(
                    id=synonym('tube_transfer_worklist_id'),
                    user=relationship(User, uselist=False,
                            primaryjoin=(u.c.db_user_id == ttw.c.db_user_id)),
                    tube_transfers=relationship(TubeTransfer, uselist=True,
                            primaryjoin=(ttw.c.tube_transfer_worklist_id == \
                                            ttwm.c.tube_transfer_worklist_id),
                            secondaryjoin=(ttwm.c.tube_transfer_id == \
                                           tt.c.tube_transfer_id),
                            secondary=ttwm)
                               )
               )


    if isinstance(TubeTransferWorklist.slug, property):
        TubeTransferWorklist.slug = \
            hybrid_property(TubeTransferWorklist.slug.fget,
                            expr=lambda cls:
                                    cast(cls.tube_transfer_worklist_id,
                                         String))

    return m
