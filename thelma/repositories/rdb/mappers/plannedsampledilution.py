"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Planned sample dilution mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship

from thelma.entities.liquidtransfer import PlannedSampleDilution
from thelma.entities.liquidtransfer import TRANSFER_TYPES
from thelma.entities.rack import RackPosition


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(planned_liquid_transfer_mapper, planned_sample_dilution_tbl,
                  rack_position_tbl):
    "Mapper factory."
    psd = planned_sample_dilution_tbl
    rp = rack_position_tbl
    m = mapper(PlannedSampleDilution, planned_sample_dilution_tbl,
               inherits=planned_liquid_transfer_mapper,
               properties=dict(
                    _diluent_info=psd.c.diluent_info,
                    _target_position=relationship(RackPosition, uselist=False,
                        primaryjoin=(psd.c.target_position_id == \
                                     rp.c.rack_position_id)),
                               ),
               polymorphic_identity=TRANSFER_TYPES.SAMPLE_DILUTION
               )
    return m
