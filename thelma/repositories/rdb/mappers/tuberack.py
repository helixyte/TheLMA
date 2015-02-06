"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Tube rack mapper.
"""
from sqlalchemy.orm import column_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.sql import func
from sqlalchemy.sql import select

from thelma.entities.container import Tube
from thelma.entities.container import TubeLocation
from thelma.entities.rack import RACK_TYPES
from thelma.entities.rack import TubeRack


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(rack_mapper, tube_rack_tbl, tube_location_tbl):
    "Mapper factory."
    tl = tube_location_tbl
    m = mapper(TubeRack, tube_rack_tbl,
               inherits=rack_mapper,
               properties=dict(
                container_locations=
                    relationship(TubeLocation,
                                 collection_class=
                                    attribute_mapped_collection('position'),
                                 back_populates='rack',
                                 cascade='all,delete,delete-orphan'),
                total_containers=column_property(
                            select([func.count(tl.c.container_id)],
                                   tube_rack_tbl.c.rack_id == tl.c.rack_id)),
                # FIXME: pylint:disable=W0511
                #        Investigate how to enable a r/w relationship here.
                containers=\
                    relationship(Tube, viewonly=True,
                                 secondary=tube_location_tbl)
                               ),
               polymorphic_identity=RACK_TYPES.TUBE_RACK)
    return m
