"""
Barcoded location mapper.
"""
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import column_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from sqlalchemy.sql import exists
from sqlalchemy.sql import select
from thelma.db.mappers.utils import CaseInsensitiveComparator
from thelma.db.mappers.utils import as_slug_expression
from thelma.models.device import Device
from thelma.models.location import BarcodedLocation
from thelma.models.rack import Rack

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(barcoded_location_tbl, rack_barcoded_location_tbl):
    "Mapper factory."
    bl = barcoded_location_tbl.alias('bl')
    rbl = rack_barcoded_location_tbl.alias('rbl')
    m = mapper(BarcodedLocation, bl,
        properties=dict(
            id=synonym('barcoded_location_id'),
            label=column_property(
                bl.c.label,
                comparator_factory=CaseInsensitiveComparator
                ),
            device=relationship(Device, uselist=False,
                                back_populates='locations'),
            rack=relationship(Rack,
                uselist=False, back_populates='location', secondary=rbl,
                foreign_keys=(rbl.c.rack_id, rbl.c.barcoded_location_id),
                ),
            checkin_date=column_property(
                    select([rbl.c.checkin_date],
                    bl.c.barcoded_location_id == rbl.c.barcoded_location_id)
                    ),
            empty=column_property(~exists(# the symbol "~" negates the clause
                    select([rbl.c.barcoded_location_id],
                        bl.c.barcoded_location_id == rbl.c.barcoded_location_id
                        )
                    )
                ),
            ),
        )
    if isinstance(BarcodedLocation.slug, property):
        BarcodedLocation.slug = \
            hybrid_property(BarcodedLocation.slug.fget,
                            expr=lambda cls: as_slug_expression(cls.name))
    return m
