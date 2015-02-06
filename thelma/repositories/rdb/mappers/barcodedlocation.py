"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Barcoded location mapper.
"""
from sqlalchemy.orm import column_property
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from thelma.entities.device import Device
from thelma.entities.location import BarcodedLocation
from thelma.entities.location import BarcodedLocationRack
from thelma.repositories.rdb.mappers.utils import CaseInsensitiveComparator


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(barcoded_location_tbl):
    "Mapper factory."
    m = mapper(BarcodedLocation, barcoded_location_tbl,
               id_attribute='barcoded_location_id',
               slug_expression=lambda cls: as_slug_expression(cls.name),
               properties=dict(
                label=column_property(
                    barcoded_location_tbl.c.label,
                    comparator_factory=CaseInsensitiveComparator
                    ),
                device=relationship(Device, uselist=False,
                                    back_populates='locations'),
                location_rack=relationship(BarcodedLocationRack,
                    uselist=False,
                    back_populates='location',
                    lazy='joined',
                    cascade='all,delete,delete-orphan',
                    ),
                ),
            )
    return m
