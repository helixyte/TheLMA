"""
Rack mapper.
"""
from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import column_property
from sqlalchemy.orm import relationship
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.sql import func
from sqlalchemy.sql import select
from thelma.db.mappers.utils import CaseInsensitiveComparator
from thelma.models.container import Container
from thelma.models.container import ContainerLocation
from thelma.models.location import BarcodedLocation
from thelma.models.rack import RACK_TYPES
from thelma.models.rack import Rack
from thelma.models.rack import RackSpecs
from thelma.models.status import ItemStatus

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(rack_tbl, rack_barcoded_location_tbl,
                  container_tbl, containment_tbl):
    "Mapper factory."
    r = rack_tbl
    rbl = rack_barcoded_location_tbl
    c = container_tbl
    cnt1 = containment_tbl.alias('containment_rack_1')
    cnt2 = containment_tbl.alias('containment_rack_2')
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
            location=relationship(BarcodedLocation,
                uselist=False, back_populates='rack', secondary=rbl,
                foreign_keys=(rbl.c.rack_id, rbl.c.barcoded_location_id),
                ),
            total_containers=column_property(
                select(
                    [func.count(cnt1.c.held_id)],
                    rack_tbl.c.rack_id == cnt1.c.holder_id)
                ),
            container_locations=
                relationship(ContainerLocation,
                             collection_class=
                                    attribute_mapped_collection('position'),
                             back_populates='rack',
                             cascade='all,delete,delete-orphan'),
            # FIXME: pylint:disable=W0511
            #        Investigate how to enable a r/w relationship here.
            containers=\
                relationship(Container, viewonly=True,
                             secondary=cnt2,
                             primaryjoin=(cnt2.c.holder_id == r.c.rack_id),
                             secondaryjoin=(c.c.container_id == cnt2.c.held_id),
                             foreign_keys=(cnt2.c.holder_id, cnt2.c.held_id),
#                             backref='rack',
                             )
            ),
        polymorphic_on=rack_tbl.c.rack_type,
        polymorphic_identity=RACK_TYPES.RACK,
        )
    return m
