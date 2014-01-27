"""
test position set run length decoding

AAB, May 06, 2011
"""

from everest.repositories.rdb.testing import RdbContextManager
from everest.repositories.rdb.testing import persist
from thelma.interfaces import IRackPositionSet
from thelma.interfaces import IUser
from thelma.models.rack import RackPosition
from thelma.models.rack import RackPositionSet
from thelma.models.rack import RackShape
from thelma.models.racklayout import RackLayout
from thelma.models.tagging import Tag
from thelma.models.tagging import Tagged
from thelma.models.tagging import TaggedRackPositionSet
from thelma.models.user import User
from thelma.testing import ThelmaModelTestCase


class TagModelTest(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.tag_domain = 'testdomain'

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.tag_domain

    def test_add_new_tag(self):
        with RdbContextManager() as session:
            attrs = dict(domain='experimentmetadata',
                         predicate='factor1',
                         value='value1')
            persist(session, Tag, attrs)

    def test_add_same_tag_two_values(self):
        with RdbContextManager() as session:
            attrs = dict(domain='experimentmetadata',
                         predicate='factor1',
                         value='value1')
            persist(session, Tag, attrs)
            attrs = dict(domain='experimentmetadata',
                         predicate='factor1',
                         value='value2')
            persist(session, Tag, attrs)

    def test_rack_layout(self):
        with RdbContextManager() as session:
            rs = session.query(RackShape).filter_by(name="8x12").one()
            user = session.query(User).filter_by(username="it").one()
            rl = RackLayout(rs)
            tag = set([Tag('experimentdata', 'factor1', 'level1')])
            positions = RackPositionSet.from_positions(
                                         [RackPosition.from_label(label)
                                         for label in ('A1', 'A2', 'B4', 'B5')])
            trps = TaggedRackPositionSet(tag, positions, user)
            rl.tagged_rack_position_sets.append(trps)
            session.add(type(rl), rl)
            session.commit()
            session.refresh(rl)
            model_id = rl.id
            # Assure a new object is loaded to test if storing worked.
            session.expunge(rl)
            del rl
            query = session.query(RackLayout)
            fetched_model = query.filter_by(id=model_id).one()
            self.assert_not_equal(fetched_model, None)
            self.assert_equal(fetched_model.tagged_rack_position_sets[0], trps)
#            attrs = dict('tags','positions')
#            check_attributes(fetched_model, attrs)

    def test_tag_init(self):
        tag = Tag(self.tag_domain, 'cell line', 'SKMC-33')
        self.assert_false(tag is None)
        self.assert_equal(tag.domain, self.tag_domain)
        self.assert_equal(tag.predicate, 'cell line')
        self.assert_equal(tag.value, 'SKMC-33')

    def test_slug(self):
        tag = Tag(self.tag_domain, 'cell line', 'SKMC-33')
        self.assert_false(tag.slug == 'testdomain:cell line=SKMC-33')
        self.assert_equal(tag.slug, 'testdomain:cell-line=skmc-33')

    def test_tag_equality(self):
        tag = Tag(self.tag_domain, 'cell line', 'SKMC-33')
        tag2 = Tag(self.tag_domain, 'cell line', 'SKMC-33')
        tag3 = Tag(self.tag_domain, 'cell line', 'RMF')
        tag4 = Tag(self.tag_domain, 'cell_line', 'SKMC-33')
        tag5 = Tag('otherdomain', 'cell line', 'SKMC-33')
        tup = (self.tag_domain, 'cell line', 'SKMC-33')
        self.assert_equal(tag, tag2)
        self.assert_false(tag == tag3)
        self.assert_false(tag == tag4)
        self.assert_false(tag == tag5)
        self.assert_false(tag == tup)

    def test_tag_is_similar(self):
        tag = Tag(self.tag_domain, 'cell line', 'SKMC-33')
        similar_tag = Tag('other_domain', 'cell line', 'SKMC-33')
        diff_tag = Tag(self.tag_domain, 'cell line', 'SKMC-34')
        self.assert_not_equal(tag, similar_tag)
        self.assert_not_equal(tag, diff_tag)
        self.assert_true(tag.is_similar(similar_tag))
        self.assert_false(tag.is_similar(diff_tag))


class TaggingModelTest(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.tag = self._create_tag()
        self.tags = set([self.tag])

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.tag
        del self.tags

    def test_tagging_init(self):
        user = self._get_entity(IUser, 'it')
        tagged = Tagged(self.tags, user)
        tagging1 = tagged.taggings[0]
        self.assert_false(tagging1 is None)
        self.assert_equal(tagging1.user, user)
        self.assert_equal(tagging1.tag, self.tag)
        self.assert_false(tagging1.tagged is None)


class TaggedModelTest(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.tag1 = self._create_tag(domain='rackshapes', predicate='default',
                                     value='true')
        self.tag2 = self._create_tag(domain='audit', predicate='creator',
                                     value='someone')
        self.tags = set([self.tag1, self.tag2])

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.tag1
        del self.tag2
        del self.tags

    def test_tagged_init(self):
        user = self._get_entity(IUser, 'it')
        tagged_entity = Tagged(self.tags, user)
        self.assert_false(tagged_entity is None)
        tag_list = [self.tag1, self.tag2]
        self.assert_not_equal(tagged_entity.tags, tag_list)
        self.assert_equal(tagged_entity.tags, self.tags)

#    def test_taggings(self):
#        user = self.__create_user(1)
#        tagged1 = Tagged([self.tag1], user)
#        tagging1 = Tagging(self.tag1, tagged1, user)
#        self.assert_equal(tagging1, tagged1.taggings[0])
#        tagged2= Tagged([self.tag2], user)
#        tagging2 = Tagging(self.tag2, tagged2, user)
#        self.assert_equal(tagging2, tagged2.taggings[0])


class TaggedRackPositionSetModelTest(ThelmaModelTestCase):

    def test_trps_initialization(self):
        default_trps = self.__get_default_trps()
        self.assert_not_equal(default_trps, None)
        self.assert_equal(default_trps.tags,
                          self.__create_tag_set())
        rps = self._get_entity(IRackPositionSet)
        self.assert_equal(default_trps.rack_position_set, rps)
        self.assert_raises(AttributeError, getattr, *(default_trps, 'user')) #pylint: disable=W0142

    def test_tprs_equality(self):
        default_trps = self.__get_default_trps()
        tags = self.__create_tag_set()
        other_tags = self.__create_tag_set(additional_value='value3')
        rps = self._get_entity(IRackPositionSet)
        other_positions = set()
        for rack_pos in rps.positions:
            other_positions.add(rack_pos)
        add_rack_position = RackPosition.from_indices(9, 9)
        other_positions.add(add_rack_position)
        other_rps = RackPositionSet.from_positions(other_positions)
        user = self._get_entity(IUser, 'it')
        other_user = self._get_entity(IUser, 'it')
        other_user.id = 3
        trps1 = TaggedRackPositionSet(other_tags, rps, user)
        trps2 = TaggedRackPositionSet(tags, other_rps, user)
        tprs3 = TaggedRackPositionSet(tags, rps, other_user)
        self.assert_not_equal(default_trps, trps1)
        self.assert_not_equal(default_trps, trps2)
        self.assert_equal(default_trps, tprs3)
        self.assert_not_equal(default_trps, rps)

    def __get_default_trps(self):
        tags = self.__create_tag_set()
        positions = self._get_entity(IRackPositionSet)
        user = self._get_entity(IUser, 'it')
        return TaggedRackPositionSet(tags, positions, user)

    def __create_tag_set(self, additional_value=None):
        tag1 = self._create_tag()
        tag2 = self._create_tag(value='other_value')
        tag_set = set([tag1, tag2])
        if not additional_value is None:
            tag3 = self._create_tag(value=additional_value)
            tag_set.add(tag3)
        return tag_set
