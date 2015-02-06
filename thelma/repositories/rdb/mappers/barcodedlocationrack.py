"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Barcoded location rack mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from thelma.entities.location import BarcodedLocation
from thelma.entities.location import BarcodedLocationRack
from thelma.entities.rack import Rack


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(rack_barcoded_location_tbl):
    "Mapper factory."
    # FIXME: The table should be renamed to barcoded_location_rack.
    m = mapper(BarcodedLocationRack, rack_barcoded_location_tbl,
               id_attribute='barcoded_location_id',
               slug_expression=lambda cls: as_slug_expression(cls.name),
               properties=dict(
                rack=relationship(Rack,
                                  uselist=False,
                                  lazy='joined'
                                  ),
                location=relationship(BarcodedLocation,
                                      uselist=False)
                ),
            )
    return m
