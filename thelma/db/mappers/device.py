"""
Device mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.device import Device
from thelma.models.device import DeviceType
from thelma.models.location import BarcodedLocation
from thelma.models.organization import Organization

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(device_tbl):
    "Mapper factory."
    m = mapper(Device, device_tbl,
        properties=dict(
            id=synonym('device_id'),
            type=relationship(DeviceType),
            locations=relationship(BarcodedLocation, back_populates='device'),
            manufacturer=relationship(Organization, uselist=False),
            ),
        )
    if isinstance(Device.slug, property):
        Device.slug = \
            hybrid_property(Device.slug.fget,
                            expr=lambda cls: as_slug_expression(cls.name))
    return m
