"""
Tube transfer mapper

AAB
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.entities.container import Tube
from thelma.entities.rack import RackPosition
from thelma.entities.rack import TubeRack
from thelma.entities.tubetransfer import TubeTransfer

__docformat__ = 'reStructuredText en'


__all__ = ['create_mapper']


def create_mapper(tube_transfer_tbl, rack_tbl, rack_position_tbl):
    """
    Planned container transfer class mapper factory
    """

    tt = tube_transfer_tbl
    r = rack_tbl
    rp = rack_position_tbl

    m = mapper(TubeTransfer, tube_transfer_tbl,
               id_attribute='tube_transfer_id',
               properties=dict(
                    tube=relationship(Tube, uselist=False),
                    source_rack=relationship(TubeRack, uselist=False,
                            primaryjoin=(tt.c.source_rack_id == r.c.rack_id)),
                    source_position=relationship(RackPosition, uselist=False,
                            primaryjoin=(tt.c.source_position_id == \
                                         rp.c.rack_position_id)),
                    target_rack=relationship(TubeRack, uselist=False,
                            primaryjoin=(tt.c.target_rack_id == r.c.rack_id)),
                    target_position=relationship(RackPosition, uselist=False,
                            primaryjoin=(tt.c.target_position_id == \
                                         rp.c.rack_position_id))
                               ),
               )
    return m
