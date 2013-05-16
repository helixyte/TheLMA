"""
Tube transfer mapper

AAB
"""
from sqlalchemy import String
from sqlalchemy import cast
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.models.container import Tube
from thelma.models.rack import RackPosition
from thelma.models.rack import TubeRack
from thelma.models.tubetransfer import TubeTransfer

__docformat__ = 'reStructuredText en'

__author__ = 'Anna-Antonia Berger'

__all__ = ['create_mapper']


def create_mapper(tube_transfer_tbl, rack_tbl, rack_position_tbl):
    """
    Planned container transfer class mapper factory
    """

    tt = tube_transfer_tbl
    r = rack_tbl
    rp = rack_position_tbl

    m = mapper(TubeTransfer, tube_transfer_tbl,
               properties=dict(
                    id=synonym('tube_transfer_id'),
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

    if isinstance(TubeTransfer.slug, property):
        TubeTransfer.slug = \
            hybrid_property(TubeTransfer.slug.fget,
                            expr=lambda cls: cast(cls.tube_transfer_id,
                                                  String))

    return m
