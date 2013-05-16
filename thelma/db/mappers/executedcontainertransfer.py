"""
Executed container transfer mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from thelma.models.container import Container
from thelma.models.liquidtransfer import ExecutedContainerTransfer
from thelma.models.liquidtransfer import TRANSFER_TYPES

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(executed_transfer_mapper, executed_container_transfer_tbl,
                  container_tbl):
    "Mapper factory."
    ect = executed_container_transfer_tbl
    cont = container_tbl
    m = mapper(ExecutedContainerTransfer, executed_container_transfer_tbl,
               inherits=executed_transfer_mapper,
               properties=dict(
                    source_container=relationship(Container, uselist=False,
                            primaryjoin=(ect.c.source_container_id == \
                                         cont.c.container_id)),
                    target_container=relationship(Container, uselist=False,
                            primaryjoin=(ect.c.target_container_id == \
                                         cont.c.container_id)),
                    ),
               polymorphic_identity=TRANSFER_TYPES.CONTAINER_TRANSFER
               )
    return m
