"""
Tube mapper.
"""
from sqlalchemy import String
from sqlalchemy.orm import column_property
#from sqlalchemy.orm import relationship
from sqlalchemy.orm.deprecated_interfaces import MapperExtension
from sqlalchemy.sql import case
from sqlalchemy.sql import cast
from sqlalchemy.sql import literal
from sqlalchemy.sql import select
from sqlalchemy.sql.expression import delete
from sqlalchemy.sql.expression import insert

from everest.repositories.rdb.utils import mapper
from thelma.models.container import CONTAINER_TYPES
from thelma.models.container import Tube
#from thelma.models.sample import StockSample


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


class TubeMapperExtension(MapperExtension):
    def __init__(self, container_barcode_tbl):
        MapperExtension.__init__(self)
        self.__container_barcode_tbl = container_barcode_tbl

    def after_insert(self, cnt_mapper, connection, instance): # pylint:disable=W0613
        value_map = dict(container_id=instance.container_id,
                         barcode=instance.barcode)
        connection.execute(insert(self.__container_barcode_tbl,
                                  values=value_map))

    def before_delete(self, cnt_mapper, connection, instance): # pylint:disable=W0613
        connection.execute(delete(self.__container_barcode_tbl.c.container_id
                                        == instance.container_id))


def create_mapper(container_mapper, container_tbl, container_barcode_tbl):
    "Mapper factory."
    bc_select = select([container_barcode_tbl.c.barcode],
                       container_barcode_tbl.c.container_id ==
                                                container_tbl.c.container_id)
    m = mapper(Tube,
               slug_expression=lambda cls: case([(cls.barcode == None,
                                                  literal('no-barcode-') +
                                                  cast(cls.id, String))],
                                                else_=cls.barcode),
               extension=TubeMapperExtension(container_barcode_tbl),
               inherits=container_mapper,
               properties=
                dict(barcode=column_property(bc_select.as_scalar()),
#                     sample=relationship(Stock4Sample, uselist=False,
#                                         back_populates='container',
#                                         lazy='joined'
#                                         ),
                     ),
               polymorphic_identity=CONTAINER_TYPES.TUBE)
    return m
