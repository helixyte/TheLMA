"""
Well mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship

from thelma.entities.container import CONTAINER_TYPES
from thelma.entities.container import Well
from thelma.entities.rack import Plate
from thelma.entities.rack import RackPosition
from thelma.entities.sample import Sample


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(container_mapper, well_tbl):
    "Mapper factory."
    m = mapper(Well, well_tbl,
               inherits=container_mapper,
               properties=
                 dict(rack=relationship(Plate, uselist=False),
                      position=relationship(RackPosition, uselist=False),
                      sample=relationship(Sample, uselist=False,
                                          backref='container',
#                                          lazy='joined'
                                          ),
                      ),
               polymorphic_identity=CONTAINER_TYPES.WELL)
    # FIXME: need a slug here # pylint:disable=W0511
    return m
