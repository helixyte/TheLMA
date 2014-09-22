from everest.entities.utils import slug_from_string
from everest.repositories.rdb.testing import check_attributes
from everest.repositories.rdb.testing import persist
from thelma.tests.entity.conftest import TestEntityBase


class TestTagEntity(TestEntityBase):

    def test_init(self, tag_fac):
        tag = tag_fac()
        check_attributes(tag, tag_fac.init_kw)
        assert tag.slug == \
            slug_from_string("%s:%s=%s" %
                             (tag.domain, tag.predicate, tag.value))

    def test_persist(self, nested_session, tag_fac):
        tag = tag_fac()
        persist(nested_session, tag, tag_fac.init_kw, True)

    def test_tag_is_similar(self, tag_fac):
        tag = tag_fac(predicate='cell line', value='SKMC-33')
        similar_tag = tag_fac(domain='other_domain',
                              predicate='cell line',
                              value='SKMC-33')
        diff_tag = tag_fac(predicate='cell line', value='SKMC-34')
        assert tag != similar_tag
        assert tag != diff_tag
        assert tag.is_similar(similar_tag)
        assert not tag.is_similar(diff_tag)


class TestTaggedEntity(TestEntityBase):

    def test_init(self, tagged_fac):
        tagged = tagged_fac()
        kw = tagged_fac.init_kw
        del kw['user']
        check_attributes(tagged, kw)

    def test_persist(self, nested_session, tagged_fac):
        tagged = tagged_fac()
        kw = tagged_fac.init_kw
        del kw['user']
        persist(nested_session, tagged, kw, True)


class TestTaggedRackPositionSetEntity(TestEntityBase):

    def test_init(self, tagged_rack_position_set_fac):
        trps = tagged_rack_position_set_fac()
        kw = tagged_rack_position_set_fac.init_kw
        del kw['user']
        check_attributes(trps, kw)

#    def test_trps_initialization(self):
#        default_trps = self.__get_default_trps()
#        self.assert_not_equal(default_trps, None)
#        self.assert_equal(default_trps.tags,
#                          self.__create_tag_set())
#        rps = self._get_entity(IRackPositionSet)
#        self.assert_equal(default_trps.rack_position_set, rps)
#        self.assert_raises(AttributeError, getattr, default_trps, 'user')

