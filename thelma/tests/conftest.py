"""
"""
from pytest import fixture # pylint: disable=E0611

from thelma.models.rack import RackPosition
from thelma.models.rack import RackPositionSet
from thelma.models.rack import rack_shape_from_rows_columns
from thelma.models.racklayout import RackLayout
from thelma.models.tagging import Tag
from thelma.models.tagging import TaggedRackPositionSet
from thelma.models.user import User


__docformat__ = 'reStructuredText en'
__all__ = []


class EntityFactory(object):
    def __init__(self, entity_generator_func, default_kw):
        self.__entity_generator_func = entity_generator_func
        self.__default_kw = default_kw

    def __call__(self, **kw):
        opts = self.__default_kw.copy()
        opts.update(kw)
        return self.__entity_generator_func(**opts)


@fixture
def entity_fac(): # pylint: disable=W0613
    return EntityFactory


@fixture
def rack_shape_fac(entity_fac): # pylint: disable=W0621
    return entity_fac(rack_shape_from_rows_columns,
                          dict(number_rows=8, number_columns=12))


@fixture
def tag_fac(entity_fac): # pylint: disable=W0621
    return entity_fac(Tag,
                          dict(domain='test_domain',
                               predicate='test_predicate',
                               value='test_value'))


@fixture
def rack_position_fac(entity_fac): # pylint: disable=W0621
    return entity_fac(RackPosition.from_indices,
                          dict(row_index=0, column_index=0))


@fixture
def rack_position_set_fac(entity_fac, rack_position_fac): # pylint: disable=W0621
    kw = dict(positions=set([rack_position_fac(row_index=pos[0],
                                               column_index=pos[1])
                             for pos in
                                [(0, 1), (0, 2), (1, 0), (1, 1), (1, 3)]]))
    return entity_fac(RackPositionSet.from_positions, kw)


@fixture
def user_fac(entity_fac): # pylint: disable=W0621
    return entity_fac(User,
                          dict(username='testuser',
                               directory_user_id='cenixadm',
                               user_preferenceses=None))


@fixture
def tagged_rack_position_set_fac(
        entity_fac, tag_fac, rack_position_set_fac, user_fac): # pylint: disable=W0621
    return entity_fac(TaggedRackPositionSet,
                          dict(tags=[tag_fac(value='value%d' % cnt)
                                     for cnt in range(3)],
                               rack_position_set=rack_position_set_fac(),
                               user=user_fac()))


@fixture
def rack_layout_fac(entity_fac, rack_shape_fac, tagged_rack_position_set_fac): # pylint: disable=W0621
    kw = dict(shape=rack_shape_fac(),
              tagged_rack_position_sets=[tagged_rack_position_set_fac()])
    return entity_fac(RackLayout, kw)
