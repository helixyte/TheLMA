"""
Rack mapper.
"""
from sqlalchemy.orm import column_property
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from thelma.entities.location import BarcodedLocation
from thelma.entities.location import BarcodedLocationRack
from thelma.entities.rack import RACK_TYPES
from thelma.entities.rack import Rack
from thelma.entities.rack import RackSpecs
from thelma.entities.status import ItemStatus
from thelma.repositories.rdb.mappers.utils import CaseInsensitiveComparator


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(rack_tbl, rack_barcoded_location_tbl):
    "Mapper factory."
    rbl = rack_barcoded_location_tbl
    m = mapper(Rack, rack_tbl,
        id_attribute='rack_id',
        slug_expression=lambda cls: as_slug_expression(cls.barcode),
        properties=dict(
            label=column_property(
                rack_tbl.c.label,
                comparator_factory=CaseInsensitiveComparator
                ),
            specs=relationship(RackSpecs,
                               innerjoin=True, uselist=False),
            status=relationship(ItemStatus,
                                innerjoin=True, uselist=False),
            location_rack=relationship(BarcodedLocationRack,
                                         uselist=False,
                                         back_populates='rack',
                                         cascade='all,delete,delete-orphan'),
            _location=relationship(BarcodedLocation, viewonly=True,
                uselist=False,
                secondary=rbl,
                foreign_keys=(rbl.c.rack_id, rbl.c.barcoded_location_id),
                ),
            ),
        polymorphic_on=rack_tbl.c.rack_type,
        polymorphic_identity=RACK_TYPES.RACK,
        )
    return m
