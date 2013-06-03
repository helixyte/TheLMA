"""
Device mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from everest.repositories.rdb.utils import as_slug_expression
from thelma.models.device import Device
from thelma.models.device import DeviceType
from thelma.models.location import BarcodedLocation
from thelma.models.organization import Organization

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
