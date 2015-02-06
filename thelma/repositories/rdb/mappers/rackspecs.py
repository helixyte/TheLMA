"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Rack specs mapper.
"""
from sqlalchemy.orm import column_property
from sqlalchemy.orm import relationship
from sqlalchemy.sql import case
from sqlalchemy.sql import literal
from sqlalchemy.sql import select

from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from everest.repositories.rdb.utils import synonym
from thelma.entities.organization import Organization
from thelma.entities.rack import RACK_SPECS_TYPES
from thelma.entities.rack import RackShape
from thelma.entities.rack import RackSpecs


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(rack_specs_tbl):
    "Mapper factory."
    rs = rack_specs_tbl
    polymorphic_select = select([
        rs,
        (case([(rs.c.has_movable_subitems,
                literal(RACK_SPECS_TYPES.TUBE_RACK_SPECS))],
              else_=literal(RACK_SPECS_TYPES.PLATE_SPECS))).label(
                                                            'rackspecs_type')
        ],
        ).alias('rackspecs')
    m = mapper(RackSpecs, polymorphic_select,
            id_attribute='rack_specs_id',
            slug_expression=lambda cls: as_slug_expression(cls.name),
            properties=dict(
                manufacturer=relationship(Organization),
                shape=relationship(RackShape, uselist=False,
                                   back_populates='specs'),
                rack_specs_type=
                        column_property(polymorphic_select.c.rackspecs_type),
                ),
            polymorphic_on=polymorphic_select.c.rackspecs_type,
            polymorphic_identity=RACK_SPECS_TYPES.RACK_SPECS,
            )
    RackSpecs.has_tubes = synonym('has_movable_subitems')
    return m
