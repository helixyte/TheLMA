from thelma.models.rack import RackPosition
from thelma.models.rack import RackPositionSet
from thelma.models.rack import rack_shape_from_rows_columns
from thelma.models.racklayout import RackLayout
from thelma.models.tagging import Tag
from thelma.testing import ThelmaModelTestCase


class RackLayoutModelTest(ThelmaModelTestCase):

    def set_up(self):
        ThelmaModelTestCase.set_up(self)
        self.tag_set = set([self._create_tag(value='TestTagValue%d' % cnt)
                            for cnt in range(3)])
        self.shape = rack_shape_from_rows_columns(8, 12)
        self.rack_positions = \
            set([RackPosition.from_indices(pos[0], pos[1])
                 for pos in [(0, 1), (0, 2), (1, 0), (1, 1), (1, 3)]]
                )

    def tear_down(self):
        ThelmaModelTestCase.tear_down(self)
        del self.tag_set
        del self.shape
        del self.rack_positions

    def test_rack_layout_init(self):
        layout = RackLayout(self.shape)
        self.assert_not_equal(layout, None)
        self.assert_equal(layout.shape, self.shape)

    def test_rack_layout_trps(self):
        layout = RackLayout(self.shape)
        self.assert_true(len(layout.tagged_rack_position_sets) == 0)
        trps = self._create_tagged_rack_position_set()
        layout.add_tagged_rack_position_set(trps)
        self.assert_true(len(layout.tagged_rack_position_sets) == 1)
        other_positions = trps.rack_position_set.positions.copy()
        other_positions.add(RackPosition.from_indices(4, 4))
        other_rps = RackPositionSet.from_positions(other_positions)
        trps2 = self._create_tagged_rack_position_set(
                                        rack_position_set=other_rps)
        layout.add_tagged_rack_position_set(trps2)
        self.assert_true(len(layout.tagged_rack_position_sets) == 2)

    def test_layout_tags(self):
        layout = RackLayout(self.shape)
        trps = self._create_tagged_rack_position_set()
        layout.add_tagged_rack_position_set(trps)
        other_tag = Tag('testing', 'addition', 'tag')
        tag_set2 = set([other_tag])
        self.assert_equal(len(layout.get_tags()), 3)
        trps2 = self._create_tagged_rack_position_set(tags=tag_set2)
        layout.add_tagged_rack_position_set(trps2)
        all_tags = layout.get_tags()
        self.assert_equal(len(all_tags), 4)
        self.assert_true(other_tag in all_tags)

    def test_layout_positions(self):
        layout = RackLayout(self.shape)
        trps = self._create_tagged_rack_position_set()
        layout.add_tagged_rack_position_set(trps)
        other_pos = RackPosition.from_indices(4, 4)
        rps = RackPositionSet.from_positions([other_pos])
        trps2 = self._create_tagged_rack_position_set(rack_position_set=rps)
        layout.add_tagged_rack_position_set(trps2)
        all_pos = layout.get_positions()
        self.assert_equal(len(all_pos), 6)
        self.assert_true(other_pos in all_pos)

    def test_layout_tags_for_position(self):
        layout = RackLayout(self.shape)
        default_trps = self._create_tagged_rack_position_set()
        layout.add_tagged_rack_position_set(default_trps)
        tag3 = Tag('testing', 'methods', 'getters')
        trps3 = self._create_tagged_rack_position_set(tags=set([tag3]))
        layout.add_tagged_rack_position_set(trps3)
        tag4 = Tag('testing', 'objects', 'getters')
        other_pos = RackPosition.from_indices(1, 1)
        rps4 = RackPositionSet.from_positions([other_pos])
        trps4 = self._create_tagged_rack_position_set(tags=set([tag4]),
                                                      rack_position_set=rps4)
        layout.add_tagged_rack_position_set(trps4)
        tag5 = Tag('testing', 'failures', 'getters')
        fail_pos = RackPosition.from_indices(6, 6)
        rps5 = RackPositionSet.from_positions([fail_pos])
        trps5 = self._create_tagged_rack_position_set(tags=set([tag5]),
                                                      rack_position_set=rps5)
        layout.add_tagged_rack_position_set(trps5)
        pos = RackPosition.from_indices(1, 1)
        matching_tags = layout.get_tags_for_position(pos)
        self.assert_equal(len(matching_tags), 5)
        self.assert_true(tag4 in matching_tags)
        self.assert_false(tag5 in matching_tags)

    def test_layout_pos_for_tag(self):
        layout = RackLayout(self.shape)
        default_trps = self._create_tagged_rack_position_set()
        layout.add_tagged_rack_position_set(default_trps)
        tag1b = Tag('testing', 'factor1', 'value1')
        trps2 = self._create_tagged_rack_position_set(tags=set([tag1b]))
        layout.add_tagged_rack_position_set(trps2)
        extra_rackpos = RackPosition.from_indices(6, 6)
        rps3 = RackPositionSet.from_positions([extra_rackpos])
        trps3 = self._create_tagged_rack_position_set(tags=set([tag1b]),
                                                      rack_position_set=rps3)
        layout.add_tagged_rack_position_set(trps3)
        tag4 = Tag('testing', 'failures', 'getters')
        fail_pos = RackPosition.from_indices(7, 7)
        rps4 = RackPositionSet.from_positions([fail_pos])
        trps4 = self._create_tagged_rack_position_set(tags=set([tag4]),
                                                      rack_position_set=rps4)
        layout.add_tagged_rack_position_set(trps4)
        pos = RackPosition.from_indices(1, 1)
        matching_pos = layout.get_positions_for_tag(tag1b)
        self.assert_equal(len(matching_pos), 6)
        self.assert_true(pos in matching_pos)
        self.assert_false(fail_pos in matching_pos)

    def _create_tagged_rack_position_set(self, **kw):
        # Overwriting to use our special tag set.
        if not 'tags' in kw:
            kw['tags'] = self.tag_set
        if not 'rack_position_set' in kw:
            kw['rack_position_set'] = RackPositionSet.from_positions(
                                                          self.rack_positions)
        return ThelmaModelTestCase._create_tagged_rack_position_set(self,
                                                                    **kw)
