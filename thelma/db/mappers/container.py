"""
Container mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.container import CONTAINER_TYPES
from thelma.models.container import Container
from thelma.models.container import ContainerLocation
from thelma.models.container import ContainerSpecs
from thelma.models.sample import Sample
from thelma.models.status import ItemStatus

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(container_tbl):
    "Mapper factory."
    m = mapper(Container, container_tbl,
           id_attribute='container_id',
           properties=
            dict(specs=relationship(ContainerSpecs, uselist=False),
                 location=relationship(ContainerLocation, uselist=False,
                                       back_populates='container',
                                       lazy='joined',
                                       cascade='all,delete,delete-orphan',
                                       single_parent=True
                                       ),
                 sample=relationship(Sample, uselist=False,
                                     back_populates='container',
                                     lazy='joined'
                                     ),
                 #empty=True or False if it has no sample or volume is 0
                 status=relationship(ItemStatus, uselist=False),
                 ),
            polymorphic_on=container_tbl.c.container_type,
            polymorphic_identity=CONTAINER_TYPES.CONTAINER
            )
    return m
