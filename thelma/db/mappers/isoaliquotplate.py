"""
ISO aliquot plate mapper
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.iso import Iso
from thelma.models.iso import IsoAliquotPlate
from thelma.models.rack import Rack

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(iso_aliquot_plate_tbl):
    "Mapper factory."
    m = mapper(IsoAliquotPlate, iso_aliquot_plate_tbl,
               id_attribute='iso_aliquot_plate_id',
               properties=dict(
                    plate=relationship(Rack, uselist=False),
                    iso=relationship(Iso, uselist=False,
                        back_populates='iso_aliquot_plates'),
                    )
               )
    return m
