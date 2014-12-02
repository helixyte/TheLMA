"""
ISO plate mapper
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import mapper
from thelma.entities.iso import ISO_PLATE_TYPES
from thelma.entities.iso import IsoPlate
from thelma.entities.rack import Rack


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(iso_plate_tbl):
    "Mapper factory."
    m = mapper(IsoPlate, iso_plate_tbl,
               id_attribute='iso_plate_id',
               polymorphic_on=iso_plate_tbl.c.iso_plate_type,
               polymorphic_identity=ISO_PLATE_TYPES.ISO_PLATE,
               properties=dict(
                    rack=relationship(Rack, uselist=False),
                               )
               )
    return m
