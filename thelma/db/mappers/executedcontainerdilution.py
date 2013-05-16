"""
Executed container dilution mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from thelma.models.container import Container
from thelma.models.liquidtransfer import ExecutedContainerDilution
from thelma.models.liquidtransfer import ReservoirSpecs
from thelma.models.liquidtransfer import TRANSFER_TYPES

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(executed_transfer_mapper, executed_container_dilution_tbl,
                  container_tbl):
    "Mapper factory."
    ecd = executed_container_dilution_tbl
    cont = container_tbl
    m = mapper(ExecutedContainerDilution, executed_container_dilution_tbl,
               inherits=executed_transfer_mapper,
               properties=dict(
                    target_container=relationship(Container, uselist=False,
                            primaryjoin=(ecd.c.target_container_id == \
                                         cont.c.container_id)),
                    reservoir_specs=relationship(ReservoirSpecs, uselist=False)
                    ),
               polymorphic_identity=TRANSFER_TYPES.CONTAINER_DILUTION
               )
    return m
