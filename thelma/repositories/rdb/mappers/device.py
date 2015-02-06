"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Device mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from thelma.entities.device import Device
from thelma.entities.device import DeviceType
from thelma.entities.location import BarcodedLocation
from thelma.entities.organization import Organization


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(device_tbl):
    "Mapper factory."
    m = mapper(Device, device_tbl,
        id_attribute='device_id',
        slug_expression=lambda cls: as_slug_expression(cls.name),
        properties=dict(
            type=relationship(DeviceType),
            locations=relationship(BarcodedLocation, back_populates='device'),
            manufacturer=relationship(Organization, uselist=False),
            ),
        )
    return m
