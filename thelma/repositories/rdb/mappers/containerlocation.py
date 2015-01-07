"""
Container location mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship

from thelma.entities.container import Container
from thelma.entities.container import ContainerLocation
from thelma.entities.rack import Rack
from thelma.entities.rack import RackPosition


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(containment_tbl):
    "Mapper factory."
    cnt = containment_tbl.alias('containment_cnt_loc')
    m = mapper(ContainerLocation, cnt,
        properties=dict(
            position=relationship(RackPosition, uselist=False,
                                  innerjoin=True, lazy='subquery'),
            rack=relationship(Rack, uselist=False,
                              innerjoin=True,
#                              cascade='all',
                              back_populates='container_locations'),
            container=relationship(Container, uselist=False,
#                                   cascade='all,delete,delete-orphan',
#                                   single_parent=True,
                                   back_populates='location',
                                   innerjoin=True
#                                   lazy='joined'
                                   )
#                                   lazy='subquery'),
            ),
        )
    return m
