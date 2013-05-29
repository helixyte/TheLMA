"""
Tag mapper.
"""
from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import column_property
from sqlalchemy.orm import relationship
from sqlalchemy.orm.interfaces import MapperExtension
from sqlalchemy.sql import select
from sqlalchemy.sql.expression import func
from sqlalchemy.sql.expression import insert
from thelma.models.tagging import Tag
from thelma.models.tagging import Tagged

__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


class TagMapperExtension(MapperExtension):
    """
    Mapper extension to take care of inserting/updating the non-mapped
    `tag_domain`, `tag_predicate`, and `tag_value` records when a `tag`
    record is created/updated.
    """
    def __init__(self, tag_domain_tbl, tag_predicate_tbl, tag_value_tbl):
        MapperExtension.__init__(self)
        self.__tag_domain_tbl = tag_domain_tbl
        self.__tag_predicate_tbl = tag_predicate_tbl
        self.__tag_value_tbl = tag_value_tbl

    def before_insert(self, tag_mapper, connection, instance): # pylint:disable=W0613
        tn_id = self.__fetch_or_insert(connection,
                                       self.__tag_domain_tbl,
                                       'tag_domain_id',
                                       'domain',
                                       instance.domain)
        instance.tag_domain_id = tn_id
        p_id = self.__fetch_or_insert(connection,
                                       self.__tag_predicate_tbl,
                                       'tag_predicate_id',
                                       'predicate',
                                       instance.predicate)
        instance.tag_predicate_id = p_id
        v_id = self.__fetch_or_insert(connection,
                                       self.__tag_value_tbl,
                                       'tag_value_id',
                                       'value',
                                       instance.value)
        instance.tag_value_id = v_id

    def __fetch_or_insert(self, conn, ref_tbl, id_col_name, val_col_name, val):
        whereclause = getattr(ref_tbl.c, val_col_name) == val
        sel_proxy = conn.execute(select([getattr(ref_tbl.c, id_col_name)],
                                    whereclause))
        result = sel_proxy.fetchall()
        if len(result) == 1:
            # Found related entry - return found ID.
            ref_id = result[0][id_col_name]
        else:
            # Not found - insert new and return new ID.
            ins_proxy = conn.execute(insert(ref_tbl,
                                            values={val_col_name:val}))
            ref_id = ins_proxy.inserted_primary_key[0]
        return ref_id


def create_mapper(tag_tbl, tag_domain_tbl, tag_predicate_tbl, tag_value_tbl,
                  tagging_tbl):
    "Mapper factory."
    m = mapper(Tag,
               tag_tbl,
               id_attribute='tag_id',
               slug_expression=lambda cls: as_slug_expression(
                                        func.concatenate(cls.domain, ':',
                                                         cls.predicate, '=',
                                                         cls.value)),
               extension=TagMapperExtension(tag_domain_tbl,
                                            tag_predicate_tbl, tag_value_tbl),
               properties=
                    dict(tagged=relationship(Tagged,
                                             secondary=tagging_tbl,
                                             back_populates='tags'),
                         domain=column_property(
                                    select([tag_domain_tbl.c.domain]) \
                                    .where(tag_tbl.c.tag_domain_id ==
                                        tag_domain_tbl.c.tag_domain_id)
                                    ),
                         predicate=column_property(
                                    select([tag_predicate_tbl.c.predicate]) \
                                    .where(tag_tbl.c.tag_predicate_id ==
                                        tag_predicate_tbl.c.tag_predicate_id)
                                    ),
                         value=column_property(
                                    select([tag_value_tbl.c.value]) \
                                    .where(tag_tbl.c.tag_value_id ==
                                        tag_value_tbl.c.tag_value_id)
                                    ),
                         )
               )
    return m
