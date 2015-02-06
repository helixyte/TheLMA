"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Container location mapper.
"""
from sqlalchemy import sql
from sqlalchemy.orm import composite
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm.descriptor_props import CompositeProperty

from everest.repositories.rdb.querying import OrderClauseList
from thelma.entities.container import Container
from thelma.entities.container import ContainerLocation
from thelma.entities.rack import Rack
from thelma.entities.rack import RackPosition


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


class RackPositionComparator(CompositeProperty.Comparator): # pylint: disable=W0223
    """
    Custom comparator for rack positions.
    """
    def asc(self):
        return OrderClauseList(
                        *[sql.asc(clause)
                          for clause in self.__clause_element__().clauses])
    def desc(self):
        return OrderClauseList(
                        *[sql.desc(clause)
                          for clause in self.__clause_element__().clauses])


def create_mapper(containment_tbl):
    "Mapper factory."
    cnt = containment_tbl.alias('containment_cnt_loc')
    m = mapper(ContainerLocation, cnt,
        properties=dict(
            position=composite(
                RackPosition.from_indices, cnt.c.row, cnt.c.col,
                comparator_factory=RackPositionComparator,
                lazy='joined'
                ),
            rack=relationship(Rack, uselist=False,
#                              cascade='all',
                              back_populates='container_locations'),
            container=relationship(Container, uselist=False,
#                                   cascade='all,delete,delete-orphan',
#                                   single_parent=True,
                                   back_populates='location',
                                   )
#                                   lazy='subquery'),
            ),
        )
    return m
