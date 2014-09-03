import pytest

from thelma.models.racklayout import RackLayout


@pytest.mark.usefixtures('session_entity_repo')
class TestRackLayoutModel(object):
    package_name = 'thelma'
    ini_section_name = 'app:thelma'

    def test_rack_layout_init(self, rack_shape_fac):
        rack_shape_96 = rack_shape_fac()
        layout = RackLayout(rack_shape_96)
        assert not layout is None
        assert layout.shape == rack_shape_96

    def test_rack_layout_trps(self, rack_shape_fac, rack_position_fac,
                              rack_position_set_fac,
                              tagged_rack_position_set_fac):
        layout = RackLayout(rack_shape_fac())
        assert len(layout.tagged_rack_position_sets) == 0
        trps = tagged_rack_position_set_fac()
        layout.add_tagged_rack_position_set(trps)
        assert len(layout.tagged_rack_position_sets) == 1
        other_positions = trps.rack_position_set.positions.copy()
        other_positions.add(rack_position_fac(row_index=4,
                                              column_index=4))
        other_rps = rack_position_set_fac(positions=other_positions)
        trps2 = tagged_rack_position_set_fac(rack_position_set=other_rps)
        layout.add_tagged_rack_position_set(trps2)
        assert len(layout.tagged_rack_position_sets) == 2

    def test_layout_tags(self, rack_layout_fac, tagged_rack_position_set_fac,
                         tag_fac):
        layout = rack_layout_fac()
        other_tag = tag_fac(predicate='addition', value='tag')
        tag_set2 = set([other_tag])
        assert len(layout.get_tags()) == 3
        trps2 = tagged_rack_position_set_fac(tags=tag_set2)
        layout.add_tagged_rack_position_set(trps2)
        all_tags = layout.get_tags()
        assert len(all_tags) == 4
        assert other_tag in all_tags

    def test_layout_positions(self, rack_layout_fac,
                              tagged_rack_position_set_fac,
                              rack_position_fac, rack_position_set_fac):
        layout = rack_layout_fac()
        other_pos = rack_position_fac(row_index=4, column_index=4)
        rps = rack_position_set_fac(positions=[other_pos])
        trps2 = tagged_rack_position_set_fac(rack_position_set=rps)
        layout.add_tagged_rack_position_set(trps2)
        all_pos = layout.get_positions()
        assert len(all_pos) == 6
        assert other_pos in all_pos

    def test_layout_tags_for_position(self, rack_layout_fac,
                                      tagged_rack_position_set_fac, tag_fac,
                                      rack_position_fac,
                                      rack_position_set_fac):
        pos = rack_position_fac(row_index=1, column_index=1)
        layout = rack_layout_fac()
        assert len(layout.get_tags_for_position(pos)) == 3
        tag3 = tag_fac(domain='testing', predicate='methods', value='getters')
        trps3 = tagged_rack_position_set_fac(tags=set([tag3]))
        layout.add_tagged_rack_position_set(trps3)
        assert len(layout.get_tags_for_position(pos)) == 4
        tag4 = tag_fac(domain='testing', predicate='objects', value='getters')
        other_pos = rack_position_fac(row_index=1, column_index=1)
        rps4 = rack_position_set_fac(positions=[other_pos])
        trps4 = tagged_rack_position_set_fac(tags=set([tag4]),
                                             rack_position_set=rps4)
        layout.add_tagged_rack_position_set(trps4)
        assert len(layout.get_tags_for_position(pos)) == 5
        tag5 = tag_fac(domain='testing', predicate='failures',
                       value='getters')
        fail_pos = rack_position_fac(row_index=6, column_index=6)
        rps5 = rack_position_set_fac(positions=[fail_pos])
        trps5 = tagged_rack_position_set_fac(tags=set([tag5]),
                                             rack_position_set=rps5)
        layout.add_tagged_rack_position_set(trps5)
        matching_tags = layout.get_tags_for_position(pos)
        assert len(matching_tags) == 5
        assert tag4 in matching_tags
        assert not tag5 in matching_tags

    def test_layout_pos_for_tag(self, rack_layout_fac,
                                tagged_rack_position_set_fac, tag_fac,
                                rack_position_fac, rack_position_set_fac):
        layout = rack_layout_fac()
        tag1b = tag_fac(domain='testing', predicate='factor1', value='value1')
        trps2 = tagged_rack_position_set_fac(tags=set([tag1b]))
        layout.add_tagged_rack_position_set(trps2)
        extra_rackpos = rack_position_fac(row_index=6, column_index=6)
        rps3 = rack_position_set_fac(positions=[extra_rackpos])
        trps3 = tagged_rack_position_set_fac(tags=set([tag1b]),
                                             rack_position_set=rps3)
        layout.add_tagged_rack_position_set(trps3)
        tag4 = tag_fac(domain='testing', predicate='failures',
                       value='getters')
        fail_pos = rack_position_fac(row_index=7, column_index=7)
        rps4 = rack_position_set_fac(positions=[fail_pos])
        trps4 = tagged_rack_position_set_fac(tags=set([tag4]),
                                             rack_position_set=rps4)
        layout.add_tagged_rack_position_set(trps4)
        pos = rack_position_fac(row_index=1, column_index=1)
        matching_pos = layout.get_positions_for_tag(tag1b)
        assert len(matching_pos) == 6
        assert pos in matching_pos
        assert not fail_pos in matching_pos
