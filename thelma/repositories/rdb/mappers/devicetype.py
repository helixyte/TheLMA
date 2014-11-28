"""
Device type mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from everest.repositories.rdb.utils import as_slug_expression
from thelma.entities.device import Device
from thelma.entities.device import DeviceType

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(device_type_tbl):
    "Mapper factory."
    m = mapper(DeviceType, device_type_tbl,
               id_attribute='device_type_id',
               slug_expression=lambda cls: as_slug_expression(cls.name),
               properties=dict(
                    devices=relationship(Device, back_populates='type'),
                    ),
               )
    return m
