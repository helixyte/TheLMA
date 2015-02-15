"""
Container location mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship

from thelma.entities.container import Tube
from thelma.entities.container import TubeLocation
from thelma.entities.rack import RackPosition
from thelma.entities.rack import TubeRack


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(tube_location_tbl):
    "Mapper factory."
    m = mapper(TubeLocation, tube_location_tbl,
        properties=dict(
            position=relationship(RackPosition, uselist=False,
                                  innerjoin=True,
#                                  lazy='joined'
#                                  lazy='subquery'
                                  ),
            rack=relationship(TubeRack, uselist=False,
                              innerjoin=True,
#                              cascade='all',
                              back_populates='tube_locations'),
            container=relationship(Tube, uselist=False,
#                                   cascade='all,delete,delete-orphan',
#                                   single_parent=True,
                                   back_populates='location',
                                   innerjoin=True,
                                   cascade_backrefs=False
#                                   lazy='joined'
                                   )
#                                   lazy='subquery'),
            ),
        )
    return m
