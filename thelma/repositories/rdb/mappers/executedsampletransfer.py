"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Executed sample transfer mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship

from thelma.entities.container import Container
from thelma.entities.liquidtransfer import ExecutedSampleTransfer
from thelma.entities.liquidtransfer import TRANSFER_TYPES


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(executed_liquid_transfer_mapper, executed_sample_transfer_tbl,
                  container_tbl):
    "Mapper factory."
    est = executed_sample_transfer_tbl
    cont = container_tbl
    m = mapper(ExecutedSampleTransfer, executed_sample_transfer_tbl,
               inherits=executed_liquid_transfer_mapper,
               properties=dict(
                    source_container=relationship(Container, uselist=False,
                            primaryjoin=(est.c.source_container_id == \
                                         cont.c.container_id)),
                    target_container=relationship(Container, uselist=False,
                            primaryjoin=(est.c.target_container_id == \
                                         cont.c.container_id)),
                    ),
               polymorphic_identity=TRANSFER_TYPES.SAMPLE_TRANSFER
               )
    return m
