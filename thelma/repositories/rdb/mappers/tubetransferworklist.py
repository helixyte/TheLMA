"""
Tube transfer worklist mapper

AAB
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.entities.tubetransfer import TubeTransfer
from thelma.entities.tubetransfer import TubeTransferWorklist
from thelma.entities.user import User

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
               id_attribute='tube_transfer_worklist_id',
               properties=dict(
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
    return m
