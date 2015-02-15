"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Tube mapper.
"""
from sqlalchemy import String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import case
from sqlalchemy.sql import cast
from sqlalchemy.sql import literal

from everest.repositories.rdb.utils import mapper
from thelma.entities.container import CONTAINER_TYPES
from thelma.entities.container import Tube
from thelma.entities.container import TubeLocation


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(container_mapper, tube_tbl):
    "Mapper factory."
    m = mapper(Tube, tube_tbl,
               inherits=container_mapper,
               slug_expression=lambda cls: case([(cls.barcode == None,
                                                  literal('no-barcode-') +
                                                  cast(cls.id, String))],
                                                else_=cls.barcode),
               properties=
                    dict(location=relationship(
                                    TubeLocation, uselist=False,
                                    back_populates='container',
                                    cascade='all,delete,delete-orphan',
                                    single_parent=True
                                    ),
                         ),
               polymorphic_identity=CONTAINER_TYPES.TUBE)
    return m
