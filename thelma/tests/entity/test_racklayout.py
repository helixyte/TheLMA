from everest.repositories.rdb.testing import persist
from thelma.entities.racklayout import RackLayout
from thelma.tests.entity.conftest import TestEntityBase


class Fixtures(object):
    empty_rack_layout = lambda rack_layout_fac, rack_shape_8x12: \
                                rack_layout_fac(shape=rack_shape_8x12,
                                                tagged_rack_position_sets=[])
    rack_layout = lambda rack_layout_fac: rack_layout_fac()
    tag1 = lambda tag_fac: tag_fac(domain='test_domain',
                                   predicate='test_racklayout_predicate',
                                   value=1)
    tag2 = lambda tag_fac: tag_fac(domain='test_domain',
                                   predicate='test_racklayout_predicate',
                                   value=2)
    tag3 = lambda tag_fac: tag_fac(domain='test_domain',
                                   predicate='test_racklayout_predicate',
                                   value=3)
    tag4 = lambda tag_fac: tag_fac(domain='test_domain',
                                   predicate='test_racklayout_predicate1',
                                   value=2)
    tag_set = lambda tag1: [tag1]
    rack_position_0_3 = lambda rack_position_fac: \
                            rack_position_fac(row_index=0, column_index=3)
    rack_position_6_6 = lambda rack_position_fac: \
                            rack_position_fac(row_index=6, column_index=6)
    rack_position_set_0_3 = \
        lambda rack_position_set_fac, rack_position_0_3: \
            rack_position_set_fac(positions=[rack_position_0_3])
    rack_position_set_6_6 = \
        lambda rack_position_set_fac, rack_position_6_6: \
            rack_position_set_fac(positions=[rack_position_6_6])
    tagged_rack_position_set = \
        lambda tagged_rack_position_set_fac, tag_set: \
            tagged_rack_position_set_fac(tags=tag_set)


class TestRackLayoutEntity(TestEntityBase):

    def test_init(self, rack_shape_8x12):
        layout = RackLayout(rack_shape_8x12)
        assert not layout is None
        assert layout.shape == rack_shape_8x12

    def test_persist(self, nested_session, rack_layout_fac):
        rl = rack_layout_fac()
        persist(nested_session, rl, rack_layout_fac.init_kw, True)

    def test_rack_layout_trps(self, empty_rack_layout, rack_position_6_6,
                              rack_position_set_fac,
                              tagged_rack_position_set_fac):
        assert len(empty_rack_layout.tagged_rack_position_sets) == 0
        trps = tagged_rack_position_set_fac()
        empty_rack_layout.add_tagged_rack_position_set(trps)
        assert len(empty_rack_layout.tagged_rack_position_sets) == 1
        other_positions = trps.rack_position_set.positions.copy()
        other_positions.add(rack_position_6_6)
        other_rps = rack_position_set_fac(positions=other_positions)
        trps2 = tagged_rack_position_set_fac(rack_position_set=other_rps)
        empty_rack_layout.add_tagged_rack_position_set(trps2)
        assert len(empty_rack_layout.tagged_rack_position_sets) == 2

    def test_layout_tags(self, rack_layout, tagged_rack_position_set):
        assert len(rack_layout.get_tags()) == 3
        rack_layout.add_tagged_rack_position_set(tagged_rack_position_set)
        all_tags = rack_layout.get_tags()
        assert len(all_tags) == 4
        assert list(tagged_rack_position_set.tags)[0] in all_tags

    def test_layout_positions(self, rack_layout, rack_position_set_6_6,
                              tagged_rack_position_set_fac):
        trps2 = tagged_rack_position_set_fac(
                            rack_position_set=rack_position_set_6_6)
        rack_layout.add_tagged_rack_position_set(trps2)
        all_pos = rack_layout.get_positions()
        assert len(all_pos) == 6
        assert list(rack_position_set_6_6)[0] in all_pos

    def test_layout_tags_for_position(self, rack_position_set_0_3, rack_layout,
                                      tagged_rack_position_set_fac, tag2,
                                      tag3):
        default_rps = list(rack_layout.tagged_rack_position_sets)[0]
        rpos = list(default_rps.rack_position_set)[0]
        assert len(rack_layout.get_tags_for_position(rpos)) == 3
        trps2 = tagged_rack_position_set_fac(tags=set([tag2]))
        rack_layout.add_tagged_rack_position_set(trps2)
        matching_tags = rack_layout.get_tags_for_position(rpos)
        assert len(matching_tags) == 4
        assert tag2 in matching_tags
        trps3 = tagged_rack_position_set_fac(tags=set([tag3]),
                                             rack_position_set=
                                                        rack_position_set_0_3)
        rack_layout.add_tagged_rack_position_set(trps3)
        matching_tags = rack_layout.get_tags_for_position(rpos)
        assert len(matching_tags) == 4
        assert not tag3 in matching_tags

    def test_layout_pos_for_tag(self, rack_layout, tagged_rack_position_set,
                                tag2, tagged_rack_position_set_fac, tag4,
                                rack_position_set_0_3, rack_position_set_6_6):
        rack_layout.add_tagged_rack_position_set(tagged_rack_position_set)
        trps3 = tagged_rack_position_set_fac(tags=set([tag2]),
                                             rack_position_set=
                                tagged_rack_position_set.rack_position_set)
        rack_layout.add_tagged_rack_position_set(trps3)
        matching_pos = rack_layout.get_positions_for_tag(tag2)
        assert len(matching_pos) == 5
        trps4 = tagged_rack_position_set_fac(tags=set([tag2]),
                                             rack_position_set=
                                                        rack_position_set_0_3)
        rack_layout.add_tagged_rack_position_set(trps4)
        matching_pos = rack_layout.get_positions_for_tag(tag2)
        pos03 = list(rack_position_set_0_3.positions)[0]
        assert pos03 in matching_pos
        assert len(matching_pos) == 6
        trps4 = tagged_rack_position_set_fac(tags=set([tag4]),
                                             rack_position_set=
                                                    rack_position_set_6_6)
        rack_layout.add_tagged_rack_position_set(trps4)
        matching_pos = rack_layout.get_positions_for_tag(tag2)
        pos66 = list(rack_position_set_6_6.positions)[0]
        assert not pos66 in matching_pos
