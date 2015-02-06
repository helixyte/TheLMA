"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Executed sample dilution mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship

from thelma.entities.container import Container
from thelma.entities.liquidtransfer import ExecutedSampleDilution
from thelma.entities.liquidtransfer import ReservoirSpecs
from thelma.entities.liquidtransfer import TRANSFER_TYPES


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(executed_liquid_transfer_mapper, executed_sample_dilution_tbl,
                  container_tbl):
    "Mapper factory."
    esd = executed_sample_dilution_tbl
    cont = container_tbl
    m = mapper(ExecutedSampleDilution, executed_sample_dilution_tbl,
               inherits=executed_liquid_transfer_mapper,
               properties=dict(
                    target_container=relationship(Container, uselist=False,
                            primaryjoin=(esd.c.target_container_id == \
                                         cont.c.container_id)),
                    reservoir_specs=relationship(ReservoirSpecs, uselist=False)
                    ),
               polymorphic_identity=TRANSFER_TYPES.SAMPLE_DILUTION
               )
    return m
