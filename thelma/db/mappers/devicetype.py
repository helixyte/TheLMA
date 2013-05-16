"""
Device type mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.device import Device, DeviceType

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(device_type_tbl):
    "Mapper factory."
    m = mapper(DeviceType, device_type_tbl,
        properties=dict(
            id=synonym('device_type_id'),
            devices=relationship(Device, back_populates='type'),
            ),
        )
    if isinstance(DeviceType.slug, property):
        DeviceType.slug = \
            hybrid_property(DeviceType.slug.fget,
                            expr=lambda cls: as_slug_expression(cls.name))
    return m
