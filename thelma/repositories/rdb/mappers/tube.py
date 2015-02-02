"""
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
from thelma.entities.sample import SampleBase


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
#                                    lazy='joined',
                                    cascade='all,delete,delete-orphan',
                                    single_parent=True
                                    ),
                         sample=relationship(SampleBase, uselist=False,
#                                             lazy='joined'
                                             ),
                         ),
               polymorphic_identity=CONTAINER_TYPES.TUBE)
    return m
